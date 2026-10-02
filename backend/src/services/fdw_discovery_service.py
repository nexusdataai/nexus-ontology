"""
FDW Discovery Service for nexus-backend

Introspects the PostgreSQL catalog to find foreign servers, foreign tables,
and their column schemas. Results are cached with a configurable TTL to
avoid repeated introspection queries.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import text

from src.models.fdw_models import ColumnInfo, ForeignServerInfo, ForeignTableInfo
from src.services.fdw_connection_manager import PostgreSQLConnectionManager

fdw_logger = logger.bind(component="fdw")

# SQL for listing foreign servers with their wrapper type and options
_LIST_SERVERS_SQL = text(
    "SELECT s.srvname, w.fdwname, s.srvoptions "
    "FROM pg_foreign_server s "
    "JOIN pg_foreign_data_wrapper w ON s.srvfdw = w.oid"
)

# SQL for listing foreign tables
_LIST_TABLES_SQL = text(
    "SELECT foreign_table_schema, foreign_table_name, foreign_server_name "
    "FROM information_schema.foreign_tables"
)

# SQL for listing foreign tables filtered by server name
_LIST_TABLES_BY_SERVER_SQL = text(
    "SELECT foreign_table_schema, foreign_table_name, foreign_server_name "
    "FROM information_schema.foreign_tables "
    "WHERE foreign_server_name = :server_name"
)

# SQL for getting column metadata for a specific table
_GET_COLUMNS_SQL = text(
    "SELECT column_name, data_type, is_nullable, ordinal_position "
    "FROM information_schema.columns "
    "WHERE table_schema = :schema AND table_name = :table "
    "ORDER BY ordinal_position"
)

# SQL for counting columns in a table (used for ForeignTableInfo.column_count)
_COUNT_COLUMNS_SQL = text(
    "SELECT table_schema, table_name, COUNT(*) as col_count "
    "FROM information_schema.columns "
    "WHERE (table_schema, table_name) IN ("
    "  SELECT foreign_table_schema, foreign_table_name "
    "  FROM information_schema.foreign_tables"
    ") "
    "GROUP BY table_schema, table_name"
)

_COUNT_COLUMNS_BY_SERVER_SQL = text(
    "SELECT table_schema, table_name, COUNT(*) as col_count "
    "FROM information_schema.columns "
    "WHERE (table_schema, table_name) IN ("
    "  SELECT foreign_table_schema, foreign_table_name "
    "  FROM information_schema.foreign_tables "
    "  WHERE foreign_server_name = :server_name"
    ") "
    "GROUP BY table_schema, table_name"
)


def _parse_server_options(srvoptions: Optional[list]) -> dict:
    """Parse PostgreSQL server options array into a dictionary.

    PostgreSQL stores server options as an array of 'key=value' strings.
    Returns an empty dict if srvoptions is None or empty.
    """
    if not srvoptions:
        return {}
    result = {}
    for opt in srvoptions:
        if "=" in opt:
            key, _, value = opt.partition("=")
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# Capability-neutral name rewrite.
#
# The underlying Postgres image we connect to (provisioned outside of this
# repo) may expose the SFDC foreign server and schema under a legacy
# capability-prefixed name we don't control. We do a thin bidirectional
# rewrite at this layer so the rest of the product (UI, mapping rules,
# query API) only ever sees capability-neutral names. The rewrite is
# symmetric: every canonical name written into the API response can be
# reverse-translated to the raw Postgres name when a query comes back in.
#
# The raw upstream name comes from the deployment via env vars
# ``LEGACY_FDW_SERVER`` / ``LEGACY_FDW_SCHEMA``. When unset (e.g. local
# dev with a clean Postgres) the rewrite is a no-op.
# ---------------------------------------------------------------------------

CANONICAL_FDW_SERVER = "sfdc_fdw"
CANONICAL_FDW_SCHEMA = "sfdc_itxp2dev"

_LEGACY_FDW_SERVER = os.getenv("LEGACY_FDW_SERVER", "").strip()
_LEGACY_FDW_SCHEMA = os.getenv("LEGACY_FDW_SCHEMA", "").strip()

_FDW_SERVER_REWRITE: Dict[str, str] = (
    {_LEGACY_FDW_SERVER: CANONICAL_FDW_SERVER}
    if _LEGACY_FDW_SERVER and _LEGACY_FDW_SERVER != CANONICAL_FDW_SERVER
    else {}
)
_FDW_SCHEMA_REWRITE: Dict[str, str] = (
    {_LEGACY_FDW_SCHEMA: CANONICAL_FDW_SCHEMA}
    if _LEGACY_FDW_SCHEMA and _LEGACY_FDW_SCHEMA != CANONICAL_FDW_SCHEMA
    else {}
)

_FDW_SERVER_REWRITE_REVERSE: Dict[str, str] = {v: k for k, v in _FDW_SERVER_REWRITE.items()}
_FDW_SCHEMA_REWRITE_REVERSE: Dict[str, str] = {v: k for k, v in _FDW_SCHEMA_REWRITE.items()}


def canonical_server(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    return _FDW_SERVER_REWRITE.get(name, name)


def canonical_schema(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    return _FDW_SCHEMA_REWRITE.get(name, name)


def raw_server(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    return _FDW_SERVER_REWRITE_REVERSE.get(name, name)


def raw_schema(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    return _FDW_SCHEMA_REWRITE_REVERSE.get(name, name)


class FDWDiscoveryService:
    """
    Discovers foreign servers, foreign tables, and column schemas
    by introspecting PostgreSQL catalog views.

    Results are cached with a configurable TTL (default 300s).
    Use refresh_cache() to force a re-query on the next call.
    """

    def __init__(
        self,
        connection_manager: PostgreSQLConnectionManager,
        cache_ttl: float = 300.0,
    ):
        self._conn_mgr = connection_manager
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._cache_ttl: float = cache_ttl

    def _cache_get(self, key: str) -> Optional[Any]:
        """Return cached value if present and not expired, else None."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, data = entry
        if (time.monotonic() - ts) >= self._cache_ttl:
            fdw_logger.debug("Cache expired", cache_key=key)
            del self._cache[key]
            return None
        fdw_logger.debug("Cache hit", cache_key=key)
        return data

    def _cache_set(self, key: str, data: Any) -> None:
        """Store data in cache with current timestamp."""
        self._cache[key] = (time.monotonic(), data)

    async def list_foreign_servers(self) -> List[ForeignServerInfo]:
        """
        Query pg_foreign_server JOIN pg_foreign_data_wrapper to list
        all configured foreign servers.

        Returns:
            List of ForeignServerInfo with server name, wrapper type,
            and parsed server options.
        """
        cache_key = "list_foreign_servers"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        fdw_logger.info("Querying foreign servers from pg_catalog")

        loop = asyncio.get_event_loop()
        async with self._conn_mgr.get_connection() as conn:
            result = await loop.run_in_executor(
                None, lambda: conn.execute(_LIST_SERVERS_SQL).fetchall()
            )

        servers: List[ForeignServerInfo] = []
        for row in result:
            servers.append(
                ForeignServerInfo(
                    server_name=canonical_server(row[0]),
                    wrapper_type=row[1],
                    server_options=_parse_server_options(row[2]),
                )
            )

        fdw_logger.info("Found foreign servers", count=len(servers))
        self._cache_set(cache_key, servers)
        return servers

    async def list_foreign_tables(
        self, server_name: Optional[str] = None
    ) -> List[ForeignTableInfo]:
        """
        Query information_schema.foreign_tables to list foreign tables,
        optionally filtered by server name. Includes column count per table.

        Args:
            server_name: If provided, only return tables for this server.

        Returns:
            List of ForeignTableInfo with schema, table name, server name,
            and column count.
        """
        cache_key = f"list_foreign_tables:{server_name or ''}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # Reverse-translate the canonical server name to the raw Postgres
        # name before hitting pg_catalog.
        raw_server_name = raw_server(server_name)

        fdw_logger.info(
            "Querying foreign tables from information_schema",
            server_name=server_name,
        )

        loop = asyncio.get_event_loop()
        async with self._conn_mgr.get_connection() as conn:
            # Fetch foreign tables
            if raw_server_name:
                table_rows = await loop.run_in_executor(
                    None,
                    lambda: conn.execute(
                        _LIST_TABLES_BY_SERVER_SQL, {"server_name": raw_server_name}
                    ).fetchall(),
                )
                # Fetch column counts for filtered tables
                col_count_rows = await loop.run_in_executor(
                    None,
                    lambda: conn.execute(
                        _COUNT_COLUMNS_BY_SERVER_SQL, {"server_name": raw_server_name}
                    ).fetchall(),
                )
            else:
                table_rows = await loop.run_in_executor(
                    None, lambda: conn.execute(_LIST_TABLES_SQL).fetchall()
                )
                col_count_rows = await loop.run_in_executor(
                    None, lambda: conn.execute(_COUNT_COLUMNS_SQL).fetchall()
                )

        # Build column count lookup: (schema, table) -> count
        col_counts: Dict[Tuple[str, str], int] = {}
        for row in col_count_rows:
            col_counts[(row[0], row[1])] = row[2]

        tables: List[ForeignTableInfo] = []
        for row in table_rows:
            schema = row[0]
            table = row[1]
            srv = row[2]
            tables.append(
                ForeignTableInfo(
                    schema_name=canonical_schema(schema),
                    table_name=table,
                    server_name=canonical_server(srv),
                    column_count=col_counts.get((schema, table), 0),
                )
            )

        fdw_logger.info(
            "Found foreign tables",
            count=len(tables),
            server_name=server_name,
        )
        self._cache_set(cache_key, tables)
        return tables

    async def get_table_columns(
        self, schema: str, table: str
    ) -> List[ColumnInfo]:
        """
        Query information_schema.columns for a specific table's column metadata.

        Args:
            schema: The table's schema name.
            table: The table name.

        Returns:
            List of ColumnInfo with column name, data type, nullability,
            and ordinal position.
        """
        cache_key = f"get_table_columns:{schema}:{table}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # Reverse-translate canonical schema to raw before SQL.
        raw_schema_name = raw_schema(schema)

        fdw_logger.info(
            "Querying columns from information_schema",
            schema=schema,
            table=table,
        )

        loop = asyncio.get_event_loop()
        async with self._conn_mgr.get_connection() as conn:
            result = await loop.run_in_executor(
                None,
                lambda: conn.execute(
                    _GET_COLUMNS_SQL, {"schema": raw_schema_name, "table": table}
                ).fetchall(),
            )

        columns: List[ColumnInfo] = []
        for row in result:
            columns.append(
                ColumnInfo(
                    column_name=row[0],
                    data_type=row[1],
                    is_nullable=row[2] == "YES",
                    ordinal_position=row[3],
                )
            )

        fdw_logger.info(
            "Found columns",
            schema=schema,
            table=table,
            count=len(columns),
        )
        self._cache_set(cache_key, columns)
        return columns

    async def refresh_cache(self) -> None:
        """Force clear the entire discovery cache.

        The next discovery call will re-query the database.
        """
        cache_size = len(self._cache)
        self._cache.clear()
        fdw_logger.info("Discovery cache cleared", previous_entries=cache_size)
