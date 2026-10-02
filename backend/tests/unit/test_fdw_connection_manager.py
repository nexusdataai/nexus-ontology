"""
Unit tests for PostgreSQL Connection Manager.

Tests retry logic, graceful degradation, context manager acquire/release,
health checks, and close behavior.

**Validates: Requirements 2.3, 2.4, 2.5, 2.6**
"""

import pytest
from unittest.mock import MagicMock, patch, call

from src.config.fdw_config import FDWConfig
from src.services.fdw_connection_manager import PostgreSQLConnectionManager
from src.utils.fdw_errors import FDWConnectionError


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_config(**overrides) -> FDWConfig:
    """Create a valid FDWConfig for testing."""
    defaults = dict(
        enabled=True,
        host="db.test.local",
        port=5432,
        database="testdb",
        user="testuser",
        password="testpass",
        schema="public",
        ssl_mode="prefer",
        pool_min=2,
        pool_max=10,
        query_timeout=30,
    )
    defaults.update(overrides)
    return FDWConfig(**defaults)


# ── Retry Logic ──────────────────────────────────────────────────────────────

class TestInitializeRetry:
    """Tests for initialize() retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self):
        """Validates: Requirement 2.3 — successful connection on first try."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)

        mock_engine = MagicMock()
        with patch.object(mgr, "_create_engine", return_value=mock_engine) as mock_create, \
             patch.object(mgr, "_test_connection") as mock_test, \
             patch("asyncio.sleep") as mock_sleep:
            await mgr.initialize()

        assert mgr.engine is mock_engine
        mock_create.assert_called_once()
        mock_test.assert_called_once_with(mock_engine)
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        """Validates: Requirement 2.3 — retries with backoff, succeeds on attempt 2."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)

        mock_engine = MagicMock()
        call_count = 0

        def _create_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("refused")
            return mock_engine

        with patch.object(mgr, "_create_engine", side_effect=_create_side_effect), \
             patch.object(mgr, "_test_connection"), \
             patch("asyncio.sleep") as mock_sleep:
            await mgr.initialize()

        assert mgr.engine is mock_engine
        # Should have slept once (1s backoff after first failure)
        mock_sleep.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_retries_on_test_connection_failure(self):
        """Validates: Requirement 2.3 — retries when _test_connection fails."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)

        mock_engine = MagicMock()
        test_call_count = 0

        def _test_side_effect(engine):
            nonlocal test_call_count
            test_call_count += 1
            if test_call_count <= 2:
                raise ConnectionError("cannot reach db")

        with patch.object(mgr, "_create_engine", return_value=mock_engine), \
             patch.object(mgr, "_test_connection", side_effect=_test_side_effect), \
             patch("asyncio.sleep") as mock_sleep:
            await mgr.initialize()

        assert mgr.engine is mock_engine
        # Slept twice: 1s after attempt 1, 2s after attempt 2
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)


# ── Degraded Mode ────────────────────────────────────────────────────────────

class TestDegradedMode:
    """Tests for graceful degradation when database is unreachable."""

    @pytest.mark.asyncio
    async def test_engine_none_after_all_retries_exhausted(self):
        """Validates: Requirement 2.6 — degraded mode after all retries fail."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)

        with patch.object(mgr, "_create_engine", side_effect=ConnectionError("refused")), \
             patch("asyncio.sleep"):
            await mgr.initialize()

        assert mgr.engine is None

    @pytest.mark.asyncio
    async def test_get_connection_raises_when_degraded(self):
        """Validates: Requirement 2.6 — get_connection raises FDWConnectionError in degraded mode."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)
        # engine is None by default (not initialized)

        with pytest.raises(FDWConnectionError) as exc_info:
            async with mgr.get_connection():
                pass  # pragma: no cover

        assert "not initialized" in str(exc_info.value).lower()
        assert exc_info.value.host == "db.test.local"
        assert exc_info.value.port == 5432


# ── Context Manager ──────────────────────────────────────────────────────────

class TestGetConnection:
    """Tests for the get_connection() async context manager."""

    @pytest.mark.asyncio
    async def test_yields_connection_and_closes(self):
        """Validates: Requirement 2.4 — acquire and release connection."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)

        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        mgr._engine = mock_engine

        async with mgr.get_connection() as conn:
            assert conn is mock_conn

        # Connection should be closed after exiting context
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_connection_on_exception(self):
        """Validates: Requirement 2.4 — connection released even on error."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)

        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        mgr._engine = mock_engine

        with pytest.raises(ValueError):
            async with mgr.get_connection() as conn:
                raise ValueError("something broke")

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_fdw_connection_error_on_connect_failure(self):
        """Validates: Requirement 2.4 — wraps connection errors."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)

        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("pool exhausted")
        mgr._engine = mock_engine

        with pytest.raises(FDWConnectionError) as exc_info:
            async with mgr.get_connection():
                pass  # pragma: no cover

        assert "pool exhausted" in str(exc_info.value)
        assert exc_info.value.original_error is not None


# ── Health Check ─────────────────────────────────────────────────────────────

class TestHealthCheck:
    """Tests for health_check() method."""

    @pytest.mark.asyncio
    async def test_healthy_when_select_1_succeeds(self):
        """Validates: Requirement 2.4 — health check returns healthy with latency."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)

        mock_conn = MagicMock()
        mock_conn.execute = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        mgr._engine = mock_engine

        result = await mgr.health_check()

        assert result["status"] == "healthy"
        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], float)

    @pytest.mark.asyncio
    async def test_unhealthy_when_engine_is_none(self):
        """Validates: Requirement 2.6 — unhealthy when not initialized."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)
        # engine is None

        result = await mgr.health_check()

        assert result["status"] == "unhealthy"
        assert result["latency_ms"] is None
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unhealthy_when_query_fails(self):
        """Validates: Requirement 2.4 — unhealthy when SELECT 1 fails."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)

        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("connection lost")
        mgr._engine = mock_engine

        result = await mgr.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result


# ── Close ────────────────────────────────────────────────────────────────────

class TestClose:
    """Tests for close() method."""

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self):
        """Validates: Requirement 2.5 — close disposes engine and sets to None."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)

        mock_engine = MagicMock()
        mgr._engine = mock_engine

        await mgr.close()

        mock_engine.dispose.assert_called_once()
        assert mgr.engine is None

    @pytest.mark.asyncio
    async def test_close_noop_when_engine_is_none(self):
        """Validates: Requirement 2.5 — close is safe when already None."""
        config = _make_config()
        mgr = PostgreSQLConnectionManager(config)
        # engine is None

        await mgr.close()  # Should not raise
        assert mgr.engine is None
