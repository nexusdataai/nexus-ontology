"""
VDL composition CRUD — how virtual entities are formed from source tables.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from loguru import logger

from src.models.mapping_rule_models import MappingRuleStatus
from src.models.vdl_composition_models import (
    CompositionJoin,
    CompositionProjection,
    CompositionSourceRef,
    VdlCompositionResponse,
    VdlCompositionStrategy,
    VdlCompositionUpsertRequest,
    VdlCompositionValidateResponse,
)
from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)
from src.services.mapping_rule_service import MappingRuleService, normalize_source_system
from src.services.vdl_composition_sql import (
    composition_to_sql,
    mapping_rule_item_to_composition_attrs,
)

comp_logger = logger.bind(component="vdl-composition")


class VdlCompositionNotFoundError(Exception):
    pass


class VdlCompositionStorageError(Exception):
    pass


def _convert_decimals(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        if obj == int(obj):
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimals(v) for v in obj]
    return obj


def _source_dp_id(src: CompositionSourceRef) -> str:
    return f"{src.source_system}.{src.schema}.{src.table}"


class VdlCompositionService:
    def __init__(
        self,
        repo: Optional[FoundryWorkspaceRepository] = None,
        mapping_service: Optional[MappingRuleService] = None,
        table_name: Optional[str] = None,
    ):
        self._repo = repo
        self._mapping = mapping_service
        self._explicit_table_name = table_name

    async def initialize(self, mapping_service: Optional[MappingRuleService] = None) -> None:
        if mapping_service is not None:
            self._mapping = mapping_service
        if self._repo is None:
            loop = asyncio.get_event_loop()
            self._repo = await loop.run_in_executor(
                None,
                lambda: FoundryWorkspaceRepository(table_name=self._explicit_table_name),
            )
        comp_logger.info("VDL composition service initialized", table=self._repo.table_name)

    def _to_response(self, item: Dict[str, Any]) -> VdlCompositionResponse:
        converted = _convert_decimals(item)
        sources = converted.get("from") or []
        return VdlCompositionResponse(
            virtual_entity=converted["virtualEntity"],
            name=converted.get("name"),
            status=MappingRuleStatus(converted.get("status", "draft")),
            strategy=VdlCompositionStrategy(converted.get("strategy", "runtime_sql")),
            sources=sources,
            joins=converted.get("joins") or [],
            projections=converted.get("select") or [],
            field_maps=converted.get("fieldMaps") or [],
            filter_expression=converted.get("filterExpression"),
            business_logic=converted.get("businessLogic"),
            created_at=converted.get("createdAt", ""),
            updated_at=converted.get("updatedAt", ""),
        )

    async def list_all(self) -> List[VdlCompositionResponse]:
        if self._repo is None:
            raise VdlCompositionStorageError("repository not initialized")
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, self._repo.list_vdl_compositions)
        return [self._to_response(i) for i in items]

    async def get(self, virtual_entity: str) -> VdlCompositionResponse:
        if self._repo is None:
            raise VdlCompositionStorageError("repository not initialized")
        loop = asyncio.get_event_loop()
        item = await loop.run_in_executor(
            None, lambda: self._repo.get_vdl_composition(virtual_entity)
        )
        if not item:
            raise VdlCompositionNotFoundError(virtual_entity)
        return self._to_response(item)

    async def get_or_none(self, virtual_entity: str) -> Optional[VdlCompositionResponse]:
        try:
            return await self.get(virtual_entity)
        except VdlCompositionNotFoundError:
            return None

    async def upsert(self, request: VdlCompositionUpsertRequest) -> VdlCompositionResponse:
        if self._repo is None:
            raise VdlCompositionStorageError("repository not initialized")

        now = datetime.now(timezone.utc).isoformat()
        try:
            existing = await self.get(request.virtual_entity)
            created_at = existing.created_at
        except VdlCompositionNotFoundError:
            created_at = now

        sources = request.sources
        for src in sources:
            src.source_system = normalize_source_system(src.source_system)

        item: Dict[str, Any] = {
            "virtualEntity": request.virtual_entity,
            "name": request.name or request.virtual_entity,
            "status": request.status.value,
            "strategy": request.strategy.value,
            "from": [s.model_dump(by_alias=True) for s in sources],
            "joins": [j.model_dump() for j in request.joins],
            "select": [p.model_dump(by_alias=True) for p in request.projections],
            "fieldMaps": [fm.model_dump(by_alias=True) for fm in request.field_maps],
            "filterExpression": request.filter_expression,
            "businessLogic": request.business_logic,
            "createdAt": created_at,
            "updatedAt": now,
            "sourceDataPlaneIds": [_source_dp_id(s) for s in sources],
        }

        if request.status == MappingRuleStatus.active and self._mapping is not None:
            await self._mapping.deactivate_all_active_for_entity(request.virtual_entity)

        dp_ids = item["sourceDataPlaneIds"]
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._repo.put_vdl_composition(request.virtual_entity, item, dp_ids),
            )
        except FoundryWorkspaceRepositoryError as e:
            raise VdlCompositionStorageError(str(e)) from e

        return self._to_response(item)

    async def validate(
        self, virtual_entity: str, *, limit: int = 5
    ) -> VdlCompositionValidateResponse:
        composition = await self.get(virtual_entity)
        sql, errors = composition_to_sql(composition, limit=limit)
        if sql and not errors:
            return VdlCompositionValidateResponse(valid=True, errors=[], sql_preview=sql)
        return VdlCompositionValidateResponse(valid=False, errors=errors, sql_preview=sql or None)

    async def migrate_from_active_mapping_rules(self) -> Dict[str, int]:
        """One-shot backfill: active mapping rules -> compositions."""
        if self._mapping is None or self._repo is None:
            raise VdlCompositionStorageError("services not initialized")
        rules = await self._mapping.list_all()
        migrated = skipped = 0
        for rule in rules:
            if rule.status != MappingRuleStatus.active:
                continue
            if await self.get_or_none(rule.virtual_entity):
                skipped += 1
                continue
            attrs = mapping_rule_item_to_composition_attrs(rule.model_dump(by_alias=True))
            attrs["createdAt"] = rule.created_at
            attrs["updatedAt"] = rule.updated_at
            loop = asyncio.get_event_loop()
            dp = f"{rule.source_system}.{rule.source_schema}.{rule.source_table}"
            await loop.run_in_executor(
                None,
                lambda a=attrs, ve=rule.virtual_entity, d=dp: self._repo.put_vdl_composition(
                    ve, a, [d]
                ),
            )
            migrated += 1
        return {"migrated": migrated, "skipped": skipped}

    async def sync_from_mapping_rule_dict(self, rule_item: Dict[str, Any]) -> None:
        """Upsert composition document from a canonical mapping-rule payload."""
        if self._repo is None:
            return
        ve = rule_item.get("virtualEntity")
        if not ve:
            return
        attrs = mapping_rule_item_to_composition_attrs(rule_item)
        attrs.setdefault("createdAt", rule_item.get("createdAt", ""))
        attrs["updatedAt"] = rule_item.get("updatedAt", attrs.get("updatedAt", ""))
        attrs["status"] = rule_item.get("status", attrs.get("status", "draft"))
        dp = f"{rule_item.get('sourceSystem')}.{rule_item.get('sourceSchema')}.{rule_item.get('sourceTable')}"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._repo.put_vdl_composition(ve, attrs, [dp]),
        )