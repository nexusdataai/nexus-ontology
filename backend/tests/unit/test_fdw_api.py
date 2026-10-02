"""
Unit tests for FDW API endpoints.

Tests all FDW discovery/query endpoints using FastAPI TestClient with
mocked service dependencies. Covers enabled/disabled states, error
handling, and correct HTTP status codes.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7**
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.apis import fdw_api
from src.models.fdw_models import (
    ColumnInfo,
    ForeignServerInfo,
    ForeignTableInfo,
    QueryMetadata,
    QueryResponse,
)
from src.utils.fdw_errors import (
    FDWConnectionError,
    FDWQueryError,
    FDWTableNotFoundError,
    FDWTimeoutError,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _create_app() -> FastAPI:
    """Create a fresh FastAPI app with the FDW router."""
    app = FastAPI()
    app.include_router(fdw_api.router)
    return app


def _configure_enabled(discovery=None, query=None):
    """Configure fdw_api with mock services (FDW enabled)."""
    conn_mgr = MagicMock()
    fdw_api.configure(
        connection_manager=conn_mgr,
        discovery_service=discovery or AsyncMock(),
        query_service=query or AsyncMock(),
    )
    return conn_mgr


def _configure_disabled():
    """Configure fdw_api as disabled (no connection manager)."""
    fdw_api.configure(
        connection_manager=None,
        discovery_service=None,
        query_service=None,
    )


# ── Disabled FDW tests ───────────────────────────────────────────────────────

class TestDisabledFDW:
    """All endpoints return 503 when FDW is not configured."""

    def setup_method(self):
        _configure_disabled()
        self.app = _create_app()
        self.client = TestClient(self.app)

    def test_servers_returns_503(self):
        resp = self.client.get("/api/fdw/servers")
        assert resp.status_code == 503
        assert "FDW integration is not configured" in resp.json()["detail"]["error"]

    def test_tables_returns_503(self):
        resp = self.client.get("/api/fdw/tables")
        assert resp.status_code == 503

    def test_columns_returns_503(self):
        resp = self.client.get("/api/fdw/tables/public/test_table/columns")
        assert resp.status_code == 503

    def test_query_returns_503(self):
        resp = self.client.post("/api/fdw/query", json={"table": "test"})
        assert resp.status_code == 503


# ── GET /servers tests ───────────────────────────────────────────────────────

class TestListServers:

    def setup_method(self):
        self.discovery = AsyncMock()
        _configure_enabled(discovery=self.discovery)
        self.app = _create_app()
        self.client = TestClient(self.app)

    def test_returns_servers(self):
        self.discovery.list_foreign_servers.return_value = [
            ForeignServerInfo(server_name="sf_server", wrapper_type="multicorn2", server_options={"host": "sf.com"}),
            ForeignServerInfo(server_name="rest_server", wrapper_type="multicorn2", server_options={}),
        ]
        resp = self.client.get("/api/fdw/servers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["serverName"] == "sf_server"
        assert data[1]["serverName"] == "rest_server"

    def test_returns_empty_list(self):
        self.discovery.list_foreign_servers.return_value = []
        resp = self.client.get("/api/fdw/servers")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_connection_error_returns_502(self):
        self.discovery.list_foreign_servers.side_effect = FDWConnectionError(
            "Connection refused", host="db.local", port=5432
        )
        resp = self.client.get("/api/fdw/servers")
        assert resp.status_code == 502
        assert "FDW database connection failed" in resp.json()["detail"]["error"]

    def test_unexpected_error_returns_500(self):
        self.discovery.list_foreign_servers.side_effect = RuntimeError("boom")
        resp = self.client.get("/api/fdw/servers")
        assert resp.status_code == 500


# ── GET /tables tests ────────────────────────────────────────────────────────

class TestListTables:

    def setup_method(self):
        self.discovery = AsyncMock()
        _configure_enabled(discovery=self.discovery)
        self.app = _create_app()
        self.client = TestClient(self.app)

    def test_returns_all_tables(self):
        self.discovery.list_foreign_tables.return_value = [
            ForeignTableInfo(schema_name="public", table_name="accounts", server_name="sf_server", column_count=5),
        ]
        resp = self.client.get("/api/fdw/tables")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["tableName"] == "accounts"
        self.discovery.list_foreign_tables.assert_called_once_with(server_name=None)

    def test_filters_by_server_query_param(self):
        self.discovery.list_foreign_tables.return_value = []
        resp = self.client.get("/api/fdw/tables?server=sf_server")
        assert resp.status_code == 200
        self.discovery.list_foreign_tables.assert_called_once_with(server_name="sf_server")

    def test_connection_error_returns_502(self):
        self.discovery.list_foreign_tables.side_effect = FDWConnectionError(
            "Connection refused", host="db.local", port=5432
        )
        resp = self.client.get("/api/fdw/tables")
        assert resp.status_code == 502


# ── GET /tables/{schema}/{table}/columns tests ──────────────────────────────

class TestGetColumns:

    def setup_method(self):
        self.discovery = AsyncMock()
        _configure_enabled(discovery=self.discovery)
        self.app = _create_app()
        self.client = TestClient(self.app)

    def test_returns_columns(self):
        self.discovery.get_table_columns.return_value = [
            ColumnInfo(column_name="id", data_type="integer", is_nullable=False, ordinal_position=1),
            ColumnInfo(column_name="name", data_type="text", is_nullable=True, ordinal_position=2),
        ]
        resp = self.client.get("/api/fdw/tables/public/accounts/columns")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["columnName"] == "id"
        assert data[1]["isNullable"] is True

    def test_table_not_found_returns_404(self):
        self.discovery.get_table_columns.return_value = []
        resp = self.client.get("/api/fdw/tables/public/nonexistent/columns")
        assert resp.status_code == 404
        assert "Table not found" in resp.json()["detail"]["error"]

    def test_connection_error_returns_502(self):
        self.discovery.get_table_columns.side_effect = FDWConnectionError(
            "Connection refused", host="db.local", port=5432
        )
        resp = self.client.get("/api/fdw/tables/public/accounts/columns")
        assert resp.status_code == 502


# ── POST /query tests ────────────────────────────────────────────────────────

class TestExecuteQuery:

    def setup_method(self):
        self.query_service = AsyncMock()
        _configure_enabled(query=self.query_service)
        self.app = _create_app()
        self.client = TestClient(self.app)

    def test_successful_query(self):
        self.query_service.execute_query.return_value = QueryResponse(
            rows=[{"id": 1, "name": "Alice"}],
            metadata=QueryMetadata(duration_ms=12.5, table_queried="public.accounts", row_count=1),
        )
        resp = self.client.post("/api/fdw/query", json={"table": "accounts"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rows"]) == 1
        assert data["metadata"]["durationMs"] == 12.5

    def test_table_not_found_returns_404(self):
        self.query_service.execute_query.side_effect = FDWTableNotFoundError(
            schema="public", table="missing"
        )
        resp = self.client.post("/api/fdw/query", json={"table": "missing"})
        assert resp.status_code == 404
        assert "Table not found" in resp.json()["detail"]["error"]

    def test_timeout_returns_504(self):
        self.query_service.execute_query.side_effect = FDWTimeoutError(
            timeout_seconds=30, table="public.slow_table"
        )
        resp = self.client.post("/api/fdw/query", json={"table": "slow_table"})
        assert resp.status_code == 504
        assert "Query timeout" in resp.json()["detail"]["error"]

    def test_connection_error_returns_502(self):
        self.query_service.execute_query.side_effect = FDWConnectionError(
            "Connection refused", host="db.local", port=5432
        )
        resp = self.client.post("/api/fdw/query", json={"table": "accounts"})
        assert resp.status_code == 502

    def test_query_error_returns_502(self):
        self.query_service.execute_query.side_effect = FDWQueryError(
            "Upstream failure", table="public.accounts"
        )
        resp = self.client.post("/api/fdw/query", json={"table": "accounts"})
        assert resp.status_code == 502

    def test_invalid_limit_returns_422(self):
        resp = self.client.post("/api/fdw/query", json={"table": "t", "limit": 0})
        assert resp.status_code == 422

    def test_invalid_limit_too_high_returns_422(self):
        resp = self.client.post("/api/fdw/query", json={"table": "t", "limit": 99999})
        assert resp.status_code == 422

    def test_negative_offset_returns_422(self):
        resp = self.client.post("/api/fdw/query", json={"table": "t", "offset": -1})
        assert resp.status_code == 422

    def test_missing_table_returns_422(self):
        resp = self.client.post("/api/fdw/query", json={})
        assert resp.status_code == 422
