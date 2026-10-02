"""
Four-Views journey stages.

Each solution gets three stage IDs (registered in
``src/stages/__init__.py``):

  * ``<solution>_predictive``    -> writes forecast + scenario rows
  * ``<solution>_action_loop``   -> writes action log + outcomes + audit + KPI sample
  * ``<solution>_history``       -> writes solution-specific Mimir history series

All three are backed by a single parameterised stage class
``FourViewsStage(app_id, concern)`` so we don't repeat 24 boilerplate
classes. The ``STAGE_REGISTRY`` lookup constructs them via factory
functions stored alongside the registry.
"""

from typing import Any, Dict, List, Optional

from ..base_stage import BaseStage
from .four_views_processor import APP_TO_PREFIX, FourViewsProcessor


PREDICTIVE_STEPS = [
    {"id": "predictive", "name": "Generate Forecasts & Scenarios", "order": 1,
     "description": "Produce <PREFIX>_Forecast_Result + <PREFIX>_Scenario_Result + Mimir kpi_forecast"},
]

ACTION_LOOP_STEPS = [
    {"id": "action_loop", "name": "Action Loop & Outcomes", "order": 1,
     "description": "Write <PREFIX>_Action_Log, <PREFIX>_Outcome_Tracker, <PREFIX>_Audit_Event, KPI sample"},
]

HISTORIAN_STEPS = [
    {"id": "historian", "name": "Append History Series", "order": 1,
     "description": "Write per-solution time-series to Mimir for the Predict view"},
]


def _resolve_app_id(stage_id: str) -> str:
    """Strip suffix to get the underlying app_id."""
    for suffix in ("_predictive", "_action_loop", "_history"):
        if stage_id.endswith(suffix):
            base = stage_id[: -len(suffix)]
            # Map snake-case stage prefix back to app_id
            for app_id in APP_TO_PREFIX:
                if app_id.replace("-", "_") == base:
                    return app_id
            return base.replace("_", "-")
    return stage_id


class FourViewsStage(BaseStage):
    """
    Generic stage class. Construct through the dynamic factories below.

    The constructor signature must match BaseStage so the stage runner
    instantiates this class the same way as built-in stages.
    """

    _CONCERN: str = "predictive"  # overridden by subclasses

    def __init__(self, journey_id, stage_id, job_id, region_name=None, role_arn=None):
        super().__init__(journey_id, stage_id, job_id, region_name, role_arn)
        self.setup_enhanced_logging()
        self._app_id = _resolve_app_id(stage_id)
        self._processor = FourViewsProcessor(
            app_id=self._app_id,
            log_callback=self.stage_log,
            job_id=job_id,
            journey_id=journey_id,
            s3_client=self.s3,
            config=self._config,
        )

    @property
    def stage_name(self) -> str:
        return f"{APP_TO_PREFIX.get(self._app_id, self._app_id)} - {self._CONCERN.replace('_', ' ').title()}"

    @property
    def stage_description(self) -> str:
        return {
            "predictive": "Generate forecasts and what-if scenarios for the Predict view",
            "action_loop": "Run action loop, capture outcomes, append KPI snapshot",
            "historian": "Append time-series history to Mimir for trend dashboards",
        }.get(self._CONCERN, "Four-views stage")

    @property
    def steps(self) -> List[Dict[str, Any]]:
        if self._CONCERN == "predictive":
            return PREDICTIVE_STEPS
        if self._CONCERN == "action_loop":
            return ACTION_LOOP_STEPS
        return HISTORIAN_STEPS

    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio
        if step_id != self._CONCERN:
            return {"status": "error", "message": f"Unknown step {step_id} for concern {self._CONCERN}"}

        loop = asyncio.new_event_loop()
        try:
            if self._CONCERN == "predictive":
                result = loop.run_until_complete(self._processor.step_predictive())
            elif self._CONCERN == "action_loop":
                result = loop.run_until_complete(self._processor.step_action_loop())
            else:
                result = loop.run_until_complete(self._processor.step_historian())
        finally:
            loop.close()

        self.flush_logs_to_s3(step_id)
        return result


class PredictiveStage(FourViewsStage):
    _CONCERN = "predictive"


class ActionLoopStage(FourViewsStage):
    _CONCERN = "action_loop"


class HistorianStage(FourViewsStage):
    _CONCERN = "historian"
