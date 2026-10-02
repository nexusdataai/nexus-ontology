"""
Order-to-Cash Journey Stage

Implements the O2C Monitor as a 10-step journey:
1. Entity Resolution — match orders across Salesforce, SAP, Oracle
2. Three-Way Match — validate PO qty = delivered qty = invoiced qty
3. Anomaly Scoring — score each order for anomalies vs baselines
4. Risk Prioritization — rank orders by composite risk score
5. Workflow Actions — execute credit holds, disputes, escalations for at-risk orders
6. Dunning & Collections — send collection notices for overdue invoices
7. Action Summary — summarize all actions taken, generate audit log
8. Cash Flow Projection — project cash inflows from open AR
9. Store Results — write to S3 + push into simulator
10. Verify Results — read back result entities from VDL and display summary
"""

from typing import Any, Dict, List

from ..base_stage import BaseStage
from .o2c_processor import O2CProcessor


class OrderToCashStage(BaseStage):

    @property
    def stage_name(self) -> str:
        return "Order-to-Cash Monitor"

    @property
    def stage_description(self) -> str:
        return "Entity resolution, three-way matching, anomaly detection, workflow actions, cash flow projection"

    @property
    def steps(self) -> List[Dict[str, Any]]:
        return [
            {"id": "entity_resolution", "name": "Entity Resolution", "order": 1,
             "description": "Match orders across Salesforce, SAP, Oracle via virtual data layer"},
            {"id": "three_way_match", "name": "Three-Way Match", "order": 2,
             "description": "Validate PO qty = delivered qty = invoiced qty (+-2% / +-5%)"},
            {"id": "anomaly_scoring", "name": "Anomaly Scoring", "order": 3,
             "description": "Score each order for cycle time deviations and discrepancies"},
            {"id": "risk_prioritization", "name": "Risk Prioritization", "order": 4,
             "description": "Rank orders by composite risk: value x overdue x tier x anomaly"},
            {"id": "workflow_actions", "name": "Workflow Actions", "order": 5,
             "description": "Execute credit holds, dispute cases, SLA escalations for at-risk orders"},
            {"id": "dunning_and_collections", "name": "Dunning & Collections", "order": 6,
             "description": "Send collection notices for overdue invoices by aging tier"},
            {"id": "action_summary", "name": "Action Summary", "order": 7,
             "description": "Summarize all workflow actions taken and generate audit log"},
            {"id": "cash_flow_projection", "name": "Cash Flow Projection", "order": 8,
             "description": "Project cash inflows from open AR using payment probability"},
            {"id": "store_results", "name": "Store Results", "order": 9,
             "description": "Write order data, alerts, KPIs, actions to S3 + simulator"},
            {"id": "verify_results", "name": "Verify Results", "order": 10,
             "description": "Read back O2C result entities from VDL and display summary report"},
        ]

    def __init__(self, journey_id, stage_id, job_id, region_name=None, role_arn=None):
        super().__init__(journey_id, stage_id, job_id, region_name, role_arn)
        self.setup_enhanced_logging()
        self._processor = O2CProcessor(
            log_callback=self.stage_log,
            job_id=job_id,
            journey_id=journey_id,
            s3_client=self.s3,
            config=self._config,
        )

    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio

        step_handlers = {
            "entity_resolution": self._processor.step_entity_resolution,
            "three_way_match": self._processor.step_three_way_match,
            "anomaly_scoring": self._processor.step_anomaly_scoring,
            "risk_prioritization": self._processor.step_risk_prioritization,
            "workflow_actions": self._processor.step_workflow_actions,
            "dunning_and_collections": self._processor.step_dunning_and_collections,
            "action_summary": self._processor.step_action_summary,
            "cash_flow_projection": self._processor.step_cash_flow_projection,
            "store_results": self._processor.step_store_results,
            "verify_results": self._processor.step_verify_results,
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
