"""
Regression guard for the ReAct Tools canary catalogue.

If a contributor adds a new write tool without wiring up its canary, or
references a diagnostic sentinel ID that the simulator seed does not
contain, the ReAct Tools Diagnostics page goes amber/red the next time
canaries run. These tests fail offline (no simulator boot, no HTTP) the
moment that drift is introduced, so the issue is caught at commit time.

Covers three invariants:

  1. Every registered tool whose ``parameters.required`` is non-empty has
     an entry in ``CANARY_PARAMS`` (or is explicitly listed in
     ``SKIP_CANARY``).
  2. Every required tool parameter key is present in its configured
     canary params (otherwise ``ToolRegistry.execute`` will raise
     ``TypeError`` and the canary will flip to ``fail``).
  3. Every ``*-DIAG-*`` sentinel ID referenced by ``CANARY_PARAMS`` is
     present in the ``DIAGNOSTIC_SENTINELS`` map (which the simulator
     ``seed_data()`` methods read at boot).
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, Iterable

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.control_plane import react_tools_diagnostics as rtd
from src.services.control_plane._diagnostic_seed import DIAGNOSTIC_SENTINELS
from src.services.control_plane.tool_registry import ToolRegistry


SKIP_CANARY: set[str] = {
    # block_supplier_orders calls update_one against Oracle_Supplier, but
    # the Oracle simulator does not seed that table at all - canary would
    # always fail. Skipped until the supplier table is added to the
    # Oracle seed.
    "block_supplier_orders",
}

# Sentinel-shaped IDs that are intentionally used as foreign-key / label
# values (not as PKs the tool will look up). They do not require a seeded
# row in DIAGNOSTIC_SENTINELS.
KNOWN_LABEL_SENTINELS: set[str] = {
    "ACT-DIAG-1",   # record_outcome.action_id (link to parent action)
    "PL-DIAG-2",    # create_transfer_order.to_plant (destination label)
    "SKU-DIAG-1",   # simulate_promotion_impact.sku (label only)
    "EQ-DIAG-1",    # schedule_predictive_maintenance.equipment_id (append-only)
    "TMPL-DIAG-1",  # send_whatsapp_campaign.template_id (label)
}
SENTINEL_RE = re.compile(r"^[A-Z]+-DIAG-\d+$")


def _build_registry() -> ToolRegistry:
    """Stand up a registry with every tool module that exists today.

    Stubs the live services so registration runs offline.
    """
    registry = ToolRegistry()

    class _RagStub:
        async def hybrid_search(self, *a, **k):
            return {"results": [], "total": 0}

    class _VqStub:
        async def query_virtual_entity(self, *a, **k):
            class _R:
                rows = []
            return _R()

    rag_stub = _RagStub()
    vq_stub = _VqStub()

    from src.services.control_plane.tools.supply_chain_tools import register_supply_chain_tools
    from src.services.control_plane.tools.o2c_tools import register_o2c_tools
    from src.services.control_plane.tools.erp_writeback_tools import register_erp_writeback_tools
    from src.services.control_plane.tools.customer_360_tools import register_customer_360_tools
    from src.services.control_plane.tools.inventory_tools import register_inventory_tools
    from src.services.control_plane.tools.supply_chain_risk_tools import register_supply_chain_risk_tools
    from src.services.control_plane.tools.production_quality_tools import register_production_quality_tools
    from src.services.control_plane.tools.notify_tools import register_notify_tools

    register_supply_chain_tools(registry, rag_stub)
    register_o2c_tools(registry, vq_stub)
    register_erp_writeback_tools(registry)
    register_customer_360_tools(registry)
    register_inventory_tools(registry)
    register_supply_chain_risk_tools(registry)
    register_production_quality_tools(registry)
    register_notify_tools(registry)

    return registry


def _iter_sentinel_values(node: Any) -> Iterable[str]:
    if isinstance(node, str):
        if SENTINEL_RE.match(node):
            yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _iter_sentinel_values(v)
    elif isinstance(node, (list, tuple)):
        for v in node:
            yield from _iter_sentinel_values(v)


def test_every_required_tool_has_canary_params():
    registry = _build_registry()
    missing: list[str] = []
    for tool in registry.list_tools():
        if tool.name in SKIP_CANARY:
            continue
        params = getattr(tool, "parameters", None) or {}
        required = params.get("required") or []
        if not required:
            continue
        if tool.name not in rtd.CANARY_PARAMS:
            missing.append(tool.name)
    assert missing == [], (
        "Tools require parameters but have no CANARY_PARAMS entry: "
        + ", ".join(sorted(missing))
    )


def test_canary_params_cover_every_required_key():
    registry = _build_registry()
    drift: list[str] = []
    for tool in registry.list_tools():
        canary = rtd.CANARY_PARAMS.get(tool.name)
        if canary is None:
            continue
        params = getattr(tool, "parameters", None) or {}
        required = set(params.get("required") or [])
        missing = sorted(required - set(canary.keys()))
        for k in missing:
            drift.append(f"{tool.name}.{k}")
    assert drift == [], (
        "CANARY_PARAMS missing required keys: " + ", ".join(drift)
    )


def test_every_diagnostic_sentinel_in_canary_params_is_seeded():
    seeded: set[str] = set()
    for rows in DIAGNOSTIC_SENTINELS.values():
        for row in rows:
            for v in row.values():
                if isinstance(v, str) and SENTINEL_RE.match(v):
                    seeded.add(v)

    referenced: set[str] = set()
    for params in rtd.CANARY_PARAMS.values():
        for v in _iter_sentinel_values(params):
            referenced.add(v)

    unseeded = sorted(referenced - seeded - KNOWN_LABEL_SENTINELS)
    assert unseeded == [], (
        "CANARY_PARAMS references diagnostic sentinel IDs that are not "
        "seeded in DIAGNOSTIC_SENTINELS (and not declared as label-only "
        "in KNOWN_LABEL_SENTINELS): " + ", ".join(unseeded)
    )


# ---------------------------------------------------------------------------
# _detect_negative_shape
# ---------------------------------------------------------------------------


def test_detect_negative_shape_top_level_action_failed():
    assert rtd._detect_negative_shape({"action": "failed", "error": "boom"}) == "boom"


def test_detect_negative_shape_top_level_updated_false():
    msg = rtd._detect_negative_shape({"updated": False, "error": "not found"})
    assert "not found" in msg


def test_detect_negative_shape_nested_simulator_update():
    payload = {
        "action": "invoice_status_updated",
        "simulator_update": {"updated": False, "error": "INV-MISSING not found"},
    }
    msg = rtd._detect_negative_shape(payload)
    assert msg is not None
    assert "simulator_update" in msg
    assert "INV-MISSING" in msg


def test_detect_negative_shape_healthy_payload_returns_none():
    assert rtd._detect_negative_shape({"action": "ok", "updated": True}) is None
    assert rtd._detect_negative_shape({"results": [{"x": 1}], "count": 1}) is None
