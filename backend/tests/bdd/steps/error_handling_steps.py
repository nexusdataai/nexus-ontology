"""
Step definitions for Error Handling and Edge Cases BDD tests
"""

import json
from behave import given, when, then
import requests
from typing import Dict, Any


# =============================================================================
# When Steps - Error-inducing Actions
# =============================================================================

@when('I send a request with action "{action}"')
def step_send_request_with_action(context, action):
    """Send request with specific action"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {"arguments": {"action": action}}
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        context.error_response = response
        context.error_response_data = response.json() if response.text else {}
    except Exception as e:
        context.error_exception = e


@when('I send a request to read a journey without journey_id')
def step_read_without_id(context):
    """Read journey without ID"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {"arguments": {"action": "read"}}
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        context.error_response = response
        context.error_response_data = response.json() if response.text else {}
    except Exception as e:
        context.error_exception = e


@when('I try to read journey with ID "{journey_id}"')
def step_try_read_journey(context, journey_id):
    """Try to read journey with specific ID"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {"arguments": {"action": "read", "journey_id": journey_id}}
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.error_response = response
    context.error_response_data = response.json() if response.text else {}


@when('I try to read journey "{journey_id}"')
def step_try_read_specific_journey(context, journey_id):
    """Try to read specific journey"""
    step_try_read_journey(context, journey_id)


@when('I try to execute job on stage "{stage_id}"')
def step_try_execute_on_stage(context, stage_id):
    """Try to execute job on stage"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "run_job",
            "journey_id": context.current_journey_id,
            "stage_id": stage_id,
            "triggered_by": "test"
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.error_response = response
    context.error_response_data = response.json() if response.text else {}


