"""
Procurement ReAct tools (Phase 3).

Two analyzers for maverick spend + renegotiation candidates. Mutator
side is shared with supply_chain_risk (block_supplier_orders) and the
existing erp_writeback_tools (oracle.purchase_order.approve).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from loguru import logger

from ..tool_registry import RiskLevel, Tool, ToolRegistry

proc_logger = logger.bind(component="procurement-tools")


# ---------------------------------------------------------------------------
# Analyzers
# ---------------------------------------------------------------------------


async def _find_maverick_spend(
    period: str = "last_quarter", top_n: int = 25,
) -> Dict[str, Any]:
    samples = [
        {"vendor_id": "VND-2099", "vendor_name": "Quickbuy Office", "off_contract_spend_usd": 84_500, "contract_id": None, "category": "office_supplies"},
        {"vendor_id": "VND-2018", "vendor_name": "Speedy Logistics", "off_contract_spend_usd": 41_200, "contract_id": None, "category": "freight"},
    ]
    return {"period": period, "count": min(top_n, len(samples)),
            "results": samples[:top_n]}


async def _find_renegotiation_candidates(
    threshold_usd: float = 250_000, top_n: int = 25,
) -> Dict[str, Any]:
    samples = [
        {"contract_id": "CNT-3041", "vendor_name": "Acme Plastics", "annual_spend_usd": 1_240_000, "expiry_in_days": 90, "savings_opportunity_pct": 8.5},
        {"contract_id": "CNT-3088", "vendor_name": "Northwind Metals", "annual_spend_usd": 720_000, "expiry_in_days": 145, "savings_opportunity_pct": 6.0},
    ]
    return {"threshold_usd": threshold_usd, "count": min(top_n, len(samples)),
            "results": samples[:top_n]}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_procurement_tools(registry: ToolRegistry) -> None:
    registry.register(Tool(
        name="find_maverick_spend",
        description=(
            "Surface invoice-line spend that bypassed an active contract (maverick "
            "spend). Returns vendors and categories ranked by uncontrolled dollar "
            "exposure for the period."
        ),
        parameters={
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Reporting period (default 'last_quarter')"},
                "top_n": {"type": "integer", "description": "Max rows (default 25)"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _find_maverick_spend(**kw),
        tool_kind="analyze",
        tags=["procurement", "maverick", "analyze"],
    ))

    registry.register(Tool(
        name="find_renegotiation_candidates",
        description=(
            "Identify contracts that are good renegotiation candidates: large annual "
            "spend, short-dated expiry, and an estimated savings opportunity. Used by "
            "the contract-renegotiation-trigger playbook."
        ),
        parameters={
            "type": "object",
            "properties": {
                "threshold_usd": {"type": "number", "description": "Minimum annual spend to consider (default 250k)"},
                "top_n": {"type": "integer", "description": "Max rows (default 25)"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _find_renegotiation_candidates(**kw),
        tool_kind="analyze",
        tags=["procurement", "contract", "analyze"],
    ))

    # Phase 1 -- stamp the supply-chain bucket on every tool registered here.
    for tool_name in ("find_maverick_spend", "find_renegotiation_candidates"):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "supply-chain"

    proc_logger.info("Procurement tools registered: 2 analyzers (bucket=supply-chain)")
