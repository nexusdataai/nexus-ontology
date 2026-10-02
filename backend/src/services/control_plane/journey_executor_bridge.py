"""
JourneyExecutorBridge -- adapter from Copilot-engine saved-journey runs
into the existing ai-engine logs/reports framework
(transformation-system DDB + S3 + LogsAndReportsService).

Why this lives here
-------------------
Saved Copilot journeys persist their *definition* in the
``foundry-workspace`` DDB table (see ``JourneyStoreService``), but the
existing per-job logs/reports API (``GET /api/v1/journeys/{id}/jobs``,
``GET .../jobs/{job_id}/logs?step_name=...``, SSE
``.../jobs/{job_id}/stream``, ``/aggregate-report``) reads from the
``transformation-system`` DDB table keyed by
``(PK=JOURNEY#{id}, SK=METADATA|JOB#...)`` and ``PK=LIVELOG#{job_id}``.

Rather than build a parallel logs API for Copilot runs, we bridge the
two: every Copilot run of a saved journey writes a ``JobExecution``
row + per-step LIVELOG entries into the transformation-system table,
and per-call sub-events (tool dispatch, virtual query, connector API,
custom-code stdout) go through ``LogsAndReportsService.add_log_entry``.
The UI then renders the Copilot Saved studio with the same endpoints
the legacy Journeys studio already uses.

Design notes
------------
- Does NOT reuse ``TransformationJobExecutor.start_job_execution`` --
  that helper hard-validates ``stage_id`` against
  ``list_available_stages()`` (only registered stages like
  ``call_processing`` / ``o2c`` are accepted). Saved Copilot journeys
  use arbitrary user-defined ``stage_id`` / ``step_id`` values, so the
  bridge ``put_item``s the JobExecution row directly with the same
  schema.
- Does reuse ``update_step_status``, ``complete_job`` and ``fail_job``
  from the executor for terminal state transitions, since those
  methods touch only ``Data.stepResults`` / ``Data.status`` and do not
  validate the stage registry.
- LIVELOG rows are written with the exact shape produced by
  ``BaseStage._write_live_logs_to_dynamo`` so the existing Layer-1
  fast path on ``/jobs/{job_id}/logs?step_name=...`` finds them with
  zero changes to ``journey_api``.
- All public methods are best-effort + idempotent. If AWS calls fail
  the bridge logs a warning and returns; the Copilot engine continues
  to run, the studio simply shows an empty job history for that run.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .journey_run_state import JobRunState

logger = logging.getLogger(__name__)


_DEFAULT_STAGE_ID = "main"
_DEFAULT_STAGE_NAME = "Main"
_DEFAULT_STAGE_ORDER = 1
_LIVELOG_TTL_SECONDS = 60 * 60  # 1 hour, matches BaseStage


class JourneyExecutorBridge:
    """Thin facade that lets ``CopilotEngine.execute_plan`` write
    JobExecution + LIVELOG + LOG rows into the transformation-system
    DDB so the existing ``/api/v1/journeys`` endpoints see Copilot runs.

    Parameters
    ----------
    executor:
        A live ``TransformationJobExecutor`` instance. We share the
        same DDB resource / table reference so credentials, region and
        retry policy match the regular Journeys path exactly.
    logs_service:
        Optional ``LogsAndReportsService``. Used for cross-step
        searchable ``LOG#`` entries. If ``None`` the bridge falls back
        to LIVELOG-only logging (per-step buffer still works).
    """

    def __init__(self, executor: Any, logs_service: Any = None):
        self._executor = executor
        self._logs_service = logs_service
        # Cache to avoid hammering ``put_item`` on every call for the
        # same journey_id.
        self._metadata_ensured: set = set()
        # Per-(job_id, step_id) rolling LIVELOG buffer so multiple
        # ``write_step_log`` calls accumulate without re-reading from
        # DDB. Matches the semantic of ``BaseStage.logs``.
        self._livelog_buffer: Dict[tuple, List[Dict[str, Any]]] = {}
        # Per-step emit counter for the rate-limit guard (avoids
        # blowing up ``LOG#`` row count when a tool prints thousands
        # of lines).
        self._emit_count: Dict[tuple, int] = {}
        self._emit_truncate_threshold = 200
        # Phase-2: per-job monotonic transition ordinal. Reset on
        # process restart; for a single run the ordinal is sufficient
        # to order JOBTXN# rows (`SK=JOBTXN#{job_id}#{ordinal:04d}`)
        # so the studio can render the transition log without
        # re-querying timestamps. JOBTXN rows ALSO carry a
        # ``timestamp`` for cross-process accuracy.
        self._txn_counter: Dict[tuple, int] = {}
        # Cache of the last observed status per (journey_id, job_id)
        # so we can populate ``from_state`` on a transition row
        # without a fresh DDB read. The bridge is the sole writer
        # of ``Data.status`` for Copilot runs so this cache is the
        # source of truth.
        self._last_state: Dict[tuple, str] = {}

    # ------------------------------------------------------------ #
    # METADATA mirror                                              #
    # ------------------------------------------------------------ #

    def ensure_metadata(
        self,
        journey_id: str,
        title: str = "",
        solution_id: Optional[str] = None,
        kind: str = "user_authored",
    ) -> bool:
        """Ensure a ``METADATA`` row exists for ``journey_id`` in the
        transformation-system DDB.

        Idempotent. Uses a ``ConditionExpression=attribute_not_exists``
        guard so we never overwrite a richer METADATA written by the
        regular Journeys path. Cached after first success.
        """
        if journey_id in self._metadata_ensured:
            return True
        if self._executor is None:
            return False
        try:
            pk = self._executor._get_journey_pk(journey_id)
            data = {
                "journeyId": journey_id,
                "title": title or journey_id,
                "solutionId": solution_id,
                "kind": kind,
                "source": "copilot_saved",
                "aggregates": {
                    "totalJobs": 0,
                    "completedJobs": 0,
                    "failedJobs": 0,
                },
                "stageSummary": {},
                "createdAt": datetime.utcnow().isoformat() + "Z",
                "updatedAt": datetime.utcnow().isoformat() + "Z",
            }
            try:
                self._executor.table.put_item(
                    Item={
                        "PK": pk,
                        "SK": "METADATA",
                        "EntityType": "Journey",
                        "GSI1PK": "JOURNEY",
                        "GSI1SK": datetime.utcnow().isoformat() + "Z",
                        "CreatedAt": datetime.utcnow().isoformat() + "Z",
                        "UpdatedAt": datetime.utcnow().isoformat() + "Z",
                        "Data": data,
                    },
                    ConditionExpression="attribute_not_exists(PK)",
                )
                logger.info(
                    "JourneyExecutorBridge: METADATA mirrored for %s",
                    journey_id,
                )
            except Exception as e:
                # ConditionalCheckFailedException is the happy path
                # for a journey that has already been mirrored (or
                # already exists from a previous run).
                msg = str(e)
                if "ConditionalCheckFailed" not in msg:
                    logger.warning(
                        "JourneyExecutorBridge.ensure_metadata put_item "
                        "for %s failed: %s",
                        journey_id, msg,
                    )
            self._metadata_ensured.add(journey_id)
            return True
        except Exception as e:
            logger.warning(
                "JourneyExecutorBridge.ensure_metadata for %s raised: %s",
                journey_id, e,
            )
            return False

    # ------------------------------------------------------------ #
    # Job lifecycle                                                #
    # ------------------------------------------------------------ #

    def start_job(
        self,
        journey_id: str,
        plan_steps: List[Dict[str, Any]],
        stage_id: str = _DEFAULT_STAGE_ID,
        stage_name: str = _DEFAULT_STAGE_NAME,
        stage_order: int = _DEFAULT_STAGE_ORDER,
        triggered_by: str = "copilot_saved",
        reason: str = "Saved-journey run via Copilot engine",
    ) -> Optional[str]:
        """Create a new ``JobExecution`` row in the transformation-
        system DDB and return its ``job_id``.

        ``plan_steps`` is the list of plan entries from
        ``CopilotEngine.execute_plan`` (each having at least an ``id``
        field). We pre-populate ``Data.stepResults`` with every
        ``step_id`` so subsequent ``update_step_status`` calls -- which
        SET on a nested path -- do not 400 on a missing key.
        """
        if self._executor is None:
            return None
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            execution_number = 1
            try:
                execution_number = self._executor.get_next_execution_number(
                    journey_id, stage_id,
                )
            except Exception:
                # First job on a freshly-mirrored journey -- GSI may
                # still be empty; default to 1.
                execution_number = 1

            job_id = f"JOB-{execution_number:03d}-{timestamp}"
            pk = self._executor._get_journey_pk(journey_id)
            sk = (
                f"JOB#{stage_order:02d}#{stage_id}#"
                f"{execution_number:03d}#{timestamp}"
            )

            step_results: Dict[str, Any] = {}
            for step in plan_steps or []:
                sid = step.get("id") or step.get("step_id")
                if not sid:
                    continue
                step_results[sid] = {
                    "status": "pending",
                    "progress": Decimal("0"),
                    "tool": step.get("tool"),
                    "name": step.get("name"),
                }

            first_step_id = None
            if plan_steps:
                first = plan_steps[0]
                first_step_id = first.get("id") or first.get("step_id")

            job_data = {
                "PK": pk,
                "SK": sk,
                "EntityType": "JobExecution",
                "GSI1PK": f"STAGE#{journey_id}#{stage_id}",
                "GSI1SK": datetime.utcnow().isoformat() + "Z",
                "CreatedAt": datetime.utcnow().isoformat() + "Z",
                "UpdatedAt": datetime.utcnow().isoformat() + "Z",
                "Data": {
                    "jobId": job_id,
                    "journeyId": journey_id,
                    "stageId": stage_id,
                    "stageName": stage_name,
                    "stageOrder": stage_order,
                    "executionNumber": execution_number,
                    "status": "in_progress",
                    "startTime": datetime.utcnow().isoformat() + "Z",
                    "endTime": None,
                    "duration": None,
                    "progress": Decimal("0"),
                    "triggeredBy": triggered_by,
                    "triggerReason": reason,
                    "retryAttempt": 0,
                    "s3Config": {
                        "logsBucket": getattr(
                            self._executor, "logs_bucket", None,
                        ),
                        "logsPrefix": (
                            f"journeys/{journey_id}/stages/{stage_id}/"
                            f"executions/{job_id}/"
                        ),
                        "reportsBucket": getattr(
                            self._executor, "reports_bucket", None,
                        ),
                        "reportsPrefix": (
                            f"journeys/{journey_id}/stages/{stage_id}/"
                            f"executions/{job_id}/"
                        ),
                        "region": getattr(self._executor, "region_name", None),
                    },
                    "currentStepIndex": 0,
                    "currentStepId": first_step_id,
                    "stepResults": step_results,
                    "jobMetrics": {
                        "totalLogs": 0,
                        "totalErrors": 0,
                        "totalWarnings": 0,
                        "overallProgress": Decimal("0"),
                        "itemsProcessed": 0,
                        "itemsTotal": len(plan_steps or []),
                    },
                    "source": "copilot_saved",
                },
            }

            self._executor.table.put_item(Item=job_data)
            logger.info(
                "JourneyExecutorBridge: started job %s for journey %s "
                "(%d steps)",
                job_id, journey_id, len(plan_steps or []),
            )
            self._record_transition(
                journey_id, job_id,
                from_state=JobRunState.pending,
                to_state=JobRunState.in_progress,
                reason="job created",
            )
            return job_id
        except Exception as e:
            logger.warning(
                "JourneyExecutorBridge.start_job for %s failed: %s",
                journey_id, e,
            )
            return None

    def mark_step_in_progress(
        self,
        journey_id: str,
        job_id: str,
        step_id: str,
        step_index: int,
    ) -> None:
        self._safe_update_step_status(
            journey_id, job_id, step_id, "in_progress", step_index,
        )

    def mark_step_completed(
        self,
        journey_id: str,
        job_id: str,
        step_id: str,
        step_index: int,
        duration_ms: int = 0,
        result_preview: str = "",
    ) -> None:
        self._safe_update_step_status(
            journey_id, job_id, step_id, "completed", step_index,
        )
        # Flush whatever LIVELOG entries have accumulated for this step
        # so the UI's first poll has something to render even if the
        # tool itself never emitted a log line.
        if duration_ms or result_preview:
            self.write_step_log(
                journey_id, job_id, step_id,
                level="INFO",
                message=(
                    f"Step {step_id} completed in {duration_ms}ms"
                    if duration_ms else f"Step {step_id} completed"
                ),
                details={"result_preview": result_preview} if result_preview else None,
                source="copilot_engine",
            )

    def mark_step_failed(
        self,
        journey_id: str,
        job_id: str,
        step_id: str,
        step_index: int,
        error: str = "",
    ) -> None:
        self._safe_update_step_status(
            journey_id, job_id, step_id, "failed", step_index,
        )
        if error:
            self.write_step_log(
                journey_id, job_id, step_id,
                level="ERROR",
                message=error,
                source="copilot_engine",
            )

    def _safe_update_step_status(
        self,
        journey_id: str,
        job_id: str,
        step_id: str,
        status: str,
        step_index: int,
    ) -> None:
        if self._executor is None or not job_id:
            return
        try:
            self._executor.update_step_status(
                journey_id, job_id, step_id, status, step_index,
            )
        except Exception as e:
            logger.warning(
                "JourneyExecutorBridge.update_step_status(%s/%s/%s -> %s) "
                "failed: %s",
                journey_id, job_id, step_id, status, e,
            )

    def complete_run(
        self,
        journey_id: str,
        job_id: str,
        items_processed: int = 0,
        items_total: int = 0,
    ) -> None:
        if self._executor is None or not job_id:
            return
        # Phase-3 (Journey-specific reports): synthesise a minimal
        # ``Data.kpis`` dict so the Copilot Saved studio's report
        # surface has something domain-meaningful to render even when
        # the journey is purely tool-driven. The journey-report builder
        # picks these up via ``Data.kpis.steps_*`` paths declared in
        # ``report-schemas/copilot-saved.yaml``.
        auto_kpis: Dict[str, Any] = {
            "steps_total": items_total or 0,
            "steps_completed": items_processed or 0,
            "steps_failed": max((items_total or 0) - (items_processed or 0), 0),
        }
        try:
            stats = self._derive_run_stats(journey_id, job_id)
            auto_kpis.update(stats)
        except Exception as e:
            logger.debug(
                "JourneyExecutorBridge.complete_run kpi derive failed: %s", e,
            )
        try:
            self._executor.complete_job(
                journey_id, job_id,
                items_processed=items_processed,
                items_total=items_total,
                stage_kpis=auto_kpis,
            )
        except TypeError:
            # Older complete_job signature without stage_kpis kwarg.
            try:
                self._executor.complete_job(
                    journey_id, job_id,
                    items_processed=items_processed,
                    items_total=items_total,
                )
            except Exception as e:
                logger.warning(
                    "JourneyExecutorBridge.complete_run(%s/%s) failed: %s",
                    journey_id, job_id, e,
                )
        except Exception as e:
            logger.warning(
                "JourneyExecutorBridge.complete_run(%s/%s) failed: %s",
                journey_id, job_id, e,
            )
        self._record_transition(
            journey_id, job_id,
            from_state=self._observed_state(journey_id, job_id, JobRunState.in_progress),
            to_state=JobRunState.completed,
        )

    def _derive_run_stats(self, journey_id: str, job_id: str) -> Dict[str, Any]:
        """Best-effort secondary KPI dict pulled from the JobExecution
        row + transition log. Used as the Copilot Saved report's
        ``Data.kpis``."""
        out: Dict[str, Any] = {}
        try:
            job = self._executor.get_job_execution(journey_id, job_id)
            if job:
                # Convert the bridge start/end timestamps to seconds.
                start = job.get("startTime")
                if start and isinstance(start, str):
                    try:
                        from datetime import datetime as _dt
                        st = _dt.fromisoformat(start.replace("Z", "+00:00"))
                        end = datetime.utcnow().replace(tzinfo=timezone.utc)
                        out["duration_seconds"] = round((end - st).total_seconds(), 2)
                    except Exception:
                        pass
                # Count distinct tools across step results.
                sr = job.get("stepResults") or {}
                tools = set()
                for v in sr.values():
                    if isinstance(v, dict) and v.get("tool"):
                        tools.add(v["tool"])
                if tools:
                    out["tools_invoked"] = len(tools)
        except Exception:
            pass
        return out

    def fail_run(
        self,
        journey_id: str,
        job_id: str,
        error: str = "",
    ) -> None:
        if self._executor is None or not job_id:
            return
        try:
            self._executor.fail_job(journey_id, job_id, error or "")
        except Exception as e:
            logger.warning(
                "JourneyExecutorBridge.fail_run(%s/%s) failed: %s",
                journey_id, job_id, e,
            )
        self._record_transition(
            journey_id, job_id,
            from_state=self._observed_state(journey_id, job_id, JobRunState.in_progress),
            to_state=JobRunState.failed,
            reason=error or None,
        )

    # ------------------------------------------------------------ #
    # Phase-2 state transitions                                    #
    # ------------------------------------------------------------ #

    def mark_awaiting_approval(
        self,
        journey_id: str,
        job_id: str,
        step_id: str,
        pending_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Flip ``Data.status`` to ``awaiting_step_approval`` and stash
        the pending-step payload on the JobExecution so the studio's
        ``/jobs/{job_id}/status`` payload can drive an inline
        ``PendingStepCard`` without a second round-trip.

        Records the transition + writes a LIVELOG line on the pausing
        step so the per-step view shows the pause inline."""
        if self._executor is None or not job_id:
            return
        ok = self._set_overall_status(
            journey_id, job_id, JobRunState.awaiting_step_approval,
            extra_data={"pendingStep": pending_payload or {}},
        )
        if not ok:
            return
        # Surface the pause in the per-step log so the inline console
        # shows "Awaiting approval" alongside the engine boundary lines.
        try:
            tool = (pending_payload or {}).get("tool")
            self.write_step_log(
                journey_id, job_id, step_id,
                level="WARNING",
                message=(
                    f"Awaiting approval for step {step_id}"
                    + (f" (tool: {tool})" if tool else "")
                ),
                details={"pending_step": pending_payload} if pending_payload else None,
                source="copilot_engine",
            )
        except Exception as e:
            logger.debug(f"awaiting-approval livelog write failed: {e}")
        self._record_transition(
            journey_id, job_id,
            from_state=JobRunState.in_progress,
            to_state=JobRunState.awaiting_step_approval,
            step_id=step_id,
            reason="step requires approval",
        )

    def reject_run(
        self,
        journey_id: str,
        job_id: str,
        step_id: str = "",
        reason: str = "step rejected by user",
    ) -> None:
        """Flip ``Data.status`` to ``rejected`` after the user rejects
        a pending step. Aggregates the run as a ``failed`` job so the
        card's Failed counter increments (DDB only has aggregate
        buckets for completed/failed today; ``rejected`` rolls into
        ``failed`` at the aggregate layer)."""
        if self._executor is None or not job_id:
            return
        ok = self._set_overall_status(
            journey_id, job_id, JobRunState.rejected,
            extra_data={
                "endTime": datetime.utcnow().isoformat() + "Z",
                "errorMessage": reason,
                "pendingStep": None,
            },
        )
        if not ok:
            return
        try:
            if step_id:
                self.write_step_log(
                    journey_id, job_id, step_id,
                    level="ERROR",
                    message=reason,
                    source="copilot_engine",
                )
        except Exception:
            pass
        # Update the journey aggregates so the card surface counts it
        # as a failed job (rejected is, from an outcome standpoint, a
        # non-completed run).
        try:
            self._executor.update_journey_aggregates(
                journey_id, _DEFAULT_STAGE_ID, "failed",
            )
        except Exception as e:
            logger.debug(f"reject_run aggregates failed: {e}")
        self._record_transition(
            journey_id, job_id,
            from_state=JobRunState.awaiting_step_approval,
            to_state=JobRunState.rejected,
            step_id=step_id or None,
            reason=reason,
        )

    def cancel_run(
        self,
        journey_id: str,
        job_id: str,
        reason: str = "cancelled by user",
    ) -> None:
        """Flip ``Data.status`` to ``cancelled``. Mirrors ``reject_run``
        but is initiated by the user rather than a rejection of a
        specific step."""
        if self._executor is None or not job_id:
            return
        prev = self._observed_state(journey_id, job_id, JobRunState.in_progress)
        ok = self._set_overall_status(
            journey_id, job_id, JobRunState.cancelled,
            extra_data={
                "endTime": datetime.utcnow().isoformat() + "Z",
                "errorMessage": reason,
                "pendingStep": None,
            },
        )
        if not ok:
            return
        try:
            self._executor.update_journey_aggregates(
                journey_id, _DEFAULT_STAGE_ID, "failed",
            )
        except Exception as e:
            logger.debug(f"cancel_run aggregates failed: {e}")
        self._record_transition(
            journey_id, job_id,
            from_state=prev,
            to_state=JobRunState.cancelled,
            reason=reason,
        )

    # ------------------------------------------------------------ #
    # Internal helpers                                             #
    # ------------------------------------------------------------ #

    def _set_overall_status(
        self,
        journey_id: str,
        job_id: str,
        new_state: JobRunState,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Direct ``update_item`` on the JobExecution row to flip
        ``Data.status`` (and optionally other ``Data.*`` fields) in a
        single call. Used for non-terminal transitions where the
        executor's ``complete_job`` / ``fail_job`` would be wrong
        (they finalise duration / aggregates)."""
        try:
            job_data = self._executor.get_job_execution(journey_id, job_id)
            if not job_data:
                logger.debug(
                    "JourneyExecutorBridge._set_overall_status: job %s "
                    "not found for %s",
                    job_id, journey_id,
                )
                return False
            stage_id = job_data["stageId"]
            execution_number = int(job_data["executionNumber"])
            stage_order = int(job_data.get("stageOrder", 1))
            timestamp = job_id.split("-")[-1]
            sk = (
                f"JOB#{stage_order:02d}#{stage_id}#"
                f"{execution_number:03d}#{timestamp}"
            )
            expr_names: Dict[str, str] = {"#data": "Data", "#status": "status"}
            expr_values: Dict[str, Any] = {
                ":status": new_state.value,
                ":updated_at": datetime.utcnow().isoformat() + "Z",
            }
            set_parts = [
                "#data.#status = :status",
                "#data.updatedAt = :updated_at",
            ]
            for i, (k, v) in enumerate(sorted((extra_data or {}).items())):
                name_key = f"#x{i}"
                val_key = f":v{i}"
                expr_names[name_key] = k
                expr_values[val_key] = v if v is not None else None
                set_parts.append(f"#data.{name_key} = {val_key}")
            self._executor.table.update_item(
                Key={
                    "PK": self._executor._get_journey_pk(journey_id),
                    "SK": sk,
                },
                UpdateExpression="SET " + ", ".join(set_parts),
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
            self._last_state[(journey_id, job_id)] = new_state.value
            return True
        except Exception as e:
            logger.warning(
                "JourneyExecutorBridge._set_overall_status(%s/%s -> %s) "
                "failed: %s",
                journey_id, job_id, new_state.value, e,
            )
            return False

    def _observed_state(
        self,
        journey_id: str,
        job_id: str,
        default: JobRunState,
    ) -> JobRunState:
        """Best-effort lookup of the last status the bridge wrote for
        this job. Used as the ``from_state`` of a transition row when
        the caller can't supply one explicitly."""
        cached = self._last_state.get((journey_id, job_id))
        if cached:
            try:
                return JobRunState(cached)
            except ValueError:
                return default
        return default

    def _record_transition(
        self,
        journey_id: str,
        job_id: str,
        from_state: JobRunState,
        to_state: JobRunState,
        step_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Append one ``EntityType=JobTransition`` row to the
        transformation-system DDB at
        ``PK=JOURNEY#{id}, SK=JOBTXN#{job_id}#{ts_us}`` where
        ``ts_us`` is a microsecond-precision UTC timestamp.

        Why timestamp-not-ordinal: behind an LB the run + approve-step
        HTTP calls may land on DIFFERENT pods, and each pod's
        in-process ordinal counter starts at zero -- using an ordinal
        as the SK suffix causes cross-pod collisions (the second
        pod's first transition overwrites the first pod's first
        transition). A microsecond timestamp is monotonic across
        processes (clocks are NTP-synced on the cluster) and sorts
        lexicographically the same way the events occurred. We still
        keep the in-process ``ordinal`` for observability in the
        Data body, but it is no longer authoritative for ordering.

        Idempotent failures (DDB outage, missing executor) are
        swallowed -- the transition log is a best-effort audit, not
        the source of truth for the row status."""
        if self._executor is None or not job_id:
            return
        try:
            key = (journey_id, job_id)
            self._txn_counter[key] = self._txn_counter.get(key, 0) + 1
            ordinal = self._txn_counter[key]
            ts_us = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            iso_ts = datetime.utcnow().isoformat() + "Z"
            sk = f"JOBTXN#{job_id}#{ts_us}"
            item: Dict[str, Any] = {
                "PK": self._executor._get_journey_pk(journey_id),
                "SK": sk,
                "EntityType": "JobTransition",
                "GSI1PK": f"JOBTXN#{journey_id}#{job_id}",
                "GSI1SK": ts_us,
                "CreatedAt": iso_ts,
                "Data": {
                    "journeyId": journey_id,
                    "jobId": job_id,
                    "ordinal": ordinal,  # per-pod best-effort
                    "fromState": from_state.value,
                    "toState": to_state.value,
                    "timestamp": iso_ts,
                    "stepId": step_id,
                    "reason": reason,
                },
            }
            self._executor.table.put_item(Item=item)
            # Keep the in-memory cache aligned even when the to_state
            # came from a path that did not call ``_set_overall_status``
            # (e.g. ``complete_run`` which goes through
            # ``executor.complete_job``).
            self._last_state[(journey_id, job_id)] = to_state.value
        except Exception as e:
            logger.debug(
                "JourneyExecutorBridge._record_transition(%s/%s) failed: %s",
                journey_id, job_id, e,
            )

    # ------------------------------------------------------------ #
    # Per-step log writer                                          #
    # ------------------------------------------------------------ #

    def write_step_log(
        self,
        journey_id: str,
        job_id: str,
        step_id: str,
        level: str = "INFO",
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        source: str = "tool",
    ) -> None:
        """Append a single log line to BOTH:

        - the LIVELOG buffer (Layer-1 fast path for
          ``GET /jobs/{job_id}/logs?step_name={step_id}``), and
        - the ``LOG#`` items via ``LogsAndReportsService.add_log_entry``
          for cross-step search.

        Rate-limited per (job_id, step_id) so a chatty custom-code
        step cannot blow up the LOG# row count: after 200 entries we
        emit a single "truncated" marker and drop subsequent lines.
        """
        if not job_id or not step_id:
            return

        key = (job_id, step_id)
        count = self._emit_count.get(key, 0)
        if count == self._emit_truncate_threshold:
            self._emit_count[key] = count + 1
            self._append_livelog(
                job_id, step_id,
                level="WARNING",
                message=(
                    f"Per-step log truncated at "
                    f"{self._emit_truncate_threshold} entries -- "
                    "full trace in S3 once the job completes."
                ),
                details=None,
                source="bridge",
                journey_id=journey_id,
            )
            return
        if count > self._emit_truncate_threshold:
            self._emit_count[key] = count + 1
            return
        self._emit_count[key] = count + 1

        self._append_livelog(
            job_id, step_id,
            level=(level or "INFO").upper(),
            message=message or "",
            details=details,
            source=source,
            journey_id=journey_id,
        )

        # Mirror to LogsAndReportsService so cross-step search and
        # the legacy ``/logs/search`` endpoint pick it up. Sync call
        # is fine -- ``add_log_entry`` itself uses ``asyncio.to_thread``
        # under the hood but the helper we touch (`add_job_log_entry`
        # on the manager) is plain DDB.
        if self._logs_service is not None:
            try:
                manager = getattr(self._logs_service, "manager", None)
                if manager is not None:
                    manager.add_job_log_entry(
                        journey_id, job_id, step_id,
                        (level or "INFO").lower(),
                        message or "",
                        details or {},
                        source,
                    )
            except Exception as e:
                logger.debug(
                    "LogsAndReportsService.add_job_log_entry failed: %s", e,
                )

    def _append_livelog(
        self,
        job_id: str,
        step_id: str,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]],
        source: str,
        journey_id: str = "",
    ) -> None:
        """Append a log entry to the rolling LIVELOG buffer for
        (job_id, step_id) and persist the full buffer to DDB.

        Uses the exact JSON shape produced by
        ``BaseStage._write_live_logs_to_dynamo`` so the legacy
        ``/jobs/{job_id}/logs?step_name=...`` handler reads it
        without any change."""
        if self._executor is None:
            return
        key = (job_id, step_id)
        buf = self._livelog_buffer.setdefault(key, [])
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "step_id": step_id,
            "stage_id": _DEFAULT_STAGE_ID,
            "job_id": job_id,
            "source": source,
        }
        if details:
            entry["details"] = details
        buf.append(entry)
        try:
            self._executor.table.put_item(Item={
                "PK": f"LIVELOG#{job_id}",
                "SK": step_id,
                "logs_json": json.dumps(buf, default=str),
                "log_count": len(buf),
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "ttl": int(datetime.utcnow().timestamp()) + _LIVELOG_TTL_SECONDS,
            })
        except Exception as e:
            logger.debug(
                "LIVELOG put_item failed for %s/%s: %s",
                job_id, step_id, e,
            )
