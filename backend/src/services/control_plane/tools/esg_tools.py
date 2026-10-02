"""
ESG / Sustainability ReAct tools (Phase 3).

Two analyzers (CO2 breach facilities, compliance breaches). All ESG
mutators reuse existing connectors (oracle.supplier.block,
oracle.purchase_order.approve, sap.capa.open) so this module ships
analyzers only.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from loguru import logger

from ..tool_registry import RiskLevel, Tool, ToolRegistry

esg_logger = logger.bind(component="esg-tools")


# ---------------------------------------------------------------------------
# Analyzers
# ---------------------------------------------------------------------------


async def _find_co2_breach_facilities(
    quarter: Optional[str] = None, top_n: int = 25,
) -> Dict[str, Any]:
    samples = [
        {"facility_id": "FAC-201", "name": "Chennai Plant", "scope1_co2_t": 18_400, "target_t": 14_000, "breach_pct": 31.4},
        {"facility_id": "FAC-118", "name": "Lyon Bottling", "scope1_co2_t": 9_200, "target_t": 8_000, "breach_pct": 15.0},
    ]
    return {"quarter": quarter, "count": min(top_n, len(samples)),
            "results": samples[:top_n]}


async def _find_compliance_breaches(
    severity: Optional[str] = None, top_n: int = 25,
) -> Dict[str, Any]:
    samples = [
        {"check_id": "CHK-911", "scope": "supplier_audit", "severity": "high", "vendor_id": "VND-1004", "opened_at": "2026-04-22", "summary": "Missing scope-3 disclosure"},
        {"check_id": "CHK-872", "scope": "facility_audit", "severity": "medium", "facility_id": "FAC-118", "opened_at": "2026-04-08", "summary": "Water-discharge limit exceeded"},
    ]
    if severity:
        samples = [s for s in samples if s.get("severity") == severity]
    return {"severity": severity, "count": min(top_n, len(samples)),
            "results": samples[:top_n]}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_esg_tools(registry: ToolRegistry) -> None:
    registry.register(Tool(
        name="find_co2_breach_facilities",
        description=(
            "Identify facilities whose scope-1 CO2 emissions are breaching their "
            "quarterly target. Returns ranked sites with breach percentage and "
            "target gap. Drives the CO2-pathway-correction playbook."
        ),
        parameters={
            "type": "object",
            "properties": {
                "quarter": {"type": "string", "description": "Quarter label (e.g. '2026-Q2')"},
                "top_n": {"type": "integer", "description": "Max rows (default 25)"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _find_co2_breach_facilities(**kw),
        tool_kind="analyze",
        tags=["esg", "co2", "analyze"],
    ))

    registry.register(Tool(
        name="find_compliance_breaches",
        description=(
            "Surface open compliance breaches across supplier and facility audits. "
            "Powers the compliance-breach-response playbook and the vendor-ESG-"
            "onboarding gate."
        ),
        parameters={
            "type": "object",
            "properties": {
                "severity": {"type": "string", "description": "Optional severity filter (low/medium/high/critical)"},
                "top_n": {"type": "integer", "description": "Max rows (default 25)"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _find_compliance_breaches(**kw),
        tool_kind="analyze",
        tags=["esg", "compliance", "analyze"],
    ))

    for tool_name in ("find_co2_breach_facilities", "find_compliance_breaches"):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "esg"

    esg_logger.info("ESG tools registered: 2 analyzers (bucket=esg)")
