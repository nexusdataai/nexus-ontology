"""
FDW Tools for the AI Control Plane.

Wraps FDW Discovery and Query services as agent-callable tools.
All tools are read-only and operate against the existing FDW connection
pool when the per-source mode is ``real``, or against the in-memory
simulator when the mode is ``simulator``.

Routing decision is delegated to ``DataSourceModeService.effective_mode``
so this file does not duplicate "is the simulator loaded?" heuristics.
On a fresh deploy the default is ``simulator`` for every source.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from src.services.fdw_discovery_service import FDWDiscoveryService
from src.services.fdw_query_service import FDWQueryService
from src.models.fdw_models import QueryRequest, QueryFilter, FilterOperator, OrderByItem
from ..tool_registry import Tool, RiskLevel

cp_logger = logger.bind(component="control-plane")

DEFAULT_SCHEMA = "sfdc_schema"


# ---------------------------------------------------------------------------
# Mode resolution helpers
# ---------------------------------------------------------------------------

def _resolve_mode(mode_service: Any, schema_name: str) -> str:
    """Return ``simulator`` or ``real`` for the given schema. Defaults to
    ``real`` when no mode_service is configured (legacy callers)."""
    if mode_service is None:
        return "real"
    source = mode_service.schema_to_source(schema_name)
    return mode_service.effective_mode(source) if source else "real"


def _pick_simulator(simulators: Optional[Dict[str, Any]], schema_name: str) -> Optional[Any]:
    """Map a foreign-table schema to the loaded simulator instance.

    Mirrors ``virtual_query_service.SCHEMA_TO_SIMULATOR`` so VDL queries
    and ReAct ``query_table`` agree on which simulator to consult.
    """
    if not simulators:
        return None
    schema_to_sim_key = {
        "sfdc_schema": "simulator",
        "sfdc_itxp2dev": "simulator",
        "salesforce":    "simulator",
        "oracle_erp":    "oracle",
        "sap_s4hana":    "sap",
        "external_sources": "external",
    }
    key = schema_to_sim_key.get((schema_name or "").lower())
    if not key:
        return None
    return simulators.get(key)


# ---------------------------------------------------------------------------
# discover_tables
# ---------------------------------------------------------------------------

async def _discover_tables(
    discovery: Optional[FDWDiscoveryService],
    simulators: Optional[Dict[str, Any]] = None,
    mode_service: Any = None,
    search_term: Optional[str] = None,
    limit: int = 20,
    schema_name: str = DEFAULT_SCHEMA,
) -> Dict[str, Any]:
    mode = _resolve_mode(mode_service, schema_name)

    if mode == "simulator":
        sim = _pick_simulator(simulators, schema_name)
        if sim is None:
            return {"error": f"simulator for schema '{schema_name}' not configured (mode=simulator)"}
        if hasattr(sim, "ensure_loaded"):
            try:
                await sim.ensure_loaded()
            except Exception as e:
                cp_logger.warning(f"simulator.ensure_loaded({schema_name}) failed: {e}")
        # BaseSimulatorService keeps its catalogue on `_tables` (List[ForeignTableInfo]).
        sim_tables = list(getattr(sim, "_tables", []) or [])
        if search_term:
            term = search_term.lower()
            sim_tables = [t for t in sim_tables if term in t.table_name.lower()]
        sim_tables = sim_tables[:limit]
        return {
            "tables": [
                {
                    "schema": t.schema_name,
                    "table": t.table_name,
                    "server": t.server_name,
                    "column_count": t.column_count,
                }
                for t in sim_tables
            ],
            "total_matched": len(sim_tables),
            "mode": "simulator",
        }

    if discovery is None:
        return {"error": "FDW discovery service not configured (mode=real)"}
    tables = await discovery.list_foreign_tables()
    if search_term:
        term = search_term.lower()
        tables = [t for t in tables if term in t.table_name.lower()]
    tables = tables[:limit]
    return {
        "tables": [
            {
                "schema": t.schema_name,
                "table": t.table_name,
                "server": t.server_name,
                "column_count": t.column_count,
            }
            for t in tables
        ],
        "total_matched": len(tables),
        "mode": "real",
    }


# ---------------------------------------------------------------------------
# discover_columns
# ---------------------------------------------------------------------------

async def _discover_columns(
    discovery: Optional[FDWDiscoveryService],
    table_name: str,
    schema_name: str = DEFAULT_SCHEMA,
    simulators: Optional[Dict[str, Any]] = None,
    mode_service: Any = None,
) -> Dict[str, Any]:
    mode = _resolve_mode(mode_service, schema_name)

    if mode == "simulator":
        sim = _pick_simulator(simulators, schema_name)
        if sim is None:
            return {"error": f"simulator for schema '{schema_name}' not configured (mode=simulator)"}
        if hasattr(sim, "ensure_loaded"):
            try:
                await sim.ensure_loaded()
            except Exception as e:
                cp_logger.warning(f"simulator.ensure_loaded({schema_name}) failed: {e}")
        cols = getattr(sim, "_columns", {}) or {}
        sim_columns = cols.get((schema_name, table_name), []) or []
        return {
            "table": f"{schema_name}.{table_name}",
            "columns": [
                {
                    "name": c.column_name,
                    "type": c.data_type,
                    "nullable": getattr(c, "is_nullable", True),
                    "position": getattr(c, "ordinal_position", 0),
                }
                for c in sim_columns
            ],
            "column_count": len(sim_columns),
            "mode": "simulator",
        }

    if discovery is None:
        return {"error": "FDW discovery service not configured (mode=real)"}
    columns = await discovery.get_table_columns(schema_name, table_name)
    return {
        "table": f"{schema_name}.{table_name}",
        "columns": [
            {
                "name": c.column_name,
                "type": c.data_type,
                "nullable": c.is_nullable,
                "position": c.ordinal_position,
            }
            for c in columns
        ],
        "column_count": len(columns),
        "mode": "real",
    }


# ---------------------------------------------------------------------------
# query_table
# ---------------------------------------------------------------------------

async def _query_table(
    query_service: Optional[FDWQueryService],
    table_name: str,
    schema_name: str = DEFAULT_SCHEMA,
    columns: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    order_by: Optional[List[Dict[str, str]]] = None,
    limit: int = 25,
    simulators: Optional[Dict[str, Any]] = None,
    mode_service: Any = None,
) -> Dict[str, Any]:
    filter_objs = None
    if filters:
        filter_objs = []
        for f in filters:
            try:
                filter_objs.append(QueryFilter(
                    column=f["column"],
                    operator=FilterOperator(f.get("operator", "eq")),
                    value=f["value"],
                ))
            except Exception as e:
                return {"error": f"Invalid filter: {e}"}

    order_objs = None
    if order_by:
        order_objs = [
            OrderByItem(column=o["column"], direction=o.get("direction", "asc"))
            for o in order_by
        ]

    request = QueryRequest(
        table=table_name,
        schema_name=schema_name,
        columns=columns,
        filters=filter_objs,
        order_by=order_objs,
        limit=min(limit, 100),
    )

    mode = _resolve_mode(mode_service, schema_name)

    if mode == "simulator":
        sim = _pick_simulator(simulators, schema_name)
        if sim is None:
            return {"error": f"simulator for schema '{schema_name}' not configured (mode=simulator)"}
        if hasattr(sim, "ensure_loaded"):
            try:
                await sim.ensure_loaded()
            except Exception as e:
                cp_logger.warning(f"simulator.ensure_loaded({schema_name}) failed: {e}")
        try:
            response = await sim.execute_query(request)
        except Exception as e:
            return {"error": f"simulator execute_query failed: {e}"}
        return {
            "rows": response.rows[:100],
            "row_count": response.metadata.row_count if response.metadata else len(response.rows),
            "duration_ms": response.metadata.duration_ms if response.metadata else 0,
            "table": f"{schema_name}.{table_name}",
            "mode": "simulator",
        }

    if query_service is None:
        return {"error": "FDW query service not configured (mode=real)"}
    response = await query_service.execute_query(request)
    return {
        "rows": response.rows[:100],
        "row_count": response.metadata.row_count,
        "duration_ms": response.metadata.duration_ms,
        "table": response.metadata.table_queried,
        "mode": "real",
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_fdw_tools(
    registry,
    discovery: Optional[FDWDiscoveryService] = None,
    query_service: Optional[FDWQueryService] = None,
    simulators: Optional[Dict[str, Any]] = None,
    mode_service: Any = None,
    # Legacy positional / keyword form: register_fdw_tools(registry, discovery, query_service)
    fdw_query_service: Optional[FDWQueryService] = None,
):
    """Register all FDW tools with the tool registry.

    The signature accepts both the new ``query_service=`` keyword and the
    legacy ``fdw_query_service=`` form so existing callers don't break.
    """
    if query_service is None and fdw_query_service is not None:
        query_service = fdw_query_service

    registry.register(Tool(
        name="discover_tables",
        description=(
            "Search for foreign tables (Salesforce objects) available via FDW. "
            "Optionally filter by name. Returns table names, schemas, and column counts."
        ),
        parameters={
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "Optional substring to filter table names (e.g. 'Account', 'Opportunity', 'Lead')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max tables to return (default 20)",
                    "default": 20,
                },
                "schema_name": {
                    "type": "string",
                    "description": "Schema to inspect (default: sfdc_itxp2dev)",
                    "default": DEFAULT_SCHEMA,
                },
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _discover_tables(
            discovery, simulators=simulators, mode_service=mode_service, **kw,
        ),
        cacheable=True,
    ))

    registry.register(Tool(
        name="discover_columns",
        description=(
            "Get column metadata (name, data type, nullable) for a specific foreign table. "
            "Use this to understand a table's schema before querying it."
        ),
        parameters={
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "The table name (e.g. 'Account', 'Opportunity', 'Lead')",
                },
                "schema_name": {
                    "type": "string",
                    "description": "Schema name (default: sfdc_itxp2dev)",
                    "default": DEFAULT_SCHEMA,
                },
            },
            "required": ["table_name"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _discover_columns(
            discovery, simulators=simulators, mode_service=mode_service, **kw,
        ),
        cacheable=True,
    ))

    registry.register(Tool(
        name="query_table",
        description=(
            "Execute a parameterized SELECT query against a foreign table. "
            "Routes to the live FDW when mode=real, or to the in-memory simulator when mode=simulator. "
            "Supports column selection, filters (eq/neq/gt/gte/lt/lte/like/in), ordering, and limit. "
            "Max 100 rows returned. Use discover_columns first to know available columns."
        ),
        parameters={
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "The table name to query",
                },
                "schema_name": {
                    "type": "string",
                    "description": "Schema name (default: sfdc_itxp2dev)",
                    "default": DEFAULT_SCHEMA,
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Columns to select. Omit for all columns.",
                },
                "filters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "column": {"type": "string"},
                            "operator": {
                                "type": "string",
                                "enum": ["eq", "neq", "gt", "gte", "lt", "lte", "like", "in"],
                            },
                            "value": {},
                        },
                        "required": ["column", "operator", "value"],
                    },
                    "description": "Filter conditions",
                },
                "order_by": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "column": {"type": "string"},
                            "direction": {"type": "string", "enum": ["asc", "desc"]},
                        },
                        "required": ["column"],
                    },
                    "description": "Ordering directives",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max rows to return (default 25, max 100)",
                    "default": 25,
                },
            },
            "required": ["table_name"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _query_table(
            query_service, simulators=simulators, mode_service=mode_service, **kw,
        ),
    ))

    # Phase 1 -- stamp the infra-query bucket on every tool registered here.
    for tool_name in ("discover_tables", "discover_columns", "query_table"):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "infra-query"
