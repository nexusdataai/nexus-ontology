"""
Response validation utilities for integration tests

This module provides validation functions for standard response formats
used by the AI Job Engine HTTP gateway and MCP tools.
"""

from typing import Dict, Any, Optional, List
import json


def _unwrap_if_mcp(response: Dict[str, Any]) -> Dict[str, Any]:
    """Unwrap MCP response format if present."""
    if "content" in response and isinstance(response["content"], list):
        try:
            content = response["content"][0]
            if content.get("type") == "text":
                return json.loads(content["text"])
        except (IndexError, KeyError, json.JSONDecodeError):
            pass
    return response


def validate_success_response(
    response: Dict[str, Any],
    expected_operation: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate standard success response format.
    
    Args:
        response: Response dictionary to validate (can be MCP wrapped or unwrapped)
        expected_operation: Expected operation name (optional)
        
    Returns:
        The validated response dictionary
        
    Raises:
        AssertionError: If validation fails
    """
    # Unwrap MCP format if needed
    response = _unwrap_if_mcp(response)
    
    assert isinstance(response, dict), f"Response must be dict, got {type(response)}"
    assert response.get("status") == "success", f"Expected success status, got: {response.get('status')}"
    assert "message" in response, "Response must contain 'message' field"
    assert "operation" in response, "Response must contain 'operation' field"
    
    if expected_operation:
        assert response["operation"] == expected_operation, \
            f"Expected operation '{expected_operation}', got: {response['operation']}"
    
    return response


def validate_error_response(
    response: Dict[str, Any],
    expected_operation: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate standard error response format.
    
    Args:
        response: Response dictionary to validate (can be MCP wrapped or unwrapped)
        expected_operation: Expected operation name (optional)
        
    Returns:
        The validated response dictionary
        
    Raises:
        AssertionError: If validation fails
    """
    # Unwrap MCP format if needed
    response = _unwrap_if_mcp(response)
    
    assert isinstance(response, dict), f"Response must be dict, got {type(response)}"
    assert response.get("status") == "error", f"Expected error status, got: {response.get('status')}"
    assert "message" in response, "Response must contain 'message' field"
    assert "error" in response or "error_code" in response, \
        "Error response must contain 'error' or 'error_code' field"
    
    if expected_operation:
        assert response.get("operation") == expected_operation, \
            f"Expected operation '{expected_operation}', got: {response.get('operation')}"
    
    return response


def validate_journey_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate journey data structure with snake_case fields.
    
    Args:
        data: Journey data dictionary to validate
        
    Returns:
        The validated data dictionary
        
    Raises:
        AssertionError: If validation fails
    """
    assert isinstance(data, dict), f"Journey data must be dict, got {type(data)}"
    assert "journey_id" in data, "Journey data must contain 'journey_id'"
    assert data["journey_id"].startswith("JRN-"), \
        f"Journey ID must start with 'JRN-', got: {data['journey_id']}"
    assert "name" in data, "Journey data must contain 'name'"
    assert "status" in data, "Journey data must contain 'status'"
    assert data["status"] in ["pending", "running", "completed", "failed", "cancelled", "paused"], \
        f"Invalid journey status: {data['status']}"
    
    return data


def validate_stage_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate stage data structure.
    
    Args:
        data: Stage data dictionary to validate
        
    Returns:
        The validated data dictionary
        
    Raises:
        AssertionError: If validation fails
    """
    assert isinstance(data, dict), f"Stage data must be dict, got {type(data)}"
    assert "stage_id" in data, "Stage data must contain 'stage_id'"
    assert "name" in data, "Stage data must contain 'name'"
    assert "order" in data, "Stage data must contain 'order'"
    
    return data


def validate_rule_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate rule data structure.
    
    Args:
        data: Rule data dictionary to validate
        
    Returns:
        The validated data dictionary
        
    Raises:
        AssertionError: If validation fails
    """
    assert isinstance(data, dict), f"Rule data must be dict, got {type(data)}"
    assert "rule_id" in data, "Rule data must contain 'rule_id'"
    assert "title" in data, "Rule data must contain 'title'"
    assert "type" in data, "Rule data must contain 'type'"
    assert data["type"] in [
        "field_mapping",
        "contextual_recommendations",
        "data_interpretation",
        "validation_rules",
        "business_logic",
        "compliance_check"
    ], f"Invalid rule type: {data['type']}"
    
    return data


def validate_log_entry(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate log entry structure.
    
    Args:
        data: Log entry dictionary to validate
        
    Returns:
        The validated data dictionary
        
    Raises:
        AssertionError: If validation fails
    """
    assert isinstance(data, dict), f"Log entry must be dict, got {type(data)}"
    assert "job_id" in data or "jobId" in data, "Log entry must contain 'job_id' or 'jobId'"
    assert "timestamp" in data, "Log entry must contain 'timestamp'"
    assert "level" in data or "log_level" in data, "Log entry must contain 'level' or 'log_level'"
    assert "message" in data or "log_message" in data, "Log entry must contain 'message' or 'log_message'"
    
    return data


def validate_report_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate report data structure.
    
    Args:
        data: Report data dictionary to validate
        
    Returns:
        The validated data dictionary
        
    Raises:
        AssertionError: If validation fails
    """
    assert isinstance(data, dict), f"Report data must be dict, got {type(data)}"
    assert "report_id" in data or "reportId" in data, "Report data must contain 'report_id' or 'reportId'"
    assert "report_type" in data or "reportType" in data, "Report data must contain 'report_type' or 'reportType'"
    
    return data


def validate_list_response(
    response: Dict[str, Any],
    min_items: int = 0,
    expected_operation: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate list operation response.
    
    Args:
        response: Response dictionary to validate
        min_items: Minimum number of items expected
        expected_operation: Expected operation name (optional)
        
    Returns:
        The validated response dictionary
        
    Raises:
        AssertionError: If validation fails
    """
    validate_success_response(response, expected_operation)
    
    assert "data" in response, "List response must contain 'data' field"
    data = response["data"]
    
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "items" in data:
        items = data["items"]
    else:
        items = []
    
    assert isinstance(items, list), f"Items must be a list, got {type(items)}"
    assert len(items) >= min_items, \
        f"Expected at least {min_items} items, got {len(items)}"
    
    return response


def validate_pagination_metadata(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate pagination metadata in response.
    
    Args:
        response: Response dictionary to validate
        
    Returns:
        The validated response dictionary
        
    Raises:
        AssertionError: If validation fails
    """
    if "metadata" in response:
        metadata = response["metadata"]
        if "total_count" in metadata:
            assert isinstance(metadata["total_count"], (int, float)), \
                "total_count must be numeric"
        if "page" in metadata:
            assert isinstance(metadata["page"], (int, float)), \
                "page must be numeric"
        if "page_size" in metadata:
            assert isinstance(metadata["page_size"], (int, float)), \
                "page_size must be numeric"
    
    return response

