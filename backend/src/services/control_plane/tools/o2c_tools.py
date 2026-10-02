"""
Order-to-Cash ReAct Tools for the AI Control Plane.

Provides O2C-specific operations: three-way match, anomaly scoring,
cash flow projection, and alert generation. All tools query the
Virtual Data Layer via VirtualQueryService.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from ..tool_registry import Tool, RiskLevel

o2c_logger = logger.bind(component="o2c-tools")

QTY_TOLERANCE = 0.02
PRICE_TOLERANCE = 0.05

SLA_DAYS = {"Standard": 5, "Express": 2, "Critical": 1}
TIER_WEIGHT = {"Platinum": 1.5, "Gold": 1.2, "Silver": 1.0, "Bronze": 0.8}


async def _match_order_delivery_invoice(
    vq_service, opportunity_id: str,
) -> Dict[str, Any]:
    from src.models.mapping_rule_models import VirtualQueryRequest, VirtualFilter

    opp_req = VirtualQueryRequest(virtual_entity="Opportunity", filters=[
        VirtualFilter(field="Opportunity_ID", operator="eq", value=opportunity_id)
    ], limit=1)
    try:
        opp_resp = await vq_service.query_virtual_entity(opp_req)
        opp = opp_resp.rows[0] if opp_resp.rows else {}
    except Exception:
        opp = {}

    if not opp:
        return {"match_status": "order_not_found", "opportunity_id": opportunity_id}

    line_req = VirtualQueryRequest(virtual_entity="Opportunity_Line_Item", filters=[
        VirtualFilter(field="Opportunity_ID", operator="eq", value=opportunity_id)
    ], limit=100)
    try:
        line_resp = await vq_service.query_virtual_entity(line_req)
        order_qty = sum(int(r.get("Quantity", r.get("Qty", 0))) for r in line_resp.rows)
        order_amount = sum(float(r.get("Total_Price", r.get("Unit_Price", 0))) for r in line_resp.rows)
    except Exception:
        order_qty = 0
        order_amount = float(opp.get("Total_Value", opp.get("Amount", 0)))

    del_req = VirtualQueryRequest(virtual_entity="Delivery_Document", filters=[
        VirtualFilter(field="Sales_Order_ID", operator="eq", value=opportunity_id)
    ], limit=10)
    try:
        del_resp = await vq_service.query_virtual_entity(del_req)
        deliveries = del_resp.rows
        delivered_qty = sum(int(r.get("Qty", r.get("Quantity", 0))) for r in deliveries)
        delivery_id = deliveries[0].get("Delivery_ID", "") if deliveries else ""
    except Exception:
        deliveries = []
        delivered_qty = 0
        delivery_id = ""

    if not deliveries:
        return {"match_status": "missing_delivery", "opportunity_id": opportunity_id,
                "order_qty": order_qty, "order_amount": order_amount,
                "delivered_qty": 0, "invoiced_amount": 0, "discrepancies": ["No delivery found"]}

    inv_req = VirtualQueryRequest(virtual_entity="AR_Invoice", filters=[
        VirtualFilter(field="Linked_Delivery_ID", operator="eq", value=delivery_id)
    ], limit=10)
    try:
        inv_resp = await vq_service.query_virtual_entity(inv_req)
        invoices = inv_resp.rows
        invoiced_amount = sum(float(r.get("Total_Amount", r.get("Amount", 0))) for r in invoices)
        invoice_id = invoices[0].get("Invoice_ID", "") if invoices else ""
    except Exception:
        invoices = []
        invoiced_amount = 0
        invoice_id = ""

    if not invoices:
        return {"match_status": "missing_invoice", "opportunity_id": opportunity_id,
                "order_qty": order_qty, "order_amount": order_amount,
                "delivered_qty": delivered_qty, "delivery_id": delivery_id,
                "invoiced_amount": 0, "discrepancies": ["No invoice found for delivery"]}

    discrepancies = []
    if order_qty > 0 and abs(delivered_qty - order_qty) / order_qty > QTY_TOLERANCE:
        discrepancies.append(f"Quantity mismatch: ordered {order_qty}, delivered {delivered_qty} (>{QTY_TOLERANCE*100}% tolerance)")
    if order_amount > 0 and abs(invoiced_amount - order_amount) / order_amount > PRICE_TOLERANCE:
        discrepancies.append(f"Amount mismatch: order ${order_amount:.2f}, invoiced ${invoiced_amount:.2f} (>{PRICE_TOLERANCE*100}% tolerance)")

    status = "matched" if not discrepancies else ("quantity_mismatch" if "Quantity" in str(discrepancies) else "price_mismatch")

    return {
        "match_status": status, "opportunity_id": opportunity_id,
        "order_qty": order_qty, "order_amount": order_amount,
        "delivered_qty": delivered_qty, "delivery_id": delivery_id,
        "invoiced_amount": invoiced_amount, "invoice_id": invoice_id,
        "discrepancies": discrepancies, "line_items": len(line_resp.rows) if 'line_resp' in dir() else 0,
    }


async def _score_order_anomaly(
    vq_service, opportunity_id: str, match_result: Optional[Dict] = None,
) -> Dict[str, Any]:
    anomalies = []
    score = 0

    if match_result:
        if match_result.get("match_status") == "missing_delivery":
            anomalies.append({"type": "missing_delivery", "severity": "High", "detail": "No delivery document found"})
            score += 40
        elif match_result.get("match_status") == "missing_invoice":
            anomalies.append({"type": "missing_invoice", "severity": "High", "detail": "No invoice for delivery"})
            score += 30
        elif match_result.get("match_status") in ("quantity_mismatch", "price_mismatch"):
            for d in match_result.get("discrepancies", []):
                anomalies.append({"type": "mismatch", "severity": "Medium", "detail": d})
                score += 20

        order_amount = float(match_result.get("order_amount", 0))
        if order_amount > 500000:
            anomalies.append({"type": "high_value", "severity": "Medium", "detail": f"High-value order: ${order_amount:,.0f}"})
            score += 15
        elif order_amount > 300000:
            score += 8
        invoiced = float(match_result.get("invoiced_amount", 0))
        if invoiced > 0 and order_amount > 0:
            variance = abs(invoiced - order_amount) / order_amount
            if variance > 0.10:
                score += 15
            elif variance > 0.05:
                score += 8

    from src.models.mapping_rule_models import VirtualQueryRequest, VirtualFilter
    try:
        pay_req = VirtualQueryRequest(virtual_entity="AR_Payment", filters=[
            VirtualFilter(field="Invoice_ID", operator="eq", value=match_result.get("invoice_id", ""))
        ], limit=10)
        pay_resp = await vq_service.query_virtual_entity(pay_req)
        payments = pay_resp.rows
    except Exception:
        payments = []

    cycle_times = {}
    if match_result and match_result.get("delivery_id"):
        cycle_times["has_delivery"] = True
        cycle_times["has_invoice"] = bool(match_result.get("invoice_id"))
        cycle_times["has_payment"] = len(payments) > 0

    if not payments and match_result and match_result.get("invoice_id"):
        anomalies.append({"type": "unpaid_invoice", "severity": "Medium", "detail": "Invoice exists but no payment recorded"})
        score += 20

    try:
        cn_req = VirtualQueryRequest(virtual_entity="AR_Credit_Note", filters=[
            VirtualFilter(field="Invoice_ID", operator="eq", value=match_result.get("invoice_id", ""))
        ], limit=5)
        cn_resp = await vq_service.query_virtual_entity(cn_req)
        for cn in cn_resp.rows:
            amount = float(cn.get("Amount", 0))
            if amount > 50000:
                anomalies.append({"type": "large_credit_note", "severity": "Medium",
                                  "detail": f"Credit note ${amount:,.0f} on invoice {match_result.get('invoice_id')}"})
                score += 10
    except Exception:
        pass

    return {
        "opportunity_id": opportunity_id,
        "anomaly_score": min(score, 100),
        "anomalies": anomalies,
        "cycle_times": cycle_times,
        "payment_count": len(payments),
    }


async def _project_cash_flow(vq_service) -> Dict[str, Any]:
    from src.models.mapping_rule_models import VirtualQueryRequest, VirtualFilter

    try:
        inv_req = VirtualQueryRequest(virtual_entity="AR_Invoice", limit=500)
        inv_resp = await vq_service.query_virtual_entity(inv_req)
        all_invoices = inv_resp.rows
    except Exception:
        all_invoices = []

    try:
        pay_req = VirtualQueryRequest(virtual_entity="AR_Payment", limit=500)
        pay_resp = await vq_service.query_virtual_entity(pay_req)
        all_payments = pay_resp.rows
    except Exception:
        all_payments = []

    def _inv_amount(i: dict) -> float:
        return float(i.get("Total_Amount", i.get("Amount", 0)))

    open_invoices = [i for i in all_invoices if i.get("Status") in ("Open", "Overdue")]
    total_open = sum(_inv_amount(i) for i in open_invoices)

    paid_invoices = {p.get("Invoice_ID") for p in all_payments}
    total_paid = sum(float(p.get("Amount", p.get("Total_Amount", 0))) for p in all_payments)

    total_ar = sum(_inv_amount(i) for i in all_invoices)
    dso = (total_open / (total_ar / 365)) if total_ar > 0 else 0

    weekly = []
    chunk = total_open / 8 if total_open > 0 else 0
    for w in range(1, 9):
        prob = max(0.95 - (w * 0.08), 0.3)
        weekly.append({"week": w, "amount": round(chunk * prob, 2), "probability": round(prob, 2)})

    at_risk = sum(_inv_amount(i) for i in open_invoices if i.get("Status") == "Overdue")

    return {
        "total_open_ar": round(total_open, 2),
        "total_invoices": len(all_invoices),
        "open_invoices": len(open_invoices),
        "dso": round(dso, 1),
        "at_risk_amount": round(at_risk, 2),
        "projected_weekly": weekly,
        "total_payments": len(all_payments),
    }


async def _generate_o2c_alerts(
    match_results: List[Dict], anomaly_scores: List[Dict], cash_projection: Dict,
) -> Dict[str, Any]:
    alerts = []

    for mr in match_results:
        if mr.get("discrepancies"):
            order_amt = float(mr.get("order_amount", 0))
            inv_amt = float(mr.get("invoiced_amount", 0))
            if order_amt > 0 and abs(inv_amt - order_amt) / order_amt > PRICE_TOLERANCE:
                alerts.append({
                    "type": "invoice_mismatch", "severity": "High",
                    "entity_id": mr.get("opportunity_id"),
                    "description": f"Invoice ${inv_amt:,.0f} deviates >{PRICE_TOLERANCE*100}% from order ${order_amt:,.0f}",
                    "action": "Hold payment; route to AR for review",
                })

    for a in anomaly_scores:
        for an in a.get("anomalies", []):
            if an.get("type") == "large_credit_note":
                alerts.append({
                    "type": "unusual_credit_note", "severity": "Medium",
                    "entity_id": a.get("opportunity_id"),
                    "description": an.get("detail", ""),
                    "action": "Flag for audit review",
                })

    total_matched = sum(1 for m in match_results if m.get("match_status") == "matched")
    total = len(match_results) or 1
    match_rate = (total_matched / total) * 100

    leakage = sum(
        abs(float(m.get("invoiced_amount", 0)) - float(m.get("order_amount", 0)))
        for m in match_results if m.get("discrepancies")
    )
    total_revenue = sum(float(m.get("order_amount", 0)) for m in match_results) or 1
    leakage_rate = (leakage / total_revenue) * 100

    kpis = {
        "dso": cash_projection.get("dso", 0),
        "match_rate": round(match_rate, 1),
        "leakage_rate": round(leakage_rate, 2),
        "total_open_ar": cash_projection.get("total_open_ar", 0),
        "total_orders_processed": total,
        "total_alerts": len(alerts),
        "at_risk_amount": cash_projection.get("at_risk_amount", 0),
    }

    return {"alerts": alerts, "kpis": kpis}


_TABLE_LOCATION: Dict[str, tuple] = {
    "Account":              ("simulator", "sfdc_itxp2dev"),
    "Opportunity":          ("simulator", "sfdc_itxp2dev"),
    "Case":                 ("simulator", "sfdc_itxp2dev"),
    "Forecast_Override":    ("simulator", "sfdc_itxp2dev"),
    "Oracle_AR_Invoice":    ("oracle", "oracle_erp"),
    "Oracle_AR_Customer":   ("oracle", "oracle_erp"),
    "Oracle_AR_Payment":    ("oracle", "oracle_erp"),
    "Oracle_AR_Credit_Note":("oracle", "oracle_erp"),
    "Oracle_Purchase_Order":("oracle", "oracle_erp"),
    "Delivery_Document":    ("sap", "sap_s4hana"),
    "Batch_Master":         ("sap", "sap_s4hana"),
    "Production_Order":     ("sap", "sap_s4hana"),
    "Material_Plant":       ("sap", "sap_s4hana"),
    "Warehouse_Transfer":   ("sap", "sap_s4hana"),
}


async def _update_simulator_entity(
    table: str,
    key_field: str,
    key_value: str,
    updates: Dict[str, Any],
    *,
    api_id: Optional[str] = None,
    actor: str = "ai-copilot",
    verb: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Write-back to the right simulator for a given entity row.

    Routes through ``connector_runtime`` so the same code path is used as
    a direct connector REST call. Emits an Audit_Event tagged with
    ``api_id`` so the Workbench can verify the write actually happened.
    """
    from src.services.control_plane.connector_runtime import (
        emit_audit, get_sim, update_one,
    )

    location = _TABLE_LOCATION.get(table)
    if not location:
        return {"updated": False, "reason": f"unknown table {table}"}
    sim_key, schema = location

    try:
        sim = await get_sim(sim_key)
        previous, _ = await update_one(sim, schema, table, key_field, str(key_value), updates)
        before = {k: previous.get(k) for k in updates}
        if api_id:
            await emit_audit(
                actor=actor,
                verb=(verb or f"update_{table.lower()}"),
                target=str(key_value),
                payload={"before": before, "after": updates},
                api_id=api_id,
            )
        return {"updated": True, "simulator": sim_key, "schema": schema, "before": before, "after": updates}
    except Exception as e:
        o2c_logger.warning(f"Simulator update failed for {table}.{key_value}: {e}")
        return {"updated": False, "error": str(e), "reason": str(e)}


