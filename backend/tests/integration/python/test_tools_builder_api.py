"""
In-process integration test for the Tool Builder REST API.

Stands up a minimal FastAPI app wired with:
  - tools_builder_api router (CRUD + test + versions + import/export)
  - a fake ToolRegistryRepository (in-memory)
  - a real DynamicToolLoader (so /test runs the source through compile())
  - a real ToolRegistry that the API maintains in sync

Drives the full lifecycle:
  create -> get -> list -> update -> versions -> restore -> test -> delete
plus an export -> import roundtrip.

After create, the live ToolRegistry contains the tool (verifies the
"DDB tool visible to the agent" contract).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

import httpx
import pytest
import pytest_asyncio

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


_GOOD_SOURCE = (
    "async def run(params, vdl, connectors, ctx, log):\n"
    "    log.info('hello', who=params.get('who', 'world'))\n"
    "    return {'greeted': params.get('who', 'world')}\n"
)
_GOOD_SOURCE_V2 = (
    "async def run(params, vdl, connectors, ctx, log):\n"
    "    return {'greeted': params.get('who', 'world'), 'version': 2}\n"
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeRepo:
    """Mirrors ToolRegistryRepository in-memory."""

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
# Fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def builder_app():
    from fastapi import FastAPI

    from src.apis import tools_builder_api
    from src.services.control_plane.dynamic_tool_loader import DynamicToolLoader
    from src.services.control_plane.tool_registry import ToolRegistry
    from src.services.control_plane.tool_store_service import ToolStoreService

    repo = FakeRepo()
    store = ToolStoreService(repository=repo)
    registry = ToolRegistry()
    loader = DynamicToolLoader(store=store)

    tools_builder_api.configure(store=store, loader=loader, registry=registry)

    app = FastAPI()
    app.include_router(tools_builder_api.router)
    return app, store, registry, loader


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t.local")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_lifecycle_create_test_update_restore_delete(builder_app):
    app, store, registry, loader = builder_app

    create_body = {
        "name": "greeter_tool",
        "description": "say hello",
        "risk_level": "read_only",
        "source_code": _GOOD_SOURCE,
        "parameters": {
            "type": "object",
            "properties": {"who": {"type": "string"}},
            "required": [],
        },
        "tags": ["demo"],
    }

    async with _client(app) as client:
        # 1. CREATE
        resp = await client.post("/api/v1/tools", json=create_body)
        assert resp.status_code == 201, resp.text
        doc = resp.json()
        tool_id = doc["tool_id"]
        assert doc["current_version"] == 1
        assert doc["name"] == "greeter_tool"

        # The live registry contains the new tool.
        assert registry.get("greeter_tool") is not None

        # 2. GET
        resp = await client.get(f"/api/v1/tools/{tool_id}")
        assert resp.status_code == 200
        assert resp.json()["source_code"] == _GOOD_SOURCE

        # 3. LIST
        resp = await client.get("/api/v1/tools")
        names = [r["name"] for r in resp.json()]
        assert "greeter_tool" in names

        # 4. TEST (dispatches the live source)
        resp = await client.post(
            f"/api/v1/tools/{tool_id}/test",
            json={"params": {"who": "ashis"}},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "pass"
        assert body["result"]["greeted"] == "ashis"
        assert any(l["msg"] == "hello" for l in body["logs"])

        # 5. UPDATE -> writes a new VERSION
        resp = await client.put(
            f"/api/v1/tools/{tool_id}",
            json={"source_code": _GOOD_SOURCE_V2, "changelog": "bump"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["current_version"] == 2

        # 6. VERSIONS
        resp = await client.get(f"/api/v1/tools/{tool_id}/versions")
        versions = resp.json()
        assert [v["version"] for v in versions] == [2, 1]

        # 7. GET VERSION snapshot
        resp = await client.get(f"/api/v1/tools/{tool_id}/versions/1")
        assert resp.status_code == 200
        assert resp.json()["source_code"] == _GOOD_SOURCE

        # 8. RESTORE version 1 -> creates version 3 with original source
        resp = await client.post(f"/api/v1/tools/{tool_id}/restore/1", json={})
        assert resp.status_code == 200, resp.text
        restored = resp.json()
        assert restored["current_version"] == 3
        assert restored["source_code"] == _GOOD_SOURCE

        # 9. TEST after restore picks up the restored source
        resp = await client.post(
            f"/api/v1/tools/{tool_id}/test",
            json={"params": {"who": "team"}},
        )
        body = resp.json()
        assert body["result"]["greeted"] == "team"
        assert "version" not in body["result"]  # the v2 marker is gone

        # 10. DELETE -> tool disappears from registry + list
        resp = await client.delete(f"/api/v1/tools/{tool_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
        assert registry.get("greeter_tool") is None
        resp = await client.get("/api/v1/tools")
        assert "greeter_tool" not in [r["name"] for r in resp.json()]


@pytest.mark.asyncio
async def test_export_then_import_roundtrip(builder_app):
    app, _store, _registry, _loader = builder_app
    async with _client(app) as client:
        await client.post("/api/v1/tools", json={
            "name": "exp_tool",
            "risk_level": "read_only",
            "source_code": _GOOD_SOURCE,
            "tags": ["x"],
        })
        await client.post("/api/v1/tools", json={
            "name": "exp_tool_two",
            "risk_level": "low_risk_write",
            "source_code": _GOOD_SOURCE,
            "tags": ["x"],
        })

        resp = await client.get("/api/v1/tools/export")
        assert resp.status_code == 200
        bundle = resp.json()
        assert len(bundle["tools"]) == 2

        # Re-import in skip_existing mode -> all skipped.
        resp = await client.post("/api/v1/tools/import", json={
            "tools": bundle["tools"], "mode": "skip_existing",
        })
        assert resp.status_code == 200
        result = resp.json()
        assert result["skipped"] == 2
        assert result["imported"] == 0

        # Merge mode -> updates each existing.
        resp = await client.post("/api/v1/tools/import", json={
            "tools": bundle["tools"], "mode": "merge",
        })
        result = resp.json()
        assert result["updated"] == 2
        assert result["imported"] == 0


@pytest.mark.asyncio
async def test_create_rejects_invalid_source(builder_app):
    app, _store, _registry, _loader = builder_app
    async with _client(app) as client:
        resp = await client.post("/api/v1/tools", json={
            "name": "bad_source",
            "risk_level": "read_only",
            "source_code": "x = 1\n",  # no async def run
        })
        assert resp.status_code == 422  # pydantic validation error


@pytest.mark.asyncio
async def test_optimistic_lock_returns_409(builder_app):
    app, _store, _registry, _loader = builder_app
    async with _client(app) as client:
        resp = await client.post("/api/v1/tools", json={
            "name": "locked_tool",
            "risk_level": "read_only",
            "source_code": _GOOD_SOURCE,
        })
        tool_id = resp.json()["tool_id"]
        baseline = resp.json()["updatedAt"]

        # First update with the baseline succeeds.
        resp1 = await client.put(
            f"/api/v1/tools/{tool_id}",
            json={"source_code": _GOOD_SOURCE_V2, "if_unchanged_updated_at": baseline},
        )
        assert resp1.status_code == 200

        # Second update with the SAME baseline must fail with 409.
        resp2 = await client.put(
            f"/api/v1/tools/{tool_id}",
            json={"source_code": _GOOD_SOURCE, "if_unchanged_updated_at": baseline},
        )
        assert resp2.status_code == 409, resp2.text
