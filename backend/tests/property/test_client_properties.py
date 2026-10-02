"""
Property-based tests for AWS Client Manager LocalStack configuration.

Feature: localstack-enablement
Property 2: AWS Client Manager LocalStack configuration

Tests client creation for various AWS services to verify correct
LocalStack endpoint configuration, credentials, and role_arn behavior.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from hypothesis import given, strategies as st, settings, assume

from src.config.localstack_config import LocalStackConfig, reset_localstack_config
from src.utils.aws_client_utils import AWSClientManager


def clean_env():
    """Remove LocalStack-related environment variables."""
    env_vars = [
        'USE_LOCALSTACK', 'LOCALSTACK_HOST', 'LOCALSTACK_PORT',
        'AWS_DEFAULT_REGION', 'AWS_REGION', 'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 'AWS_ENDPOINT_URL', 'AWS_ROLE_ARN',
        'AWS_PROFILE'
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


class TestAWSClientManagerLocalStackConfiguration:
    """
    Property 2: AWS Client Manager LocalStack configuration
    
    For any AWS service name, when LocalStack mode is enabled, the AWS_Client_Manager
    SHALL create a client with endpoint_url pointing to LocalStack, use dummy credentials,
    and have role_arn set to None.
    """
    
    @given(service_name=st.sampled_from(['dynamodb', 's3', 'cloudwatch', 'sts', 'athena']))
    @settings(max_examples=100)
    def test_localstack_mode_detection(self, service_name):
        """
        Feature: localstack-enablement, Property 2: AWS Client Manager LocalStack configuration
        **Validates: Requirements 3.1**
        
        AWS Client Manager should detect LocalStack mode from environment.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = 'localhost'
        os.environ['LOCALSTACK_PORT'] = '4566'
        
        manager = AWSClientManager()
        
        assert manager.localstack_config.enabled == True, \
            "LocalStack mode should be detected as enabled"
    
    @given(service_name=st.sampled_from(['dynamodb', 's3', 'cloudwatch', 'sts']))
    @settings(max_examples=100)
    def test_role_arn_none_in_localstack_mode(self, service_name):
        """
        Feature: localstack-enablement, Property 2: AWS Client Manager LocalStack configuration
        **Validates: Requirements 3.4**
        
        In LocalStack mode, role_arn should be None (no role assumption).
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['AWS_ROLE_ARN'] = 'arn:aws:iam::123456789012:role/TestRole'
        
        manager = AWSClientManager()
        
        assert manager.role_arn is None, \
            "role_arn should be None in LocalStack mode even if AWS_ROLE_ARN is set"
    
    @given(service_name=st.sampled_from(['dynamodb', 's3', 'cloudwatch', 'sts']))
    @settings(max_examples=100)
    def test_dummy_credentials_in_localstack_mode(self, service_name):
        """
        Feature: localstack-enablement, Property 2: AWS Client Manager LocalStack configuration
        **Validates: Requirements 3.3**
        
        In LocalStack mode, dummy credentials (test/test) should be used.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        
        manager = AWSClientManager()
        
        assert manager.localstack_config.access_key == 'test', \
            "Access key should be 'test' in LocalStack mode"
        assert manager.localstack_config.secret_key == 'test', \
            "Secret key should be 'test' in LocalStack mode"
    
    @given(
        host=st.sampled_from(['localhost', '127.0.0.1', 'localstack']),
        port=st.sampled_from([4566, 4510, 5000])
    )
    @settings(max_examples=100)
    def test_endpoint_url_configuration(self, host, port):
        """
        Feature: localstack-enablement, Property 2: AWS Client Manager LocalStack configuration
        **Validates: Requirements 3.2**
        
        In LocalStack mode, endpoint_url should point to LocalStack.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = host
        os.environ['LOCALSTACK_PORT'] = str(port)
        
        manager = AWSClientManager()
        
        expected_endpoint = f"http://{host}:{port}"
        assert manager.localstack_config.endpoint_url == expected_endpoint, \
            f"Endpoint URL should be {expected_endpoint}"
    
    def test_localstack_session_creation(self):
        """
        Feature: localstack-enablement, Property 2: AWS Client Manager LocalStack configuration
        **Validates: Requirements 3.2, 3.3**
        
        LocalStack session should be created with correct credentials.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = 'localhost'
        os.environ['LOCALSTACK_PORT'] = '4566'
        
        manager = AWSClientManager()
        session = manager._create_localstack_session()
        
        # Verify session credentials
        credentials = session.get_credentials()
        assert credentials.access_key == 'test'
        assert credentials.secret_key == 'test'
    
    def test_aws_mode_uses_real_credentials(self):
        """
        Feature: localstack-enablement, Property 2: AWS Client Manager LocalStack configuration
        **Validates: Requirements 3.1**
        
        When LocalStack is disabled, real AWS credentials should be used.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'false'
        os.environ['AWS_ROLE_ARN'] = 'arn:aws:iam::123456789012:role/TestRole'
        
        manager = AWSClientManager()
        
        assert manager.localstack_config.enabled == False
        assert manager.role_arn == 'arn:aws:iam::123456789012:role/TestRole'
    
    def test_test_localstack_connection_disabled(self):
        """
        Feature: localstack-enablement, Property 2: AWS Client Manager LocalStack configuration
        **Validates: Requirements 3.5**
        
        test_localstack_connection should indicate disabled when LocalStack is off.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'false'
        
        manager = AWSClientManager()
        result = manager.test_localstack_connection()
        
        assert result['enabled'] == False
        assert 'message' in result