async def _append_simulator_row(
    sim_key: str,
    schema: str,
    table: str,
    row: Dict[str, Any],
    *,
    api_id: Optional[str] = None,
    actor: str = "ai-copilot",
    verb: Optional[str] = None,
    target_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Append a row through ``connector_runtime`` and emit a tagged audit event."""
    from src.services.control_plane.connector_runtime import (
        append_row, emit_audit, get_sim,
    )
    try:
        sim = await get_sim(sim_key)
        await append_row(sim, schema, table, row)
        if api_id:
            await emit_audit(
                actor=actor,
                verb=(verb or f"create_{table.lower()}"),
                target=str(target_id or row.get("Case_ID") or row.get("Notice_ID") or ""),
                payload=row,
                api_id=api_id,
            )
        return {"appended": True, "simulator": sim_key, "schema": schema, "table": table}
    except Exception as e:
        o2c_logger.warning(f"Simulator append failed for {schema}.{table}: {e}")
        return {"appended": False, "error": str(e), "reason": str(e)}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _place_credit_hold(vq_service, account_id: str, reason: str = "AR threshold exceeded") -> Dict[str, Any]:
    from src.models.mapping_rule_models import VirtualQueryRequest, VirtualFilter
    try:
        resp = await vq_service.query_virtual_entity(VirtualQueryRequest(
            virtual_entity="Account", filters=[VirtualFilter(field="Account_ID", operator="eq", value=account_id)], limit=1))
        account = resp.rows[0] if resp.rows else {}
    except Exception:
        account = {}
    if not account:
        return {"action": "skipped", "reason": f"Account {account_id} not found"}

    credit_limit = float(account.get("Credit_Limit", account.get("credit_limit", 0)) or 0)
    if account.get("Credit_Hold_Status") == "On_Hold":
        return {"action": "skipped", "reason": "Already on credit hold", "account_id": account_id}

    result = await _update_simulator_entity(
        "Account", "Account_ID", account_id,
        {"Credit_Hold_Status": "On_Hold", "Hold_Reason": reason, "Hold_Date": _now_iso()},
        api_id="sfdc.account.credit_hold.set",
        verb="place_credit_hold",
    )
    return {"action": "credit_hold_placed", "account_id": account_id, "credit_limit": credit_limit,
            "reason": reason, "simulator_update": result}


async def _release_credit_hold(vq_service, account_id: str, approved_by: str = "Finance Manager") -> Dict[str, Any]:
    result = await _update_simulator_entity(
        "Account", "Account_ID", account_id,
        {"Credit_Hold_Status": "Active", "Hold_Reason": "", "Release_Approved_By": approved_by, "Release_Date": _now_iso()},
        api_id="sfdc.account.credit_hold.set",
        verb="release_credit_hold",
    )
    return {"action": "credit_hold_released", "account_id": account_id, "approved_by": approved_by, "simulator_update": result}


async def _create_dispute_case(vq_service, opportunity_id: str, invoice_id: str, dispute_reason: str = "Three-way match mismatch",
                               order_amount: float = 0, invoiced_amount: float = 0) -> Dict[str, Any]:
    import uuid
    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    case_row = {
        "Case_ID": case_id, "Opportunity_ID": opportunity_id, "Invoice_ID": invoice_id,
        "Subject": f"Invoice Dispute: {dispute_reason}", "Status": "Open", "Priority": "High",
        "Type": "Invoice_Dispute", "Order_Amount": order_amount, "Invoiced_Amount": invoiced_amount,
        "Created_Date": _now_iso(), "Policy_Reference": "POL-OFC-001 Section 4",
    }
    result = await _append_simulator_row(
        "external", "external_sources", "O2C_Dispute_Case", case_row,
        api_id="sfdc.case.create", verb="create_dispute_case", target_id=case_id,
    )
    return {"action": "dispute_case_created", "case_id": case_id, "opportunity_id": opportunity_id,
            "invoice_id": invoice_id, "reason": dispute_reason, "simulator_update": result}


async def _update_invoice_status(vq_service, invoice_id: str, new_status: str = "Disputed") -> Dict[str, Any]:
    result = await _update_simulator_entity(
        "Oracle_AR_Invoice", "Invoice_ID", invoice_id,
        {"Status": new_status, "Status_Updated": _now_iso()},
        api_id="oracle.invoice.status.set", verb="update_invoice_status",
    )
    return {"action": "invoice_status_updated", "invoice_id": invoice_id, "new_status": new_status, "simulator_update": result}


async def _send_dunning_notice(vq_service, invoice_id: str, customer_id: str, days_overdue: int, tier: str = "reminder") -> Dict[str, Any]:
    import uuid
    notice_id = f"DUN-{uuid.uuid4().hex[:8].upper()}"
    notice = {
        "Notice_ID": notice_id, "Invoice_ID": invoice_id, "Customer_ID": customer_id,
        "Days_Overdue": days_overdue, "Tier": tier, "Sent_Date": _now_iso(),
        "Status": "Sent", "Policy_Reference": "POL-CREDIT-001",
    }
    result = await _append_simulator_row(
        "external", "external_sources", "O2C_Dunning_Notice", notice,
        api_id="external.dunning_notice.create", verb="send_dunning_notice", target_id=notice_id,
    )
    return {"action": "dunning_notice_sent", "notice_id": notice_id, "invoice_id": invoice_id,
            "customer_id": customer_id, "days_overdue": days_overdue, "tier": tier, "simulator_update": result}


async def _escalate_sla_breach(vq_service, opportunity_id: str, sla_pct: float, escalation_level: str = "fulfillment_team") -> Dict[str, Any]:
    import uuid
    esc_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
    escalation = {
        "Escalation_ID": esc_id, "Opportunity_ID": opportunity_id,
        "SLA_Percentage": round(sla_pct, 1), "Level": escalation_level,
        "Created_Date": _now_iso(), "Status": "Open",
        "Policy_Reference": "POL-OFC-001 Section 6",
    }
    result = await _append_simulator_row(
        "external", "external_sources", "O2C_Escalation", escalation,
        api_id="external.alert.create", verb="escalate_sla_breach", target_id=esc_id,
    )
    return {"action": "sla_breach_escalated", "escalation_id": esc_id, "opportunity_id": opportunity_id,
            "sla_pct": round(sla_pct, 1), "level": escalation_level, "simulator_update": result}


async def _request_expedited_fulfillment(vq_service, delivery_id: str, reason: str = "High-risk SLA") -> Dict[str, Any]:
    result = await _update_simulator_entity(
        "Delivery_Document", "Delivery_ID", delivery_id,
        {"Priority": "Express", "Expedite_Reason": reason, "Expedite_Date": _now_iso()},
        api_id="sap.delivery.expedite", verb="request_expedited_fulfillment",
    )
    return {"action": "expedited_fulfillment_requested", "delivery_id": delivery_id, "reason": reason, "simulator_update": result}


async def _process_credit_note(vq_service, invoice_id: str, amount: float, reason: str = "Return processed") -> Dict[str, Any]:
    import uuid
    cn_id = f"CN-{uuid.uuid4().hex[:8].upper()}"
    cn_row = {
        "Credit_Note_ID": cn_id, "Invoice_ID": invoice_id, "Amount": amount,
        "Reason": reason, "Status": "Issued", "Issue_Date": _now_iso(),
        "Policy_Reference": "POL-OFC-001 Section 8",
    }
    append_result = await _append_simulator_row(
        "oracle", "oracle_erp", "Oracle_AR_Credit_Note", cn_row,
        api_id="oracle.credit_note.create", verb="process_credit_note", target_id=cn_id,
    )
    update_result = await _update_simulator_entity(
        "Oracle_AR_Invoice", "Invoice_ID", invoice_id,
        {"Status": "Credit_Applied", "Credit_Note_ID": cn_id},
        api_id="oracle.invoice.status.set", verb="apply_credit_note",
    )
    return {"action": "credit_note_processed", "credit_note_id": cn_id, "invoice_id": invoice_id,
            "amount": amount, "simulator_update": append_result, "invoice_update": update_result}


async def _record_outcome(vq_service, action_id: str, kpi_name: str,
                           kpi_before: float, kpi_after: float, currency: str = "USD") -> Dict[str, Any]:
    """Append an O2C_Outcome_Tracker row capturing the before/after KPI delta."""
    import uuid
    outcome_id = str(uuid.uuid4())
    row = {
        "outcome_id": outcome_id,
        "action_id": action_id,
        "kpi_name": kpi_name,
        "kpi_before": kpi_before,
        "kpi_after": kpi_after,
        "delta_value": round(kpi_after - kpi_before, 4),
        "currency": currency,
        "measured_at": _now_iso(),
    }
    result = await _append_simulator_row(
        "external", "external_sources", "O2C_Outcome_Tracker", row,
        api_id="external.outcome.write", verb="record_outcome", target_id=outcome_id,
    )
    return {"action": "outcome_recorded", "outcome_id": outcome_id, "simulator_update": result, **row}


async def _record_action(vq_service, action_type: str, target_id: str, status: str,
                          target_entity: str = "", notes: str = "") -> Dict[str, Any]:
    import uuid
    action_id = f"ACT-O2C-{int(__import__('time').time())}-{uuid.uuid4().hex[:6]}"
    row = {
        "action_id": action_id,
        "action_type": action_type,
        "target_entity": target_entity or action_type.split(":")[0],
        "target_id": target_id,
        "status": status,
        "notes": notes,
        "taken_by": "ai-copilot",
        "taken_at": _now_iso(),
    }
    result = await _append_simulator_row(
        "external", "external_sources", "O2C_Action_Log", row,
        api_id="external.audit_event.create", verb="record_action", target_id=action_id,
    )
    return {"action": "action_recorded", "simulator_update": result, **row}


async def _update_account_terms(vq_service, customer_id: str, payment_terms: str) -> Dict[str, Any]:
    """Set new payment terms on AR_Customer."""
    result = await _update_simulator_entity(
        "Oracle_AR_Customer", "Customer_ID", customer_id,
        {"Payment_Terms": payment_terms, "Terms_Updated": _now_iso()},
        api_id="oracle.customer.terms.set", verb="update_account_terms",
    )
    return {"action": "account_terms_updated", "customer_id": customer_id,
            "payment_terms": payment_terms, "simulator_update": result}


async def _request_early_pay_discount(vq_service, invoice_id: str,
                                       discount_pct: float, expires_in_days: int = 7) -> Dict[str, Any]:
    """Attach an early-pay discount offer to an open invoice."""
    result = await _update_simulator_entity(
        "Oracle_AR_Invoice", "Invoice_ID", invoice_id,
        {
            "Early_Pay_Discount_Pct": discount_pct,
            "Discount_Expires_At": _now_iso(),
            "Discount_Window_Days": expires_in_days,
        },
        api_id="oracle.invoice.discount.offer", verb="offer_early_pay_discount",
    )
    return {
        "action": "early_pay_discount_offered",
        "invoice_id": invoice_id,
        "discount_pct": discount_pct,
        "expires_in_days": expires_in_days,
        "simulator_update": result,
    }


def register_o2c_tools(registry, virtual_query_service=None):
    if not virtual_query_service:
        o2c_logger.warning("Virtual query service not available — O2C tools not registered")
        return

    registry.register(Tool(
        name="match_order_delivery_invoice",
        description=(
            "Perform three-way match for an order: compare Opportunity qty/amount with "
            "SAP Delivery qty and Oracle AR Invoice amount. Tolerance: qty +-2%, amount +-5%. "
            "Returns match status and any discrepancies."
        ),
        parameters={
            "type": "object",
            "properties": {
                "opportunity_id": {"type": "string", "description": "Salesforce Opportunity ID (e.g. OPP-00123)"},
            },
            "required": ["opportunity_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _match_order_delivery_invoice(virtual_query_service, **kw),
        tags=["o2c", "match"],
    ))

    registry.register(Tool(
        name="score_order_anomaly",
        description=(
            "Score anomalies for an order: cycle time deviations, missing deliveries/invoices, "
            "unpaid invoices, large credit notes. Returns anomaly score 0-100 and list of anomalies."
        ),
        parameters={
            "type": "object",
            "properties": {
                "opportunity_id": {"type": "string", "description": "Opportunity ID"},
                "match_result": {"type": "object", "properties": {}, "description": "Result from match_order_delivery_invoice"},
            },
            "required": ["opportunity_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _score_order_anomaly(virtual_query_service, **kw),
        tags=['o2c', 'anomaly']
    ))

    registry.register(Tool(
        name="project_cash_flow",
        description=(
            "Project cash inflows from open AR invoices. Analyzes payment history to estimate "
            "weekly collection probability. Returns DSO, at-risk amount, and 8-week forecast."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _project_cash_flow(virtual_query_service),
        tags=['o2c', 'ar']
    ))

    registry.register(Tool(
        name="generate_o2c_alerts",
        description=(
            "Evaluate O2C alert rules: invoice mismatch >5%, 3+ overdue >$100K, SLA breach imminent, "
            "unusual credit notes, cash shortfall. Returns triggered alerts and KPIs."
        ),
        parameters={
            "type": "object",
            "properties": {
                "match_results": {"type": "array", "items": {"type": "object"}, "description": "Array of match results from three-way match"},
                "anomaly_scores": {"type": "array", "items": {"type": "object"}, "description": "Array of anomaly scores"},
                "cash_projection": {"type": "object", "properties": {}, "description": "Cash flow projection result"},
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _generate_o2c_alerts(
            kw.get("match_results", []), kw.get("anomaly_scores", []), kw.get("cash_projection", {}),
        ),
        tags=['o2c', 'alerts']
    ))

    registry.register(Tool(
        name="place_credit_hold",
        description="Place credit hold on an account when AR balance exceeds 80% of credit limit. Blocks new shipments per credit-policy Section 5.",
        parameters={"type": "object", "properties": {
            "account_id": {"type": "string", "description": "Account ID to place on hold"},
            "reason": {"type": "string", "description": "Reason for credit hold"},
        }, "required": ["account_id"]},
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _place_credit_hold(virtual_query_service, **kw),
        connector_api="sfdc.account.credit_hold.set",
        requires_approval=True,
        tags=['o2c', 'credit-hold']
    ))

    registry.register(Tool(
        name="release_credit_hold",
        description="Release credit hold on an account after Finance Manager approval.",
        parameters={"type": "object", "properties": {
            "account_id": {"type": "string", "description": "Account ID to release"},
            "approved_by": {"type": "string", "description": "Approver name/role"},
        }, "required": ["account_id"]},
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _release_credit_hold(virtual_query_service, **kw),
        connector_api="sfdc.account.credit_hold.set",
        tags=['o2c', 'credit-hold']
    ))

    registry.register(Tool(
        name="create_dispute_case",
        description="Create a dispute case in Salesforce for invoice mismatch. Routes to AR team for review per order-fulfillment-policy Section 4.",
        parameters={"type": "object", "properties": {
            "opportunity_id": {"type": "string", "description": "Opportunity ID"},
            "invoice_id": {"type": "string", "description": "Invoice ID with mismatch"},
            "dispute_reason": {"type": "string", "description": "Reason for dispute"},
            "order_amount": {"type": "number", "description": "Original order amount"},
            "invoiced_amount": {"type": "number", "description": "Invoiced amount"},
        }, "required": ["opportunity_id", "invoice_id"]},
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _create_dispute_case(virtual_query_service, **kw),
        connector_api="sfdc.case.create",
        tags=['o2c', 'dispute']
    ))

    registry.register(Tool(
        name="update_invoice_status",
        description="Change Oracle AR invoice status (Disputed, On_Hold, Released, Credit_Applied).",
        parameters={"type": "object", "properties": {
            "invoice_id": {"type": "string", "description": "Invoice ID to update"},
            "new_status": {"type": "string", "description": "New status value"},
        }, "required": ["invoice_id", "new_status"]},
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _update_invoice_status(virtual_query_service, **kw),
        connector_api="oracle.invoice.status.set",
        requires_approval=True,
        tags=['o2c', 'ar']
    ))

    registry.register(Tool(
        name="send_dunning_notice",
        description="Send collection reminder for an overdue invoice. Tiers: reminder (7d), warning (14d), escalation (30d), final (60d).",
        parameters={"type": "object", "properties": {
            "invoice_id": {"type": "string", "description": "Overdue invoice ID"},
            "customer_id": {"type": "string", "description": "Customer/Account ID"},
            "days_overdue": {"type": "integer", "description": "Number of days overdue"},
            "tier": {"type": "string", "description": "Dunning tier: reminder, warning, escalation, final"},
        }, "required": ["invoice_id", "customer_id", "days_overdue"]},
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _send_dunning_notice(virtual_query_service, **kw),
        connector_api="external.dunning_notice.create",
        tags=['o2c', 'dunning']
    ))

    registry.register(Tool(
        name="escalate_sla_breach",
        description="Create escalation for SLA breach: 80% = fulfillment team, 100% = Regional SC Manager, 120% = VP Supply Chain.",
        parameters={"type": "object", "properties": {
            "opportunity_id": {"type": "string", "description": "Order/Opportunity ID"},
            "sla_pct": {"type": "number", "description": "SLA elapsed percentage (e.g. 85.0)"},
            "escalation_level": {"type": "string", "description": "Level: fulfillment_team, regional_manager, vp_supply_chain"},
        }, "required": ["opportunity_id", "sla_pct"]},
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _escalate_sla_breach(virtual_query_service, **kw),
        connector_api="external.alert.create",
        tags=['o2c', 'escalation']
    ))

    registry.register(Tool(
        name="request_expedited_fulfillment",
        description="Set SAP delivery to express priority for high-risk or SLA-threatened orders.",
        parameters={"type": "object", "properties": {
            "delivery_id": {"type": "string", "description": "SAP Delivery Document ID"},
            "reason": {"type": "string", "description": "Reason for expediting"},
        }, "required": ["delivery_id"]},
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _request_expedited_fulfillment(virtual_query_service, **kw),
        connector_api="sap.delivery.expedite",
        tags=['o2c', 'delivery']
    ))

    registry.register(Tool(
        name="process_credit_note",
        description="Create credit note in Oracle AR for a return. Updates invoice status to Credit_Applied.",
        parameters={"type": "object", "properties": {
            "invoice_id": {"type": "string", "description": "Invoice to credit"},
            "amount": {"type": "number", "description": "Credit note amount"},
            "reason": {"type": "string", "description": "Reason for credit"},
        }, "required": ["invoice_id", "amount"]},
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _process_credit_note(virtual_query_service, **kw),
        connector_api="oracle.credit_note.create",
        requires_approval=True,
        tags=['o2c', 'credit-note']
    ))

    registry.register(Tool(
        name="record_outcome",
        description=(
            "Append an O2C_Outcome_Tracker row capturing the before/after KPI delta and $ value "
            "attributed to an automation action. Used at the end of an automation playbook."
        ),
        parameters={"type": "object", "properties": {
            "action_id": {"type": "string"},
            "kpi_name": {"type": "string"},
            "kpi_before": {"type": "number"},
            "kpi_after": {"type": "number"},
        }, "required": ["action_id", "kpi_name", "kpi_before", "kpi_after"]},
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _record_outcome(virtual_query_service, **kw),
        connector_api="external.outcome.write",
        tags=["o2c", "outcome"],
    ))

    registry.register(Tool(
        name="record_action",
        description="Append an O2C_Action_Log row recording an automation action that took effect.",
        parameters={"type": "object", "properties": {
            "action_type": {"type": "string"},
            "target_entity": {"type": "string"},
            "target_id": {"type": "string"},
            "status": {"type": "string"},
            "notes": {"type": "string"},
        }, "required": ["action_type", "target_id", "status"]},
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _record_action(virtual_query_service, **kw),
        connector_api="external.audit_event.create",
        tags=["o2c", "action-log"],
    ))

    registry.register(Tool(
        name="update_account_terms",
        description="Update an AR customer's payment terms (e.g. Net_60 -> Net_30 for high-risk accounts).",
        parameters={"type": "object", "properties": {
            "customer_id": {"type": "string"},
            "payment_terms": {"type": "string", "description": "e.g. Net_30, Net_60, Net_90, COD"},
        }, "required": ["customer_id", "payment_terms"]},
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _update_account_terms(virtual_query_service, **kw),
        connector_api="oracle.customer.terms.set",
        requires_approval=True,
        tags=["o2c", "terms"],
    ))

    registry.register(Tool(
        name="request_early_pay_discount",
        description="Attach an early-pay discount offer to an open invoice.",
        parameters={"type": "object", "properties": {
            "invoice_id": {"type": "string"},
            "discount_pct": {"type": "number"},
            "expires_in_days": {"type": "integer"},
        }, "required": ["invoice_id", "discount_pct"]},
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _request_early_pay_discount(virtual_query_service, **kw),
        connector_api="oracle.invoice.discount.offer",
        requires_approval=True,
        tags=["o2c", "ar", "discount"],
    ))

    # Phase 1 -- stamp the bucket on every tool this bundle registers.
    # The default ``output_relationships=[Relationship("success")]`` on
    # the Tool dataclass keeps all 16 valid; future mutator fan-out
    # (success / failure) can be added per-tool incrementally without
    # touching this sweep.
    for tool_name in (
        "match_order_delivery_invoice", "score_order_anomaly", "project_cash_flow",
        "generate_o2c_alerts", "place_credit_hold", "release_credit_hold",
        "create_dispute_case", "update_invoice_status", "send_dunning_notice",
        "escalate_sla_breach", "request_expedited_fulfillment", "process_credit_note",
        "record_outcome", "record_action", "update_account_terms",
        "request_early_pay_discount",
    ):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "o2c"

    o2c_logger.info("O2C tools registered: 4 read + 12 write tools (bucket=o2c)")
