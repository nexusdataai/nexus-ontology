"""
Mapping Rule Service

Provides async CRUD operations for mapping rule configurations stored in the
foundry-workspace DynamoDB table. Each rule lives as three rows
(canonical META + denormalized links by source data-plane and by target VDL
entity) so list-by-source and list-by-target queries are PK-direct.

Backed by :class:`FoundryWorkspaceRepository`. The PostgreSQL-first fallback
of earlier revisions is gone; foundry-workspace is the single source of truth.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from loguru import logger

from src.models.mapping_rule_models import (
    MappingRuleCreateRequest,
    MappingRuleResponse,
    MappingRuleStatus,
    MappingRuleUpdateRequest,
)
from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)

mr_logger = logger.bind(component="mapping-rules")

# Canonical display keys for source systems (seeders may use legacy aliases).
SOURCE_SYSTEM_ALIASES: Dict[str, str] = {
    "sfdc": "Salesforce",
    "simulator": "Salesforce",
    "oracle": "Oracle",
    "oracle_erp": "Oracle",
    "sap": "SAP",
    "external": "External",
    "tpm": "TPM",
    "sourcing": "Sourcing",
    "bss": "BSS",
    "nss": "NSS",
    "oss": "OSS",
    "telco_golden": "Telco",
    "athena": "Athena",
    "mimir": "Mimir",
}

CANONICAL_SCHEMAS_FOR_DEDUPE = {
    "sfdc_itxp2dev",
    "sap_s4hana",
    "oracle_erp",
    "external_sources",
}


def normalize_source_system(value: str) -> str:
    if not value:
        return value
    key = value.strip()
    return SOURCE_SYSTEM_ALIASES.get(key.lower(), key)


def index_rules_by_virtual_entity(rules: List[MappingRuleResponse]) -> Dict[str, MappingRuleResponse]:
    """Pick the best representative rule per virtual entity (prefer active)."""
    by_ve: Dict[str, MappingRuleResponse] = {}
    for rule in rules:
        cur = by_ve.get(rule.virtual_entity)
        if cur is None:
            by_ve[rule.virtual_entity] = rule
            continue
        if rule.status == MappingRuleStatus.active and cur.status != MappingRuleStatus.active:
            by_ve[rule.virtual_entity] = rule
    return by_ve


def _dedupe_score_rule(item: Dict[str, Any]) -> tuple:
    field_count = len(item.get("fieldMaps") or [])
    schema_bonus = 100 if item.get("sourceSchema") in CANONICAL_SCHEMAS_FOR_DEDUPE else 0
    type_bonus = 10 if item.get("sourceType") == "FDW" else 0
    updated_at = item.get("updatedAt") or item.get("createdAt") or ""
    recency = 0
    try:
        recency = int(datetime.fromisoformat(updated_at.replace("Z", "+00:00")).timestamp())
    except Exception:
        recency = 0
    return (field_count, schema_bonus, type_bonus, recency)


class MappingRuleNotFoundError(Exception):
    def __init__(self, rule_id: str):
        self.rule_id = rule_id
        super().__init__(f"Mapping rule not found: {rule_id}")


class MappingRuleStorageError(Exception):
    def __init__(self, message: str, operation: str, original: Optional[Exception] = None):
        self.operation = operation
        self.original = original
        super().__init__(f"Storage error during {operation}: {message}")


class MappingRuleValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


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


class MappingRuleService:
    """Service for managing mapping rule configurations via foundry-workspace."""

    def __init__(
        self,
        repo: Optional[FoundryWorkspaceRepository] = None,
        table_name: Optional[str] = None,  # accepted for backward-compat with tests
    ):
        self._repo: Optional[FoundryWorkspaceRepository] = repo
        self._explicit_table_name = table_name
        self._composition_service: Any = None

    def set_composition_service(self, composition_service: Any) -> None:
        self._composition_service = composition_service

    async def initialize(self) -> None:
        try:
            loop = asyncio.get_event_loop()
            if self._repo is None:
                self._repo = await loop.run_in_executor(
                    None,
                    lambda: FoundryWorkspaceRepository(table_name=self._explicit_table_name),
                )
            mr_logger.info(
                "Mapping Rule service initialized",
                table=self._repo.table_name,
                backed_by="foundry-workspace",
            )
        except Exception as e:
            mr_logger.warning(f"foundry-workspace not available for Mapping Rule service: {e}")
            self._repo = None

    # ----- helpers -----

    def _source_dp_key(self, item_or_request: Any) -> str:
        """Synthesize a stable key for the source side of a mapping rule.
        Combines source system + schema + table so different sources don't collide.
        """
        if hasattr(item_or_request, "source_system"):
            sys_, sch, tbl = (
                item_or_request.source_system,
                item_or_request.source_schema,
                item_or_request.source_table,
            )
        else:
            sys_ = item_or_request.get("sourceSystem", "")
            sch = item_or_request.get("sourceSchema", "")
            tbl = item_or_request.get("sourceTable", "")
        return f"{sys_}.{sch}.{tbl}"

    def _target_vdl_key(self, item_or_request: Any) -> str:
        """Synthesize the target VDL entity key (just the virtualEntity name)."""
        if hasattr(item_or_request, "virtual_entity"):
            return item_or_request.virtual_entity
        return item_or_request.get("virtualEntity", "")

    async def deactivate_all_active_for_entity(self, virtual_entity: str) -> int:
        """Deactivate every active mapping rule for an entity (VDL composition takeover)."""
        rules = await self.list_all(virtual_entity=virtual_entity)
        deactivated = 0
        for rule in rules:
            if rule.status != MappingRuleStatus.active:
                continue
            await self.update(
                rule.id,
                MappingRuleUpdateRequest(status=MappingRuleStatus.inactive),
            )
            deactivated += 1
        return deactivated

    async def _deactivate_sibling_actives(
        self, virtual_entity: str, keep_rule_id: str
    ) -> int:
        """Ensure at most one active rule per virtual entity."""
        siblings = await self.list_all(virtual_entity=virtual_entity)
        deactivated = 0
        for rule in siblings:
            if rule.id == keep_rule_id:
                continue
            if rule.status != MappingRuleStatus.active:
                continue
            await self.update(
                rule.id,
                MappingRuleUpdateRequest(status=MappingRuleStatus.inactive),
            )
            deactivated += 1
        if deactivated:
            mr_logger.info(
                "Deactivated duplicate active mapping rules",
                virtual_entity=virtual_entity,
                keep=keep_rule_id,
                count=deactivated,
            )
        return deactivated

    async def dedupe_active_rules(self) -> Dict[str, Any]:
        """Keep the best active rule per virtual entity; deactivate the rest."""
        if self._repo is None:
            raise MappingRuleStorageError("foundry-workspace not available", "dedupe")
        all_rules = await self.list_all()
        per_entity: Dict[str, List[MappingRuleResponse]] = {}
        for rule in all_rules:
            if rule.status != MappingRuleStatus.active:
                continue
            per_entity.setdefault(rule.virtual_entity, []).append(rule)

        deactivated = 0
        affected_entities = 0
        for ve, items in per_entity.items():
            if len(items) <= 1:
                continue
            affected_entities += 1
            scored = sorted(
                items,
                key=lambda r: _dedupe_score_rule(r.model_dump(by_alias=True)),
                reverse=True,
            )
            keeper = scored[0]
            for drop in scored[1:]:
                await self.update(
                    drop.id,
                    MappingRuleUpdateRequest(status=MappingRuleStatus.inactive),
                )
                deactivated += 1
            await self._deactivate_sibling_actives(ve, keep_rule_id=keeper.id)

        return {
            "affected_entities": affected_entities,
            "deactivated": deactivated,
        }

    async def upsert_binding(
        self,
        request: MappingRuleCreateRequest,
        *,
        activate: bool = True,
        name_prefix: Optional[str] = None,
    ) -> tuple[MappingRuleResponse, str]:
        """
        Create or update the single binding for a virtual entity.
        Returns (rule, status) where status is created|updated|skipped.
        """
        existing_all = await self.list_all(virtual_entity=request.virtual_entity)
        candidate = None
        if name_prefix:
            for rule in existing_all:
                if (rule.name or "").startswith(name_prefix):
                    candidate = rule
                    break
        if candidate is None:
            active = [r for r in existing_all if r.status == MappingRuleStatus.active]
            candidate = active[0] if active else (existing_all[0] if existing_all else None)

        norm_system = normalize_source_system(request.source_system)

        if candidate:
            unchanged = (
                candidate.source_table == request.source_table
                and candidate.source_schema == request.source_schema
                and candidate.source_system == norm_system
                and (request.business_logic is None or candidate.business_logic == request.business_logic)
                and candidate.status == MappingRuleStatus.active
                and activate
            )
            if unchanged:
                return candidate, "skipped"
            updated = await self.update(
                candidate.id,
                MappingRuleUpdateRequest(
                    name=request.name,
                    source_type=request.source_type,
                    source_system=norm_system,
                    source_schema=request.source_schema,
                    source_table=request.source_table,
                    field_maps=request.field_maps,
                    business_logic=request.business_logic,
                    filter_expression=request.filter_expression,
                    status=MappingRuleStatus.active if activate else None,
                ),
            )
            if activate:
                await self._deactivate_sibling_actives(
                    request.virtual_entity, keep_rule_id=updated.id
                )
            return updated, "updated"

        created = await self.create(request)
        if activate:
            updated = await self.update(
                created.id,
                MappingRuleUpdateRequest(status=MappingRuleStatus.active),
            )
            await self._deactivate_sibling_actives(
                request.virtual_entity, keep_rule_id=updated.id
            )
            return updated, "created"
        return created, "created"

    # ----- CRUD -----

    async def create(self, request: MappingRuleCreateRequest) -> MappingRuleResponse:
        if self._repo is None:
            raise MappingRuleStorageError("foundry-workspace not available", "create")

        now = datetime.now(timezone.utc).isoformat()
        rule_id = f"MR-{uuid.uuid4()}"

        field_maps_dicts = [fm.model_dump(by_alias=True) for fm in request.field_maps]

        norm_system = normalize_source_system(request.source_system)
        item: Dict[str, Any] = {
            "id": rule_id,
            "name": request.name,
            "virtualEntity": request.virtual_entity,
            "sourceType": request.source_type.value,
            "sourceSystem": norm_system,
            "sourceTable": request.source_table,
            "sourceSchema": request.source_schema,
            "fieldMaps": field_maps_dicts,
            "status": MappingRuleStatus.draft.value,
            "createdAt": now,
            "updatedAt": now,
        }
        if request.business_logic is not None:
            item["businessLogic"] = request.business_logic
        if request.filter_expression is not None:
            item["filterExpression"] = request.filter_expression

        source_dp = self._source_dp_key(request)
        target_vdl = self._target_vdl_key(request)

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._repo.put_mapping_rule(rule_id, source_dp, target_vdl, item),
            )
            mr_logger.info("Mapping rule created", id=rule_id)
            if item.get("status") == MappingRuleStatus.active.value:
                await self._deactivate_sibling_actives(
                    request.virtual_entity, keep_rule_id=rule_id
                )
        except FoundryWorkspaceRepositoryError as e:
            mr_logger.error("Failed to create mapping rule", error=str(e))
            raise MappingRuleStorageError(str(e), "create", e)
        except Exception as e:
            mr_logger.error("Failed to create mapping rule", error=str(e))
            raise MappingRuleStorageError(str(e), "create", e)

        return self._to_response(item)

    async def get(self, rule_id: str) -> MappingRuleResponse:
        if self._repo is None:
            raise MappingRuleStorageError("foundry-workspace not available", "get")

        try:
            loop = asyncio.get_event_loop()
            item = await loop.run_in_executor(None, lambda: self._repo.get_mapping_rule(rule_id))
        except FoundryWorkspaceRepositoryError as e:
            raise MappingRuleStorageError(str(e), "get", e)
        except Exception as e:
            raise MappingRuleStorageError(str(e), "get", e)

        if not item:
            raise MappingRuleNotFoundError(rule_id)
        return self._to_response(item)

    async def list_all(
        self,
        virtual_entity: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[MappingRuleResponse]:
        if self._repo is None:
            raise MappingRuleStorageError("foundry-workspace not available", "list")

        try:
            loop = asyncio.get_event_loop()
            if virtual_entity:
                # PK-direct query under VDLENTITY#{virtual_entity} (denormalized links)
                items = await loop.run_in_executor(
                    None, lambda: self._repo.list_mapping_rules_by_target(virtual_entity)
                )
            else:
                # GSI1 query for all canonical META rows
                items = await loop.run_in_executor(None, lambda: self._repo.list_mapping_rules())

            if source_type:
                items = [i for i in items if i.get("sourceType") == source_type]
            return [self._to_response(item) for item in items]
        except FoundryWorkspaceRepositoryError as e:
            raise MappingRuleStorageError(str(e), "list", e)
        except Exception as e:
            raise MappingRuleStorageError(str(e), "list", e)

    async def update(
        self, rule_id: str, request: MappingRuleUpdateRequest
    ) -> MappingRuleResponse:
        existing = await self.get(rule_id)
        if self._repo is None:
            raise MappingRuleStorageError("foundry-workspace not available", "update")

        now = datetime.now(timezone.utc).isoformat()

        # Merge new fields on top of the existing canonical item. field_maps
        # must be dumped to plain dicts: existing.field_maps is List[FieldMap]
        # (Pydantic), and persisting those directly would round-trip them through
        # _to_attr's str() fallback, corrupting the stored shape.
        existing_field_maps = [
            fm.model_dump(by_alias=True) if hasattr(fm, "model_dump") else fm
            for fm in (existing.field_maps or [])
        ]
        merged: Dict[str, Any] = {
            "id": existing.id,
            "name": existing.name,
            "virtualEntity": existing.virtual_entity,
            "sourceType": existing.source_type
            if isinstance(existing.source_type, str)
            else existing.source_type.value,
            "sourceSystem": existing.source_system,
            "sourceTable": existing.source_table,
            "sourceSchema": existing.source_schema,
            "fieldMaps": existing_field_maps,
            "status": existing.status.value,
            "createdAt": existing.created_at,
            "updatedAt": now,
        }
        if existing.business_logic is not None:
            merged["businessLogic"] = existing.business_logic
        if existing.filter_expression is not None:
            merged["filterExpression"] = existing.filter_expression

        if request.name is not None:
            merged["name"] = request.name
        if request.source_type is not None:
            merged["sourceType"] = request.source_type.value
        if request.source_system is not None:
            merged["sourceSystem"] = normalize_source_system(request.source_system)
        if request.source_schema is not None:
            merged["sourceSchema"] = request.source_schema
        if request.source_table is not None:
            merged["sourceTable"] = request.source_table
        if request.status is not None:
            merged["status"] = request.status.value
        if request.field_maps is not None:
            merged["fieldMaps"] = [fm.model_dump(by_alias=True) for fm in request.field_maps]
        if request.business_logic is not None:
            merged["businessLogic"] = request.business_logic
        if request.filter_expression is not None:
            merged["filterExpression"] = request.filter_expression

        # Source/target keys don't change in MappingRuleUpdateRequest, so reuse
        # those of the existing rule.
        source_dp = self._source_dp_key(merged)
        target_vdl = self._target_vdl_key(merged)

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._repo.put_mapping_rule(rule_id, source_dp, target_vdl, merged),
            )
            mr_logger.info("Mapping rule updated", id=rule_id)
            if merged.get("status") == MappingRuleStatus.active.value:
                await self._deactivate_sibling_actives(
                    merged["virtualEntity"], keep_rule_id=rule_id
                )
                if self._composition_service is not None:
                    try:
                        await self._composition_service.sync_from_mapping_rule_dict(merged)
                    except Exception as sync_err:
                        mr_logger.warning(
                            "Failed to sync VDL composition from mapping rule",
                            rule_id=rule_id,
                            error=str(sync_err),
                        )
            return self._to_response(merged)
        except FoundryWorkspaceRepositoryError as e:
            raise MappingRuleStorageError(str(e), "update", e)
        except Exception as e:
            raise MappingRuleStorageError(str(e), "update", e)

    async def delete(self, rule_id: str) -> None:
        await self.get(rule_id)
        if self._repo is None:
            raise MappingRuleStorageError("foundry-workspace not available", "delete")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._repo.delete_mapping_rule(rule_id))
            mr_logger.info("Mapping rule deleted", id=rule_id)
        except FoundryWorkspaceRepositoryError as e:
            raise MappingRuleStorageError(str(e), "delete", e)
        except Exception as e:
            raise MappingRuleStorageError(str(e), "delete", e)

    async def validate_rule(self, rule_id: str) -> dict:
        rule = await self.get(rule_id)
        errors: List[str] = []

        try:
            from src.services.fdw_discovery_service import FDWDiscoveryService
        except ImportError:
            return {"valid": False, "errors": ["FDW discovery service is not available"]}

        try:
            discovery = FDWDiscoveryService()
            await discovery.initialize()

            tables = await discovery.list_foreign_tables()
            table_match = None
            for t in tables:
                if t.schema_name == rule.source_schema and t.table_name == rule.source_table:
                    table_match = t
                    break

            if table_match is None:
                errors.append(
                    f"Source table {rule.source_schema}.{rule.source_table} not found in foreign tables"
                )
                return {"valid": False, "errors": errors}

            columns = await discovery.get_table_columns(rule.source_schema, rule.source_table)
            column_names = {col.column_name for col in columns}

            for fm in rule.field_maps:
                if fm.source_field not in column_names:
                    errors.append(f"Source field '{fm.source_field}' not found in {rule.source_table}")

        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")

        return {"valid": len(errors) == 0, "errors": errors}

    async def suggest_mappings(
        self, virtual_entity: str, source_schema: str, source_table: str
    ) -> List[dict]:
        try:
            from src.services.fdw_discovery_service import FDWDiscoveryService
        except ImportError:
            return [{"error": "FDW discovery service is not available"}]

        try:
            discovery = FDWDiscoveryService()
            await discovery.initialize()
            columns = await discovery.get_table_columns(source_schema, source_table)
        except Exception as e:
            return [{"error": f"Failed to discover columns: {str(e)}"}]

        source_col_names = [col.column_name for col in columns]
        target_fields = self._get_virtual_entity_fields(virtual_entity)

        suggestions = []
        for target in target_fields:
            normalized_target = target.lower().replace("_", "").replace("-", "")
            best_match = None
            for source in source_col_names:
                normalized_source = source.lower().replace("_", "").replace("-", "")
                if normalized_source == normalized_target:
                    best_match = source
                    break
            if best_match:
                suggestions.append({
                    "sourceField": best_match,
                    "targetField": target,
                    "confidence": "high",
                })
            else:
                for source in source_col_names:
                    normalized_source = source.lower().replace("_", "").replace("-", "")
                    if normalized_target in normalized_source or normalized_source in normalized_target:
                        suggestions.append({
                            "sourceField": source,
                            "targetField": target,
                            "confidence": "low",
                        })
                        break

        return suggestions

    def _get_virtual_entity_fields(self, virtual_entity: str) -> List[str]:
        known_entities: Dict[str, List[str]] = {
            "customer": ["id", "name", "email", "phone", "address", "created_at", "updated_at"],
            "order": ["id", "customer_id", "total", "status", "created_at", "updated_at"],
            "product": ["id", "name", "description", "price", "category", "created_at"],
        }
        return known_entities.get(virtual_entity.lower(), ["id", "name", "created_at", "updated_at"])

    def _to_response(self, item: Dict[str, Any]) -> MappingRuleResponse:
        converted = _convert_decimals(item)
        return MappingRuleResponse(
            id=converted["id"],
            name=converted["name"],
            virtual_entity=converted["virtualEntity"],
            source_type=converted["sourceType"],
            source_system=converted["sourceSystem"],
            source_table=converted["sourceTable"],
            source_schema=converted["sourceSchema"],
            field_maps=converted.get("fieldMaps", []),
            business_logic=converted.get("businessLogic"),
            filter_expression=converted.get("filterExpression"),
            status=MappingRuleStatus(converted["status"]),
            created_at=converted["createdAt"],
            updated_at=converted["updatedAt"],
        )
