"""
Nexus Flow stage — catalog data processors as plain Python journey steps.
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from typing import Any, Dict, List

_current_dir = os.path.dirname(os.path.abspath(__file__))
_stages_dir = os.path.dirname(_current_dir)
if _stages_dir not in sys.path:
    sys.path.insert(0, _stages_dir)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from base_stage import BaseStage


def _decimal_to_native(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_native(i) for i in obj]
    return obj


class NexusFlowStage(BaseStage):
    def __init__(self, journey_id, stage_id, job_id, region_name=None, role_arn=None):
        super().__init__(journey_id, stage_id, job_id, region_name, role_arn)
        self.processor = None
        self._flow_config = self._load_flow_config()

    def _load_flow_config(self) -> dict:
        try:
            pk = f"JOURNEY#{self.journey_id}"
            response = self.table.get_item(Key={"PK": pk, "SK": "METADATA"})
            item = response.get("Item", {})
            data = _decimal_to_native(item.get("Data", item))
            metadata = data.get("metadata", data)
            config = metadata.get("config", {})
            prod = metadata.get("productionConfig")
            if isinstance(prod, dict) and prod:
                config = {**config, **prod}
            return config
        except Exception as e:
            self.log_warning(f"Could not load Nexus Flow config: {e}")
            return {}

    @property
    def stage_name(self) -> str:
        return "Nexus Flow"

    @property
    def stage_description(self) -> str:
        return "Run harvested processors as plain Python steps in journey order"

    @property
    def steps(self) -> List[Dict[str, Any]]:
        flow_steps = self._flow_config.get("flowSteps") or []
        return [
            {
                "id": s["id"],
                "name": s.get("name") or s.get("processorType", s["id"]),
                "description": s.get("processorType", ""),
                "order": s.get("order", idx),
            }
            for idx, s in enumerate(flow_steps)
        ]

    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.processor is None:
            from nexus_flow_processor import NexusFlowProcessor

            flow_steps = self._flow_config.get("flowSteps") or []
            self.processor = NexusFlowProcessor(
                flow_steps=flow_steps,
                log_callback=lambda level, msg, sid: self.log_info(msg, sid),
            )
        result = self.processor.run_step(step_id)
        self.upload_logs_to_s3(step_id)
        return result