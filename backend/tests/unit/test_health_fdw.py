"""
Unit tests for FDW health check endpoints.

Tests the /health/fdw endpoint and FDW inclusion in /health/dependencies.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.apis.health_api as health_api_module
from src.apis.health_api import router


@pytest.fixture(autouse=True)
def reset_fdw_services():
    """Reset FDW service references before and after each test."""
    health_api_module._fdw_connection_manager = None
    health_api_module._fdw_discovery_service = None
    yield
    health_api_module._fdw_connection_manager = None
    health_api_module._fdw_discovery_service = None


@pytest.fixture
def client():
    """Create a test client with the health router."""
    app = FastAPI()
    app.include_router(router, prefix="/health")
    return TestClient(app)


class TestFDWHealthEndpoint:
    """Tests for GET /health/fdw."""

    def test_fdw_disabled_returns_disabled_status(self, client):
        """
        **Validates: Requirements 6.5**

        When FDW is not configured, endpoint returns {"status": "disabled"}.
        """
        response = client.get("/health/fdw")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"

    def test_fdw_healthy_returns_healthy_with_latency(self, client):
        """
        **Validates: Requirements 6.1, 6.2**

        When FDW database is reachable, returns healthy status with latency.
        """
        mock_conn_mgr = AsyncMock()
        mock_conn_mgr.health_check.return_value = {
            "status": "healthy",
            "latency_ms": 5.23,
        }

        mock_discovery = AsyncMock()
        mock_discovery.list_foreign_servers.return_value = [
            MagicMock(), MagicMock()
        ]
        mock_discovery.list_foreign_tables.return_value = [
            MagicMock(), MagicMock(), MagicMock()
        ]

        health_api_module._fdw_connection_manager = mock_conn_mgr
        health_api_module._fdw_discovery_service = mock_discovery

        response = client.get("/health/fdw")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["latency_ms"] == 5.23
        assert data["foreign_servers_count"] == 2
        assert data["foreign_tables_count"] == 3

    def test_fdw_unhealthy_returns_unhealthy_with_error(self, client):
        """
        **Validates: Requirements 6.3**

        When FDW database is unreachable, returns unhealthy with error.
        """
        mock_conn_mgr = AsyncMock()
        mock_conn_mgr.health_check.return_value = {
            "status": "unhealthy",
            "latency_ms": None,
            "error": "Connection pool not initialized",
        }

        health_api_module._fdw_connection_manager = mock_conn_mgr

        response = client.get("/health/fdw")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data

    def test_fdw_healthy_without_discovery_service(self, client):
        """
        **Validates: Requirements 6.1, 6.2**

        When healthy but no discovery service, returns healthy without counts.
        """
        mock_conn_mgr = AsyncMock()
        mock_conn_mgr.health_check.return_value = {
            "status": "healthy",
            "latency_ms": 3.1,
        }

        health_api_module._fdw_connection_manager = mock_conn_mgr
        health_api_module._fdw_discovery_service = None

        response = client.get("/health/fdw")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["latency_ms"] == 3.1
        assert "foreign_servers_count" not in data

    def test_fdw_healthy_discovery_error_returns_null_counts(self, client):
        """
        **Validates: Requirements 6.4**

        When healthy but discovery fails, returns healthy with null counts.
        """
        mock_conn_mgr = AsyncMock()
        mock_conn_mgr.health_check.return_value = {
            "status": "healthy",
            "latency_ms": 2.5,
        }

        mock_discovery = AsyncMock()
        mock_discovery.list_foreign_servers.side_effect = Exception("discovery failed")

        health_api_module._fdw_connection_manager = mock_conn_mgr
        health_api_module._fdw_discovery_service = mock_discovery

        response = client.get("/health/fdw")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["foreign_servers_count"] is None
        assert data["foreign_tables_count"] is None

    def test_fdw_health_check_exception_returns_unhealthy(self, client):
        """
        **Validates: Requirements 6.3**

        When health_check raises an exception, returns unhealthy.
        """
        mock_conn_mgr = AsyncMock()
        mock_conn_mgr.health_check.side_effect = Exception("connection lost")

        health_api_module._fdw_connection_manager = mock_conn_mgr

        response = client.get("/health/fdw")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "connection lost" in data["error"]


class TestDependenciesFDWInclusion:
    """Tests for FDW inclusion in /health/dependencies."""

    def test_dependencies_includes_fdw_disabled(self, client):
        """
        **Validates: Requirements 6.6**

        When FDW is disabled, dependencies includes fdw with disabled status.
        """
        response = client.get("/health/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert "fdw" in data["dependencies"]
        assert data["dependencies"]["fdw"]["status"] == "disabled"
        # disabled should not degrade overall status
        assert data["overall_status"] == "healthy"

    def test_dependencies_includes_fdw_healthy(self, client):
        """
        **Validates: Requirements 6.6**

        When FDW is healthy, dependencies includes fdw health result.
        """
        mock_conn_mgr = AsyncMock()
        mock_conn_mgr.health_check.return_value = {
            "status": "healthy",
            "latency_ms": 4.0,
        }

        health_api_module._fdw_connection_manager = mock_conn_mgr

        response = client.get("/health/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert data["dependencies"]["fdw"]["status"] == "healthy"
        assert data["overall_status"] == "healthy"

    def test_dependencies_includes_fdw_unhealthy(self, client):
        """
        **Validates: Requirements 6.6**

        When FDW is unhealthy, dependencies reflects degraded overall status.
        """
        mock_conn_mgr = AsyncMock()
        mock_conn_mgr.health_check.return_value = {
            "status": "unhealthy",
            "error": "Connection refused",
        }

        health_api_module._fdw_connection_manager = mock_conn_mgr

        response = client.get("/health/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert data["dependencies"]["fdw"]["status"] == "unhealthy"
        assert data["overall_status"] == "degraded"

    def test_dependencies_fdw_exception_shows_unhealthy(self, client):
        """
        **Validates: Requirements 6.6**

        When FDW health check throws, dependencies shows unhealthy.
        """
        mock_conn_mgr = AsyncMock()
        mock_conn_mgr.health_check.side_effect = Exception("timeout")

        health_api_module._fdw_connection_manager = mock_conn_mgr

        response = client.get("/health/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert data["dependencies"]["fdw"]["status"] == "unhealthy"
        assert data["overall_status"] == "degraded"


class TestConfigureFDW:
    """Tests for the configure_fdw function."""

    def test_configure_fdw_sets_services(self):
        """Verify configure_fdw sets module-level service references."""
        mock_conn = MagicMock()
        mock_disc = MagicMock()

        health_api_module.configure_fdw(
            connection_manager=mock_conn,
            discovery_service=mock_disc,
        )

        assert health_api_module._fdw_connection_manager is mock_conn
        assert health_api_module._fdw_discovery_service is mock_disc

    def test_configure_fdw_defaults_to_none(self):
        """Verify configure_fdw with no args sets None."""
        health_api_module._fdw_connection_manager = MagicMock()
        health_api_module.configure_fdw()
        assert health_api_module._fdw_connection_manager is None
        assert health_api_module._fdw_discovery_service is None
