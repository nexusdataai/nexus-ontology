"""
Tests for Journey Management Pydantic Models

Comprehensive tests for all Pydantic models used in journey management.
Tests validation, serialization, deserialization, and edge cases.
"""

import pytest
from pydantic import ValidationError
from src.models.journey_model import (
    JourneyAction,
    JourneyStatus,
    Priority,
    RuleType,
    RuleScope,
    RuleStatus,
    StageId,
    JobStatus,
    JourneyData,
    StageData,
    StageDefinition,
    RuleData,
    JobStatusUpdate,
    JourneyActionRequest,
    JourneyResponse,
    JourneyListResponse,
    JourneySummary,
    JobMetrics,
    convert_to_journey_data,
    convert_to_stage_data,
    convert_to_rule_data,
)


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Test enum definitions"""
    
    def test_journey_action_enum(self):
        """Test JourneyAction enum values"""
        assert JourneyAction.CREATE.value == "create"
        assert JourneyAction.LIST.value == "list"
        assert JourneyAction.LIST_STAGES.value == "list_stages"
        assert JourneyAction.ADD_RULE.value == "add_rule"
        
    def test_journey_status_enum(self):
        """Test JourneyStatus enum values"""
        assert JourneyStatus.PENDING.value == "pending"
        assert JourneyStatus.RUNNING.value == "running"
        assert JourneyStatus.COMPLETED.value == "completed"
        
    def test_priority_enum(self):
        """Test Priority enum values"""
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"
        assert Priority.CRITICAL.value == "critical"
    
    def test_rule_type_enum(self):
        """Test RuleType enum values"""
        assert RuleType.FIELD_MAPPING.value == "field_mapping"
        assert RuleType.VALIDATION_RULES.value == "validation_rules"
    
    def test_stage_id_enum(self):
        """Test StageId enum values"""
        assert StageId.RAW_ANALYSIS.value == "raw_analysis"
        assert StageId.STRIPPED_SCHEMA.value == "stripped_schema"


# =============================================================================
# DATA MODEL TESTS
# =============================================================================

class TestStageDefinition:
    """Test StageDefinition model (used for journey creation with stages)"""
    
    def test_stage_definition_minimal(self):
        """Test creating StageDefinition with minimal required fields"""
        stage = StageDefinition(stageId="test_stage", name="Test Stage", order=1)
        assert stage.stageId == "test_stage"
        assert stage.name == "Test Stage"
        assert stage.order == 1
        assert stage.secondBrainEnabled is True
        assert stage.status == "pending"
    
    def test_stage_definition_full(self):
        """Test creating StageDefinition with all fields"""
        stage = StageDefinition(
            stageId="call_process",
            name="Call Processing",
            description="Process WXCC calls",
            order=1,
            secondBrainEnabled=False,
            estimatedDuration="1h",
            status="active",
            steps=[{"step": "fetch"}, {"step": "transcribe"}],
            dependencies=["raw_analysis"],
            config={"minutes_back": 60, "transcribe": True},
            metadata={"source": "wxcc"}
        )
        assert stage.stageId == "call_process"
        assert stage.description == "Process WXCC calls"
        assert stage.secondBrainEnabled is False
        assert len(stage.steps) == 2
        assert stage.config["minutes_back"] == 60
    
    def test_stage_definition_missing_required(self):
        """Test validation error when required fields missing"""
        with pytest.raises(ValidationError):
            StageDefinition(name="Test")  # Missing stageId
        
        with pytest.raises(ValidationError):
            StageDefinition(stageId="test")  # Missing name


class TestJourneyData:
    """Test JourneyData model"""
    
    def test_journey_data_creation_minimal(self):
        """Test creating JourneyData with minimal required fields"""
        data = JourneyData(
            name="Test Journey",
            odaComponentType="PRODUCTCATALOG"
        )
        assert data.name == "Test Journey"
        assert data.odaComponentType == "PRODUCTCATALOG"
        assert data.priority == Priority.MEDIUM
        assert data.status == JourneyStatus.PENDING
        assert data.createdBy == "system"
        
    def test_journey_data_creation_full(self):
        """Test creating JourneyData with all fields"""
        data = JourneyData(
            name="Test Journey",
            description="Test description",
            odaComponentType="PRODUCTCATALOG",
            priority=Priority.HIGH,
            status=JourneyStatus.RUNNING,
            createdBy="user123",
            tags=["test", "demo"],
            metadata={"key": "value"}
        )
        assert data.name == "Test Journey"
        assert data.description == "Test description"
        assert data.priority == Priority.HIGH
        assert data.status == JourneyStatus.RUNNING
        assert data.createdBy == "user123"
        assert len(data.tags) == 2
        assert data.metadata["key"] == "value"
    
    def test_journey_data_missing_required(self):
        """Test validation error when required fields missing"""
        with pytest.raises(ValidationError) as exc_info:
            JourneyData(name="Test")  # Missing odaComponentType
        assert "odaComponentType" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            JourneyData(odaComponentType="PRODUCTCATALOG")  # Missing name
        assert "name" in str(exc_info.value)
    
    def test_journey_data_serialization(self):
        """Test JourneyData serialization"""
        data = JourneyData(
            name="Test Journey",
            odaComponentType="PRODUCTCATALOG",
            priority=Priority.HIGH
        )
        data_dict = data.model_dump()
        assert data_dict["name"] == "Test Journey"
        assert data_dict["priority"] == "high"  # Enum value
        assert data_dict["status"] == "pending"
    
    def test_journey_data_with_stages(self):
        """Test JourneyData with stages field"""
        stage = StageDefinition(
            stageId="call_process",
            name="Call Processing",
            order=1
        )
        data = JourneyData(
            name="Test Journey",
            odaComponentType="CALLCENTER",
            stages=[stage]
        )
        assert data.stages is not None
        assert len(data.stages) == 1
        assert data.stages[0].stageId == "call_process"
    
    def test_journey_data_with_multiple_stages(self):
        """Test JourneyData with multiple stages"""
        stages = [
            StageDefinition(stageId="raw_analysis", name="Raw Analysis", order=1),
            StageDefinition(stageId="data_migration", name="Data Migration", order=2),
        ]
        data = JourneyData(
            name="Multi-Stage Journey",
            odaComponentType="customer-management",
            stages=stages
        )
        assert len(data.stages) == 2
        assert data.stages[0].order == 1
        assert data.stages[1].order == 2


class TestStageData:
    """Test StageData model"""
    
    def test_stage_data_creation_minimal(self):
        """Test creating StageData with minimal required fields"""
        data = StageData(
            stageId="raw_analysis",
            name="Raw Analysis",
            order=1
        )
        assert data.stageId == "raw_analysis"
        assert data.name == "Raw Analysis"
        assert data.order == 1
        assert data.secondBrainEnabled is True
        assert data.estimatedDuration == "30m"
        
    def test_stage_data_creation_full(self):
        """Test creating StageData with all fields"""
        data = StageData(
            stageId="raw_analysis",
            name="Raw Analysis",
            description="Analyze raw data",
            order=1,
            secondBrainEnabled=False,
            estimatedDuration="45m",
            status="running",
            steps=[{"id": "step1", "name": "Step 1"}],
            dependencies=["stage0"],
            metadata={"key": "value"}
        )
        assert data.stageId == "raw_analysis"
        assert data.secondBrainEnabled is False
        assert data.estimatedDuration == "45m"
        assert len(data.steps) == 1
        assert len(data.dependencies) == 1
    
    def test_stage_data_missing_required(self):
        """Test validation error when required fields missing"""
        with pytest.raises(ValidationError) as exc_info:
            StageData(stageId="raw_analysis", name="Test")  # Missing order
        assert "order" in str(exc_info.value)


class TestRuleData:
    """Test RuleData model"""
    
    def test_rule_data_creation_minimal(self):
        """Test creating RuleData with minimal required fields"""
        data = RuleData(
            title="Test Rule",
            description="Test description",
            type=RuleType.FIELD_MAPPING,
            context="Test context",
            content="Test content"
        )
        assert data.title == "Test Rule"
        assert data.description == "Test description"
        assert data.type == RuleType.FIELD_MAPPING
        assert data.context == "Test context"
        assert data.content == "Test content"
        assert data.priority == Priority.MEDIUM
        assert data.scope == RuleScope.STAGE
        assert data.status == RuleStatus.ACTIVE
        
    def test_rule_data_creation_full(self):
        """Test creating RuleData with all fields"""
        data = RuleData(
            title="Test Rule",
            description="Test description",
            type=RuleType.VALIDATION_RULES,
            priority=Priority.HIGH,
            scope=RuleScope.GLOBAL,
            status=RuleStatus.ACTIVE,
            context="Test context",
            content="Rule content",
            conditions={"condition": "value"},
            actions={"action": "do_something"},
            examples=[{"example": "test"}],
            metadata={"key": "value"}
        )
        assert data.title == "Test Rule"
        assert data.description == "Test description"
        assert data.type == RuleType.VALIDATION_RULES
        assert data.context == "Test context"
        assert data.content == "Rule content"
        assert data.priority == Priority.HIGH
        assert data.scope == RuleScope.GLOBAL
        assert len(data.examples) == 1
    
    def test_rule_data_missing_required(self):
        """Test validation error when required fields missing"""
        with pytest.raises(ValidationError) as exc_info:
            RuleData(title="Test")  # Missing type, description, context, content
        assert "type" in str(exc_info.value) or "description" in str(exc_info.value)


class TestJobStatusUpdate:
    """Test JobStatusUpdate model"""
    
    def test_job_status_update_minimal(self):
        """Test creating JobStatusUpdate with minimal fields"""
        data = JobStatusUpdate(status=JobStatus.RUNNING)
        assert data.status == JobStatus.RUNNING
        assert data.progress is None
        
    def test_job_status_update_full(self):
        """Test creating JobStatusUpdate with all fields"""
        data = JobStatusUpdate(
            status=JobStatus.RUNNING,
            progress=50,
            current_step="processing",
            error_message=None
        )
        assert data.status == JobStatus.RUNNING
        assert data.progress == 50
        assert data.current_step == "processing"
    
    def test_job_status_update_progress_validation(self):
        """Test progress percentage validation"""
        # Valid progress
        data = JobStatusUpdate(status=JobStatus.RUNNING, progress=0)
        assert data.progress == 0
        
        data = JobStatusUpdate(status=JobStatus.RUNNING, progress=100)
        assert data.progress == 100
        
        # Invalid progress - too low
        with pytest.raises(ValidationError):
            JobStatusUpdate(status=JobStatus.RUNNING, progress=-1)
        
        # Invalid progress - too high
        with pytest.raises(ValidationError):
            JobStatusUpdate(status=JobStatus.RUNNING, progress=101)


# =============================================================================
# REQUEST MODEL TESTS
# =============================================================================

class TestJourneyActionRequest:
    """Test JourneyActionRequest model and validation"""
    
    # Test CREATE action
    def test_create_action_with_journey_data_and_stages(self):
        """Test CREATE action with journey_data including stages"""
        request = JourneyActionRequest(
            action=JourneyAction.CREATE,
            journey_data={
                "name": "Test Journey",
                "odaComponentType": "PRODUCTCATALOG",
                "stages": [
                    {"stageId": "test_stage", "name": "Test Stage", "order": 1}
                ]
            }
        )
        assert request.action == JourneyAction.CREATE
        assert request.journey_data is not None
        assert request.journey_data["stages"] is not None
        assert len(request.journey_data["stages"]) == 1
    
    def test_create_action_requires_stages(self):
        """Test CREATE action validation when stages are missing"""
        with pytest.raises(ValidationError) as exc_info:
            JourneyActionRequest(
                action=JourneyAction.CREATE,
                journey_data={
                    "name": "Test Journey",
                    "odaComponentType": "PRODUCTCATALOG"
                    # No stages provided
                }
            )
        assert "stage" in str(exc_info.value).lower()
    
    def test_create_action_requires_at_least_one_stage(self):
        """Test CREATE action validation when stages is empty list"""
        with pytest.raises(ValidationError) as exc_info:
            JourneyActionRequest(
                action=JourneyAction.CREATE,
                journey_data={
                    "name": "Test Journey",
                    "odaComponentType": "PRODUCTCATALOG",
                    "stages": []  # Empty stages
                }
            )
        assert "stage" in str(exc_info.value).lower()
    
    def test_create_action_with_multiple_stages(self):
        """Test CREATE action with multiple stages"""
        request = JourneyActionRequest(
            action=JourneyAction.CREATE,
            journey_data={
                "name": "Multi-Stage Journey",
                "odaComponentType": "customer-management",
                "stages": [
                    {"stageId": "raw_analysis", "name": "Raw Analysis", "order": 1},
                    {"stageId": "data_migration", "name": "Data Migration", "order": 2}
                ]
            }
        )
        assert len(request.journey_data["stages"]) == 2
    
    def test_create_action_missing_required_data(self):
        """Test CREATE action validation when data is missing"""
        with pytest.raises(ValidationError) as exc_info:
            JourneyActionRequest(action=JourneyAction.CREATE)
        assert "journey_data" in str(exc_info.value) or "name" in str(exc_info.value) or "stage" in str(exc_info.value).lower()
    
    # Test READ action
    def test_read_action_valid(self):
        """Test READ action with journey_id"""
        request = JourneyActionRequest(
            action=JourneyAction.READ,
            journey_id="JRN-123"
        )
        assert request.action == JourneyAction.READ
        assert request.journey_id == "JRN-123"
    
    def test_read_action_missing_journey_id(self):
        """Test READ action validation when journey_id is missing"""
        with pytest.raises(ValidationError) as exc_info:
            JourneyActionRequest(action=JourneyAction.READ)
        assert "journey_id" in str(exc_info.value)
    
    # Test LIST action
    def test_list_action_valid(self):
        """Test LIST action with optional filters"""
        request = JourneyActionRequest(
            action=JourneyAction.LIST,
            status_filter="pending",
            component_type_filter="PRODUCTCATALOG"
        )
        assert request.action == JourneyAction.LIST
        assert request.status_filter == "pending"
        assert request.component_type_filter == "PRODUCTCATALOG"
    
    def test_list_action_no_filters(self):
        """Test LIST action without filters"""
        request = JourneyActionRequest(action=JourneyAction.LIST)
        assert request.action == JourneyAction.LIST
        assert request.status_filter is None
    
    # Test UPDATE action
    def test_update_action_valid(self):
        """Test UPDATE action with journey_id and data"""
        request = JourneyActionRequest(
            action=JourneyAction.UPDATE,
            journey_id="JRN-123",
            journey_data={"status": "running"}
        )
        assert request.action == JourneyAction.UPDATE
        assert request.journey_id == "JRN-123"
    
    def test_update_action_missing_journey_id(self):
        """Test UPDATE action validation when journey_id is missing"""
        with pytest.raises(ValidationError):
            JourneyActionRequest(
                action=JourneyAction.UPDATE,
                journey_data={"status": "running"}
            )
    
    # Test DELETE action
    def test_delete_action_valid(self):
        """Test DELETE action with journey_id"""
        request = JourneyActionRequest(
            action=JourneyAction.DELETE,
            journey_id="JRN-123",
            confirm=True
        )
        assert request.action == JourneyAction.DELETE
        assert request.journey_id == "JRN-123"
        assert request.confirm is True
    
    def test_delete_action_missing_journey_id(self):
        """Test DELETE action validation when journey_id is missing"""
        with pytest.raises(ValidationError):
            JourneyActionRequest(action=JourneyAction.DELETE)
    
    # Test STAGE actions
    def test_list_stages_valid(self):
        """Test LIST_STAGES action"""
        request = JourneyActionRequest(
            action=JourneyAction.LIST_STAGES,
            journey_id="JRN-123"
        )
        assert request.action == JourneyAction.LIST_STAGES
        assert request.journey_id == "JRN-123"
    
    def test_add_stage_valid(self):
        """Test ADD_STAGE action with stage_data"""
        request = JourneyActionRequest(
            action=JourneyAction.ADD_STAGE,
            journey_id="JRN-123",
            stage_data={
                "stageId": "raw_analysis",
                "name": "Raw Analysis",
                "order": 1
            }
        )
        assert request.action == JourneyAction.ADD_STAGE
        assert request.journey_id == "JRN-123"
        assert request.stage_data is not None
    
    def test_add_stage_missing_stage_data(self):
        """Test ADD_STAGE validation when stage_data is missing"""
        with pytest.raises(ValidationError):
            JourneyActionRequest(
                action=JourneyAction.ADD_STAGE,
                journey_id="JRN-123"
            )
    
    def test_update_stage_valid(self):
        """Test UPDATE_STAGE action"""
        request = JourneyActionRequest(
            action=JourneyAction.UPDATE_STAGE,
            journey_id="JRN-123",
            stage_id="raw_analysis",
            stage_data={"status": "completed"}
        )
        assert request.action == JourneyAction.UPDATE_STAGE
        assert request.stage_id == "raw_analysis"
    
    def test_update_stage_missing_stage_id(self):
        """Test UPDATE_STAGE validation when stage_id is missing"""
        with pytest.raises(ValidationError):
            JourneyActionRequest(
                action=JourneyAction.UPDATE_STAGE,
                journey_id="JRN-123",
                stage_data={"status": "completed"}
            )
    
    def test_delete_stage_valid(self):
        """Test DELETE_STAGE action"""
        request = JourneyActionRequest(
            action=JourneyAction.DELETE_STAGE,
            journey_id="JRN-123",
            stage_id="raw_analysis"
        )
        assert request.action == JourneyAction.DELETE_STAGE
        assert request.stage_id == "raw_analysis"
    
    def test_add_default_stages_valid(self):
        """Test ADD_DEFAULT_STAGES action"""
        request = JourneyActionRequest(
            action=JourneyAction.ADD_DEFAULT_STAGES,
            journey_id="JRN-123"
        )
        assert request.action == JourneyAction.ADD_DEFAULT_STAGES
    
    # Test RULE actions
    def test_list_rules_valid(self):
        """Test LIST_RULES action"""
        request = JourneyActionRequest(
            action=JourneyAction.LIST_RULES,
            journey_id="JRN-123",
            stage_id="raw_analysis",
            rule_type=RuleType.FIELD_MAPPING
        )
        assert request.action == JourneyAction.LIST_RULES
        assert request.journey_id == "JRN-123"
        assert request.stage_id == "raw_analysis"
    
    def test_add_rule_valid(self):
        """Test ADD_RULE action with rule_data"""
        request = JourneyActionRequest(
            action=JourneyAction.ADD_RULE,
            journey_id="JRN-123",
            stage_id="raw_analysis",
            rule_data={
                "title": "Test Rule",
                "description": "Test description",
                "type": "field_mapping",
                "context": "Test context",
                "content": "Test content"
            }
        )
        assert request.action == JourneyAction.ADD_RULE
        assert request.stage_id == "raw_analysis"
        assert request.rule_data is not None
    
    def test_add_rule_missing_stage_id(self):
        """Test ADD_RULE validation when stage_id is missing"""
        with pytest.raises(ValidationError):
            JourneyActionRequest(
                action=JourneyAction.ADD_RULE,
                journey_id="JRN-123",
                rule_data={
                    "title": "Test Rule",
                    "description": "Test",
                    "type": "field_mapping",
                    "context": "Test",
                    "content": "Test"
                }
            )
    
    def test_update_rule_valid(self):
        """Test UPDATE_RULE action"""
        request = JourneyActionRequest(
            action=JourneyAction.UPDATE_RULE,
            journey_id="JRN-123",
            stage_id="raw_analysis",
            rule_id="RULE-123",
            rule_data={"status": "inactive"}
        )
        assert request.action == JourneyAction.UPDATE_RULE
        assert request.rule_id == "RULE-123"
    
    def test_update_rule_missing_rule_id(self):
        """Test UPDATE_RULE validation when rule_id is missing"""
        with pytest.raises(ValidationError):
            JourneyActionRequest(
                action=JourneyAction.UPDATE_RULE,
                journey_id="JRN-123",
                stage_id="raw_analysis",
                rule_data={"status": "inactive"}
            )
    
    def test_delete_rule_valid(self):
        """Test DELETE_RULE action"""
        request = JourneyActionRequest(
            action=JourneyAction.DELETE_RULE,
            journey_id="JRN-123",
            stage_id="raw_analysis",
            rule_id="RULE-123"
        )
        assert request.action == JourneyAction.DELETE_RULE
        assert request.rule_id == "RULE-123"
    
    # Test JOB actions
    def test_update_job_status_valid(self):
        """Test UPDATE_JOB_STATUS action"""
        request = JourneyActionRequest(
            action=JourneyAction.UPDATE_JOB_STATUS,
            journey_id="JRN-123",
            job_id="JOB-456",
            job_status=JobStatus.RUNNING,
            progress=50
        )
        assert request.action == JourneyAction.UPDATE_JOB_STATUS
        assert request.job_id == "JOB-456"
        assert request.job_status == JobStatus.RUNNING
        assert request.progress == 50
    
    def test_update_job_status_missing_job_status(self):
        """Test UPDATE_JOB_STATUS validation when job_status is missing"""
        with pytest.raises(ValidationError):
            JourneyActionRequest(
                action=JourneyAction.UPDATE_JOB_STATUS,
                journey_id="JRN-123",
                job_id="JOB-456"
            )
    
    def test_get_job_metrics_valid(self):
        """Test GET_JOB_METRICS action"""
        request = JourneyActionRequest(
            action=JourneyAction.GET_JOB_METRICS,
            journey_id="JRN-123",
            job_id="JOB-456"
        )
        assert request.action == JourneyAction.GET_JOB_METRICS
        assert request.job_id == "JOB-456"
    
    def test_batch_cancel_jobs_valid(self):
        """Test BATCH_CANCEL_JOBS action"""
        request = JourneyActionRequest(
            action=JourneyAction.BATCH_CANCEL_JOBS,
            journey_id="JRN-123",
            job_ids=["JOB-1", "JOB-2", "JOB-3"],
            reason="Test cancellation"
        )
        assert request.action == JourneyAction.BATCH_CANCEL_JOBS
        assert len(request.job_ids) == 3
        assert request.reason == "Test cancellation"
    
    def test_batch_cancel_jobs_missing_job_ids(self):
        """Test BATCH_CANCEL_JOBS validation when job_ids is missing"""
        with pytest.raises(ValidationError):
            JourneyActionRequest(
                action=JourneyAction.BATCH_CANCEL_JOBS,
                journey_id="JRN-123"
            )
    
    # Test IMPORT/EXPORT actions
    def test_export_complete_valid(self):
        """Test EXPORT_COMPLETE action"""
        request = JourneyActionRequest(
            action=JourneyAction.EXPORT_COMPLETE,
            journey_id="JRN-123",
            output_file="/path/to/export.json"
        )
        assert request.action == JourneyAction.EXPORT_COMPLETE
        assert request.output_file == "/path/to/export.json"
    
    def test_export_complete_missing_output_file(self):
        """Test EXPORT_COMPLETE validation when output_file is missing"""
        with pytest.raises(ValidationError):
            JourneyActionRequest(
                action=JourneyAction.EXPORT_COMPLETE,
                journey_id="JRN-123"
            )
    
    def test_import_complete_valid(self):
        """Test IMPORT_COMPLETE action"""
        request = JourneyActionRequest(
            action=JourneyAction.IMPORT_COMPLETE,
            input_file="/path/to/import.json",
            new_journey_id="JRN-NEW"
        )
        assert request.action == JourneyAction.IMPORT_COMPLETE
        assert request.input_file == "/path/to/import.json"
        assert request.new_journey_id == "JRN-NEW"
    
    def test_import_complete_missing_input_file(self):
        """Test IMPORT_COMPLETE validation when input_file is missing"""
        with pytest.raises(ValidationError):
            JourneyActionRequest(action=JourneyAction.IMPORT_COMPLETE)


# =============================================================================
# RESPONSE MODEL TESTS
# =============================================================================

class TestJourneyResponse:
    """Test JourneyResponse model"""
    
    def test_journey_response_success(self):
        """Test successful JourneyResponse"""
        response = JourneyResponse(
            status="success",
            message="Operation completed successfully",
            operation="create_journey",
            journey_id="JRN-123",
            data={"key": "value"}
        )
        assert response.status == "success"
        assert response.message == "Operation completed successfully"
        assert response.journey_id == "JRN-123"
        assert response.error is None
    
    def test_journey_response_error(self):
        """Test error JourneyResponse"""
        response = JourneyResponse(
            status="error",
            message="Operation failed",
            operation="create_journey",
            error="Invalid parameter"
        )
        assert response.status == "error"
        assert response.error == "Invalid parameter"
    
    def test_journey_response_serialization(self):
        """Test JourneyResponse serialization"""
        response = JourneyResponse(
            status="success",
            message="Test",
            operation="test",
            data={"nested": {"key": "value"}}
        )
        response_dict = response.model_dump()
        assert response_dict["status"] == "success"
        assert "data" in response_dict


class TestJourneyListResponse:
    """Test JourneyListResponse model"""
    
    def test_list_response_creation(self):
        """Test creating list response"""
        response = JourneyListResponse(
            status="success",
            message="Found 2 journeys",
            total_count=2,
            items=[
                {"journeyId": "JRN-1", "name": "Journey 1"},
                {"journeyId": "JRN-2", "name": "Journey 2"}
            ]
        )
        assert response.status == "success"
        assert response.total_count == 2
        assert len(response.items) == 2


class TestJourneySummary:
    """Test JourneySummary model"""
    
    def test_journey_summary_creation(self):
        """Test creating journey summary"""
        summary = JourneySummary(
            journey_id="JRN-123",
            name="Test Journey",
            status="running",
            priority="high",
            odaComponentType="PRODUCTCATALOG",
            overallProgress=50,
            totalStages=6,
            totalRules=10,
            activeRules=8
        )
        assert summary.journey_id == "JRN-123"
        assert summary.overallProgress == 50
        assert summary.totalStages == 6


class TestJobMetrics:
    """Test JobMetrics model"""
    
    def test_job_metrics_creation(self):
        """Test creating job metrics"""
        metrics = JobMetrics(
            job_id="JOB-456",
            stage_id="raw_analysis",
            status="completed",
            progress=100,
            duration=120.5,
            totalLogs=150,
            errorCount=2,
            warningCount=5,
            infoCount=143
        )
        assert metrics.job_id == "JOB-456"
        assert metrics.duration == 120.5
        assert metrics.errorCount == 2


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestHelperFunctions:
    """Test helper functions"""
    
    def test_convert_to_journey_data_from_model(self):
        """Test converting JourneyData model to dict"""
        journey_data = JourneyData(
            name="Test",
            odaComponentType="PRODUCTCATALOG"
        )
        result = convert_to_journey_data(journey_data)
        assert isinstance(result, dict)
        assert result["name"] == "Test"
    
    def test_convert_to_journey_data_from_dict(self):
        """Test converting dict to dict (passthrough)"""
        data_dict = {"name": "Test", "odaComponentType": "PRODUCTCATALOG"}
        result = convert_to_journey_data(data_dict)
        assert result == data_dict
    
    def test_convert_to_stage_data_from_model(self):
        """Test converting StageData model to dict"""
        stage_data = StageData(
            stageId="raw_analysis",
            name="Raw Analysis",
            order=1
        )
        result = convert_to_stage_data(stage_data)
        assert isinstance(result, dict)
        assert result["stageId"] == "raw_analysis"
    
    def test_convert_to_rule_data_from_model(self):
        """Test converting RuleData model to dict"""
        rule_data = RuleData(
            title="Test Rule",
            description="Test description",
            type=RuleType.FIELD_MAPPING,
            context="Test context",
            content="Test content"
        )
        result = convert_to_rule_data(rule_data)
        assert isinstance(result, dict)
        assert result["title"] == "Test Rule"


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_string_fields(self):
        """Test handling of empty string fields - Pydantic V2 allows empty strings by default"""
        # Pydantic V2 allows empty strings unless explicitly constrained
        # This test verifies that empty strings are accepted
        data = JourneyData(name="", odaComponentType="PRODUCTCATALOG")
        assert data.name == ""
    
    def test_null_optional_fields(self):
        """Test that optional fields can be None"""
        request = JourneyActionRequest(
            action=JourneyAction.LIST,
            status_filter=None,
            component_type_filter=None
        )
        assert request.status_filter is None
        assert request.component_type_filter is None
    
    def test_very_long_strings(self):
        """Test handling of very long strings"""
        long_name = "A" * 10000
        data = JourneyData(
            name=long_name,
            odaComponentType="PRODUCTCATALOG"
        )
        assert len(data.name) == 10000
    
    def test_special_characters_in_strings(self):
        """Test handling of special characters"""
        data = JourneyData(
            name="Test 🎯 Journey!@#$%^&*()",
            description="Special chars: <>&\"'",
            odaComponentType="PRODUCTCATALOG"
        )
        assert "🎯" in data.name
        assert "<>&" in data.description
    
    def test_nested_dict_structures(self):
        """Test deeply nested dictionary structures"""
        stage_data = StageData(
            stageId="test",
            name="Test",
            order=1,
            metadata={
                "level1": {
                    "level2": {
                        "level3": {
                            "key": "value"
                        }
                    }
                }
            }
        )
        assert stage_data.metadata["level1"]["level2"]["level3"]["key"] == "value"
    
    def test_empty_lists(self):
        """Test handling of empty lists"""
        data = JourneyData(
            name="Test",
            odaComponentType="PRODUCTCATALOG",
            tags=[]
        )
        assert data.tags == []
        assert isinstance(data.tags, list)
    
    def test_large_numbers(self):
        """Test handling of large numbers"""
        data = StageData(
            stageId="test",
            name="Test",
            order=999999
        )
        assert data.order == 999999


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

