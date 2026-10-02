"""
Property-based tests for Data Plane service.

Feature: ai-data-plane
Properties 1, 2, 5, 6, 7

Tests DataPlaneService CRUD operations against a moto-mocked DynamoDB backend
using hypothesis strategies to generate random valid/invalid requests.
"""

import asyncio
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import boto3
import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from hypothesis.strategies import composite
from moto import mock_dynamodb
from pydantic import ValidationError

from src.models.data_plane_models import (
    DataPlaneCreateRequest,
    DataPlaneStatus,
    DataPlaneType,
    DataPlaneUpdateRequest,
)
from src.services.data_plane_service import DataPlaneService
from src.utils.data_plane_errors import DataPlaneValidationError


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TABLE_NAME = "test-foundry-workspace"
REGION = "us-east-1"
_FDW_REQUIRED_FIELDS = ["host", "port", "database", "user", "password"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_table():
    """Create the foundry-workspace shaped DDB table (PK/SK + GSI1) inside moto."""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )


def _make_service() -> DataPlaneService:
    """Create a DataPlaneService pointing at the test table."""
    svc = DataPlaneService(table_name=TABLE_NAME)
    svc._region = REGION
    return svc


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_safe_text = st.text(
    min_size=1,
    max_size=30,
    alphabet=st.characters(whitelist_categories=("L", "N"), blacklist_characters="\x00"),
).filter(lambda s: s.strip() != "")

_data_plane_type_st = st.sampled_from(list(DataPlaneType))

_fdw_connection_config_st = st.fixed_dictionaries({
    "host": _safe_text,
    "port": st.integers(min_value=1, max_value=65535),
    "database": _safe_text,
    "user": _safe_text,
    "password": _safe_text,
})

_cdc_connection_config_st = st.fixed_dictionaries({
    "bootstrapServers": _safe_text,
    "topicPrefix": _safe_text,
    "sourceDatabase": _safe_text,
})

_etl_connection_config_st = st.fixed_dictionaries({
    "sourceType": _safe_text,
    "schedule": _safe_text,
    "transformationEngine": _safe_text,
})


def _connection_config_for_type(dp_type: DataPlaneType):
    """Return a strategy for connectionConfig matching the given type."""
    if dp_type == DataPlaneType.FDW:
        return _fdw_connection_config_st
    elif dp_type == DataPlaneType.CDC:
        return _cdc_connection_config_st
    else:
        return _etl_connection_config_st


@composite
def valid_create_request_st(draw):
    """Generate a valid DataPlaneCreateRequest for any type."""
    dp_type = draw(_data_plane_type_st)
    config = draw(_connection_config_for_type(dp_type))
    name = draw(_safe_text)
    return DataPlaneCreateRequest(name=name, type=dp_type, connection_config=config)


@composite
def valid_fdw_create_request_st(draw):
    """Generate a valid FDW DataPlaneCreateRequest."""
    config = draw(_fdw_connection_config_st)
    name = draw(_safe_text)
    return DataPlaneCreateRequest(name=name, type=DataPlaneType.FDW, connection_config=config)


@composite
def valid_cdc_or_etl_create_request_st(draw):
    """Generate a valid CDC or ETL DataPlaneCreateRequest."""
    dp_type = draw(st.sampled_from([DataPlaneType.CDC, DataPlaneType.ETL]))
    config = draw(_connection_config_for_type(dp_type))
    name = draw(_safe_text)
    return DataPlaneCreateRequest(name=name, type=dp_type, connection_config=config)


@composite
def valid_update_request_st(draw):
    """Generate a valid DataPlaneUpdateRequest with at least one field set."""
    name = draw(st.one_of(st.none(), _safe_text))
    status = draw(st.one_of(st.none(), st.sampled_from(list(DataPlaneStatus))))
    config = draw(st.one_of(st.none(), _fdw_connection_config_st))
    # Ensure at least one field is set
    if name is None and status is None and config is None:
        name = draw(_safe_text)
    return DataPlaneUpdateRequest(name=name, status=status, connection_config=config)



# ---------------------------------------------------------------------------
# Property 1: CRUD round-trip consistency
# ---------------------------------------------------------------------------


