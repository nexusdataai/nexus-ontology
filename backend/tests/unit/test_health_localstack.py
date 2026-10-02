"""
Unit tests for LocalStack health endpoint.

Tests the /health/localstack endpoint for various scenarios.

**Validates: Requirements 7.1, 7.4, 7.5**
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def clean_env():
    """Remove LocalStack-related environment variables."""
    env_vars = [
        'USE_LOCALSTACK', 'LOCALSTACK_HOST', 'LOCALSTACK_PORT',
        'AWS_DEFAULT_REGION', 'AWS_REGION', 'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY'
    ]
    for var in env_vars:
        os.environ.pop(var, None)


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment before and after each test."""
    clean_env()
    yield
    clean_env()


class TestLocalStackHealthEndpoint:
    """Tests for /health/localstack endpoint."""
    
    def test_localstack_disabled_returns_disabled_status(self):
        """
        **Validates: Requirements 7.1**
        
        When LocalStack is disabled, endpoint should return disabled status.
        """
        clean_env()
        os.environ['USE_LOCALSTACK'] = 'false'
        
        # Mock the is_localstack_enabled function
        with patch('src.apis.health_api.is_localstack_enabled', return_value=False):
            from src.apis.health_api import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/health")
            client = TestClient(app)
            
            response = client.get("/health/localstack")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "disabled"
            assert "hint" in data
    
    def test_localstack_healthy_returns_healthy_status(self):
        """
        **Validates: Requirements 7.4**
        
        When LocalStack is running and healthy, endpoint should return healthy status.
        """
        clean_env()
        os.environ['USE_LOCALSTACK'] = 'true'
        
        mock_health_result = {
            "enabled": True,
            "healthy": True,
            "endpoint": "http://localhost:4566",
            "region": "us-east-1",
            "services": {
                "dynamodb": "running",
                "s3": "running",
                "cloudwatch": "running"
            }
        }
        
        mock_client_manager = MagicMock()
        mock_client_manager.test_localstack_connection.return_value = mock_health_result
        
        with patch('src.apis.health_api.is_localstack_enabled', return_value=True), \
             patch('src.apis.health_api.get_default_client_manager', return_value=mock_client_manager), \
             patch('src.apis.health_api.HAS_LOCALSTACK', True):
            
            from src.apis.health_api import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/health")
            client = TestClient(app)
            
            response = client.get("/health/localstack")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["endpoint"] == "http://localhost:4566"
            assert "services" in data
    
    def test_localstack_unhealthy_returns_503(self):
        """
        **Validates: Requirements 7.5**
        
        When LocalStack is not accessible, endpoint should return 503 with troubleshooting.
        """
        clean_env()
        os.environ['USE_LOCALSTACK'] = 'true'
        
        mock_health_result = {
            "enabled": True,
            "healthy": False,
            "endpoint": "http://localhost:4566",
            "error": "Connection refused",
            "troubleshooting": [
                "Check if LocalStack is running",
                "Start LocalStack: ./scripts/start-localstack.sh"
            ]
        }
        
        mock_client_manager = MagicMock()
        mock_client_manager.test_localstack_connection.return_value = mock_health_result
        
        with patch('src.apis.health_api.is_localstack_enabled', return_value=True), \
             patch('src.apis.health_api.get_default_client_manager', return_value=mock_client_manager), \
             patch('src.apis.health_api.HAS_LOCALSTACK', True):
            
            from src.apis.health_api import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/health")
            client = TestClient(app)
            
            response = client.get("/health/localstack")
            
            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["status"] == "unhealthy"
            assert "troubleshooting" in data
    
    def test_localstack_exception_returns_503(self):
        """
        **Validates: Requirements 7.5**
        
        When an exception occurs, endpoint should return 503 with error details.
        """
        clean_env()
        os.environ['USE_LOCALSTACK'] = 'true'
        
        mock_client_manager = MagicMock()
        mock_client_manager.test_localstack_connection.side_effect = Exception("Connection error")
        
        with patch('src.apis.health_api.is_localstack_enabled', return_value=True), \
             patch('src.apis.health_api.get_default_client_manager', return_value=mock_client_manager), \
             patch('src.apis.health_api.HAS_LOCALSTACK', True):
            
            from src.apis.health_api import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/health")
            client = TestClient(app)
            
            response = client.get("/health/localstack")
            
            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["status"] == "error"
            assert "troubleshooting" in data
    
    def test_localstack_returns_timestamp(self):
        """
        **Validates: Requirements 7.4**
        
        All responses should include a timestamp.
        """
        clean_env()
        os.environ['USE_LOCALSTACK'] = 'false'
        
        with patch('src.apis.health_api.is_localstack_enabled', return_value=False):
            from src.apis.health_api import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/health")
            client = TestClient(app)
            
            response = client.get("/health/localstack")
            
            assert response.status_code == 200
            data = response.json()
            assert "timestamp" in data
