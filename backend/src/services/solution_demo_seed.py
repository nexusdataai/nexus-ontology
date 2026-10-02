"""
Solution Four Views - demo data seeder.

Runs FourViewsProcessor.step_predictive / step_action_loop / step_historian
for every solution once at startup so the new Monitor / Diagnose / Predict /
Outcomes dashboards have non-empty data without the operator having to
manually run journeys first.

Idempotent: by default it only seeds an entity if its current Redis simulator
table is empty. Pass ``force=True`` to re-run regardless.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

demo_logger = logger.bind(component="solution-demo-seed")


_SOLUTION_PREFIXES = {
    "order-to-cash": "O2C",
    "demand-forecasting": "DF",
    "inventory-optimization": "IO",
    "procurement-analytics": "PA",
    "production-quality": "PQ",
    "supply-chain-risk": "SCR",
    "customer-360": "C360",
    "esg-sustainability": "ESG",
}


async def _table_is_empty(simulator: Any, schema: str, table: str) -> bool:
    if simulator is None:
        return True
    try:
        if hasattr(simulator, "_get_table_data"):
            rows = await simulator._get_table_data(schema, table)
            return not rows
    except Exception:
        pass
    return True


async def _resolve_external_sim() -> Any:
    try:
        from src.apis.fdw_api import _simulators
        sim = _simulators.get("external")
        if sim and hasattr(sim, "ensure_loaded"):
            try:
                await sim.ensure_loaded()
            except Exception:
                pass
        return sim
    except Exception:
        return None


async def seed_demo_data(
    apps: Optional[List[str]] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Run one batch of synthetic data through FourViewsProcessor for each app.

    Returns a summary dict suitable for logging.
    """
    target_apps = apps or list(_SOLUTION_PREFIXES.keys())
    summary: Dict[str, Any] = {"apps": {}, "skipped": [], "errors": []}

    try:
        from src.stages.four_views.four_views_processor import FourViewsProcessor
    except Exception as e:
        demo_logger.warning("Cannot import FourViewsProcessor: {}", e)
        return {"status": "skipped", "reason": f"import: {e}"}

    sim = await _resolve_external_sim()

    for app_id in target_apps:
        prefix = _SOLUTION_PREFIXES[app_id]
        per: Dict[str, Any] = {"prefix": prefix, "ran": [], "skipped": []}

        # Skip whole app if every result entity already has rows AND not forced.
        # The first three archetypes are written by step_predictive / action_loop;
        # the next three (KPI_Trend, Cohort_Summary, Anomaly_Score) are populated
        # only by step_action_loop and were missed on the original idempotency
        # check, so dashboards using them stayed empty across redeploys. Now we
        # require ALL six to be non-empty before declaring a solution seeded.
        archetype_seeded = False
        if not force:
            checked = [
                f"{prefix}_Action_Log",
                f"{prefix}_Forecast_Result",
                f"{prefix}_Outcome_Tracker",
                f"{prefix}_KPI_Trend",
                f"{prefix}_Cohort_Summary",
                f"{prefix}_Anomaly_Score",
            ]
            existing = []
            for ent in checked:
                if not await _table_is_empty(sim, "external_sources", ent):
                    existing.append(ent)
            if len(existing) == len(checked):
                archetype_seeded = True
                per["skipped"] = checked

        proc = FourViewsProcessor(
            app_id=app_id,
            log_callback=None,
            job_id=f"demo-seed-{prefix}",
            journey_id="demo-seed",
            s3_client=None,
            config=None,
        )

        if not archetype_seeded:
            for step_name, fn in (
                ("predictive", proc.step_predictive),
                ("action_loop", proc.step_action_loop),
                ("historian", proc.step_historian),
            ):
                try:
                    result = await fn()
                    per["ran"].append({step_name: result})
                except Exception as e:
                    demo_logger.warning("Demo seed {}/{} failed: {}", app_id, step_name, e)
                    summary["errors"].append({"app": app_id, "step": step_name, "error": str(e)})

        # ALWAYS run the extras seeder. It is independently idempotent
        # (skips entities that already have rows) and addresses the case
        # where a previous run only populated archetypes, leaving the
        # catalogue's solution-specific entities (C360_Campaign_ROI,
        # PA_Match_Result, PQ_Yield_Loss, etc.) empty.
        try:
            from src.stages.four_views.extra_entities_seed import seed_extra_entities
            extras = await seed_extra_entities(prefix, proc._sink_obj(), sim)
            if extras:
                per["extras"] = extras
        except Exception as e:
            demo_logger.warning("Demo seed extras for {} failed: {}", app_id, e)
            summary["errors"].append({"app": app_id, "step": "extras", "error": str(e)})

        if archetype_seeded and not per.get("extras"):
            summary["skipped"].append(app_id)

        summary["apps"][app_id] = per

    seeded = len(target_apps) - len(summary["skipped"])
    demo_logger.info(
        "Solution demo data seeding complete: seeded={} skipped={} errors={}",
        seeded, len(summary["skipped"]), len(summary["errors"]),
    )
    summary["status"] = "ok"
    return summary
