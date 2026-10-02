"""HTTP client for the standalone nexus-simulator FDW + write contract."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from src.models.fdw_models import ColumnInfo, ForeignServerInfo, ForeignTableInfo, QueryRequest, QueryResponse

fdw_logger = logger.bind(component="simulator-fdw-client")

_REMOTE_KEYS = ("simulator", "oracle", "sap", "external", "tpm", "sourcing")
_SHARED_CLIENT: Optional[httpx.AsyncClient] = None


def simulator_base_url() -> str:
    return (os.getenv("SIMULATOR_BASE_URL") or "").rstrip("/")


def simulator_ui_url() -> str:
    return (os.getenv("SIMULATOR_UI_URL") or "").rstrip("/")


def simulator_remote_enabled() -> bool:
    if os.getenv("SIMULATOR_ENABLED", "true").lower() == "false":
        return False
    return bool(simulator_base_url())


def require_simulator_base_url() -> str:
    url = simulator_base_url()
    if os.getenv("SIMULATOR_ENABLED", "true").lower() != "false" and not url:
        raise RuntimeError(
            "SIMULATOR_ENABLED is true but SIMULATOR_BASE_URL is not set. "
            "Ontology is remote-only; set SIMULATOR_BASE_URL to the in-cluster "
            "simulator backend, e.g. "
            "http://simulator-local-backend-svc-internal.simulator-local.svc.cluster.local:8000"
        )
    return url


def get_simulator_http_client() -> httpx.AsyncClient:
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
        _SHARED_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            follow_redirects=True,
        )
    return _SHARED_CLIENT


class RemoteSimulator:
    """Duck-typed stand-in for a simulator plugin, backed by HTTP."""

    def __init__(self, base_url: str, source: str):
        self._base = base_url.rstrip("/")
        self._source = source
        self._status: Dict[str, Any] = {}
        self.enabled = True
        self.bucket = ""
        self.prefix = ""

    @property
    def loaded(self) -> bool:
        return bool(self._status.get("loaded", True))

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Any = None,
        timeout: float = 60.0,
    ) -> httpx.Response:
        url = f"{self._base}{path}"
        client = get_simulator_http_client()
        last_exc: Optional[Exception] = None
        for attempt in range(3):
            try:
                response = await client.request(
                    method, url, params=params, json=json, timeout=timeout,
                )
                response.raise_for_status()
                return response
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                last_exc = exc
                if attempt == 2:
                    break
        raise last_exc or RuntimeError(f"simulator request failed: {method} {path}")

    async def _refresh_status(self) -> Dict[str, Any]:
        try:
            response = await self._request("GET", "/health")
            body = response.json() if response.content else {}
            healthy = str(body.get("status", "")).lower() in ("ok", "healthy", "")
            self._status = {"loaded": healthy, "enabled": True, **body}
        except Exception as exc:
            fdw_logger.warning("remote health failed for {}: {}", self._source, exc)
            self._status = {"loaded": False, "enabled": True}
        self.enabled = bool(self._status.get("enabled", True))
        return self._status

    def get_status(self) -> Dict[str, Any]:
        return dict(self._status)

    async def ensure_loaded(self) -> None:
        await self._refresh_status()
        if not self.loaded:
            raise RuntimeError(f"nexus-simulator is not healthy for source={self._source}")

    async def list_foreign_servers(self) -> List[ForeignServerInfo]:
        response = await self._request("GET", "/api/fdw/servers", params={"source": self._source})
        return [ForeignServerInfo.model_validate(item) for item in response.json()]

    async def list_foreign_tables(self, server_name: Optional[str] = None) -> List[ForeignTableInfo]:
        params: Dict[str, Any] = {"source": self._source}
        if server_name:
            params["server"] = server_name
        response = await self._request("GET", "/api/fdw/tables", params=params)
        return [ForeignTableInfo.model_validate(item) for item in response.json()]

    async def get_table_columns(self, schema: str, table: str) -> List[ColumnInfo]:
        response = await self._request(
            "GET",
            f"/api/fdw/tables/{schema}/{table}/columns",
            params={"source": self._source},
        )
        return [ColumnInfo.model_validate(item) for item in response.json()]

    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        payload = request.model_dump(by_alias=True, exclude_none=True)
        response = await self._request(
            "POST",
            "/api/fdw/query",
            params={"source": self._source},
            json=payload,
        )
        return QueryResponse.model_validate(response.json())

    async def write_table(self, schema: str, table: str, rows: List[Dict[str, Any]]) -> int:
        response = await self._request(
            "POST",
            "/api/fdw/write",
            params={"source": self._source},
            json={"schemaName": schema, "table": table, "rows": rows, "append": False},
        )
        body = response.json() if response.content else {}
        return int(body.get("rowCount", len(rows)))

    async def append_rows(self, schema: str, table: str, rows: List[Dict[str, Any]]) -> int:
        response = await self._request(
            "POST",
            "/api/fdw/write",
            params={"source": self._source},
            json={"schemaName": schema, "table": table, "rows": rows, "append": True},
        )
        body = response.json() if response.content else {}
        return int(body.get("rowCount", len(rows)))

    async def _get_table_data(self, schema: str, table: str) -> List[Dict[str, Any]]:
        query = QueryRequest(table=table, schema_name=schema, limit=10000, offset=0)
        result = await self.execute_query(query)
        return list(result.rows or [])


def register_remote_simulators(base_url: Optional[str] = None) -> Dict[str, RemoteSimulator]:
    """Register RemoteSimulator proxies on ontology FDW routing only."""
    url = (base_url or require_simulator_base_url()).rstrip("/")
    if not url:
        raise ValueError("SIMULATOR_BASE_URL is required to register remote simulators")

    from src.apis import fdw_api

    remotes: Dict[str, RemoteSimulator] = {}
    for key in _REMOTE_KEYS:
        remote = RemoteSimulator(url, key)
        remotes[key] = remote
        fdw_api.configure_simulator(remote, key)

    fdw_logger.info("Registered remote nexus-simulator proxies", url=url, keys=list(remotes))
    return remotes
