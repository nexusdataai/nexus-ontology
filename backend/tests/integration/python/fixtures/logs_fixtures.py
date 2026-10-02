"""
Logs and reports test fixtures

Provides reusable test data for logs and reports operations.
"""

from typing import Dict, Any
import pytest
from datetime import datetime


@pytest.fixture
def log_entry_data() -> Dict[str, Any]:
    """
    Log entry data for testing log operations.
    """
    return {
        "log_level": "info",
        "log_message": "Test log entry for integration tests",
        "log_source": "integration_test",
        "log_details": {
            "test_type": "integration",
            "component": "logs_tool"
        }
    }


@pytest.fixture
def error_log_data() -> Dict[str, Any]:
    """
    Error log entry data.
    """
    return {
        "log_level": "error",
        "log_message": "Test error log entry",
        "log_source": "integration_test",
        "log_details": {
            "error_type": "TestError",
            "error_code": "TEST_001"
        }
    }


@pytest.fixture
def warning_log_data() -> Dict[str, Any]:
    """
    Warning log entry data.
    """
    return {
        "log_level": "warning",
        "log_message": "Test warning log entry",
        "log_source": "integration_test",
        "log_details": {
            "warning_type": "TestWarning"
        }
    }


@pytest.fixture
def report_data_fixture() -> Dict[str, Any]:
    """
    Report data for testing report operations.
    """
    return {
        "report_type": "custom",
        "report_title": "Test Report",
        "report_summary": "Summary of test report",
        "report_content": {
            "sections": [
                {
                    "title": "Section 1",
                    "content": "Test content for section 1"
                },
                {
                    "title": "Section 2",
                    "content": "Test content for section 2"
                }
            ],
            "metrics": {
                "test_metric_1": 42,
                "test_metric_2": 3.14
            }
        }
    }


# Non-fixture helper functions

def create_log_entry_payload(
    level: str = "info",
    message: str = None,
    step_name: str = "test_step"
) -> Dict[str, Any]:
    """
    Create log entry payload for testing.
    
    Args:
        level: Log level (error/warning/info/debug)
        message: Log message
        step_name: Step name
        
    Returns:
        Dictionary with log entry data
    """
    import time
    if message is None:
        message = f"Test log message at {int(time.time())}"
    
    return {
        "log_level": level,
        "log_message": message,
        "step_name": step_name,
        "log_source": "integration_test",
        "log_details": {
            "timestamp": datetime.utcnow().isoformat()
        }
    }


def create_report_payload(
    report_type: str = "summary",
    title: str = None
) -> Dict[str, Any]:
    """
    Create report payload for testing.
    
    Args:
        report_type: Report type (summary/performance/error_analysis/custom)
        title: Report title
        
    Returns:
        Dictionary with report data
    """
    import time
    if title is None:
        title = f"Test Report {int(time.time())}"
    
    return {
        "report_type": report_type,
        "report_title": title,
        "report_summary": f"Test {report_type} report",
        "report_content": {
            "generated_at": datetime.utcnow().isoformat(),
            "test": True
        }
    }


def create_search_query_payload(
    query: str,
    level_filter: str = None,
    step_filter: str = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Create search query payload for log search.
    
    Args:
        query: Search query string
        level_filter: Filter by log level
        step_filter: Filter by step name
        limit: Maximum number of results
        
    Returns:
        Dictionary with search parameters
    """
    payload = {
        "search_query": query,
        "limit": limit
    }
    
    if level_filter:
        payload["level_filter"] = level_filter
    if step_filter:
        payload["step_filter"] = step_filter
    
    return payload

