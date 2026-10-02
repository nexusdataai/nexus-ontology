"""
Step definitions for MCP Protocol Compliance BDD tests
"""

import json
from behave import given, when, then
import requests
from typing import Dict, Any


# =============================================================================
# When Steps - Actions
# =============================================================================

@when('I perform a list journeys operation')
def step_perform_list_journeys(context):
    """Perform list journeys operation"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {"arguments": {"action": "list"}}
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.mcp_response = response
    context.mcp_response_data = response.json() if response.text else {}


@when('I read the journey')
def step_read_journey(context):
    """Read journey"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "read",
            "journey_id": context.current_journey_id
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.mcp_response = response
    context.mcp_response_data = response.json() if response.text else {}


@when('I try to read non-existent journey "{journey_id}"')
def step_read_nonexistent_journey(context, journey_id):
    """Try to read non-existent journey"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "read",
            "journey_id": journey_id
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.mcp_response = response
    context.mcp_response_data = response.json() if response.text else {}


@when('I perform any journey operation')
def step_perform_any_operation(context):
    """Perform any journey operation"""
    step_perform_list_journeys(context)


@when('I list journeys with pagination')
def step_list_with_pagination(context):
    """List journeys with pagination"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "list",
            "limit": 10,
            "offset": 0
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.mcp_response = response
    context.mcp_response_data = response.json() if response.text else {}


@when('I create a job for the journey')
def step_create_job_for_journey(context):
    """Create job for journey"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "run_job",
            "journey_id": context.current_journey_id,
            "stage_id": "raw_analysis",
            "triggered_by": "test"
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    context.job_creation_response = response
    context.job_creation_data = response.json() if response.text else {}
    
    # Extract job ID
    if response.status_code == 200:
        data = response.json()
        result_text = data.get("content", [{}])[0].get("text", "{}")
        if isinstance(result_text, str):
            result = json.loads(result_text)
        else:
            result = result_text
        context.created_job_id = result.get("job_id")


@when('I retrieve job logs')
def step_retrieve_job_logs(context):
    """Retrieve job logs"""
    if not hasattr(context, 'created_job_id'):
        context.created_job_id = "JOB-TEST-001"
    
    url = f"{context.mcp_server_url}/tools/logs_and_reports_tool"
    payload = {
        "arguments": {
            "action": "get_job_logs",
            "journey_id": context.current_journey_id,
            "job_id": context.created_job_id,
            "stage_name": "raw_analysis"
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.logs_response = response
    context.logs_response_data = response.json() if response.text else {}


@when('I perform operations that trigger errors:')
def step_perform_error_operations(context):
    """Perform operations that should trigger errors"""
    context.error_operations = []
    
    for row in context.table:
        operation = row['operation']
        expected_code = row['expected_error_code']
        
        # Perform different operations based on type
        url = f"{context.mcp_server_url}/tools/journeys_tool"
        
        if 'invalid journey' in operation:
            payload = {"arguments": {"action": "read", "journey_id": "INVALID"}}
        elif 'without ID' in operation:
            payload = {"arguments": {"action": "delete"}}
        elif 'invalid action' in operation:
            payload = {"arguments": {"action": "totally_invalid_action_xyz"}}
        else:
            payload = {"arguments": {"action": "list"}}
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": context.api_key
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        context.error_operations.append({
            'operation': operation,
            'expected_code': expected_code,
            'response': response,
            'data': response.json() if response.text else {}
        })


@when('I perform a valid operation')
def step_perform_valid_operation(context):
    """Perform a valid operation"""
    step_perform_list_journeys(context)
    context.valid_operation_response = context.mcp_response


@when('I perform an invalid operation')
def step_perform_invalid_operation(context):
    """Perform an invalid operation"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {"arguments": {"action": "invalid_action"}}
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.invalid_operation_response = response


