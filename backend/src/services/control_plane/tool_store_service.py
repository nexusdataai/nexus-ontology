"""
Tool Store Service.

High-level CRUD + import/export API for user-authored ReAct tools. Sits
between the REST router and the DynamoDB repository, owns versioning
semantics, and emits a Redis pub/sub event after every mutation so other
pods invalidate their ``DynamicToolLoader`` caches.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger

from src.models.tool_builder_models import (
    ToolCreate,
    ToolDoc,
    ToolImportBundle,
    ToolImportResult,
    ToolStatus,
    ToolSummary,
    ToolUpdate,
    ToolVersion,
    source_hash,
)
from src.repositories.tool_registry_repository import (
    ToolRegistryRepository,
    ToolRegistryRepositoryError,
)

ts_logger = logger.bind(component="tool-store")

INVALIDATION_CHANNEL = "tool-cache-invalidate"


class ToolStoreError(Exception):
    """Raised by ToolStoreService for caller-visible failures."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _meta_to_doc(meta: Dict[str, Any]) -> ToolDoc:
    return ToolDoc(
        tool_id=meta.get("tool_id") or str(meta.get("PK", "")).replace("TOOL#", ""),
        name=meta.get("name", ""),
        description=meta.get("description", "") or "",
        risk_level=meta.get("risk_level", "read_only"),
        requires_approval=bool(meta.get("requires_approval", False)),
        cacheable=bool(meta.get("cacheable", False)),
        connector_api=meta.get("connector_api"),
        tags=list(meta.get("tags") or []),
        current_version=int(meta.get("current_version", 1)),
        status=meta.get("status", "active"),
        createdBy=meta.get("createdBy"),
        createdAt=meta.get("createdAt"),
        updatedAt=meta.get("updatedAt"),
        parameters=dict(meta.get("parameters") or {"type": "object", "properties": {}, "required": []}),
        source_code=meta.get("source_code", "") or "",
        source_sha256=meta.get("source_sha256"),
        changelog=meta.get("changelog"),
        tool_kind=meta.get("tool_kind"),
        header_comment=meta.get("header_comment"),
    )


def _meta_to_summary(meta: Dict[str, Any]) -> ToolSummary:
    return ToolSummary(
        tool_id=meta.get("tool_id") or str(meta.get("PK", "")).replace("TOOL#", ""),
        name=meta.get("name", ""),
        description=meta.get("description", "") or "",
        risk_level=meta.get("risk_level", "read_only"),
        requires_approval=bool(meta.get("requires_approval", False)),
        cacheable=bool(meta.get("cacheable", False)),
        connector_api=meta.get("connector_api"),
        tags=list(meta.get("tags") or []),
        current_version=int(meta.get("current_version", 1)),
        status=meta.get("status", "active"),
        createdBy=meta.get("createdBy"),
        createdAt=meta.get("createdAt"),
        updatedAt=meta.get("updatedAt"),
        tool_kind=meta.get("tool_kind"),
        header_comment=meta.get("header_comment"),
    )


