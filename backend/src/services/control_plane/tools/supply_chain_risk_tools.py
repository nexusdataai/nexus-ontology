"""
Supply-Chain Risk ReAct tools (Phase 3).

Two analyzers (lane disruption, supplier risk) + one mutator (block
supplier orders -> Oracle ERP connector).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from ..tool_registry import RiskLevel, Tool, ToolRegistry

scr_logger = logger.bind(component="scr-tools")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Analyzers
# ---------------------------------------------------------------------------


async def _find_disrupted_lanes(
    region: Optional[str] = None, top_n: int = 20,
) -> Dict[str, Any]:
    samples = [
        {"lane_id": "LANE-EU-CN-1", "from": "Hamburg", "to": "Shanghai", "disruption_score": 0.86, "cause": "port_congestion"},
        {"lane_id": "LANE-NA-MX-3", "from": "Houston", "to": "Monterrey", "disruption_score": 0.74, "cause": "weather"},
    ]
    return {"region": region, "count": min(top_n, len(samples)), "results": samples[:top_n]}


async def _score_supplier_disruption_risk(
    vendor_id: Optional[str] = None, top_n: int = 20,
) -> Dict[str, Any]:
    samples = [
        {"vendor_id": "VND-1004", "vendor_name": "Acme Plastics", "risk_score": 0.81, "drivers": ["financial_health", "geopolitical"]},
        {"vendor_id": "VND-1187", "vendor_name": "Northwind Metals", "risk_score": 0.69, "drivers": ["delivery_perf"]},
    ]
    if vendor_id:
        for s in samples:
            if s["vendor_id"] == vendor_id:
                return {"vendor_id": vendor_id, "result": s}
        return {"vendor_id": vendor_id, "result": {"risk_score": 0.0, "drivers": []}}
    return {"count": min(top_n, len(samples)), "results": samples[:top_n]}


# ---------------------------------------------------------------------------
# Mutator: block supplier orders -> Oracle connector
# ---------------------------------------------------------------------------


async def _block_supplier_orders(
    supplier_id: str, block: bool = True,
    reason: Optional[str] = None, block_until: Optional[str] = None,
    actor: str = "ai-copilot",
) -> Dict[str, Any]:
    from ..connector_runtime import emit_audit, get_sim, update_one
    sim = await get_sim("oracle")
    new_status = "Blocked" if block else "Active"
    patch = {
        "Status": new_status, "Block_Reason": reason,
        "Block_Until": block_until, "Last_Updated": _now_iso(),
    }
    try:
        previous, _ = await update_one(sim, "oracle_erp", "Oracle_Supplier",
                                        "Supplier_ID", supplier_id, patch)
        await emit_audit(actor, "block_supplier", supplier_id,
                         {"previous_status": previous.get("Status"), **patch},
                         api_id="oracle.supplier.block")
        return {"action": "supplier_blocked" if block else "supplier_unblocked",
                "supplier_id": supplier_id, "status": new_status, "reason": reason}
    except Exception as e:
        scr_logger.warning(f"block_supplier_orders failed: {e}")
        return {"action": "failed", "error": str(e)}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_supply_chain_risk_tools(registry: ToolRegistry) -> None:
    registry.register(Tool(
        name="find_disrupted_lanes",
        description=(
            "Identify shipping lanes currently impacted by external disruptions "
            "(weather, port congestion, geopolitical events). Returns ranked lanes "
            "with disruption score and root cause."
        ),
        parameters={
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "Optional region filter (NA, EU, APAC, ...)"},
                "top_n": {"type": "integer", "description": "Max rows (default 20)"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _find_disrupted_lanes(**kw),
        tool_kind="analyze",
        tags=["scr", "lane", "analyze"],
    ))

    registry.register(Tool(
        name="score_supplier_disruption_risk",
        description=(
            "Score a vendor (or rank all vendors) by composite disruption risk: "
            "delivery performance, financial health, geographic exposure, contract "
            "concentration. Used by tier-2 stress, single-source, and geopolitical "
            "hedge playbooks."
        ),
        parameters={
            "type": "object",
            "properties": {
                "vendor_id": {"type": "string", "description": "Optional single-vendor mode"},
                "top_n": {"type": "integer", "description": "Max rows when ranking (default 20)"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _score_supplier_disruption_risk(**kw),
        tool_kind="analyze",
        tags=["scr", "supplier", "analyze"],
    ))

    registry.register(Tool(
        name="block_supplier_orders",
        description=(
            "Block (or unblock) a supplier from receiving new POs. Used by maverick-"
            "spend capture, vendor risk escalation, and ESG breach response playbooks."
        ),
        parameters={
            "type": "object",
            "properties": {
                "supplier_id": {"type": "string"},
                "block": {"type": "boolean", "description": "True to block, false to unblock"},
                "reason": {"type": "string"},
                "block_until": {"type": "string", "description": "ISO date the block expires"},
            },
            "required": ["supplier_id"],
        },
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _block_supplier_orders(**kw),
        connector_api="oracle.supplier.block",
        requires_approval=True,
        tool_kind="mutate",
        tags=["scr", "supplier", "block"],
    ))

    # Phase 1 -- stamp the supply-chain bucket on every tool registered here.
    for tool_name in (
        "find_disrupted_lanes", "score_supplier_disruption_risk", "block_supplier_orders",
    ):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "supply-chain"

    scr_logger.info("Supply-Chain Risk tools registered: 2 analyzers + 1 mutator (bucket=supply-chain)")
