"""
Customer-360 ReAct tools.

Phase 3: analyzers (read/analyze) return shape-correct dummy data so
playbooks like ``c360.retain_risky_customers`` validate end-to-end while
real model wiring is staged behind subsequent PRs. Mutator tools route
through ``connector_runtime`` so writes land in the simulator and are
reflected in the audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from ..tool_registry import Relationship, RelationshipResult, RiskLevel, Tool, ToolRegistry

c360_logger = logger.bind(component="c360-tools")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Analyzers (stubs return shape-correct dummy data; runtime to be filled in
# by a follow-up PR per plan section 31.1 budget).
# ---------------------------------------------------------------------------


async def _find_churning_customers(
    horizon_days: int = 90, top_n: int = 20, segment_filter: Optional[str] = None,
    log: Any = None,
) -> Dict[str, Any]:
    if log:
        log.info(
            f"scanning customer base for churn risk (horizon={horizon_days}d, top_n={top_n})",
            horizon_days=horizon_days, top_n=top_n, segment_filter=segment_filter,
        )
    samples = [
        {"customer_id": "ACC-1001", "churn_score": 0.91, "top_features": ["payment_lateness", "support_volume"], "last_touch": "2026-04-29"},
        {"customer_id": "ACC-1042", "churn_score": 0.87, "top_features": ["nps_drop", "usage_decline"], "last_touch": "2026-05-02"},
        {"customer_id": "ACC-1098", "churn_score": 0.82, "top_features": ["renewal_in_30d", "ticket_escalations"], "last_touch": "2026-04-19"},
    ]
    out_count = min(top_n, len(samples))
    if log:
        log.info(f"ranked {out_count} customers by churn score", count=out_count)
    return {
        "horizon_days": horizon_days,
        "segment_filter": segment_filter,
        "count": out_count,
        "results": samples[:top_n],
    }


async def _find_upsell_candidates(
    top_n: int = 20, segment_filter: Optional[str] = None,
    log: Any = None,
) -> Dict[str, Any]:
    if log:
        log.info(
            f"scanning customer base for upsell candidates (top_n={top_n})",
            top_n=top_n, segment_filter=segment_filter,
        )
    samples = [
        {"customer_id": "ACC-2114", "upsell_score": 0.88, "recommended_sku": "SKU-PRO-PLUS", "expected_uplift_usd": 18000},
        {"customer_id": "ACC-2031", "upsell_score": 0.81, "recommended_sku": "SKU-SUPPORT-GOLD", "expected_uplift_usd": 9600},
    ]
    out_count = min(top_n, len(samples))
    if log:
        log.info(f"ranked {out_count} upsell candidates", count=out_count)
    return {
        "segment_filter": segment_filter,
        "count": out_count,
        "results": samples[:top_n],
    }


async def _score_customer_lifetime_value(
    customer_id: Optional[str] = None, top_n: int = 20,
    log: Any = None,
) -> Dict[str, Any]:
    if log:
        log.info(
            "scoring customer lifetime value",
            customer_id=customer_id, top_n=top_n,
        )
    samples = [
        {"customer_id": "ACC-1001", "clv_usd": 184500, "recurring_arr": 96000, "tier": "Platinum"},
        {"customer_id": "ACC-1042", "clv_usd": 78400, "recurring_arr": 38000, "tier": "Gold"},
    ]
    if customer_id:
        for s in samples:
            if s["customer_id"] == customer_id:
                if log:
                    log.info(
                        f"found customer {customer_id}: tier={s['tier']} CLV=${s['clv_usd']}",
                        customer_id=customer_id, tier=s["tier"], clv_usd=s["clv_usd"],
                    )
                return {"customer_id": customer_id, "result": s}
        if log:
            log.warning(f"customer {customer_id} not found in CLV sample data")
        return {"customer_id": customer_id, "result": {"clv_usd": 0, "recurring_arr": 0, "tier": "Unknown"}}
    if log:
        log.info(f"ranked top {min(top_n, len(samples))} customers by CLV")
    return {"count": min(top_n, len(samples)), "results": samples[:top_n]}


# ---------------------------------------------------------------------------
# Mutators (real connector calls via connector_runtime).
# ---------------------------------------------------------------------------


async def _apply_promo_discount(
    name: str, discount_pct: float,
    promo_code: Optional[str] = None,
    applies_to: Optional[Dict[str, Any]] = None,
    customer_id: Optional[str] = None,
    valid_from: Optional[str] = None, valid_to: Optional[str] = None,
    max_redemptions: Optional[int] = None,
    actor: str = "ai-copilot",
    log: Any = None,
) -> Dict[str, Any]:
    from ..connector_runtime import append_row, emit_audit, get_sim
    if log:
        log.info(
            f"creating promotion '{name}' ({discount_pct}% off)"
            + (f" for {customer_id}" if customer_id else ""),
            name=name, discount_pct=discount_pct, customer_id=customer_id,
        )
    sim = await get_sim("oracle")
    promo_id = f"PROMO-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:6]}"
    code = promo_code or promo_id.lower()
    row = {
        "Promo_ID": promo_id, "Promo_Code": code, "Name": name,
        "Discount_Pct": discount_pct,
        "Applies_To": applies_to or ({"customer_id": customer_id} if customer_id else {}),
        "Customer_ID": customer_id,
        "Valid_From": valid_from or _now_iso(), "Valid_To": valid_to,
        "Max_Redemptions": max_redemptions, "Status": "Active",
        "Created_At": _now_iso(),
    }
    try:
        await append_row(sim, "oracle_erp", "Oracle_AR_Promotion", row)
        await emit_audit(actor, "create_promotion", promo_id, row,
                         api_id="oracle.promotion.create")
        if log:
            log.info(
                f"promotion {promo_id} created and audited",
                promo_id=promo_id, promo_code=code,
            )
        return RelationshipResult(
            relationship="promo_created",
            data={
                "action": "promo_created", "promo_id": promo_id, "promo_code": code,
                "discount_pct": discount_pct, "name": name, "customer_id": customer_id,
            },
        )
    except Exception as e:
        c360_logger.warning(f"apply_promo_discount failed: {e}")
        if log:
            log.error(f"apply_promo_discount failed: {e}", error=str(e))
        return RelationshipResult(
            relationship="failure",
            data={"action": "failed", "error": str(e)},
        )


async def _assign_csm_outreach(
    account_id: str, subject: str,
    description: Optional[str] = None,
    priority: str = "Medium",
    due_date: Optional[str] = None,
    owner_user_id: Optional[str] = None,
    outreach_type: str = "csm_outreach",
    actor: str = "ai-copilot",
) -> Dict[str, Any]:
    from ..connector_runtime import append_row, emit_audit, get_sim
    try:
        sim = await get_sim("simulator")
    except Exception:
        sim = None
    task_id = f"TASK-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:6]}"
    row = {
        "Task_ID": task_id, "Account_ID": account_id, "Subject": subject,
        "Description": description, "Priority": priority,
        "Due_Date": due_date, "Owner_User_ID": owner_user_id,
        "Outreach_Type": outreach_type, "Status": "Open",
        "Created_Date": _now_iso(),
    }
    try:
        if sim is not None:
            await append_row(sim, "sfdc_itxp2dev", "Task", row)
        await emit_audit(actor, "create_csm_outreach_task", task_id, row,
                         api_id="sfdc.task.create_csm_outreach")
        return RelationshipResult(
            relationship="task_created",
            data={
                "action": "csm_task_created", "task_id": task_id,
                "account_id": account_id, "subject": subject,
            },
        )
    except Exception as e:
        c360_logger.warning(f"assign_csm_outreach failed: {e}")
        return RelationshipResult(
            relationship="failure",
            data={"action": "failed", "error": str(e)},
        )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


_C360_BUCKET = "customer-360"


def register_customer_360_tools(registry: ToolRegistry) -> None:
    registry.register(Tool(
        name="find_churning_customers",
        description=(
            "Identify customers most likely to churn within the lookback horizon. "
            "Combines payment-lateness, NPS / health-score deltas, support-ticket trend "
            "and usage decline into a single churn risk score. Returns ranked customers "
            "with feature attributions (Cursor-for-data: ripgrep over Customer history)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "horizon_days": {"type": "integer", "description": "Lookback horizon for behaviour signals (default 90)"},
                "top_n": {"type": "integer", "description": "Max ranked rows to return (default 20)"},
                "segment_filter": {"type": "string", "description": "Optional segment / tier filter"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda log=None, **kw: _find_churning_customers(log=log, **kw),
        tool_kind="analyze",
        tags=["c360", "churn", "analyze"],
        bucket=_C360_BUCKET,
        output_relationships=[
            Relationship(name="success", description="Ranked churn-risk customers and feature attributions"),
        ],
    ))

    registry.register(Tool(
        name="find_upsell_candidates",
        description=(
            "Surface accounts whose product mix + usage trajectory suggests they will "
            "respond to a recommended upsell. Returns ranked customers with the "
            "suggested SKU and expected uplift."
        ),
        parameters={
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "description": "Max rows to return (default 20)"},
                "segment_filter": {"type": "string", "description": "Optional tier / region filter"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda log=None, **kw: _find_upsell_candidates(log=log, **kw),
        tool_kind="analyze",
        tags=["c360", "upsell", "analyze"],
        bucket=_C360_BUCKET,
        output_relationships=[
            Relationship(name="success", description="Ranked upsell candidates with recommended SKU"),
        ],
    ))

    registry.register(Tool(
        name="score_customer_lifetime_value",
        description=(
            "Compute customer lifetime value across recurring revenue, expansion, and "
            "expected retention. Either scores a single customer (when customer_id is "
            "supplied) or returns the top-N by CLV."
        ),
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Optional single-customer mode"},
                "top_n": {"type": "integer", "description": "Max rows when scanning all customers"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda log=None, **kw: _score_customer_lifetime_value(log=log, **kw),
        tool_kind="analyze",
        tags=["c360", "clv", "analyze"],
        bucket=_C360_BUCKET,
        output_relationships=[
            Relationship(name="success", description="CLV score(s) for a single customer or top-N ranked"),
        ],
    ))

    registry.register(Tool(
        name="apply_promo_discount",
        description=(
            "Create a promotion / discount offer in Oracle AR. Used by retain-risky / "
            "liquidation playbooks to attach a personalised offer to an at-risk segment."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "discount_pct": {"type": "number"},
                "promo_code": {"type": "string"},
                "applies_to": {"type": "object", "description": "Targeting filter, e.g. {segment:'at_risk'}"},
                "customer_id": {"type": "string", "description": "Optional single-customer target (overrides applies_to when set); typically wired from find_churning_customers.results.0.customer_id"},
                "valid_from": {"type": "string"},
                "valid_to": {"type": "string"},
                "max_redemptions": {"type": "integer"},
            },
            "required": ["name", "discount_pct"],
        },
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda log=None, **kw: _apply_promo_discount(log=log, **kw),
        connector_api="oracle.promotion.create",
        requires_approval=True,
        tool_kind="mutate",
        tags=["c360", "promotion", "discount"],
        bucket=_C360_BUCKET,
        output_relationships=[
            Relationship(name="promo_created", description="Oracle AR promotion row created"),
            Relationship(name="failure", description="Connector or simulator write failed", auto_terminate_default=True),
        ],
    ))

    registry.register(Tool(
        name="assign_csm_outreach",
        description=(
            "Create a CSM outreach Task on a Salesforce account / opportunity. The "
            "Task carries the outreach type so the CSM team knows whether to call, "
            "email, or open a ticket."
        ),
        parameters={
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "subject": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string"},
                "due_date": {"type": "string"},
                "owner_user_id": {"type": "string"},
                "outreach_type": {"type": "string"},
            },
            "required": ["account_id", "subject"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _assign_csm_outreach(**kw),
        connector_api="sfdc.task.create_csm_outreach",
        tool_kind="mutate",
        tags=["c360", "csm", "task"],
        bucket=_C360_BUCKET,
        output_relationships=[
            Relationship(name="task_created", description="SFDC outreach Task row created"),
            Relationship(name="failure", description="Connector or simulator write failed", auto_terminate_default=True),
        ],
    ))

    c360_logger.info("Customer-360 tools registered: 3 analyzers + 2 mutators (bucket=%s)", _C360_BUCKET)
