"""
Inventory ReAct tools (Phase 3).

Analyzers return shape-correct dummy data; mutator (kit creation) routes
through Oracle ERP connector via connector_runtime.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from ..tool_registry import RiskLevel, Tool, ToolRegistry

inv_logger = logger.bind(component="inventory-tools")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Analyzers
# ---------------------------------------------------------------------------


async def _find_excess_inventory_near_expiry(
    horizon_days: int = 60, plant_id: Optional[str] = None, top_n: int = 50,
) -> Dict[str, Any]:
    samples = [
        {"material_id": "MAT-00231", "qty": 4200, "expiry_date": "2026-06-12", "plant": plant_id or "PLT-N1", "writeoff_at_risk_usd": 18900},
        {"material_id": "MAT-00417", "qty": 1800, "expiry_date": "2026-05-29", "plant": plant_id or "PLT-N3", "writeoff_at_risk_usd": 7400},
    ]
    return {"horizon_days": horizon_days, "plant_id": plant_id,
            "count": min(top_n, len(samples)), "results": samples[:top_n]}


async def _find_slow_movers(
    velocity_threshold: float = 0.5, top_n: int = 50, plant_id: Optional[str] = None,
) -> Dict[str, Any]:
    samples = [
        {"material_id": "MAT-00109", "weekly_velocity": 0.21, "on_hand_qty": 980, "plant": plant_id or "PLT-N2"},
        {"material_id": "MAT-00204", "weekly_velocity": 0.34, "on_hand_qty": 740, "plant": plant_id or "PLT-N1"},
    ]
    return {"velocity_threshold": velocity_threshold, "plant_id": plant_id,
            "count": min(top_n, len(samples)), "results": samples[:top_n]}


async def _project_inventory_writeoff(
    horizon_days: int = 90, plant_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "horizon_days": horizon_days, "plant_id": plant_id,
        "projected_writeoff_usd": 142_300,
        "by_category": {
            "near_expiry": 91_400, "slow_movers": 38_600, "obsolete": 12_300,
        },
        "currency": "USD",
    }


# ---------------------------------------------------------------------------
# Mutator: bundle SKUs for liquidation -> Oracle Kit creation
# ---------------------------------------------------------------------------


async def _bundle_skus_for_liquidation(
    name: str, components: List[Dict[str, Any]],
    kit_sku: Optional[str] = None, list_price: Optional[float] = None,
    discount_pct: Optional[float] = None, actor: str = "ai-copilot",
) -> Dict[str, Any]:
    from ..connector_runtime import append_row, emit_audit, get_sim
    sim = await get_sim("oracle")
    kit_id = f"KIT-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:6]}"
    code = kit_sku or kit_id.lower()
    row = {
        "Kit_ID": kit_id, "Kit_SKU": code, "Name": name,
        "Components": components or [], "List_Price": list_price,
        "Discount_Pct": discount_pct, "Status": "Active",
        "Created_At": _now_iso(),
    }
    try:
        await append_row(sim, "oracle_erp", "Oracle_Kit", row)
        await emit_audit(actor, "create_kit", kit_id, row, api_id="oracle.kit.create")
        return {"action": "kit_created", "kit_id": kit_id, "kit_sku": code,
                "components": components, "discount_pct": discount_pct}
    except Exception as e:
        inv_logger.warning(f"bundle_skus_for_liquidation failed: {e}")
        return {"action": "failed", "error": str(e)}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_inventory_tools(registry: ToolRegistry) -> None:
    registry.register(Tool(
        name="find_excess_inventory_near_expiry",
        description=(
            "Identify inventory positions whose batches will expire inside the horizon "
            "window with high write-off risk. Returns ranked SKUs with quantity, "
            "expiry date, plant, and the projected dollar exposure."
        ),
        parameters={
            "type": "object",
            "properties": {
                "horizon_days": {"type": "integer", "description": "Lookahead window in days (default 60)"},
                "plant_id": {"type": "string", "description": "Optional plant filter"},
                "top_n": {"type": "integer", "description": "Max rows to return (default 50)"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _find_excess_inventory_near_expiry(**kw),
        tool_kind="analyze",
        tags=["inventory", "expiry", "analyze"],
    ))

    registry.register(Tool(
        name="find_slow_movers",
        description=(
            "Rank materials by weekly sell-through velocity and surface the slowest "
            "movers. Used by liquidation playbooks and inter-plant rebalance plays."
        ),
        parameters={
            "type": "object",
            "properties": {
                "velocity_threshold": {"type": "number", "description": "Weekly velocity threshold (default 0.5)"},
                "top_n": {"type": "integer", "description": "Max rows (default 50)"},
                "plant_id": {"type": "string", "description": "Optional plant filter"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _find_slow_movers(**kw),
        tool_kind="analyze",
        tags=["inventory", "slow-movers", "analyze"],
    ))

    registry.register(Tool(
        name="project_inventory_writeoff",
        description=(
            "Project the total inventory write-off exposure (in USD) across the horizon "
            "window, decomposed by category (near-expiry / slow-movers / obsolete). "
            "Powers the verify stage of liquidation playbooks."
        ),
        parameters={
            "type": "object",
            "properties": {
                "horizon_days": {"type": "integer", "description": "Lookahead in days (default 90)"},
                "plant_id": {"type": "string", "description": "Optional plant filter"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _project_inventory_writeoff(**kw),
        tool_kind="analyze",
        tags=["inventory", "writeoff", "analyze"],
    ))

    registry.register(Tool(
        name="bundle_skus_for_liquidation",
        description=(
            "Create a sellable kit by bundling multiple SKUs (typically slow-movers + "
            "near-expiry stock) into a single Oracle Kit so it can be discounted as a "
            "single unit."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "components": {"type": "array", "items": {"type": "object", "properties": {
                    "sku": {"type": "string"}, "quantity": {"type": "integer"},
                }}},
                "kit_sku": {"type": "string"},
                "list_price": {"type": "number"},
                "discount_pct": {"type": "number"},
            },
            "required": ["name", "components"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _bundle_skus_for_liquidation(**kw),
        connector_api="oracle.kit.create",
        tool_kind="mutate",
        tags=["inventory", "kit", "liquidation"],
    ))

    # Phase 1 -- stamp the supply-chain bucket on every tool registered here.
    for tool_name in (
        "find_excess_inventory_near_expiry",
        "find_slow_movers",
        "project_inventory_writeoff",
        "bundle_skus_for_liquidation",
    ):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "supply-chain"

    inv_logger.info("Inventory tools registered: 3 analyzers + 1 mutator (bucket=supply-chain)")