class TestCRUDRoundTripConsistency:
    """
    Property 1: CRUD round-trip consistency

    For any valid DataPlaneCreateRequest (with valid name, type, and
    connectionConfig), creating a data plane via the service and then
    retrieving it via get() by the returned ID should produce a
    DataPlaneResponse with matching name, type, and connectionConfig fields.
    """

    @given(request=valid_create_request_st())
    @settings(max_examples=5, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @mock_dynamodb
    def test_create_then_get_matches(self, request):
        """
        Feature: ai-data-plane, Property 1: CRUD round-trip consistency
        **Validates: Requirements 1.2, 2.1, 2.3**
        """
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = REGION

        _create_table()
        svc = _make_service()
        _run(svc.initialize())

        created = _run(svc.create(request))
        fetched = _run(svc.get(created.id))

        assert fetched.name == request.name
        assert fetched.type == request.type
        assert fetched.connection_config == request.connection_config
        assert fetched.id == created.id


# ---------------------------------------------------------------------------
# Property 2: Invalid creation requests are rejected
# ---------------------------------------------------------------------------


class TestInvalidCreationRejected:
    """
    Property 2: Invalid creation requests are rejected

    For any DataPlaneCreateRequest with an empty name, or an invalid type
    value, or (for FDW type) a connectionConfig missing required fields
    (host, port, database, user, password), the creation should raise a
    validation error, and no record should be stored.
    """

    @given(
        missing_field=st.sampled_from(_FDW_REQUIRED_FIELDS),
        config=_fdw_connection_config_st,
        name=_safe_text,
    )
    @settings(max_examples=5, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @mock_dynamodb
    def test_fdw_missing_required_field_rejected(self, missing_field, config, name):
        """
        Feature: ai-data-plane, Property 2: Invalid creation requests are rejected
        **Validates: Requirements 1.3, 2.7, 3.1, 6.4**

        FDW type with a missing required connection field should raise
        DataPlaneValidationError and store no record.
        """
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = REGION

        _create_table()
        svc = _make_service()
        _run(svc.initialize())

        # Remove one required field
        bad_config = {k: v for k, v in config.items() if k != missing_field}
        req = DataPlaneCreateRequest(
            name=name, type=DataPlaneType.FDW, connection_config=bad_config
        )

        with pytest.raises(DataPlaneValidationError):
            _run(svc.create(req))

        # Verify nothing was stored
        all_items = _run(svc.list_all())
        assert len(all_items) == 0

    @given(data=st.data())
    @settings(max_examples=5)
    def test_empty_name_rejected_at_model_level(self, data):
        """
        Feature: ai-data-plane, Property 2: Invalid creation requests are rejected
        **Validates: Requirements 1.3, 2.7, 3.1, 6.4**

        Empty name should be rejected by Pydantic validation before
        reaching the service.
        """
        dp_type = data.draw(_data_plane_type_st)
        config = data.draw(_connection_config_for_type(dp_type))

        with pytest.raises(ValidationError):
            DataPlaneCreateRequest(name="", type=dp_type, connection_config=config)

    @given(invalid_type=_safe_text.filter(lambda s: s not in ("FDW", "CDC", "ETL")))
    @settings(max_examples=5)
    def test_invalid_type_rejected_at_model_level(self, invalid_type):
        """
        Feature: ai-data-plane, Property 2: Invalid creation requests are rejected
        **Validates: Requirements 1.3, 2.7, 3.1, 6.4**

        Invalid type value should be rejected by Pydantic validation.
        """
        with pytest.raises(ValidationError):
            DataPlaneCreateRequest(
                name="test",
                type=invalid_type,
                connection_config={"host": "localhost"},
            )


# ---------------------------------------------------------------------------
# Property 5: List returns all created records
# ---------------------------------------------------------------------------


class TestListReturnsAllCreated:
    """
    Property 5: List returns all created records

    For any sequence of N valid data plane creations (with distinct names),
    the list_all() method should return a list containing at least N records,
    and every created ID should appear in the list.
    """

    @given(requests=st.lists(valid_create_request_st(), min_size=1, max_size=3))
    @settings(
        max_examples=5, deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    )
    @mock_dynamodb
    def test_list_contains_all_created_ids(self, requests):
        """
        Feature: ai-data-plane, Property 5: List returns all created records
        **Validates: Requirements 2.2**
        """
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = REGION

        _create_table()
        svc = _make_service()
        _run(svc.initialize())

        created_ids = set()
        for req in requests:
            resp = _run(svc.create(req))
            created_ids.add(resp.id)

        all_items = _run(svc.list_all())
        listed_ids = {item.id for item in all_items}

        assert len(all_items) >= len(requests)
        assert created_ids.issubset(listed_ids)


# ---------------------------------------------------------------------------
# Property 6: Update changes updatedAt timestamp
# ---------------------------------------------------------------------------


class TestUpdateChangesTimestamp:
    """
    Property 6: Update changes updatedAt timestamp

    For any existing data plane and any valid update request, the updatedAt
    field of the returned record should be greater than or equal to the
    updatedAt field before the update.
    """

    @given(
        create_req=valid_create_request_st(),
        update_req=valid_update_request_st(),
    )
    @settings(
        max_examples=5, deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @mock_dynamodb
    def test_updated_at_advances_on_update(self, create_req, update_req):
        """
        Feature: ai-data-plane, Property 6: Update changes updatedAt timestamp
        **Validates: Requirements 1.4, 2.4**
        """
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = REGION

        _create_table()
        svc = _make_service()
        _run(svc.initialize())

        created = _run(svc.create(create_req))
        original_updated_at = created.updated_at

        updated = _run(svc.update(created.id, update_req))

        assert updated.updated_at >= original_updated_at


# ---------------------------------------------------------------------------
# Property 7: CDC and ETL data planes default to pending status
# ---------------------------------------------------------------------------


class TestCDCETLDefaultPending:
    """
    Property 7: CDC and ETL data planes default to pending status

    For any DataPlaneCreateRequest with type CDC or ETL, the created
    DataPlaneResponse should have status "pending".
    """

    @given(request=valid_cdc_or_etl_create_request_st())
    @settings(
        max_examples=5, deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @mock_dynamodb
    def test_cdc_etl_status_is_pending(self, request):
        """
        Feature: ai-data-plane, Property 7: CDC and ETL data planes default to pending status
        **Validates: Requirements 4.1, 4.2**
        """
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = REGION

        _create_table()
        svc = _make_service()
        _run(svc.initialize())

        created = _run(svc.create(request))

        assert created.status == DataPlaneStatus.pending
        assert request.type in (DataPlaneType.CDC, DataPlaneType.ETL)
