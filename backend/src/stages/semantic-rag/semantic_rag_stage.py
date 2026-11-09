"""
Knowledge Processor Stage

Uses BaseStage.stage_log() and setup_enhanced_logging() for common logging
shared across all journey stages.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

_stages_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _stages_dir not in sys.path:
    sys.path.insert(0, _stages_dir)

from base_stage import BaseStage

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

_sub_pkg_name = "src.stages.semantic_rag"
if _sub_pkg_name in sys.modules:
    import importlib.util as _ilu
    _cp_path = os.path.join(_current_dir, "semantic_rag_processor.py")
    _cp_mod_name = f"{_sub_pkg_name}.semantic_rag_processor"
    if _cp_mod_name not in sys.modules:
        _cp_spec = _ilu.spec_from_file_location(_cp_mod_name, _cp_path)
        _cp_mod = _ilu.module_from_spec(_cp_spec)
        _cp_mod.__package__ = _sub_pkg_name
        sys.modules[_cp_mod_name] = _cp_mod
        _cp_spec.loader.exec_module(_cp_mod)
    else:
        _cp_mod = sys.modules[_cp_mod_name]
    SemanticRagProcessor = _cp_mod.SemanticRagProcessor
    SemanticRagConfig = _cp_mod.SemanticRagConfig
else:
    from semantic_rag_processor import SemanticRagProcessor, SemanticRagConfig


class SemanticRagStage(BaseStage):

    def __init__(self, journey_id: str, stage_id: str, job_id: str,
                 region_name: str = None, role_arn: Optional[str] = None,
                 enable_logging: bool = True):
        super().__init__(journey_id, stage_id, job_id, region_name, role_arn)
        self.processor: Optional[SemanticRagProcessor] = None
        self.config: Optional[SemanticRagConfig] = None
        if enable_logging:
            self.setup_enhanced_logging()

    @property
    def stage_name(self) -> str:
        return "Knowledge Processor"

    @property
    def stage_description(self) -> str:
        return "Build enterprise knowledge graph: extract, enrich, embed, load into Vector DB + Graph DB"

    @property
    def steps(self) -> List[Dict[str, Any]]:
        return [
            {'id': 'extract_unified_schema', 'name': 'Extract Unified Schema', 'description': 'Read canonical-entities.yaml into virtual entity docs', 'order': 0, 'estimatedDuration': '30s'},
            {'id': 'resolve_fdw_mapping', 'name': 'Resolve FDW Mapping', 'description': 'Match schema entities to live FDW + simulator tables', 'order': 1, 'estimatedDuration': '30s'},
            {'id': 'extract_mapping_rules', 'name': 'Extract Mapping Rules', 'description': 'Read active mapping rules and enrich schema docs', 'order': 2, 'estimatedDuration': '30s'},
            {'id': 'extract_policies', 'name': 'Extract Policies', 'description': 'Parse business policy documents', 'order': 3, 'estimatedDuration': '30s'},
            {'id': 'extract_workflows', 'name': 'Extract Workflows', 'description': 'Parse workflow definitions', 'order': 4, 'estimatedDuration': '30s'},
            {'id': 'extract_integrations', 'name': 'Extract Integrations', 'description': 'Parse integration field mappings', 'order': 5, 'estimatedDuration': '30s'},
            {'id': 'normalize', 'name': 'Normalize to .onto Bundle', 'description': 'Merge, deduplicate, produce .onto bundle', 'order': 6, 'estimatedDuration': '30s'},
            {'id': 'enrich', 'name': 'LLM Semantic Enrichment', 'description': 'Generate semantic descriptions with LLM', 'order': 7, 'estimatedDuration': '5m'},
            {'id': 'chunk_embed', 'name': 'Chunk & Embed', 'description': 'Semantic chunking + embedding generation', 'order': 8, 'estimatedDuration': '2m'},
            {'id': 'load_vector', 'name': 'Load Vector DB', 'description': 'Upsert embeddings into pgvector', 'order': 9, 'estimatedDuration': '1m'},
            {'id': 'index_nlq_exemplars', 'name': 'Index NLQ Exemplars', 'description': 'Generate NLP query exemplars from curated YAML + schema templates and index for AI Query Builder', 'order': 10, 'estimatedDuration': '1m'},
            {'id': 'load_graph', 'name': 'Load Graph DB', 'description': 'Load relationships into graph DB', 'order': 11, 'estimatedDuration': '1m'},
            {'id': 'validate', 'name': 'Validate Quality', 'description': 'Run black-box test scenarios', 'order': 12, 'estimatedDuration': '2m'},
        ]

    def _get_config_from_step_data(self, step_data: Dict[str, Any]) -> SemanticRagConfig:
        config_data = step_data.get('config', {})
        journey_metadata = step_data.get('journey_metadata', {})
        s3_bucket = ""
        try:
            # .onto bundles and validation reports live in solution-results storage.
            s3_bucket = (
                self._config.s3_solution_results_bucket
                or self._config.s3_recordings_bucket
            )
        except Exception:
            pass
        return SemanticRagConfig(
            policy_path=config_data.get('policy_path', journey_metadata.get('policy_path', '')),
            workflow_path=config_data.get('workflow_path', journey_metadata.get('workflow_path', '')),
            integration_path=config_data.get('integration_path', journey_metadata.get('integration_path', '')),
            policy_s3_prefix=config_data.get('policy_s3_prefix', ''),
            enrich_with_llm=config_data.get('enrich_with_llm', True),
            llm_model=config_data.get('llm_model', 'gpt-4o-mini'),
            skip_enrichment=config_data.get('skip_enrichment', False),
            skip_graph=config_data.get('skip_graph', False),
            skip_validation=config_data.get('skip_validation', False),
            aws_region=config_data.get('aws_region', self.region_name or 'us-east-1'),
            s3_bucket=config_data.get('s3_bucket', s3_bucket),
        )

    def _ensure_processor(self, step_data: Dict[str, Any]):
        if self.processor is None:
            self.config = self._get_config_from_step_data(step_data)
            self.processor = SemanticRagProcessor(
                config=self.config,
                log_callback=self.stage_log,
                job_id=self.job_id,
                journey_id=self.journey_id,
            )
            self.stage_log('INFO', "Initialized SemanticRagProcessor")
            self.stage_log('INFO', f"  policy_path: {self.config.policy_path}")
            self.stage_log('INFO', f"  workflow_path: {self.config.workflow_path}")
            self.stage_log('INFO', f"  integration_path: {self.config.integration_path}")

    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        step_start = datetime.now(timezone.utc)
        self.stage_log('INFO', f"Starting step: {step_id}", step_id)

        try:
            self._ensure_processor(step_data)

            step_handlers = {
                'extract_unified_schema': self.processor.step_extract_unified_schema,
                'resolve_fdw_mapping': self.processor.step_resolve_fdw_mapping,
                'extract_fdw': self.processor.step_extract_fdw,
                'extract_mapping_rules': self.processor.step_extract_mapping_rules,
                'extract_policies': self.processor.step_extract_policies,
                'extract_workflows': self.processor.step_extract_workflows,
                'extract_integrations': self.processor.step_extract_integrations,
                'normalize': self.processor.step_normalize,
                'enrich': self.processor.step_enrich,
                'chunk_embed': self.processor.step_chunk_embed,
                'load_vector': self.processor.step_load_vector,
                'index_nlq_exemplars': self.processor.step_index_nlq_exemplars,
                'load_graph': self.processor.step_load_graph,
                'validate': self.processor.step_validate,
            }

            handler = step_handlers.get(step_id)
            if not handler:
                self.stage_log('ERROR', f"Unknown step: {step_id}", step_id)
                return {'status': 'failed', 'error': f'Unknown step: {step_id}'}

            result = handler()

            elapsed = (datetime.now(timezone.utc) - step_start).total_seconds()
            result['elapsed_seconds'] = round(elapsed, 2)
            self.set_metric(f"{step_id}_elapsed", round(elapsed, 2))
            self.stage_log('INFO', f"Step {step_id} completed in {elapsed:.1f}s", step_id)

            result_summary = {k: v for k, v in result.items() if k != 'report'}
            self.stage_log('INFO', f"Result: {json.dumps(result_summary, default=str)[:500]}", step_id)

            if step_id == 'validate':
                self.stage_log('INFO', f"Pipeline summary: {self.processor.get_summary()}", step_id)
                # Phase 3.4 (data-organization spec): record a compact run
                # summary in KP# rows so /api/v1/knowledge-pipelines/{id}/runs
                # returns the pipeline's execution history. Full logs stay
                # in S3 journey-logs.
                try:
                    import asyncio as _asyncio
                    from src.services.control_plane.knowledge_pipeline_service import (
                        get_knowledge_pipeline_service,
                    )
                    summary = self.processor.get_summary() or {}
                    run_row: Dict[str, Any] = {
                        "pipelineId": "semantic_rag",
                        "journeyId": self.journey_id,
                        "jobId": self.job_id,
                        "counts": {k: summary.get(k) for k in (
                            "unified_schema", "fdw", "mapping_rules",
                            "policies", "workflows", "integrations", "embeddings",
                        ) if k in summary},
                        "success": True,
                    }
                    _asyncio.get_event_loop().create_task(
                        get_knowledge_pipeline_service().record_run("semantic_rag", run_row)
                    )
                except Exception as _kpe:
                    self.stage_log('WARNING', f"KP run persist failed: {_kpe}", step_id)

            self.upload_logs_to_s3(step_id)
            return result

        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - step_start).total_seconds()
            self.stage_log('ERROR', f"Step {step_id} failed after {elapsed:.1f}s: {str(e)}", step_id)
            import traceback
            self.stage_log('ERROR', traceback.format_exc(), step_id)
            self.upload_logs_to_s3(step_id)
            return {'status': 'failed', 'error': str(e), 'elapsed_seconds': round(elapsed, 2)}
