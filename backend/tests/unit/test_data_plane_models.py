"""
Unit tests for Data Plane Pydantic models.

Tests DataPlaneType enum, DataPlaneStatus enum, DataPlaneCreateRequest,
DataPlaneUpdateRequest, and DataPlaneResponse models including validation,
camelCase serialization, and populate_by_name behavior.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from pydantic import ValidationError
from src.models.data_plane_models import (
    DataPlaneType,
    DataPlaneStatus,
    DataPlaneCreateRequest,
    DataPlaneUpdateRequest,
    DataPlaneResponse,
)


class TestDataPlaneType:
    """Tests for DataPlaneType enum."""

    def test_fdw_value(self):
        assert DataPlaneType.FDW == "FDW"

    def test_cdc_value(self):
        assert DataPlaneType.CDC == "CDC"

    def test_etl_value(self):
        assert DataPlaneType.ETL == "ETL"

    def test_all_values(self):
        assert set(DataPlaneType) == {DataPlaneType.FDW, DataPlaneType.CDC, DataPlaneType.ETL}

    def test_is_string_enum(self):
        assert isinstance(DataPlaneType.FDW, str)


class TestDataPlaneStatus:
    """Tests for DataPlaneStatus enum."""

    def test_connected_value(self):
        assert DataPlaneStatus.connected == "connected"

    def test_disconnected_value(self):
        assert DataPlaneStatus.disconnected == "disconnected"

    def test_error_value(self):
        assert DataPlaneStatus.error == "error"

    def test_pending_value(self):
        assert DataPlaneStatus.pending == "pending"

    def test_all_values(self):
        assert set(DataPlaneStatus) == {
            DataPlaneStatus.connected,
            DataPlaneStatus.disconnected,
            DataPlaneStatus.error,
            DataPlaneStatus.pending,
        }

    def test_is_string_enum(self):
        assert isinstance(DataPlaneStatus.connected, str)


class TestDataPlaneCreateRequest:
    """Tests for DataPlaneCreateRequest model."""

    def test_valid_fdw_request(self):
        req = DataPlaneCreateRequest(
            name="my-fdw",
            type=DataPlaneType.FDW,
            connection_config={"host": "localhost", "port": 5432},
        )
        assert req.name == "my-fdw"
        assert req.type == DataPlaneType.FDW
        assert req.connection_config == {"host": "localhost", "port": 5432}

    def test_valid_request_with_alias(self):
        req = DataPlaneCreateRequest(
            name="my-cdc",
            type=DataPlaneType.CDC,
            connectionConfig={"bootstrapServers": "kafka:9092"},
        )
        assert req.connection_config == {"bootstrapServers": "kafka:9092"}

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            DataPlaneCreateRequest(
                name="",
                type=DataPlaneType.FDW,
                connection_config={"host": "localhost"},
            )

    def test_missing_name_rejected(self):
        with pytest.raises(ValidationError):
            DataPlaneCreateRequest(
                type=DataPlaneType.FDW,
                connection_config={"host": "localhost"},
            )

    def test_missing_type_rejected(self):
        with pytest.raises(ValidationError):
            DataPlaneCreateRequest(
                name="test",
                connection_config={"host": "localhost"},
            )

    def test_missing_connection_config_rejected(self):
        with pytest.raises(ValidationError):
            DataPlaneCreateRequest(
                name="test",
                type=DataPlaneType.FDW,
            )

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            DataPlaneCreateRequest(
                name="test",
                type="INVALID",
                connection_config={"host": "localhost"},
            )

    def test_camel_case_serialization(self):
        req = DataPlaneCreateRequest(
            name="test",
            type=DataPlaneType.ETL,
            connection_config={"schedule": "daily"},
        )
        data = req.model_dump(by_alias=True)
        assert "connectionConfig" in data
        assert "connection_config" not in data


class TestDataPlaneUpdateRequest:
    """Tests for DataPlaneUpdateRequest model."""

    def test_all_fields_optional(self):
        req = DataPlaneUpdateRequest()
        assert req.name is None
        assert req.status is None
        assert req.connection_config is None

    def test_partial_update_name(self):
        req = DataPlaneUpdateRequest(name="new-name")
        assert req.name == "new-name"
        assert req.status is None

    def test_partial_update_status(self):
        req = DataPlaneUpdateRequest(status=DataPlaneStatus.connected)
        assert req.status == DataPlaneStatus.connected

    def test_partial_update_connection_config_alias(self):
        req = DataPlaneUpdateRequest(connectionConfig={"host": "new-host"})
        assert req.connection_config == {"host": "new-host"}

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            DataPlaneUpdateRequest(name="")

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            DataPlaneUpdateRequest(status="invalid")

    def test_camel_case_serialization(self):
        req = DataPlaneUpdateRequest(
            connection_config={"host": "localhost"},
        )
        data = req.model_dump(by_alias=True)
        assert "connectionConfig" in data
        assert "connection_config" not in data


class TestDataPlaneResponse:
    """Tests for DataPlaneResponse model."""

    def _make_response(self, **overrides):
        defaults = {
            "id": "abc-123",
            "name": "test-plane",
            "type": DataPlaneType.FDW,
            "status": DataPlaneStatus.connected,
            "connection_config": {"host": "localhost"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        defaults.update(overrides)
        return DataPlaneResponse(**defaults)

    def test_valid_response(self):
        resp = self._make_response()
        assert resp.id == "abc-123"
        assert resp.name == "test-plane"
        assert resp.type == DataPlaneType.FDW
        assert resp.status == DataPlaneStatus.connected

    def test_response_with_aliases(self):
        resp = DataPlaneResponse(
            id="abc-123",
            name="test",
            type=DataPlaneType.CDC,
            status=DataPlaneStatus.pending,
            connectionConfig={"key": "val"},
            createdAt="2024-01-01T00:00:00Z",
            updatedAt="2024-01-01T00:00:00Z",
        )
        assert resp.connection_config == {"key": "val"}
        assert resp.created_at == "2024-01-01T00:00:00Z"

    def test_camel_case_serialization(self):
        resp = self._make_response()
        data = resp.model_dump(by_alias=True)
        assert "connectionConfig" in data
        assert "createdAt" in data
        assert "updatedAt" in data
        assert "connection_config" not in data
        assert "created_at" not in data
        assert "updated_at" not in data

    def test_missing_required_field_rejected(self):
        with pytest.raises(ValidationError):
            DataPlaneResponse(
                id="abc",
                name="test",
                type=DataPlaneType.FDW,
                status=DataPlaneStatus.connected,
                # missing connection_config, created_at, updated_at
            )

    def test_round_trip_serialization(self):
        resp = self._make_response()
        data = resp.model_dump(by_alias=True)
        restored = DataPlaneResponse(**data)
        assert restored.id == resp.id
        assert restored.name == resp.name
        assert restored.type == resp.type
        assert restored.status == resp.status
        assert restored.connection_config == resp.connection_config
        assert restored.created_at == resp.created_at
        assert restored.updated_at == resp.updated_at
