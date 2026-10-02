"""
Property-based tests for Gateway MCP Worker environment inheritance.

Feature: gateway-localstack-integration
Property 3: MCP worker environment inheritance

Tests that MCP workers spawned by the gateway inherit LocalStack environment
variables so that MCP tools can access LocalStack services.

**Validates: Requirements 3.1, 3.2**
"""

import os
import sys
import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from hypothesis import given, strategies as st, settings
from unittest.mock import MagicMock, patch, AsyncMock


def clean_env():
    """Remove LocalStack-related environment variables."""
    env_vars = [
        'USE_LOCALSTACK', 'LOCALSTACK_HOST', 'LOCALSTACK_PORT',
        'AWS_DEFAULT_REGION', 'AWS_REGION', 'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 'AWS_ENDPOINT_URL',
        'AWS_ENDPOINT_URL_DYNAMODB', 'AWS_ENDPOINT_URL_S3',
        'AWS_ENDPOINT_URL_CLOUDWATCH', 'AWS_ENDPOINT_URL_STS'
    ]
    for var in env_vars:
        os.environ.pop(var, None)


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment before and after each test."""
    clean_env()
    yield
    clean_env()


class TestMCPWorkerEnvironmentInheritance:
    """
    Property 3: MCP worker environment inheritance
    
    For any MCP worker spawned by the gateway when LocalStack mode is enabled,
    the worker's environment SHALL contain all LocalStack-related environment
    variables (USE_LOCALSTACK, LOCALSTACK_HOST, LOCALSTACK_PORT, AWS_DEFAULT_REGION).
    """
    
    def _create_mock_worker(self):
        """Create a mock MCPWorker for testing environment preparation."""
        # Import the actual class to test its method
        sys.path.insert(0, project_root)
        
        # We need to import the module to get the MCPWorker class
        # But we'll test the _get_worker_environment method directly
        from mcp_http_gateway import MCPWorker
        
        worker = MCPWorker(worker_id=0, cmd=['python', '-m', 'src.server', '--stdio'])
        return worker
    
    @given(
        host=st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Nd'),
            whitelist_characters='-._'
        )).filter(lambda x: x.strip() and not x.startswith('-')),
        port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=100)
    def test_localstack_vars_passed_to_worker(self, host, port):
        """
        Feature: gateway-localstack-integration, Property 3: MCP worker environment inheritance
        **Validates: Requirements 3.1, 3.2**
        
        When LocalStack mode is enabled, workers should receive all LocalStack
        environment variables.
        """
        clean_env()
        
        # Set LocalStack environment variables
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = host
        os.environ['LOCALSTACK_PORT'] = str(port)
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        os.environ['AWS_ACCESS_KEY_ID'] = 'test'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
        
        try:
            worker = self._create_mock_worker()
            worker_env = worker._get_worker_environment()
            
            # Verify all LocalStack variables are present
            assert worker_env.get('USE_LOCALSTACK') == 'true', \
                "USE_LOCALSTACK should be passed to worker"
            assert worker_env.get('LOCALSTACK_HOST') == host, \
                f"LOCALSTACK_HOST should be '{host}', got '{worker_env.get('LOCALSTACK_HOST')}'"
            assert worker_env.get('LOCALSTACK_PORT') == str(port), \
                f"LOCALSTACK_PORT should be '{port}', got '{worker_env.get('LOCALSTACK_PORT')}'"
            assert worker_env.get('AWS_DEFAULT_REGION') == 'us-east-1', \
                "AWS_DEFAULT_REGION should be passed to worker"
            assert worker_env.get('AWS_ACCESS_KEY_ID') == 'test', \
                "AWS_ACCESS_KEY_ID should be passed to worker"
            assert worker_env.get('AWS_SECRET_ACCESS_KEY') == 'test', \
                "AWS_SECRET_ACCESS_KEY should be passed to worker"
        except ImportError:
            pytest.skip("mcp_http_gateway module not available for import")
    
    @given(
        region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1', 'us-east-1'])
    )
    @settings(max_examples=50)
    def test_aws_region_passed_to_worker(self, region):
        """
        Feature: gateway-localstack-integration, Property 3: MCP worker environment inheritance
        **Validates: Requirements 3.1, 3.2**
        
        AWS region should be correctly passed to worker environment.
        """
        clean_env()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['AWS_DEFAULT_REGION'] = region
        
        try:
            worker = self._create_mock_worker()
            worker_env = worker._get_worker_environment()
            
            assert worker_env.get('AWS_DEFAULT_REGION') == region, \
                f"AWS_DEFAULT_REGION should be '{region}'"
        except ImportError:
            pytest.skip("mcp_http_gateway module not available for import")
    
    def test_service_specific_endpoints_passed(self):
        """
        Feature: gateway-localstack-integration, Property 3: MCP worker environment inheritance
        **Validates: Requirements 3.1, 3.2**
        
        Service-specific endpoint overrides should be passed to workers.
        """
        clean_env()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['AWS_ENDPOINT_URL_DYNAMODB'] = 'http://custom-dynamodb:8000'
        os.environ['AWS_ENDPOINT_URL_S3'] = 'http://custom-s3:9000'
        
        try:
            worker = self._create_mock_worker()
            worker_env = worker._get_worker_environment()
            
            assert worker_env.get('AWS_ENDPOINT_URL_DYNAMODB') == 'http://custom-dynamodb:8000', \
                "AWS_ENDPOINT_URL_DYNAMODB should be passed to worker"
            assert worker_env.get('AWS_ENDPOINT_URL_S3') == 'http://custom-s3:9000', \
                "AWS_ENDPOINT_URL_S3 should be passed to worker"
        except ImportError:
            pytest.skip("mcp_http_gateway module not available for import")
    
    def test_worker_env_includes_system_vars(self):
        """
        Feature: gateway-localstack-integration, Property 3: MCP worker environment inheritance
        **Validates: Requirements 3.1**
        
        Worker environment should include system environment variables
        in addition to LocalStack variables.
        """
        clean_env()
        
        # Set a custom system variable
        os.environ['CUSTOM_VAR'] = 'custom_value'
        os.environ['USE_LOCALSTACK'] = 'true'
        
        try:
            worker = self._create_mock_worker()
            worker_env = worker._get_worker_environment()
            
            # Should include both LocalStack and system vars
            assert worker_env.get('USE_LOCALSTACK') == 'true'
            assert worker_env.get('CUSTOM_VAR') == 'custom_value', \
                "System environment variables should be included"
        except ImportError:
            pytest.skip("mcp_http_gateway module not available for import")
        finally:
            os.environ.pop('CUSTOM_VAR', None)
    
    def test_localstack_disabled_still_passes_vars(self):
        """
        Feature: gateway-localstack-integration, Property 3: MCP worker environment inheritance
        **Validates: Requirements 3.1**
        
        Even when LocalStack is disabled, environment variables should still
        be passed to workers (they just won't use LocalStack endpoints).
        """
        clean_env()
        
        os.environ['USE_LOCALSTACK'] = 'false'
        os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
        
        try:
            worker = self._create_mock_worker()
            worker_env = worker._get_worker_environment()
            
            assert worker_env.get('USE_LOCALSTACK') == 'false'
            assert worker_env.get('AWS_DEFAULT_REGION') == 'us-west-2'
        except ImportError:
            pytest.skip("mcp_http_gateway module not available for import")


class TestWorkerEnvironmentCompleteness:
    """
    Tests for completeness of worker environment variable passing.
    """
    
    def _create_mock_worker(self):
        """Create a mock MCPWorker for testing."""
        try:
            from mcp_http_gateway import MCPWorker
            return MCPWorker(worker_id=0, cmd=['python', '-m', 'src.server', '--stdio'])
        except ImportError:
            return None
    
    def test_all_localstack_vars_defined(self):
        """
        Feature: gateway-localstack-integration, Property 3: MCP worker environment inheritance
        **Validates: Requirements 3.1, 3.2**
        
        The worker should check for all known LocalStack-related variables.
        """
        clean_env()
        
        # Set all possible LocalStack variables
        all_vars = {
            'USE_LOCALSTACK': 'true',
            'LOCALSTACK_HOST': 'localhost',
            'LOCALSTACK_PORT': '4566',
            'AWS_DEFAULT_REGION': 'us-east-1',
            'AWS_REGION': 'us-east-1',
            'AWS_ACCESS_KEY_ID': 'test',
            'AWS_SECRET_ACCESS_KEY': 'test',
            'AWS_ENDPOINT_URL': 'http://localhost:4566',
            'AWS_ENDPOINT_URL_DYNAMODB': 'http://localhost:4566',
            'AWS_ENDPOINT_URL_S3': 'http://localhost:4566',
            'AWS_ENDPOINT_URL_CLOUDWATCH': 'http://localhost:4566',
            'AWS_ENDPOINT_URL_STS': 'http://localhost:4566'
        }
        
        for key, value in all_vars.items():
            os.environ[key] = value
        
        try:
            worker = self._create_mock_worker()
            if worker is None:
                pytest.skip("mcp_http_gateway module not available")
            
            worker_env = worker._get_worker_environment()
            
            # Verify all variables are present
            for key, value in all_vars.items():
                assert worker_env.get(key) == value, \
                    f"Variable {key} should be '{value}', got '{worker_env.get(key)}'"
        except ImportError:
            pytest.skip("mcp_http_gateway module not available for import")