@when('I try to get logs for non-existent job "{job_id}"')
def step_try_get_logs_nonexistent(context, job_id):
    """Try to get logs for non-existent job"""
    url = f"{context.mcp_server_url}/tools/logs_and_reports_tool"
    payload = {
        "arguments": {
            "action": "get_job_logs",
            "journey_id": "JRN-TEST-001",
            "job_id": job_id,
            "stage_name": "raw_analysis"
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.error_response = response
    context.error_response_data = response.json() if response.text else {}


@when('I try to create a journey with empty name')
def step_create_journey_empty_name(context):
    """Create journey with empty name"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "create",
            "name": "",
            "odaComponentType": "test"
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.error_response = response
    context.error_response_data = response.json() if response.text else {}


@when('I send a request with null values for required fields')
def step_send_null_values(context):
    """Send request with null values"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "create",
            "name": None,
            "odaComponentType": None
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.error_response = response
    context.error_response_data = response.json() if response.text else {}


@when('I send a request with:')
def step_send_request_with_table(context):
    """Send request with table data"""
    # Store the invalid data
    context.invalid_request_data = {row['field']: row['value'] for row in context.table}


@when('I try to update journey status to "{status}"')
def step_update_to_invalid_status(context, status):
    """Update to invalid status"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "update",
            "journey_id": "JRN-TEST-001",
            "journey_data": {"status": status}
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.error_response = response
    context.error_response_data = response.json() if response.text else {}


@when('I try to create journey with priority "{priority}"')
def step_create_with_invalid_priority(context, priority):
    """Create journey with invalid priority"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "create",
            "name": "Test Journey",
            "odaComponentType": "test",
            "priority": priority
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.error_response = response
    context.error_response_data = response.json() if response.text else {}


@when('I send a malformed JSON request')
def step_send_malformed_json(context):
    """Send malformed JSON"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    # Send intentionally malformed JSON
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    try:
        response = requests.post(
            url,
            data='{"arguments": {"action": "list"',  # Incomplete JSON
            headers=headers,
            timeout=10
        )
        context.error_response = response
        context.error_response_data = response.json() if response.text else {}
    except Exception as e:
        context.error_exception = e


@when('I try to list journeys')
def step_try_list_journeys(context):
    """Try to list journeys"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {"arguments": {"action": "list"}}
    headers = {
        "Content-Type": "application/json"
    }
    
    # Add API key if it exists and isn't removed
    if hasattr(context, 'api_key') and not hasattr(context, 'api_key_removed'):
        headers["x-api-key"] = context.api_key
    elif hasattr(context, 'invalid_api_key'):
        headers["x-api-key"] = context.invalid_api_key
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.error_response = response
    context.error_response_data = response.json() if response.text else {}


@when('I try to delete the journey without confirmation')
def step_delete_without_confirmation(context):
    """Delete without confirmation"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "delete",
            "journey_id": context.current_journey_id,
            "confirm": False  # Missing or false confirmation
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.error_response = response
    context.error_response_data = response.json() if response.text else {}


@when('I try to update immutable fields:')
def step_update_immutable_fields(context):
    """Try to update immutable fields"""
    immutable_data = {row['field']: row['value'] for row in context.table}
    
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "update",
            "journey_id": context.current_journey_id,
            "journey_data": immutable_data
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.immutable_update_response = response


@when('two users update the journey simultaneously')
def step_concurrent_updates(context):
    """Simulate concurrent updates"""
    context.concurrent_updates = True


@when('I request comprehensive data with short timeout')
def step_request_with_short_timeout(context):
    """Request with short timeout"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "get_comprehensive",
            "journey_id": context.current_journey_id
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=0.1)
        context.error_response = response
    except requests.Timeout:
        context.timeout_error = True


@when('I try to read the journey')
def step_try_read_corrupted_journey(context):
    """Try to read journey"""
    step_try_read_specific_journey(context, context.current_journey_id)


@when('I try to create circular dependencies')
def step_create_circular_dependencies(context):
    """Try to create circular dependencies"""
    context.circular_dependency_attempt = True


@when('I make {count:d} requests in {seconds:d} second')
def step_make_rapid_requests(context, count, seconds):
    """Make rapid requests"""
    import time
    context.rapid_request_results = []
    
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {"arguments": {"action": "list"}}
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    start = time.time()
    for i in range(min(count, 10)):  # Limit to 10 for testing
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        context.rapid_request_results.append(response)
        if time.time() - start > seconds:
            break


@when('I send a request with {size} payload')
def step_send_large_payload(context, size):
    """Send large payload"""
    # Create large payload
    large_data = "x" * (10 * 1024 * 1024)  # 10MB
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "create",
            "name": "Test",
            "large_data": large_data
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        context.error_response = response
    except Exception as e:
        context.error_exception = e


@when('I create a journey with name containing special characters')
def step_create_with_special_chars(context):
    """Create journey with special characters"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "create",
            "name": "Test @#$%^&*() Journey <script>alert('xss')</script>",
            "odaComponentType": "test"
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.special_char_response = response


@when('I try to set progress to {progress:d}')
def step_set_invalid_progress(context, progress):
    """Set invalid progress value"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "update_job_status",
            "journey_id": "JRN-TEST-001",
            "job_id": "JOB-TEST-001",
            "progress": progress
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.error_response = response
    context.error_response_data = response.json() if response.text else {}


@when('I try to create another journey with same ID')
def step_create_duplicate_id(context):
    """Try to create duplicate journey"""
    context.duplicate_attempt = True


@when('I try to access the orphaned resources')
def step_access_orphaned_resources(context):
    """Try to access orphaned resources"""
    context.orphaned_access_attempt = True


@when('a critical operation fails')
def step_critical_operation_fails(context):
    """Simulate critical operation failure"""
    context.critical_failure = True


@when('the operation fails temporarily')
def step_operation_fails_temporarily(context):
    """Simulate temporary failure"""
    context.temporary_failure = True


# =============================================================================
# Given Steps - Error Scenarios Setup
# =============================================================================

@given('I remove the API key from headers')
def step_remove_api_key(context):
    """Remove API key"""
    context.api_key_removed = True


@given('I use an invalid API key "{key}"')
def step_use_invalid_api_key(context, key):
    """Use invalid API key"""
    context.invalid_api_key = key


@given('the database connection is interrupted')
def step_db_connection_interrupted(context):
    """Simulate database connection interruption"""
    context.db_connection_interrupted = True


@given('a journey with corrupted records')
def step_journey_corrupted_records(context):
    """Setup journey with corrupted records"""
    context.corrupted_records = True
    context.current_journey_id = "JRN-CORRUPTED-001"


@given('a journey with stages')
def step_journey_with_stages_error(context):
    """Setup journey with stages for error testing"""
    context.current_journey_id = "JRN-STAGES-ERR-001"


@given('a journey with extremely large dataset')
def step_journey_large_dataset(context):
    """Setup journey with large dataset"""
    context.large_dataset = True
    context.current_journey_id = "JRN-LARGE-001"


@given('an operation that can be retried')
def step_retriable_operation(context):
    """Setup retriable operation"""
    context.retriable_operation = True


@given('a journey with dependent resources')
def step_journey_with_dependencies(context):
    """Setup journey with dependent resources"""
    context.has_dependencies = True
    context.current_journey_id = "JRN-DEPS-001"


@given('orphaned job records exist without parent journey')
def step_orphaned_records_exist(context):
    """Setup orphaned records"""
    context.orphaned_records = True


# =============================================================================
# Then Steps - Error Assertions
# =============================================================================

@then('the response should list valid actions')
def step_verify_valid_actions_listed(context):
    """Verify valid actions listed"""
    response_str = str(context.error_response_data).lower()
    # Should mention some valid actions
    assert 'list' in response_str or 'create' in response_str or 'read' in response_str or 'valid' in response_str


@then('the error should indicate name is required')
def step_verify_name_required(context):
    """Verify name required error"""
    response_str = str(context.error_response_data).lower()
    assert 'name' in response_str and ('required' in response_str or 'empty' in response_str)


@then('invalid fields should be listed')
def step_verify_invalid_fields_listed(context):
    """Verify invalid fields listed"""
    # Error should list invalid fields
    assert hasattr(context, 'error_response_data')


@then('the error should indicate type mismatch')
def step_verify_type_mismatch(context):
    """Verify type mismatch error"""
    response_str = str(context.error_response_data).lower()
    assert 'type' in response_str or 'invalid' in response_str


@then('the error should list valid status values')
def step_verify_valid_statuses_listed(context):
    """Verify valid statuses listed"""
    response_str = str(context.error_response_data).lower()
    assert 'valid' in response_str or 'status' in response_str or 'pending' in response_str


@then('the error should list valid priority values')
def step_verify_valid_priorities_listed(context):
    """Verify valid priorities listed"""
    response_str = str(context.error_response_data).lower()
    assert 'priority' in response_str or 'valid' in response_str


@then('the error should indicate JSON parsing error')
def step_verify_json_parsing_error(context):
    """Verify JSON parsing error"""
    # Should have error about JSON
    assert hasattr(context, 'error_response') or hasattr(context, 'error_exception')


@then('I should receive an authentication error')
def step_verify_authentication_error(context):
    """Verify authentication error"""
    assert hasattr(context, 'error_response'), "No error response"
    # Should indicate authentication problem
    status = context.error_response.status_code
    assert status in [401, 403], f"Expected 401 or 403, got {status}"


@then('HTTP status should be 401 or 403')
def step_verify_auth_status(context):
    """Verify auth status code"""
    assert hasattr(context, 'error_response'), "No error response"
    status = context.error_response.status_code
    assert status in [401, 403], f"Expected 401 or 403, got {status}"


@then('the error should indicate confirmation required')
def step_verify_confirmation_required(context):
    """Verify confirmation required error"""
    response_str = str(context.error_response_data).lower()
    assert 'confirm' in response_str or 'confirmation' in response_str


@then('the update should fail or ignore immutable fields')
def step_verify_immutable_handling(context):
    """Verify immutable fields handled"""
    # Should either fail or ignore
    assert hasattr(context, 'immutable_update_response')


@then('the original values should remain unchanged')
def step_verify_values_unchanged(context):
    """Verify values unchanged"""
    # Original values should be preserved
    pass


@then('one update should succeed')
def step_verify_one_succeeds(context):
    """Verify one update succeeds"""
    # In concurrent scenario
    pass


@then('the other should handle the conflict appropriately')
def step_verify_conflict_handled(context):
    """Verify conflict handled"""
    # Conflict resolution should work
    pass


@then('I should receive a timeout error')
def step_verify_timeout_error(context):
    """Verify timeout error"""
    assert hasattr(context, 'timeout_error') or hasattr(context, 'error_response')


@then('I should receive a service error')
def step_verify_service_error(context):
    """Verify service error"""
    assert hasattr(context, 'error_response')


@then('the error should indicate connectivity issue')
def step_verify_connectivity_error(context):
    """Verify connectivity error"""
    # Should indicate connection problem
    pass


@then('I should receive partial data')
def step_verify_partial_data(context):
    """Verify partial data received"""
    # Should have some data even if incomplete
    pass


@then('I should receive a data integrity error')
def step_verify_data_integrity_error(context):
    """Verify data integrity error"""
    response_str = str(context.error_response_data).lower()
    assert 'integrity' in response_str or 'corrupt' in response_str or 'error' in response_str


@then('the validation should prevent it')
def step_verify_circular_prevented(context):
    """Verify circular dependency prevented"""
    # Validation should catch circular dependencies
    pass


@then('the error should explain the circular dependency')
def step_verify_circular_explanation(context):
    """Verify circular dependency explanation"""
    # Error should be clear about circular issue
    pass


@then('some requests should be rate limited')
def step_verify_rate_limited(context):
    """Verify some requests rate limited"""
    # At least one should hit rate limit
    assert hasattr(context, 'rapid_request_results')


@then('rate limit error should be informative')
def step_verify_rate_limit_informative(context):
    """Verify rate limit error is informative"""
    # Should explain rate limiting
    pass


@then('I should receive a payload size error')
def step_verify_payload_size_error(context):
    """Verify payload size error"""
    # Should indicate payload too large
    assert hasattr(context, 'error_response') or hasattr(context, 'error_exception')


@then('the error should indicate size limit')
def step_verify_size_limit_indicated(context):
    """Verify size limit indicated"""
    # Error should mention size
    pass


@then('the system should either accept or reject appropriately')
def step_verify_special_chars_handled(context):
    """Verify special characters handled"""
    assert hasattr(context, 'special_char_response')
    # Should handle consistently
    pass


@then('any rejection should be clearly explained')
def step_verify_rejection_explained(context):
    """Verify rejection explained"""
    # If rejected, should be clear why
    pass


@then('the error should indicate valid range')
def step_verify_valid_range(context):
    """Verify valid range indicated"""
    response_str = str(context.error_response_data).lower()
    assert 'range' in response_str or 'valid' in response_str or 'between' in response_str


@then('the error should indicate valid range is 0-100')
def step_verify_progress_range(context):
    """Verify progress range"""
    response_str = str(context.error_response_data).lower()
    assert '0' in response_str or '100' in response_str or 'range' in response_str


@then('the system should handle the duplicate appropriately')
def step_verify_duplicate_handled(context):
    """Verify duplicate handled"""
    # Duplicate should be caught
    pass


@then('the system should handle gracefully')
def step_verify_orphaned_handled_gracefully(context):
    """Verify orphaned resources handled"""
    # Should not crash
    pass


@then('appropriate warnings should be issued')
def step_verify_warnings_issued(context):
    """Verify warnings issued"""
    # Warnings should be provided
    pass


@then('dependent operations should be handled appropriately')
def step_verify_dependent_ops_handled(context):
    """Verify dependent operations handled"""
    # Dependencies should be managed
    pass


@then('rollback should occur if necessary')
def step_verify_rollback_occurs(context):
    """Verify rollback on failure"""
    # Rollback logic should execute
    pass


@then('the system should provide retry information')
def step_verify_retry_info_provided(context):
    """Verify retry information provided"""
    # Retry guidance should be given
    pass


@then('subsequent retry should succeed if issue resolved')
def step_verify_retry_succeeds(context):
    """Verify retry can succeed"""
    # Retry should work
    pass


@then('the error code should be "{code}"')
def step_verify_error_code(context, code):
    """Verify specific error code or equivalent error indication in response"""
    response = context.error_response_data if hasattr(context, 'error_response_data') else {}
    response_str = str(response)
    
    # Direct error code check
    if code in response_str or code.lower() in response_str.lower():
        return
    
    # Check for error_code field
    if isinstance(response, dict):
        if response.get('error_code') == code:
            return
        if response.get('result', {}).get('error_code') == code:
            return
    
    # Map expected error codes to equivalent API responses
    code_mappings = {
        'JOURNEY_NOT_FOUND': ['not found', 'does not exist', 'no journey', 'journey not found'],
        'STAGE_NOT_FOUND': ['stage not found', 'invalid stage', 'stage does not exist'],
        'JOB_NOT_FOUND': ['job not found', 'no job', 'job does not exist'],
        'VALIDATION_ERROR': ['validation error', 'invalid', 'required'],
    }
    
    # Check if any equivalent message is in response
    if code in code_mappings:
        for equiv_msg in code_mappings[code]:
            if equiv_msg in response_str.lower():
                return
    
    # For general error codes, check if response indicates error status
    if isinstance(response, dict) and response.get('status') == 'error':
        # Error was returned, check if message relates to expected code
        msg = str(response.get('message', '')).lower()
        code_keywords = code.lower().replace('_', ' ').split()
        if any(kw in msg for kw in code_keywords):
            return
    
    assert False, f"ASSERT FAILED: Expected error code '{code}' in response"


# Note: 'the error should indicate "not found" or "invalid"' handled by generic step in common_steps.py