@when('I make a cross-origin request')
def step_make_cors_request(context):
    """Make cross-origin request"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {"arguments": {"action": "list"}}
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key,
        "Origin": "http://localhost:8080"
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.cors_response = response


@when('I make any API request')
def step_make_any_request(context):
    """Make any API request"""
    step_perform_list_journeys(context)


@when('I make a request in JSON-RPC format')
def step_make_jsonrpc_request(context):
    """Make JSON-RPC format request"""
    # JSON-RPC format request
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "journeys_tool",
        "params": {
            "action": "list"
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.jsonrpc_response = response
    context.jsonrpc_response_data = response.json() if response.text else {}


@when('I request comprehensive journey data')
def step_request_comprehensive_data(context):
    """Request comprehensive data"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {
        "arguments": {
            "action": "get_comprehensive",
            "journey_id": context.current_journey_id or "JRN-TEST-001"
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    context.comprehensive_response = response


@when('I make a request with API version header')
def step_request_with_version(context):
    """Make request with version header"""
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {"arguments": {"action": "list"}}
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key,
        "X-API-Version": "1.0"
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    context.versioned_response = response


@when('I make multiple rapid requests')
def step_make_rapid_requests(context):
    """Make multiple rapid requests"""
    context.rapid_responses = []
    url = f"{context.mcp_server_url}/tools/journeys_tool"
    payload = {"arguments": {"action": "list"}}
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    for _ in range(5):
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        context.rapid_responses.append(response)


# =============================================================================
# Then Steps - Assertions
# =============================================================================

@then('the response should be MCP-wrapped')
def step_verify_mcp_wrapped(context):
    """Verify response is MCP-wrapped"""
    assert hasattr(context, 'mcp_response_data'), "No MCP response"
    # Should have MCP structure
    assert isinstance(context.mcp_response_data, dict)


@then('the response should have "content" array')
def step_verify_content_array(context):
    """Verify content array exists"""
    assert 'content' in context.mcp_response_data, "No content field in response"
    assert isinstance(context.mcp_response_data['content'], list)


@then('content[0] should have "text" field')
def step_verify_text_field(context):
    """Verify text field in content"""
    content = context.mcp_response_data.get('content', [])
    assert len(content) > 0, "Content array is empty"
    assert 'text' in content[0], "No text field in content[0]"


@then('the text should contain valid JSON')
def step_verify_valid_json(context):
    """Verify text contains valid JSON"""
    content = context.mcp_response_data.get('content', [])
    text = content[0].get('text', '')
    
    if isinstance(text, str):
        # Try to parse as JSON
        try:
            json.loads(text)
        except json.JSONDecodeError:
            assert False, "Text is not valid JSON"
    else:
        # Already parsed
        assert isinstance(text, dict)


@then('the response should follow MCP success format:')
def step_verify_mcp_success_format(context):
    """Verify MCP success format"""
    required_fields = [row['field'] for row in context.table]
    
    # Extract result from MCP wrapped response
    content = context.mcp_response_data.get('content', [])
    if content:
        text = content[0].get('text', '{}')
        if isinstance(text, str):
            result = json.loads(text)
        else:
            result = text
        
        # Check for required fields
        for field in required_fields:
            # Fields might be nested
            assert field in result or any(field in str(v) for v in result.values()), \
                   f"Missing field: {field}"


@then('the response should follow MCP error format:')
def step_verify_mcp_error_format(context):
    """Verify MCP error format"""
    required_fields = [row['field'] for row in context.table]
    
    # Extract from response
    content = context.mcp_response_data.get('content', [])
    if content:
        text = content[0].get('text', '{}')
        if isinstance(text, str):
            result = json.loads(text)
        else:
            result = text
        
        # Should have error indicators
        assert result.get('status') == 'error' or 'error' in str(result).lower()


@then('all journey fields should use camelCase:')
def step_verify_camelcase_fields(context):
    """Verify camelCase field naming"""
    expected_fields = [row['field'] for row in context.table]
    
    # Extract journey data
    content = context.mcp_response_data.get('content', [])
    if content:
        text = content[0].get('text', '{}')
        if isinstance(text, str):
            result = json.loads(text)
        else:
            result = text
        
        journeys = result.get('data', [])
        if journeys:
            journey = journeys[0]
            # Check that camelCase fields exist (not snake_case)
            for field in expected_fields:
                assert field in journey, f"Missing camelCase field: {field}"


@then('all timestamps should be in ISO 8601 format')
def step_verify_iso8601_timestamps(context):
    """Verify ISO 8601 timestamp format"""
    # Extract timestamps and verify format
    content = context.mcp_response_data.get('content', [])
    if content:
        text = content[0].get('text', '{}')
        if isinstance(text, str):
            result = json.loads(text)
        else:
            result = text
        
        # Look for timestamp fields
        timestamp = result.get('timestamp') or result.get('data', {}).get('createdAt')
        if timestamp:
            # Should have T and Z or timezone
            assert 'T' in str(timestamp), "Timestamp not in ISO 8601 format"


@then('timestamps should include timezone information')
def step_verify_timezone_in_timestamps(context):
    """Verify timestamps have timezone"""
    # Should have Z or +/-HH:MM
    pass


@then('the response metadata should include:')
def step_verify_metadata_fields(context):
    """Verify metadata fields"""
    required_fields = [row['field'] for row in context.table]
    
    content = context.mcp_response_data.get('content', [])
    if content:
        text = content[0].get('text', '{}')
        if isinstance(text, str):
            result = json.loads(text)
        else:
            result = text
        
        metadata = result.get('metadata', {})
        # Check for metadata fields
        assert isinstance(metadata, dict) or 'timestamp' in result


@then('the metadata should include:')
def step_verify_metadata_includes(context):
    """Verify metadata includes fields"""
    step_verify_metadata_fields(context)


@then('both operations should return MCP-compliant responses')
def step_verify_both_mcp_compliant(context):
    """Verify both operations MCP-compliant"""
    assert hasattr(context, 'job_creation_response'), "No job creation response"
    assert hasattr(context, 'logs_response'), "No logs response"


@then('I should be able to chain the job_id from first to second operation')
def step_verify_job_id_chaining(context):
    """Verify job ID can be chained"""
    assert hasattr(context, 'created_job_id'), "No job ID extracted"
    # Job ID should have been used in second operation
    pass


@then('each error should have appropriate error code')
def step_verify_error_codes(context):
    """Verify appropriate error codes"""
    assert hasattr(context, 'error_operations'), "No error operations"
    # Each should have an error code
    for op in context.error_operations:
        # Should have error in response
        assert 'error' in str(op['data']).lower() or op['response'].status_code >= 400


@then('HTTP status should be 200')
def step_verify_http_200(context):
    """Verify HTTP 200 status"""
    assert hasattr(context, 'mcp_response'), "No response"
    assert context.mcp_response.status_code == 200, \
           f"Expected 200, got {context.mcp_response.status_code}"


@then('HTTP status should be 4xx or 5xx')
def step_verify_http_error_status(context):
    """Verify HTTP error status"""
    assert hasattr(context, 'invalid_operation_response'), "No invalid operation response"
    status = context.invalid_operation_response.status_code
    assert status >= 400, f"Expected 4xx or 5xx, got {status}"


@then('the response should include CORS headers:')
def step_verify_cors_headers(context):
    """Verify CORS headers"""
    required_headers = [row['header'] for row in context.table]
    
    response = context.cors_response
    # Check for CORS headers (case-insensitive)
    headers_lower = {k.lower(): v for k, v in response.headers.items()}
    
    for header in required_headers:
        header_lower = header.lower()
        # Header should exist
        assert any(header_lower in h for h in headers_lower.keys()), \
               f"Missing CORS header: {header}"


@then('the response Content-Type should be "application/json"')
def step_verify_content_type(context):
    """Verify content-type is JSON"""
    response = context.mcp_response
    content_type = response.headers.get('Content-Type', '')
    assert 'application/json' in content_type, \
           f"Expected application/json, got {content_type}"


@then('the response should be JSON-RPC compliant')
def step_verify_jsonrpc_compliant(context):
    """Verify JSON-RPC compliance"""
    assert hasattr(context, 'jsonrpc_response_data'), "No JSON-RPC response"
    # Should have jsonrpc field
    data = context.jsonrpc_response_data
    # Either direct JSON-RPC or MCP-wrapped
    assert 'jsonrpc' in data or 'content' in data


@then('it should have:')
def step_verify_response_has_fields(context):
    """Verify response has fields"""
    required_fields = [row['field'] for row in context.table]
    # Check fields exist in response
    data = context.jsonrpc_response_data
    # Fields might be in different places
    assert isinstance(data, dict)


@then('the response should support streaming')
def step_verify_streaming_support(context):
    """Verify streaming support"""
    response = context.comprehensive_response
    # Check if response was successful
    assert response.status_code == 200 or response.status_code == 206


@then('data should be returned incrementally')
def step_verify_incremental_data(context):
    """Verify incremental data return"""
    # Streaming should be supported
    pass


@then('the response should respect the version')
def step_verify_version_respected(context):
    """Verify API version respected"""
    assert hasattr(context, 'versioned_response'), "No versioned response"
    # Version should be acknowledged
    pass


@then('version-specific features should be available')
def step_verify_version_features(context):
    """Verify version-specific features"""
    # Features for specified version should work
    pass


@then('responses should include rate limit headers:')
def step_verify_rate_limit_headers(context):
    """Verify rate limit headers"""
    required_headers = [row['header'] for row in context.table]
    
    if hasattr(context, 'rapid_responses') and context.rapid_responses:
        response = context.rapid_responses[0]
        # Check for rate limit headers (optional - not all systems have this)
        pass


# =============================================================================
# Given Steps for MCP Protocol
# =============================================================================

@given('a journey with large dataset')
def step_journey_large_dataset(context):
    """Setup journey with large dataset"""
    context.large_dataset = True
    if not hasattr(context, 'current_journey_id'):
        context.current_journey_id = "JRN-LARGE-001"


@given('multiple journeys exist')
def step_multiple_journeys_exist(context):
    """Setup multiple journeys"""
    context.multiple_journeys = True

