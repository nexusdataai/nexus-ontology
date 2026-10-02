"""
Property-based tests for LocalStack configuration.

Feature: localstack-enablement
Property 1: Configuration endpoint mode detection

Tests various combinations of USE_LOCALSTACK, LOCALSTACK_HOST, LOCALSTACK_PORT
to verify correct endpoint mode detection.

**Validates: Requirements 2.1, 2.2, 2.3, 2.5**
"""

import os
import sys
import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from hypothesis import given, strategies as st, settings, assume
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


class TestConfigurationEndpointModeDetection:
    """
    Property 1: Configuration endpoint mode detection
    
    For any combination of environment variable settings, the LocalStackConfig
    class SHALL correctly determine whether LocalStack mode is enabled and
    construct the correct endpoint URL.
    """
    
    @given(
        use_localstack=st.sampled_from(['true', 'false', 'TRUE', 'FALSE', 'True', 'False', '', 'yes', 'no']),
    )
    @settings(max_examples=100)
    def test_localstack_enabled_detection(self, use_localstack):
        """
        Feature: localstack-enablement, Property 1: Configuration endpoint mode detection
        **Validates: Requirements 2.1**
        
        LocalStack should only be enabled when USE_LOCALSTACK is exactly 'true' (case-insensitive).
        """
        clean_env()
        reset_localstack_config()
        
        if use_localstack:
            os.environ['USE_LOCALSTACK'] = use_localstack
        
        config = LocalStackConfig.from_environment()
        
        # LocalStack should only be enabled for 'true' (case-insensitive)
        expected_enabled = use_localstack.lower().strip() == 'true' if use_localstack else False
        assert config.enabled == expected_enabled, \
            f"Expected enabled={expected_enabled} for USE_LOCALSTACK='{use_localstack}', got {config.enabled}"
    
    @given(
        host=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Nd'),
            whitelist_characters='-._'
        )).filter(lambda x: x.strip() and not x.startswith('-')),
        port=st.integers(min_value=1, max_value=65535)
    )
    @settings(max_examples=100)
    def test_endpoint_url_construction(self, host, port):
        """
        Feature: localstack-enablement, Property 1: Configuration endpoint mode detection
        **Validates: Requirements 2.5**
        
        For any valid host and port, the endpoint URL should be correctly constructed.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = host
        os.environ['LOCALSTACK_PORT'] = str(port)
        
        config = LocalStackConfig.from_environment()
        
        assert config.enabled == True
        assert config.host == host.strip()
        assert config.port == port
        assert config.endpoint_url == f"http://{host.strip()}:{port}"
    
    @given(
        region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-south-1', 'sa-east-1'])
    )
    @settings(max_examples=100)
    def test_region_configuration(self, region):
        """
        Feature: localstack-enablement, Property 1: Configuration endpoint mode detection
        **Validates: Requirements 2.2, 2.3**
        
        Region should be correctly read from environment.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['AWS_DEFAULT_REGION'] = region
        
        config = LocalStackConfig.from_environment()
        
        assert config.region == region
    
    @given(
        service=st.sampled_from(['dynamodb', 's3', 'cloudwatch', 'sts', 'athena'])
    )
    @settings(max_examples=100)
    def test_service_endpoint_in_localstack_mode(self, service):
        """
        Feature: localstack-enablement, Property 1: Configuration endpoint mode detection
        **Validates: Requirements 2.2, 2.6**
        
        When LocalStack is enabled, all services should use the LocalStack endpoint.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = 'localhost'
        os.environ['LOCALSTACK_PORT'] = '4566'
        
        config = LocalStackConfig.from_environment()
        
        endpoint = config.get_service_endpoint(service)
        assert endpoint == 'http://localhost:4566', \
            f"Expected LocalStack endpoint for {service}, got {endpoint}"
    
    @given(
        service=st.sampled_from(['dynamodb', 's3', 'cloudwatch', 'sts', 'athena'])
    )
    @settings(max_examples=100)
    def test_service_endpoint_in_aws_mode(self, service):
        """
        Feature: localstack-enablement, Property 1: Configuration endpoint mode detection
        **Validates: Requirements 2.3**
        
        When LocalStack is disabled, service endpoints should be None (use AWS defaults).
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'false'
        
        config = LocalStackConfig.from_environment()
        
        endpoint = config.get_service_endpoint(service)
        assert endpoint is None, \
            f"Expected None endpoint for {service} in AWS mode, got {endpoint}"
    
    def test_default_values_when_not_set(self):
        """
        Feature: localstack-enablement, Property 1: Configuration endpoint mode detection
        **Validates: Requirements 2.1, 2.5**
        
        Default values should be used when environment variables are not set.
        """
        clean_env()
        reset_localstack_config()
        
        config = LocalStackConfig.from_environment()
        
        assert config.enabled == False
        assert config.host == 'localhost'
        assert config.port == 4566
        assert config.region == 'us-east-1'
    
    def test_dummy_credentials_in_localstack_mode(self):
        """
        Feature: localstack-enablement, Property 1: Configuration endpoint mode detection
        **Validates: Requirements 2.7**
        
        In LocalStack mode, dummy credentials should be used.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        
        config = LocalStackConfig.from_environment()
        
        assert config.access_key == 'test'
        assert config.secret_key == 'test'
    
    def test_service_endpoint_override(self):
        """
        Feature: localstack-enablement, Property 1: Configuration endpoint mode detection
        **Validates: Requirements 2.6**
        
        Service-specific endpoint overrides should be respected.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['AWS_ENDPOINT_URL_DYNAMODB'] = 'http://custom-dynamodb:8000'
        
        config = LocalStackConfig.from_environment()
        
        # DynamoDB should use override
        assert config.get_service_endpoint('dynamodb') == 'http://custom-dynamodb:8000'
        # Other services should use LocalStack endpoint
        assert config.get_service_endpoint('s3') == config.endpoint_url
