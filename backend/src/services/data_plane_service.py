"""
Data Plane Service

Provides async CRUD operations for Data Plane configurations (FDW / CDC / ETL
connection configs) stored in the foundry-workspace DynamoDB table under the
``DATAPLANE#`` PK namespace. Delegates persistence to
:class:`FoundryWorkspaceRepository`; preserves the external API surface
(request/response models, exception types).

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 4.1, 4.2, 6.1, 6.3**
"""

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from loguru import logger

from src.models.data_plane_models import (
    DataPlaneCreateRequest,
    DataPlaneResponse,
    DataPlaneStatus,
    DataPlaneType,
    DataPlaneUpdateRequest,
)
from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)
from src.utils.data_plane_errors import (
    DataPlaneNotFoundError,
    DataPlaneStorageError,
    DataPlaneValidationError,
)

dp_logger = logger.bind(component="data-plane")

_FDW_REQUIRED_FIELDS = {"host", "port", "database", "user", "password"}


def _convert_decimals(obj: Any) -> Any:
    """Convert Decimal values to int/float for JSON serialization."""
    if isinstance(obj, Decimal):
        if obj == int(obj):
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimals(v) for v in obj]
    return obj


class DataPlaneService:
    """Service for managing Data Plane configurations via foundry-workspace."""

    def __init__(
        self,
        repo: Optional[FoundryWorkspaceRepository] = None,
        table_name: Optional[str] = None,  # accepted for backward-compat with tests
    ):
        # ``table_name`` is kept in the signature so existing tests / callers
        # that pass a moto-backed test table name continue to work; it is
        # forwarded to the underlying foundry-workspace repository.
        self._repo: Optional[FoundryWorkspaceRepository] = repo
        self._explicit_table_name = table_name
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize underlying foundry-workspace repo. Logs warning on failure."""
        try:
            loop = asyncio.get_event_loop()
            if self._repo is None:
                self._repo = await loop.run_in_executor(
                    None,
                    lambda: FoundryWorkspaceRepository(table_name=self._explicit_table_name),
                )
            dp_logger.info(
                "Data Plane service initialized",
                table=self._repo.table_name,
                backed_by="foundry-workspace",
            )
            self._initialized = True
        except Exception as e:
            dp_logger.warning(
                "foundry-workspace not available for Data Plane service, running in degraded mode",
                error=str(e),
            )
            self._repo = None
            self._initialized = False

    async def create(self, request: DataPlaneCreateRequest) -> DataPlaneResponse:
        """Create a new data plane record.

        Generates UUID, sets timestamps, validates FDW config,
        and defaults CDC/ETL status to pending.
        """
        if self._repo is None:
            raise DataPlaneStorageError("foundry-workspace not available", "create")

        # Validate FDW connection config
        if request.type == DataPlaneType.FDW:
            self._validate_fdw_config(request.connection_config)

        now = datetime.now(timezone.utc).isoformat()
        data_plane_id = str(uuid.uuid4())

        # CDC and ETL default to pending; FDW defaults to connected
        if request.type in (DataPlaneType.CDC, DataPlaneType.ETL):
            status = DataPlaneStatus.pending.value
        else:
            status = DataPlaneStatus.connected.value

        attrs = {
            "id": data_plane_id,
            "name": request.name,
            "type": request.type.value,
            "status": status,
            "connectionConfig": request.connection_config,
            "createdAt": now,
            "updatedAt": now,
        }

        try:
            loop = asyncio.get_event_loop()
            item = await loop.run_in_executor(
                None, lambda: self._repo.put_data_plane(data_plane_id, attrs)
            )
            dp_logger.info("Data plane created", id=data_plane_id, type=request.type.value)
        except FoundryWorkspaceRepositoryError as e:
            dp_logger.error("Failed to create data plane", error=str(e))
            raise DataPlaneStorageError(str(e), "create", e)
        except Exception as e:
            dp_logger.error("Failed to create data plane", error=str(e))
            raise DataPlaneStorageError(str(e), "create", e)

        return self._to_response(item)

    async def get(self, data_plane_id: str) -> DataPlaneResponse:
        """Get a data plane by ID. Raises DataPlaneNotFoundError if not found."""
        if self._repo is None:
            raise DataPlaneStorageError("foundry-workspace not available", "get")

        try:
            loop = asyncio.get_event_loop()
            item = await loop.run_in_executor(
                None, lambda: self._repo.get_data_plane(data_plane_id)
            )
        except FoundryWorkspaceRepositoryError as e:
            dp_logger.error("Failed to get data plane", id=data_plane_id, error=str(e))
            raise DataPlaneStorageError(str(e), "get", e)
        except Exception as e:
            dp_logger.error("Failed to get data plane", id=data_plane_id, error=str(e))
            raise DataPlaneStorageError(str(e), "get", e)

        if not item:
            raise DataPlaneNotFoundError(data_plane_id)

        return self._to_response(item)

    async def list_all(self) -> List[DataPlaneResponse]:
        """List all data plane records (GSI1-backed)."""
        if self._repo is None:
            raise DataPlaneStorageError("foundry-workspace not available", "list")

        try:
            loop = asyncio.get_event_loop()
            items = await loop.run_in_executor(None, lambda: self._repo.list_data_planes())
            dp_logger.info("Listed data planes", count=len(items))
            return [self._to_response(item) for item in items]
        except FoundryWorkspaceRepositoryError as e:
            dp_logger.error("Failed to list data planes", error=str(e))
            raise DataPlaneStorageError(str(e), "list", e)
        except Exception as e:
            dp_logger.error("Failed to list data planes", error=str(e))
            raise DataPlaneStorageError(str(e), "list", e)

    async def update(
        self, data_plane_id: str, request: DataPlaneUpdateRequest
    ) -> DataPlaneResponse:
        """Update an existing data plane. Raises DataPlaneNotFoundError if not found."""
        existing = await self.get(data_plane_id)

        if self._repo is None:
            raise DataPlaneStorageError("foundry-workspace not available", "update")

        now = datetime.now(timezone.utc).isoformat()

        # Merge into existing item (foundry-workspace stores META rows whole;
        # a single put_meta call rewrites the row so we must preserve unchanged
        # fields).
        merged: Dict[str, Any] = {
            "id": existing.id,
            "name": existing.name,
            "type": existing.type.value,
            "status": existing.status.value,
            "connectionConfig": existing.connection_config,
            "createdAt": existing.created_at,
            "updatedAt": now,
        }
        if request.name is not None:
            merged["name"] = request.name
        if request.status is not None:
            merged["status"] = request.status.value
        if request.connection_config is not None:
            merged["connectionConfig"] = request.connection_config

        try:
            loop = asyncio.get_event_loop()
            item = await loop.run_in_executor(
                None, lambda: self._repo.put_data_plane(data_plane_id, merged)
            )
            dp_logger.info("Data plane updated", id=data_plane_id)
            return self._to_response(item)
        except FoundryWorkspaceRepositoryError as e:
            dp_logger.error("Failed to update data plane", id=data_plane_id, error=str(e))
            raise DataPlaneStorageError(str(e), "update", e)
        except Exception as e:
            dp_logger.error("Failed to update data plane", id=data_plane_id, error=str(e))
            raise DataPlaneStorageError(str(e), "update", e)

    async def delete(self, data_plane_id: str) -> None:
        """Delete a data plane by ID. Raises DataPlaneNotFoundError if not found."""
        await self.get(data_plane_id)

        if self._repo is None:
            raise DataPlaneStorageError("foundry-workspace not available", "delete")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self._repo.delete_data_plane(data_plane_id)
            )
            dp_logger.info("Data plane deleted", id=data_plane_id)
        except FoundryWorkspaceRepositoryError as e:
            dp_logger.error("Failed to delete data plane", id=data_plane_id, error=str(e))
            raise DataPlaneStorageError(str(e), "delete", e)
        except Exception as e:
            dp_logger.error("Failed to delete data plane", id=data_plane_id, error=str(e))
            raise DataPlaneStorageError(str(e), "delete", e)

    def _validate_fdw_config(self, connection_config: Dict[str, Any]) -> None:
        """Validate FDW connection config has required fields: host, port, database, user, password."""
        missing = _FDW_REQUIRED_FIELDS - set(connection_config.keys())
        if missing:
            raise DataPlaneValidationError(
                f"FDW connectionConfig missing required fields: {', '.join(sorted(missing))}"
            )

    def _to_response(self, item: Dict[str, Any]) -> DataPlaneResponse:
        """Convert foundry-workspace item to DataPlaneResponse."""
        converted = _convert_decimals(item)
        return DataPlaneResponse(
            id=converted["id"],
            name=converted["name"],
            type=DataPlaneType(converted["type"]),
            status=DataPlaneStatus(converted["status"]),
            connection_config=converted.get("connectionConfig", {}),
            created_at=converted["createdAt"],
            updated_at=converted["updatedAt"],
        )
