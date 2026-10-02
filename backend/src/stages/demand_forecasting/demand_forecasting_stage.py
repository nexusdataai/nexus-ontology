"""
Demand Forecasting & Planning Engine Stage

Implements the demand forecast generation workflow as a 6-step journey:
1. Feature Engineering — aggregate sales history, inventory, promotions, market signals
2. Model Ensemble — run time-series + ML models, ensemble via weighted average
3. Promotion Overlay — apply learned promotion response curves
4. Cannibalization Adjustment — cross-product substitution factors
5. Consensus Integration — merge AI forecast with sales-team overrides
6. Publish Forecast — write KPIs, alerts, forecast data to S3 + simulator
"""

from typing import Any, Dict, List

from ..base_stage import BaseStage
from .demand_forecasting_processor import DemandForecastProcessor


class DemandForecastingStage(BaseStage):

    @property
    def stage_name(self) -> str:
        return "Demand Forecasting Engine"

    @property
    def stage_description(self) -> str:
        return "AI-driven demand prediction across SKUs, regions, and channels"

    @property
    def steps(self) -> List[Dict[str, Any]]:
        return [
            {"id": "feature_engineering", "name": "Feature Engineering", "order": 1,
             "description": "Aggregate sales history, inventory, promotions, market signals into feature matrix"},
            {"id": "model_ensemble", "name": "Model Ensemble", "order": 2,
             "description": "Run time-series + ML models in parallel; combine via weighted average"},
            {"id": "promotion_overlay", "name": "Promotion Overlay", "order": 3,
             "description": "Apply learned promotion response curves per mechanic x category x region"},
            {"id": "cannibalization_adjustment", "name": "Cannibalization Adjustment", "order": 4,
             "description": "Apply cross-product substitution factors from historical data"},
            {"id": "consensus_integration", "name": "Consensus Integration", "order": 5,
             "description": "Merge AI forecast with approved Forecast_Override entries from sales team"},
            {"id": "publish_forecast", "name": "Publish Forecast", "order": 6,
             "description": "Write forecast data, KPIs, alerts to S3 and simulate SAP MRP push"},
        ]

    def __init__(self, journey_id, stage_id, job_id, region_name=None, role_arn=None):
        super().__init__(journey_id, stage_id, job_id, region_name, role_arn)
        self.setup_enhanced_logging()
        self._processor = DemandForecastProcessor(
            log_callback=self.stage_log,
            job_id=job_id,
            journey_id=journey_id,
            s3_client=self.s3,
            config=self._config,
        )

    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio

        step_handlers = {
            "feature_engineering": self._processor.step_feature_engineering,
            "model_ensemble": self._processor.step_model_ensemble,
            "promotion_overlay": self._processor.step_promotion_overlay,
            "cannibalization_adjustment": self._processor.step_cannibalization_adjustment,
            "consensus_integration": self._processor.step_consensus_integration,
            "publish_forecast": self._processor.step_publish_forecast,
        }

        handler = step_handlers.get(step_id)
        if not handler:
            return {"status": "error", "message": f"Unknown step: {step_id}"}

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(handler())
        finally:
            loop.close()

        self.flush_logs_to_s3(step_id)
        return result
