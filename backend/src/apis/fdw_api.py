"""
FDW Discovery and Query REST API

Exposes endpoints for discovering foreign servers/tables and executing
queries against the FDW-enabled PostgreSQL database. Returns HTTP 503
when FDW integration is disabled.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7**
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from src.models.fdw_models import (
    ColumnInfo,
    ForeignServerInfo,
    ForeignTableInfo,
    QueryRequest,
    QueryResponse,
)
from src.utils.fdw_errors import (
    FDWConnectionError,
    FDWQueryError,
    FDWTableNotFoundError,
    FDWTimeoutError,
)

fdw_logger = logger.bind(component="fdw")

# Module-level service references (set during app startup)
_connection_manager = None
_discovery_service = None
_query_service = None
_simulators: Dict[str, object] = {}
_mode_service = None

# Map from a mode-service "source" key to the simulator key registered
# on this module. Lets the resolver translate `effective_mode("oracle")`
# into the right entry in `_simulators`. The three external sub-sources
# (file_uploads / google_drive / social_listening) all currently route
# to the single ``external`` simulator service.
_SOURCE_TO_SIM_KEY = {
    "sfdc":             "simulator",
    "oracle":           "oracle",
    "sap":              "sap",
    "file_uploads":     "external",
    "google_drive":     "external",
    "social_listening": "external",
    # Legacy aggregate retained for callers that may pass ``source=external``
    # directly (e.g. mid-deploy where one replica is older).
    "external":         "external",
    "tpm":              "tpm",
    "sourcing":         "sourcing",
}


def configure(connection_manager, discovery_service, query_service, mode_service=None):
    """Configure FDW API with service instances. Called during app startup."""
    global _connection_manager, _discovery_service, _query_service, _mode_service
    _connection_manager = connection_manager
    _discovery_service = discovery_service
    _query_service = query_service
    if mode_service is not None:
        _mode_service = mode_service


def configure_simulator(simulator_service, name: str = "simulator"):
    """Configure a simulator service. name can be 'simulator', 'oracle', 'sap'."""
    _simulators[name] = simulator_service
    fdw_logger.info(f"FDW API simulator configured: {name}")


def _resolve_source_default(schema: Optional[str] = None) -> Optional[str]:
    """When ``?source=`` is omitted, decide whether to route to the
    simulator or the live FDW based on the per-source mode resolver.

    Returns one of:
      - ``"simulator"`` / ``"oracle"`` / ``"sap"`` / ``"external"`` - matches a key in ``_simulators``
      - ``"real"`` - explicit real-mode hint (caller skips simulator path)
      - ``None`` - resolver not configured; legacy behaviour applies
    """
    if _mode_service is None:
        return None
    src: Optional[str] = None
    if schema:
        src = _mode_service.schema_to_source(schema)
    if not src:
        # Without an explicit schema, default the resolver to SFDC since
        # that is the canonical FDW path for table/server discovery.
        src = "sfdc"
    mode = _mode_service.effective_mode(src)
    if mode == "simulator":
        return _SOURCE_TO_SIM_KEY.get(src, "simulator")
    return "real"


def _check_fdw_enabled():
    """Raise HTTP 503 if FDW integration is not configured."""
    if _connection_manager is None and _discovery_service is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "FDW integration is not configured"},
        )


def _get_simulator(source: Optional[str]):
    """Get the simulator service for the given source, or None.

    Does not require ``loaded`` — callers ``ensure_loaded()`` and hard-error
    in simulator mode instead of silently falling through to live FDW.
    """
    if not source or source == "real":
        return None
    sim = _simulators.get(source)
    if sim:
        return sim
    if source == "simulator":
        return _simulators.get("simulator")
    return None


# Create router
router = APIRouter(prefix="/api/fdw", tags=["fdw"])


@router.get("/servers", response_model=List[ForeignServerInfo])
async def list_servers(source: Optional[str] = Query(None)):
    """List foreign servers. Pass source=simulator|oracle|sap to use simulator data;
    when omitted the per-source mode resolver decides simulator vs real."""
    if source is None:
        source = _resolve_source_default()
    sim = _get_simulator(source)
    if sim:
        await sim.ensure_loaded()
        return await sim.list_foreign_servers()
    _check_fdw_enabled()
    try:
        servers = await _discovery_service.list_foreign_servers()
        return servers
    except FDWConnectionError as e:
        raise HTTPException(status_code=502, detail={"error": "FDW database connection failed", "detail": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Internal server error", "detail": str(e)})


@router.get("/tables", response_model=List[ForeignTableInfo])
async def list_tables(server: Optional[str] = Query(None), source: Optional[str] = Query(None)):
    """List foreign tables. Pass source=simulator|oracle|sap to use simulator data;
    when omitted the per-source mode resolver decides simulator vs real."""
    if source is None:
        source = _resolve_source_default()
    sim = _get_simulator(source)
    if sim:
        await sim.ensure_loaded()
        return await sim.list_foreign_tables(server_name=server)
    _check_fdw_enabled()
    try:
        tables = await _discovery_service.list_foreign_tables(server_name=server)
        return tables
    except FDWConnectionError as e:
        raise HTTPException(status_code=502, detail={"error": "FDW database connection failed", "detail": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Internal server error", "detail": str(e)})


@router.get("/tables/{schema}/{table}/columns", response_model=List[ColumnInfo])
async def get_columns(schema: str, table: str, source: Optional[str] = Query(None)):
    """Get column metadata. Pass source=simulator|oracle|sap to use simulator data;
    when omitted the per-source mode resolver decides simulator vs real."""
    if source is None:
        source = _resolve_source_default(schema=schema)
    sim = _get_simulator(source)
    if sim:
        await sim.ensure_loaded()
        columns = await sim.get_table_columns(schema, table)
        if not columns:
            raise HTTPException(status_code=404, detail={"error": "Table not found", "detail": f"{schema}.{table} does not exist"})
        return columns
    _check_fdw_enabled()
    try:
        columns = await _discovery_service.get_table_columns(schema, table)
        if not columns:
            raise HTTPException(status_code=404, detail={"error": "Table not found", "detail": f"{schema}.{table} does not exist"})
        return columns
    except HTTPException:
        raise
    except FDWConnectionError as e:
        raise HTTPException(status_code=502, detail={"error": "FDW database connection failed", "detail": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Internal server error", "detail": str(e)})


@router.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest, source: Optional[str] = Query(None)):
    """Execute a query. Pass source=simulator|oracle|sap to use simulator data;
    when omitted the per-source mode resolver decides simulator vs real."""
    if source is None:
        source = _resolve_source_default(schema=request.schema_name)
    sim = _get_simulator(source)
    if sim:
        await sim.ensure_loaded()
        try:
            return await sim.execute_query(request)
        except Exception as e:
            raise HTTPException(status_code=500, detail={"error": "Simulator query failed", "detail": str(e)})
    _check_fdw_enabled()
    try:
        result = await _query_service.execute_query(request)
        return result
    except FDWTableNotFoundError as e:
        raise HTTPException(status_code=404, detail={"error": "Table not found", "detail": str(e)})
    except FDWTimeoutError as e:
        raise HTTPException(status_code=504, detail={"error": "Query timeout", "detail": str(e)})
    except (FDWConnectionError, FDWQueryError) as e:
        raise HTTPException(status_code=502, detail={"error": "Query execution failed", "detail": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Internal server error", "detail": str(e)})

