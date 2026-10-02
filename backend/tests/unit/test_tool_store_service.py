"""
Unit tests for ``services/control_plane/tool_store_service.py``.

Uses an in-memory fake repository so we cover the store's versioning,
optimistic locking, list/filter, restore, and import/export semantics
without spinning up DDB.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.models.tool_builder_models import (
    ToolCreate,
    ToolImportBundle,
    ToolUpdate,
)
from src.services.control_plane.tool_store_service import (
    ToolStoreError,
    ToolStoreService,
)


_GOOD_SOURCE = "async def run(params, vdl, connectors, ctx, log):\n    return {}\n"
_GOOD_SOURCE_V2 = "async def run(params, vdl, connectors, ctx, log):\n    return {'v': 2}\n"


class FakeRepo:
    """In-memory fake of ToolRegistryRepository."""

    def __init__(self) -> None:
        self.meta: Dict[str, Dict[str, Any]] = {}
        self.versions: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self.tags: Dict[str, List[str]] = {}

    @property
    def table_name(self) -> str:
        return "fake-table"

    def list_active_tools(self) -> List[Dict[str, Any]]:
        return [m for m in self.meta.values() if m.get("status", "active") != "deleted"]

    def put_tool_meta(
        self,
        tool_id: str,
        attrs: Dict[str, Any],
        *,
        condition_not_exists: bool = False,
        if_unchanged_updated_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        from src.repositories.tool_registry_repository import ToolRegistryRepositoryError
        existing = self.meta.get(tool_id)
        if condition_not_exists and existing is not None:
            raise ToolRegistryRepositoryError("already exists")
        if if_unchanged_updated_at is not None and existing is not None:
            if existing.get("updatedAt") != if_unchanged_updated_at:
                raise ToolRegistryRepositoryError("concurrent-modification conflict")
        self.meta[tool_id] = dict(attrs)
        return self.meta[tool_id]

    def get_tool_meta(self, tool_id: str) -> Optional[Dict[str, Any]]:
        return self.meta.get(tool_id)

    def soft_delete_tool(self, tool_id: str, *, deleted_by: str, deleted_at: str) -> None:
        m = self.meta.get(tool_id)
        if m is None:
            return
        m["status"] = "deleted"
        m["deletedBy"] = deleted_by
        m["deletedAt"] = deleted_at
        m["updatedAt"] = deleted_at

    def put_tool_version(self, tool_id: str, version: int, attrs: Dict[str, Any]) -> Dict[str, Any]:
        self.versions.setdefault(tool_id, {})[int(version)] = dict(attrs)
        self.versions[tool_id][int(version)]["version"] = int(version)
        return self.versions[tool_id][int(version)]

    def get_tool_version(self, tool_id: str, version: int) -> Optional[Dict[str, Any]]:
        return self.versions.get(tool_id, {}).get(int(version))

    def list_tool_versions(self, tool_id: str) -> List[Dict[str, Any]]:
        return sorted(
            self.versions.get(tool_id, {}).values(),
            key=lambda r: int(r.get("version", 0)),
            reverse=True,
        )

    def put_tool_tags(self, tool_id: str, tags: List[str]) -> None:
        self.tags[tool_id] = list(tags or [])


# ---------------------------------------------------------------------------

@pytest.fixture
def store() -> ToolStoreService:
    repo = FakeRepo()
    svc = ToolStoreService(repository=repo)
    return svc


@pytest.mark.asyncio
async def test_create_persists_and_returns_doc(store: ToolStoreService):
    body = ToolCreate(
        name="my_tool",
        description="d",
        risk_level="read_only",
        source_code=_GOOD_SOURCE,
    )
    doc = await store.create(body, user="u1")
    assert doc.tool_id.startswith("tool-my_tool-")
    assert doc.current_version == 1
    assert doc.source_sha256
    assert doc.createdBy == "u1"


@pytest.mark.asyncio
async def test_create_rejects_duplicate_name(store: ToolStoreService):
    body = ToolCreate(
        name="dup_tool",
        risk_level="read_only",
        source_code=_GOOD_SOURCE,
    )
    await store.create(body)
    with pytest.raises(ToolStoreError):
        await store.create(body)


@pytest.mark.asyncio
async def test_update_bumps_version_and_writes_history(store: ToolStoreService):
    doc = await store.create(ToolCreate(
        name="versioned",
        risk_level="read_only",
        source_code=_GOOD_SOURCE,
    ))
    assert doc.current_version == 1

    updated = await store.update(
        doc.tool_id,
        ToolUpdate(source_code=_GOOD_SOURCE_V2, changelog="bump"),
    )
    assert updated.current_version == 2

    versions = await store.list_versions(doc.tool_id)
    assert [v.version for v in versions] == [2, 1]


@pytest.mark.asyncio
async def test_optimistic_lock_rejects_stale_update(store: ToolStoreService):
    doc = await store.create(ToolCreate(
        name="locked",
        risk_level="read_only",
        source_code=_GOOD_SOURCE,
    ))
    # Two clients hold the same baseline; first wins.
    baseline = doc.updatedAt
    await store.update(
        doc.tool_id,
        ToolUpdate(source_code=_GOOD_SOURCE_V2, if_unchanged_updated_at=baseline),
    )
    with pytest.raises(ToolStoreError):
        await store.update(
            doc.tool_id,
            ToolUpdate(source_code=_GOOD_SOURCE, if_unchanged_updated_at=baseline),
        )


@pytest.mark.asyncio
async def test_restore_version_promotes_old_source(store: ToolStoreService):
    doc = await store.create(ToolCreate(
        name="restorable",
        risk_level="read_only",
        source_code=_GOOD_SOURCE,
    ))
    await store.update(doc.tool_id, ToolUpdate(source_code=_GOOD_SOURCE_V2))

    restored = await store.restore_version(doc.tool_id, 1)
    assert restored.current_version == 3  # 1 (initial) -> 2 (update) -> 3 (restore)
    assert restored.source_code == _GOOD_SOURCE


@pytest.mark.asyncio
async def test_list_filters_by_search_and_risk(store: ToolStoreService):
    await store.create(ToolCreate(
        name="alpha_tool", risk_level="read_only", source_code=_GOOD_SOURCE,
        description="alpha thing", tags=["a"],
    ))
    await store.create(ToolCreate(
        name="beta_tool", risk_level="high_risk_write", source_code=_GOOD_SOURCE,
        description="beta thing", tags=["b"],
    ))
    out = await store.list(search="alpha")
    assert {s.name for s in out} == {"alpha_tool"}

    out2 = await store.list(risk_level="high_risk_write")
    assert {s.name for s in out2} == {"beta_tool"}


@pytest.mark.asyncio
async def test_delete_marks_status(store: ToolStoreService):
    doc = await store.create(ToolCreate(
        name="goner", risk_level="read_only", source_code=_GOOD_SOURCE,
    ))
    ok = await store.delete(doc.tool_id)
    assert ok is True
    assert (await store.list()) == []  # soft-deleted hidden from list_active


@pytest.mark.asyncio
async def test_export_roundtrips_through_import(store: ToolStoreService):
    await store.create(ToolCreate(
        name="exp_tool", risk_level="read_only", source_code=_GOOD_SOURCE,
        tags=["x"],
    ))
    bundle = await store.export_bundle()
    assert len(bundle["tools"]) == 1
    # Fresh store, import the bundle.
    fresh = ToolStoreService(repository=FakeRepo())
    res = await fresh.import_bundle(ToolImportBundle(**{"tools": bundle["tools"], "mode": "merge"}))
    assert res.imported == 1
    listed = await fresh.list()
    assert {s.name for s in listed} == {"exp_tool"}
