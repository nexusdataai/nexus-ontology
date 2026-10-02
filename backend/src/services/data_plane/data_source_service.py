"""
Data Source Definition service (Data Plane, Phase 2)

CRUD facade over ``DATASOURCE#{id}`` rows in foundry-workspace. Data
sources are the first-class definition objects the spec calls for -
distinct from ``DATAPLANE#`` (which models the plane itself) and from
mapping rules (transformation between sources and VDL).

Attributes stored per row:
- ``id``            slug used in URLs
- ``dataPlaneId``   FK to a ``DATAPLANE#`` row (optional)
- ``type``          FDW | ETL | CDC | ATHENA | MIMIR | FILE_UPLOAD | SOCIAL
- ``name``          display name
- ``schemaName``    schema in the source system (e.g. ``sfdc_itxp2dev``)
- ``connectionRef`` optional reference to SSM path or secret name
- ``mode``          ``simulator`` | ``real`` - overrides the SSM
                    ``data_source_mode/*`` default when set
- ``simulatorKey``  routing key into the simulator dispatch (e.g. ``sfdc``)
- ``verticals``     list[str]
- ``description``
- ``updatedAt``
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DataSourceService:
    _instance: Optional["DataSourceService"] = None

    def __init__(self, repo: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repo or FoundryWorkspaceRepository()

    @classmethod
    def get_instance(cls) -> "DataSourceService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def list(self) -> List[Dict[str, Any]]:
        try:
            return self._repo.list_data_sources()
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"DataSource list failed: {e}")
            return []

    async def get(self, data_source_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self._repo.get_data_source(data_source_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"DataSource get({data_source_id}) failed: {e}")
            return None

    async def put(self, data_source_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attrs = dict(attrs)
        attrs["id"] = data_source_id
        attrs.setdefault("updatedAt", _now_iso())
        try:
            return self._repo.put_data_source(data_source_id, attrs)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"DataSource put({data_source_id}) failed: {e}")
            raise

    async def delete(self, data_source_id: str) -> int:
        try:
            return self._repo.delete_data_source(data_source_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"DataSource delete({data_source_id}) failed: {e}")
            return 0

    async def resolve_mode(self, data_source_id: str, ssm_default: str = "simulator") -> str:
        """Return the effective ``mode`` (``simulator`` | ``real``) for a
        source. DataSource row's ``mode`` takes precedence; falls back to
        the SSM-provided default from ``DataSourceModeService``."""
        row = await self.get(data_source_id)
        if row and row.get("mode") in ("simulator", "real"):
            return row["mode"]
        return ssm_default


def get_data_source_service() -> DataSourceService:
    return DataSourceService.get_instance()
