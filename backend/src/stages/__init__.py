"""
Stage Registry for TMF ODA Transformation System

This module provides the registry and lookup functions for all transformation stages.
"""

from typing import Dict, Type, List, Any
import importlib.util
import os
import sys
from .base_stage import BaseStage

# Dynamically import stage modules from subdirectories
def _import_stage_module(subdir: str, module_name: str):
    """Helper to import a stage module from a subdirectory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    subdir_path = os.path.join(current_dir, subdir)
    module_path = os.path.join(subdir_path, f"{module_name}.py")
    
    # Ensure the full package hierarchy is in sys.modules for relative imports
    # (e.g., from ...config imports need src, src.stages to exist)
    if "src" not in sys.modules:
        import types
        src_pkg = types.ModuleType("src")
        src_pkg.__path__ = [os.path.dirname(current_dir)]
        src_pkg.__package__ = "src"
        sys.modules["src"] = src_pkg
    
    parent_package = "src.stages"
    if parent_package not in sys.modules:
        sys.modules[parent_package] = sys.modules[__name__]
        sys.modules[parent_package].__package__ = parent_package
        if not hasattr(sys.modules[parent_package], '__path__'):
            sys.modules[parent_package].__path__ = [current_dir]
    
    # Register the sub-package (e.g., src.stages.call_process) so relative imports work
    sub_package_name = f"src.stages.{subdir.replace('-', '_')}"
    if sub_package_name not in sys.modules:
        init_path = os.path.join(subdir_path, "__init__.py")
        if os.path.exists(init_path):
            sub_spec = importlib.util.spec_from_file_location(
                sub_package_name, init_path,
                submodule_search_locations=[subdir_path]
            )
            sub_pkg = importlib.util.module_from_spec(sub_spec)
            sub_pkg.__path__ = [subdir_path]
            sub_pkg.__package__ = sub_package_name
            sys.modules[sub_package_name] = sub_pkg
        else:
            import types
            sub_pkg = types.ModuleType(sub_package_name)
            sub_pkg.__path__ = [subdir_path]
            sub_pkg.__package__ = sub_package_name
            sys.modules[sub_package_name] = sub_pkg
    
    # Load the module with proper package hierarchy
    full_module_name = f"{sub_package_name}.{module_name}"
    spec = importlib.util.spec_from_file_location(full_module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = sub_package_name
    
    # Add to sys.modules before exec to allow relative imports
    sys.modules[full_module_name] = module
    spec.loader.exec_module(module)
    return module

# Import stage classes
_raw_analysis_module = _import_stage_module('raw-analysis', 'raw_analysis')
RawAnalysisStage = _raw_analysis_module.RawAnalysisStage

_stripped_schema_module = _import_stage_module('stripped-schema', 'stripped_schema')
StrippedSchemaStage = _stripped_schema_module.StrippedSchemaStage

# Import Knowledge Processor stage
_semantic_rag_module = _import_stage_module('semantic-rag', 'semantic_rag_stage')
SemanticRagStage = _semantic_rag_module.SemanticRagStage

# Import ETL Pipeline stage
_etl_pipeline_module = _import_stage_module('etl-pipeline', 'etl_pipeline_stage')
ETLPipelineStage = _etl_pipeline_module.ETLPipelineStage

# Import stub stages for stages not yet fully implemented
class TMFMappingStage(BaseStage):
    """TMF Schema Mapping Stage (stub implementation)"""
    
    @property
    def stage_name(self) -> str:
        return "TMF Schema Mapping"
    
    @property
    def stage_description(self) -> str:
        return "Map schema elements to TMF API specifications"
    
    @property
    def steps(self) -> List[Dict]:
        return [
            {'id': 'api_matching', 'name': 'TMF API Matching', 'order': 0},
            {'id': 'attribute_mapping', 'name': 'Attribute Mapping', 'order': 1},
            {'id': 'relationship_mapping', 'name': 'Relationship Mapping', 'order': 2},
            {'id': 'coverage_analysis', 'name': 'API Coverage Analysis', 'order': 3},
            {'id': 'gap_identification', 'name': 'Gap Identification', 'order': 4}
        ]
    
    def execute_step(self, step_id: str, step_data: Dict) -> Dict:
        """Execute step (stub implementation)"""
        self.log_info(f"Executing step: {step_id}")
        self.log_info(f"Step {step_id} completed successfully")
        return {
            'status': 'completed',
            'step_id': step_id,
            'message': f'Step {step_id} completed'
        }


class MigrationPlanningStage(BaseStage):
    """Data Migration Planning Stage (stub implementation)"""
    
    @property
    def stage_name(self) -> str:
        return "Data Migration Planning"
    
    @property
    def stage_description(self) -> str:
        return "Plan data migration strategy and generate scripts"
    
    @property
    def steps(self) -> List[Dict]:
        return [
            {'id': 'strategy_planning', 'name': 'Migration Strategy Planning', 'order': 0},
            {'id': 'etl_generation', 'name': 'ETL Script Generation', 'order': 1},
            {'id': 'validation_rules', 'name': 'Data Validation Rules', 'order': 2},
            {'id': 'rollback_procedures', 'name': 'Rollback Procedures', 'order': 3}
        ]
    
    def execute_step(self, step_id: str, step_data: Dict) -> Dict:
        """Execute step (stub implementation)"""
        self.log_info(f"Executing step: {step_id}")
        self.log_info(f"Step {step_id} completed successfully")
        return {
            'status': 'completed',
            'step_id': step_id,
            'message': f'Step {step_id} completed'
        }


class DataMigrationStage(BaseStage):
    """Data Migration Stage (stub implementation)"""
    
    @property
    def stage_name(self) -> str:
        return "Data Migration"
    
    @property
    def stage_description(self) -> str:
        return "Execute data migration to TMF-compliant format"
    
    @property
    def steps(self) -> List[Dict]:
        return [
            {'id': 'dataset_selection', 'name': 'Candidate Dataset Selection', 'order': 0},
            {'id': 'data_transfer', 'name': 'Data Transfer', 'order': 1},
            {'id': 'compliance_test', 'name': 'TMF API Compliance Test', 'order': 2},
            {'id': 'mark_completion', 'name': 'Mark Completion', 'order': 3}
        ]
    
    def execute_step(self, step_id: str, step_data: Dict) -> Dict:
        """Execute step (stub implementation)"""
        self.log_info(f"Executing step: {step_id}")
        self.log_info(f"Step {step_id} completed successfully")
        return {
            'status': 'completed',
            'step_id': step_id,
            'message': f'Step {step_id} completed'
        }


class VerificationValidationStage(BaseStage):
    """Verification & Validation Stage (stub implementation)"""
    
    @property
    def stage_name(self) -> str:
        return "Verification & Validation"
    
    @property
    def stage_description(self) -> str:
        return "Validate TMF compliance and data integrity"
    
    @property
    def steps(self) -> List[Dict]:
        return [
            {'id': 'mapping_validation', 'name': 'Mapping Validation', 'order': 0},
            {'id': 'compliance_check', 'name': 'API Compliance Check', 'order': 1},
            {'id': 'integrity_verification', 'name': 'Data Integrity Verification', 'order': 2},
            {'id': 'performance_assessment', 'name': 'Performance Assessment', 'order': 3},
            {'id': 'report_generation', 'name': 'Final Report Generation', 'order': 4}
        ]
    
    def execute_step(self, step_id: str, step_data: Dict) -> Dict:
        """Execute step (stub implementation)"""
        self.log_info(f"Executing step: {step_id}")
        self.log_info(f"Step {step_id} completed successfully")
        return {
            'status': 'completed',
            'step_id': step_id,
            'message': f'Step {step_id} completed'
        }


# Stage Registry
STAGE_REGISTRY: Dict[str, Type[BaseStage]] = {
    'raw_analysis': RawAnalysisStage,
    'stripped_schema': StrippedSchemaStage,
    'tmf_mapping': TMFMappingStage,
    'migration_planning': MigrationPlanningStage,
    'data_migration': DataMigrationStage,
    'verification_validation': VerificationValidationStage,
    'semantic_rag': SemanticRagStage,
    'etl_pipeline': ETLPipelineStage,
}

try:
    from .order_to_cash.o2c_stage import OrderToCashStage
    STAGE_REGISTRY['order_to_cash'] = OrderToCashStage
except ImportError:
    pass

try:
    from .demand_forecasting.demand_forecasting_stage import DemandForecastingStage
    STAGE_REGISTRY['demand_forecasting'] = DemandForecastingStage
except ImportError:
    pass

try:
    from .inventory_optimization.inventory_optimization_stage import InventoryOptimizationStage
    STAGE_REGISTRY['inventory_optimization'] = InventoryOptimizationStage
except ImportError:
    pass

try:
    from .procurement_analytics.procurement_analytics_stage import ProcurementAnalyticsStage
    STAGE_REGISTRY['procurement_analytics'] = ProcurementAnalyticsStage
except ImportError:
    pass

try:
    from .production_quality.production_quality_stage import ProductionQualityStage
    STAGE_REGISTRY['production_quality'] = ProductionQualityStage
except ImportError:
    pass

try:
    from .supply_chain_risk.supply_chain_risk_stage import SupplyChainRiskStage
    STAGE_REGISTRY['supply_chain_risk'] = SupplyChainRiskStage
except ImportError:
    pass

try:
    from .customer_360.customer_360_stage import Customer360Stage
    STAGE_REGISTRY['customer_360'] = Customer360Stage
except ImportError:
    pass

try:
    from .esg_sustainability.esg_sustainability_stage import ESGSustainabilityStage
    STAGE_REGISTRY['esg_sustainability'] = ESGSustainabilityStage
except ImportError:
    pass

try:
    from .dynamic_tool_stage import DynamicToolStage
    STAGE_REGISTRY['dynamic_tool'] = DynamicToolStage
except ImportError:
    pass

# Four-Views journey stages: <solution>_predictive / _action_loop / _history
# (Section 3.3 of the Solution Four Views Expansion plan.)
try:
    from .four_views.four_views_stage import (
        PredictiveStage as _FV_PredictiveStage,
        ActionLoopStage as _FV_ActionLoopStage,
        HistorianStage as _FV_HistorianStage,
    )
    _FV_APPS = {
        "order_to_cash": "order-to-cash",
        "demand_forecasting": "demand-forecasting",
        "inventory_optimization": "inventory-optimization",
        "procurement_analytics": "procurement-analytics",
        "production_quality": "production-quality",
        "supply_chain_risk": "supply-chain-risk",
        "customer_360": "customer-360",
        "esg_sustainability": "esg-sustainability",
    }
    for _stage_prefix, _app_id in _FV_APPS.items():
        STAGE_REGISTRY[f"{_stage_prefix}_predictive"] = _FV_PredictiveStage
        STAGE_REGISTRY[f"{_stage_prefix}_action_loop"] = _FV_ActionLoopStage
        STAGE_REGISTRY[f"{_stage_prefix}_history"] = _FV_HistorianStage
except ImportError:
    pass


def get_stage_class(stage_id: str) -> Type[BaseStage]:
    """
    Get the stage class for a given stage ID.
    
    Args:
        stage_id: The stage identifier
        
    Returns:
        The stage class
        
    Raises:
        ValueError: If the stage ID is not recognized
    """
    if stage_id not in STAGE_REGISTRY:
        try:
            from .plugin_journey_stage import PluginJourneyStage
            from ..services.plugins.plugin_service import PluginService
            return PluginJourneyStage
        except ImportError:
            pass
        raise ValueError(
            f"Unknown stage ID: {stage_id}. "
            f"Available stages: {', '.join(STAGE_REGISTRY.keys())}"
        )
    
    return STAGE_REGISTRY[stage_id]


def list_available_stages() -> List[str]:
    """
    List all available stage IDs.
    
    Returns:
        List of stage IDs
    """
    return list(STAGE_REGISTRY.keys())


def register_stage(stage_id: str, stage_class: Type[BaseStage]) -> None:
    """
    Register a new stage class.
    
    Args:
        stage_id: The stage identifier
        stage_class: The stage class (must inherit from BaseStage)
        
    Raises:
        TypeError: If stage_class doesn't inherit from BaseStage
    """
    if not issubclass(stage_class, BaseStage):
        raise TypeError(f"Stage class must inherit from BaseStage")
    
    STAGE_REGISTRY[stage_id] = stage_class


# Export public API
__all__ = [
    'BaseStage',
    'RawAnalysisStage',
    'StrippedSchemaStage',
    'SemanticRagStage',
    'ETLPipelineStage',
    'TMFMappingStage',
    'MigrationPlanningStage',
    'DataMigrationStage',
    'VerificationValidationStage',
    'get_stage_class',
    'list_available_stages',
    'register_stage',
    'STAGE_REGISTRY',
]

