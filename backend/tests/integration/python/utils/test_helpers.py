"""
Test helper utilities for integration tests

This module provides utility functions for test setup, cleanup,
and common operations.
"""

import asyncio
import time
import json
from typing import Callable, Any, Optional, Dict
from datetime import datetime


def unwrap_mcp_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unwrap MCP protocol response format.
    
    MCP responses may be wrapped in: {"content": [{"type": "text", "text": "{...}"}]}
    This function extracts the actual response data.
    
    Args:
        response: Raw response dictionary
        
    Returns:
        Unwrapped response dictionary
    """
    # If already unwrapped (has status field), return as-is
    if "status" in response:
        return response
    
    # Check for MCP wrapper format
    if "content" in response and isinstance(response["content"], list):
        if len(response["content"]) > 0:
            content_item = response["content"][0]
            if isinstance(content_item, dict) and "text" in content_item:
                # Parse the JSON string in text field
                try:
                    return json.loads(content_item["text"])
                except (json.JSONDecodeError, TypeError):
                    pass
    
    # Return as-is if we can't unwrap
    return response


def generate_unique_name(prefix: str = "Test") -> str:
    """
    Generate a unique name for test resources.
    
    Args:
        prefix: Prefix for the name
        
    Returns:
        Unique name string with timestamp
    """
    timestamp = int(time.time())
    return f"{prefix} {timestamp}"


async def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 30.0,
    interval: float = 1.0,
    error_message: str = "Condition not met within timeout"
) -> bool:
    """
    Wait for a condition to become true.
    
    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        error_message: Error message if timeout is reached
        
    Returns:
        True if condition was met
        
    Raises:
        TimeoutError: If condition not met within timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if condition():
                return True
        except Exception:
            pass
        
        await asyncio.sleep(interval)
    
    raise TimeoutError(error_message)


async def cleanup_journey(
    client: Any,
    journey_id: str,
    api_key: str = "super-secret"
) -> bool:
    """
    Cleanup a test journey.
    
    Args:
        client: HTTP client
        journey_id: Journey ID to cleanup
        api_key: API key for authentication
        
    Returns:
        True if cleanup successful
    """
    try:
        response = await client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "delete",
                "journey_id": journey_id,
                "confirm": True
            }},
            headers={"x-api-key": api_key}
        )
        return response.status_code in [200, 404]  # 404 is OK if already deleted
    except Exception as e:
        print(f"Warning: Failed to cleanup journey {journey_id}: {e}")
        return False


async def cleanup_job(
    client: Any,
    journey_id: str,
    job_id: str,
    api_key: str = "super-secret"
) -> bool:
    """
    Cleanup a test job.
    
    Args:
        client: HTTP client
        journey_id: Journey ID
        job_id: Job ID to cleanup
        api_key: API key for authentication
        
    Returns:
        True if cleanup successful
    """
    try:
        response = await client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "batch_cancel_jobs",
                "journey_id": journey_id,
                "job_ids": [job_id]
            }},
            headers={"x-api-key": api_key}
        )
        return response.status_code in [200, 404]
    except Exception as e:
        print(f"Warning: Failed to cleanup job {job_id}: {e}")
        return False


def assert_field_exists(data: dict, field: str, message: Optional[str] = None):
    """
    Assert that a field exists in a dictionary.
    
    Args:
        data: Dictionary to check
        field: Field name to look for
        message: Optional custom error message
    """
    if message is None:
        message = f"Field '{field}' not found in data"
    assert field in data, message


def assert_field_value(
    data: dict,
    field: str,
    expected_value: Any,
    message: Optional[str] = None
):
    """
    Assert that a field has a specific value.
    
    Args:
        data: Dictionary to check
        field: Field name
        expected_value: Expected value
        message: Optional custom error message
    """
    assert_field_exists(data, field)
    if message is None:
        message = f"Expected {field}='{expected_value}', got '{data[field]}'"
    assert data[field] == expected_value, message


def extract_journey_id(response: dict) -> str:
    """
    Extract journey ID from response.
    
    Args:
        response: Response dictionary (can be raw MCP response or unwrapped)
        
    Returns:
        Journey ID string
        
    Raises:
        KeyError: If journey_id not found
    """
    # Handle MCP response format - unwrap if needed
    if "content" in response and isinstance(response["content"], list):
        response = unwrap_mcp_response(response)
    
    # Try direct journey_id field
    if "journey_id" in response:
        return response["journey_id"]
    
    # Try data.journey_id
    if "data" in response and isinstance(response["data"], dict):
        if "journey_id" in response["data"]:
            return response["data"]["journey_id"]
        # Try data.journeyId (camelCase variant)
        if "journeyId" in response["data"]:
            return response["data"]["journeyId"]
    
    # Try journeyId at top level (camelCase variant)
    if "journeyId" in response:
        return response["journeyId"]
    
    raise KeyError(f"journey_id not found in response. Available keys: {list(response.keys())}")


def extract_job_id(response: dict) -> str:
    """
    Extract job ID from response.
    
    Args:
        response: Response dictionary
        
    Returns:
        Job ID string
        
    Raises:
        KeyError: If job_id not found
    """
    # Try direct job_id field
    if "job_id" in response:
        return response["job_id"]
    
    # Try data.job_id
    if "data" in response and isinstance(response["data"], dict):
        if "job_id" in response["data"]:
            return response["data"]["job_id"]
        # Try data.jobId (camelCase variant)
        if "jobId" in response["data"]:
            return response["data"]["jobId"]
    
    # Try jobId at top level (camelCase variant)
    if "jobId" in response:
        return response["jobId"]
    
    raise KeyError(f"job_id not found in response. Available keys: {list(response.keys())}")