class ToolStoreService:
    """Public API for the Tool Builder. Idempotent against DDB and Redis."""

    def __init__(
        self,
        repository: Optional[ToolRegistryRepository] = None,
        redis_publisher: Optional[Any] = None,
    ) -> None:
        self._repo = repository or ToolRegistryRepository()
        self._publisher = redis_publisher
        ts_logger.info("ToolStoreService initialized: table={}", self._repo.table_name)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, body: ToolCreate, user: str = "anonymous") -> ToolDoc:
        # Reject duplicate names against existing active tools to avoid two
        # rows competing for the same registry entry.
        for existing in self._repo.list_active_tools():
            if existing.get("name") == body.name:
                raise ToolStoreError(f"tool name '{body.name}' already exists")

        tool_id = f"tool-{body.name}-{uuid4().hex[:8]}"
        now = _now_iso()
        attrs = {
            "tool_id": tool_id,
            "name": body.name,
            "description": body.description,
            "parameters": body.parameters,
            "risk_level": body.risk_level.value,
            "requires_approval": body.requires_approval,
            "cacheable": body.cacheable,
            "connector_api": body.connector_api,
            "tags": list(body.tags),
            "source_code": body.source_code,
            "source_sha256": source_hash(body.source_code),
            "current_version": 1,
            "status": ToolStatus.ACTIVE.value,
            "createdBy": user,
            "createdAt": now,
            "updatedAt": now,
            "tool_kind": body.tool_kind,
            "header_comment": body.header_comment,
        }
        try:
            self._repo.put_tool_meta(tool_id, attrs, condition_not_exists=True)
            self._repo.put_tool_version(tool_id, 1, {
                "source_code": body.source_code,
                "parameters": body.parameters,
                "source_sha256": attrs["source_sha256"],
                "changelog": "initial version",
                "createdBy": user,
                "createdAt": now,
            })
            self._repo.put_tool_tags(tool_id, body.tags)
        except ToolRegistryRepositoryError as e:
            raise ToolStoreError(str(e))

        await self._publish(tool_id, "create")
        ts_logger.info("Tool created: {}", tool_id)
        return _meta_to_doc(attrs)

    async def update(
        self, tool_id: str, body: ToolUpdate, user: str = "anonymous",
    ) -> ToolDoc:
        meta = self._repo.get_tool_meta(tool_id)
        if not meta or meta.get("status") == "deleted":
            raise ToolStoreError(f"tool not found: {tool_id}")

        next_version = int(meta.get("current_version", 1)) + 1
        now = _now_iso()
        new_meta = dict(meta)
        if body.description is not None:
            new_meta["description"] = body.description
        if body.parameters is not None:
            new_meta["parameters"] = body.parameters
        if body.risk_level is not None:
            new_meta["risk_level"] = body.risk_level.value
        if body.requires_approval is not None:
            new_meta["requires_approval"] = body.requires_approval
        if body.cacheable is not None:
            new_meta["cacheable"] = body.cacheable
        if body.connector_api is not None:
            new_meta["connector_api"] = body.connector_api
        if body.tags is not None:
            new_meta["tags"] = list(body.tags)
        if body.source_code is not None:
            new_meta["source_code"] = body.source_code
            new_meta["source_sha256"] = source_hash(body.source_code)
        if body.tool_kind is not None:
            new_meta["tool_kind"] = body.tool_kind
        if body.header_comment is not None:
            new_meta["header_comment"] = body.header_comment
        new_meta["current_version"] = next_version
        new_meta["updatedAt"] = now
        new_meta["changelog"] = body.changelog

        # Optimistic lock: only proceed if the prior updatedAt matches.
        if_unchanged = body.if_unchanged_updated_at
        if if_unchanged is None:
            if_unchanged = meta.get("updatedAt")

        try:
            self._repo.put_tool_meta(
                tool_id, new_meta,
                if_unchanged_updated_at=if_unchanged,
            )
            self._repo.put_tool_version(tool_id, next_version, {
                "source_code": new_meta.get("source_code", ""),
                "parameters": new_meta.get("parameters", {}),
                "source_sha256": new_meta.get("source_sha256"),
                "changelog": body.changelog or "",
                "createdBy": user,
                "createdAt": now,
            })
            if body.tags is not None:
                self._repo.put_tool_tags(tool_id, body.tags)
        except ToolRegistryRepositoryError as e:
            raise ToolStoreError(str(e))

        await self._publish(tool_id, "update")
        return _meta_to_doc(new_meta)

    async def get(
        self, tool_id: str, version: Optional[int] = None,
    ) -> Optional[ToolDoc]:
        if version is not None:
            v = self._repo.get_tool_version(tool_id, version)
            if not v:
                return None
            meta = self._repo.get_tool_meta(tool_id) or {}
            doc = _meta_to_doc({
                **meta,
                "source_code": v.get("source_code", ""),
                "parameters": v.get("parameters", {}),
                "source_sha256": v.get("source_sha256"),
                "current_version": int(v.get("version", 0)),
                "changelog": v.get("changelog"),
            })
            return doc
        meta = self._repo.get_tool_meta(tool_id)
        if not meta:
            return None
        return _meta_to_doc(meta)

    async def list(
        self,
        search: str = "",
        tags: Optional[List[str]] = None,
        risk_level: Optional[str] = None,
        include_deleted: bool = False,
    ) -> List[ToolSummary]:
        rows = self._repo.list_active_tools()
        if include_deleted:
            try:
                from src.repositories.foundry_workspace_repository import (
                    FoundryWorkspaceRepository,
                )
                _ = FoundryWorkspaceRepository  # imported for type only; rows already filtered above
            except Exception:
                pass

        out = [_meta_to_summary(r) for r in rows]
        if search:
            q = search.lower()
            out = [
                s for s in out
                if q in (s.name or "").lower()
                or q in (s.description or "").lower()
                or q in (s.tool_id or "").lower()
            ]
        if tags:
            tag_set = set(tags)
            out = [s for s in out if tag_set.intersection(set(s.tags or []))]
        if risk_level:
            out = [s for s in out if s.risk_level.value == risk_level]
        out.sort(key=lambda s: s.updatedAt or "", reverse=True)
        return out

    async def delete(self, tool_id: str, user: str = "anonymous") -> bool:
        meta = self._repo.get_tool_meta(tool_id)
        if not meta:
            return False
        try:
            self._repo.soft_delete_tool(
                tool_id, deleted_by=user, deleted_at=_now_iso()
            )
        except ToolRegistryRepositoryError as e:
            raise ToolStoreError(str(e))
        await self._publish(tool_id, "delete")
        return True

    async def list_versions(self, tool_id: str) -> List[ToolVersion]:
        rows = self._repo.list_tool_versions(tool_id)
        out: List[ToolVersion] = []
        for r in rows:
            out.append(ToolVersion(
                tool_id=tool_id,
                version=int(r.get("version", 0)),
                source_code=r.get("source_code", "") or "",
                parameters=dict(r.get("parameters") or {}),
                source_sha256=r.get("source_sha256"),
                changelog=r.get("changelog"),
                createdBy=r.get("createdBy"),
                createdAt=r.get("createdAt"),
            ))
        return out

    async def restore_version(
        self, tool_id: str, version: int, user: str = "anonymous",
    ) -> ToolDoc:
        v = self._repo.get_tool_version(tool_id, version)
        if not v:
            raise ToolStoreError(f"version {version} not found for {tool_id}")
        body = ToolUpdate(
            source_code=v.get("source_code", ""),
            parameters=v.get("parameters") or None,
            changelog=f"restored from version {version}",
        )
        return await self.update(tool_id, body, user=user)

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    async def export_bundle(
        self, tool_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        rows = self._repo.list_active_tools()
        if tool_ids:
            wanted = set(tool_ids)
            rows = [r for r in rows if r.get("tool_id") in wanted]
        return {
            "exported_at": _now_iso(),
            "tools": [
                {
                    "name": r.get("name"),
                    "description": r.get("description"),
                    "parameters": r.get("parameters"),
                    "risk_level": r.get("risk_level"),
                    "requires_approval": r.get("requires_approval"),
                    "cacheable": r.get("cacheable"),
                    "connector_api": r.get("connector_api"),
                    "tags": r.get("tags") or [],
                    "source_code": r.get("source_code"),
                }
                for r in rows
            ],
        }

    async def import_bundle(
        self, bundle: ToolImportBundle, user: str = "anonymous",
    ) -> ToolImportResult:
        result = ToolImportResult()
        existing_by_name = {
            t.get("name"): t for t in self._repo.list_active_tools() if t.get("name")
        }
        for body in bundle.tools:
            try:
                if body.name in existing_by_name:
                    if bundle.mode == "skip_existing":
                        result.skipped += 1
                        continue
                    if bundle.mode in ("merge", "replace"):
                        existing = existing_by_name[body.name]
                        upd = ToolUpdate(
                            description=body.description,
                            parameters=body.parameters,
                            risk_level=body.risk_level,
                            requires_approval=body.requires_approval,
                            cacheable=body.cacheable,
                            connector_api=body.connector_api,
                            tags=body.tags,
                            source_code=body.source_code,
                            changelog=f"import:{bundle.mode}",
                        )
                        await self.update(existing.get("tool_id"), upd, user=user)
                        result.updated += 1
                        continue
                await self.create(body, user=user)
                result.imported += 1
            except Exception as e:
                result.errors.append({"name": body.name, "error": str(e)})
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _publish(self, tool_id: str, action: str) -> None:
        """Best-effort Redis pub/sub broadcast. Silent on failure."""
        if self._publisher is None:
            return
        try:
            payload = json.dumps({"tool_id": tool_id, "action": action, "ts": _now_iso()})
            await self._publisher.publish(INVALIDATION_CHANNEL, payload)
        except Exception as e:
            ts_logger.debug("invalidation publish failed: {}", e)
