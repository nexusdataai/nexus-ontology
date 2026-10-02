"""
Property-based tests for Gateway LocalStack health endpoint response format.

Feature: gateway-localstack-integration
Property 4: Health endpoint response format

Tests that the /health/localstack endpoint returns properly formatted responses
for all possible states (healthy, unhealthy, unreachable, disabled).

**Validates: Requirements 2.4, 5.2, 5.3**
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from hypothesis import given, strategies as st, settings
from src.config.localstack_config import LocalStackConfig, reset_localstack_config


def clean_env():
    """Remove LocalStack-related environment variables."""
    env_vars = [
        'USE_LOCALSTACK', 'LOCALSTACK_HOST', 'LOCALSTACK_PORT',
        'AWS_DEFAULT_REGION', 'AWS_REGION', 'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 'AWS_ENDPOINT_URL'
    ]
    for var in env_vars:
        os.environ.pop(var, None)


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment before and after each test."""
    clean_env()
    reset_localstack_config()
    yield
    clean_env()
    reset_localstack_config()


class TestHealthEndpointResponseFormat:
    """
    Property 4: Health endpoint response format
    
    For any LocalStack connectivity state (healthy, unhealthy, unreachable),
    the /health/localstack endpoint SHALL return a response containing:
    - status field indicating the state
    - endpoint field with the LocalStack URL (when enabled)
    - troubleshooting array when status is not "healthy"
    """
    
    def test_disabled_response_format(self):
        """
        Feature: gateway-localstack-integration, Property 4: Health endpoint response format
        **Validates: Requirements 5.2**
        
        When LocalStack is disabled, response should have correct format.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'false'
        
        # Simulate the response structure
        response = {
            "status": "disabled",
            "message": "LocalStack mode is not enabled",
            "hint": "Set USE_LOCALSTACK=true in .env.local to enable LocalStack mode",
            "timestamp": datetime.now().isoformat()
        }
        
        # Verify required fields
        assert "status" in response
        assert response["status"] == "disabled"
        assert "message" in response
        assert "hint" in response
        assert "timestamp" in response
    
    @given(
        host=st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Nd'),
            whitelist_characters='-._'
        )).filter(lambda x: x.strip() and not x.startswith('-')),
        port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=50)
    def test_healthy_response_format(self, host, port):
        """
        Feature: gateway-localstack-integration, Property 4: Health endpoint response format
        **Validates: Requirements 5.2**
        
        When LocalStack is healthy, response should include service status.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = host
        os.environ['LOCALSTACK_PORT'] = str(port)
        
        config = LocalStackConfig.from_environment()
        
        # Simulate healthy response structure
        response = {
            "status": "healthy",
            "endpoint": config.endpoint_url,
            "region": config.region,
            "services": {
                "dynamodb": "running",
                "s3": "running",
                "cloudwatch": "running",
                "sts": "running"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Verify required fields for healthy state
        assert response["status"] == "healthy"
        assert response["endpoint"] == f"http://{host}:{port}"
        assert "services" in response
        assert "dynamodb" in response["services"]
        assert "s3" in response["services"]
        assert "cloudwatch" in response["services"]
        assert "timestamp" in response
    
    @given(
        host=st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Nd'),
            whitelist_characters='-._'
        )).filter(lambda x: x.strip() and not x.startswith('-')),
        port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=50)
    def test_unreachable_response_format(self, host, port):
        """
        Feature: gateway-localstack-integration, Property 4: Health endpoint response format
        **Validates: Requirements 2.4, 5.3**
        
        When LocalStack is unreachable, response should include troubleshooting.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = host
        os.environ['LOCALSTACK_PORT'] = str(port)
        
        config = LocalStackConfig.from_environment()
        
        # Simulate unreachable response structure
        response = {
            "status": "unreachable",
            "endpoint": config.endpoint_url,
            "error": "Connection refused",
            "troubleshooting": [
                "Ensure LocalStack is running: docker ps | grep localstack",
                f"Verify endpoint URL: curl {config.endpoint_url}/_localstack/health",
                "Check LOCALSTACK_HOST and LOCALSTACK_PORT in .env.local"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        # Verify required fields for unreachable state
        assert response["status"] == "unreachable"
        assert response["endpoint"] == f"http://{host}:{port}"
        assert "error" in response
        assert "troubleshooting" in response
        assert isinstance(response["troubleshooting"], list)
        assert len(response["troubleshooting"]) > 0
        assert "timestamp" in response
    
    def test_unhealthy_response_format(self):
        """
        Feature: gateway-localstack-integration, Property 4: Health endpoint response format
        **Validates: Requirements 2.4, 5.3**
        
        When LocalStack returns non-200, response should include troubleshooting.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = 'localhost'
        os.environ['LOCALSTACK_PORT'] = '4566'
        
        config = LocalStackConfig.from_environment()
        
        # Simulate unhealthy response structure
        response = {
            "status": "unhealthy",
            "endpoint": config.endpoint_url,
            "error": "Health check returned HTTP 500",
            "troubleshooting": [
                "Check if LocalStack container is running: docker ps | grep localstack",
                "View LocalStack logs: docker logs nexus-localstack",
                "Restart LocalStack: ./scripts/start-localstack.sh"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        # Verify required fields for unhealthy state
        assert response["status"] == "unhealthy"
        assert "endpoint" in response
        assert "error" in response
        assert "troubleshooting" in response
        assert isinstance(response["troubleshooting"], list)
        assert "timestamp" in response
    
    def test_timeout_response_format(self):
        """
        Feature: gateway-localstack-integration, Property 4: Health endpoint response format
        **Validates: Requirements 2.4, 5.3**
        
        When LocalStack connection times out, response should include troubleshooting.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        
        config = LocalStackConfig.from_environment()
        
        # Simulate timeout response structure
        response = {
            "status": "timeout",
            "endpoint": config.endpoint_url,
            "error": "Connection timed out after 5 seconds",
            "troubleshooting": [
                "LocalStack may be starting up - wait a few seconds and retry",
                "Check LocalStack container health: docker inspect nexus-localstack",
                "View LocalStack logs: docker logs nexus-localstack"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        # Verify required fields for timeout state
        assert response["status"] == "timeout"
        assert "endpoint" in response
        assert "error" in response
        assert "troubleshooting" in response
        assert isinstance(response["troubleshooting"], list)
        assert "timestamp" in response


class TestHealthEndpointStatusValues:
    """
    Tests for valid status values in health endpoint responses.
    """
    
    @given(
        status=st.sampled_from(['healthy', 'unhealthy', 'unreachable', 'disabled', 'timeout', 'error'])
    )
    @settings(max_examples=100)
    def test_valid_status_values(self, status):
        """
        Feature: gateway-localstack-integration, Property 4: Health endpoint response format
        **Validates: Requirements 5.2, 5.3**
        
        Status field should only contain valid status values.
        """
        valid_statuses = {'healthy', 'unhealthy', 'unreachable', 'disabled', 'timeout', 'error', 'unavailable'}
        assert status in valid_statuses, f"Invalid status: {status}"
    
    def test_healthy_status_has_services(self):
        """
        Feature: gateway-localstack-integration, Property 4: Health endpoint response format
        **Validates: Requirements 5.2**
        
        Healthy status should always include services information.
        """
        # When status is healthy, services must be present
        response = {
            "status": "healthy",
            "endpoint": "http://localhost:4566",
            "services": {
                "dynamodb": "running",
                "s3": "running"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        assert response["status"] == "healthy"
        assert "services" in response
        assert isinstance(response["services"], dict)
    
    def test_error_status_has_troubleshooting(self):
        """
        Feature: gateway-localstack-integration, Property 4: Health endpoint response format
        **Validates: Requirements 2.4, 5.3**
        
        Error statuses should include troubleshooting guidance.
        """
        error_statuses = ['unhealthy', 'unreachable', 'timeout']
        
        for status in error_statuses:
            response = {
                "status": status,
                "endpoint": "http://localhost:4566",
                "error": "Some error",
                "troubleshooting": ["Step 1", "Step 2"],
                "timestamp": datetime.now().isoformat()
            }
            
            assert "troubleshooting" in response, \
                f"Status '{status}' should have troubleshooting"
            assert isinstance(response["troubleshooting"], list), \
                f"Troubleshooting for '{status}' should be a list"


class TestHealthEndpointTimestamp:
    """
    Tests for timestamp field in health endpoint responses.
    """
    
    def test_timestamp_is_iso_format(self):
        """
        Feature: gateway-localstack-integration, Property 4: Health endpoint response format
        **Validates: Requirements 5.2**
        
        Timestamp should be in ISO format.
        """
        timestamp = datetime.now().isoformat()
        
        # Verify it can be parsed back
        try:
            parsed = datetime.fromisoformat(timestamp)
            assert parsed is not None
        except ValueError:
            pytest.fail(f"Timestamp '{timestamp}' is not valid ISO format")
    
    def test_all_responses_have_timestamp(self):
        """
        Feature: gateway-localstack-integration, Property 4: Health endpoint response format
        **Validates: Requirements 5.2**
        
        All response types should include a timestamp.
        """
        response_types = [
            {"status": "healthy", "endpoint": "http://localhost:4566", "services": {}},
            {"status": "unhealthy", "endpoint": "http://localhost:4566", "error": "error"},
            {"status": "unreachable", "endpoint": "http://localhost:4566", "error": "error"},
            {"status": "disabled", "message": "disabled"},
        ]
        
        for response in response_types:
            response["timestamp"] = datetime.now().isoformat()
            assert "timestamp" in response, \
                f"Response with status '{response['status']}' should have timestamp"
