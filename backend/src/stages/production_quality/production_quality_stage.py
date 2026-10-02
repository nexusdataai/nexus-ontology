"""
Production & Quality Copilot Stage

Implements the production quality workflow as a 6-step journey:
1. Load Production Data — query production orders, lines, BOM, batches, quality inspections
2. OEE Calculation — calculate Overall Equipment Effectiveness per production line
3. Yield Analysis — analyze planned vs actual quantities and defect categorization
4. Quality Scoring — evaluate inspection lot results and first-pass rates per material
5. Schedule Adherence — compare planned vs actual completion dates and durations
6. Publish Results — write production KPIs, quality alerts, and analysis to S3 and simulator
"""

from typing import Any, Dict, List

from ..base_stage import BaseStage
from .production_quality_processor import ProductionQualityProcessor


class ProductionQualityStage(BaseStage):

    @property
    def stage_name(self) -> str:
        return "Production & Quality Copilot"

    @property
    def stage_description(self) -> str:
        return "AI-assisted production scheduling, yield optimization, and quality detection"

    @property
    def steps(self) -> List[Dict[str, Any]]:
        return [
            {"id": "load_production_data", "name": "Load Production Data", "order": 1,
             "description": "Query production orders, lines, BOM, batches, quality inspections"},
            {"id": "oee_calculation", "name": "OEE Calculation", "order": 2,
             "description": "Calculate Overall Equipment Effectiveness per production line"},
            {"id": "yield_analysis", "name": "Yield Analysis", "order": 3,
             "description": "Analyze planned vs actual quantities and defect categorization"},
            {"id": "quality_scoring", "name": "Quality Scoring", "order": 4,
             "description": "Evaluate inspection lot results and first-pass rates per material"},
            {"id": "schedule_adherence", "name": "Schedule Adherence", "order": 5,
             "description": "Compare planned vs actual completion dates and durations"},
            {"id": "publish_results", "name": "Publish Results", "order": 6,
             "description": "Write production KPIs, quality alerts, and analysis to S3 and simulator"},
        ]

    def __init__(self, journey_id, stage_id, job_id, region_name=None, role_arn=None):
        super().__init__(journey_id, stage_id, job_id, region_name, role_arn)
        self.setup_enhanced_logging()
        self._processor = ProductionQualityProcessor(
            log_callback=self.stage_log,
            job_id=job_id,
            journey_id=journey_id,
            s3_client=self.s3,
            config=self._config,
        )

    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio

        step_handlers = {
            "load_production_data": self._processor.step_load_production_data,
            "oee_calculation": self._processor.step_oee_calculation,
            "yield_analysis": self._processor.step_yield_analysis,
            "quality_scoring": self._processor.step_quality_scoring,
            "schedule_adherence": self._processor.step_schedule_adherence,
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
