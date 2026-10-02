"""
Customer 360 & Revenue Growth Processor

Implements the 6-step customer profile generation pipeline. Each step queries the
Virtual Data Layer, processes data using deterministic simulation logic, and
stores results for the final S3 write and alert generation.
"""

import hashlib
import json
import math
import random
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

c360_logger = logger.bind(component="customer-360-processor")

try:
    from ...utils.sse_manager import emit_task_progress, emit_log
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    def emit_task_progress(*a, **kw): pass
    def emit_log(*a, **kw): pass

TIERS = ["Enterprise", "Mid-Market", "SMB", "Strategic"]
REGIONS = ["North", "South", "East", "West", "Central"]

INDUSTRY_WALLET_FACTOR = {
    "Technology": 3.5,
    "Manufacturing": 2.8,
    "Healthcare": 3.0,
    "Financial Services": 4.0,
    "Retail": 2.2,
    "Energy": 3.2,
    "Telecommunications": 2.6,
    "Other": 2.5,
}

PRODUCT_CATEGORIES = [
    "Carbonated", "Juice", "Water", "Energy", "Sports", "Tea", "Snacks",
    "Dairy", "Supplements", "Frozen",
]


class Customer360Processor:

    def __init__(self, log_callback: Optional[Callable] = None, job_id: str = "",
                 journey_id: str = "", s3_client=None, config=None):
        self._log_cb = log_callback
        self.job_id = job_id
        self.journey_id = journey_id
        self._s3 = s3_client
        self._config = config

        self._account_map: Dict[str, Dict] = {}
        self._opp_by_account: Dict[str, List[Dict]] = defaultdict(list)
        self._invoice_by_account: Dict[str, List[Dict]] = defaultdict(list)
        self._sentiment_by_account: Dict[str, List[Dict]] = defaultdict(list)
        self._contacts: List[Dict] = []
        self._campaigns: List[Dict] = []
        self._return_orders: List[Dict] = []
        self._line_items: List[Dict] = []
        self._payments: List[Dict] = []

        self._clv_data: Dict[str, Dict] = {}
        self._churn_scores: Dict[str, Dict] = {}
        self._wallet_data: Dict[str, Dict] = {}
        self._cross_sell_scores: Dict[str, Dict] = {}
        self._alerts: List[Dict] = []
        self._kpis: Dict[str, Any] = {}

    def _log(self, level: str, msg: str, step_id: str = None):
        if self._log_cb:
            self._log_cb(level, msg, step_id)
        else:
            c360_logger.log(level.upper(), msg)
        if SSE_AVAILABLE and self.job_id and step_id:
            emit_log(self.job_id, step_id, level.upper(), msg)

    def _get_vq_service(self):
        from src.apis.control_plane_api import _virtual_query_service
        return _virtual_query_service

    async def _query_entity(self, entity: str, filters=None, limit=2000) -> List[Dict]:
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

    async def _query_simulator_direct(self, entity: str, filters=None, limit=2000) -> List[Dict]:
        try:
            from src.apis.fdw_api import _simulators
            from src.models.fdw_models import QueryRequest, QueryFilter, FilterOperator

            schema_map = {
                "Account": ("sfdc_itxp2dev", "simulator", None),
                "Contact": ("sfdc_itxp2dev", "simulator", None),
                "Opportunity": ("sfdc_itxp2dev", "simulator", None),
                "Opportunity_Line_Item": ("sfdc_itxp2dev", "simulator", None),
                "AR_Customer": ("oracle_erp", "oracle", "Oracle_AR_Customer"),
                "AR_Invoice": ("oracle_erp", "oracle", "Oracle_AR_Invoice"),
                "AR_Payment": ("oracle_erp", "oracle", "Oracle_AR_Payment"),
                "Brand_Sentiment": ("external_sources", "external", None),
                "Campaign": ("sfdc_itxp2dev", "simulator", None),
                "Return_Order": ("sap_s4hana", "sap", None),
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
    def _deterministic_seed(key1: str, key2: str, salt: int = 0) -> float:
        h = hashlib.md5(f"{key1}-{key2}-{salt}".encode()).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF

    async def _ensure_c360_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_entities = {r.virtual_entity for r in existing}

            rules = [
                ("Account", "sfdc_itxp2dev", "Account", {
                    "Account_ID": "Account_ID", "Name": "Name", "Channel_Type": "Channel_Type",
                    "Region": "Region", "Tier": "Tier", "Industry": "Industry",
                    "Annual_Revenue": "Annual_Revenue"}),
                ("Contact", "sfdc_itxp2dev", "Contact", {
                    "Contact_ID": "Contact_ID", "Account_ID": "Account_ID",
                    "Email": "Email", "Title": "Title", "Role": "Role"}),
                ("Opportunity", "sfdc_itxp2dev", "Opportunity", {
                    "Opportunity_ID": "Opportunity_ID", "Account_ID": "Account_ID",
                    "Total_Value": "Amount", "Stage": "Stage", "Close_Date": "Close_Date",
                    "Region": "Region", "Product_Category": "Product_Category"}),
                ("Opportunity_Line_Item", "sfdc_itxp2dev", "Opportunity_Line_Item", {
                    "Line_ID": "Line_Item_ID", "Opportunity_ID": "Opportunity_ID",
                    "Product_ID": "Product_ID", "Quantity": "Quantity", "Unit_Price": "Unit_Price"}),
                ("AR_Customer", "oracle_erp", "Oracle_AR_Customer", {
                    "Customer_ID": "Customer_ID", "Account_ID": "Account_ID",
                    "Credit_Limit": "Credit_Limit", "Payment_Terms": "Payment_Terms"}),
                ("AR_Invoice", "oracle_erp", "Oracle_AR_Invoice", {
                    "Invoice_ID": "Invoice_ID", "Customer_ID": "Customer_ID",
                    "Amount": "Amount", "Due_Date": "Due_Date", "Status": "Status",
                    "Invoice_Date": "Invoice_Date"}),
                ("AR_Payment", "oracle_erp", "Oracle_AR_Payment", {
                    "Payment_ID": "Payment_ID", "Invoice_ID": "Invoice_ID",
                    "Amount": "Amount", "Payment_Date": "Payment_Date", "Method": "Method"}),
                ("Brand_Sentiment", "external_sources", "Brand_Sentiment", {
                    "Sentiment_ID": "Sentiment_ID", "Account_ID": "Account_ID",
                    "Score": "Score", "Source": "Source", "Sentiment": "Sentiment",
                    "Timestamp": "Timestamp"}),
                ("Campaign", "sfdc_itxp2dev", "Campaign", {
                    "Campaign_ID": "Campaign_ID", "Type": "Type", "Start_Date": "Start_Date",
                    "End_Date": "End_Date", "Target_Segment": "Target_Segment", "Status": "Status"}),
                ("Return_Order", "sap_s4hana", "Return_Order", {
                    "Return_ID": "Return_ID", "Account_ID": "Account_ID",
                    "Amount": "Amount", "Reason": "Reason", "Return_Date": "Return_Date"}),
            ]

            from src.models.mapping_rule_models import (
                MappingRuleCreateRequest, MappingRuleUpdateRequest,
                MappingRuleSourceType, MappingRuleStatus, FieldMap,
            )
            created = 0
            for virtual_entity, schema, table, field_map in rules:
                if virtual_entity in existing_entities:
                    continue
                field_maps = [FieldMap(source_field=s, target_field=t) for s, t in field_map.items()]
                rule = MappingRuleCreateRequest(
                    name=f"C360: {virtual_entity}",
                    virtual_entity=virtual_entity,
                    source_schema=schema,
                    source_table=table,
                    source_system=schema,
                    source_type=MappingRuleSourceType.FDW,
                    field_maps=field_maps,
                )
                resp = await service.create(rule)
                await service.update(resp.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
                created += 1

            if created:
                self._log("INFO", f"Created {created} VDL mapping rules for customer 360")
        except Exception as e:
            self._log("WARNING", f"Could not ensure mapping rules: {e}")

    # ─── Step 1: Load Customer Data ──────────────────────────────────────

    async def step_load_customer_data(self) -> Dict[str, Any]:
        self._log("INFO", "Step 1: Load Customer Data — querying 10 entities...", "load_customer_data")

        await self._ensure_c360_mapping_rules()

        accounts = await self._query_entity("Account")
        contacts = await self._query_entity("Contact")
        opps = await self._query_entity("Opportunity")
        line_items = await self._query_entity("Opportunity_Line_Item")
        ar_customers = await self._query_entity("AR_Customer")
        invoices = await self._query_entity("AR_Invoice")
        payments = await self._query_entity("AR_Payment")
        sentiments = await self._query_entity("Brand_Sentiment")
        campaigns = await self._query_entity("Campaign")
        return_orders = await self._query_entity("Return_Order")

        self._log("INFO", (
            f"Loaded entities — Accounts: {len(accounts)}, Contacts: {len(contacts)}, "
            f"Opps: {len(opps)}, LineItems: {len(line_items)}, AR_Customers: {len(ar_customers)}, "
            f"Invoices: {len(invoices)}, Payments: {len(payments)}, Sentiments: {len(sentiments)}, "
            f"Campaigns: {len(campaigns)}, ReturnOrders: {len(return_orders)}"
        ), "load_customer_data")

        self._account_map = {}
        for a in accounts:
            aid = a.get("Account_ID", "")
            if aid:
                self._account_map[aid] = a

        self._opp_by_account = defaultdict(list)
        for o in opps:
            aid = o.get("Account_ID", "")
            if aid:
                self._opp_by_account[aid].append(o)

        ar_customer_to_account = {}
        for arc in ar_customers:
            cid = arc.get("Customer_ID", "")
            aid = arc.get("Account_ID", "")
            if cid and aid:
                ar_customer_to_account[cid] = aid

        self._invoice_by_account = defaultdict(list)
        for inv in invoices:
            cid = inv.get("Customer_ID", "")
            aid = ar_customer_to_account.get(cid, cid)
            if aid:
                self._invoice_by_account[aid].append(inv)

        self._sentiment_by_account = defaultdict(list)
        for s in sentiments:
            aid = s.get("Account_ID", "")
            if aid:
                self._sentiment_by_account[aid].append(s)

        self._contacts = contacts
        self._campaigns = campaigns
        self._return_orders = return_orders
        self._line_items = line_items
        self._payments = payments

        self._log("INFO", (
            f"Built indexes — account_map: {len(self._account_map)}, "
            f"opp_by_account: {len(self._opp_by_account)}, "
            f"invoice_by_account: {len(self._invoice_by_account)}, "
            f"sentiment_by_account: {len(self._sentiment_by_account)}"
        ), "load_customer_data")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "load_customer_data", "completed",
                               len(self._account_map), len(self._account_map))

        return {
            "status": "completed",
            "accounts_loaded": len(self._account_map),
            "entities_queried": 10,
            "total_opportunities": len(opps),
            "total_invoices": len(invoices),
            "total_sentiments": len(sentiments),
        }

    # ─── Step 2: CLV Calculation ─────────────────────────────────────────

    async def step_clv_calculation(self) -> Dict[str, Any]:
        self._log("INFO", "Step 2: CLV Calculation — computing lifetime value per account...", "clv_calculation")

        if not self._account_map:
            return {"status": "error", "message": "No accounts loaded — run step 1 first"}

        clv_data = {}
        for aid, account in self._account_map.items():
            account_opps = self._opp_by_account.get(aid, [])
            won_opps = [o for o in account_opps if o.get("Stage") in ("Closed_Won", "Fulfilled")]

            total_revenue = sum(self._safe_float(o.get("Amount", o.get("Total_Value", 0))) for o in won_opps)
            order_count = len(won_opps)

            close_dates = []
            for o in won_opps:
                cd = o.get("Close_Date", "")
                if cd:
                    try:
                        dt = datetime.fromisoformat(str(cd).replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        close_dates.append(dt)
                    except (ValueError, TypeError):
                        pass

            now = datetime.now(timezone.utc)
            if close_dates:
                most_recent = max(close_dates)
                recency_days = (now - most_recent).days
            else:
                recency_days = 365

            seed = self._deterministic_seed(aid, "clv", 0)
            frequency_factor = min(1.0 + (order_count / 20.0), 2.5)
            recency_factor = max(1.0 - (recency_days / 730.0), 0.3)
            clv = round(total_revenue * frequency_factor * recency_factor * (0.8 + seed * 0.4), 2)

            clv_data[aid] = {
                "total_revenue": round(total_revenue, 2),
                "order_count": order_count,
                "recency_days": recency_days,
                "frequency_factor": round(frequency_factor, 3),
                "recency_factor": round(recency_factor, 3),
                "clv": clv,
            }

        self._clv_data = clv_data

        avg_clv = sum(d["clv"] for d in clv_data.values()) / max(len(clv_data), 1)
        self._log("INFO", (
            f"CLV computed for {len(clv_data)} accounts — avg CLV: ${avg_clv:,.2f}"
        ), "clv_calculation")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "clv_calculation", "completed",
                               len(clv_data), len(clv_data))

        return {
            "status": "completed",
            "accounts_scored": len(clv_data),
            "avg_clv": round(avg_clv, 2),
            "total_revenue": round(sum(d["total_revenue"] for d in clv_data.values()), 2),
        }

    # ─── Step 3: Churn Prediction ────────────────────────────────────────

    async def step_churn_prediction(self) -> Dict[str, Any]:
        self._log("INFO", "Step 3: Churn Prediction — scoring churn risk per account...", "churn_prediction")

        if not self._account_map:
            return {"status": "error", "message": "No accounts loaded — run step 1 first"}

        churn_scores = {}
        for aid, account in self._account_map.items():
            signals = []

            account_opps = self._opp_by_account.get(aid, [])
            won_opps = [o for o in account_opps if o.get("Stage") in ("Closed_Won", "Fulfilled")]
            if len(won_opps) >= 2:
                close_dates = []
                for o in won_opps:
                    cd = o.get("Close_Date", "")
                    if cd:
                        try:
                            close_dates.append(datetime.fromisoformat(str(cd).replace("Z", "+00:00")))
                        except (ValueError, TypeError):
                            pass
                if len(close_dates) >= 2:
                    close_dates.sort()
                    mid = len(close_dates) // 2
                    first_half_gap = self._avg_gap_days(close_dates[:mid])
                    second_half_gap = self._avg_gap_days(close_dates[mid:])
                    if first_half_gap > 0 and second_half_gap > first_half_gap * 1.3:
                        signals.append(("declining_frequency", 25))
                    else:
                        signals.append(("stable_frequency", 0))

            invoices = self._invoice_by_account.get(aid, [])
            overdue_count = sum(1 for inv in invoices if inv.get("Status") in ("Overdue", "Past_Due", "Delinquent"))
            if overdue_count > 0:
                overdue_signal = min(overdue_count * 10, 30)
                signals.append(("overdue_invoices", overdue_signal))

            sentiments = self._sentiment_by_account.get(aid, [])
            negative_count = sum(1 for s in sentiments if s.get("Sentiment") in ("Negative", "Very Negative"))
            positive_count = sum(1 for s in sentiments if s.get("Sentiment") in ("Positive", "Very Positive"))
            if negative_count > positive_count and negative_count > 0:
                sentiment_signal = min(negative_count * 8, 25)
                signals.append(("negative_sentiment", sentiment_signal))
            elif positive_count > 0:
                signals.append(("positive_sentiment", -5))

            clv_info = self._clv_data.get(aid, {})
            recency_days = clv_info.get("recency_days", 365)
            if recency_days > 180:
                signals.append(("high_recency", min(int(recency_days / 15), 20)))

            seed = self._deterministic_seed(aid, "churn", 1)
            base_score = 20 + seed * 15

            signal_score = sum(s[1] for s in signals)
            raw_score = base_score + signal_score
            churn_score = max(0, min(100, round(raw_score)))

            churn_scores[aid] = {
                "churn_score": churn_score,
                "signals": signals,
                "overdue_invoices": overdue_count,
                "negative_sentiments": negative_count,
                "recency_days": recency_days,
            }

        self._churn_scores = churn_scores

        high_risk = sum(1 for d in churn_scores.values() if d["churn_score"] > 70)
        avg_score = sum(d["churn_score"] for d in churn_scores.values()) / max(len(churn_scores), 1)
        self._log("INFO", (
            f"Churn scored for {len(churn_scores)} accounts — "
            f"avg score: {avg_score:.1f}, high risk (>70): {high_risk}"
        ), "churn_prediction")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "churn_prediction", "completed",
                               len(churn_scores), len(churn_scores))

        return {
            "status": "completed",
            "accounts_scored": len(churn_scores),
            "avg_churn_score": round(avg_score, 1),
            "high_risk_count": high_risk,
        }

    # ─── Step 4: Wallet Share Analysis ───────────────────────────────────

    async def step_wallet_share_analysis(self) -> Dict[str, Any]:
        self._log("INFO", "Step 4: Wallet Share Analysis — estimating addressable wallet...", "wallet_share_analysis")

        if not self._account_map:
            return {"status": "error", "message": "No accounts loaded — run step 1 first"}

        wallet_data = {}
        for aid, account in self._account_map.items():
            annual_revenue = self._safe_float(account.get("Annual_Revenue", 0))
            if annual_revenue <= 0:
                seed = self._deterministic_seed(aid, "revenue", 2)
                annual_revenue = 500_000 + seed * 9_500_000

            industry = account.get("Industry", "Other") or "Other"
            industry_factor = INDUSTRY_WALLET_FACTOR.get(industry, 2.5)

            total_wallet = annual_revenue * industry_factor

            clv_info = self._clv_data.get(aid, {})
            our_revenue = clv_info.get("total_revenue", 0)
            if our_revenue <= 0:
                seed = self._deterministic_seed(aid, "wallet", 3)
                our_revenue = total_wallet * (0.05 + seed * 0.25)

            wallet_share = round((our_revenue / total_wallet) * 100, 2) if total_wallet > 0 else 0.0

            wallet_data[aid] = {
                "annual_revenue": round(annual_revenue, 2),
                "industry": industry,
                "industry_factor": industry_factor,
                "total_wallet": round(total_wallet, 2),
                "our_revenue": round(our_revenue, 2),
                "wallet_share": wallet_share,
            }

        self._wallet_data = wallet_data

        avg_share = sum(d["wallet_share"] for d in wallet_data.values()) / max(len(wallet_data), 1)
        self._log("INFO", (
            f"Wallet share computed for {len(wallet_data)} accounts — avg share: {avg_share:.1f}%"
        ), "wallet_share_analysis")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "wallet_share_analysis", "completed",
                               len(wallet_data), len(wallet_data))

        return {
            "status": "completed",
            "accounts_analyzed": len(wallet_data),
            "avg_wallet_share": round(avg_share, 2),
        }

    # ─── Step 5: Cross-Sell Scoring ──────────────────────────────────────

    async def step_cross_sell_scoring(self) -> Dict[str, Any]:
        self._log("INFO", "Step 5: Cross-Sell Scoring — identifying whitespace opportunities...", "cross_sell_scoring")

        if not self._account_map:
            return {"status": "error", "message": "No accounts loaded — run step 1 first"}

        opp_map = {}
        for opps_list in self._opp_by_account.values():
            for o in opps_list:
                oid = o.get("Opportunity_ID", "")
                if oid:
                    opp_map[oid] = o

        categories_by_account = defaultdict(set)
        for li in self._line_items:
            oid = li.get("Opportunity_ID", "")
            opp = opp_map.get(oid, {})
            aid = opp.get("Account_ID", "")
            if not aid:
                continue
            cat = opp.get("Product_Category", "")
            if not cat:
                pid = li.get("Product_ID", "")
                seed = self._deterministic_seed(pid, "cat", 0) if pid else 0.5
                cat = PRODUCT_CATEGORIES[int(seed * len(PRODUCT_CATEGORIES)) % len(PRODUCT_CATEGORIES)]
            categories_by_account[aid].add(cat)

        full_catalogue = set(PRODUCT_CATEGORIES)
        cross_sell_scores = {}

        for aid, account in self._account_map.items():
            purchased = categories_by_account.get(aid, set())
            missing = full_catalogue - purchased
            missing_count = len(missing)

            seed = self._deterministic_seed(aid, "cross_sell", 4)
            affinity_scores = {}
            for cat in missing:
                cat_seed = self._deterministic_seed(aid, cat, 5)
                affinity_scores[cat] = round(cat_seed * 100, 1)

            sorted_opportunities = sorted(affinity_scores.items(), key=lambda x: x[1], reverse=True)
            top_opportunities = sorted_opportunities[:5]

            cross_sell_score = round(
                (missing_count / max(len(full_catalogue), 1)) * 50 + seed * 50, 1
            )

            cross_sell_scores[aid] = {
                "purchased_categories": list(purchased),
                "missing_categories": list(missing),
                "cross_sell_count": missing_count,
                "top_opportunities": [{"category": c, "affinity": s} for c, s in top_opportunities],
                "cross_sell_score": min(cross_sell_score, 100),
            }

        self._cross_sell_scores = cross_sell_scores

        avg_score = sum(d["cross_sell_score"] for d in cross_sell_scores.values()) / max(len(cross_sell_scores), 1)
        total_opps = sum(d["cross_sell_count"] for d in cross_sell_scores.values())
        self._log("INFO", (
            f"Cross-sell scored for {len(cross_sell_scores)} accounts — "
            f"avg score: {avg_score:.1f}, total opportunities: {total_opps}"
        ), "cross_sell_scoring")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "cross_sell_scoring", "completed",
                               len(cross_sell_scores), len(cross_sell_scores))

        return {
            "status": "completed",
            "accounts_scored": len(cross_sell_scores),
            "avg_cross_sell_score": round(avg_score, 1),
            "total_cross_sell_opportunities": total_opps,
        }

    # ─── Step 6: Publish Results ─────────────────────────────────────────

    async def step_publish_results(self) -> Dict[str, Any]:
        self._log("INFO", "Step 6: Publish Results — generating KPIs, alerts, writing to S3...", "publish_results")

        if not self._account_map:
            return {"status": "error", "message": "No account data — run steps 1-5 first"}

        self._generate_alerts()
        self._compute_kpis()

        customer_results = self._build_customer_results()
        segment_summary = self._build_segment_summary(customer_results)
        revenue_summary = self._build_revenue_summary(customer_results)

        now = datetime.now(timezone.utc)

        results = {
            "customer_results": customer_results,
            "kpis": self._kpis,
            "alerts": self._alerts,
            "segment_summary": segment_summary,
            "revenue_summary": revenue_summary,
            "generated_at": now.isoformat(),
        }

        written = await self._write_to_s3(results)
        await self._push_to_simulator(customer_results, segment_summary, revenue_summary, now)

        self._log("INFO", (
            f"Published {len(customer_results)} customer profiles, {len(self._alerts)} alerts, "
            f"avg_clv=${self._kpis.get('avg_clv', 0):,.2f}, churn_risk={self._kpis.get('churn_risk_pct', 0):.1f}%"
        ), "publish_results")

        return {
            "status": "completed",
            "profiles_published": len(customer_results),
            "alerts_generated": len(self._alerts),
            "kpis": self._kpis,
            "s3_written": written,
            "segments": len(segment_summary),
            "regions": len(revenue_summary),
        }

    # ─── Helper: Build Customer Results ──────────────────────────────────

    def _build_customer_results(self) -> List[Dict]:
        results = []
        for aid, account in self._account_map.items():
            clv_info = self._clv_data.get(aid, {})
            churn_info = self._churn_scores.get(aid, {})
            wallet_info = self._wallet_data.get(aid, {})
            cross_sell_info = self._cross_sell_scores.get(aid, {})

            sentiments = self._sentiment_by_account.get(aid, [])
            sentiment_scores = [self._safe_float(s.get("Score", 50)) for s in sentiments]
            avg_sentiment = round(sum(sentiment_scores) / max(len(sentiment_scores), 1), 1)

            clv = clv_info.get("clv", 0)
            if clv >= 500_000:
                ltv_segment = "Platinum"
            elif clv >= 200_000:
                ltv_segment = "Gold"
            elif clv >= 50_000:
                ltv_segment = "Silver"
            else:
                ltv_segment = "Bronze"

            results.append({
                "account_id": aid,
                "name": account.get("Name", ""),
                "tier": account.get("Tier", "SMB"),
                "region": account.get("Region", "Central"),
                "clv": clv,
                "churn_score": churn_info.get("churn_score", 0),
                "wallet_share": wallet_info.get("wallet_share", 0),
                "sentiment_score": avg_sentiment,
                "cross_sell_count": cross_sell_info.get("cross_sell_count", 0),
                "ltv_segment": ltv_segment,
            })

        return results

    # ─── Helper: Build Segment Summary ───────────────────────────────────

    def _build_segment_summary(self, customer_results: List[Dict]) -> List[Dict]:
        by_tier = defaultdict(list)
        for cr in customer_results:
            by_tier[cr["tier"]].append(cr)

        summary = []
        for segment, customers in by_tier.items():
            count = len(customers)
            avg_clv = sum(c["clv"] for c in customers) / max(count, 1)
            avg_churn = sum(c["churn_score"] for c in customers) / max(count, 1)
            total_rev = sum(self._clv_data.get(c["account_id"], {}).get("total_revenue", 0) for c in customers)
            summary.append({
                "segment": segment,
                "customer_count": count,
                "avg_clv": round(avg_clv, 2),
                "avg_churn_risk": round(avg_churn, 1),
                "total_revenue": round(total_rev, 2),
            })

        return summary

    # ─── Helper: Build Revenue Summary ───────────────────────────────────

    def _build_revenue_summary(self, customer_results: List[Dict]) -> List[Dict]:
        by_region = defaultdict(list)
        for cr in customer_results:
            by_region[cr["region"]].append(cr)

        summary = []
        for region, customers in by_region.items():
            count = len(customers)
            total_rev = sum(self._clv_data.get(c["account_id"], {}).get("total_revenue", 0) for c in customers)
            avg_wallet = sum(c["wallet_share"] for c in customers) / max(count, 1)
            seed = self._deterministic_seed(region, "growth", 6)
            growth_pct = round(-5 + seed * 25, 1)
            summary.append({
                "region": region,
                "total_revenue": round(total_rev, 2),
                "customer_count": count,
                "avg_wallet_share": round(avg_wallet, 2),
                "growth_pct": growth_pct,
            })

        return summary

    # ─── Helper: Generate Alerts ─────────────────────────────────────────

    def _generate_alerts(self):
        alerts = []

        for aid, churn_info in self._churn_scores.items():
            if churn_info["churn_score"] > 70:
                account = self._account_map.get(aid, {})
                clv_info = self._clv_data.get(aid, {})
                alerts.append({
                    "type": "high_churn_risk",
                    "severity": "High",
                    "account_id": aid,
                    "account_name": account.get("Name", ""),
                    "churn_score": churn_info["churn_score"],
                    "clv_at_risk": clv_info.get("clv", 0),
                    "message": (
                        f"Account {account.get('Name', aid)} has churn score "
                        f"{churn_info['churn_score']}/100 with ${clv_info.get('clv', 0):,.0f} CLV at risk"
                    ),
                    "action": "Trigger retention workflow; schedule executive review",
                })

        for aid, sentiments in self._sentiment_by_account.items():
            negative = [s for s in sentiments if s.get("Sentiment") in ("Negative", "Very Negative")]
            if negative:
                account = self._account_map.get(aid, {})
                alerts.append({
                    "type": "declining_sentiment",
                    "severity": "Medium",
                    "account_id": aid,
                    "account_name": account.get("Name", ""),
                    "negative_count": len(negative),
                    "message": (
                        f"Account {account.get('Name', aid)} has {len(negative)} negative sentiment "
                        f"signals from {', '.join(set(s.get('Source', 'unknown') for s in negative))}"
                    ),
                    "action": "Review sentiment sources; notify customer success team",
                })

        for aid, wallet_info in self._wallet_data.items():
            clv_info = self._clv_data.get(aid, {})
            if clv_info.get("clv", 0) > 200_000 and wallet_info.get("wallet_share", 100) < 15:
                account = self._account_map.get(aid, {})
                cross_sell_info = self._cross_sell_scores.get(aid, {})
                alerts.append({
                    "type": "cross_sell_opportunity",
                    "severity": "Info",
                    "account_id": aid,
                    "account_name": account.get("Name", ""),
                    "wallet_share": wallet_info["wallet_share"],
                    "clv": clv_info["clv"],
                    "cross_sell_count": cross_sell_info.get("cross_sell_count", 0),
                    "message": (
                        f"High-value account {account.get('Name', aid)} (CLV ${clv_info['clv']:,.0f}) "
                        f"has only {wallet_info['wallet_share']:.1f}% wallet share with "
                        f"{cross_sell_info.get('cross_sell_count', 0)} cross-sell opportunities"
                    ),
                    "action": "Prioritize for cross-sell campaign; assign account development rep",
                })

        self._alerts = alerts

    # ─── Helper: Compute KPIs ────────────────────────────────────────────

    def _compute_kpis(self):
        if not self._account_map:
            self._kpis = {}
            return

        total_accounts = len(self._account_map)

        clv_values = [d["clv"] for d in self._clv_data.values()]
        avg_clv = sum(clv_values) / max(len(clv_values), 1)

        churn_values = [d["churn_score"] for d in self._churn_scores.values()]
        high_risk_count = sum(1 for s in churn_values if s > 70)
        churn_risk_pct = round((high_risk_count / max(total_accounts, 1)) * 100, 1)

        wallet_values = [d["wallet_share"] for d in self._wallet_data.values()]
        wallet_share_avg = sum(wallet_values) / max(len(wallet_values), 1)

        cross_sell_totals = [d["cross_sell_count"] for d in self._cross_sell_scores.values()]
        accounts_with_cross_sell = sum(1 for c in cross_sell_totals if c > 0)
        cross_sell_rate_pct = round((accounts_with_cross_sell / max(total_accounts, 1)) * 100, 1)

        sentiment_values = []
        for aid in self._account_map:
            sentiments = self._sentiment_by_account.get(aid, [])
            scores = [self._safe_float(s.get("Score", 50)) for s in sentiments]
            if scores:
                sentiment_values.append(sum(scores) / len(scores))
        avg_nps = round(sum(sentiment_values) / max(len(sentiment_values), 1), 1)

        revenue_values = [d.get("total_revenue", 0) for d in self._clv_data.values()]
        wallet_values_full = [d.get("our_revenue", 0) for d in self._wallet_data.values()]
        total_rev = sum(revenue_values)
        total_wallet_rev = sum(wallet_values_full) if wallet_values_full else total_rev
        profitability_avg = round(
            (total_rev / max(total_wallet_rev, 1)) * 100, 1
        ) if total_wallet_rev > 0 else 0.0

        self._kpis = {
            "avg_clv": round(avg_clv, 2),
            "churn_risk_pct": churn_risk_pct,
            "wallet_share_avg": round(wallet_share_avg, 2),
            "cross_sell_rate_pct": cross_sell_rate_pct,
            "avg_nps": avg_nps,
            "customer_profitability_avg": profitability_avg,
            "total_accounts": total_accounts,
            "high_churn_count": high_risk_count,
            "alerts_count": len(self._alerts),
            "alerts": list(self._alerts) if isinstance(self._alerts, list) else [],
        }

    # ─── Helper: Push to Simulator ───────────────────────────────────────

    async def _push_to_simulator(self, customer_results: List[Dict],
                                  segment_summary: List[Dict],
                                  revenue_summary: List[Dict],
                                  now: datetime):
        try:
            from src.apis.fdw_api import _simulators
            ext = _simulators.get("external")
            if not ext or not getattr(ext, "loaded", False):
                self._log("INFO", "External simulator not available — skipping simulator push", "publish_results")
                return

            await ext.write_table("external_sources", "C360_KPI_Snapshot", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                **self._kpis,
            }])

            await ext.write_table("external_sources", "C360_Customer_Result", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in customer_results
            ])

            await ext.write_table("external_sources", "C360_Alert", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                "total_alerts": len(self._alerts),
                "alerts": json.dumps(self._alerts, default=str),
            }])

            await ext.write_table("external_sources", "C360_Segment_Summary", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in segment_summary
            ])

            await ext.write_table("external_sources", "C360_Revenue_Summary", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in revenue_summary
            ])

            self._log("INFO", (
                f"Pushed to simulator: {len(customer_results)} customer profiles, "
                f"{len(segment_summary)} segment summaries, {len(revenue_summary)} revenue summaries, "
                f"KPIs + {len(self._alerts)} alerts"
            ), "publish_results")

            await self._ensure_c360_result_mapping_rules()

            try:
                save_result = await ext.save_to_s3()
                if save_result.get("success"):
                    self._log("INFO", (
                        f"Persisted simulator to S3 ({save_result.get('tables')} tables, "
                        f"{save_result.get('rows')} rows)"
                    ), "publish_results")
                    await self._broadcast_simulator_reload()
                else:
                    self._log("WARNING", f"S3 persist skipped: {save_result.get('message')}", "publish_results")
            except Exception as se:
                self._log("WARNING", f"Simulator S3 persist failed (non-fatal): {se}", "publish_results")

        except Exception as e:
            self._log("WARNING", f"Simulator push failed (non-fatal): {e}", "publish_results")

    async def _broadcast_simulator_reload(self):
        try:
            import aiohttp, os
            namespace = os.getenv("NAMESPACE", "nexus-ai-dev")
            svc = f"nexus-ai-dev-backend-svc.{namespace}.svc.cluster.local"
            reloaded = 0
            async with aiohttp.ClientSession() as session:
                for _ in range(6):
                    try:
                        async with session.post(
                            f"http://{svc}:8000/api/v1/external-simulator/reset",
                            timeout=aiohttp.ClientTimeout(total=5),
                        ) as resp:
                            if resp.status == 200:
                                reloaded += 1
                    except Exception:
                        pass
            if reloaded:
                self._log("INFO", f"Broadcast simulator reload ({reloaded} calls)", "publish_results")
        except Exception as e:
            self._log("WARNING", f"Simulator reload broadcast failed (non-fatal): {e}", "publish_results")

    async def _ensure_c360_result_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_by_entity = {r.virtual_entity: r for r in existing}

            result_entities = [
                "C360_KPI_Snapshot", "C360_Customer_Result", "C360_Alert",
                "C360_Segment_Summary", "C360_Revenue_Summary",
            ]

            from src.models.mapping_rule_models import (
                MappingRuleCreateRequest, MappingRuleUpdateRequest,
                MappingRuleSourceType, MappingRuleStatus, FieldMap,
            )
            created = 0
            activated = 0
            for entity in result_entities:
                existing_rule = existing_by_entity.get(entity)
                if existing_rule:
                    if existing_rule.status.value != "active":
                        await service.update(existing_rule.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
                        activated += 1
                    continue
                rule = MappingRuleCreateRequest(
                    name=f"C360 Result: {entity}",
                    virtual_entity=entity,
                    source_schema="external_sources",
                    source_table=entity,
                    source_system="external_sources",
                    source_type=MappingRuleSourceType.FDW,
                    field_maps=[],
                )
                resp = await service.create(rule)
                await service.update(resp.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
                created += 1
            if created or activated:
                self._log("INFO", (
                    f"Created {created}, activated {activated} VDL mapping rules for C360 result entities"
                ), "publish_results")
        except Exception as e:
            self._log("WARNING", f"C360 result mapping rules failed (non-fatal): {e}", "publish_results")

    # ─── Helper: Write to S3 ─────────────────────────────────────────────

    async def _write_to_s3(self, results: Dict) -> bool:
        if not self._s3:
            self._log("WARNING", "No S3 client configured — skipping S3 write", "publish_results")
            return False

        try:
            bucket = None
            if self._config:
                bucket = (
                    getattr(self._config, "s3_bucket", None)
                    or getattr(self._config, "stage_bucket", None)
                    or getattr(self._config, "s3_journey_reports_bucket", None)
                )
            if not bucket:
                import os
                bucket = os.getenv("STAGE_BUCKET", "") or os.getenv("S3_JOURNEY_REPORTS_BUCKET", "")
            if not bucket:
                self._log("WARNING", "No S3 bucket configured", "publish_results")
                return False

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            prefix = f"customer-360/{self.journey_id}/{timestamp}"

            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/customer-results.json",
                Body=json.dumps(results["customer_results"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/c360-kpis.json",
                Body=json.dumps(results["kpis"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/c360-alerts.json",
                Body=json.dumps(results["alerts"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/segment-summary.json",
                Body=json.dumps(results["segment_summary"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/revenue-summary.json",
                Body=json.dumps(results["revenue_summary"], default=str),
                ContentType="application/json",
            )
            self._log("INFO", f"Written to s3://{bucket}/{prefix}/", "publish_results")
            return True
        except Exception as e:
            self._log("WARNING", f"S3 write failed: {e}", "publish_results")
            return False

    # ─── Utility ─────────────────────────────────────────────────────────

    @staticmethod
    def _avg_gap_days(dates: List[datetime]) -> float:
        if len(dates) < 2:
            return 0
        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        return sum(gaps) / len(gaps)
