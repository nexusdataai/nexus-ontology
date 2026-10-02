"""
Virtual Data API Registry Service (Data Plane, Phase 2)

Owns the ``VDLAPI#`` PK namespace in foundry-workspace. Exposes CRUD + a
``resolve()`` helper that produces an ``ExecutionPlan`` for a given VDL
API + arguments.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, List, Optional

from loguru import logger

from src.models.vdl_api_models import (
    DirectSqlBinding,
    ExecutionPlan,
    ExecutionStep,
    ImplBinding,
    VdlApiSpec,
)
from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)


_CACHE_TTL_SECS = int(os.getenv("VDL_API_REGISTRY_CACHE_TTL", "300"))


def _spec_to_attrs(spec: VdlApiSpec) -> Dict[str, Any]:
    return {
        "apiId": spec.api_id,
        "verb": spec.verb,
        "virtual_entity": spec.virtual_entity,
        "parameters_schema": spec.parameters_schema or {},
        "impl": [b.model_dump() for b in spec.impl],
        "direct_sql": spec.direct_sql.model_dump() if spec.direct_sql else None,
        "risk_level": spec.risk_level,
        "description": spec.description,
        "tags": list(spec.tags or []),
    }


def _attrs_to_spec(attrs: Dict[str, Any]) -> VdlApiSpec:
    return VdlApiSpec(
        api_id=str(attrs.get("apiId") or attrs.get("api_id") or ""),
        verb=str(attrs.get("verb") or "read"),
        virtual_entity=str(attrs.get("virtual_entity") or attrs.get("virtualEntity") or ""),
        parameters_schema=dict(attrs.get("parameters_schema") or {}),
        impl=[ImplBinding(**b) for b in (attrs.get("impl") or [])],
        direct_sql=(
            DirectSqlBinding(**attrs["direct_sql"])
            if isinstance(attrs.get("direct_sql"), dict)
            else None
        ),
        risk_level=str(attrs.get("risk_level") or "read_only"),
        description=str(attrs.get("description") or ""),
        tags=list(attrs.get("tags") or []),
    )


def _resolve_arg(ref: str, args: Dict[str, Any]) -> Any:
    """Resolve a mapping-value reference against caller args.

    Supported forms:
        - ``$now``       - ISO timestamp of now
        - ``@literal:X`` - literal string X
        - ``a.b.c``      - dotted path lookup in args (a['b']['c'])
        - anything else - treated as a bare key lookup in args
    """
    if ref == "$now":
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    if ref.startswith("@literal:"):
        return ref[len("@literal:"):]
    if "." in ref:
        cursor: Any = args
        for part in ref.split("."):
            if isinstance(cursor, dict):
                cursor = cursor.get(part)
            else:
                return None
            if cursor is None:
                return None
        return cursor
    return args.get(ref)


class VdlApiRegistryService:
    _instance: Optional["VdlApiRegistryService"] = None

    def __init__(self, repo: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repo or FoundryWorkspaceRepository()
        self._cache: Dict[str, VdlApiSpec] = {}
        self._cache_loaded_at: float = 0.0
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "VdlApiRegistryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _cache_fresh(self) -> bool:
        return (time.time() - self._cache_loaded_at) < _CACHE_TTL_SECS and bool(self._cache)

    async def _ensure_cache(self) -> None:
        if self._cache_fresh():
            return
        async with self._lock:
            if self._cache_fresh():
                return
            try:
                rows = self._repo.list_vdl_apis()
            except FoundryWorkspaceRepositoryError as e:
                logger.warning(f"VdlApiRegistry list failed: {e}")
                return
            new_cache: Dict[str, VdlApiSpec] = {}
            for row in rows:
                spec = _attrs_to_spec(row)
                if spec.api_id:
                    new_cache[spec.api_id] = spec
            self._cache = new_cache
            self._cache_loaded_at = time.time()

    def invalidate(self) -> None:
        self._cache = {}
        self._cache_loaded_at = 0.0

    # -------- reads --------

    async def get(self, api_id: str) -> Optional[VdlApiSpec]:
        await self._ensure_cache()
        return self._cache.get(api_id)

    async def list(
        self,
        *,
        virtual_entity: Optional[str] = None,
        verb: Optional[str] = None,
    ) -> List[VdlApiSpec]:
        await self._ensure_cache()
        items = list(self._cache.values())
        if verb:
            items = [i for i in items if i.verb == verb]
        if virtual_entity:
            items = [i for i in items if i.virtual_entity == virtual_entity]
        return items

    # -------- writes --------

    async def register(self, spec: VdlApiSpec) -> VdlApiSpec:
        try:
            self._repo.put_vdl_api(spec.api_id, _spec_to_attrs(spec))
            self.invalidate()
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"VdlApiRegistry register({spec.api_id}) failed: {e}")
            raise
        return spec

    async def delete(self, api_id: str) -> bool:
        try:
            self._repo.delete_vdl_api(api_id)
            self.invalidate()
            return True
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"VdlApiRegistry delete({api_id}) failed: {e}")
            return False

    # -------- planning --------

    async def resolve(self, api_id: str, args: Dict[str, Any]) -> ExecutionPlan:
        spec = await self.get(api_id)
        if spec is None:
            raise LookupError(f"vdl api not found: {api_id}")

        steps: List[ExecutionStep] = []
        for binding in spec.impl:
            if binding.when and not self._matches(binding.when, args):
                continue
            step_args: Dict[str, Any] = {}
            for k, v in binding.arg_mapping.items():
                step_args[k] = _resolve_arg(v, args)
            steps.append(ExecutionStep(connector_api_id=binding.connector_api_id, args=step_args))

        return ExecutionPlan(
            api_id=spec.api_id,
            verb=spec.verb,
            virtual_entity=spec.virtual_entity,
            steps=steps,
            direct_sql=spec.direct_sql,
        )

    @staticmethod
    def _matches(predicate: Dict[str, Any], args: Dict[str, Any]) -> bool:
        for k, v in predicate.items():
            if args.get(k) != v:
                return False
        return True

    # -------- bootstrap --------

    async def bootstrap_if_empty(self, seed_specs: List[VdlApiSpec]) -> int:
        try:
            existing = self._repo.list_vdl_apis()
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"VdlApiRegistry bootstrap list failed: {e}")
            return 0
        if existing:
            return 0
        written = 0
        for spec in seed_specs:
            try:
                self._repo.put_vdl_api(spec.api_id, _spec_to_attrs(spec))
                written += 1
            except FoundryWorkspaceRepositoryError as e:
                logger.warning(f"VdlApiRegistry bootstrap seed {spec.api_id} failed: {e}")
        if written:
            self.invalidate()
            logger.info(f"VdlApiRegistry bootstrapped {written} seed specs into DDB")
        return written


def get_vdl_api_registry() -> VdlApiRegistryService:
    return VdlApiRegistryService.get_instance()
