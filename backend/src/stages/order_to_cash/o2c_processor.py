"""
Order-to-Cash Processor

Implements the 6-step O2C pipeline logic. Each step method queries the
Virtual Data Layer via VirtualQueryService, processes data using the O2C
ReAct tool logic, and stores results for the final S3/Glue write.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

o2c_logger = logger.bind(component="o2c-processor")

try:
    from ...utils.sse_manager import emit_task_progress, emit_log
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    def emit_task_progress(*a, **kw): pass
    def emit_log(*a, **kw): pass

TIER_WEIGHT = {"Platinum": 1.5, "Gold": 1.2, "Silver": 1.0, "Bronze": 0.8}


class O2CProcessor:

    def __init__(self, log_callback: Optional[Callable] = None, job_id: str = "",
                 journey_id: str = "", s3_client=None, config=None):
        self._log_cb = log_callback
        self.job_id = job_id
        self.journey_id = journey_id
        self._s3 = s3_client
        self._config = config

        self._resolved_orders: List[Dict] = []
        self._match_results: List[Dict] = []
        self._anomaly_scores: List[Dict] = []
        self._risk_ranked: List[Dict] = []
        self._cash_projection: Dict = {}
        self._alerts: Dict = {}
        # Domain KPI dict surfaced to BaseStage.effective_kpis -> Data.kpis
        # so the journey-report builder can roll it up. Populated in
        # step_store_results from the alerts_result["kpis"] dict that
        # ``_generate_o2c_alerts`` returns.
        self._kpis: Dict[str, Any] = {}

    def _log(self, level: str, msg: str, step_id: str = None):
        if self._log_cb:
            self._log_cb(level, msg, step_id)
        else:
            o2c_logger.log(level.upper(), msg)
        if SSE_AVAILABLE and self.job_id and step_id:
            emit_log(self.job_id, step_id, level.upper(), msg)

    def _get_vq_service(self):
        from src.apis.control_plane_api import _virtual_query_service
        return _virtual_query_service

    async def _query_entity(self, entity: str, filters=None, limit=500) -> List[Dict]:
        vq = self._get_vq_service()
        if not vq:
            self._log("WARNING", f"VirtualQueryService not available for {entity}")
            return []
        from src.models.mapping_rule_models import VirtualQueryRequest, VirtualFilter
        vf = [VirtualFilter(field=f["field"], operator=f["operator"], value=f["value"]) for f in (filters or [])]
        req = VirtualQueryRequest(virtual_entity=entity, filters=vf if vf else None, limit=limit)
        try:
            resp = await vq.query_virtual_entity(req)
            return resp.rows
        except Exception as e:
            self._log("WARNING", f"VDL query {entity} failed: {e}, trying direct simulator...", entity)
            return await self._query_simulator_direct(entity, filters, limit)

    async def _query_simulator_direct(self, entity: str, filters=None, limit=500) -> List[Dict]:
        try:
            from src.apis.fdw_api import _simulators
            from src.models.fdw_models import QueryRequest, QueryFilter, FilterOperator

            schema_map = {
                "Account": ("sfdc_itxp2dev", "simulator", None),
                "Opportunity": ("sfdc_itxp2dev", "simulator", None),
                "Contact": ("sfdc_itxp2dev", "simulator", None),
                "Campaign": ("sfdc_itxp2dev", "simulator", None),
                "Opportunity_Line_Item": ("sfdc_itxp2dev", "simulator", None),
                "Delivery_Document": ("sap_s4hana", "sap", None),
                "Shipment": ("sap_s4hana", "sap", None),
                "AR_Invoice": ("oracle_erp", "oracle", "Oracle_AR_Invoice"),
                "AR_Payment": ("oracle_erp", "oracle", "Oracle_AR_Payment"),
                "AR_Customer": ("oracle_erp", "oracle", "Oracle_AR_Customer"),
                "AR_Credit_Note": ("oracle_erp", "oracle", "Oracle_AR_Credit_Note"),
            }

            entry = schema_map.get(entity)
            if not entry:
                return []

            schema, sim_key, physical_table = entry
            sim = _simulators.get(sim_key)
            if not sim or not getattr(sim, "loaded", False):
                self._log("WARNING", f"Simulator '{sim_key}' not loaded for {entity}")
                return []

            query_filters = None
            if filters:
                query_filters = [
                    QueryFilter(column=f["field"], operator=FilterOperator(f["operator"]), value=f["value"])
                    for f in filters
                ]

            req = QueryRequest(table=physical_table or entity, schema_name=schema, filters=query_filters, limit=limit)
            resp = await sim.execute_query(req)
            self._log("INFO", f"Direct simulator query {entity}: {len(resp.rows)} rows", "entity_resolution")
            return resp.rows
        except Exception as e:
            self._log("WARNING", f"Direct simulator query {entity} failed: {e}")
            return []

    @staticmethod
    def _safe_float(val, default=0.0) -> float:
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _get_field(row: Dict, *names, default=None):
        for n in names:
            v = row.get(n)
            if v is not None:
                return v
        return default

    async def step_entity_resolution(self) -> Dict[str, Any]:
        self._log("INFO", "Resolving orders across Salesforce, SAP, Oracle...", "entity_resolution")

        opps = await self._query_entity("Opportunity")
        if opps:
            sample = opps[0]
            self._log("INFO", f"Opportunity sample keys: {sorted(sample.keys())}", "entity_resolution")
            self._log("INFO", f"Opportunity sample values: {{{', '.join(f'{k}={repr(v)[:40]}' for k, v in list(sample.items())[:8])}}}", "entity_resolution")
        else:
            self._log("WARNING", "No Opportunity rows returned from VDL", "entity_resolution")

        closed_won = [o for o in opps if o.get("Stage") in ("Closed_Won", "Fulfilled")]
        self._log("INFO", f"Found {len(closed_won)} Closed_Won/Fulfilled out of {len(opps)} total", "entity_resolution")

        if not closed_won:
            self._log("WARNING", "No Closed_Won/Fulfilled orders found — check Opportunity data", "entity_resolution")
            self._resolved_orders = []
            return {"status": "completed", "orders_resolved": 0}

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "entity_resolution", "resolving", 0, len(closed_won))

        accounts_list = await self._query_entity("Account")
        if not accounts_list:
            self._log("WARNING", "Account entity returned 0 rows, trying 'Accounts'...", "entity_resolution")
            accounts_list = await self._query_entity("Accounts")
        accounts = {}
        for a in accounts_list:
            aid = self._get_field(a, "Account_ID", "account_id", "AccountId", "Id", default="")
            name = self._get_field(a, "Name", "Account_Name", "name", "account_name", "Company_Name", default="")
            tier = self._get_field(a, "Tier", "tier", "Account_Tier", "Customer_Tier", default="Silver")
            if aid:
                accounts[aid] = {"name": name, "tier": tier}
        if accounts_list and not accounts:
            sample_a = accounts_list[0]
            self._log("WARNING", f"Account keys but no Account_ID match: {sorted(sample_a.keys())[:10]}", "entity_resolution")
        self._log("INFO", f"Loaded {len(accounts)} accounts from {len(accounts_list)} rows", "entity_resolution")

        all_deliveries = await self._query_entity("Delivery_Document", limit=2000)
        del_by_order = {}
        for d in all_deliveries:
            so_id = d.get("Sales_Order_ID", "")
            if so_id:
                del_by_order.setdefault(so_id, []).append(d)
        self._log("INFO", f"Loaded {len(all_deliveries)} deliveries, {len(del_by_order)} linked to orders", "entity_resolution")

        all_invoices = await self._query_entity("AR_Invoice", limit=2000)
        inv_by_delivery = {}
        for inv in all_invoices:
            did = inv.get("Linked_Delivery_ID", "")
            if did:
                inv_by_delivery.setdefault(did, []).append(inv)
        self._log("INFO", f"Loaded {len(all_invoices)} invoices, {len(inv_by_delivery)} linked to deliveries", "entity_resolution")

        resolved = []
        linked_count = 0
        amount_samples = []
        for i, opp in enumerate(closed_won):
            oid = self._get_field(opp, "Opportunity_ID", "opportunity_id", "Id", default="")
            acct_id = self._get_field(opp, "Account_ID", "account_id", "AccountId", default="")
            acct = accounts.get(acct_id, {})
            raw_amount = self._get_field(opp, "Amount", "Total_Value", "Total_Amount", "amount", "Order_Amount", "order_amount", "total_value")
            amount = self._safe_float(raw_amount)

            if i < 3:
                amount_samples.append(f"{oid}: raw={repr(raw_amount)}, float={amount}")

            deliveries = del_by_order.get(oid, [])
            delivery_id = deliveries[0].get("Delivery_ID", "") if deliveries else ""
            invoices = inv_by_delivery.get(delivery_id, []) if delivery_id else []

            if deliveries:
                linked_count += 1

            resolved.append({
                "opportunity_id": oid,
                "account_id": acct_id,
                "account_name": acct.get("name", ""),
                "account_tier": acct.get("tier", "Silver"),
                "order_amount": amount,
                "close_date": self._get_field(opp, "Close_Date", "close_date", "CloseDate", default=""),
                "delivery_id": delivery_id,
                "deliveries": deliveries,
                "invoices": invoices,
            })

            if (i + 1) % 100 == 0 and SSE_AVAILABLE and self.job_id:
                emit_task_progress(self.job_id, "entity_resolution", "resolving", i + 1, len(closed_won))

        self._resolved_orders = resolved
        total_value = sum(o["order_amount"] for o in resolved)
        nonzero_count = sum(1 for o in resolved if o["order_amount"] > 0)
        self._log("INFO", f"Amount samples: {'; '.join(amount_samples)}", "entity_resolution")
        self._log("INFO", f"Resolved {len(resolved)} orders: {linked_count} with deliveries, "
                          f"{nonzero_count} with nonzero amount, total value ${total_value:,.0f}", "entity_resolution")
        return {"status": "completed", "orders_resolved": len(resolved), "with_deliveries": linked_count,
                "nonzero_amounts": nonzero_count, "total_value": round(total_value, 2)}

    async def step_three_way_match(self) -> Dict[str, Any]:
        self._log("INFO", f"Running three-way match on {len(self._resolved_orders)} orders (in-memory)...", "three_way_match")

        results = []
        for order in self._resolved_orders:
            oid = order["opportunity_id"]
            order_amount = order.get("order_amount", 0)
            deliveries = order.get("deliveries", [])
            invoices = order.get("invoices", [])

            delivered_qty = sum(self._safe_float(self._get_field(d, "Quantity", "quantity", "Delivered_Qty", default=0)) for d in deliveries)
            invoiced_amount = sum(self._safe_float(self._get_field(inv, "Amount", "Total_Value", "amount", "Invoice_Amount", default=0)) for inv in invoices)
            delivery_id = order.get("delivery_id", "")
            invoice_id = invoices[0].get("Invoice_ID", "") if invoices else ""

            if not deliveries:
                results.append({
                    "match_status": "missing_delivery", "opportunity_id": oid,
                    "order_amount": order_amount, "delivered_qty": 0,
                    "invoiced_amount": 0, "delivery_id": "", "invoice_id": "",
                    "discrepancies": ["No delivery document found for order"],
                })
                continue

            if not invoices:
                results.append({
                    "match_status": "missing_invoice", "opportunity_id": oid,
                    "order_amount": order_amount, "delivered_qty": delivered_qty,
                    "invoiced_amount": 0, "delivery_id": delivery_id, "invoice_id": "",
                    "discrepancies": ["No invoice found for delivered order"],
                })
                continue

            discrepancies = []
            if invoiced_amount > 0 and order_amount > 0:
                variance_pct = abs(invoiced_amount - order_amount) / order_amount
                if variance_pct > 0.20:
                    discrepancies.append(f"Amount variance {variance_pct:.0%}: order ${order_amount:,.0f} vs invoice ${invoiced_amount:,.0f}")

            has_all_docs = bool(deliveries and invoices)
            if has_all_docs and not discrepancies:
                status = "matched"
            elif has_all_docs and discrepancies:
                status = "partial_match"
            else:
                status = "price_mismatch"

            results.append({
                "match_status": status, "opportunity_id": oid,
                "order_amount": order_amount, "delivered_qty": delivered_qty,
                "invoiced_amount": invoiced_amount, "delivery_id": delivery_id,
                "invoice_id": invoice_id, "discrepancies": discrepancies,
            })

        self._match_results = results
        matched = sum(1 for r in results if r.get("match_status") == "matched")
        partial = sum(1 for r in results if r.get("match_status") == "partial_match")
        missing_del = sum(1 for r in results if r.get("match_status") == "missing_delivery")
        missing_inv = sum(1 for r in results if r.get("match_status") == "missing_invoice")
        self._log("INFO", f"Three-way match: {matched} matched, {partial} partial, "
                          f"{missing_del} missing delivery, {missing_inv} missing invoice", "three_way_match")
        return {"status": "completed", "matched": matched, "partial_match": partial,
                "missing_delivery": missing_del, "missing_invoice": missing_inv}

    async def step_anomaly_scoring(self) -> Dict[str, Any]:
        self._log("INFO", f"Scoring anomalies for {len(self._match_results)} orders (in-memory)...", "anomaly_scoring")

        scores = []
        for mr in self._match_results:
            oid = mr.get("opportunity_id", "")
            anomalies = []
            score = 0

            status = mr.get("match_status", "")
            if status == "missing_delivery":
                anomalies.append({"type": "missing_delivery", "severity": "High", "detail": "No delivery document found"})
                score += 40
            elif status == "missing_invoice":
                anomalies.append({"type": "missing_invoice", "severity": "High", "detail": "No invoice for delivery"})
                score += 30
            elif status == "price_mismatch":
                anomalies.append({"type": "price_mismatch", "severity": "Medium", "detail": mr.get("discrepancies", [""])[0]})
                score += 25

            if mr.get("discrepancies"):
                score += len(mr["discrepancies"]) * 10

            if not mr.get("invoice_id") and mr.get("delivery_id"):
                anomalies.append({"type": "unpaid", "severity": "Medium", "detail": "Delivered but no invoice/payment"})
                score += 15

            scores.append({
                "opportunity_id": oid,
                "anomaly_score": min(score, 100),
                "anomalies": anomalies,
            })

        self._anomaly_scores = scores
        high_risk = sum(1 for s in scores if s.get("anomaly_score", 0) > 50)
        self._log("INFO", f"Anomaly scoring: {high_risk} high-risk orders (score > 50)", "anomaly_scoring")
        return {"status": "completed", "total_scored": len(scores), "high_risk": high_risk}

    async def step_risk_prioritization(self) -> Dict[str, Any]:
        self._log("INFO", "Computing composite risk scores and ranking...", "risk_prioritization")

        max_value = max((o.get("order_amount", 1) for o in self._resolved_orders), default=1)

        ranked = []
        for order, mr, anomaly in zip(self._resolved_orders, self._match_results, self._anomaly_scores):
            a_score = anomaly.get("anomaly_score", 0) / 100
            value_factor = order.get("order_amount", 0) / max_value if max_value > 0 else 0
            tier = order.get("account_tier", "Silver")
            tier_w = TIER_WEIGHT.get(tier, 1.0)

            composite = round(a_score * value_factor * tier_w * 100, 1)

            ranked.append({
                **order,
                "match_status": mr.get("match_status"),
                "discrepancies": mr.get("discrepancies", []),
                "delivered_qty": mr.get("delivered_qty", 0),
                "invoiced_amount": mr.get("invoiced_amount", 0),
                "anomaly_score": anomaly.get("anomaly_score", 0),
                "anomalies": anomaly.get("anomalies", []),
                "composite_risk": composite,
            })

        ranked.sort(key=lambda x: x["composite_risk"], reverse=True)
        for i, r in enumerate(ranked):
            r["risk_rank"] = i + 1

        self._risk_ranked = ranked
        self._log("INFO", f"Risk ranking complete. Top risk: {ranked[0]['composite_risk'] if ranked else 0}", "risk_prioritization")
        return {"status": "completed", "ranked_orders": len(ranked)}

    async def step_workflow_actions(self) -> Dict[str, Any]:
        self._log("INFO", "Evaluating workflow actions for at-risk orders...", "workflow_actions")
        from src.services.control_plane.tools.o2c_tools import (
            _place_credit_hold, _create_dispute_case, _update_invoice_status,
            _escalate_sla_breach, _request_expedited_fulfillment,
        )
        vq = self._get_vq_service()
        actions = []

        accounts_checked = set()
        for order in self._risk_ranked[:50]:
            oid = order.get("opportunity_id", "")
            match_status = order.get("match_status", "")
            amount = float(order.get("order_amount", 0))
            account_id = order.get("account_id", "")
            invoice_id = order.get("invoice_id", "")
            delivery_id = order.get("delivery_id", "")
            anomaly_score = order.get("anomaly_score", 0)

            if match_status in ("price_mismatch", "quantity_mismatch") and amount > 50000 and invoice_id:
                try:
                    result = await _create_dispute_case(vq, oid, invoice_id,
                                                        dispute_reason=f"Three-way match {match_status}",
                                                        order_amount=amount,
                                                        invoiced_amount=float(order.get("invoiced_amount", 0)))
                    actions.append({**result, "entity_type": "Invoice", "entity_id": invoice_id})
                    await _update_invoice_status(vq, invoice_id, "Disputed")
                    self._log("INFO", f"  Dispute case created for {oid} (${amount:,.0f})", "workflow_actions")
                except Exception as e:
                    self._log("WARNING", f"  Dispute creation failed for {oid}: {e}", "workflow_actions")

            if account_id and account_id not in accounts_checked and anomaly_score >= 40:
                accounts_checked.add(account_id)
                try:
                    result = await _place_credit_hold(vq, account_id, reason=f"High anomaly score ({anomaly_score}) on {oid}")
                    if result.get("action") == "credit_hold_placed":
                        actions.append({**result, "entity_type": "Account", "entity_id": account_id})
                        self._log("INFO", f"  Credit hold placed on {account_id}", "workflow_actions")
                except Exception as e:
                    self._log("WARNING", f"  Credit hold failed for {account_id}: {e}", "workflow_actions")

            if anomaly_score >= 50 and delivery_id:
                try:
                    result = await _request_expedited_fulfillment(vq, delivery_id, reason=f"Anomaly score {anomaly_score}")
                    actions.append({**result, "entity_type": "Delivery", "entity_id": delivery_id})
                except Exception:
                    pass

            if match_status == "missing_delivery":
                sla_pct = 100.0
                level = "regional_manager" if amount > 200000 else "fulfillment_team"
                try:
                    result = await _escalate_sla_breach(vq, oid, sla_pct, level)
                    actions.append({**result, "entity_type": "Order", "entity_id": oid})
                    self._log("INFO", f"  SLA escalation for {oid} -> {level}", "workflow_actions")
                except Exception:
                    pass

        self._workflow_actions = actions
        self._log("INFO", f"Workflow actions complete: {len(actions)} actions executed", "workflow_actions")
        return {"status": "completed", "actions_executed": len(actions)}

    async def step_dunning_and_collections(self) -> Dict[str, Any]:
        self._log("INFO", "Processing dunning and collections for overdue invoices...", "dunning_and_collections")
        from src.services.control_plane.tools.o2c_tools import _send_dunning_notice
        vq = self._get_vq_service()

        all_invoices = await self._query_entity("AR_Invoice", limit=2000)
        overdue = [i for i in all_invoices if i.get("Status") in ("Open", "Overdue")]

        from datetime import datetime, timedelta
        now = datetime.now()
        dunning_actions = []

        for inv in overdue:
            inv_id = inv.get("Invoice_ID", "")
            customer_id = inv.get("Customer_ID", "")
            due_date_str = inv.get("Due_Date", "")
            if not due_date_str or not inv_id:
                continue
            try:
                due_date = datetime.fromisoformat(due_date_str) if "T" in due_date_str else datetime.strptime(due_date_str, "%Y-%m-%d")
                days_overdue = (now - due_date).days
            except Exception:
                continue

            if days_overdue < 7:
                continue

            if days_overdue >= 60:
                tier = "final"
            elif days_overdue >= 30:
                tier = "escalation"
            elif days_overdue >= 14:
                tier = "warning"
            else:
                tier = "reminder"

            try:
                result = await _send_dunning_notice(vq, inv_id, customer_id, days_overdue, tier)
                dunning_actions.append({**result, "entity_type": "Invoice", "entity_id": inv_id})
            except Exception:
                pass

        if not hasattr(self, '_workflow_actions'):
            self._workflow_actions = []
        self._workflow_actions.extend(dunning_actions)

        tier_counts = {}
        for d in dunning_actions:
            t = d.get("tier", "unknown")
            tier_counts[t] = tier_counts.get(t, 0) + 1

        self._log("INFO", f"Dunning complete: {len(dunning_actions)} notices sent ({tier_counts})", "dunning_and_collections")
        return {"status": "completed", "dunning_notices": len(dunning_actions), "by_tier": tier_counts}

    async def step_action_summary(self) -> Dict[str, Any]:
        self._log("INFO", "Generating action summary and audit log...", "action_summary")
        import uuid
        actions = getattr(self, '_workflow_actions', [])

        action_log = []
        for i, action in enumerate(actions):
            action_log.append({
                "action_id": f"ACT-{uuid.uuid4().hex[:8].upper()}",
                "action_type": action.get("action", "unknown").replace("_placed", "").replace("_created", "").replace("_sent", "").replace("_requested", "").replace("_escalated", "").replace("_processed", ""),
                "entity_type": action.get("entity_type", ""),
                "entity_id": action.get("entity_id", ""),
                "status": "executed",
                "policy_reference": action.get("policy_reference", action.get("Policy_Reference", "")),
                "details": {k: v for k, v in action.items() if k not in ("entity_type", "entity_id", "simulator_update")},
                "job_id": self.job_id,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            })

        try:
            from src.apis.fdw_api import _simulators
            ext = _simulators.get("external")
            if ext and getattr(ext, "loaded", False):
                if hasattr(ext, "write_table"):
                    await ext.write_table("external_sources", "O2C_Action_Log", action_log)
                else:
                    ext._data[("external_sources", "O2C_Action_Log")] = action_log
                self._log("INFO", f"Stored {len(action_log)} action log entries in simulator", "action_summary")
        except Exception as e:
            self._log("WARNING", f"Failed to store action log: {e}", "action_summary")

        self._action_log = action_log

        by_type = {}
        for a in action_log:
            t = a.get("action_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        self._log("INFO", f"Action summary: {len(action_log)} total actions — {by_type}", "action_summary")
        return {"status": "completed", "total_actions": len(action_log), "by_type": by_type}

    async def step_cash_flow_projection(self) -> Dict[str, Any]:
        self._log("INFO", "Projecting cash flow from resolved orders and invoices...", "cash_flow_projection")

        all_invoices = await self._query_entity("AR_Invoice", limit=2000)
        if all_invoices:
            self._log("INFO", f"Invoice sample keys: {sorted(all_invoices[0].keys())[:8]}", "cash_flow_projection")

        def _inv_amount(inv):
            return self._safe_float(self._get_field(inv, "Total_Amount", "Amount", "Total_Value", "amount", "Invoice_Amount", "total_value"))

        def _inv_status(inv):
            return self._get_field(inv, "Status", "status", "Invoice_Status", default="")

        open_invoices = [i for i in all_invoices if _inv_status(i) in ("Open", "Overdue", "Partial")]
        total_open = sum(_inv_amount(i) for i in open_invoices)
        total_ar = sum(_inv_amount(i) for i in all_invoices)
        at_risk = sum(_inv_amount(i) for i in open_invoices if _inv_status(i) == "Overdue")
        self._log("INFO", f"Invoices: {len(all_invoices)} total, {len(open_invoices)} open, "
                          f"AR=${total_ar:,.0f}, open=${total_open:,.0f}", "cash_flow_projection")

        dso = (total_open / (total_ar / 365)) if total_ar > 0 else 0

        total_order_value = sum(o.get("order_amount", 0) for o in self._resolved_orders)
        mismatched_value = sum(
            o.get("order_amount", 0) for o, mr in zip(self._resolved_orders, self._match_results)
            if mr.get("match_status") != "matched"
        )

        weekly = []
        chunk = total_open / 8 if total_open > 0 else 0
        for w in range(1, 9):
            prob = max(0.95 - (w * 0.08), 0.3)
            weekly.append({"week": w, "amount": round(chunk * prob, 2), "probability": round(prob, 2)})

        projection = {
            "total_open_ar": round(total_open, 2),
            "total_invoices": len(all_invoices),
            "open_invoices": len(open_invoices),
            "dso": round(dso, 1),
            "at_risk_amount": round(at_risk, 2),
            "projected_weekly": weekly,
            "total_order_value": round(total_order_value, 2),
            "mismatched_value": round(mismatched_value, 2),
        }
        self._cash_projection = projection
        self._log("INFO", f"Cash projection: ${total_open:,.0f} open AR, DSO {dso:.1f}, "
                          f"${at_risk:,.0f} at risk, total orders ${total_order_value:,.0f}", "cash_flow_projection")
        return {"status": "completed", **projection}

    async def step_store_results(self) -> Dict[str, Any]:
        self._log("INFO", "Generating alerts and storing results to S3...", "store_results")

        from src.services.control_plane.tools.o2c_tools import _generate_o2c_alerts
        alerts_result = await _generate_o2c_alerts(self._match_results, self._anomaly_scores, self._cash_projection)
        self._alerts = alerts_result
        # Surface the domain KPI dict to BaseStage.effective_kpis() so
        # ``complete_job`` persists it on Data.kpis. Includes the
        # ``alerts`` list itself + ``total_alerts`` count so the
        # report schema's alerts_list section has its source path
        # resolved at ``Data.kpis.alerts``.
        kpis_dict = dict(alerts_result.get("kpis", {}) or {})
        alerts_list = alerts_result.get("alerts", []) or []
        kpis_dict.setdefault("alerts", alerts_list)
        kpis_dict.setdefault("total_alerts", len(alerts_list))
        # Cash flow + portfolio totals that o2c_processor already
        # computes are also worth surfacing.
        if self._cash_projection:
            for k in ("total_open_ar", "at_risk_amount", "mismatched_value",
                      "total_order_value", "dso"):
                if k in self._cash_projection and k not in kpis_dict:
                    kpis_dict[k] = self._cash_projection.get(k)
            # Sum the weekly amounts into a single scalar so the
            # report schema (which uses rollup=sum on a numeric value)
            # can render it -- avoids passing a list through the
            # numeric formatter.
            weekly = self._cash_projection.get("projected_weekly") or []
            if weekly:
                kpis_dict.setdefault(
                    "projected_weekly_total",
                    round(sum(float(w.get("amount", 0)) for w in weekly), 2),
                )
        # Workflow-action counters surfaced for the report's collections
        # section. ``_workflow_actions`` is a list of action dicts
        # populated by step_workflow_actions + step_dunning_and_collections.
        actions = getattr(self, "_workflow_actions", []) or []
        if actions:
            kpis_dict.setdefault("total_actions", len(actions))
            dunning_count = sum(
                1 for a in actions
                if "dunning" in str(a.get("action", "")).lower()
            )
            if dunning_count:
                kpis_dict.setdefault("dunning_notices", dunning_count)
        self._kpis = kpis_dict

        now = datetime.now(timezone.utc)
        year, month, day = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")

        bucket = getattr(self._config, "s3_recordings_bucket", "") if self._config else ""
        if not bucket:
            import os
            bucket = os.getenv("S3_RECORDINGS_BUCKET", "")

        results_stored = 0

        if bucket and self._s3:
            for order in self._risk_ranked:
                oid = order.get("opportunity_id", "unknown")
                key = f"o2c-data/year={year}/month={month}/day={day}/{oid}.json"
                order_clean = {k: v for k, v in order.items() if k not in ("deliveries", "invoices")}
                order_clean["job_id"] = self.job_id
                order_clean["processed_at"] = now.isoformat()
                try:
                    self._s3.put_object(Bucket=bucket, Key=key,
                                        Body=json.dumps(order_clean, default=str),
                                        ContentType="application/json")
                    results_stored += 1
                except Exception as e:
                    if results_stored == 0:
                        self._log("WARNING", f"S3 write failed: {e}", "store_results")

            alerts_key = f"o2c-alerts/year={year}/month={month}/day={day}/alerts_{self.job_id}.json"
            alerts_doc = {"job_id": self.job_id, "processed_at": now.isoformat(),
                          "total_alerts": len(alerts_result.get("alerts", [])),
                          "alerts": alerts_result.get("alerts", [])}
            try:
                self._s3.put_object(Bucket=bucket, Key=alerts_key,
                                    Body=json.dumps(alerts_doc, default=str),
                                    ContentType="application/json")
            except Exception as e:
                self._log("WARNING", f"Alerts S3 write failed: {e}", "store_results")

            kpis_key = f"o2c-kpis/year={year}/month={month}/day={day}/kpis_{self.job_id}.json"
            kpis_doc = {"job_id": self.job_id, "processed_at": now.isoformat(),
                        **alerts_result.get("kpis", {}),
                        "cash_projection": self._cash_projection.get("projected_weekly", [])}
            try:
                self._s3.put_object(Bucket=bucket, Key=kpis_key,
                                    Body=json.dumps(kpis_doc, default=str),
                                    ContentType="application/json")
            except Exception as e:
                self._log("WARNING", f"KPIs S3 write failed: {e}", "store_results")

            self._log("INFO", f"Stored {results_stored} order results + alerts + KPIs to S3", "store_results")
        else:
            self._log("WARNING", "No S3 bucket configured — results stored in memory only", "store_results")

        try:
            from .o2c_glue_catalog import O2CGlueCatalog
            glue = O2CGlueCatalog(
                region_name=getattr(self._config, "aws_region", "us-east-1"),
                database_name=getattr(self._config, "glue_database_name", ""),
            )
            glue.ensure_tables(bucket)
            glue.add_partition("o2c_orders", bucket, f"o2c-data/year={year}/month={month}/day={day}/", year, month, day)
            glue.add_partition("o2c_alerts", bucket, f"o2c-alerts/year={year}/month={month}/day={day}/", year, month, day)
            glue.add_partition("o2c_kpis", bucket, f"o2c-kpis/year={year}/month={month}/day={day}/", year, month, day)
            self._log("INFO", "Glue partitions registered", "store_results")
        except Exception as e:
            self._log("WARNING", f"Glue registration failed (non-fatal): {e}", "store_results")

        try:
            from src.apis.fdw_api import _simulators
            ext_sim = _simulators.get("external")
            if ext_sim and getattr(ext_sim, "loaded", False):
                order_rows: List[Dict] = []
                for order in self._risk_ranked:
                    row = {k: v for k, v in order.items() if k not in ("deliveries", "invoices")}
                    row["job_id"] = self.job_id
                    row["processed_at"] = now.isoformat()
                    order_rows.append(row)
                if hasattr(ext_sim, "write_table"):
                    await ext_sim.write_table("external_sources", "O2C_Order_Result", order_rows)
                else:
                    ext_sim._data.setdefault(("external_sources", "O2C_Order_Result"), []).clear()
                    for r in order_rows:
                        ext_sim._data.setdefault(("external_sources", "O2C_Order_Result"), []).append(r)

                alerts_list = alerts_result.get("alerts", [])
                alert_row = {
                    "job_id": self.job_id, "processed_at": now.isoformat(),
                    "total_alerts": len(alerts_list),
                    "alerts": json.dumps(alerts_list, default=str),
                }
                if hasattr(ext_sim, "write_table"):
                    await ext_sim.write_table("external_sources", "O2C_Alert", [alert_row])
                else:
                    ext_sim._data[("external_sources", "O2C_Alert")] = [alert_row]

                kpis_row = {"job_id": self.job_id, "processed_at": now.isoformat(),
                            **alerts_result.get("kpis", {})}
                if hasattr(ext_sim, "write_table"):
                    await ext_sim.write_table("external_sources", "O2C_KPI_Snapshot", [kpis_row])
                else:
                    ext_sim._data[("external_sources", "O2C_KPI_Snapshot")] = [kpis_row]

                self._log("INFO", f"Pushed {len(self._risk_ranked)} results + alerts + KPIs to external simulator", "store_results")

                try:
                    save_result = await ext_sim.save_to_s3()
                    if save_result.get("success"):
                        self._log("INFO", f"Persisted simulator to S3 ({save_result.get('tables')} tables, {save_result.get('rows')} rows)", "store_results")
                    else:
                        self._log("WARNING", f"S3 persist skipped: {save_result.get('message')}", "store_results")
                except Exception as se:
                    self._log("WARNING", f"Simulator S3 persist failed (non-fatal): {se}", "store_results")
            else:
                self._log("INFO", "External simulator not available — skipping simulator push", "store_results")
        except Exception as e:
            self._log("WARNING", f"Simulator push failed (non-fatal): {e}", "store_results")

        try:
            await self._ensure_o2c_mapping_rules()
        except Exception as e:
            self._log("WARNING", f"Mapping rule creation failed (non-fatal): {e}", "store_results")

        kpis = alerts_result.get("kpis", {})
        total_alerts = len(alerts_result.get("alerts", []))

        self._log("INFO", f"O2C complete: {len(self._risk_ranked)} orders, {total_alerts} alerts, "
                          f"DSO {kpis.get('dso', 0):.1f}, match rate {kpis.get('match_rate', 0):.1f}%", "store_results")

        return {
            "status": "completed",
            "orders_stored": results_stored,
            "total_alerts": total_alerts,
            "kpis": kpis,
        }

    async def _ensure_o2c_mapping_rules(self):
        """Create VDL mapping rules for O2C entities so dashboard widgets can query them."""
        from src.apis.mapping_rule_api import _service as mr_service
        from src.models.mapping_rule_models import (
            MappingRuleCreateRequest, MappingRuleUpdateRequest,
            MappingRuleSourceType, MappingRuleStatus, FieldMap,
        )

        if mr_service is None:
            self._log("WARNING", "Mapping rule service not initialized — skipping rule creation", "store_results")
            return

        o2c_entities = [
            "O2C_Order_Result", "O2C_Alert", "O2C_KPI_Snapshot",
            "O2C_Action_Log", "O2C_Dunning_Notice", "O2C_Escalation",
        ]

        svc = mr_service
        existing = await svc.list_all()
        existing_ve = {r.virtual_entity for r in existing}

        created = 0
        for entity in o2c_entities:
            if entity in existing_ve:
                continue
            data_rows = []
            try:
                from src.apis.fdw_api import _simulators
                ext = _simulators.get("external")
                if ext:
                    if hasattr(ext, "_get_table_data"):
                        data_rows = await ext._get_table_data("external_sources", entity)
                    elif hasattr(ext, "_data"):
                        data_rows = ext._data.get(("external_sources", entity), [])
            except Exception:
                pass
            fields = list(data_rows[0].keys()) if data_rows else []
            field_maps = [FieldMap(source_field=f, target_field=f) for f in fields]

            try:
                rule = await svc.create(MappingRuleCreateRequest(
                    name=f"Auto: {entity}",
                    virtual_entity=entity,
                    source_type=MappingRuleSourceType.FDW,
                    source_system="O2C",
                    source_table=entity,
                    source_schema="external_sources",
                    field_maps=field_maps,
                ))
                await svc.update(rule.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
                created += 1
            except Exception as e:
                self._log("WARNING", f"Failed to create mapping rule for {entity}: {e}", "store_results")

        if created:
            self._log("INFO", f"Created {created} VDL mapping rules for O2C entities", "store_results")

    async def step_verify_results(self) -> Dict[str, Any]:
        """Read back O2C result entities from Athena via VDL to verify data is queryable."""
        import asyncio
        self._log("INFO", "Waiting 5s for Athena partition recognition...", "verify_results")
        await asyncio.sleep(5)
        self._log("INFO", "Verifying result objects via Athena/VDL...", "verify_results")

        for src_entity in ["Opportunity", "Account", "Delivery_Document", "AR_Invoice"]:
            try:
                rows = await self._query_entity(src_entity, limit=3)
                if rows:
                    sample = rows[0]
                    self._log("INFO", f"Source {src_entity}: {len(rows)}+ rows, keys={sorted(sample.keys())[:8]}", "verify_results")
                else:
                    self._log("WARNING", f"Source {src_entity}: 0 rows", "verify_results")
            except Exception as e:
                self._log("WARNING", f"Source {src_entity}: error — {e}", "verify_results")

        entities = {
            "O2C_Order_Result": {"expected_min": 1, "key_columns": ["opportunity_id", "match_status", "anomaly_score", "risk_rank"]},
            "O2C_KPI_Snapshot": {"expected_min": 1, "key_columns": ["dso", "match_rate", "total_open_ar"]},
            "O2C_Alert": {"expected_min": 1, "key_columns": ["total_alerts", "alerts"]},
        }

        verification = {}
        all_ok = True

        for entity, spec in entities.items():
            rows = await self._query_entity(entity, limit=200)
            row_count = len(rows)
            ok = row_count >= spec["expected_min"]
            if not ok:
                all_ok = False

            present_cols = list(rows[0].keys()) if rows else []
            missing_cols = [c for c in spec["key_columns"] if c not in present_cols]

            verification[entity] = {
                "rows": row_count,
                "status": "pass" if ok and not missing_cols else "fail",
                "missing_columns": missing_cols,
                "sample_columns": present_cols[:10],
            }

            status_label = "PASS" if ok and not missing_cols else "FAIL"
            self._log("INFO", f"  {entity}: {row_count} rows — {status_label}"
                      + (f" (missing: {missing_cols})" if missing_cols else ""), "verify_results")

        summary = {}
        order_rows = await self._query_entity("O2C_Order_Result", limit=500)
        if order_rows:
            matched = sum(1 for r in order_rows if r.get("match_status") in ("matched", "partial_match"))
            total = len(order_rows)
            total_value = sum(float(r.get("order_amount", 0)) for r in order_rows)
            high_risk = sum(1 for r in order_rows if float(r.get("anomaly_score", 0)) > 50)
            top_risk = sorted(order_rows, key=lambda r: float(r.get("composite_risk", 0)), reverse=True)[:5]

            summary = {
                "total_orders": total,
                "matched": matched,
                "mismatched": total - matched,
                "match_rate_pct": round(matched / total * 100, 1) if total else 0,
                "total_order_value": round(total_value, 2),
                "high_risk_orders": high_risk,
                "top_5_risk": [
                    {
                        "opportunity_id": r.get("opportunity_id"),
                        "account_name": r.get("account_name"),
                        "amount": r.get("order_amount"),
                        "match_status": r.get("match_status"),
                        "anomaly_score": r.get("anomaly_score"),
                        "risk_rank": r.get("risk_rank"),
                    }
                    for r in top_risk
                ],
            }

            self._log("INFO", f"  Summary: {total} orders, {matched} matched ({summary['match_rate_pct']}%), "
                      f"{high_risk} high-risk, total value ${total_value:,.0f}", "verify_results")

        kpi_rows = await self._query_entity("O2C_KPI_Snapshot", limit=1)
        kpi_summary = {}
        if kpi_rows:
            kpi = kpi_rows[0]
            kpi_summary = {
                "dso": kpi.get("dso"),
                "match_rate": kpi.get("match_rate"),
                "leakage_rate": kpi.get("leakage_rate"),
                "total_open_ar": kpi.get("total_open_ar"),
            }
            self._log("INFO", f"  KPIs: DSO={kpi.get('dso')}, Match Rate={kpi.get('match_rate')}, "
                      f"Open AR=${float(kpi.get('total_open_ar', 0)):,.0f}", "verify_results")

        alert_rows = await self._query_entity("O2C_Alert", limit=1)
        alert_count = 0
        if alert_rows:
            alert_count = alert_rows[0].get("total_alerts", 0)
            self._log("INFO", f"  Alerts: {alert_count} active alerts", "verify_results")

        overall = "passed" if all_ok else "failed"
        self._log("INFO", f"Verification {overall}: all result entities {'are' if all_ok else 'are NOT'} queryable via VDL", "verify_results")

        return {
            "status": "completed",
            "verification": overall,
            "entities": verification,
            "summary": summary,
            "kpis": kpi_summary,
            "alert_count": alert_count,
        }
