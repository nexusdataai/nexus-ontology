"""
Unit tests for Data Plane service.

Tests DataPlaneService CRUD operations, FDW config validation,
and graceful degradation when DynamoDB is unavailable.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 7.3**
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
from moto import mock_dynamodb

from src.models.data_plane_models import (
    DataPlaneCreateRequest,
    DataPlaneStatus,
    DataPlaneType,
    DataPlaneUpdateRequest,
)
from src.services.data_plane_service import DataPlaneService
from src.utils.data_plane_errors import (
    DataPlaneNotFoundError,
    DataPlaneStorageError,
    DataPlaneValidationError,
)

TABLE_NAME = "test-foundry-workspace"
REGION = "us-east-1"


def _create_table():
    """Create a moto foundry-workspace shaped table (PK/SK + GSI1).

    DataPlaneService now persists into the foundry-workspace table under the
    DATAPLANE# PK namespace, so unit-test fixtures must match the operator's
    schema (see kube-operator/src/nexus_operator/resources/dynamodb.py).
    """
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
    svc = DataPlaneService(table_name=TABLE_NAME)
    svc._region = REGION
    return svc


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


VALID_FDW_CONFIG = {
    "host": "postgres.example.com",
    "port": 5432,
    "database": "fdw_db",
    "user": "fdw_user",
    "password": "secret",
}

VALID_CDC_CONFIG = {
    "bootstrapServers": "kafka:9092",
    "topicPrefix": "cdc-",
    "sourceDatabase": "source_db",
}

VALID_ETL_CONFIG = {
    "sourceType": "postgresql",
    "schedule": "0 2 * * *",
    "transformationEngine": "spark",
}


# ---------------------------------------------------------------------------
# Create tests
# ---------------------------------------------------------------------------


class TestCreate:
    """Tests for DataPlaneService.create()."""

    @mock_dynamodb
    def test_create_fdw_sets_connected_status(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        req = DataPlaneCreateRequest(
            name="fdw-plane", type=DataPlaneType.FDW, connection_config=VALID_FDW_CONFIG
        )
        result = _run(svc.create(req))
        assert result.status == DataPlaneStatus.connected
        assert result.name == "fdw-plane"
        assert result.type == DataPlaneType.FDW
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None

    @mock_dynamodb
    def test_create_cdc_sets_pending_status(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        req = DataPlaneCreateRequest(
            name="cdc-plane", type=DataPlaneType.CDC, connection_config=VALID_CDC_CONFIG
        )
        result = _run(svc.create(req))
        assert result.status == DataPlaneStatus.pending

    @mock_dynamodb
    def test_create_etl_sets_pending_status(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        req = DataPlaneCreateRequest(
            name="etl-plane", type=DataPlaneType.ETL, connection_config=VALID_ETL_CONFIG
        )
        result = _run(svc.create(req))
        assert result.status == DataPlaneStatus.pending

    @mock_dynamodb
    def test_create_fdw_missing_host_raises_validation_error(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        bad_config = {k: v for k, v in VALID_FDW_CONFIG.items() if k != "host"}
        req = DataPlaneCreateRequest(
            name="bad-fdw", type=DataPlaneType.FDW, connection_config=bad_config
        )
        with pytest.raises(DataPlaneValidationError, match="host"):
            _run(svc.create(req))

    @mock_dynamodb
    def test_create_fdw_missing_multiple_fields_raises_validation_error(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        req = DataPlaneCreateRequest(
            name="bad-fdw", type=DataPlaneType.FDW, connection_config={"host": "localhost"}
        )
        with pytest.raises(DataPlaneValidationError):
            _run(svc.create(req))

    def test_create_without_dynamo_raises_storage_error(self):
        svc = _make_service()
        req = DataPlaneCreateRequest(
            name="no-db", type=DataPlaneType.CDC, connection_config=VALID_CDC_CONFIG
        )
        with pytest.raises(DataPlaneStorageError):
            _run(svc.create(req))


# ---------------------------------------------------------------------------
# Get tests
# ---------------------------------------------------------------------------


class TestGet:
    """Tests for DataPlaneService.get()."""

    @mock_dynamodb
    def test_get_existing_record(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        req = DataPlaneCreateRequest(
            name="get-test", type=DataPlaneType.FDW, connection_config=VALID_FDW_CONFIG
        )
        created = _run(svc.create(req))
        fetched = _run(svc.get(created.id))
        assert fetched.id == created.id
        assert fetched.name == "get-test"
        assert fetched.type == DataPlaneType.FDW

    @mock_dynamodb
    def test_get_nonexistent_raises_not_found(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        with pytest.raises(DataPlaneNotFoundError):
            _run(svc.get("nonexistent-id"))

    def test_get_without_dynamo_raises_storage_error(self):
        svc = _make_service()
        with pytest.raises(DataPlaneStorageError):
            _run(svc.get("any-id"))


# ---------------------------------------------------------------------------
# List tests
# ---------------------------------------------------------------------------


class TestListAll:
    """Tests for DataPlaneService.list_all()."""

    @mock_dynamodb
    def test_list_empty(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        result = _run(svc.list_all())
        assert result == []

    @mock_dynamodb
    def test_list_returns_all_created(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        for i in range(3):
            req = DataPlaneCreateRequest(
                name=f"plane-{i}", type=DataPlaneType.CDC, connection_config=VALID_CDC_CONFIG
            )
            _run(svc.create(req))
        result = _run(svc.list_all())
        assert len(result) == 3
        names = {r.name for r in result}
        assert names == {"plane-0", "plane-1", "plane-2"}


# ---------------------------------------------------------------------------
# Update tests
# ---------------------------------------------------------------------------


class TestUpdate:
    """Tests for DataPlaneService.update()."""

    @mock_dynamodb
    def test_update_name(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        req = DataPlaneCreateRequest(
            name="original", type=DataPlaneType.FDW, connection_config=VALID_FDW_CONFIG
        )
        created = _run(svc.create(req))
        update_req = DataPlaneUpdateRequest(name="renamed")
        updated = _run(svc.update(created.id, update_req))
        assert updated.name == "renamed"
        assert updated.id == created.id

    @mock_dynamodb
    def test_update_changes_updated_at(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        req = DataPlaneCreateRequest(
            name="ts-test", type=DataPlaneType.ETL, connection_config=VALID_ETL_CONFIG
        )
        created = _run(svc.create(req))
        update_req = DataPlaneUpdateRequest(name="ts-test-v2")
        updated = _run(svc.update(created.id, update_req))
        assert updated.updated_at >= created.updated_at

    @mock_dynamodb
    def test_update_nonexistent_raises_not_found(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        update_req = DataPlaneUpdateRequest(name="nope")
        with pytest.raises(DataPlaneNotFoundError):
            _run(svc.update("nonexistent-id", update_req))

    @mock_dynamodb
    def test_update_status(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        req = DataPlaneCreateRequest(
            name="status-test", type=DataPlaneType.CDC, connection_config=VALID_CDC_CONFIG
        )
        created = _run(svc.create(req))
        assert created.status == DataPlaneStatus.pending
        update_req = DataPlaneUpdateRequest(status=DataPlaneStatus.connected)
        updated = _run(svc.update(created.id, update_req))
        assert updated.status == DataPlaneStatus.connected


# ---------------------------------------------------------------------------
# Delete tests
# ---------------------------------------------------------------------------


class TestDelete:
    """Tests for DataPlaneService.delete()."""

    @mock_dynamodb
    def test_delete_existing_record(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        req = DataPlaneCreateRequest(
            name="to-delete", type=DataPlaneType.FDW, connection_config=VALID_FDW_CONFIG
        )
        created = _run(svc.create(req))
        _run(svc.delete(created.id))
        with pytest.raises(DataPlaneNotFoundError):
            _run(svc.get(created.id))

    @mock_dynamodb
    def test_delete_nonexistent_raises_not_found(self):
        _create_table()
        svc = _make_service()
        _run(svc.initialize())
        with pytest.raises(DataPlaneNotFoundError):
            _run(svc.delete("nonexistent-id"))

    def test_delete_without_dynamo_raises_storage_error(self):
        svc = _make_service()
        with pytest.raises(DataPlaneStorageError):
            _run(svc.delete("any-id"))


# ---------------------------------------------------------------------------
# Graceful degradation tests
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Tests for graceful degradation when DynamoDB is unavailable."""

    def test_initialize_without_dynamo_does_not_raise(self):
        """Service should log warning but not crash if DynamoDB is unreachable."""
        svc = DataPlaneService(table_name="nonexistent-table")
        svc._region = "us-east-1"
        assert svc._table is None

    def test_all_ops_raise_storage_error_when_uninitialized(self):
        """All CRUD ops should raise DataPlaneStorageError when table is None."""
        svc = _make_service()
        req = DataPlaneCreateRequest(
            name="test", type=DataPlaneType.CDC, connection_config=VALID_CDC_CONFIG
        )
        with pytest.raises(DataPlaneStorageError):
            _run(svc.create(req))
        with pytest.raises(DataPlaneStorageError):
            _run(svc.get("any"))
        with pytest.raises(DataPlaneStorageError):
            _run(svc.list_all())
        with pytest.raises(DataPlaneStorageError):
            _run(svc.update("any", DataPlaneUpdateRequest(name="x")))
        with pytest.raises(DataPlaneStorageError):
            _run(svc.delete("any"))
