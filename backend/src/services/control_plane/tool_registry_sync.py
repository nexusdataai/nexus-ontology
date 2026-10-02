"""
Tool Registry Sync.

Background task that periodically reconciles the live ``ToolRegistry``
on this pod with the DynamoDB-backed source of truth. Handles the
multi-pod case where pod A creates a tool through the API and pods B/C
need to pick it up.

Strategy: every ``poll_interval_s``, list active DDB tools, compare each
``(tool_id, source_sha256)`` against the local cache, and:

  - add tools we don't know about
  - replace tools whose source_sha256 changed
  - remove tools that disappeared (or were soft-deleted)

Code-defined tools are never touched - we only manage names belonging
to the DDB-managed set (tracked by ``self._owned_names``).

Worst-case staleness: ``poll_interval_s`` (default 60s).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Set

from loguru import logger

from src.services.control_plane.dynamic_tool_loader import DynamicToolLoader

trs_logger = logger.bind(component="tool-registry-sync")


class ToolRegistrySync:
    def __init__(
        self,
        registry: Any,
        store: Any,
        loader: DynamicToolLoader,
        poll_interval_s: int = 60,
    ) -> None:
        self._registry = registry
        self._store = store
        self._loader = loader
        self._interval = max(10, int(poll_interval_s))
        self._task: Optional[asyncio.Task] = None
        # tool_id -> source_sha256 for tools we own in the registry
        self._owned: Dict[str, str] = {}
        # tool name we last registered for each tool_id - lets us evict
        # cleanly even if the user renames (current models don't allow
        # rename, but we keep this map ready).
        self._owned_names: Dict[str, str] = {}

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            return
        self._task = loop.create_task(self._run())
        trs_logger.info("ToolRegistrySync started (interval={}s)", self._interval)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

    async def reconcile_now(self) -> Dict[str, int]:
        """Run one reconciliation pass. Returns a {action: count} summary."""
        return await self._reconcile()

    async def _run(self) -> None:
        while True:
            try:
                await self._reconcile()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                trs_logger.warning("reconcile pass failed: {}", e)
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                raise

    async def _reconcile(self) -> Dict[str, int]:
        if self._store is None or self._registry is None or self._loader is None:
            return {"added": 0, "updated": 0, "removed": 0}

        try:
            summaries = await self._store.list()
        except Exception as e:
            trs_logger.debug("list active tools failed: {}", e)
            return {"added": 0, "updated": 0, "removed": 0}

        live_ids: Set[str] = set()
        added = updated = removed = 0
        existing_names = {t.name for t in self._registry.list_tools()}

        for s in summaries:
            tool_id = s.tool_id
            live_ids.add(tool_id)
            try:
                doc = await self._store.get(tool_id)
            except Exception:
                continue
            if doc is None:
                continue
            meta = doc.dict()
            sha = str(meta.get("source_sha256") or "")

            prior_sha = self._owned.get(tool_id)
            if prior_sha is None:
                # New tool from DDB. Don't shadow code-defined tools.
                if doc.name in existing_names and tool_id not in self._owned_names:
                    trs_logger.warning(
                        "DDB tool '{}' shadowed by existing tool of same name; skipping", doc.name
                    )
                    continue
                try:
                    self._registry.register(self._loader.make_tool(meta))
                    self._owned[tool_id] = sha
                    self._owned_names[tool_id] = doc.name
                    added += 1
                except Exception as e:
                    trs_logger.warning("add {} failed: {}", tool_id, e)
            elif prior_sha != sha or self._owned_names.get(tool_id) != doc.name:
                try:
                    self._loader.invalidate(tool_id)
                    # Drop old name slot if the name changed (defensive).
                    old_name = self._owned_names.get(tool_id)
                    if old_name and old_name != doc.name and hasattr(self._registry, "_tools"):
                        self._registry._tools.pop(old_name, None)
                    self._registry.register(self._loader.make_tool(meta))
                    self._owned[tool_id] = sha
                    self._owned_names[tool_id] = doc.name
                    updated += 1
                except Exception as e:
                    trs_logger.warning("update {} failed: {}", tool_id, e)

        # Remove tools that disappeared from DDB.
        for tool_id in list(self._owned.keys()):
            if tool_id in live_ids:
                continue
            name = self._owned_names.get(tool_id)
            try:
                if name and hasattr(self._registry, "_tools"):
                    self._registry._tools.pop(name, None)
                self._loader.invalidate(tool_id)
                self._owned.pop(tool_id, None)
                self._owned_names.pop(tool_id, None)
                removed += 1
            except Exception as e:
                trs_logger.warning("remove {} failed: {}", tool_id, e)

        if added or updated or removed:
            trs_logger.info(
                "reconcile: added={} updated={} removed={}",
                added, updated, removed,
            )
        return {"added": added, "updated": updated, "removed": removed}
