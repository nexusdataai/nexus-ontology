"""
Unit tests for FDW lifecycle management module.

Tests initialization and shutdown of FDW services, including
graceful degradation when FDW is disabled or initialization fails.

**Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5**
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.fdw_lifecycle as lifecycle_module


@pytest.fixture(autouse=True)
def reset_lifecycle_globals():
    """Reset module-level service instances before and after each test."""
    lifecycle_module._connection_manager = None
    lifecycle_module._discovery_service = None
    lifecycle_module._query_service = None
    yield
    lifecycle_module._connection_manager = None
    lifecycle_module._discovery_service = None
    lifecycle_module._query_service = None


class TestInitializeFDWDisabled:
    """Tests for initialize_fdw when FDW is disabled."""

    @pytest.mark.asyncio
    async def test_returns_false_when_disabled(self):
        """
        **Validates: Requirements 13.5**

        When FDW_PG_HOST is not set, initialize_fdw returns False
        and no services are created.
        """
        with patch("src.config.fdw_config.is_fdw_enabled", return_value=False):
            result = await lifecycle_module.initialize_fdw()

        assert result is False
        assert lifecycle_module._connection_manager is None
        assert lifecycle_module._discovery_service is None

    @pytest.mark.asyncio
    async def test_does_not_affect_existing_operation(self):
        """
        **Validates: Requirements 13.5**

        When FDW is disabled, no exceptions are raised and no
        services are initialized — existing backend is unaffected.
        """
        with patch("src.config.fdw_config.is_fdw_enabled", return_value=False):
            result = await lifecycle_module.initialize_fdw()

        assert result is False
        assert lifecycle_module._query_service is None


class TestInitializeFDWEnabled:
    """Tests for initialize_fdw when FDW is enabled."""

    def _make_config(self):
        """Create a mock FDWConfig."""
        config = MagicMock()
        config.host = "localhost"
        config.port = 5432
        config.database = "testdb"
        return config

    @pytest.mark.asyncio
    async def test_returns_true_when_enabled(self):
        """
        **Validates: Requirements 13.1, 13.3**

        When FDW is enabled, all services are initialized and
        API modules are configured.
        """
        mock_config = self._make_config()
        mock_conn_mgr = AsyncMock()
        mock_discovery = MagicMock()
        mock_query = MagicMock()
        mock_fdw_api = MagicMock()
        mock_health_api = MagicMock()

        with patch("src.config.fdw_config.is_fdw_enabled", return_value=True), \
             patch("src.config.fdw_config.get_fdw_config", return_value=mock_config), \
             patch("src.services.fdw_connection_manager.PostgreSQLConnectionManager", return_value=mock_conn_mgr), \
             patch("src.services.fdw_discovery_service.FDWDiscoveryService", return_value=mock_discovery), \
             patch("src.services.fdw_query_service.FDWQueryService", return_value=mock_query), \
             patch.dict("sys.modules", {
                 "src.apis.fdw_api": mock_fdw_api,
                 "src.apis.health_api": mock_health_api,
             }), \
             patch("src.apis.fdw_api", mock_fdw_api, create=True), \
             patch("src.apis.health_api", mock_health_api, create=True):

            result = await lifecycle_module.initialize_fdw()

        assert result is True
        mock_conn_mgr.initialize.assert_awaited_once()


class TestInitializeFDWErrorHandling:
    """Tests for initialize_fdw error handling."""

    @pytest.mark.asyncio
    async def test_returns_false_on_initialization_error(self):
        """
        **Validates: Requirements 13.5**

        When initialization fails, returns False (degraded mode)
        instead of crashing the backend.
        """
        mock_config = MagicMock()
        mock_config.host = "localhost"
        mock_config.port = 5432
        mock_config.database = "testdb"

        mock_conn_mgr = AsyncMock()
        mock_conn_mgr.initialize.side_effect = Exception("Connection refused")

        with patch("src.config.fdw_config.is_fdw_enabled", return_value=True), \
             patch("src.config.fdw_config.get_fdw_config", return_value=mock_config), \
             patch("src.services.fdw_connection_manager.PostgreSQLConnectionManager", return_value=mock_conn_mgr), \
             patch("src.apis.health_api", MagicMock(), create=True):

            result = await lifecycle_module.initialize_fdw()

        assert result is False

    @pytest.mark.asyncio
    async def test_configures_health_api_in_degraded_mode(self):
        """
        **Validates: Requirements 13.5**

        When initialization fails after connection manager is created,
        health API is still configured so it can report degraded status.
        """
        mock_config = MagicMock()
        mock_config.host = "localhost"
        mock_config.port = 5432
        mock_config.database = "testdb"

        mock_conn_mgr = AsyncMock()
        mock_health_api = MagicMock()

        with patch("src.config.fdw_config.is_fdw_enabled", return_value=True), \
             patch("src.config.fdw_config.get_fdw_config", return_value=mock_config), \
             patch("src.services.fdw_connection_manager.PostgreSQLConnectionManager", return_value=mock_conn_mgr), \
             patch("src.services.fdw_discovery_service.FDWDiscoveryService", side_effect=Exception("Discovery init failed")), \
             patch("src.apis.health_api", mock_health_api, create=True):

            result = await lifecycle_module.initialize_fdw()

        assert result is False
        mock_health_api.configure_fdw.assert_called_once_with(
            connection_manager=mock_conn_mgr
        )


class TestShutdownFDW:
    """Tests for shutdown_fdw."""

    @pytest.mark.asyncio
    async def test_shutdown_when_not_initialized(self):
        """
        **Validates: Requirements 13.2**

        Calling shutdown when FDW was never initialized does not raise.
        """
        assert lifecycle_module._connection_manager is None
        await lifecycle_module.shutdown_fdw()

    @pytest.mark.asyncio
    async def test_shutdown_closes_connection_pool(self):
        """
        **Validates: Requirements 13.2**

        When initialized, shutdown calls close() on the connection manager.
        """
        mock_conn_mgr = AsyncMock()
        lifecycle_module._connection_manager = mock_conn_mgr

        await lifecycle_module.shutdown_fdw()

        mock_conn_mgr.close.assert_awaited_once()
        assert lifecycle_module._connection_manager is None

    @pytest.mark.asyncio
    async def test_shutdown_handles_close_error(self):
        """
        **Validates: Requirements 13.2**

        When close() raises, shutdown logs warning but doesn't crash.
        """
        mock_conn_mgr = AsyncMock()
        mock_conn_mgr.close.side_effect = Exception("Close failed")
        lifecycle_module._connection_manager = mock_conn_mgr

        await lifecycle_module.shutdown_fdw()

        assert lifecycle_module._connection_manager is None
