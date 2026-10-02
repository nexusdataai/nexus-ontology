"""
Property Tests for Service Health Check Consistency

Feature: localstack-test-automation
Property 1: Service Health Check Consistency

For any service (LocalStack or Gateway) and any health check timeout value,
if the service is running and healthy, the health check function SHALL return
true within the timeout period; if the service is not running or unhealthy,
the health check SHALL return false or raise a timeout error.

Validates: Requirements 1.3, 2.2, 1.5, 2.3
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch
import requests

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.localstack_automation.localstack_manager import LocalStackManager
from tests.localstack_automation.gateway_manager import GatewayManager
from tests.localstack_automation.models import ServiceHealth


class TestLocalStackHealthCheckConsistency:
    """Property tests for LocalStack health check consistency."""
    
    @given(
        response_time_ms=st.floats(min_value=1, max_value=5000),
        dynamodb_status=st.sampled_from(["running", "available", "starting", "error"])
    )
    @settings(max_examples=100, deadline=None)
    def test_healthy_localstack_returns_true(self, response_time_ms: float, dynamodb_status: str):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        When LocalStack is running with healthy DynamoDB, is_healthy() returns True.
        """
        with patch('tests.localstack_automation.localstack_manager.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "services": {"dynamodb": dynamodb_status}
            }
            mock_requests.get.return_value = mock_response
            
            manager = LocalStackManager()
            result = manager.is_healthy()
            
            # Should be healthy only if dynamodb is running or available
            expected = dynamodb_status in ("running", "available")
            assert result == expected
    
    @given(
        status_code=st.sampled_from([400, 401, 403, 404, 500, 502, 503]),
    )
    @settings(max_examples=50, deadline=None)
    def test_unhealthy_response_returns_false(self, status_code: int):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        When LocalStack returns non-200 status, is_healthy() returns False.
        """
        with patch('tests.localstack_automation.localstack_manager.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_requests.get.return_value = mock_response
            
            manager = LocalStackManager()
            result = manager.is_healthy()
            
            assert result is False
    
    @given(
        exception_type=st.sampled_from([
            requests.ConnectionError,
            requests.Timeout,
            requests.RequestException
        ])
    )
    @settings(max_examples=30, deadline=None)
    def test_connection_error_returns_false(self, exception_type):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        When connection fails, is_healthy() returns False without raising.
        """
        with patch('tests.localstack_automation.localstack_manager.requests') as mock_requests:
            mock_requests.get.side_effect = exception_type("Connection failed")
            mock_requests.RequestException = requests.RequestException
            
            manager = LocalStackManager()
            result = manager.is_healthy()
            
            assert result is False
    
    @given(
        timeout=st.integers(min_value=1, max_value=120),
        healthy_after_seconds=st.integers(min_value=0, max_value=60)
    )
    @settings(max_examples=50, deadline=None)
    def test_wait_for_health_respects_timeout(self, timeout: int, healthy_after_seconds: int):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        wait_for_health() returns True if healthy within timeout, False otherwise.
        """
        with patch('tests.localstack_automation.localstack_manager.requests') as mock_requests:
            with patch('tests.localstack_automation.localstack_manager.time') as mock_time:
                call_count = [0]
                current_time = [0]
                
                def mock_sleep(seconds):
                    current_time[0] += seconds
                
                def mock_time_func():
                    return current_time[0]
                
                def mock_get(*args, **kwargs):
                    call_count[0] += 1
                    mock_response = MagicMock()
                    
                    # Become healthy after specified seconds
                    if current_time[0] >= healthy_after_seconds:
                        mock_response.status_code = 200
                        mock_response.json.return_value = {"services": {"dynamodb": "running"}}
                    else:
                        mock_response.status_code = 503
                    
                    return mock_response
                
                mock_time.time.side_effect = mock_time_func
                mock_time.sleep.side_effect = mock_sleep
                mock_requests.get.side_effect = mock_get
                mock_requests.RequestException = requests.RequestException
                
                manager = LocalStackManager()
                result = manager.wait_for_health(timeout=timeout)
                
                # Should succeed if healthy_after_seconds < timeout
                expected = healthy_after_seconds < timeout
                assert result == expected


class TestGatewayHealthCheckConsistency:
    """Property tests for Gateway health check consistency."""
    
    @given(
        status=st.sampled_from(["healthy", "ok", "running", "starting", "error", "unhealthy"])
    )
    @settings(max_examples=50, deadline=None)
    def test_gateway_health_status_interpretation(self, status: str):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        Gateway is_healthy() correctly interprets status field.
        """
        with patch('tests.localstack_automation.gateway_manager.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": status}
            mock_requests.get.return_value = mock_response
            
            manager = GatewayManager()
            result = manager.is_healthy()
            
            # Should be healthy only for specific status values
            expected = status in ("healthy", "ok", "running")
            assert result == expected
    
    @given(
        status_code=st.sampled_from([400, 401, 403, 404, 500, 502, 503])
    )
    @settings(max_examples=50, deadline=None)
    def test_gateway_unhealthy_response_returns_false(self, status_code: int):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        When Gateway returns non-200 status, is_healthy() returns False.
        """
        with patch('tests.localstack_automation.gateway_manager.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_requests.get.return_value = mock_response
            
            manager = GatewayManager()
            result = manager.is_healthy()
            
            assert result is False
    
    @given(
        exception_type=st.sampled_from([
            requests.ConnectionError,
            requests.Timeout,
            requests.RequestException
        ])
    )
    @settings(max_examples=30, deadline=None)
    def test_gateway_connection_error_returns_false(self, exception_type):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        When Gateway connection fails, is_healthy() returns False without raising.
        """
        with patch('tests.localstack_automation.gateway_manager.requests') as mock_requests:
            mock_requests.get.side_effect = exception_type("Connection failed")
            mock_requests.RequestException = requests.RequestException
            
            manager = GatewayManager()
            result = manager.is_healthy()
            
            assert result is False


class TestServiceHealthModel:
    """Property tests for ServiceHealth model consistency."""
    
    @given(
        name=st.text(min_size=1, max_size=50),
        healthy=st.booleans(),
        endpoint=st.text(min_size=5, max_size=100),
        response_time=st.floats(min_value=0, max_value=10000, allow_nan=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_service_health_model_consistency(
        self, 
        name: str, 
        healthy: bool, 
        endpoint: str, 
        response_time: float
    ):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        ServiceHealth model correctly stores and returns health information.
        """
        health = ServiceHealth(
            name=name,
            healthy=healthy,
            endpoint=endpoint,
            response_time_ms=response_time
        )
        
        assert health.name == name
        assert health.healthy == healthy
        assert health.endpoint == endpoint
        assert health.response_time_ms == response_time
    
    @given(
        error_message=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=50, deadline=None)
    def test_service_health_with_error(self, error_message: str):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        ServiceHealth correctly stores error information.
        """
        health = ServiceHealth(
            name="TestService",
            healthy=False,
            endpoint="http://localhost:8000",
            error=error_message
        )
        
        assert health.healthy is False
        assert health.error == error_message


class TestGetHealthMethodConsistency:
    """Property tests for get_health() method consistency."""
    
    @given(
        response_time_ms=st.floats(min_value=1, max_value=5000, allow_nan=False)
    )
    @settings(max_examples=50, deadline=None)
    def test_localstack_get_health_returns_service_health(self, response_time_ms: float):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        LocalStackManager.get_health() always returns a ServiceHealth object.
        """
        with patch('tests.localstack_automation.localstack_manager.requests') as mock_requests:
            with patch('tests.localstack_automation.localstack_manager.time') as mock_time:
                mock_time.time.side_effect = [0, response_time_ms / 1000]
                
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"services": {"dynamodb": "running"}}
                mock_requests.get.return_value = mock_response
                
                manager = LocalStackManager()
                health = manager.get_health()
                
                assert isinstance(health, ServiceHealth)
                assert health.name == "LocalStack"
                assert health.endpoint == manager.endpoint
    
    @given(
        response_time_ms=st.floats(min_value=1, max_value=5000, allow_nan=False)
    )
    @settings(max_examples=50, deadline=None)
    def test_gateway_get_health_returns_service_health(self, response_time_ms: float):
        """
        Feature: localstack-test-automation, Property 1: Service Health Check Consistency
        
        GatewayManager.get_health() always returns a ServiceHealth object.
        """
        with patch('tests.localstack_automation.gateway_manager.requests') as mock_requests:
            with patch('tests.localstack_automation.gateway_manager.time') as mock_time:
                mock_time.time.side_effect = [0, response_time_ms / 1000]
                
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "healthy"}
                mock_requests.get.return_value = mock_response
                
                manager = GatewayManager()
                health = manager.get_health()
                
                assert isinstance(health, ServiceHealth)
                assert health.name == "Gateway"
                assert health.endpoint == manager.server_url
