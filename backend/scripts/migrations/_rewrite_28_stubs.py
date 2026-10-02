#!/usr/bin/env python3
"""
One-shot helper: rewrites the 28 stub automation YAMLs per the section-32
mapping table in the AI Automation Framework plan.

Each file gets:
  - Cursor-style header band (passes lint_yaml_headers).
  - status: active, real tags + KPIs.
  - stages: resolve -> diagnose -> decide -> act -> [notify ->] verify
  - Tools resolved from the section-31 catalogue.
  - record_outcome in the verify stage.

Idempotent: rewrites the file every run with a deterministic body.

Usage:
    python3 scripts/migrations/_rewrite_28_stubs.py
    python3 scripts/migrations/_rewrite_28_stubs.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_AUTO_ROOT = _BACKEND_ROOT / "enterprise-knowledge" / "automation"


# ---------------------------------------------------------------------------
# Section-32 mapping table (one row per stub).
# Each row is fully self-describing so the generator can render the YAML.
# ---------------------------------------------------------------------------

ROWS: List[Dict[str, Any]] = [
    # customer-360
    {
        "file": "customer-360/at_risk_save.yaml",
        "use_case_id": "c360.at_risk_save",
        "title": "At-Risk Account Save Play",
        "solution_id": "customer-360",
        "headline": "Save plays for low-health accounts.",
        "description": (
            "When health-score drops below the threshold, run a coordinated save "
            "play: open a CSM outreach task, attach a tailored discount, and "
            "follow up via email."
        ),
        "tags": ["c360", "save-play", "health"],
        "kpi_impact": ["churn_rate", "save_rate", "expansion_arr"],
        "consumes": ["Customer", "Activity_Log", "Support_Case"],
        "produces": ["Task", "Oracle_AR_Promotion", "Email_Campaign_Send", "O2C_Outcome_Tracker", "Audit_Event"],
        "primary_analyzer": "find_churning_customers",
        "primary_analyzer_params": {"horizon_days": 60, "top_n": 25},
        "diagnose_analyzer": "score_customer_lifetime_value",
        "diagnose_params": {},
        "decide_summary": "Pick the right save play (CSM call vs discount vs both) per CLV tier.",
        "act_steps": [
            {"tool": "assign_csm_outreach", "approval": False,
             "params": {"account_id": "${item.customer_id}", "subject": "Save play -- low health-score outreach", "outreach_type": "csm_outreach"}},
            {"tool": "apply_promo_discount", "approval": True,
             "params": {"name": "Save Play Discount", "discount_pct": 10.0, "applies_to": {"segment": "at_risk"}}},
        ],
        "notify_steps": [
            {"tool": "send_email_campaign", "approval": False,
             "params": {"subject": "We value your partnership -- exclusive offer", "recipients": "${stage.resolve.list.results}"}},
        ],
        "verify_kpi": "churn_rate",
        "verify_kpi_before": "${stage.resolve.list.count}",
        "verify_kpi_after": "${stage.verify.requery.count}",
    },
    {
        "file": "customer-360/upsell_nba.yaml",
        "use_case_id": "c360.upsell_nba",
        "title": "Next-Best Upsell Action",
        "solution_id": "customer-360",
        "headline": "Next-best upsell action for high-fit accounts.",
        "description": (
            "Identify upsell candidates and route a tailored CSM outreach task "
            "with the recommended SKU. Email follow-up consolidates the play."
        ),
        "tags": ["c360", "upsell", "nba"],
        "kpi_impact": ["expansion_arr", "win_rate"],
        "consumes": ["Customer", "Opportunity", "Account"],
        "produces": ["Task", "Email_Campaign_Send", "O2C_Outcome_Tracker", "Audit_Event"],
        "primary_analyzer": "find_upsell_candidates",
        "primary_analyzer_params": {"top_n": 25},
        "diagnose_analyzer": "score_customer_lifetime_value",
        "decide_summary": "Pair each customer with the highest-fit upsell SKU.",
        "act_steps": [
            {"tool": "assign_csm_outreach", "approval": False,
             "params": {"account_id": "${item.customer_id}", "subject": "Recommended upsell -- ${item.recommended_sku}", "outreach_type": "upsell_play"}},
        ],
        "notify_steps": [
            {"tool": "send_email_campaign", "approval": False,
             "params": {"subject": "A recommendation for your account", "recipients": "${stage.resolve.list.results}"}},
        ],
        "verify_kpi": "expansion_arr",
        "verify_kpi_before": 0,
        "verify_kpi_after": "${stage.verify.requery.count}",
    },
    {
        "file": "customer-360/churn_prevention.yaml",
        "use_case_id": "c360.churn_prevention",
        "title": "Churn Prevention Outreach",
        "solution_id": "customer-360",
        "headline": "Pre-empt churn with a retention bundle and outreach.",
        "description": (
            "When churn risk crosses the threshold, attach a retention bundle and "
            "push a multi-channel outreach (WhatsApp + email)."
        ),
        "tags": ["c360", "churn", "prevention"],
        "kpi_impact": ["churn_rate", "save_rate"],
        "consumes": ["Customer", "Activity_Log", "Support_Case"],
        "produces": ["Oracle_AR_Promotion", "WhatsApp_Campaign_Send", "Email_Campaign_Send", "O2C_Outcome_Tracker", "Audit_Event"],
        "primary_analyzer": "find_churning_customers",
        "primary_analyzer_params": {"horizon_days": 90, "top_n": 25},
        "diagnose_analyzer": "score_customer_lifetime_value",
        "decide_summary": "Pick a personalised retention bundle per customer.",
        "act_steps": [
            {"tool": "apply_promo_discount", "approval": True,
             "params": {"name": "Churn Prevention Bundle", "discount_pct": 15.0, "applies_to": {"segment": "at_risk"}}},
        ],
        "notify_steps": [
            {"tool": "send_whatsapp_campaign", "approval": True,
             "params": {"template_id": "churn_prev_q2", "recipients": "${stage.resolve.list.results}"}},
            {"tool": "send_email_campaign", "approval": False,
             "params": {"subject": "We'd love to keep you", "recipients": "${stage.resolve.list.results}"}},
        ],
        "verify_kpi": "churn_rate",
        "verify_kpi_before": "${stage.resolve.list.count}",
        "verify_kpi_after": "${stage.verify.requery.count}",
    },
    {
        "file": "customer-360/renewal_negotiation.yaml",
        "use_case_id": "c360.renewal_negotiation",
        "title": "Renewal Negotiation Play",
        "solution_id": "customer-360",
        "headline": "Renewal negotiation with terms + discount levers.",
        "description": (
            "Score each renewal by CLV, propose updated terms (or a renewal "
            "discount), and write the outcome back to AR."
        ),
        "tags": ["c360", "renewal", "negotiation"],
        "kpi_impact": ["renewal_rate", "renewal_arr"],
        "consumes": ["Customer", "AR_Invoice", "Opportunity"],
        "produces": ["Oracle_AR_Promotion", "O2C_Action_Log", "O2C_Outcome_Tracker", "Audit_Event"],
        "primary_analyzer": "score_customer_lifetime_value",
        "primary_analyzer_params": {"top_n": 25},
        "diagnose_analyzer": None,
        "decide_summary": "Per-account: terms change, discount, or status quo based on CLV.",
        "act_steps": [
            {"tool": "update_account_terms", "approval": True,
             "params": {"customer_id": "${item.customer_id}", "payment_terms": "Net_45"}},
            {"tool": "apply_promo_discount", "approval": True,
             "params": {"name": "Renewal Loyalty Discount", "discount_pct": 7.5, "applies_to": {"segment": "renewal"}}},
        ],
        "notify_steps": [],
        "verify_kpi": "renewal_arr",
        "verify_kpi_before": 0,
        "verify_kpi_after": "${stage.verify.requery.count}",
    },

    # inventory-optimization
    {
        "file": "inventory-optimization/expiry_risk_mitigation.yaml",
        "use_case_id": "io.expiry_risk_mitigation",
        "title": "Expiry Risk Mitigation",
        "solution_id": "inventory-optimization",
        "headline": "Move / discount near-expiry stock before write-off.",
        "description": (
            "Identify near-expiry stock, bundle SKUs into clearance kits, attach "
            "a discount, and notify channel partners."
        ),
        "tags": ["inventory", "expiry", "liquidation"],
        "kpi_impact": ["expiry_writeoff_usd", "sell_through_rate"],
        "consumes": ["Material", "Inventory_Position", "Batch"],
        "produces": ["Oracle_Kit", "Oracle_AR_Promotion", "Warehouse_Transfer", "Email_Campaign_Send", "Audit_Event"],
        "primary_analyzer": "find_excess_inventory_near_expiry",
        "primary_analyzer_params": {"horizon_days": 60},
        "diagnose_analyzer": "project_inventory_writeoff",
        "diagnose_params": {"horizon_days": 90},
        "decide_summary": "Decide bundle / discount / inter-plant transfer per SKU.",
        "act_steps": [
            {"tool": "bundle_skus_for_liquidation", "approval": False,
             "params": {"name": "Near-Expiry Clearance", "components": "${stage.decide.choose_action.bundle}"}},
            {"tool": "apply_promo_discount", "approval": True,
             "params": {"name": "Clearance Discount", "discount_pct": 25.0, "applies_to": {"segment": "clearance"}}},
            {"tool": "create_transfer_order", "approval": False,
             "params": {"from_plant": "${item.plant}", "to_plant": "PLT-N1", "material_id": "${item.material_id}", "quantity": "${item.qty}"}},
        ],
        "notify_steps": [
            {"tool": "send_email_campaign", "approval": False,
             "params": {"subject": "Clearance bundle available", "recipients": "${stage.resolve.list.results}"}},
        ],
        "verify_kpi": "expiry_writeoff_usd",
        "verify_kpi_before": "${stage.diagnose.diag.projected_writeoff_usd}",
        "verify_kpi_after": "${stage.verify.requery.projected_writeoff_usd}",
    },
    {
        "file": "inventory-optimization/reorder_auto_trigger.yaml",
        "use_case_id": "io.reorder_auto_trigger",
        "title": "Reorder Auto-Trigger",
        "solution_id": "inventory-optimization",
        "headline": "Auto-trigger reorders when stock drops below safety.",
        "description": (
            "Compare current inventory positions against safety stock. Where "
            "shortfalls exist, create a transfer order or escalate to PO approval."
        ),
        "tags": ["inventory", "reorder", "safety-stock"],
        "kpi_impact": ["stockout_rate", "fill_rate"],
        "consumes": ["Material", "Inventory_Position"],
        "produces": ["Warehouse_Transfer", "Audit_Event"],
        "primary_analyzer": "get_inventory_position",
        "primary_analyzer_params": {"material_id": "${item.material_id}"},
        "diagnose_analyzer": None,
        "decide_summary": "Decide transfer vs new PO based on lead-time vs urgency.",
        "act_steps": [
            {"tool": "create_transfer_order", "approval": False,
             "params": {"from_plant": "PLT-N1", "to_plant": "${item.plant_id}", "material_id": "${item.material_id}", "quantity": "${item.shortfall_qty}"}},
        ],
        "notify_steps": [],
        "verify_kpi": "stockout_rate",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "inventory-optimization/slow_mover_liquidation.yaml",
        "use_case_id": "io.slow_mover_liquidation",
        "title": "Slow-Mover Liquidation",
        "solution_id": "inventory-optimization",
        "headline": "Liquidate slow-moving SKUs as discounted bundles.",
        "description": (
            "Rank SKUs by velocity, bundle the slowest movers, and discount the "
            "bundle. Notify channel partners via email."
        ),
        "tags": ["inventory", "slow-movers", "liquidation"],
        "kpi_impact": ["sell_through_rate", "obsolete_writeoff_usd"],
        "consumes": ["Material", "Inventory_Position"],
        "produces": ["Oracle_Kit", "Oracle_AR_Promotion", "Email_Campaign_Send", "Audit_Event"],
        "primary_analyzer": "find_slow_movers",
        "primary_analyzer_params": {"velocity_threshold": 0.5, "top_n": 50},
        "diagnose_analyzer": "project_inventory_writeoff",
        "decide_summary": "Decide bundle composition + discount tier per SKU group.",
        "act_steps": [
            {"tool": "bundle_skus_for_liquidation", "approval": False,
             "params": {"name": "Slow-Mover Bundle", "components": "${stage.decide.choose_bundle.components}"}},
            {"tool": "apply_promo_discount", "approval": True,
             "params": {"name": "Slow-Mover Clearance", "discount_pct": 30.0, "applies_to": {"segment": "clearance"}}},
        ],
        "notify_steps": [
            {"tool": "send_email_campaign", "approval": False,
             "params": {"subject": "Limited-time clearance bundle", "recipients": "${stage.resolve.list.results}"}},
        ],
        "verify_kpi": "obsolete_writeoff_usd",
        "verify_kpi_before": "${stage.diagnose.diag.projected_writeoff_usd}",
        "verify_kpi_after": "${stage.verify.requery.projected_writeoff_usd}",
    },
    {
        "file": "inventory-optimization/inter_plant_rebalance.yaml",
        "use_case_id": "io.inter_plant_rebalance",
        "title": "Inter-Plant Rebalance",
        "solution_id": "inventory-optimization",
        "headline": "Rebalance excess stock across plants.",
        "description": (
            "Identify plants with excess near-expiry stock and move to plants "
            "with deficits via warehouse transfer orders."
        ),
        "tags": ["inventory", "rebalance"],
        "kpi_impact": ["fill_rate", "expiry_writeoff_usd"],
        "consumes": ["Material", "Inventory_Position"],
        "produces": ["Warehouse_Transfer", "Audit_Event"],
        "primary_analyzer": "find_excess_inventory_near_expiry",
        "primary_analyzer_params": {"horizon_days": 60},
        "diagnose_analyzer": None,
        "decide_summary": "Pair surplus plant -> deficit plant per material.",
        "act_steps": [
            {"tool": "create_transfer_order", "approval": False,
             "params": {"from_plant": "${item.plant}", "to_plant": "${item.target_plant}", "material_id": "${item.material_id}", "quantity": "${item.qty}"}},
        ],
        "notify_steps": [],
        "verify_kpi": "fill_rate",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },

    # demand-forecasting
    {
        "file": "demand-forecasting/forecast_override_validation.yaml",
        "use_case_id": "df.forecast_override_validation",
        "title": "Forecast Override Validation",
        "solution_id": "demand-forecasting",
        "headline": "Validate manual sales-team forecast overrides.",
        "description": (
            "Score each pending sales-team override against bias signals. If "
            "the override aligns with bias correction, accept it; otherwise "
            "create the override row pending sales-manager review."
        ),
        "tags": ["forecast", "override", "validation"],
        "kpi_impact": ["forecast_accuracy_pct", "mape_pct"],
        "consumes": ["Forecast", "Actual_Sales", "Forecast_Override"],
        "produces": ["Forecast_Override", "Audit_Event"],
        "primary_analyzer": "find_forecast_bias",
        "primary_analyzer_params": {"top_n": 25},
        "diagnose_analyzer": None,
        "decide_summary": "Approve auto-fix overrides; route others to sales manager.",
        "act_steps": [
            {"tool": "create_forecast_override", "approval": False,
             "params": {"product_id": "${item.product_id}", "region": "${item.region}", "period": "2026-W22", "override_qty": 0, "justification": "bias-correction"}},
        ],
        "notify_steps": [],
        "verify_kpi": "forecast_accuracy_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "demand-forecasting/promo_lift_replan.yaml",
        "use_case_id": "df.promo_lift_replan",
        "title": "Promo Lift Re-Plan",
        "solution_id": "demand-forecasting",
        "headline": "Re-plan demand after a promo lift event.",
        "description": (
            "Simulate the impact of an upcoming promotion on the forecast and "
            "create override rows so downstream planning reflects the lift."
        ),
        "tags": ["forecast", "promo", "replan"],
        "kpi_impact": ["forecast_accuracy_pct", "promo_uplift_pct"],
        "consumes": ["Forecast"],
        "produces": ["Forecast_Override", "Audit_Event"],
        "primary_analyzer": "simulate_promotion_impact",
        "primary_analyzer_params": {"sku": "${context.sku}", "region": "${context.region}", "promotion_type": "Discount", "discount_pct": 15},
        "diagnose_analyzer": None,
        "decide_summary": "Approve override magnitudes per SKU x region pair.",
        "act_steps": [
            {"tool": "create_forecast_override", "approval": False,
             "params": {"product_id": "${context.sku}", "region": "${context.region}", "period": "${context.period}", "override_qty": "${stage.resolve.list.expected_volume_lift}", "justification": "promo-lift"}},
        ],
        "notify_steps": [],
        "verify_kpi": "forecast_accuracy_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "demand-forecasting/stockout_prevention.yaml",
        "use_case_id": "df.stockout_prevention",
        "title": "Stockout Prevention Trigger",
        "solution_id": "demand-forecasting",
        "headline": "Pre-empt stockouts on volatile SKUs.",
        "description": (
            "Find high-CoV SKUs, project shortfall, and trigger transfer "
            "orders + slack alert to ops."
        ),
        "tags": ["forecast", "stockout", "trigger"],
        "kpi_impact": ["stockout_rate", "fill_rate"],
        "consumes": ["Forecast", "Sales_Order"],
        "produces": ["Warehouse_Transfer", "Slack_Message", "Audit_Event"],
        "primary_analyzer": "find_volatile_skus",
        "primary_analyzer_params": {"top_n": 25},
        "diagnose_analyzer": None,
        "decide_summary": "Decide expedite-from / expedite-to plant per volatile SKU.",
        "act_steps": [
            {"tool": "create_transfer_order", "approval": False,
             "params": {"from_plant": "PLT-N1", "to_plant": "PLT-N3", "material_id": "${item.product_id}", "quantity": 100}},
        ],
        "notify_steps": [
            {"tool": "send_slack_alert", "approval": False,
             "params": {"channel": "#df-ops", "message": "Stockout prevention triggered", "severity": "warning"}},
        ],
        "verify_kpi": "stockout_rate",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "demand-forecasting/bias_investigation.yaml",
        "use_case_id": "df.bias_investigation",
        "title": "Forecast Bias Investigation",
        "solution_id": "demand-forecasting",
        "headline": "Investigate persistent forecast bias.",
        "description": (
            "Surface SKUs with persistent over- or under-forecast bias and "
            "create override rows to correct the trend."
        ),
        "tags": ["forecast", "bias", "investigation"],
        "kpi_impact": ["mape_pct", "bias_pct"],
        "consumes": ["Forecast", "Actual_Sales"],
        "produces": ["Forecast_Override", "Audit_Event"],
        "primary_analyzer": "find_forecast_bias",
        "primary_analyzer_params": {"top_n": 25},
        "diagnose_analyzer": None,
        "decide_summary": "Decide override magnitude + direction per SKU x region.",
        "act_steps": [
            {"tool": "create_forecast_override", "approval": False,
             "params": {"product_id": "${item.product_id}", "region": "${item.region}", "period": "2026-W22", "override_qty": 0, "justification": "bias-correction"}},
        ],
        "notify_steps": [],
        "verify_kpi": "bias_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },

    # supply-chain-risk
    {
        "file": "supply-chain-risk/disruption_mitigation.yaml",
        "use_case_id": "scr.disruption_mitigation",
        "title": "Disruption Mitigation Playbook",
        "solution_id": "supply-chain-risk",
        "headline": "Mitigate active lane / supplier disruption.",
        "description": (
            "Identify disrupted lanes, expedite alternative routes, and "
            "post a Slack alert to the SCR ops team."
        ),
        "tags": ["scr", "disruption", "mitigation"],
        "kpi_impact": ["on_time_delivery_pct", "expedite_cost_usd"],
        "consumes": ["Shipment", "Lane_Health"],
        "produces": ["Warehouse_Transfer", "Slack_Message", "Audit_Event"],
        "primary_analyzer": "find_disrupted_lanes",
        "primary_analyzer_params": {"top_n": 20},
        "diagnose_analyzer": None,
        "decide_summary": "Decide route swap + expedite priority per lane.",
        "act_steps": [
            {"tool": "create_transfer_order", "approval": False,
             "params": {"from_plant": "PLT-N1", "to_plant": "PLT-N3", "material_id": "MAT-NA", "quantity": 1}},
            {"tool": "request_expedited_fulfillment", "approval": False,
             "params": {"delivery_id": "${item.lane_id}", "reason": "Lane disruption"}},
        ],
        "notify_steps": [
            {"tool": "send_slack_alert", "approval": False,
             "params": {"channel": "#scr-ops", "message": "Lane disruption mitigated", "severity": "warning"}},
        ],
        "verify_kpi": "on_time_delivery_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "supply-chain-risk/tier2_stress_response.yaml",
        "use_case_id": "scr.tier2_stress_response",
        "title": "Tier-2 Vendor Stress Response",
        "solution_id": "supply-chain-risk",
        "headline": "Respond when a tier-2 vendor shows stress signals.",
        "description": (
            "Score tier-2 vendor disruption risk and block any vendor "
            "exceeding the threshold; notify procurement on Slack."
        ),
        "tags": ["scr", "tier2", "vendor-stress"],
        "kpi_impact": ["supplier_risk_score", "stockout_rate"],
        "consumes": ["Supplier", "Geopolitical_Event"],
        "produces": ["Oracle_Supplier", "Slack_Message", "Audit_Event"],
        "primary_analyzer": "score_supplier_disruption_risk",
        "primary_analyzer_params": {"top_n": 20},
        "diagnose_analyzer": None,
        "decide_summary": "Decide block + alternative vendor per stressed supplier.",
        "act_steps": [
            {"tool": "block_supplier_orders", "approval": True,
             "params": {"supplier_id": "${item.vendor_id}", "block": True, "reason": "Tier-2 stress threshold"}},
        ],
        "notify_steps": [
            {"tool": "send_slack_alert", "approval": False,
             "params": {"channel": "#scr-ops", "message": "Tier-2 vendor blocked due to stress", "severity": "critical"}},
        ],
        "verify_kpi": "supplier_risk_score",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "supply-chain-risk/single_source_derisk.yaml",
        "use_case_id": "scr.single_source_derisk",
        "title": "Single-Source De-Risking",
        "solution_id": "supply-chain-risk",
        "headline": "De-risk single-sourced items by approving alternatives.",
        "description": (
            "Identify items with sole-supplier exposure and approve alternative "
            "vendor POs to diversify supply."
        ),
        "tags": ["scr", "single-source", "derisk"],
        "kpi_impact": ["supplier_diversification_pct"],
        "consumes": ["Supplier", "Material"],
        "produces": ["Oracle_Purchase_Order", "Audit_Event"],
        "primary_analyzer": "score_supplier_disruption_risk",
        "primary_analyzer_params": {"top_n": 20},
        "diagnose_analyzer": None,
        "decide_summary": "Pick best alternative vendor per single-sourced material.",
        "act_steps": [
            {"tool": "approve_purchase_order", "approval": True,
             "params": {"po_id": "PO-NEW-${item.vendor_id}", "status": "Approved"}},
        ],
        "notify_steps": [],
        "verify_kpi": "supplier_diversification_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "supply-chain-risk/geopolitical_hedge.yaml",
        "use_case_id": "scr.geopolitical_hedge",
        "title": "Geopolitical Hedge Action",
        "solution_id": "supply-chain-risk",
        "headline": "Block exposed vendors and notify ops on geopolitical risk.",
        "description": (
            "When geopolitical risk score crosses the threshold, block exposed "
            "vendors and notify the SCR ops team."
        ),
        "tags": ["scr", "geopolitical", "hedge"],
        "kpi_impact": ["supplier_risk_score"],
        "consumes": ["Supplier", "Geopolitical_Event"],
        "produces": ["Oracle_Supplier", "Slack_Message", "Audit_Event"],
        "primary_analyzer": "score_supplier_disruption_risk",
        "primary_analyzer_params": {"top_n": 25},
        "diagnose_analyzer": None,
        "decide_summary": "Pick blocks + alternative regions per exposed vendor.",
        "act_steps": [
            {"tool": "block_supplier_orders", "approval": True,
             "params": {"supplier_id": "${item.vendor_id}", "block": True, "reason": "Geopolitical risk"}},
        ],
        "notify_steps": [
            {"tool": "send_slack_alert", "approval": False,
             "params": {"channel": "#scr-ops", "message": "Geopolitical hedge action triggered", "severity": "critical"}},
        ],
        "verify_kpi": "supplier_risk_score",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },

    # procurement-analytics
    {
        "file": "procurement-analytics/maverick_spend_capture.yaml",
        "use_case_id": "pa.maverick_spend_capture",
        "title": "Maverick Spend Capture",
        "solution_id": "procurement-analytics",
        "headline": "Catch and convert off-contract spend.",
        "description": (
            "Surface vendors / categories with off-contract spend, then "
            "block the worst offenders or route them to PO approval."
        ),
        "tags": ["procurement", "maverick", "capture"],
        "kpi_impact": ["off_contract_spend_pct"],
        "consumes": ["Invoice_Line", "Contract"],
        "produces": ["Oracle_Supplier", "Oracle_Purchase_Order", "Audit_Event"],
        "primary_analyzer": "find_maverick_spend",
        "primary_analyzer_params": {"period": "last_quarter"},
        "diagnose_analyzer": None,
        "decide_summary": "Block worst offenders; route the rest to PO approval.",
        "act_steps": [
            {"tool": "block_supplier_orders", "approval": True,
             "params": {"supplier_id": "${item.vendor_id}", "block": True, "reason": "Maverick spend"}},
        ],
        "notify_steps": [],
        "verify_kpi": "off_contract_spend_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "procurement-analytics/three_way_match_pa.yaml",
        "use_case_id": "pa.three_way_match",
        "title": "3-Way Match (Procurement)",
        "solution_id": "procurement-analytics",
        "headline": "Procurement-side 3-way match resolution.",
        "description": (
            "Run order-delivery-invoice match for procurement; create credit "
            "notes / status updates for any mismatches."
        ),
        "tags": ["procurement", "three-way-match"],
        "kpi_impact": ["match_rate_pct", "invoice_dispute_count"],
        "consumes": ["Opportunity", "Delivery_Document", "AR_Invoice"],
        "produces": ["Oracle_AR_Invoice", "Oracle_AR_Credit_Note", "Audit_Event"],
        "primary_analyzer": "match_order_delivery_invoice",
        "primary_analyzer_params": {"opportunity_id": "${context.opportunity_id}"},
        "diagnose_analyzer": None,
        "decide_summary": "Decide credit-note vs status-update vs auto-resolve per mismatch.",
        "act_steps": [
            {"tool": "update_invoice_status", "approval": True,
             "params": {"invoice_id": "${context.invoice_id}", "new_status": "Under_Review"}},
            {"tool": "process_credit_note", "approval": True,
             "params": {"invoice_id": "${context.invoice_id}", "amount": 0, "reason": "3-way match adjustment"}},
        ],
        "notify_steps": [],
        "verify_kpi": "match_rate_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "procurement-analytics/vendor_risk_escalation.yaml",
        "use_case_id": "pa.vendor_risk_escalation",
        "title": "Vendor Risk Escalation",
        "solution_id": "procurement-analytics",
        "headline": "Escalate (and block) high-risk vendors.",
        "description": (
            "Score vendor disruption risk and block any vendor crossing the "
            "threshold; notify procurement on Slack."
        ),
        "tags": ["procurement", "vendor-risk"],
        "kpi_impact": ["supplier_risk_score"],
        "consumes": ["Supplier", "Geopolitical_Event"],
        "produces": ["Oracle_Supplier", "Slack_Message", "Audit_Event"],
        "primary_analyzer": "score_supplier_disruption_risk",
        "primary_analyzer_params": {"top_n": 20},
        "diagnose_analyzer": None,
        "decide_summary": "Decide block thresholds per vendor risk band.",
        "act_steps": [
            {"tool": "block_supplier_orders", "approval": True,
             "params": {"supplier_id": "${item.vendor_id}", "block": True, "reason": "Vendor risk escalation"}},
        ],
        "notify_steps": [
            {"tool": "send_slack_alert", "approval": False,
             "params": {"channel": "#procurement-ops", "message": "Vendor risk escalated -- supplier blocked", "severity": "critical"}},
        ],
        "verify_kpi": "supplier_risk_score",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "procurement-analytics/contract_renegotiation_trigger.yaml",
        "use_case_id": "pa.contract_renegotiation_trigger",
        "title": "Contract Re-negotiation Trigger",
        "solution_id": "procurement-analytics",
        "headline": "Trigger renegotiation on under-performing contracts.",
        "description": (
            "Identify renegotiation candidates and update vendor terms in line "
            "with the negotiation outcome."
        ),
        "tags": ["procurement", "contract", "renegotiation"],
        "kpi_impact": ["contract_savings_usd"],
        "consumes": ["Contract", "Spend_History"],
        "produces": ["Oracle_AR_Customer", "Audit_Event"],
        "primary_analyzer": "find_renegotiation_candidates",
        "primary_analyzer_params": {"top_n": 25},
        "diagnose_analyzer": None,
        "decide_summary": "Decide updated terms per contract.",
        "act_steps": [
            {"tool": "update_account_terms", "approval": True,
             "params": {"customer_id": "${item.contract_id}", "payment_terms": "Net_45"}},
        ],
        "notify_steps": [],
        "verify_kpi": "contract_savings_usd",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },

    # production-quality
    {
        "file": "production-quality/oee_recovery.yaml",
        "use_case_id": "pq.oee_recovery",
        "title": "OEE Recovery",
        "solution_id": "production-quality",
        "headline": "Recover declining OEE with a maintenance schedule.",
        "description": (
            "Detect OEE decline per line and schedule predictive maintenance "
            "on the equipment driving the decline."
        ),
        "tags": ["pq", "oee", "recovery"],
        "kpi_impact": ["oee_pct"],
        "consumes": ["Production_Order", "Downtime_Event"],
        "produces": ["Maintenance_Order", "Slack_Message", "Audit_Event"],
        "primary_analyzer": "score_oee_decline",
        "primary_analyzer_params": {"top_n": 20},
        "diagnose_analyzer": "predict_equipment_failure",
        "diagnose_params": {"horizon_days": 30},
        "decide_summary": "Pick maintenance type + scheduled window per line.",
        "act_steps": [
            {"tool": "schedule_predictive_maintenance", "approval": False,
             "params": {"equipment_id": "${item.line_id}", "scheduled_for": "2026-05-30T08:00:00Z", "maintenance_type": "Predictive"}},
        ],
        "notify_steps": [
            {"tool": "send_slack_alert", "approval": False,
             "params": {"channel": "#pq-ops", "message": "OEE recovery scheduled", "severity": "warning"}},
        ],
        "verify_kpi": "oee_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "production-quality/capa_lifecycle.yaml",
        "use_case_id": "pq.capa_lifecycle",
        "title": "CAPA Lifecycle Play",
        "solution_id": "production-quality",
        "headline": "Open CAPA workflows for recurring root causes.",
        "description": (
            "Cluster recent quality events by root cause and open a CAPA for "
            "each persistent recurrence."
        ),
        "tags": ["pq", "capa", "lifecycle"],
        "kpi_impact": ["capa_close_rate_pct"],
        "consumes": ["Quality_Event", "CAPA"],
        "produces": ["CAPA", "Audit_Event"],
        "primary_analyzer": "find_capa_recurrence",
        "primary_analyzer_params": {"horizon_days": 180},
        "diagnose_analyzer": None,
        "decide_summary": "Decide severity + owner per recurring root cause.",
        "act_steps": [
            {"tool": "open_capa_workflow", "approval": True,
             "params": {"subject": "${item.description}", "severity": "high"}},
        ],
        "notify_steps": [],
        "verify_kpi": "capa_close_rate_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "production-quality/predictive_maintenance.yaml",
        "use_case_id": "pq.predictive_maintenance",
        "title": "Predictive Maintenance Schedule",
        "solution_id": "production-quality",
        "headline": "Schedule predictive maintenance for at-risk equipment.",
        "description": (
            "Predict equipment failure probability and schedule maintenance "
            "for any asset above the risk threshold."
        ),
        "tags": ["pq", "maintenance", "predictive"],
        "kpi_impact": ["unplanned_downtime_hours"],
        "consumes": ["Equipment", "Sensor_Reading"],
        "produces": ["Maintenance_Order", "Audit_Event"],
        "primary_analyzer": "predict_equipment_failure",
        "primary_analyzer_params": {"horizon_days": 30, "top_n": 20},
        "diagnose_analyzer": None,
        "decide_summary": "Decide priority + schedule per asset.",
        "act_steps": [
            {"tool": "schedule_predictive_maintenance", "approval": False,
             "params": {"equipment_id": "${item.equipment_id}", "scheduled_for": "2026-05-30T08:00:00Z", "maintenance_type": "Predictive"}},
        ],
        "notify_steps": [],
        "verify_kpi": "unplanned_downtime_hours",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "production-quality/quality_hold_investigation.yaml",
        "use_case_id": "pq.quality_hold_investigation",
        "title": "Quality Hold + Investigation",
        "solution_id": "production-quality",
        "headline": "Hold suspect batches and open a CAPA investigation.",
        "description": (
            "When quality recurrence is detected, place a hold on the affected "
            "batch and open a CAPA workflow."
        ),
        "tags": ["pq", "quality-hold", "capa"],
        "kpi_impact": ["batch_hold_count", "capa_open_count"],
        "consumes": ["Quality_Event", "CAPA", "Batch"],
        "produces": ["Batch_Master", "CAPA", "Slack_Message", "Audit_Event"],
        "primary_analyzer": "find_capa_recurrence",
        "primary_analyzer_params": {"horizon_days": 90},
        "diagnose_analyzer": None,
        "decide_summary": "Decide hold scope + CAPA severity per recurrence.",
        "act_steps": [
            {"tool": "hold_batch", "approval": True,
             "params": {"batch_id": "${context.batch_id}", "material_id": "${context.material_id}", "reason": "Quality recurrence detected"}},
            {"tool": "open_capa_workflow", "approval": True,
             "params": {"subject": "${item.description}", "severity": "high"}},
        ],
        "notify_steps": [
            {"tool": "send_slack_alert", "approval": False,
             "params": {"channel": "#pq-ops", "message": "Quality hold placed", "severity": "critical"}},
        ],
        "verify_kpi": "batch_hold_count",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },

    # esg-sustainability
    {
        "file": "esg-sustainability/co2_pathway_correction.yaml",
        "use_case_id": "esg.co2_pathway_correction",
        "title": "CO2 Pathway Correction",
        "solution_id": "esg-sustainability",
        "headline": "Correct facility CO2 pathway breaches.",
        "description": (
            "Identify facilities breaching their CO2 target and block high-"
            "emission suppliers; approve alternative low-emission POs."
        ),
        "tags": ["esg", "co2", "pathway"],
        "kpi_impact": ["scope1_co2_t", "co2_target_breach_pct"],
        "consumes": ["Facility", "Emission_Reading"],
        "produces": ["Oracle_Supplier", "Audit_Event"],
        "primary_analyzer": "find_co2_breach_facilities",
        "primary_analyzer_params": {"top_n": 25},
        "diagnose_analyzer": None,
        "decide_summary": "Decide which suppliers to block and which alternatives to approve.",
        "act_steps": [
            {"tool": "block_supplier_orders", "approval": True,
             "params": {"supplier_id": "${item.facility_id}", "block": True, "reason": "CO2 pathway breach"}},
        ],
        "notify_steps": [],
        "verify_kpi": "scope1_co2_t",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "esg-sustainability/compliance_breach_response.yaml",
        "use_case_id": "esg.compliance_breach_response",
        "title": "Compliance Breach Response",
        "solution_id": "esg-sustainability",
        "headline": "Open CAPA + alert ops on compliance breaches.",
        "description": (
            "Identify open compliance breaches and open a CAPA workflow for "
            "each high-severity finding; notify ESG ops on Slack."
        ),
        "tags": ["esg", "compliance", "breach"],
        "kpi_impact": ["compliance_breach_open_count"],
        "consumes": ["Compliance_Check"],
        "produces": ["CAPA", "Slack_Message", "Audit_Event"],
        "primary_analyzer": "find_compliance_breaches",
        "primary_analyzer_params": {"severity": "high"},
        "diagnose_analyzer": None,
        "decide_summary": "Decide CAPA severity + owner per breach.",
        "act_steps": [
            {"tool": "open_capa_workflow", "approval": True,
             "params": {"subject": "${item.summary}", "severity": "high"}},
        ],
        "notify_steps": [
            {"tool": "send_slack_alert", "approval": False,
             "params": {"channel": "#esg-ops", "message": "Compliance breach -- CAPA opened", "severity": "critical"}},
        ],
        "verify_kpi": "compliance_breach_open_count",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "esg-sustainability/initiative_roi_review.yaml",
        "use_case_id": "esg.initiative_roi_review",
        "title": "Initiative ROI Review",
        "solution_id": "esg-sustainability",
        "headline": "Review ROI of running ESG initiatives and record outcomes.",
        "description": (
            "Score initiative impact via CLV adapter; record outcomes so the "
            "next planning cycle prioritises high-ROI initiatives."
        ),
        "tags": ["esg", "roi", "review"],
        "kpi_impact": ["esg_initiative_roi_pct"],
        "consumes": ["AR_Invoice", "Customer"],
        "produces": ["O2C_Outcome_Tracker", "Audit_Event"],
        "primary_analyzer": "score_customer_lifetime_value",
        "primary_analyzer_params": {"top_n": 25},
        "diagnose_analyzer": None,
        "decide_summary": "Decide which initiatives to scale, sustain, or sunset.",
        "act_steps": [],
        "notify_steps": [],
        "verify_kpi": "esg_initiative_roi_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
    {
        "file": "esg-sustainability/vendor_esg_onboarding.yaml",
        "use_case_id": "esg.vendor_esg_onboarding",
        "title": "Vendor ESG Onboarding",
        "solution_id": "esg-sustainability",
        "headline": "Onboard vendors with ESG compliance gating.",
        "description": (
            "Run compliance check on the prospective vendor. On fail, block "
            "the vendor; on pass, update terms to reflect onboarding."
        ),
        "tags": ["esg", "vendor", "onboarding"],
        "kpi_impact": ["vendor_esg_compliant_pct"],
        "consumes": ["Compliance_Check"],
        "produces": ["Oracle_Supplier", "Oracle_AR_Customer", "Audit_Event"],
        "primary_analyzer": "find_compliance_breaches",
        "primary_analyzer_params": {"top_n": 25},
        "diagnose_analyzer": None,
        "decide_summary": "Decide block vs onboard based on breach severity.",
        "act_steps": [
            {"tool": "block_supplier_orders", "approval": True,
             "params": {"supplier_id": "${item.vendor_id}", "block": True, "reason": "ESG onboarding fail"}},
            {"tool": "update_account_terms", "approval": True,
             "params": {"customer_id": "${item.vendor_id}", "payment_terms": "Net_60"}},
        ],
        "notify_steps": [],
        "verify_kpi": "vendor_esg_compliant_pct",
        "verify_kpi_before": 0,
        "verify_kpi_after": 0,
    },
]


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def _wrap(text: str, width: int = 72) -> List[str]:
    out: List[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            out.append("")
            continue
        line = ""
        for word in paragraph.split():
            if line and len(line) + 1 + len(word) > width:
                out.append(line)
                line = word
            else:
                line = (line + " " + word).strip()
        if line:
            out.append(line)
    return out


def _render_params(params: Dict[str, Any], indent: int) -> str:
    if not params:
        return " " * indent + "params: {}\n"
    lines = [" " * indent + "params:"]
    for k, v in params.items():
        if isinstance(v, str):
            # Quote so YAML treats interpolation expressions safely.
            quoted = v.replace('"', '\\"')
            lines.append(f"{' ' * (indent + 2)}{k}: \"{quoted}\"")
        elif isinstance(v, bool):
            lines.append(f"{' ' * (indent + 2)}{k}: {str(v).lower()}")
        elif isinstance(v, (int, float)):
            lines.append(f"{' ' * (indent + 2)}{k}: {v}")
        elif isinstance(v, dict):
            inline = ", ".join(f"{kk}: {vv}" for kk, vv in v.items())
            lines.append(f"{' ' * (indent + 2)}{k}: {{ {inline} }}")
        else:
            lines.append(f"{' ' * (indent + 2)}{k}: {v}")
    return "\n".join(lines) + "\n"


def _render(row: Dict[str, Any]) -> str:
    out: List[str] = []

    # ----- header band ----------------------------------------------------
    out.append("# ============================================================================")
    out.append(f"# Automation: {row['title']}")
    out.append(f"# Solution:   {row['solution_id']}")
    out.append(f"# Use case:   {row['use_case_id']}")
    out.append("# ----------------------------------------------------------------------------")
    out.append("# What this playbook does:")
    for line in _wrap(row['headline'] + ' ' + row['description'], 72):
        out.append(f"#   {line}" if line else "#")
    out.append("#")
    out.append("# Stages:")
    out.append(f"#   - resolve  -> {row['primary_analyzer']}")
    if row.get("diagnose_analyzer"):
        out.append(f"#   - diagnose -> {row['diagnose_analyzer']}")
    out.append("#   - decide   -> LLM step (no tool binding)")
    if row.get("act_steps"):
        out.append(f"#   - act      -> {', '.join(s['tool'] for s in row['act_steps'])}")
    if row.get("notify_steps"):
        out.append(f"#   - notify   -> {', '.join(s['tool'] for s in row['notify_steps'])}")
    out.append("#   - verify   -> re-run analyzer + record_outcome")
    out.append("#")
    out.append(f"# KPIs:       {', '.join(row['kpi_impact'])}")
    approvals = []
    for s in row.get("act_steps", []) + row.get("notify_steps", []):
        if s.get("approval"):
            approvals.append(s["tool"])
    if approvals:
        out.append(f"# Approvals:  {', '.join(approvals)}")
    out.append("# ============================================================================")
    out.append("")

    # ----- body -----------------------------------------------------------
    out.append(f"use_case_id: {row['use_case_id']}")
    out.append(f"title: {row['title']}")
    out.append(f"solution_id: {row['solution_id']}")
    desc = row['headline'] + ' ' + row['description']
    out.append("description: >")
    for line in _wrap(desc, 72):
        out.append(f"  {line}")
    out.append("status: active")
    out.append(f"tags: [{', '.join(row['tags'])}]")
    out.append(f"kpi_impact: [{', '.join(row['kpi_impact'])}]")
    out.append(f"consumes_entities: [{', '.join(row['consumes'])}]")
    out.append(f"produces_entities: [{', '.join(row['produces'])}]")
    out.append("")
    out.append("stages:")

    order = 1

    # resolve
    out.append(f"  - stage_id: resolve")
    out.append(f"    name: Resolve")
    out.append(f"    order: {order}"); order += 1
    out.append(f"    description: Identify the entities in scope.")
    out.append(f"    steps:")
    out.append(f"      - step_id: list")
    out.append(f"        name: List Candidates")
    out.append(f"        order: 1")
    out.append(f"        tool: {row['primary_analyzer']}")
    out.append(_render_params(row.get('primary_analyzer_params') or {}, 8).rstrip("\n"))

    # diagnose
    if row.get('diagnose_analyzer'):
        out.append(f"  - stage_id: diagnose")
        out.append(f"    name: Diagnose")
        out.append(f"    order: {order}"); order += 1
        out.append(f"    description: Score / decompose the candidates.")
        out.append(f"    steps:")
        out.append(f"      - step_id: diag")
        out.append(f"        name: Score / Project")
        out.append(f"        order: 1")
        out.append(f"        tool: {row['diagnose_analyzer']}")
        out.append(_render_params(row.get('diagnose_params') or {}, 8).rstrip("\n"))

    # decide
    out.append(f"  - stage_id: decide")
    out.append(f"    name: Decide")
    out.append(f"    order: {order}"); order += 1
    out.append(f"    description: |")
    for line in _wrap(row['decide_summary'] + ' LLM-only step; no tool binding because the reasoning is the action.', 70):
        out.append(f"      {line}")
    out.append(f"    steps:")
    out.append(f"      - step_id: choose_action")
    out.append(f"        name: Choose Action Per Candidate")
    out.append(f"        order: 1")

    # act
    if row.get('act_steps'):
        out.append(f"  - stage_id: act")
        out.append(f"    name: Act")
        out.append(f"    order: {order}"); order += 1
        out.append(f"    steps:")
        for i, step in enumerate(row['act_steps'], start=1):
            sid = f"act_{i}"
            out.append(f"      - step_id: {sid}")
            out.append(f"        name: {step['tool'].replace('_', ' ').title()}")
            out.append(f"        order: {i}")
            if step.get('approval'):
                out.append(f"        requires_approval: true")
            out.append(f"        tool: {step['tool']}")
            out.append(_render_params(step.get('params') or {}, 8).rstrip("\n"))

    # notify
    if row.get('notify_steps'):
        out.append(f"  - stage_id: notify")
        out.append(f"    name: Notify")
        out.append(f"    order: {order}"); order += 1
        out.append(f"    steps:")
        for i, step in enumerate(row['notify_steps'], start=1):
            sid = f"notify_{i}"
            out.append(f"      - step_id: {sid}")
            out.append(f"        name: {step['tool'].replace('_', ' ').title()}")
            out.append(f"        order: {i}")
            if step.get('approval'):
                out.append(f"        requires_approval: true")
            out.append(f"        tool: {step['tool']}")
            out.append(_render_params(step.get('params') or {}, 8).rstrip("\n"))

    # verify
    out.append(f"  - stage_id: verify")
    out.append(f"    name: Verify")
    out.append(f"    order: {order}"); order += 1
    out.append(f"    description: Re-query and write Outcome_Tracker row.")
    out.append(f"    steps:")
    out.append(f"      - step_id: requery")
    out.append(f"        name: Re-Run Analyzer")
    out.append(f"        order: 1")
    out.append(f"        tool: {row['primary_analyzer']}")
    out.append(_render_params(row.get('primary_analyzer_params') or {}, 8).rstrip("\n"))
    out.append(f"      - step_id: write_outcome")
    out.append(f"        name: Append Outcome Tracker")
    out.append(f"        order: 2")
    out.append(f"        tool: record_outcome")
    out.append(f"        params:")
    out.append(f"          action_id: \"${{context.run_id}}\"")
    out.append(f"          kpi_name: {row['verify_kpi']}")
    before = row['verify_kpi_before']
    after = row['verify_kpi_after']
    if isinstance(before, str):
        out.append(f"          kpi_before: \"{before}\"")
    else:
        out.append(f"          kpi_before: {before}")
    if isinstance(after, str):
        out.append(f"          kpi_after:  \"{after}\"")
    else:
        out.append(f"          kpi_after:  {after}")

    return "\n".join(out) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    written = 0
    for row in ROWS:
        target = _AUTO_ROOT / row["file"]
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
        body = _render(row)
        if args.dry_run:
            print(f"  would-write {target.relative_to(_BACKEND_ROOT)}")
        else:
            target.write_text(body, encoding="utf-8")
            print(f"  wrote {target.relative_to(_BACKEND_ROOT)}")
        written += 1

    print(f"\nrewrite_28_stubs: rows={len(ROWS)} written={written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
