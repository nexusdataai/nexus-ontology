"""
Unit tests for FDW Discovery Service.

Tests foreign server listing, foreign table listing with optional server filter,
column metadata retrieval, TTL-based caching, and cache refresh.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.config.fdw_config import FDWConfig
from src.models.fdw_models import ColumnInfo, ForeignServerInfo, ForeignTableInfo
from src.services.fdw_connection_manager import PostgreSQLConnectionManager
from src.services.fdw_discovery_service import FDWDiscoveryService, _parse_server_options


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_config(**overrides) -> FDWConfig:
    defaults = dict(
        enabled=True, host="db.test.local", port=5432, database="testdb",
        user="testuser", password="testpass", schema="public", ssl_mode="prefer",
        pool_min=2, pool_max=10, query_timeout=30,
    )
    defaults.update(overrides)
    return FDWConfig(**defaults)


def _make_connection_manager() -> PostgreSQLConnectionManager:
    """Create a connection manager with a mocked engine."""
    config = _make_config()
    mgr = PostgreSQLConnectionManager(config)
    mgr._engine = MagicMock()
    return mgr


def _mock_execute(mgr, return_values):
    """
    Patch get_connection so that conn.execute(...).fetchall() returns
    the given values in sequence (one per call).
    """
    call_idx = [0]

    mock_conn = MagicMock()

    def _execute_side_effect(*args, **kwargs):
        result = MagicMock()
        idx = call_idx[0]
        result.fetchall.return_value = return_values[idx] if idx < len(return_values) else []
        call_idx[0] += 1
        return result

    mock_conn.execute.side_effect = _execute_side_effect

    # Patch get_connection to yield our mock connection
    original_get_connection = mgr.get_connection

    from contextlib import asynccontextmanager
    import asyncio

    @asynccontextmanager
    async def _mock_get_connection():
        yield mock_conn

    mgr.get_connection = _mock_get_connection
    return mock_conn


# ── parse_server_options ─────────────────────────────────────────────────────

class TestParseServerOptions:
    def test_none_returns_empty_dict(self):
        assert _parse_server_options(None) == {}

    def test_empty_list_returns_empty_dict(self):
        assert _parse_server_options([]) == {}

    def test_parses_key_value_pairs(self):
        opts = ["host=salesforce.example.com", "port=443", "protocol=https"]
        result = _parse_server_options(opts)
        assert result == {"host": "salesforce.example.com", "port": "443", "protocol": "https"}

    def test_handles_value_with_equals_sign(self):
        opts = ["connection_string=host=db;port=5432"]
        result = _parse_server_options(opts)
        assert result == {"connection_string": "host=db;port=5432"}

    def test_skips_entries_without_equals(self):
        opts = ["valid=yes", "noequalssign"]
        result = _parse_server_options(opts)
        assert result == {"valid": "yes"}


# ── list_foreign_servers ─────────────────────────────────────────────────────

class TestListForeignServers:
    """Validates: Requirements 3.4"""

    @pytest.mark.asyncio
    async def test_returns_servers_from_pg_catalog(self):
        mgr = _make_connection_manager()
        _mock_execute(mgr, [
            [
                ("salesforce_srv", "multicorn", ["wrapper_class=SalesforceFDW"]),
                ("rest_srv", "multicorn", ["url=https://api.example.com"]),
            ]
        ])
        svc = FDWDiscoveryService(mgr)

        servers = await svc.list_foreign_servers()

        assert len(servers) == 2
        assert servers[0].server_name == "salesforce_srv"
        assert servers[0].wrapper_type == "multicorn"
        assert servers[0].server_options == {"wrapper_class": "SalesforceFDW"}
        assert servers[1].server_name == "rest_srv"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_servers(self):
        mgr = _make_connection_manager()
        _mock_execute(mgr, [[]])
        svc = FDWDiscoveryService(mgr)

        servers = await svc.list_foreign_servers()
        assert servers == []

    @pytest.mark.asyncio
    async def test_handles_none_server_options(self):
        mgr = _make_connection_manager()
        _mock_execute(mgr, [
            [("srv1", "postgres_fdw", None)]
        ])
        svc = FDWDiscoveryService(mgr)

        servers = await svc.list_foreign_servers()
        assert servers[0].server_options == {}


# ── list_foreign_tables ──────────────────────────────────────────────────────

class TestListForeignTables:
    """Validates: Requirements 3.1, 3.2"""

    @pytest.mark.asyncio
    async def test_returns_all_tables_without_filter(self):
        mgr = _make_connection_manager()
        # First call: foreign tables, second call: column counts
        _mock_execute(mgr, [
            [
                ("public", "sf_accounts", "salesforce_srv"),
                ("public", "sf_contacts", "salesforce_srv"),
                ("data", "rest_products", "rest_srv"),
            ],
            [
                ("public", "sf_accounts", 5),
                ("public", "sf_contacts", 3),
                ("data", "rest_products", 8),
            ],
        ])
        svc = FDWDiscoveryService(mgr)

        tables = await svc.list_foreign_tables()

        assert len(tables) == 3
        assert tables[0].schema_name == "public"
        assert tables[0].table_name == "sf_accounts"
        assert tables[0].server_name == "salesforce_srv"
        assert tables[0].column_count == 5
        assert tables[2].column_count == 8

    @pytest.mark.asyncio
    async def test_filters_by_server_name(self):
        mgr = _make_connection_manager()
        _mock_execute(mgr, [
            [("public", "sf_accounts", "salesforce_srv")],
            [("public", "sf_accounts", 5)],
        ])
        svc = FDWDiscoveryService(mgr)

        tables = await svc.list_foreign_tables(server_name="salesforce_srv")

        assert len(tables) == 1
        assert tables[0].server_name == "salesforce_srv"

    @pytest.mark.asyncio
    async def test_returns_zero_column_count_when_no_columns(self):
        mgr = _make_connection_manager()
        _mock_execute(mgr, [
            [("public", "empty_table", "srv1")],
            [],  # no column count rows
        ])
        svc = FDWDiscoveryService(mgr)

        tables = await svc.list_foreign_tables()
        assert tables[0].column_count == 0


# ── get_table_columns ────────────────────────────────────────────────────────

class TestGetTableColumns:
    """Validates: Requirements 3.3"""

    @pytest.mark.asyncio
    async def test_returns_columns_for_table(self):
        mgr = _make_connection_manager()
        _mock_execute(mgr, [
            [
                ("id", "integer", "NO", 1),
                ("name", "text", "YES", 2),
                ("active", "boolean", "YES", 3),
            ]
        ])
        svc = FDWDiscoveryService(mgr)

        columns = await svc.get_table_columns("public", "sf_accounts")

        assert len(columns) == 3
        assert columns[0].column_name == "id"
        assert columns[0].data_type == "integer"
        assert columns[0].is_nullable is False
        assert columns[0].ordinal_position == 1
        assert columns[1].is_nullable is True

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_nonexistent_table(self):
        mgr = _make_connection_manager()
        _mock_execute(mgr, [[]])
        svc = FDWDiscoveryService(mgr)

        columns = await svc.get_table_columns("public", "nonexistent")
        assert columns == []


# ── Caching ──────────────────────────────────────────────────────────────────

class TestCaching:
    """Validates: Requirements 3.5, 3.6"""

    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self):
        mgr = _make_connection_manager()
        mock_conn = _mock_execute(mgr, [
            [("srv1", "multicorn", None)],
        ])
        svc = FDWDiscoveryService(mgr)

        # First call queries the database
        result1 = await svc.list_foreign_servers()
        assert len(result1) == 1

        # Second call should use cache (mock only had 1 set of results)
        result2 = await svc.list_foreign_servers()
        assert result2 == result1

        # execute was called only once
        assert mock_conn.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self):
        mgr = _make_connection_manager()
        mock_conn = _mock_execute(mgr, [
            [("srv1", "multicorn", None)],
            [("srv1", "multicorn", None), ("srv2", "postgres_fdw", None)],
        ])
        svc = FDWDiscoveryService(mgr, cache_ttl=0.1)

        result1 = await svc.list_foreign_servers()
        assert len(result1) == 1

        # Wait for cache to expire
        import asyncio
        await asyncio.sleep(0.15)

        result2 = await svc.list_foreign_servers()
        assert len(result2) == 2
        assert mock_conn.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_refresh_cache_clears_all_entries(self):
        mgr = _make_connection_manager()
        mock_conn = _mock_execute(mgr, [
            [("srv1", "multicorn", None)],
            [("srv1", "multicorn", None)],
        ])
        svc = FDWDiscoveryService(mgr)

        await svc.list_foreign_servers()
        assert mock_conn.execute.call_count == 1

        await svc.refresh_cache()

        await svc.list_foreign_servers()
        assert mock_conn.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_different_server_filters_use_separate_cache_keys(self):
        mgr = _make_connection_manager()
        mock_conn = _mock_execute(mgr, [
            # First call: list_foreign_tables(server_name=None)
            [("public", "t1", "srv1"), ("public", "t2", "srv2")],
            [("public", "t1", 3), ("public", "t2", 5)],
            # Second call: list_foreign_tables(server_name="srv1")
            [("public", "t1", "srv1")],
            [("public", "t1", 3)],
        ])
        svc = FDWDiscoveryService(mgr)

        all_tables = await svc.list_foreign_tables()
        assert len(all_tables) == 2

        filtered = await svc.list_foreign_tables(server_name="srv1")
        assert len(filtered) == 1

        # 4 execute calls total (2 per list_foreign_tables call)
        assert mock_conn.execute.call_count == 4

    @pytest.mark.asyncio
    async def test_configurable_cache_ttl(self):
        mgr = _make_connection_manager()
        _mock_execute(mgr, [[("srv1", "multicorn", None)]])
        svc = FDWDiscoveryService(mgr, cache_ttl=600.0)

        assert svc._cache_ttl == 600.0
