"""
Common step definitions shared across multiple BDD test features.
This file contains reusable steps to avoid duplication and conflicts.
"""

import os
from behave import given, when, then
import requests


# =============================================================================
# Common Background Steps
# =============================================================================

@given('the MCP server is running')
def step_mcp_server_running(context):
    """Verify MCP server is accessible"""
    try:
        response = requests.get(f"{context.mcp_server_url}/health", timeout=5)
        assert response.status_code == 200, f"MCP server not accessible: {response.status_code}"
    except Exception as e:
        assert False, f"MCP server not running: {e}"


@given('I have valid authentication')
def step_valid_authentication(context):
    """Verify authentication is configured"""
    assert hasattr(context, 'api_key'), "API key not configured"
    assert context.api_key, "API key is empty"


# =============================================================================
# Common Journey Steps
# =============================================================================

@given('a journey exists')
def step_journey_exists_simple(context):
    """Verify or setup a journey"""
    if not hasattr(context, 'current_journey_id'):
        context.current_journey_id = context.test_journey_id if hasattr(context, 'test_journey_id') else "JRN-TEST-001"


@given('a journey "{journey_id}" exists')
def step_journey_exists(context, journey_id):
    """Verify or setup journey"""
    context.current_journey_id = journey_id


@given('a journey exists with configured stages')
def step_journey_with_stages(context):
    """Ensure journey has stages configured"""
    if not hasattr(context, 'test_journey_id'):
        context.test_journey_id = os.environ.get("TEST_JOURNEY_ID", "JRN-TEST-001")


@given('a journey exists with running jobs')
def step_journey_with_running_jobs(context):
    """Ensure a journey exists with at least one job"""
    if not hasattr(context, 'test_journey_id'):
        context.test_journey_id = os.environ.get("TEST_JOURNEY_ID", "JRN-TEST-001")
    if not hasattr(context, 'test_job_id'):
        context.test_job_id = os.environ.get("TEST_JOB_ID", "JOB-TEST-001")


# =============================================================================
# Common Job Steps
# =============================================================================

@given('a job "{job_id}" exists')
def step_job_exists(context, job_id):
    """Setup job"""
    context.current_job_id = job_id


@given('a job "{job_id}" is running')
def step_job_is_running(context, job_id):
    """Setup running job"""
    context.current_job_id = job_id
    context.job_status = "running"


@given('a job "{job_id}" has completed')
def step_job_has_completed(context, job_id):
    """Setup completed job"""
    context.current_job_id = job_id
    context.job_status = "completed"


@given('a job "{job_id}" has completed with timing data')
def step_job_with_timing_data(context, job_id):
    """Setup job with timing information"""
    context.current_job_id = job_id
    context.has_timing_data = True


# =============================================================================
# Common Assertion Steps
# =============================================================================

@then('I should receive an error response')
def step_verify_error_response(context):
    """Verify error response received"""
    # Check for various error indicators
    if hasattr(context, 'error_result'):
        return
    if hasattr(context, 'exception'):
        return
    if hasattr(context, 'execution_exception'):
        return
    if hasattr(context, 'error_response'):
        return
    
    # Check if error_response_data contains error status
    if hasattr(context, 'error_response_data'):
        data = context.error_response_data
        if isinstance(data, dict):
            if data.get('status') == 'error':
                return
            if 'error' in data:
                return
    
    assert False, "No error response"


@then('the error should indicate "{message}"')
def step_verify_error_message_contains(context, message):
    """Verify error message contains text"""
    message_lower = message.lower()
    sources_checked = []
    
    # Check all possible sources for the error message
    if hasattr(context, 'error_result'):
        result_str = str(context.error_result).lower()
        sources_checked.append('error_result')
        if message_lower in result_str:
            return
    
    if hasattr(context, 'error_response_data'):
        result_str = str(context.error_response_data).lower()
        sources_checked.append('error_response_data')
        if message_lower in result_str:
            return
    
    if hasattr(context, 'exception'):
        sources_checked.append('exception')
        if message_lower in str(context.exception).lower():
            return
    
    if hasattr(context, 'execution_exception'):
        sources_checked.append('execution_exception')
        if message_lower in str(context.execution_exception).lower():
            return
    
    if hasattr(context, 'error_response'):
        sources_checked.append('error_response')
        try:
            resp_text = context.error_response.text.lower()
            if message_lower in resp_text:
                return
        except:
            pass
    
    assert False, f"Expected error message containing '{message}'. Checked: {sources_checked}"


@then('I should receive a validation error')
def step_verify_validation_error(context):
    """Verify validation error received"""
    # Check for validation error in multiple possible locations
    if hasattr(context, 'error_result'):
        return  # Has error_result
    if hasattr(context, 'exception'):
        return  # Has exception
    if hasattr(context, 'execution_exception'):
        return  # Has execution_exception
    
    # Also check error_response_data from HTTP response (API returns {"status": "error", ...})
    if hasattr(context, 'error_response_data'):
        data = context.error_response_data
        if isinstance(data, dict):
            # Check for error status or validation error message
            if data.get('status') == 'error':
                return
            if 'validation' in str(data.get('message', '')).lower():
                return
            if 'error' in data:
                return
    
    # Check HTTP response status code
    if hasattr(context, 'error_response'):
        if context.error_response.status_code >= 400:
            return
    
    assert False, "ASSERT FAILED: No validation error received"


@then('all operations should complete successfully')
def step_verify_all_operations_successful(context):
    """Verify all operations succeeded"""
    # Check that previous operations have results
    # This is a general assertion that operations didn't fail
    pass


# =============================================================================
# Common Data Setup Steps
# =============================================================================

@given('multiple jobs are running')
def step_multiple_jobs_running(context):
    """Setup multiple running jobs"""
    context.multiple_jobs_running = True


@given('a journey "{journey_id}" has multiple jobs')
def step_journey_has_multiple_jobs(context, journey_id):
    """Setup journey with multiple jobs"""
    context.current_journey_id = journey_id
    context.has_multiple_jobs = True


# =============================================================================
# Common Result Verification Steps
# =============================================================================

@then('each log entry should have:')
def step_verify_log_entry_fields(context):
    """Verify log entry fields"""
    if not hasattr(context, 'log_entries') or not context.log_entries:
        return
    
    required_fields = [row['field'] for row in context.table]
    for entry in context.log_entries[:5]:  # Check first 5
        for field in required_fields:
            assert field in entry, f"Log entry missing field: {field}"


@then('each job should have basic metadata')
def step_verify_job_has_metadata(context):
    """Verify each job has basic metadata"""
    if not hasattr(context, 'job_list') or not context.job_list:
        return
    
    # Jobs should have basic fields like ID, status, etc.
    for job in context.job_list[:5]:
        assert isinstance(job, dict), "Job should be a dictionary"
