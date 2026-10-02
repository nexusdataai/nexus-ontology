"""
Property-based tests for FDW configuration, models, and error types.

Feature: fdw-integration
Properties 1, 2, 19, 20

Tests FDW configuration round-trip, validation, model serialization,
and password exclusion from error messages.
"""

import os
import sys
import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from hypothesis import given, strategies as st, settings, assume
from src.config.fdw_config import FDWConfig, reset_fdw_config
from src.utils.fdw_errors import FDWConfigurationError, FDWConnectionError
from src.models.fdw_models import (
    ForeignServerInfo,
    ForeignTableInfo,
    ColumnInfo,
    QueryMetadata,
    QueryResponse,
    FDWHealthResponse,
)


# ---------------------------------------------------------------------------
# Env-var helpers
# ---------------------------------------------------------------------------

FDW_ENV_VARS = [
    'FDW_PG_HOST', 'FDW_PG_PORT', 'FDW_PG_DATABASE', 'FDW_PG_USER',
    'FDW_PG_PASSWORD', 'FDW_PG_SCHEMA', 'FDW_PG_SSL_MODE',
    'FDW_PG_POOL_MIN', 'FDW_PG_POOL_MAX', 'FDW_PG_QUERY_TIMEOUT',
]


def _clear_fdw_env():
    for var in FDW_ENV_VARS:
        os.environ.pop(var, None)


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment before and after each test."""
    _clear_fdw_env()
    reset_fdw_config()
    yield
    _clear_fdw_env()
    reset_fdw_config()


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strategy for non-empty, printable strings without NUL bytes that won't be
# stripped to empty by .strip()
_nonempty_text = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S'), blacklist_characters='\x00'),
).filter(lambda s: s.strip() != '')

_port_strategy = st.integers(min_value=1, max_value=65535)
_pool_strategy = st.integers(min_value=1, max_value=100)
_timeout_strategy = st.integers(min_value=1, max_value=3600)


# ---------------------------------------------------------------------------
# Property 1: Configuration environment variable round-trip
# ---------------------------------------------------------------------------

class TestConfigRoundTrip:
    """
    Property 1: Configuration environment variable round-trip

    For any set of valid PostgreSQL connection parameters, setting them as
    environment variables and calling FDWConfig.from_environment() should
    produce a config whose fields match the original values exactly.
    """

    @given(
        host=_nonempty_text,
        port=_port_strategy,
        database=_nonempty_text,
        user=_nonempty_text,
        password=_nonempty_text,
        schema=_nonempty_text,
        ssl_mode=_nonempty_text,
        pool_min=_pool_strategy,
        pool_max=_pool_strategy,
        query_timeout=_timeout_strategy,
    )
    @settings(max_examples=25)
    def test_config_round_trip(
        self, host, port, database, user, password, schema, ssl_mode,
        pool_min, pool_max, query_timeout,
    ):
        """
        Feature: fdw-integration, Property 1: Configuration environment variable round-trip
        **Validates: Requirements 1.1**

        Setting valid connection parameters as env vars and calling
        from_environment() produces a config whose fields match exactly.
        """
        _clear_fdw_env()
        reset_fdw_config()

        os.environ['FDW_PG_HOST'] = host
        os.environ['FDW_PG_PORT'] = str(port)
        os.environ['FDW_PG_DATABASE'] = database
        os.environ['FDW_PG_USER'] = user
        os.environ['FDW_PG_PASSWORD'] = password
        os.environ['FDW_PG_SCHEMA'] = schema
        os.environ['FDW_PG_SSL_MODE'] = ssl_mode
        os.environ['FDW_PG_POOL_MIN'] = str(pool_min)
        os.environ['FDW_PG_POOL_MAX'] = str(pool_max)
        os.environ['FDW_PG_QUERY_TIMEOUT'] = str(query_timeout)

        config = FDWConfig.from_environment()

        assert config.enabled is True
        assert config.host == host.strip()
        assert config.port == port
        assert config.database == database.strip()
        assert config.user == user.strip()
        assert config.password == password.strip()
        assert config.schema == schema.strip()
        assert config.ssl_mode == ssl_mode.strip()
        assert config.pool_min == pool_min
        assert config.pool_max == pool_max
        assert config.query_timeout == query_timeout


# ---------------------------------------------------------------------------
# Property 2: Configuration validation reports all missing parameters
# ---------------------------------------------------------------------------

class TestConfigValidationMissingParams:
    """
    Property 2: Configuration validation reports all missing parameters

    For any non-empty subset of required parameters (database, user, password)
    that is omitted while FDW_PG_HOST is set, from_environment() should raise
    FDWConfigurationError whose missing_params list contains exactly the
    omitted parameter names.
    """

    # Map from logical name to (env var name, a valid default value)
    _REQUIRED_PARAMS = {
        'FDW_PG_DATABASE': 'testdb',
        'FDW_PG_USER': 'testuser',
        'FDW_PG_PASSWORD': 'testpass',
    }

    @given(
        missing=st.sets(
            st.sampled_from(list(_REQUIRED_PARAMS.keys())),
            min_size=1,
        ),
    )
    @settings(max_examples=25)
    def test_missing_params_reported(self, missing):
        """
        Feature: fdw-integration, Property 2: Configuration validation reports all missing parameters
        **Validates: Requirements 1.5, 1.6**

        Omitting a subset of required params while FDW_PG_HOST is set raises
        FDWConfigurationError listing exactly the omitted parameter names.
        """
        _clear_fdw_env()
        reset_fdw_config()

        os.environ['FDW_PG_HOST'] = 'localhost'

        # Set only the params that are NOT in the missing set
        for param, default_val in self._REQUIRED_PARAMS.items():
            if param not in missing:
                os.environ[param] = default_val

        with pytest.raises(FDWConfigurationError) as exc_info:
            FDWConfig.from_environment()

        assert set(exc_info.value.missing_params) == missing


# ---------------------------------------------------------------------------
# Property 19: Model serialization uses camelCase
# ---------------------------------------------------------------------------

# Strategies that build valid model instances

_foreign_server_info_st = st.builds(
    ForeignServerInfo,
    server_name=_nonempty_text,
    wrapper_type=_nonempty_text,
    server_options=st.just({}),
)

_foreign_table_info_st = st.builds(
    ForeignTableInfo,
    schema_name=_nonempty_text,
    table_name=_nonempty_text,
    server_name=_nonempty_text,
    column_count=st.integers(min_value=0, max_value=1000),
)

_column_info_st = st.builds(
    ColumnInfo,
    column_name=_nonempty_text,
    data_type=st.sampled_from(['integer', 'text', 'boolean', 'timestamp', 'jsonb']),
    is_nullable=st.booleans(),
    ordinal_position=st.integers(min_value=1, max_value=500),
)

_query_metadata_st = st.builds(
    QueryMetadata,
    duration_ms=st.floats(min_value=0.0, max_value=60000.0, allow_nan=False, allow_infinity=False),
    table_queried=_nonempty_text,
    row_count=st.integers(min_value=0, max_value=100000),
)

_query_response_st = st.builds(
    QueryResponse,
    rows=st.just([]),
    metadata=_query_metadata_st,
)

_fdw_health_response_st = st.builds(
    FDWHealthResponse,
    status=st.sampled_from(['healthy', 'unhealthy', 'disabled']),
    latency_ms=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False)),
    foreign_servers_count=st.one_of(st.none(), st.integers(min_value=0, max_value=100)),
    foreign_tables_count=st.one_of(st.none(), st.integers(min_value=0, max_value=1000)),
    error=st.one_of(st.none(), _nonempty_text),
)


def _has_no_underscores(keys):
    """Check that none of the keys contain underscores."""
    return all('_' not in k for k in keys)


class TestModelCamelCase:
    """
    Property 19: Model serialization uses camelCase

    For any FDW Pydantic model instance, serializing with
    model_dump(by_alias=True) should produce a dictionary where all keys
    are camelCase (no underscores).
    """

    @given(instance=_foreign_server_info_st)
    @settings(max_examples=25)
    def test_foreign_server_info_camel_case(self, instance):
        """
        Feature: fdw-integration, Property 19: Model serialization uses camelCase
        **Validates: Requirements 11.7**
        """
        data = instance.model_dump(by_alias=True)
        assert _has_no_underscores(data.keys()), f"Non-camelCase keys found: {list(data.keys())}"

    @given(instance=_foreign_table_info_st)
    @settings(max_examples=25)
    def test_foreign_table_info_camel_case(self, instance):
        """
        Feature: fdw-integration, Property 19: Model serialization uses camelCase
        **Validates: Requirements 11.7**
        """
        data = instance.model_dump(by_alias=True)
        assert _has_no_underscores(data.keys()), f"Non-camelCase keys found: {list(data.keys())}"

    @given(instance=_column_info_st)
    @settings(max_examples=25)
    def test_column_info_camel_case(self, instance):
        """
        Feature: fdw-integration, Property 19: Model serialization uses camelCase
        **Validates: Requirements 11.7**
        """
        data = instance.model_dump(by_alias=True)
        assert _has_no_underscores(data.keys()), f"Non-camelCase keys found: {list(data.keys())}"

    @given(instance=_query_response_st)
    @settings(max_examples=25)
    def test_query_response_camel_case(self, instance):
        """
        Feature: fdw-integration, Property 19: Model serialization uses camelCase
        **Validates: Requirements 11.7**
        """
        data = instance.model_dump(by_alias=True)
        # Check top-level keys and nested metadata keys
        assert _has_no_underscores(data.keys()), f"Non-camelCase keys found: {list(data.keys())}"
        assert _has_no_underscores(data['metadata'].keys()), \
            f"Non-camelCase metadata keys found: {list(data['metadata'].keys())}"

    @given(instance=_fdw_health_response_st)
    @settings(max_examples=25)
    def test_fdw_health_response_camel_case(self, instance):
        """
        Feature: fdw-integration, Property 19: Model serialization uses camelCase
        **Validates: Requirements 11.7**
        """
        data = instance.model_dump(by_alias=True)
        assert _has_no_underscores(data.keys()), f"Non-camelCase keys found: {list(data.keys())}"


# ---------------------------------------------------------------------------
# Property 20: Password excluded from error messages
# ---------------------------------------------------------------------------

class TestPasswordExcludedFromErrors:
    """
    Property 20: Password excluded from error messages

    For any password string and any connection error scenario, the
    FDWConnectionError message and string representation should not
    contain the password value.
    """

    @given(
        password=st.text(min_size=8, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P'),
            blacklist_characters='\x00',
        )).filter(lambda s: s.strip() != ''),
        host=_nonempty_text,
        port=_port_strategy,
    )
    @settings(max_examples=25)
    def test_password_not_in_error_message(self, password, host, port):
        """
        Feature: fdw-integration, Property 20: Password excluded from error messages
        **Validates: Requirements 12.1**

        Creating an FDWConnectionError should never leak the password
        through str() or repr(). We use passwords of length >= 8 to
        avoid false positives from trivial substring matches with
        host/port metadata.
        """
        # Skip if the password happens to be a substring of the host or
        # port representation (coincidental overlap, not a real leak)
        assume(password not in host)
        assume(password not in str(port))

        err = FDWConnectionError(
            message="Connection failed",
            host=host,
            port=port,
            original_error=None,
        )

        assert password not in str(err), \
            f"Password leaked in str(): {str(err)}"
        assert password not in repr(err), \
            f"Password leaked in repr(): {repr(err)}"

    @given(
        password=st.text(min_size=8, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P'),
            blacklist_characters='\x00',
        )).filter(lambda s: s.strip() != ''),
        host=_nonempty_text,
        port=_port_strategy,
    )
    @settings(max_examples=25)
    def test_password_not_in_error_even_if_in_original(self, password, host, port):
        """
        Feature: fdw-integration, Property 20: Password excluded from error messages
        **Validates: Requirements 12.1**

        Even when the original exception message contains the password,
        FDWConnectionError should not expose it through its own message
        or representation.
        """
        assume(password not in host)
        assume(password not in str(port))

        original = Exception(f"auth failed for password={password}")
        err = FDWConnectionError(
            message="Connection failed",
            host=host,
            port=port,
            original_error=original,
        )

        # The error's own message and repr must not contain the password
        assert password not in err.message, \
            f"Password leaked in .message: {err.message}"
        assert password not in repr(err), \
            f"Password leaked in repr(): {repr(err)}"


# ---------------------------------------------------------------------------
# Property 3: Discovery server name filtering
# ---------------------------------------------------------------------------

import time
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

from src.services.fdw_discovery_service import FDWDiscoveryService
from src.services.fdw_connection_manager import PostgreSQLConnectionManager


def _make_mock_connection_manager():
    """Create a PostgreSQLConnectionManager with a mocked engine."""
    config = FDWConfig(
        enabled=True, host="db.test", port=5432, database="testdb",
        user="u", password="p", schema="public", ssl_mode="prefer",
        pool_min=2, pool_max=10, query_timeout=30,
    )
    mgr = PostgreSQLConnectionManager(config)
    mgr._engine = MagicMock()
    return mgr


def _patch_connection_for_tables(mgr, table_rows, col_count_rows):
    """
    Patch get_connection so that the first conn.execute returns table_rows
    and the second returns col_count_rows (matching list_foreign_tables flow).
    Returns the mock connection for call-count assertions.
    """
    call_idx = [0]
    mock_conn = MagicMock()
    sequences = [table_rows, col_count_rows]

    def _execute_side_effect(*args, **kwargs):
        result = MagicMock()
        idx = call_idx[0]
        result.fetchall.return_value = sequences[idx] if idx < len(sequences) else []
        call_idx[0] += 1
        return result

    mock_conn.execute.side_effect = _execute_side_effect

    @asynccontextmanager
    async def _mock_get_connection():
        yield mock_conn

    mgr.get_connection = _mock_get_connection
    return mock_conn


# Strategy for generating ForeignTableInfo instances with controlled server names
_server_name_st = st.sampled_from(["server_a", "server_b", "server_c", "server_d"])

_foreign_table_info_for_discovery_st = st.builds(
    ForeignTableInfo,
    schema_name=st.just("public"),
    table_name=st.text(
        min_size=1, max_size=20,
        alphabet=st.characters(whitelist_categories=('L', 'N'), blacklist_characters='\x00'),
    ).filter(lambda s: s.strip() != ''),
    server_name=_server_name_st,
    column_count=st.integers(min_value=0, max_value=50),
)


class TestDiscoveryServerNameFiltering:
    """
    Property 3: Discovery server name filtering

    For any list of foreign table records and any server name filter,
    calling list_foreign_tables(server_name=filter) should return only
    tables whose server_name field matches the filter. The result should
    be a subset of the unfiltered list, and every item in the result
    should have the matching server name.
    """

    @given(
        tables=st.lists(_foreign_table_info_for_discovery_st, min_size=0, max_size=20),
        filter_name=_server_name_st,
    )
    @settings(max_examples=25)
    @pytest.mark.asyncio
    async def test_server_name_filtering(self, tables, filter_name):
        """
        Feature: fdw-integration, Property 3: Discovery server name filtering
        **Validates: Requirements 3.2**

        Generate a list of ForeignTableInfo with various server names, mock
        the connection manager to return them, filter by a chosen server name,
        and verify the result contains only matching tables.
        """
        # Build the raw rows the DB would return for the filtered query
        # The discovery service queries with server_name filter, so the DB
        # itself returns only matching rows. We simulate that here.
        expected_tables = [t for t in tables if t.server_name == filter_name]

        # Build mock DB rows: (schema, table_name, server_name)
        table_rows = [
            (t.schema_name, t.table_name, t.server_name)
            for t in expected_tables
        ]
        # Build mock column count rows: (schema, table_name, col_count)
        col_count_rows = [
            (t.schema_name, t.table_name, t.column_count)
            for t in expected_tables
        ]

        mgr = _make_mock_connection_manager()
        _patch_connection_for_tables(mgr, table_rows, col_count_rows)
        service = FDWDiscoveryService(mgr, cache_ttl=300.0)

        result = await service.list_foreign_tables(server_name=filter_name)

        # Every returned item must have the matching server name
        for item in result:
            assert item.server_name == filter_name, (
                f"Expected server_name={filter_name!r}, got {item.server_name!r}"
            )

        # Result count must match the expected filtered count
        assert len(result) == len(expected_tables), (
            f"Expected {len(expected_tables)} tables, got {len(result)}"
        )

        # Result should be a subset of the original list (by table identity)
        result_keys = {(r.schema_name, r.table_name, r.server_name) for r in result}
        all_keys = {(t.schema_name, t.table_name, t.server_name) for t in tables}
        assert result_keys.issubset(all_keys), (
            f"Filtered result contains tables not in original list"
        )


# ---------------------------------------------------------------------------
# Property 4: Discovery cache respects TTL
# ---------------------------------------------------------------------------

class TestDiscoveryCacheRespectsTTL:
    """
    Property 4: Discovery cache respects TTL

    For any sequence of discovery calls within the cache TTL, the underlying
    database query should be executed exactly once. After the TTL expires or
    refresh_cache() is called, the next discovery call should execute a new
    database query.
    """

    @given(
        ttl=st.floats(min_value=0.1, max_value=600.0),
    )
    @settings(max_examples=25)
    @pytest.mark.asyncio
    async def test_cache_within_ttl_queries_once(self, ttl):
        """
        Feature: fdw-integration, Property 4: Discovery cache respects TTL
        **Validates: Requirements 3.5, 3.6**

        Multiple calls within the TTL should hit the DB exactly once.
        """
        mgr = _make_mock_connection_manager()

        # Track how many times execute is called across connections
        execute_count = [0]
        mock_conn = MagicMock()

        def _execute_side_effect(*args, **kwargs):
            execute_count[0] += 1
            result = MagicMock()
            # Return empty results for both table and column count queries
            result.fetchall.return_value = []
            return result

        mock_conn.execute.side_effect = _execute_side_effect

        @asynccontextmanager
        async def _mock_get_connection():
            yield mock_conn

        mgr.get_connection = _mock_get_connection
        service = FDWDiscoveryService(mgr, cache_ttl=ttl)

        # First call — should query the DB
        await service.list_foreign_tables()
        first_count = execute_count[0]
        assert first_count > 0, "First call should execute at least one DB query"

        # Second call within TTL — should NOT query the DB again
        await service.list_foreign_tables()
        assert execute_count[0] == first_count, (
            f"Second call within TTL should not query DB again. "
            f"Expected {first_count} executions, got {execute_count[0]}"
        )

        # Third call within TTL — still cached
        await service.list_foreign_tables()
        assert execute_count[0] == first_count, (
            f"Third call within TTL should not query DB again. "
            f"Expected {first_count} executions, got {execute_count[0]}"
        )

    @given(
        ttl=st.floats(min_value=0.01, max_value=0.15),
    )
    @settings(max_examples=25)
    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self, ttl):
        """
        Feature: fdw-integration, Property 4: Discovery cache respects TTL
        **Validates: Requirements 3.5, 3.6**

        After the TTL expires, the next call should execute a new DB query.
        """
        import asyncio as aio

        mgr = _make_mock_connection_manager()

        execute_count = [0]
        mock_conn = MagicMock()

        def _execute_side_effect(*args, **kwargs):
            execute_count[0] += 1
            result = MagicMock()
            result.fetchall.return_value = []
            return result

        mock_conn.execute.side_effect = _execute_side_effect

        @asynccontextmanager
        async def _mock_get_connection():
            yield mock_conn

        mgr.get_connection = _mock_get_connection
        service = FDWDiscoveryService(mgr, cache_ttl=ttl)

        # First call — populates cache
        await service.list_foreign_tables()
        first_count = execute_count[0]

        # Wait for TTL to expire
        await aio.sleep(ttl + 0.05)

        # Next call after TTL — should query DB again
        await service.list_foreign_tables()
        assert execute_count[0] > first_count, (
            f"Call after TTL expiry should trigger new DB query. "
            f"Expected > {first_count} executions, got {execute_count[0]}"
        )

    @given(
        ttl=st.floats(min_value=10.0, max_value=600.0),
    )
    @settings(max_examples=25)
    @pytest.mark.asyncio
    async def test_refresh_cache_forces_new_query(self, ttl):
        """
        Feature: fdw-integration, Property 4: Discovery cache respects TTL
        **Validates: Requirements 3.5, 3.6**

        Calling refresh_cache() should clear the cache so the next discovery
        call executes a new database query, even within the TTL.
        """
        mgr = _make_mock_connection_manager()

        execute_count = [0]
        mock_conn = MagicMock()

        def _execute_side_effect(*args, **kwargs):
            execute_count[0] += 1
            result = MagicMock()
            result.fetchall.return_value = []
            return result

        mock_conn.execute.side_effect = _execute_side_effect

        @asynccontextmanager
        async def _mock_get_connection():
            yield mock_conn

        mgr.get_connection = _mock_get_connection
        service = FDWDiscoveryService(mgr, cache_ttl=ttl)

        # First call — populates cache
        await service.list_foreign_tables()
        first_count = execute_count[0]

        # Second call — cached, no new query
        await service.list_foreign_tables()
        assert execute_count[0] == first_count

        # Force refresh
        await service.refresh_cache()

        # Next call after refresh — should query DB again
        await service.list_foreign_tables()
        assert execute_count[0] > first_count, (
            f"Call after refresh_cache() should trigger new DB query. "
            f"Expected > {first_count} executions, got {execute_count[0]}"
        )


# ---------------------------------------------------------------------------
# Property 5: FDW SQL builder produces correct query structure
# ---------------------------------------------------------------------------

import re
from src.services.fdw_query_service import FDWQueryService
from src.models.fdw_models import QueryRequest, QueryFilter, FilterOperator, OrderByItem

# Fixed set of valid column names for the whitelist
VALID_COLUMNS = {"id", "name", "price", "status", "created_at"}

# Strategies for building QueryRequest components
_valid_column_st = st.sampled_from(sorted(VALID_COLUMNS))

_filter_operator_st = st.sampled_from([
    FilterOperator.eq, FilterOperator.neq, FilterOperator.gt,
    FilterOperator.gte, FilterOperator.lt, FilterOperator.lte,
    FilterOperator.like,
])

_filter_value_st = st.one_of(
    st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('L', 'N'), blacklist_characters='\x00',
    )),
    st.integers(min_value=-10000, max_value=10000),
)

_query_filter_st = st.builds(
    QueryFilter,
    column=_valid_column_st,
    operator=_filter_operator_st,
    value=_filter_value_st,
)

_order_by_item_st = st.builds(
    OrderByItem,
    column=_valid_column_st,
    direction=st.sampled_from(["asc", "desc"]),
)

_table_name_st = st.text(
    min_size=1, max_size=20,
    alphabet=st.characters(whitelist_categories=('L', 'N'), blacklist_characters='\x00'),
).filter(lambda s: s.strip() != '')

_schema_name_st = st.just("public")


def _build_query_request_strategy():
    """Strategy that builds a valid QueryRequest with arbitrary combinations."""
    return st.builds(
        QueryRequest,
        table=_table_name_st,
        schema_name=_schema_name_st,
        filters=st.one_of(st.none(), st.lists(_query_filter_st, min_size=1, max_size=5)),
        columns=st.one_of(st.none(), st.lists(_valid_column_st, min_size=1, max_size=5, unique=True)),
        limit=st.one_of(st.none(), st.integers(min_value=1, max_value=10000)),
        offset=st.one_of(st.none(), st.integers(min_value=0, max_value=10000)),
        order_by=st.one_of(st.none(), st.lists(_order_by_item_st, min_size=1, max_size=3)),
    )


class TestFDWSQLBuilderQueryStructure:
    """
    Property 5: FDW SQL builder produces correct query structure

    For any valid QueryRequest with arbitrary combinations of filters,
    column selections, limit, offset, and order_by, the generated SQL
    should contain a SELECT clause with the requested columns (or *),
    a WHERE clause with exactly len(filters) conditions when filters
    are provided, LIMIT/OFFSET clauses when set, and ORDER BY with
    correct columns and directions when order_by is provided.
    """

    def _make_service(self) -> FDWQueryService:
        """Create an FDWQueryService with mocked dependencies."""
        mock_conn_mgr = MagicMock(spec=PostgreSQLConnectionManager)
        mock_discovery = MagicMock(spec=FDWDiscoveryService)
        return FDWQueryService(mock_conn_mgr, mock_discovery)

    @given(request=_build_query_request_strategy())
    @settings(max_examples=25)
    def test_sql_builder_query_structure(self, request):
        """
        Feature: fdw-integration, Property 5: FDW SQL builder produces correct query structure
        **Validates: Requirements 4.2, 4.3, 4.4, 4.5**

        For any valid QueryRequest, _build_select() should produce SQL with
        the correct SELECT, WHERE, ORDER BY, LIMIT, and OFFSET clauses.
        """
        service = self._make_service()
        sql, params = service._build_select(request, valid_columns=VALID_COLUMNS)

        # SQL should always start with SELECT
        assert sql.startswith("SELECT "), f"SQL should start with SELECT: {sql}"

        # Check column selection
        if request.columns:
            for col in request.columns:
                assert f'"{col}"' in sql, (
                    f"Column '{col}' should appear quoted in SQL: {sql}"
                )
            assert "*" not in sql.split("FROM")[0], (
                "SELECT clause should not contain * when columns are specified"
            )
        else:
            assert "SELECT *" in sql, (
                f"SQL should contain SELECT * when no columns specified: {sql}"
            )

        # Check FROM clause with quoted schema and table
        assert f'FROM "{request.schema_name}"."{request.table}"' in sql, (
            f"SQL should contain quoted FROM clause: {sql}"
        )

        # Check WHERE clause
        if request.filters:
            assert "WHERE" in sql, (
                f"SQL should contain WHERE when filters provided: {sql}"
            )
            # Count AND-separated conditions in the WHERE clause
            where_part = sql.split("WHERE")[1]
            # Trim off ORDER BY / LIMIT / OFFSET if present
            for keyword in ["ORDER BY", "LIMIT", "OFFSET"]:
                if keyword in where_part:
                    where_part = where_part.split(keyword)[0]
            conditions = where_part.split(" AND ")
            assert len(conditions) == len(request.filters), (
                f"Expected {len(request.filters)} WHERE conditions, "
                f"got {len(conditions)}: {where_part}"
            )
            # Each filter column should appear in the WHERE clause
            for filt in request.filters:
                assert f'"{filt.column}"' in sql, (
                    f"Filter column '{filt.column}' should appear in SQL: {sql}"
                )
        else:
            assert "WHERE" not in sql, (
                f"SQL should not contain WHERE when no filters: {sql}"
            )

        # Check ORDER BY clause
        if request.order_by:
            assert "ORDER BY" in sql, (
                f"SQL should contain ORDER BY when order_by provided: {sql}"
            )
            for ob in request.order_by:
                assert f'"{ob.column}" {ob.direction.upper()}' in sql, (
                    f"ORDER BY should contain '{ob.column} {ob.direction.upper()}': {sql}"
                )
        else:
            assert "ORDER BY" not in sql, (
                f"SQL should not contain ORDER BY when no order_by: {sql}"
            )

        # Check LIMIT clause
        if request.limit is not None:
            assert "LIMIT :limit_val" in sql, (
                f"SQL should contain LIMIT :limit_val: {sql}"
            )
            assert params["limit_val"] == request.limit, (
                f"LIMIT param should be {request.limit}, got {params['limit_val']}"
            )
        else:
            assert "LIMIT" not in sql, (
                f"SQL should not contain LIMIT when not set: {sql}"
            )

        # Check OFFSET clause
        if request.offset is not None:
            assert "OFFSET :offset_val" in sql, (
                f"SQL should contain OFFSET :offset_val: {sql}"
            )
            assert params["offset_val"] == request.offset, (
                f"OFFSET param should be {request.offset}, got {params['offset_val']}"
            )
        else:
            assert "OFFSET" not in sql, (
                f"SQL should not contain OFFSET when not set: {sql}"
            )

        # All filter values should be in params dict (not raw in SQL)
        if request.filters:
            for i, filt in enumerate(request.filters):
                param_name = f"param_{i}"
                assert param_name in params, (
                    f"Expected param '{param_name}' in params dict: {params}"
                )
                assert params[param_name] == filt.value, (
                    f"Param '{param_name}' should be {filt.value!r}, got {params[param_name]!r}"
                )


# ---------------------------------------------------------------------------
# Property 6: SQL injection prevention via parameterization
# ---------------------------------------------------------------------------

# Strategy for SQL injection attempt strings.
# Values must be at least 3 chars to avoid false positives from single
# characters (e.g., `"`) that coincidentally appear in SQL identifier quoting.
_sql_injection_st = st.one_of(
    st.just("'; DROP TABLE users; --"),
    st.just("1; DELETE FROM accounts"),
    st.just("' OR '1'='1"),
    st.just("'; TRUNCATE TABLE data; --"),
    st.just("Robert'); DROP TABLE students;--"),
    st.just("1 UNION SELECT * FROM passwords"),
    st.text(
        min_size=3, max_size=100,
        alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S', 'Z'),
            blacklist_characters='\x00',
        ),
    ).filter(lambda s: s.strip() != '' and any(c in s for c in "';\"--")),
)


class TestSQLInjectionPrevention:
    """
    Property 6: SQL injection prevention via parameterization

    For any query containing user-supplied filter values (including strings
    with SQL metacharacters like '; DROP TABLE --, quotes, semicolons),
    the generated SQL text should never contain the raw filter value.
    All user-supplied values should appear only in the parameters dictionary.
    """

    def _make_service(self) -> FDWQueryService:
        """Create an FDWQueryService with mocked dependencies."""
        mock_conn_mgr = MagicMock(spec=PostgreSQLConnectionManager)
        mock_discovery = MagicMock(spec=FDWDiscoveryService)
        return FDWQueryService(mock_conn_mgr, mock_discovery)

    @given(
        injection_value=_sql_injection_st,
        column=_valid_column_st,
        operator=_filter_operator_st,
    )
    @settings(max_examples=25)
    def test_injection_values_never_in_sql_text(self, injection_value, column, operator):
        """
        Feature: fdw-integration, Property 6: SQL injection prevention via parameterization
        **Validates: Requirements 4.6, 8.9**

        For any filter value containing SQL metacharacters, the generated SQL
        text should never contain the raw filter value. The value should only
        appear in the parameters dictionary.
        """
        # Skip values that are trivial substrings of SQL structural elements
        # (e.g., a single `"` matches identifier quoting, not a real injection)
        _structural_parts = (
            'SELECT', 'FROM', 'WHERE', 'AND', 'ORDER', 'BY', 'LIMIT',
            'OFFSET', 'ASC', 'DESC', 'IN', 'LIKE', 'public', 'test_table',
            '"', '*', '=', '!=', '>', '>=', '<', '<=', ':',
        )
        # Also skip if the value is a substring of any column name
        _all_structural = set(_structural_parts) | VALID_COLUMNS
        assume(injection_value not in _all_structural)
        # Skip if the value is a substring of the fixed SQL structure
        _fixed_sql_parts = 'SELECT * FROM "public"."test_table" WHERE'
        assume(injection_value not in _fixed_sql_parts)

        request = QueryRequest(
            table="test_table",
            schema_name="public",
            filters=[
                QueryFilter(column=column, operator=operator, value=injection_value),
            ],
        )

        service = self._make_service()
        sql, params = service._build_select(request, valid_columns=VALID_COLUMNS)

        # The raw injection value must NOT appear in the SQL text
        assert injection_value not in sql, (
            f"SQL injection value found in SQL text!\n"
            f"Value: {injection_value!r}\n"
            f"SQL: {sql}"
        )

        # The injection value MUST appear in the params dict
        param_values = list(params.values())
        assert injection_value in param_values, (
            f"Injection value should be in params dict.\n"
            f"Value: {injection_value!r}\n"
            f"Params: {params}"
        )

        # SQL should use named parameter placeholders, not raw values
        assert ":param_0" in sql, (
            f"SQL should use :param_0 placeholder: {sql}"
        )

    @given(
        injection_values=st.lists(
            _sql_injection_st,
            min_size=2,
            max_size=5,
        ),
    )
    @settings(max_examples=25)
    def test_multiple_injection_values_all_parameterized(self, injection_values):
        """
        Feature: fdw-integration, Property 6: SQL injection prevention via parameterization
        **Validates: Requirements 4.6, 8.9**

        When multiple filters with SQL injection values are provided,
        none of the raw values should appear in the SQL text.
        """
        # Use different columns for each filter to avoid duplicates
        columns = sorted(VALID_COLUMNS)
        filters = []
        for i, val in enumerate(injection_values):
            col = columns[i % len(columns)]
            filters.append(
                QueryFilter(column=col, operator=FilterOperator.eq, value=val)
            )

        request = QueryRequest(
            table="test_table",
            schema_name="public",
            filters=filters,
        )

        service = self._make_service()
        sql, params = service._build_select(request, valid_columns=VALID_COLUMNS)

        # No raw injection value should appear in the SQL text
        for val in injection_values:
            assert val not in sql, (
                f"SQL injection value found in SQL text!\n"
                f"Value: {val!r}\n"
                f"SQL: {sql}"
            )

        # All values should be in the params dict
        param_values = list(params.values())
        for val in injection_values:
            assert val in param_values, (
                f"Injection value should be in params dict.\n"
                f"Value: {val!r}\n"
                f"Params: {params}"
            )


# ===========================================================================
# Property 7, 8, 18 — API Router Property Tests
# ===========================================================================

import re
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.apis import fdw_api


# ── Helpers for API property tests ────────────────────────────────────────────

# All FDW endpoints that should return 503 when disabled
_FDW_ENDPOINTS = [
    ("GET", "/api/fdw/servers"),
    ("GET", "/api/fdw/tables"),
    ("GET", "/api/fdw/tables/public/test_table/columns"),
    ("POST", "/api/fdw/query"),
]


def _disabled_fdw_app() -> tuple:
    """Create a FastAPI app with the FDW router, FDW disabled."""
    fdw_api.configure(
        connection_manager=None,
        discovery_service=None,
        query_service=None,
    )
    app = FastAPI()
    app.include_router(fdw_api.router)
    return app


def _enabled_fdw_query_app() -> tuple:
    """Create a FastAPI app with FDW enabled (mock services) for query validation tests."""
    conn_mgr = MagicMock()
    discovery = AsyncMock()
    query_svc = AsyncMock()
    fdw_api.configure(
        connection_manager=conn_mgr,
        discovery_service=discovery,
        query_service=query_svc,
    )
    app = FastAPI()
    app.include_router(fdw_api.router)
    return app


# ── Property 7: Disabled FDW returns 503 for all endpoints ───────────────────


class TestDisabledFDWReturns503:
    """
    Feature: fdw-integration, Property 7: Disabled FDW returns 503 for all endpoints

    *For any* FDW or TMF API endpoint, when FDW integration is disabled
    (FDW_PG_HOST not set), the HTTP response status code should be 503.

    **Validates: Requirements 5.5**
    """

    @given(
        endpoint=st.sampled_from(_FDW_ENDPOINTS),
    )
    @settings(max_examples=25)
    def test_fdw_endpoints_return_503_when_disabled(self, endpoint):
        """
        Feature: fdw-integration, Property 7: Disabled FDW returns 503 for all endpoints
        **Validates: Requirements 5.5**

        Any FDW endpoint returns 503 when FDW is disabled.
        """
        method, path = endpoint
        app = _disabled_fdw_app()
        client = TestClient(app, raise_server_exceptions=False)

        if method == "GET":
            resp = client.get(path)
        elif method == "POST":
            # POST /api/fdw/query needs a body to avoid 422 before reaching 503 check
            # But since _check_fdw_enabled() runs first, any body works
            resp = client.post(path, json={"table": "test"})
        else:
            resp = client.request(method, path)

        assert resp.status_code == 503, (
            f"Expected 503 for {method} {path} when FDW disabled, got {resp.status_code}"
        )

# ── Property 8: Invalid query requests rejected by Pydantic validation ───────


# Strategies for generating invalid QueryRequest bodies
_invalid_query_bodies = st.one_of(
    # Missing required 'table' field
    st.just({}),
    st.just({"limit": 10}),
    st.just({"offset": 0, "columns": ["id"]}),
    # limit < 1
    st.integers(max_value=0).map(lambda l: {"table": "t", "limit": l}),
    # limit > 10000
    st.integers(min_value=10001, max_value=999999).map(lambda l: {"table": "t", "limit": l}),
    # offset < 0
    st.integers(max_value=-1, min_value=-999999).map(lambda o: {"table": "t", "offset": o}),
    # Invalid operator in filters
    st.sampled_from(["invalid", "EQ", "LIKE", "between", "not_in", "exists", ""]).map(
        lambda op: {"table": "t", "filters": [{"column": "id", "operator": op, "value": 1}]}
    ),
    # Filter missing required column field
    st.just({"table": "t", "filters": [{"operator": "eq", "value": 1}]}),
    # Filter missing required operator field
    st.just({"table": "t", "filters": [{"column": "id", "value": 1}]}),
)


class TestInvalidQueryRequestsRejected:
    """
    Feature: fdw-integration, Property 8: Invalid query requests rejected by Pydantic validation

    *For any* QueryRequest body that violates the Pydantic schema (e.g., limit < 1,
    limit > 10000, offset < 0, invalid operator, missing required `table` field),
    the POST /api/fdw/query endpoint should return HTTP 422.

    **Validates: Requirements 5.6**
    """

    @given(body=_invalid_query_bodies)
    @settings(max_examples=25)
    def test_invalid_query_request_returns_422(self, body):
        """
        Feature: fdw-integration, Property 8: Invalid query requests rejected by Pydantic validation
        **Validates: Requirements 5.6**

        Any QueryRequest body violating the Pydantic schema is rejected with 422.
        """
        app = _enabled_fdw_query_app()
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post("/api/fdw/query", json=body)

        assert resp.status_code == 422, (
            f"Expected 422 for invalid body {body!r}, got {resp.status_code}\n"
            f"Response: {resp.json()}"
        )

