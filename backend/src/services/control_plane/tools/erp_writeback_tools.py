"""
ERP Write-back ReAct Tools.

A small block of write tools that exists for one reason: to give every
ConnectorAPISpec a registered ToolRegistry caller, so the ReAct Tools
diagnostic stops reporting orphans.

Each tool routes through ``connector_runtime`` (the same path the
per-system simulator routers use) and emits an Audit_Event tagged with
its ``connector_api`` so the Workbench verification can prove the write.

Six tools, one per remaining orphan:

  approve_purchase_order     -> oracle.purchase_order.approve
  record_payment             -> oracle.payment.record
  update_safety_stock        -> sap.material_plant.reorder
  update_production_order    -> sap.production_order.update
  update_account_health      -> sfdc.account.churn_risk.set
  update_opportunity_stage   -> sfdc.opportunity.update
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger

from ..connector_runtime import append_row, emit_audit, get_sim, update_one
from ..tool_registry import RiskLevel, Tool

erp_logger = logger.bind(component="erp-writeback-tools")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Oracle
# ---------------------------------------------------------------------------

async def _approve_purchase_order(po_id: str, status: str = "Approved",
                                  actor: str = "ai-copilot") -> Dict[str, Any]:
    sim = await get_sim("oracle")
    try:
        previous, _ = await update_one(
            sim, "oracle_erp", "Oracle_Purchase_Order", "PO_ID", po_id,
            {"Status": status, "Status_Updated": _now_iso()},
        )
    except Exception as e:
        return {"error": str(e), "po_id": po_id}
    await emit_audit(
        actor=actor, verb="approve_purchase_order", target=po_id,
        payload={"previous_status": previous.get("Status"), "status": status},
        api_id="oracle.purchase_order.approve",
    )
    return {"action": "purchase_order_approved", "po_id": po_id,
            "previous_status": previous.get("Status"), "status": status}


async def _record_payment(invoice_id: str, customer_id: str, amount: float,
                          payment_method: str = "Wire",
                          actor: str = "ai-copilot") -> Dict[str, Any]:
    sim = await get_sim("oracle")
    payment_id = f"PAY-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:6]}"
    row = {
        "Payment_ID": payment_id,
        "Invoice_ID": invoice_id,
        "Customer_ID": customer_id,
        "Amount": amount,
        "Payment_Date": _now_iso(),
        "Payment_Method": payment_method,
        "Applied_Flag": True,
    }
    try:
        await append_row(sim, "oracle_erp", "Oracle_AR_Payment", row)
    except Exception as e:
        return {"error": str(e), "invoice_id": invoice_id}
    await emit_audit(
        actor=actor, verb="record_payment", target=payment_id, payload=row,
        api_id="oracle.payment.record",
    )
    return {"action": "payment_recorded", "payment_id": payment_id,
            "invoice_id": invoice_id, "amount": amount}


# ---------------------------------------------------------------------------
# SAP
# ---------------------------------------------------------------------------

async def _update_safety_stock(material_id: str, plant_id: str,
                               safety_stock: Optional[int] = None,
                               reorder_point: Optional[int] = None,
                               actor: str = "ai-copilot") -> Dict[str, Any]:
    sim = await get_sim("sap")
    rows = list(await sim._get_table_data("sap_s4hana", "Material_Plant") or [])
    target_idx = next(
        (i for i, r in enumerate(rows)
         if str(r.get("Material_ID")) == material_id and str(r.get("Plant_ID")) == plant_id),
        -1,
    )
    if target_idx < 0:
        return {"error": f"Material_Plant not found: {material_id}/{plant_id}"}
    patch: Dict[str, Any] = {"Last_Updated": _now_iso()}
    if safety_stock is not None: patch["Safety_Stock"] = safety_stock
    if reorder_point is not None: patch["Reorder_Point"] = reorder_point
    rows[target_idx] = {**rows[target_idx], **patch}
    await sim.write_table("sap_s4hana", "Material_Plant", rows)
    await emit_audit(
        actor=actor, verb="update_material_plant",
        target=f"{material_id}/{plant_id}", payload=patch,
        api_id="sap.material_plant.reorder",
    )
    return {"action": "safety_stock_updated", "material_id": material_id,
            "plant_id": plant_id, **patch}


async def _update_production_order(production_order_id: str,
                                   status: Optional[str] = None,
                                   quantity: Optional[int] = None,
                                   shift_id: Optional[str] = None,
                                   actor: str = "ai-copilot") -> Dict[str, Any]:
    sim = await get_sim("sap")
    patch: Dict[str, Any] = {"Last_Updated": _now_iso()}
    if status is not None: patch["Status"] = status
    if quantity is not None: patch["Qty_Planned"] = quantity
    if shift_id is not None: patch["Shift"] = shift_id
    try:
        _, _ = await update_one(
            sim, "sap_s4hana", "Production_Order", "Order_ID",
            production_order_id, patch,
        )
    except Exception as e:
        return {"error": str(e), "production_order_id": production_order_id}
    await emit_audit(
        actor=actor, verb="update_production_order",
        target=production_order_id, payload=patch,
        api_id="sap.production_order.update",
    )
    return {"action": "production_order_updated",
            "production_order_id": production_order_id, **patch}


# ---------------------------------------------------------------------------
# SFDC
# ---------------------------------------------------------------------------

async def _update_account_health(account_id: str,
                                 health_bucket: Optional[str] = None,
                                 churn_date: Optional[str] = None,
                                 churn_reason: Optional[str] = None,
                                 actor: str = "ai-copilot") -> Dict[str, Any]:
    sim = await get_sim("simulator")
    patch: Dict[str, Any] = {"Last_Updated": _now_iso()}
    if health_bucket is not None: patch["Health_Bucket"] = health_bucket
    if churn_date is not None: patch["Churn_Date"] = churn_date
    if churn_reason is not None: patch["Churn_Reason"] = churn_reason
    try:
        _, _ = await update_one(
            sim, "sfdc_itxp2dev", "Account", "Account_ID", account_id, patch,
        )
    except Exception as e:
        return {"error": str(e), "account_id": account_id}
    await emit_audit(
        actor=actor, verb="update_account_health", target=account_id,
        payload=patch, api_id="sfdc.account.churn_risk.set",
    )
    return {"action": "account_health_updated", "account_id": account_id, **patch}


async def _update_opportunity_stage(opportunity_id: str,
                                    stage: Optional[str] = None,
                                    amount: Optional[float] = None,
                                    close_date: Optional[str] = None,
                                    actor: str = "ai-copilot") -> Dict[str, Any]:
    sim = await get_sim("simulator")
    patch: Dict[str, Any] = {"Last_Updated": _now_iso()}
    if stage is not None: patch["Stage"] = stage
    if amount is not None: patch["Amount"] = amount
    if close_date is not None: patch["Close_Date"] = close_date
    try:
        _, _ = await update_one(
            sim, "sfdc_itxp2dev", "Opportunity", "Opportunity_ID",
            opportunity_id, patch,
        )
    except Exception as e:
        return {"error": str(e), "opportunity_id": opportunity_id}
    await emit_audit(
        actor=actor, verb="update_opportunity", target=opportunity_id,
        payload=patch, api_id="sfdc.opportunity.update",
    )
    return {"action": "opportunity_updated",
            "opportunity_id": opportunity_id, **patch}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_erp_writeback_tools(registry) -> None:
    registry.register(Tool(
        name="approve_purchase_order",
        description="Approve / cancel an Oracle Purchase Order.",
        parameters={"type": "object", "properties": {
            "po_id":  {"type": "string", "description": "Purchase Order ID"},
            "status": {"type": "string", "description": "New status (e.g. Approved, Cancelled)"},
        }, "required": ["po_id", "status"]},
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _approve_purchase_order(**kw),
        connector_api="oracle.purchase_order.approve",
        requires_approval=True,
        tags=["procurement", "po"],
    ))

    registry.register(Tool(
        name="record_payment",
        description="Record a customer payment against an open invoice.",
        parameters={"type": "object", "properties": {
            "invoice_id":     {"type": "string"},
            "customer_id":    {"type": "string"},
            "amount":         {"type": "number"},
            "payment_method": {"type": "string", "description": "e.g. Wire, ACH, Check"},
        }, "required": ["invoice_id", "customer_id", "amount"]},
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _record_payment(**kw),
        connector_api="oracle.payment.record",
        tags=["o2c", "ar", "payment"],
    ))

    registry.register(Tool(
        name="update_safety_stock",
        description="Update safety stock / reorder point for a material+plant.",
        parameters={"type": "object", "properties": {
            "material_id":   {"type": "string"},
            "plant_id":      {"type": "string"},
            "safety_stock":  {"type": "integer"},
            "reorder_point": {"type": "integer"},
        }, "required": ["material_id", "plant_id"]},
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _update_safety_stock(**kw),
        connector_api="sap.material_plant.reorder",
        tags=["inventory", "sap"],
    ))

    registry.register(Tool(
        name="update_production_order",
        description="Update a production order's status, quantity, or shift assignment.",
        parameters={"type": "object", "properties": {
            "production_order_id": {"type": "string"},
            "status":              {"type": "string"},
            "quantity":            {"type": "integer"},
            "shift_id":            {"type": "string"},
        }, "required": ["production_order_id"]},
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _update_production_order(**kw),
        connector_api="sap.production_order.update",
        requires_approval=True,
        tags=["pq", "production"],
    ))

    registry.register(Tool(
        name="update_account_health",
        description="Update an account's health bucket / churn flag in Salesforce.",
        parameters={"type": "object", "properties": {
            "account_id":    {"type": "string"},
            "health_bucket": {"type": "string", "description": "e.g. Green, Yellow, Red"},
            "churn_date":    {"type": "string"},
            "churn_reason":  {"type": "string"},
        }, "required": ["account_id"]},
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _update_account_health(**kw),
        connector_api="sfdc.account.churn_risk.set",
        tags=["c360", "churn"],
    ))

    registry.register(Tool(
        name="update_opportunity_stage",
        description="Update opportunity stage / amount / close date.",
        parameters={"type": "object", "properties": {
            "opportunity_id": {"type": "string"},
            "stage":          {"type": "string"},
            "amount":         {"type": "number"},
            "close_date":     {"type": "string"},
        }, "required": ["opportunity_id"]},
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _update_opportunity_stage(**kw),
        connector_api="sfdc.opportunity.update",
        requires_approval=True,
        tags=["c360", "sales"],
    ))

    # Phase 1 -- ERP write-back tools live in the o2c bucket alongside the
    # primary O2C surface, since they all close the loop of an o2c playbook.
    for tool_name in (
        "approve_purchase_order", "record_payment", "update_safety_stock",
        "update_production_order", "update_account_health", "update_opportunity_stage",
    ):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "o2c"

    erp_logger.info("Registered 6 ERP write-back tools (bucket=o2c)")
