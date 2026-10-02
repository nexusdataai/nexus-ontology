#!/usr/bin/env python3
"""
Generic API Step Definitions for BDD Tests
Provides reusable steps for making HTTP requests and validating responses
"""

import requests
import json
import re
from behave import given, when, then, step


@given('the backend service is running at "{url}"')
def step_backend_running(context, url):
    """Verify backend service is accessible"""
    context.base_url = url
    context.api_key = context.api_key if hasattr(context, 'api_key') else "super-secret"
    
    try:
        response = requests.get(f"{url}/health", timeout=5)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        context.service_healthy = True
    except Exception as e:
        raise AssertionError(f"Backend service not accessible at {url}: {e}")


@given('the backend service is running')
def step_backend_running_default(context):
    """Verify backend service is accessible at default URL"""
    default_url = context.base_url if hasattr(context, 'base_url') else "http://localhost:8000"
    step_backend_running(context, default_url)


@given('I have a valid API key "{api_key}"')
def step_set_api_key(context, api_key):
    """Set API key for authentication"""
    context.api_key = api_key


@when('I send POST to "{endpoint}" with')
def step_post_with_json_body(context):
    """Send POST request with JSON body from docstring"""
    payload = json.loads(context.text)
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    endpoint = context.endpoint if hasattr(context, 'endpoint') else "/tools/journeys_tool"
    context.response = requests.post(
        f"{context.base_url}{endpoint}",
        json=payload,
        headers=headers,
        timeout=30
    )
    context.response_data = context.response.json()


@when('I send POST to "{endpoint}" with action "{action}"')
def step_post_with_action(context, endpoint, action):
    """Send POST request with simple action"""
    payload = {"arguments": {"action": action}}
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    context.response = requests.post(
        f"{context.base_url}{endpoint}",
        json=payload,
        headers=headers,
        timeout=30
    )
    context.response_data = context.response.json()


@when('I send {method} to "{endpoint}"')
def step_send_request(context, method, endpoint):
    """Send HTTP request with specified method"""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": context.api_key
    }
    
    url = f"{context.base_url}{endpoint}"
    
    if method.upper() == "GET":
        context.response = requests.get(url, headers=headers, timeout=30)
    elif method.upper() == "POST":
        payload = json.loads(context.text) if context.text else {}
        context.response = requests.post(url, json=payload, headers=headers, timeout=30)
    elif method.upper() == "PUT":
        payload = json.loads(context.text) if context.text else {}
        context.response = requests.put(url, json=payload, headers=headers, timeout=30)
    elif method.upper() == "DELETE":
        context.response = requests.delete(url, headers=headers, timeout=30)
    
    try:
        context.response_data = context.response.json()
    except:
        context.response_data = {"raw": context.response.text}


@then('the response status code should be {code:d}')
def step_check_status_code(context, code):
    """Verify HTTP status code"""
    assert context.response.status_code == code, \
        f"Expected status {code}, got {context.response.status_code}"


@then('the response should be successful')
@then('the operation should succeed')
@then(u'the response should be successful')
def step_response_successful(context):
    """Verify API operation was successful"""
    # Handle MCP wrapped response
    if 'content' in context.response_data:
        result_text = context.response_data['content'][0]['text']
        result = json.loads(result_text)
        status = result.get('status', 'error')
    else:
        # Direct response
        status = context.response_data.get('status', 'error')
    
    assert status == 'success', f"Expected success, got: {status}"


@then('the response should contain "{text}"')
def step_response_contains(context, text):
    """Verify response contains specific text"""
    response_text = json.dumps(context.response_data)
    assert text in response_text, f"Expected '{text}' in response"


@then('the response should have field "{field}"')
def step_response_has_field(context, field):
    """Verify response has specific field"""
    # Handle MCP wrapped response
    if 'content' in context.response_data:
        result_text = context.response_data['content'][0]['text']
        result = json.loads(result_text)
        data = result.get('data', result)
    else:
        data = context.response_data
    
    # Support nested field access with dot notation
    fields = field.split('.')
    current = data
    for f in fields:
        assert f in current, f"Field '{f}' not found in response"
        current = current[f]


@then('the response field "{field}" should be "{value}"')
def step_response_field_equals(context, field, value):
    """Verify response field has specific value"""
    # Handle MCP wrapped response
    if 'content' in context.response_data:
        result_text = context.response_data['content'][0]['text']
        result = json.loads(result_text)
        data = result.get('data', result)
    else:
        data = context.response_data
    
    # Support nested field access
    fields = field.split('.')
    current = data
    for f in fields:
        current = current[f]
    
    assert str(current) == value, f"Expected {field}={value}, got {current}"


@then('the response field "{field}" should match pattern "{pattern}"')
def step_response_field_matches_pattern(context, field, pattern):
    """Verify response field matches regex pattern"""
    # Handle MCP wrapped response
    if 'content' in context.response_data:
        result_text = context.response_data['content'][0]['text']
        result = json.loads(result_text)
        data = result.get('data', result)
    else:
        data = context.response_data
    
    # Support nested field access
    fields = field.split('.')
    current = data
    for f in fields:
        current = current[f]
    
    assert re.match(pattern, str(current)), f"{field}={current} doesn't match pattern {pattern}"


@then('the response should contain at least {count:d} items')
@then('the response should contain at least {count:d} journeys')
@then('the response should list at least {count:d} journeys')
def step_response_count_min(context, count):
    """Verify response contains minimum number of items"""
    # Handle MCP wrapped response
    if 'content' in context.response_data:
        result_text = context.response_data['content'][0]['text']
        result = json.loads(result_text)
        data = result.get('data', [])
    else:
        data = context.response_data.get('data', [])
    
    # Handle various response formats
    if isinstance(data, dict):
        data = data.get('journeys', data.get('stages', data.get('rules', data.get('jobs', data.get('items', [])))))
    
    actual_count = len(data) if isinstance(data, list) else 0
    assert actual_count >= count, f"Expected at least {count} items, got {actual_count}"


@then('the response should fail with error containing "{error_text}"')
def step_response_error(context, error_text):
    """Verify API operation failed with specific error"""
    # Handle MCP wrapped response
    if 'content' in context.response_data:
        result_text = context.response_data['content'][0]['text']
        result = json.loads(result_text)
    else:
        result = context.response_data
    
    status = result.get('status', 'success')
    assert status == 'error', f"Expected error, got {status}"
    
    error_msg = result.get('message', result.get('error', ''))
    assert error_text.lower() in error_msg.lower(), f"Expected error containing '{error_text}', got '{error_msg}'"


def extract_result_from_response(context):
    """Helper to extract result from MCP wrapped response"""
    if 'content' in context.response_data:
        result_text = context.response_data['content'][0]['text']
        return json.loads(result_text)
    return context.response_data

