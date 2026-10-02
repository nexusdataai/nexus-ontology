"""
Orphan invariant: every registered ConnectorAPISpec must have at least
one tool whose ``connector_api`` field references it.

If this test fails, either:
  - a Connector API was added without a calling tool, or
  - a tool was renamed without updating its ``connector_api=`` binding.

The fix is one of:
  - bind an existing tool to the orphan api_id, or
  - register a write-back tool in
    ``services/control_plane/tools/erp_writeback_tools.py``, or
  - delete the unused spec.
"""

from __future__ import annotations

import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.control_plane import connector_apis as ca
from src.services.control_plane.tool_registry import ToolRegistry


def _build_registry_with_all_tools() -> ToolRegistry:
    """
    Stand up a ToolRegistry and register every tool module that binds
    ``connector_api`` values. We don't care if read-only tools that need
    a real RAG service end up disabled - we just need every WRITE tool
    binding to be visible.
    """
    registry = ToolRegistry()

    class _RagStub:
        async def hybrid_search(self, *a, **k):
            return {"results": [], "total": 0}

    rag_stub = _RagStub()

    class _VqStub:
        async def query_virtual_entity(self, *a, **k):
            class _R:
                rows = []
            return _R()

    vq_stub = _VqStub()

    from src.services.control_plane.tools.supply_chain_tools import register_supply_chain_tools
    from src.services.control_plane.tools.o2c_tools import register_o2c_tools
    from src.services.control_plane.tools.erp_writeback_tools import register_erp_writeback_tools

    register_supply_chain_tools(registry, rag_stub)
    register_o2c_tools(registry, vq_stub)
    register_erp_writeback_tools(registry)

    return registry


def test_every_connector_api_has_at_least_one_tool_caller():
    registry = _build_registry_with_all_tools()
    bound: set[str] = {
        getattr(t, "connector_api", None) or ""
        for t in registry.list_tools()
    }
    bound.discard("")

    orphans = []
    for spec in ca.list_all():
        if spec.api_id not in bound:
            orphans.append(spec.api_id)

    assert orphans == [], (
        "Connector APIs without any tool caller: " + ", ".join(orphans)
    )


def test_every_tool_binding_targets_registered_api():
    registry = _build_registry_with_all_tools()
    known = {s.api_id for s in ca.list_all()}
    dangling = []
    for t in registry.list_tools():
        cap = getattr(t, "connector_api", None)
        if cap and cap not in known:
            dangling.append((t.name, cap))
    assert dangling == [], (
        "Tools binding to unregistered connector_api: "
        + ", ".join(f"{n}->{c}" for n, c in dangling)
    )
