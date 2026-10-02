"""
Journey Persistence Service.

Stores Copilot-saved journeys (and any user-authored journey from the
Journey Builder UI) in the same Foundry workspace DynamoDB table that
holds dashboards. The full ``JourneyDoc`` YAML is serialised as JSON in
the META item's ``payloadJson`` attribute.

Item layout (single-table style, mirrors dashboard_service):

| Entity            | PK                  | SK     | GSI1PK    | GSI1SK        |
|-------------------|---------------------|--------|-----------|---------------|
| Journey metadata  | JOURNEY#{uid}       | META   | JOURNEY   | {updatedAt}   |

Public API mirrors the dashboard_service surface so a thin journey API
router can wrap it without bespoke marshalling.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
    journey_pk,
)

js_logger = logger.bind(component="journey-store")

# Same headroom rationale as dashboard_service - DDB hard cap is 400KB.
INLINE_PAYLOAD_MAX_BYTES = 350 * 1024


class JourneyStoreService:
    """Foundry-DDB-backed CRUD for saved journeys."""

    GSI1PK = "JOURNEY"

    def __init__(
        self,
        repository: Optional[FoundryWorkspaceRepository] = None,
        executor_bridge: Any = None,
    ) -> None:
        self._repo = repository or FoundryWorkspaceRepository()
        # JourneyExecutorBridge: when set, every successful create/update
        # mirrors a minimal METADATA row into the transformation-system
        # DDB so the existing /api/v1/journeys/{id}/* endpoints accept
        # the journey_id. Fire-and-forget; failures are logged but never
        # surface to the user-facing save response.
        self._bridge = executor_bridge
        js_logger.info("Journey store initialized", table=self._repo.table_name)

    def configure_executor_bridge(self, bridge: Any) -> None:
        """Late-binding setter so the gateway can wire the bridge
        after both singletons have been constructed."""
        self._bridge = bridge

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(self, journey: Dict[str, Any], user: str = "anonymous") -> Dict[str, Any]:
        """Persist a JourneyDoc-shaped dict and return the saved record."""
        uid = (
            journey.get("journey_id")
            or journey.get("use_case_id")
            or str(uuid4())
        )
        now = datetime.now(timezone.utc).isoformat()
        record = {
            **journey,
            "journey_id": uid,
            "createdAt": journey.get("createdAt") or now,
            "updatedAt": now,
            "createdBy": user,
            "version": 1,
        }
        await self._save(uid, record)
        js_logger.info("Journey saved", journey_id=uid, kind=record.get("kind"))
        self._mirror_metadata_fire_and_forget(uid, record)
        return record

    async def get(self, journey_id: str) -> Optional[Dict[str, Any]]:
        return await self._load(journey_id)

    async def update(self, journey_id: str, journey: Dict[str, Any], user: str = "anonymous") -> Dict[str, Any]:
        existing = await self._load(journey_id)
        if not existing:
            raise ValueError(f"Journey not found: {journey_id}")
        now = datetime.now(timezone.utc).isoformat()
        record = {
            **journey,
            "journey_id": journey_id,
            "createdAt": existing.get("createdAt", now),
            "updatedAt": now,
            "createdBy": existing.get("createdBy", user),
            "version": int(existing.get("version", 1)) + 1,
        }
        await self._save(journey_id, record)
        self._mirror_metadata_fire_and_forget(journey_id, record)
        return record

    async def delete(self, journey_id: str) -> bool:
        try:
            self._repo.delete_pk(journey_pk(journey_id))
            return True
        except FoundryWorkspaceRepositoryError as e:
            js_logger.warning(f"DDB delete failed for {journey_id}: {e}")
            return False

    async def list_all(
        self,
        search: str = "",
        tags: Optional[List[str]] = None,
        kind: Optional[str] = None,
        solution_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            rows = self._repo.query_gsi1(self.GSI1PK, scan_forward=False)
        except FoundryWorkspaceRepositoryError as e:
            js_logger.warning(f"DDB list failed: {e}")
            rows = []

        out: List[Dict[str, Any]] = []
        for row in rows:
            try:
                journey = self._item_to_journey(row)
            except Exception as e:
                js_logger.warning(f"Failed to hydrate journey {row.get('PK')}: {e}")
                continue
            out.append(journey)

        if search:
            q = search.lower()
            out = [
                j for j in out
                if q in str(j.get("title") or j.get("display_name") or "").lower()
                or q in str(j.get("description") or "").lower()
                or q in str(j.get("journey_id") or "").lower()
            ]
        if tags:
            tag_set = set(tags)
            out = [j for j in out if tag_set.intersection(set(j.get("tags") or []))]
        if kind:
            out = [j for j in out if j.get("kind") == kind]
        if solution_id:
            out = [j for j in out if j.get("solution_id") == solution_id]

        out.sort(key=lambda j: str(j.get("updatedAt") or ""), reverse=True)
        return out

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    async def _save(self, uid: str, record: Dict[str, Any]) -> None:
        title = (
            record.get("title")
            or record.get("display_name")
            or record.get("name")
            or uid
        )
        attrs: Dict[str, Any] = {
            "journey_id": uid,
            "title": title,
            "description": record.get("description"),
            "kind": record.get("kind", "user_authored"),
            "solution_id": record.get("solution_id"),
            "tags": record.get("tags", []) or [],
            "createdAt": record.get("createdAt"),
            "updatedAt": record.get("updatedAt"),
            "createdBy": record.get("createdBy"),
            "version": record.get("version", 1),
        }

        payload_json = json.dumps(record, default=str)
        if len(payload_json.encode("utf-8")) > INLINE_PAYLOAD_MAX_BYTES:
            # Same overflow story as dashboards: extremely large journeys
            # can be pushed to S3 in a follow-up. For now we accept the
            # warning and still persist the truncated metadata so the
            # journey list works.
            js_logger.warning(
                "Journey payload exceeds inline cap; storing without payloadJson",
                journey_id=uid, size_bytes=len(payload_json),
            )
        else:
            attrs["payloadJson"] = payload_json

        try:
            self._repo.put_meta(
                pk=journey_pk(uid),
                attrs=attrs,
                gsi1pk=self.GSI1PK,
                gsi1sk=record.get("updatedAt") or "",
            )
        except FoundryWorkspaceRepositoryError as e:
            js_logger.error(f"DDB save failed for {uid}: {e}")
            raise

    def _mirror_metadata_fire_and_forget(
        self, uid: str, record: Dict[str, Any],
    ) -> None:
        """Schedule a best-effort METADATA mirror into the
        transformation-system DDB so the existing /api/v1/journeys/{id}/
        endpoints accept this journey_id. Runs as an asyncio task so
        save latency is not affected; failures are logged only."""
        if self._bridge is None:
            return
        title = (
            record.get("title")
            or record.get("display_name")
            or record.get("name")
            or uid
        )
        solution_id = record.get("solution_id")
        kind = record.get("kind") or "user_authored"

        def _mirror():
            try:
                self._bridge.ensure_metadata(
                    uid, title=title, solution_id=solution_id, kind=kind,
                )
            except Exception as e:
                js_logger.debug(f"bridge.ensure_metadata for {uid} failed: {e}")

        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, _mirror)
        except RuntimeError:
            # No running loop -- run synchronously, still best-effort.
            _mirror()

    async def _load(self, uid: str) -> Optional[Dict[str, Any]]:
        item = self._repo.get_meta(journey_pk(uid))
        if not item:
            return None
        return self._item_to_journey(item)

    def _item_to_journey(self, item: Dict[str, Any]) -> Dict[str, Any]:
        payload_json = item.get("payloadJson")
        if payload_json:
            try:
                return json.loads(payload_json)
            except Exception as e:
                js_logger.warning(f"payloadJson parse failed for {item.get('journey_id')}: {e}")
        # Fallback: return the metadata-only view (list endpoint can hide
        # rows without payloadJson if it wants execution).
        return {
            "journey_id": item.get("journey_id") or item.get("PK", "").replace("JOURNEY#", ""),
            "title": item.get("title"),
            "description": item.get("description"),
            "kind": item.get("kind"),
            "solution_id": item.get("solution_id"),
            "tags": item.get("tags") or [],
            "createdAt": item.get("createdAt"),
            "updatedAt": item.get("updatedAt"),
            "createdBy": item.get("createdBy"),
            "version": item.get("version"),
        }
