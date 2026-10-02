"""
Customer 360 & Revenue Growth Stage

Implements the unified customer profile generation workflow as a 6-step journey:
1. Load Customer Data — query accounts, opportunities, invoices, payments, sentiment data
2. CLV Calculation — calculate customer lifetime value from historical revenue and frequency
3. Churn Prediction — score churn risk from behavioral signals, payment patterns, sentiment
4. Wallet Share Analysis — estimate share of customer spend vs total addressable wallet
5. Cross-Sell Scoring — identify product affinity and whitespace cross-sell opportunities
6. Publish Results — write customer profiles, KPIs, alerts to S3 and simulator
"""

from typing import Any, Dict, List

from ..base_stage import BaseStage
from .customer_360_processor import Customer360Processor


class Customer360Stage(BaseStage):

    @property
    def stage_name(self) -> str:
        return "Customer 360 & Revenue Growth"

    @property
    def stage_description(self) -> str:
        return "Unified customer profiles with churn prediction and cross-sell recommendations"

    @property
    def steps(self) -> List[Dict[str, Any]]:
        return [
            {"id": "load_customer_data", "name": "Load Customer Data", "order": 1,
             "description": "Query accounts, opportunities, invoices, payments, sentiment data"},
            {"id": "clv_calculation", "name": "CLV Calculation", "order": 2,
             "description": "Calculate customer lifetime value from historical revenue and frequency"},
            {"id": "churn_prediction", "name": "Churn Prediction", "order": 3,
             "description": "Score churn risk from behavioral signals, payment patterns, sentiment"},
            {"id": "wallet_share_analysis", "name": "Wallet Share Analysis", "order": 4,
             "description": "Estimate share of customer spend vs total addressable wallet"},
            {"id": "cross_sell_scoring", "name": "Cross-Sell Scoring", "order": 5,
             "description": "Identify product affinity and whitespace cross-sell opportunities"},
            {"id": "publish_results", "name": "Publish Results", "order": 6,
             "description": "Write customer profiles, KPIs, alerts to S3 and simulator"},
        ]

    def __init__(self, journey_id, stage_id, job_id, region_name=None, role_arn=None):
        super().__init__(journey_id, stage_id, job_id, region_name, role_arn)
        self.setup_enhanced_logging()
        self._processor = Customer360Processor(
            log_callback=self.stage_log,
            job_id=job_id,
            journey_id=journey_id,
            s3_client=self.s3,
            config=self._config,
        )

    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio

        step_handlers = {
            "load_customer_data": self._processor.step_load_customer_data,
            "clv_calculation": self._processor.step_clv_calculation,
            "churn_prediction": self._processor.step_churn_prediction,
            "wallet_share_analysis": self._processor.step_wallet_share_analysis,
            "cross_sell_scoring": self._processor.step_cross_sell_scoring,
            "publish_results": self._processor.step_publish_results,
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
