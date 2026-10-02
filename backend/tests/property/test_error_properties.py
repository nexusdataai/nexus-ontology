"""
Property-based tests for error handling with descriptive messages.

Feature: localstack-enablement
Property 4: Error handling with descriptive messages

Tests connection failure scenarios to verify error type and message content.

**Validates: Requirements 3.6, 12.1, 12.2**
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from hypothesis import given, strategies as st, settings

from src.config.localstack_config import reset_localstack_config
from src.utils.localstack_errors import (
    LocalStackError,
    LocalStackConnectionError,
    LocalStackServiceError,
    LocalStackInitializationError,
    LocalStackConfigurationError
)


def clean_env():
    """Remove LocalStack-related environment variables."""
    env_vars = [
        'USE_LOCALSTACK', 'LOCALSTACK_HOST', 'LOCALSTACK_PORT',
        'AWS_DEFAULT_REGION', 'AWS_REGION', 'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 'AWS_ENDPOINT_URL', 'AWS_ROLE_ARN'
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


class TestErrorHandlingWithDescriptiveMessages:
    """
    Property 4: Error handling with descriptive messages
    
    For any LocalStack connection failure scenario, the error raised SHALL
    be of appropriate type, contain the endpoint URL, contain the underlying
    error message, and provide troubleshooting guidance.
    """
    
    @given(
        endpoint=st.sampled_from([
            'http://localhost:4566',
            'http://127.0.0.1:4566',
            'http://localstack:4566',
            'http://custom-host:5000'
        ])
    )
    @settings(max_examples=100)
    def test_connection_error_contains_endpoint(self, endpoint):
        """
        Feature: localstack-enablement, Property 4: Error handling with descriptive messages
        **Validates: Requirements 3.6, 12.1**
        
        LocalStackConnectionError should contain the endpoint URL.
        """
        original_error = ConnectionRefusedError("Connection refused")
        error = LocalStackConnectionError(endpoint=endpoint, original_error=original_error)
        
        assert endpoint in str(error), \
            f"Error message should contain endpoint '{endpoint}'"
        assert error.endpoint == endpoint
    
    @given(
        error_message=st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
    )
    @settings(max_examples=100)
    def test_connection_error_contains_original_error(self, error_message):
        """
        Feature: localstack-enablement, Property 4: Error handling with descriptive messages
        **Validates: Requirements 12.1**
        
        LocalStackConnectionError should contain the original error message.
        """
        original_error = Exception(error_message)
        error = LocalStackConnectionError(
            endpoint='http://localhost:4566',
            original_error=original_error
        )
        
        assert error_message in str(error), \
            f"Error message should contain original error '{error_message}'"
        assert error.original_error == original_error
    
    def test_connection_error_has_troubleshooting(self):
        """
        Feature: localstack-enablement, Property 4: Error handling with descriptive messages
        **Validates: Requirements 12.1**
        
        LocalStackConnectionError should provide troubleshooting guidance.
        """
        error = LocalStackConnectionError(
            endpoint='http://localhost:4566',
            original_error=Exception("Connection refused")
        )
        
        error_str = str(error)
        assert 'Troubleshooting' in error_str, \
            "Error should contain troubleshooting section"
        assert 'docker' in error_str.lower(), \
            "Troubleshooting should mention Docker"
    
    @given(
        service=st.sampled_from(['dynamodb', 's3', 'cloudwatch', 'sts', 'athena']),
        status=st.sampled_from(['unavailable', 'error', 'starting', 'stopped'])
    )
    @settings(max_examples=100)
    def test_service_error_contains_service_info(self, service, status):
        """
        Feature: localstack-enablement, Property 4: Error handling with descriptive messages
        **Validates: Requirements 12.2**
        
        LocalStackServiceError should contain service name and status.
        """
        error = LocalStackServiceError(service=service, status=status)
        
        error_str = str(error)
        assert service in error_str, \
            f"Error should contain service name '{service}'"
        assert status in error_str, \
            f"Error should contain status '{status}'"
        assert error.service == service
        assert error.status == status
    
    def test_service_error_has_troubleshooting(self):
        """
        Feature: localstack-enablement, Property 4: Error handling with descriptive messages
        **Validates: Requirements 12.2**
        
        LocalStackServiceError should provide troubleshooting guidance.
        """
        error = LocalStackServiceError(service='dynamodb', status='unavailable')
        
        error_str = str(error)
        assert 'Troubleshooting' in error_str
        assert len(error.troubleshooting) > 0
    
    @given(
        resource_type=st.sampled_from(['DynamoDB table', 'S3 bucket', 'CloudWatch log group']),
        resource_name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Nd'),
            whitelist_characters='-_'
        )).filter(lambda x: x.strip())
    )
    @settings(max_examples=100)
    def test_initialization_error_contains_resource_info(self, resource_type, resource_name):
        """
        Feature: localstack-enablement, Property 4: Error handling with descriptive messages
        **Validates: Requirements 12.1**
        
        LocalStackInitializationError should contain resource type and name.
        """
        error = LocalStackInitializationError(
            resource_type=resource_type,
            resource_name=resource_name,
            original_error=Exception("Resource creation failed")
        )
        
        error_str = str(error)
        assert resource_type in error_str
        assert resource_name in error_str
        assert error.resource_type == resource_type
        assert error.resource_name == resource_name
    
    def test_configuration_error_contains_config_info(self):
        """
        Feature: localstack-enablement, Property 4: Error handling with descriptive messages
        **Validates: Requirements 12.1**
        
        LocalStackConfigurationError should contain config key and value.
        """
        error = LocalStackConfigurationError(
            config_key='LOCALSTACK_PORT',
            config_value='invalid',
            reason='Port must be a number'
        )
        
        error_str = str(error)
        assert 'LOCALSTACK_PORT' in error_str
        assert 'invalid' in error_str
        assert 'Port must be a number' in error_str
    
    def test_all_errors_inherit_from_base(self):
        """
        Feature: localstack-enablement, Property 4: Error handling with descriptive messages
        **Validates: Requirements 3.6**
        
        All LocalStack errors should inherit from LocalStackError.
        """
        errors = [
            LocalStackConnectionError('http://localhost:4566', Exception("test")),
            LocalStackServiceError('dynamodb', 'unavailable'),
            LocalStackInitializationError('table', 'test', Exception("test")),
            LocalStackConfigurationError('key', 'value', 'reason')
        ]
        
        for error in errors:
            assert isinstance(error, LocalStackError), \
                f"{type(error).__name__} should inherit from LocalStackError"
            assert isinstance(error, Exception), \
                f"{type(error).__name__} should be an Exception"
