"""
Procurement & Spend Analytics Stage

Implements the procurement analytics workflow as a 6-step journey:
1. Load Procurement Data — query purchase orders, invoices, vendors, goods receipts, contracts
2. Spend Classification — categorize spending and detect maverick purchases outside contracts
3. Three-Way Match — reconcile purchase orders vs goods receipts vs invoices
4. Price Variance Analysis — compare contract prices vs actual and identify anomalies
5. Vendor Scorecard — score vendors on delivery, quality, compliance, and cost metrics
6. Publish Results — write spend KPIs, alerts, and analytics to S3 and simulator
"""

from typing import Any, Dict, List

from ..base_stage import BaseStage
from .procurement_analytics_processor import ProcurementAnalyticsProcessor


class ProcurementAnalyticsStage(BaseStage):

    @property
    def stage_name(self) -> str:
        return "Procurement & Spend Analytics"

    @property
    def stage_description(self) -> str:
        return "Spend visibility, maverick detection, and intelligent invoice processing"

    @property
    def steps(self) -> List[Dict[str, Any]]:
        return [
            {"id": "load_procurement_data", "name": "Load Procurement Data", "order": 1,
             "description": "Query purchase orders, invoices, vendors, goods receipts, contracts"},
            {"id": "spend_classification", "name": "Spend Classification", "order": 2,
             "description": "Categorize spending and detect maverick purchases outside contracts"},
            {"id": "three_way_match", "name": "Three-Way Match", "order": 3,
             "description": "Reconcile purchase orders vs goods receipts vs invoices"},
            {"id": "price_variance_analysis", "name": "Price Variance Analysis", "order": 4,
             "description": "Compare contract prices vs actual and identify anomalies"},
            {"id": "vendor_scorecard", "name": "Vendor Scorecard", "order": 5,
             "description": "Score vendors on delivery, quality, compliance, and cost metrics"},
            {"id": "publish_results", "name": "Publish Results", "order": 6,
             "description": "Write spend KPIs, alerts, and analytics to S3 and simulator"},
        ]

    def __init__(self, journey_id, stage_id, job_id, region_name=None, role_arn=None):
        super().__init__(journey_id, stage_id, job_id, region_name, role_arn)
        self.setup_enhanced_logging()
        self._processor = ProcurementAnalyticsProcessor(
            log_callback=self.stage_log,
            job_id=job_id,
            journey_id=journey_id,
            s3_client=self.s3,
            config=self._config,
        )

    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio

        step_handlers = {
            "load_procurement_data": self._processor.step_load_procurement_data,
            "spend_classification": self._processor.step_spend_classification,
            "three_way_match": self._processor.step_three_way_match,
            "price_variance_analysis": self._processor.step_price_variance_analysis,
            "vendor_scorecard": self._processor.step_vendor_scorecard,
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
