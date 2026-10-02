"""
Unit tests for ``services/control_plane/dynamic_tool_loader.py``.

Exercises compile + cache + watchdog + audit emission against pure
fakes (no DDB, no FastAPI, no live simulator).
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, List

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.control_plane.dynamic_tool_loader import DynamicToolLoader
from src.services.control_plane.tool_registry import RiskLevel, ToolRegistry


_TRIVIAL_TOOL = """
async def run(params, vdl, connectors, ctx, log):
    log.info("hello", who=params.get("who", "world"))
    return {"greeted": params.get("who", "world")}
""".strip()


_FAILING_TOOL = """
async def run(params, vdl, connectors, ctx, log):
    raise ValueError("intentional")
""".strip()


_HANG_TOOL = """
import asyncio
async def run(params, vdl, connectors, ctx, log):
    await asyncio.sleep(10)
    return {"ok": True}
""".strip()


class FakeStore:
    async def list(self):  # not used in these tests
        return []

    async def get(self, _tool_id, version=None):
        return None


def _meta(name: str, source: str, version: int = 1) -> Dict[str, Any]:
    return {
        "tool_id": f"tool-{name}-abc",
        "name": name,
        "description": "test",
        "risk_level": "read_only",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "source_code": source,
        "source_sha256": f"sha-{version}",
        "current_version": version,
    }


@pytest.mark.asyncio
async def test_compile_and_dispatch_returns_result():
    audits: List[Dict[str, Any]] = []

    async def emit_audit(**kw):
        audits.append(kw)

    loader = DynamicToolLoader(
        store=FakeStore(),
        emit_audit_fn=emit_audit,
    )
    out = await loader.dispatch(_meta("greeter", _TRIVIAL_TOOL), {"who": "ashis"})
    assert out["greeted"] == "ashis"
    assert "_meta" in out
    assert audits, "expected at least one audit emission"
    assert audits[0]["api_id"].startswith("tool.")
    assert audits[0]["payload"]["status"] == "ok"


@pytest.mark.asyncio
async def test_compile_caches_per_version():
    loader = DynamicToolLoader(store=FakeStore())
    meta = _meta("greeter", _TRIVIAL_TOOL, version=1)
    await loader.dispatch(meta, {})
    cache_size_after_first = len(loader._compiled)
    await loader.dispatch(meta, {})
    assert len(loader._compiled) == cache_size_after_first

    # New version => new cache entry.
    meta_v2 = _meta("greeter", _TRIVIAL_TOOL, version=2)
    meta_v2["source_sha256"] = "sha-2"
    await loader.dispatch(meta_v2, {})
    assert len(loader._compiled) == cache_size_after_first + 1


@pytest.mark.asyncio
async def test_dispatch_returns_error_on_exception():
    audits = []

    async def emit_audit(**kw):
        audits.append(kw)

    loader = DynamicToolLoader(store=FakeStore(), emit_audit_fn=emit_audit)
    out = await loader.dispatch(_meta("bad", _FAILING_TOOL), {})
    assert "error" in out
    assert "intentional" in out["error"]
    # Audit recorded with status=exception.
    assert any(a["payload"].get("status") == "exception" for a in audits)


@pytest.mark.asyncio
async def test_watchdog_kills_runaway_tool():
    loader = DynamicToolLoader(store=FakeStore(), timeout_s=1)
    out = await loader.dispatch(_meta("hang", _HANG_TOOL), {})
    assert "error" in out
    assert "watchdog" in out["error"]


@pytest.mark.asyncio
async def test_invalidate_drops_cache():
    loader = DynamicToolLoader(store=FakeStore())
    await loader.dispatch(_meta("greeter", _TRIVIAL_TOOL), {})
    assert loader._compiled
    loader.invalidate("tool-greeter-abc")
    assert not loader._compiled


@pytest.mark.asyncio
async def test_make_tool_returns_registrable_tool():
    loader = DynamicToolLoader(store=FakeStore())
    meta = _meta("greeter", _TRIVIAL_TOOL)
    tool = loader.make_tool(meta)
    assert tool.name == "greeter"
    assert tool.risk_level == RiskLevel.READ_ONLY
    # Register and execute via the registry.
    reg = ToolRegistry()
    reg.register(tool)
    result = await reg.execute("greeter", {"who": "team"})
    assert result["greeted"] == "team"


@pytest.mark.asyncio
async def test_compile_rejects_source_without_run():
    loader = DynamicToolLoader(store=FakeStore())
    with pytest.raises(ValueError):
        loader.compile("x = 1\n")
