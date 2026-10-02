"""
Automation Diagnostics API.

Exposes a dry-run that walks every indexed Use Case, validates the YAML
schema, and cross-references each tool reference against the live
ToolRegistry and each connector_api reference against the connector_apis
registry. Returns a structured report that powers the Automation tab in
the Diagnostics page (parallel to Backends and Dashboards).

Routes (Phase 1):
  POST /api/v1/diagnostics/automation/dry-run
  GET  /api/v1/diagnostics/automation
  GET  /api/v1/diagnostics/automation/graph-integrity

Routes (Phase 2 - tool catalogue, saved journeys, runtime, smoke-test):
  GET  /api/v1/diagnostics/automation/tool-catalogue
  GET  /api/v1/diagnostics/automation/saved-journeys
  GET  /api/v1/diagnostics/automation/copilot-runtime
  POST /api/v1/diagnostics/automation/smoke-test
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException
from loguru import logger
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/diagnostics/automation", tags=["Diagnostics"])

_indexer: Any = None
_kg: Any = None
_journey_store: Any = None
_copilot: Any = None
_vector_store: Any = None
_session_store: Any = None


def configure(
    indexer: Any,
    automation_kg: Any = None,
    journey_store: Any = None,
    copilot_engine: Any = None,
    vector_store: Any = None,
    session_store: Any = None,
) -> None:
    global _indexer, _kg, _journey_store, _copilot, _vector_store, _session_store
    _indexer = indexer
    if automation_kg is not None:
        _kg = automation_kg
    if journey_store is not None:
        _journey_store = journey_store
    if copilot_engine is not None:
        _copilot = copilot_engine
    if vector_store is not None:
        _vector_store = vector_store
    if session_store is not None:
        _session_store = session_store


def _svc() -> Any:
    if not _indexer:
        raise HTTPException(status_code=503, detail="Automation indexer not available")
    return _indexer


@router.post("/dry-run")
async def dry_run():
    try:
        return await _svc().dry_run()
    except Exception as e:
        logger.error(f"Automation dry-run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def status():
    try:
        return await _svc().dry_run()
    except Exception as e:
        logger.error(f"Automation diagnostics status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph-integrity")
async def graph_integrity():
    """Phase 2: walk the indexed Use Cases and report broken cross-edges.

    Powers the Diagnostics page Automation panel's "knowledge graph"
    sub-section. Returns ``{broken_edges, orphan_registry_tools,
    use_cases_checked, missing_tools, missing_connector_apis, overall}``.
    Falls back to the indexer's own dry_run shape when the
    AutomationKnowledgeGraph helper is not configured.
    """
    if _kg is not None:
        try:
            return await _kg.validate_graph()
        except Exception as e:
            logger.warning(f"automation_kg.validate_graph failed: {e}")

    # Fallback: synthesize an integrity report from the indexer's dry_run.
    try:
        dry = await _svc().dry_run()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"graph-integrity fallback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    broken = []
    for uc in dry.get("use_cases", []):
        for tname in uc.get("missing_tools") or []:
            broken.append({"use_case_id": uc.get("use_case_id"), "type": "USES_TOOL", "missing_target": tname})
        for aid in uc.get("missing_connector_apis") or []:
            broken.append({"use_case_id": uc.get("use_case_id"), "type": "CALLS_API", "missing_target": aid})
    return {
        "use_cases_checked": dry.get("totals", {}).get("use_cases", 0),
        "missing_tools": dry.get("totals", {}).get("missing_tools", 0),
        "missing_connector_apis": dry.get("totals", {}).get("missing_connector_apis", 0),
        "broken_edges": broken,
        "orphan_registry_tools": [],
        "overall": dry.get("overall", "unknown"),
        "source": "indexer-fallback",
    }


# ============================================================================
# Phase 2 - Tool Catalogue / Saved Journeys / Copilot Runtime / Smoke Test
# ============================================================================


@router.get("/tool-catalogue")
async def tool_catalogue():
    """Tool catalogue health: YAML coverage, registry orphans, metadata
    quality, risk distribution. Powers the Diagnostics > Automation >
    Tool Catalogue panel.
    """
    try:
        return await _svc().tool_catalogue_report()
    except Exception as e:
        logger.error(f"tool-catalogue failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/taxonomy")
async def taxonomy_report():
    """Phase 3 - Cursor-for-data taxonomy health.

    Surfaces (a) automation YAMLs missing the Cursor-style header band,
    (b) stage / tool_kind alignment mismatches (`act` stage with no
    mutate/notify step, `resolve`/`diagnose` stage with a mutate/notify
    step), (c) steps still carrying a forbidden step-level
    ``connector_api`` field, and (d) YAML tools without a backing runtime.
    Powers the Diagnostics > Automation > Taxonomy panel.
    """
    try:
        return await _svc().taxonomy_report()
    except Exception as e:
        logger.error(f"taxonomy_report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/saved-journeys")
async def saved_journeys_health():
    """List saved journeys + revalidate each against the live registries.

    Returns total / by_kind / by_solution counts, broken-journey rows
    (missing tools or connector APIs after schema/registry drift), and
    a recent-10 list with per-journey validation status.
    """
    if _journey_store is None:
        return {
            "total": 0,
            "by_kind": {},
            "by_solution": {},
            "broken_journeys": [],
            "recent": [],
            "overall": "unknown",
            "source": "store-unconfigured",
        }

    try:
        journeys: List[Dict[str, Any]] = await _journey_store.list_all()
    except Exception as e:
        logger.warning(f"saved-journeys list failed: {e}")
        return {
            "total": 0, "by_kind": {}, "by_solution": {},
            "broken_journeys": [], "recent": [],
            "overall": "unhealthy", "error": str(e),
        }

    # Resolve registries once for cross-referencing.
    known_tools: set = set()
    known_apis: set = set()
    if _indexer is not None and getattr(_indexer, "_tool_registry", None) is not None:
        try:
            known_tools = {t.name for t in _indexer._tool_registry.list_tools()}
        except Exception:
            pass
    if _indexer is not None and getattr(_indexer, "_connector_apis", None) is not None:
        try:
            known_apis = {s.api_id for s in _indexer._connector_apis.list_all()}
        except Exception:
            pass

    by_kind: Dict[str, int] = {}
    by_solution: Dict[str, int] = {}
    broken: List[Dict[str, Any]] = []
    recent: List[Dict[str, Any]] = []

    # JourneyDoc lives in src.models.automation_models; import lazily so
    # we do not couple the diagnostics module to the model file at boot.
    try:
        from src.models.automation_models import JourneyDoc
    except Exception:
        JourneyDoc = None  # type: ignore

    for j in journeys:
        kind = str(j.get("kind") or "user_authored")
        solution = str(j.get("solution_id") or "unknown")
        by_kind[kind] = by_kind.get(kind, 0) + 1
        by_solution[solution] = by_solution.get(solution, 0) + 1

        validation_ok = True
        missing_tools: List[str] = []
        missing_apis: List[str] = []

        if JourneyDoc is not None:
            try:
                doc = JourneyDoc(**j)
                report = doc.validate_strict(known_tools=known_tools, known_connector_apis=known_apis)
                validation_ok = bool(report.ok)
                for err in report.errors:
                    if err.code == "unknown_tool":
                        # Extract tool name from message (best-effort).
                        msg = err.message
                        if "Tool '" in msg:
                            missing_tools.append(msg.split("Tool '")[1].split("'")[0])
                    elif err.code == "unknown_connector_api":
                        msg = err.message
                        if "connector_api '" in msg:
                            missing_apis.append(msg.split("connector_api '")[1].split("'")[0])
            except Exception:
                validation_ok = False

        if not validation_ok:
            broken.append({
                "journey_id": j.get("journey_id"),
                "title": j.get("title") or j.get("display_name"),
                "kind": kind,
                "solution_id": solution,
                "missing_tools": sorted(set(missing_tools)),
                "missing_connector_apis": sorted(set(missing_apis)),
            })

    # Recent: top 10 by updatedAt (already sorted by list_all).
    for j in journeys[:10]:
        kind = str(j.get("kind") or "user_authored")
        recent.append({
            "journey_id": j.get("journey_id"),
            "title": j.get("title") or j.get("display_name"),
            "kind": kind,
            "solution_id": j.get("solution_id"),
            "createdBy": j.get("createdBy"),
            "createdAt": j.get("createdAt"),
            "updatedAt": j.get("updatedAt"),
            "step_count": sum(len(st.get("steps", [])) for st in (j.get("stages") or [])),
            "validation_ok": j.get("journey_id") not in {b["journey_id"] for b in broken},
        })

    overall = "healthy" if not broken else ("degraded" if len(broken) <= 2 else "unhealthy")

    return {
        "total": len(journeys),
        "by_kind": by_kind,
        "by_solution": by_solution,
        "broken_journeys": broken,
        "recent": recent,
        "overall": overall,
    }


@router.get("/copilot-runtime")
async def copilot_runtime():
    """Copilot session store + vector index + AGE availability.

    Returns ``session_store`` (mode + by_status + stuck count),
    ``vector_index`` (rows per content_type), ``knowledge_graph``
    (AGE flag), and the live registry sizes.
    """
    out: Dict[str, Any] = {
        "session_store": {"mode": "unknown", "recent_count": 0, "by_status": {}, "stuck_awaiting_approval_24h": 0},
        "vector_index": {},
        "knowledge_graph": {"age_available": False, "uses_metadata_fallback": True},
        "tool_registry_size": 0,
        "connector_api_registry_size": 0,
        "overall": "healthy",
    }

    # Session store
    store = _session_store
    if store is None and _copilot is not None:
        store = getattr(_copilot, "_session_store", None)
    if store is not None:
        try:
            stats = store.count_by_status(lookback=200)
            out["session_store"] = {
                "mode": stats.get("mode", "memory"),
                "recent_count": stats.get("total_recent", 0),
                "by_status": stats.get("by_status", {}),
                "stuck_awaiting_approval_24h": stats.get("stuck_awaiting_approval_24h", 0),
            }
        except Exception as e:
            logger.warning(f"session_store.count_by_status failed: {e}")

    # Vector index per content_type.
    vs = _vector_store
    if vs is None and _indexer is not None:
        vs = getattr(_indexer, "_vector", None)
    if vs is not None:
        try:
            counts = await vs.count_by_content_type()
            out["vector_index"] = counts
        except Exception as e:
            logger.warning(f"vector_store.count_by_content_type failed: {e}")

    # Knowledge graph - AGE availability via the GraphStore.
    if _kg is not None:
        gs = getattr(_kg, "_graph", None)
        if gs is not None:
            try:
                age_ok = await gs._is_age_available()  # type: ignore[attr-defined]
                out["knowledge_graph"] = {
                    "age_available": bool(age_ok),
                    "uses_metadata_fallback": not bool(age_ok),
                }
            except Exception as e:
                logger.debug(f"AGE availability probe failed: {e}")

    # Registry sizes
    if _indexer is not None:
        try:
            tr = _indexer._tool_registry
            if tr is not None:
                out["tool_registry_size"] = len(tr.list_tools())
        except Exception:
            pass
        try:
            ca = _indexer._connector_apis
            if ca is not None:
                out["connector_api_registry_size"] = len(ca.list_all())
        except Exception:
            pass

    # Overall: unhealthy if no sessions at all OR no vector rows.
    if out["session_store"]["mode"] == "memory":
        out["overall"] = "degraded"
    if out["vector_index"] and sum(out["vector_index"].values()) == 0:
        out["overall"] = "unhealthy"
    if out["session_store"]["stuck_awaiting_approval_24h"] > 0:
        out["overall"] = "degraded"

    return out


class SmokeTestRequest(BaseModel):
    goal: Optional[str] = None
    name: Optional[str] = None


def _stage(name: str, status: str, started: float, **detail) -> Dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "detail": detail,
    }


@router.post("/smoke-test")
async def smoke_test(body: SmokeTestRequest = Body(default_factory=SmokeTestRequest)):
    """One-click end-to-end check: plan -> execute -> save -> list -> run-saved -> cleanup.

    Each stage records pass/fail + duration_ms. Idempotent: cleanup
    deletes both the journey row and the session at the end.
    """
    if _copilot is None:
        raise HTTPException(status_code=503, detail="Copilot engine not initialized")

    goal = (body.goal or "").strip() or "Recover past-due AR invoices for at-risk accounts"
    save_name = (body.name or "").strip() or f"diagnostic-smoke-{int(time.time())}"
    stages: List[Dict[str, Any]] = []
    overall = "healthy"
    session_id: Optional[str] = None
    journey_id: Optional[str] = None

    # 1. Plan
    s = time.monotonic()
    try:
        session = await _copilot.create_session(goal)
        session_id = session.session_id
        plan_r = await _copilot.plan(session_id)
        if plan_r.get("error"):
            stages.append(_stage("plan", "fail", s, error=plan_r["error"]))
            overall = "unhealthy"
        else:
            pb = plan_r.get("playbook_context") or {}
            v = plan_r.get("validation") or {}
            stages.append(_stage(
                "plan", "pass", s,
                steps=len(plan_r.get("plan", [])),
                playbook=pb.get("title") or pb.get("use_case_id"),
                score=pb.get("score"),
                validation_ok=bool(v.get("ok")),
                rag_sources=len(plan_r.get("rag_context", []) or []),
            ))
    except Exception as e:
        stages.append(_stage("plan", "fail", s, error=str(e)))
        overall = "unhealthy"

    # 2. Execute (expected to pause on the first high-risk step).
    s = time.monotonic()
    if session_id and overall != "unhealthy":
        try:
            ex = await _copilot.execute_plan(session_id)
            ps = ex.get("pending_step") or {}
            if ex.get("error"):
                stages.append(_stage("execute", "fail", s, error=ex["error"]))
                overall = "unhealthy"
            else:
                stages.append(_stage(
                    "execute", "pass", s,
                    execute_status=ex.get("status"),
                    pending_step=ps.get("step_id"),
                    pending_tool=ps.get("tool"),
                    completed=len(ex.get("steps", [])),
                ))
        except Exception as e:
            stages.append(_stage("execute", "fail", s, error=str(e)))
            overall = "unhealthy"
    else:
        stages.append(_stage("execute", "skip", s))

    # 3. Save (only when journey store is configured).
    s = time.monotonic()
    if session_id and overall != "unhealthy" and _journey_store is not None:
        try:
            sv = await _copilot.save_as_journey(session_id, save_name, journey_store=_journey_store)
            if sv.get("error"):
                stages.append(_stage("save", "fail", s, error=sv["error"]))
                overall = "unhealthy"
            else:
                journey_id = sv.get("journey_id")
                stages.append(_stage(
                    "save", "pass", s,
                    persisted=bool(sv.get("persisted")),
                    journey_id=journey_id,
                ))
        except Exception as e:
            stages.append(_stage("save", "fail", s, error=str(e)))
            overall = "unhealthy"
    else:
        stages.append(_stage("save", "skip", s,
                             reason="journey_store unavailable" if _journey_store is None else "prior failure"))

    # 4. List
    s = time.monotonic()
    if _journey_store is not None and journey_id:
        try:
            ls = await _journey_store.list_all(search=save_name)
            found = sum(1 for j in ls if j.get("journey_id") == journey_id)
            stages.append(_stage(
                "list", "pass" if found else "fail", s,
                found=found, total=len(ls),
            ))
            if not found:
                overall = "unhealthy"
        except Exception as e:
            stages.append(_stage("list", "fail", s, error=str(e)))
            overall = "unhealthy"
    else:
        stages.append(_stage("list", "skip", s))

    # 5. Run saved (replay through the engine; expected to pause on the
    # same high-risk step as the original execute).
    s = time.monotonic()
    if journey_id and overall != "unhealthy":
        try:
            journey = await _journey_store.get(journey_id)
            if not journey:
                stages.append(_stage("run_saved", "fail", s, error="journey not found"))
                overall = "unhealthy"
            else:
                title = journey.get("title") or journey.get("display_name") or journey_id
                run_session = await _copilot.create_session(f"Smoke run: {title}")
                plan_steps = []
                idx = 0
                for stage in journey.get("stages", []):
                    for step in stage.get("steps", []):
                        idx += 1
                        params = dict(step.get("params") or {})
                        foreach = params.pop("__foreach__", None) or step.get("foreach")
                        entry = {
                            "id": step.get("step_id") or step.get("id") or f"s{idx}",
                            "name": step.get("name") or f"Step {idx}",
                            "tool": step.get("tool"),
                            "params": params,
                            "rationale": step.get("description") or step.get("rationale"),
                            "requires_approval": bool(step.get("requires_approval")),
                        }
                        if foreach:
                            entry["foreach"] = foreach
                        plan_steps.append(entry)
                run_session.plan = plan_steps
                run_session.status = "planned"
                _copilot._persist_session(run_session)
                rr = await _copilot.execute_plan(run_session.session_id)
                if rr.get("error"):
                    stages.append(_stage("run_saved", "fail", s, error=rr["error"]))
                    overall = "unhealthy"
                else:
                    stages.append(_stage(
                        "run_saved", "pass", s,
                        run_status=rr.get("status"),
                        steps=len(rr.get("steps", [])),
                    ))
                # Cleanup the replay session immediately.
                try:
                    if _copilot._session_store is not None:
                        _copilot._session_store.delete(run_session.session_id)
                except Exception:
                    pass
        except Exception as e:
            stages.append(_stage("run_saved", "fail", s, error=str(e)))
            overall = "unhealthy"
    else:
        stages.append(_stage("run_saved", "skip", s))

    # 6. Cleanup (always best-effort)
    s = time.monotonic()
    cleanup_detail: Dict[str, Any] = {}
    try:
        if journey_id and _journey_store is not None:
            ok = await _journey_store.delete(journey_id)
            cleanup_detail["journey_deleted"] = bool(ok)
        if session_id and _copilot is not None and _copilot._session_store is not None:
            _copilot._session_store.delete(session_id)
            cleanup_detail["session_deleted"] = True
        stages.append(_stage("cleanup", "pass", s, **cleanup_detail))
    except Exception as e:
        stages.append(_stage("cleanup", "fail", s, error=str(e)))
        # Cleanup failure should not flip overall - the actual journey worked.

    return {
        "overall": overall,
        "goal": goal,
        "stages": stages,
        "session_id": session_id,
        "journey_id": journey_id,
    }
