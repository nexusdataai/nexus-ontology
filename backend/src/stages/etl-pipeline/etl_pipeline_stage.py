"""
ETL Pipeline Stage

Executes data extraction, transformation, and loading using mapping rules
to hydrate the virtual data layer from source systems.

Reads sourceType and config from the journey metadata stored in DynamoDB.
"""

import os
import sys
import json
from typing import Any, Dict, List
from decimal import Decimal

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


class ETLPipelineStage(BaseStage):

    def __init__(self, journey_id, stage_id, job_id, region_name=None, role_arn=None):
        super().__init__(journey_id, stage_id, job_id, region_name, role_arn)
        self.processor = None
        self._etl_config = self._load_etl_config()

    def _load_etl_config(self) -> dict:
        """Read ETL config (sourceType, mappingRuleId, etc.) from journey metadata in DynamoDB."""
        try:
            pk = f'JOURNEY#{self.journey_id}'
            response = self.table.get_item(Key={'PK': pk, 'SK': 'METADATA'})
            item = response.get('Item', {})
            data = item.get('Data', item)
            data = _decimal_to_native(data)
            metadata = data.get('metadata', data)
            config = metadata.get('config', {})
            source_type = config.get('sourceType', metadata.get('sourceType', 'generic'))
            config['sourceType'] = source_type
            config['source_type'] = source_type
            self.log_info(f"Loaded ETL config: sourceType={source_type}, mappingRuleId={config.get('mappingRuleId', '')}")
            return config
        except Exception as e:
            self.log_warning(f"Could not load ETL config from journey metadata: {e}")
            return {}

    @property
    def stage_name(self) -> str:
        return "ETL Pipeline"

    @property
    def stage_description(self) -> str:
        return "Extract, transform, and load data from source systems using mapping rules"

    @property
    def steps(self) -> List[Dict[str, Any]]:
        return [
            {"id": "extract", "name": "Extract Source Data", "description": "Read data from source system (FDW, file, API)"},
            {"id": "validate_schema", "name": "Validate Schema", "description": "Validate source data against mapping rule field definitions"},
            {"id": "transform", "name": "Transform Data", "description": "Apply field mappings and business logic transforms"},
            {"id": "load", "name": "Load Data", "description": "Write transformed data to hydrated storage"},
            {"id": "verify", "name": "Verify Results", "description": "Row count checks, null validation, data quality"},
        ]

    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.processor is None:
            from etl_pipeline_processor import ETLPipelineProcessor
            self.processor = ETLPipelineProcessor(config=self._etl_config, log_callback=self)

        step_map = {
            "extract": self.processor.step_extract,
            "validate_schema": self.processor.step_validate_schema,
            "transform": self.processor.step_transform,
            "load": self.processor.step_load,
            "verify": self.processor.step_verify,
        }

        fn = step_map.get(step_id)
        if fn is None:
            return {"status": "error", "message": f"Unknown step: {step_id}"}

        self.processor._current_step_id = step_id
        self.log_info(f"Starting ETL step: {step_id}", step_id)
        result = fn(step_data)
        self.log_info(f"Completed ETL step: {step_id}", step_id)
        self.upload_logs_to_s3(step_id)
        return result
