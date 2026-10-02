"""
Journey test fixtures

Provides reusable test data for journey, stage, and rule operations.
"""

from typing import Dict, Any
import pytest


@pytest.fixture
def basic_journey_data() -> Dict[str, Any]:
    """
    Basic journey data with required fields only.
    Uses snake_case field naming to match current implementation.
    Note: stages are required for journey creation.
    """
    return {
        "journey_data": {
            "name": "Test Journey Basic",
            "description": "Basic test journey for integration tests",
            "odaComponentType": "product-catalog",
            "stages": [
                {"stageId": "test_stage", "name": "Test Stage", "order": 1}
            ]
        }
    }


@pytest.fixture
def journey_with_stages_data() -> Dict[str, Any]:
    """
    Journey data with custom stages included.
    """
    return {
        "journey_data": {
            "name": "Test Journey With Stages",
            "description": "Journey with custom stages",
            "odaComponentType": "customer-management",
            "priority": "high",
            "stages": [
                {
                    "stageId": "custom_stage_1",
                    "name": "Custom Analysis Stage",
                    "description": "Custom stage for testing",
                    "order": 1,
                    "secondBrainEnabled": True,
                    "estimatedDuration": "20m",
                    "status": "pending"
                },
                {
                    "stageId": "custom_stage_2",
                    "name": "Custom Processing Stage",
                    "description": "Second custom stage",
                    "order": 2
                }
            ]
        }
    }


@pytest.fixture
def journey_with_rules_data() -> Dict[str, Any]:
    """
    Journey data with Second Brain rules included.
    """
    return {
        "journey_data": {
            "name": "Test Journey With Rules",
            "description": "Journey with Second Brain rules",
            "odaComponentType": "service-catalog",
            "priority": "medium",
            "stages": [
                {"stageId": "rules_stage", "name": "Rules Stage", "order": 1}
            ]
        }
    }


@pytest.fixture
def stage_data_fixture() -> Dict[str, Any]:
    """
    Stage data for testing stage operations.
    """
    return {
        "stage_id": "test_stage",
        "name": "Test Stage",
        "description": "Stage for integration testing",
        "order": 99,
        "second_brain_enabled": True,
        "estimated_duration": "15m",
        "status": "pending",
        "steps": [
            {
                "id": "test_step_1",
                "name": "Test Step 1",
                "description": "First test step",
                "order": 0,
                "estimated_duration": "5m",
                "ai_assisted": True
            },
            {
                "id": "test_step_2",
                "name": "Test Step 2",
                "description": "Second test step",
                "order": 1,
                "estimated_duration": "10m",
                "ai_assisted": False
            }
        ]
    }


@pytest.fixture
def rule_data_fixture() -> Dict[str, Any]:
    """
    Rule data for testing Second Brain rule operations.
    """
    return {
        "title": "Test Rule",
        "type": "field_mapping",
        "priority": "high",
        "scope": "global",
        "status": "active",
        "content": {
            "natural_language": "Test rule for integration testing",
            "json_rule": {
                "conditions": {
                    "table_patterns": ["*test_table*"]
                },
                "actions": {
                    "map_to": "TEST_ENTITY"
                }
            }
        }
    }


@pytest.fixture
def job_execution_data() -> Dict[str, Any]:
    """
    Job execution data for testing run_job operations.
    """
    return {
        "triggered_by": "integration_test",
        "reason": "Testing job execution"
    }


@pytest.fixture
def comprehensive_journey_data() -> Dict[str, Any]:
    """
    Comprehensive journey data with all optional fields.
    """
    return {
        "journey_data": {
            "name": "Comprehensive Test Journey",
            "description": "Journey with all fields populated",
            "odaComponentType": "resource-catalog",
            "priority": "critical",
            "status": "pending",
            "createdBy": "test_user",
            "tags": ["test", "integration", "comprehensive"],
            "metadata": {
                "test_type": "integration",
                "environment": "test"
            },
            "stages": [
                {"stageId": "analysis", "name": "Analysis", "order": 1},
                {"stageId": "processing", "name": "Processing", "order": 2},
                {"stageId": "validation", "name": "Validation", "order": 3}
            ]
        }
    }


# Non-fixture helper functions

def create_minimal_journey_payload(name: str = None) -> Dict[str, Any]:
    """
    Create minimal journey payload for quick tests.
    Note: stages are required for journey creation.
    
    Args:
        name: Journey name (generates unique name if not provided)
        
    Returns:
        Dictionary with minimal journey data including required stages
    """
    import time
    if name is None:
        name = f"Test Journey {int(time.time())}"
    
    return {
        "journey_data": {
            "name": name,
            "odaComponentType": "product-catalog",
            "stages": [
                {"stageId": "default_stage", "name": "Default Stage", "order": 1}
            ]
        }
    }


def create_stage_payload(stage_id: str, order: int = 0) -> Dict[str, Any]:
    """
    Create stage payload for testing.
    
    Args:
        stage_id: Stage identifier
        order: Stage order in sequence
        
    Returns:
        Dictionary with stage data
    """
    return {
        "stage_id": stage_id,
        "name": f"Stage {stage_id}",
        "description": f"Test stage {stage_id}",
        "order": order,
        "second_brain_enabled": True,
        "estimated_duration": "10m",
        "status": "pending"
    }


def create_rule_payload(
    title: str,
    rule_type: str = "field_mapping",
    stage_id: str = None
) -> Dict[str, Any]:
    """
    Create rule payload for testing.
    
    Args:
        title: Rule title
        rule_type: Rule type
        stage_id: Optional stage ID for stage-specific rules
        
    Returns:
        Dictionary with rule data
    """
    payload = {
        "title": title,
        "type": rule_type,
        "priority": "medium",
        "scope": "stage" if stage_id else "global",
        "status": "active",
        "content": {
            "natural_language": f"Test rule: {title}",
            "json_rule": {
                "test": True
            }
        }
    }
    
    if stage_id:
        payload["stage_id"] = stage_id
    
    return payload

