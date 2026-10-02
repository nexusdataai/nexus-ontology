"""
FDW Query Service for nexus-backend

Builds and executes parameterized SQL queries against the FDW-enabled
PostgreSQL database. Validates table/column names against the discovery
cache (whitelist approach) and classifies upstream errors.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8**
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger
from sqlalchemy import text

from src.models.fdw_models import (
    QueryMetadata,
    QueryRequest,
    QueryResponse,
)
from src.services.fdw_connection_manager import PostgreSQLConnectionManager
from src.services.fdw_discovery_service import FDWDiscoveryService, raw_schema
from src.utils.fdw_errors import (
    FDWQueryError,
    FDWTableNotFoundError,
    FDWTimeoutError,
)

fdw_logger = logger.bind(component="fdw")


class FDWQueryService:
    """
    Builds and executes parameterized SELECT queries against the FDW database.

    Table and column names are validated against the discovery cache
    (whitelist approach) — never interpolated from raw user input.
    All filter values use named parameter placeholders.
    """

    ALLOWED_OPERATORS: Dict[str, str] = {
        "eq": "=",
        "neq": "!=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "like": "LIKE",
        "in": "IN",
    }

    def __init__(
        self,
        connection_manager: PostgreSQLConnectionManager,
        discovery_service: FDWDiscoveryService,
        tmf_type_map: Optional[Dict] = None,
    ):
        self._conn_mgr = connection_manager
        self._discovery = discovery_service
        self._tmf_type_map = tmf_type_map

    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        """
        Validate the table, build SQL, execute, and return QueryResponse.

        Steps:
            1. Validate the table exists via discovery service
            2. Validate requested columns against discovered columns
            3. Build parameterized SQL via _build_select()
            4. Set statement_timeout on the connection
            5. Execute the query
            6. Return QueryResponse with metadata

        Raises:
            FDWTableNotFoundError: If the table does not exist.
            FDWTimeoutError: If the query exceeds the configured timeout.
            FDWQueryError: If the query fails for any other reason.
        """
        # The caller passes the canonical schema (e.g. ``sfdc_itxp2dev``);
        # the underlying Postgres may host foreign tables under a legacy
        # schema (deployment-supplied via LEGACY_FDW_SCHEMA). The
        # discovery service translates between the two; we resolve the raw
        # schema once up-front and use it for both the introspection cache
        # lookup and the FROM clause we build below.
        # schema for the SQL FROM clause but keep the canonical name in
        # validation messages and response metadata so nothing leaks.
        schema = request.schema_name
        raw_schema_name = raw_schema(schema)
        table = request.table
        sql_request = (
            request
            if raw_schema_name == schema
            else request.model_copy(update={"schema_name": raw_schema_name})
        )

        # 1. Validate table exists
        await self._validate_table_exists(schema, table)

        # 2. Validate columns against discovery cache
        discovered_columns = await self._discovery.get_table_columns(schema, table)
        valid_column_names = {col.column_name for col in discovered_columns}

        if request.columns:
            for col in request.columns:
                if col not in valid_column_names:
                    raise FDWQueryError(
                        f"Column '{col}' not found in table '{schema}.{table}'",
                        table=f"{schema}.{table}",
                    )

        if request.filters:
            for f in request.filters:
                if f.column not in valid_column_names:
                    raise FDWQueryError(
                        f"Filter column '{f.column}' not found in table '{schema}.{table}'",
                        table=f"{schema}.{table}",
                    )

        if request.order_by:
            for ob in request.order_by:
                if ob.column not in valid_column_names:
                    raise FDWQueryError(
                        f"Order-by column '{ob.column}' not found in table '{schema}.{table}'",
                        table=f"{schema}.{table}",
                    )

        # 3. Build SQL (uses the raw schema so the FROM clause hits the
        # actual Postgres foreign tables).
        sql_text, params = self._build_select(sql_request, valid_column_names)

        fdw_logger.info(
            "Executing FDW query",
            table=f"{schema}.{table}",
            filters_count=len(request.filters) if request.filters else 0,
        )

        # 4 & 5. Execute with timeout
        start = time.monotonic()
        try:
            loop = asyncio.get_event_loop()
            async with self._conn_mgr.get_connection() as conn:
                # Set statement_timeout
                timeout_ms = self._conn_mgr._config.query_timeout * 1000
                await loop.run_in_executor(
                    None,
                    lambda: conn.execute(
                        text(f"SET statement_timeout = '{timeout_ms}'")
                    ),
                )

                def _execute_and_fetch():
                    cursor_result = conn.execute(text(sql_text), params)
                    keys = list(cursor_result.keys())
                    rows_raw = cursor_result.fetchall()
                    return keys, rows_raw

                column_keys, result = await loop.run_in_executor(
                    None, _execute_and_fetch
                )

        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            self._handle_query_error(e, schema, table, elapsed_ms)

        elapsed_ms = (time.monotonic() - start) * 1000

        # Convert rows to list of dicts
        rows = [dict(zip(column_keys, row)) for row in result]

        fdw_logger.info(
            "Query completed",
            table=f"{schema}.{table}",
            row_count=len(rows),
            duration_ms=round(elapsed_ms, 2),
        )

        # Bridge per-call log entry -- captures the actual SQL string
        # + param keys (values are redacted by run_context.redact when
        # any look secret-ish) so the Copilot Saved studio's per-step
        # drill-down can show the exact query that ran. No-op when
        # no active RunContext.
        try:
            from src.services.control_plane.run_context import emit as _emit
            _emit(
                level="DEBUG",
                message=(
                    f"FDW SELECT {schema}.{table} -> {len(rows)} rows "
                    f"in {round(elapsed_ms, 2)}ms"
                ),
                details={
                    "sql": sql_text,
                    "params": params,
                    "table": f"{schema}.{table}",
                    "row_count": len(rows),
                    "duration_ms": round(elapsed_ms, 2),
                },
                source="virtual_query",
            )
        except Exception:
            pass

        # 6. Return QueryResponse
        metadata = QueryMetadata(
            duration_ms=round(elapsed_ms, 2),
            table_queried=f"{schema}.{table}",
            row_count=len(rows),
        )

        return QueryResponse(rows=rows, metadata=metadata)

    def _build_select(
        self,
        request: QueryRequest,
        valid_columns: Optional[Set[str]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a parameterized SELECT statement from a QueryRequest.

        Returns:
            Tuple of (sql_text, params_dict) where sql_text uses :named_param
            placeholders for all user-supplied values.

        Table and column names are double-quoted in the SQL. Column names
        are validated against the valid_columns whitelist when provided.
        """
        schema = request.schema_name
        table = request.table
        params: Dict[str, Any] = {}

        # SELECT clause
        if request.columns:
            col_list = ", ".join(f'"{col}"' for col in request.columns)
            select_clause = f"SELECT {col_list}"
        else:
            select_clause = "SELECT *"

        # FROM clause — double-quoted schema and table
        from_clause = f'FROM "{schema}"."{table}"'

        # WHERE clause
        where_parts: List[str] = []
        if request.filters:
            for i, filt in enumerate(request.filters):
                param_name = f"param_{i}"
                col_quoted = f'"{filt.column}"'
                op_value = filt.operator.value if filt.operator.value != "in" else "in"
                sql_op = self.ALLOWED_OPERATORS.get(op_value)

                if sql_op is None:
                    raise FDWQueryError(
                        f"Unsupported operator: {filt.operator}",
                        table=f"{schema}.{table}",
                    )

                if sql_op == "IN":
                    # For IN operator, use expanding bind with tuple
                    if isinstance(filt.value, list):
                        # Build individual params for each value in the list
                        in_params = []
                        for j, val in enumerate(filt.value):
                            in_param_name = f"param_{i}_{j}"
                            params[in_param_name] = val
                            in_params.append(f":{in_param_name}")
                        in_clause = ", ".join(in_params)
                        where_parts.append(f"{col_quoted} IN ({in_clause})")
                    else:
                        params[param_name] = filt.value
                        where_parts.append(f"{col_quoted} IN (:{param_name})")
                else:
                    params[param_name] = filt.value
                    where_parts.append(f"{col_quoted} {sql_op} :{param_name}")

        where_clause = ""
        if where_parts:
            where_clause = "WHERE " + " AND ".join(where_parts)

        # ORDER BY clause
        order_clause = ""
        if request.order_by:
            order_parts = []
            for ob in request.order_by:
                direction = ob.direction.upper()
                order_parts.append(f'"{ob.column}" {direction}')
            order_clause = "ORDER BY " + ", ".join(order_parts)

        # LIMIT / OFFSET
        limit_clause = ""
        if request.limit is not None:
            params["limit_val"] = request.limit
            limit_clause = "LIMIT :limit_val"

        offset_clause = ""
        if request.offset is not None:
            params["offset_val"] = request.offset
            offset_clause = "OFFSET :offset_val"

        # Assemble
        parts = [select_clause, from_clause]
        if where_clause:
            parts.append(where_clause)
        if order_clause:
            parts.append(order_clause)
        if limit_clause:
            parts.append(limit_clause)
        if offset_clause:
            parts.append(offset_clause)

        sql = " ".join(parts)
        return sql, params

    async def _validate_table_exists(self, schema: str, table: str) -> None:
        """
        Check the discovery cache to verify the table exists.

        Raises:
            FDWTableNotFoundError: If the table is not found.
        """
        columns = await self._discovery.get_table_columns(schema, table)
        if not columns:
            raise FDWTableNotFoundError(schema=schema, table=table)

    def _handle_query_error(
        self, error: Exception, schema: str, table: str, elapsed_ms: float
    ) -> None:
        """
        Classify and re-raise psycopg2/SQLAlchemy exceptions as FDW error types.

        Categories:
            - Timeout: QueryCanceledError → FDWTimeoutError
            - Connection: OperationalError → FDWQueryError (category=connection)
            - Auth: insufficient_privilege → FDWQueryError (category=auth)
            - Data: other errors → FDWQueryError (category=data)
        """
        error_str = str(error).lower()
        table_ref = f"{schema}.{table}"

        fdw_logger.error(
            "Query execution failed",
            table=table_ref,
            duration_ms=round(elapsed_ms, 2),
            error_type=type(error).__name__,
            error=str(error),
        )

        # Check for timeout (cancellation due to statement_timeout)
        if "canceling statement due to statement timeout" in error_str or \
           "QueryCanceledError" in type(error).__name__ or \
           "cancel" in error_str and "timeout" in error_str:
            timeout_seconds = getattr(
                getattr(self._conn_mgr, '_config', None), 'query_timeout', 30
            )
            raise FDWTimeoutError(
                timeout_seconds=timeout_seconds,
                table=table_ref,
            ) from error

        # Check for connection errors
        if any(kw in error_str for kw in [
            "connection refused", "could not connect", "connection reset",
            "connection timed out", "broken pipe", "operationalerror",
            "server closed the connection",
        ]):
            raise FDWQueryError(
                message=f"Connection error during query: {error}",
                table=table_ref,
                original_error=error,
            ) from error

        # Check for auth errors
        if any(kw in error_str for kw in [
            "authentication failed", "insufficient_privilege",
            "permission denied", "password authentication failed",
        ]):
            raise FDWQueryError(
                message=f"Authentication/authorization error during query: {error}",
                table=table_ref,
                original_error=error,
            ) from error

        # Default: data/general error
        raise FDWQueryError(
            message=f"Query execution failed: {error}",
            table=table_ref,
            original_error=error,
        ) from error
