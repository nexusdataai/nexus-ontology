"""
JourneyReportBuilder -- single generic report builder.

Reads completed JobExecution rows for a given journey, looks up its
schema via ``ReportSchemaCatalog``, resolves each KPI's source path
across all jobs with the declared rollup, dispatches each section to
the right renderer, and returns the envelope the UI consumes:

    {
      "schema_version": "1",
      "journey_id": "...",
      "journey_title": "...",
      "solution_id": "...",
      "title": "Demand Forecasting Report",
      "icon": "TrendingUp",
      "summary_kpis": [{key,label,value,format,status,icon}, ...],
      "sections":     [{id,title,kind,...renderer-specific fields...}, ...],
      "total_jobs": 7,
      "generated_at": "2026-05-17T...Z",
    }

This builder is the ONLY component aware of "raw KPI dict -> rolled-up
report value". One implementation, used by every solution.
"""

from __future__ import annotations

import asyncio
import statistics
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from loguru import logger

from .journey_report_catalog import (
    ReportKpi,
    ReportSchema,
    ReportSchemaCatalog,
    ReportSection,
    get_catalog,
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class JourneyNotFound(Exception):
    """Raised when the journey METADATA row is missing in the
    transformation-system DDB. The HTTP route converts this to a 404."""


# ---------------------------------------------------------------------------
# Source-path resolution
# ---------------------------------------------------------------------------


def _resolve_path(root: Dict[str, Any], path: str) -> Any:
    """Walk a dotted path inside a nested dict / list.

    Supports list indices (``Data.kpis.alerts.0.severity``) AND object
    keys. Returns ``None`` on any miss so caller can treat missing as
    "no contribution to the rollup". Decimals are normalised to floats
    so downstream numeric ops behave."""
    if not path or root is None:
        return None
    cur: Any = root
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            try:
                idx = int(part)
            except (TypeError, ValueError):
                return None
            if idx < 0 or idx >= len(cur):
                return None
            cur = cur[idx]
            continue
        if isinstance(cur, dict):
            cur = cur.get(part)
            continue
        # Scalar in the middle of a deeper path -> miss.
        return None
    if isinstance(cur, Decimal):
        return float(cur)
    return cur


# ---------------------------------------------------------------------------
# Rollup engine
# ---------------------------------------------------------------------------


_NUMERIC_ROLLUPS = {"avg", "sum", "max", "min"}


def _coerce_number(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, bool):
        return float(int(v))
    if isinstance(v, (int, float, Decimal)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _rollup(values: List[Any], rollup: str) -> Any:
    """Apply a rollup strategy to a list of raw per-job values.

    Numeric rollups silently skip non-numeric entries (so an alert list
    with a stringified status code doesn't break the sum). ``last``
    returns the most-recent non-None value (jobs list is assumed
    newest-first). ``count_distinct`` accepts any hashable type."""
    if not values:
        return None
    rollup = (rollup or "last").lower()
    if rollup == "last":
        for v in values:
            if v is not None:
                return v
        return None
    if rollup == "count_distinct":
        try:
            return len({v for v in values if v is not None})
        except TypeError:
            # Unhashable members (e.g. list of dicts) -> count of non-None.
            return sum(1 for v in values if v is not None)
    if rollup in _NUMERIC_ROLLUPS:
        nums = [_coerce_number(v) for v in values]
        nums = [n for n in nums if n is not None]
        if not nums:
            return None
        if rollup == "sum":
            return sum(nums)
        if rollup == "avg":
            return statistics.mean(nums)
        if rollup == "max":
            return max(nums)
        if rollup == "min":
            return min(nums)
    # Unknown rollup -- return the first non-None value.
    for v in values:
        if v is not None:
            return v
    return None


def _threshold_status(value: Any, threshold: Optional[Dict[str, float]]) -> Optional[str]:
    """Map a numeric value through ``{warn, critical}`` thresholds into
    one of {"ok", "warn", "critical"}. Direction is "higher is worse"
    by default; ``invert: true`` in the threshold dict flips it."""
    if value is None or not threshold:
        return None
    v = _coerce_number(value)
    if v is None:
        return None
    invert = bool(threshold.get("invert"))
    warn = threshold.get("warn")
    crit = threshold.get("critical")
    if invert:
        if crit is not None and v <= crit:
            return "critical"
        if warn is not None and v <= warn:
            return "warn"
        return "ok"
    if crit is not None and v >= crit:
        return "critical"
    if warn is not None and v >= warn:
        return "warn"
    return "ok"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class JourneyReportBuilder:
    """Generic report builder. Reads the transformation-system DDB
    table directly via a ``TransformationJobExecutor``-style accessor."""

    def __init__(
        self,
        catalog: Optional[ReportSchemaCatalog] = None,
        executor: Any = None,
    ):
        # ``executor`` is a TransformationJobExecutor (or any object
        # exposing ``table`` + ``_get_journey_pk``). Optional so unit
        # tests can pass a mock that doesn't need real AWS creds.
        self._catalog = catalog or get_catalog()
        self._executor = executor

    # ----- public API -------------------------------------------------- #

    async def build(self, journey_id: str) -> Dict[str, Any]:
        journey_meta = await asyncio.to_thread(self._load_journey_meta, journey_id)
        if journey_meta is None:
            raise JourneyNotFound(f"Journey not found: {journey_id}")
        solution_id = journey_meta.get("solutionId") or journey_meta.get("solution_id")
        schema = self._catalog.get(solution_id)
        jobs = await asyncio.to_thread(self._list_completed_jobs, journey_id)
        transitions = await asyncio.to_thread(self._list_transitions, journey_id)
        derived = self._compute_derived(jobs, transitions)
        return {
            "schema_version": "1",
            "journey_id": journey_id,
            "journey_title": journey_meta.get("title") or journey_id,
            "solution_id": solution_id,
            "title": schema.title,
            "icon": schema.icon,
            "summary_kpis": [
                self._render_kpi(k, jobs, derived) for k in schema.summary_kpis
            ],
            "sections": [
                self._render_section(s, jobs, derived) for s in schema.sections
            ],
            "total_jobs": derived.get("total_jobs", 0),
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    # ----- DDB IO ----------------------------------------------------- #

    def _load_journey_meta(self, journey_id: str) -> Optional[Dict[str, Any]]:
        if self._executor is None:
            return None
        try:
            pk = self._executor._get_journey_pk(journey_id)
            resp = self._executor.table.get_item(Key={"PK": pk, "SK": "METADATA"})
            item = resp.get("Item")
            if not item:
                return None
            return item.get("Data") or {}
        except Exception as e:
            logger.warning("JourneyReportBuilder: METADATA read failed for {}: {}", journey_id, e)
            return None

    def _list_completed_jobs(self, journey_id: str) -> List[Dict[str, Any]]:
        """All JobExecution Data dicts under PK=JOURNEY#{id}. Excludes
        non-terminal rows so the report only counts what actually ran.
        The list is returned newest-first to match the ``last``-rollup
        semantic."""
        if self._executor is None:
            return []
        try:
            pk = self._executor._get_journey_pk(journey_id)
            jobs: List[Dict[str, Any]] = []
            last_evaluated_key = None
            while True:
                params = {
                    "KeyConditionExpression": "PK = :pk AND begins_with(SK, :sk)",
                    "ExpressionAttributeValues": {":pk": pk, ":sk": "JOB#"},
                    "ScanIndexForward": False,  # newest first
                }
                if last_evaluated_key:
                    params["ExclusiveStartKey"] = last_evaluated_key
                resp = self._executor.table.query(**params)
                for it in resp.get("Items", []):
                    if it.get("EntityType") != "JobExecution":
                        continue
                    data = it.get("Data") or {}
                    jobs.append(data)
                last_evaluated_key = resp.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break
            return jobs
        except Exception as e:
            logger.warning("JourneyReportBuilder: job query failed for {}: {}", journey_id, e)
            return []

    def _list_transitions(self, journey_id: str) -> List[Dict[str, Any]]:
        """Best-effort transition log fetch. Returns oldest-first so
        the UI timeline renders chronologically."""
        if self._executor is None:
            return []
        try:
            pk = self._executor._get_journey_pk(journey_id)
            resp = self._executor.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
                ExpressionAttributeValues={":pk": pk, ":sk": "JOBTXN#"},
                ScanIndexForward=True,
            )
            out: List[Dict[str, Any]] = []
            for it in resp.get("Items", []):
                if it.get("EntityType") != "JobTransition":
                    continue
                out.append(it.get("Data") or {})
            return out
        except Exception as e:
            logger.debug("JourneyReportBuilder: transitions query failed for {}: {}", journey_id, e)
            return []

    # ----- derived fields --------------------------------------------- #

    def _compute_derived(
        self,
        jobs: List[Dict[str, Any]],
        transitions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        total = len(jobs)
        completed = sum(1 for j in jobs if j.get("status") == "completed")
        failed = sum(1 for j in jobs if j.get("status") == "failed")
        rejected = sum(1 for j in jobs if j.get("status") == "rejected")
        cancelled = sum(1 for j in jobs if j.get("status") == "cancelled")
        durations: List[float] = []
        for j in jobs:
            ds = ((j.get("metrics") or {}).get("durationSeconds")
                  or j.get("durationSeconds"))
            n = _coerce_number(ds)
            if n is not None and n > 0:
                durations.append(n)
        avg_dur = statistics.mean(durations) if durations else 0.0
        success_rate = (completed * 100.0 / max(completed + failed, 1)) if total else 0.0
        return {
            "total_jobs": total,
            "completed_jobs": completed,
            "failed_jobs": failed,
            "rejected_jobs": rejected,
            "cancelled_jobs": cancelled,
            "avg_duration_seconds": round(avg_dur, 2),
            "success_rate": round(success_rate, 1),
            "transitions": transitions,
        }

    # ----- KPI rendering ---------------------------------------------- #

    def _resolve_kpi_values(
        self,
        kpi: ReportKpi,
        jobs: List[Dict[str, Any]],
        derived: Dict[str, Any],
    ) -> List[Any]:
        """Return the list of per-job values that the rollup will see.
        ``derived.*`` paths short-circuit to a single-element list so
        derived numbers don't get re-aggregated."""
        if not kpi.source:
            return []
        if kpi.source.startswith("derived."):
            key = kpi.source.split(".", 1)[1]
            return [derived.get(key)]
        # ``Data.kpis.x`` -- jobs already give us the ``Data`` dict.
        if kpi.source.startswith("Data."):
            rel = kpi.source[len("Data."):]
        else:
            rel = kpi.source
        return [_resolve_path(j, rel) for j in jobs]

    def _render_kpi(
        self,
        kpi: ReportKpi,
        jobs: List[Dict[str, Any]],
        derived: Dict[str, Any],
    ) -> Dict[str, Any]:
        values = self._resolve_kpi_values(kpi, jobs, derived)
        rolled = _rollup(values, kpi.rollup)
        return {
            "key": kpi.key,
            "label": kpi.label,
            "icon": kpi.icon,
            "format": kpi.format,
            "value": rolled,
            "status": _threshold_status(rolled, kpi.threshold),
        }

    # ----- Section dispatch ------------------------------------------- #

    def _render_section(
        self,
        section: ReportSection,
        jobs: List[Dict[str, Any]],
        derived: Dict[str, Any],
    ) -> Dict[str, Any]:
        kind = (section.kind or "kpi_grid").lower()
        base = {
            "id": section.id,
            "title": section.title,
            "kind": kind,
            "description": section.description,
        }
        try:
            if kind == "kpi_grid":
                base["kpis"] = [self._render_kpi(k, jobs, derived) for k in section.kpis]
            elif kind == "table":
                base.update(self._render_table(section, jobs, derived))
            elif kind == "distribution":
                base.update(self._render_distribution(section, jobs))
            elif kind == "alerts_list":
                base.update(self._render_alerts_list(section, jobs))
            elif kind == "timeline":
                base["events"] = list(derived.get("transitions") or [])
            elif kind == "step_breakdown":
                base.update(self._render_step_breakdown(jobs))
            else:
                # Unknown kind -- still render the title so the user
                # sees the section but with no body.
                base["kpis"] = []
        except Exception as e:
            logger.debug("JourneyReportBuilder: section {} render failed: {}", section.id, e)
            base["error"] = str(e)
        return base

    def _render_table(
        self,
        section: ReportSection,
        jobs: List[Dict[str, Any]],
        derived: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Each KPI becomes a column; one row per job (newest first)
        so the table is a per-job slice of the listed KPIs."""
        rows: List[Dict[str, Any]] = []
        for j in jobs:
            row: Dict[str, Any] = {"jobId": j.get("jobId")}
            for k in section.kpis:
                if k.source.startswith("derived."):
                    row[k.key] = derived.get(k.source.split(".", 1)[1])
                else:
                    rel = k.source[len("Data."):] if k.source.startswith("Data.") else k.source
                    row[k.key] = _resolve_path(j, rel)
            rows.append(row)
        return {
            "columns": [{"key": k.key, "label": k.label, "format": k.format} for k in section.kpis],
            "rows": rows,
        }

    def _render_distribution(
        self, section: ReportSection, jobs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Counts occurrences of each value at ``section.source`` across
        all jobs. The source can resolve to a scalar (one count per
        job) or a list (each element counted)."""
        if not section.source:
            return {"buckets": []}
        rel = section.source[len("Data."):] if section.source.startswith("Data.") else section.source
        buckets: Dict[str, int] = {}
        for j in jobs:
            val = _resolve_path(j, rel)
            if val is None:
                continue
            items = val if isinstance(val, list) else [val]
            for it in items:
                label = str(it) if not isinstance(it, dict) else (
                    str(it.get("label") or it.get("name") or it.get("type") or it.get("key") or "Other")
                )
                buckets[label] = buckets.get(label, 0) + 1
        total = sum(buckets.values()) or 1
        out = [
            {"label": k, "count": v, "percentage": round(v * 100.0 / total, 1)}
            for k, v in sorted(buckets.items(), key=lambda kv: -kv[1])
        ]
        return {"buckets": out, "total": sum(buckets.values())}

    def _render_alerts_list(
        self, section: ReportSection, jobs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Flatten ``section.source`` (a list field on each job) into a
        single list, grouped by ``section.grouping.key`` if present."""
        if not section.source:
            return {"alerts": [], "groups": []}
        rel = section.source[len("Data."):] if section.source.startswith("Data.") else section.source
        flat: List[Dict[str, Any]] = []
        for j in jobs:
            val = _resolve_path(j, rel)
            if isinstance(val, list):
                for it in val:
                    if isinstance(it, dict):
                        flat.append({**it, "jobId": j.get("jobId")})
                    else:
                        flat.append({"value": it, "jobId": j.get("jobId")})
        groups: List[Dict[str, Any]] = []
        if section.grouping and section.grouping.get("key"):
            gkey = section.grouping["key"]
            lmap = section.grouping.get("label_map") or {}
            counts: Dict[str, int] = {}
            for a in flat:
                k = a.get(gkey)
                if k is None:
                    continue
                counts[k] = counts.get(k, 0) + 1
            groups = [
                {"key": k, "label": lmap.get(k, k), "count": v}
                for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
            ]
        return {"alerts": flat, "groups": groups}

    def _render_step_breakdown(
        self, jobs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Aggregate per-step status counts across all jobs. For each
        step_id, count how many jobs saw it in each terminal status."""
        per_step: Dict[str, Dict[str, Any]] = {}
        for j in jobs:
            sr = j.get("stepResults") or {}
            if not isinstance(sr, dict):
                continue
            for step_id, step_data in sr.items():
                if not isinstance(step_data, dict):
                    continue
                entry = per_step.setdefault(step_id, {
                    "step_id": step_id,
                    "name": step_data.get("name") or step_id,
                    "tool": step_data.get("tool"),
                    "completed": 0,
                    "failed": 0,
                    "pending": 0,
                    "other": 0,
                    "total": 0,
                })
                # Don't overwrite name/tool if a later job omits them.
                if not entry.get("name") or entry.get("name") == step_id:
                    entry["name"] = step_data.get("name") or entry["name"]
                if not entry.get("tool"):
                    entry["tool"] = step_data.get("tool") or entry.get("tool")
                status = (step_data.get("status") or "").lower()
                entry["total"] += 1
                if status == "completed":
                    entry["completed"] += 1
                elif status == "failed":
                    entry["failed"] += 1
                elif status == "pending":
                    entry["pending"] += 1
                else:
                    entry["other"] += 1
        return {"steps": list(per_step.values())}


# ---------------------------------------------------------------------------
# Singleton accessor (wired by the gateway at startup)
# ---------------------------------------------------------------------------


_singleton: Optional[JourneyReportBuilder] = None


def get_report_builder() -> Optional[JourneyReportBuilder]:
    """Return the gateway-wired builder. ``None`` when the gateway
    hasn't initialised it (e.g. during a unit test that only loads the
    module)."""
    return _singleton


def set_report_builder(builder: JourneyReportBuilder) -> None:
    global _singleton
    _singleton = builder
