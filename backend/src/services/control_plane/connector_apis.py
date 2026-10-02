"""
Connector API registry.

Each entry is the canonical contract for one mutation against a target
system (Oracle ERP / SAP / SFDC / External). ReAct tools reference these
by ``api_id`` so the indexer can wire ``(TOOL_BINDING)-[:CALLS_API]->
(CONNECTOR_API)`` edges in the AGE graph and the diagnostic can verify
that every step's tool actually has a backing API.

Today every entry routes to a simulator write endpoint
(``POST/PATCH /api/v1/simulator/...``); the same shape will route to
real Oracle / SAP / SFDC in production once the storage mode flips.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ConnectorAPISpec:
    api_id: str
    target_system: str  # oracle | sap | sfdc | external
    operation: str  # "<METHOD> <PATH>", e.g. "PATCH /api/v1/simulator/sfdc/accounts/{id}/credit-hold"
    description: str
    request_schema: Dict[str, Any] = field(default_factory=dict)
    response_schema: Dict[str, Any] = field(default_factory=dict)
    simulator_writeback: bool = True
    risk_level: str = "low_risk_write"
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Catalogue - keep additions alphabetical within each system block.
# ---------------------------------------------------------------------------

_GLOBAL_CONNECTOR_APIS: Dict[str, ConnectorAPISpec] = {}


def _reg(spec: ConnectorAPISpec) -> None:
    if spec.api_id in _GLOBAL_CONNECTOR_APIS:
        return
    _GLOBAL_CONNECTOR_APIS[spec.api_id] = spec


# Oracle ERP --------------------------------------------------------------

_reg(ConnectorAPISpec(
    api_id="oracle.invoice.status.set",
    target_system="oracle",
    operation="PATCH /api/v1/simulator/oracle-erp/invoices/{invoice_id}",
    description="Update an Oracle AR invoice status (e.g. Open -> Paid / Disputed / Under_Review).",
    request_schema={"invoice_id": "string", "status": "string", "new_status": "string", "reason": "string?"},
    response_schema={"invoice_id": "string", "previous_status": "string", "status": "string"},
    risk_level="high_risk_write",
    tags=["o2c", "ar", "invoice"],
))
_reg(ConnectorAPISpec(
    api_id="oracle.credit_note.create",
    target_system="oracle",
    operation="POST /api/v1/simulator/oracle-erp/credit-notes",
    description="Create an AR credit note for an invoice.",
    request_schema={"customer_id": "string", "invoice_id": "string", "amount": "number", "reason": "string"},
    response_schema={"credit_note_id": "string", "amount": "number"},
    risk_level="high_risk_write",
    tags=["o2c", "ar", "credit-note"],
))
_reg(ConnectorAPISpec(
    api_id="oracle.payment.record",
    target_system="oracle",
    operation="POST /api/v1/simulator/oracle-erp/payments",
    description="Record a customer payment against one or more invoices.",
    request_schema={"customer_id": "string", "invoice_id": "string", "amount": "number", "payment_method": "string"},
    response_schema={"payment_id": "string"},
    risk_level="low_risk_write",
    tags=["o2c", "ar", "payment"],
))
_reg(ConnectorAPISpec(
    api_id="oracle.invoice.discount.offer",
    target_system="oracle",
    operation="PATCH /api/v1/simulator/oracle-erp/invoices/{invoice_id}/early-pay-discount",
    description="Attach an early-pay discount offer to an open invoice.",
    request_schema={"invoice_id": "string", "discount_pct": "number", "expires_in_days": "integer"},
    response_schema={"invoice_id": "string", "discount_pct": "number"},
    risk_level="high_risk_write",
    tags=["o2c", "ar", "discount"],
))
_reg(ConnectorAPISpec(
    api_id="oracle.customer.terms.set",
    target_system="oracle",
    operation="PATCH /api/v1/simulator/oracle-erp/ar-customers/{customer_id}",
    description="Change a customer's payment terms (e.g. Net_60 -> Net_30 for high-risk accounts).",
    request_schema={"customer_id": "string", "payment_terms": "string"},
    response_schema={"customer_id": "string", "payment_terms": "string"},
    risk_level="high_risk_write",
    tags=["o2c", "ar", "terms"],
))
_reg(ConnectorAPISpec(
    api_id="oracle.purchase_order.approve",
    target_system="oracle",
    operation="PATCH /api/v1/simulator/oracle-erp/purchase-orders/{po_id}",
    description="Approve / cancel an Oracle Purchase Order.",
    request_schema={"po_id": "string", "status": "string"},
    response_schema={"po_id": "string", "status": "string"},
    risk_level="high_risk_write",
    tags=["procurement", "po"],
))
# Phase 3 - Oracle additions for retain-risky-customers / liquidation /
# supplier-block plays.
_reg(ConnectorAPISpec(
    api_id="oracle.promotion.create",
    target_system="oracle",
    operation="POST /api/v1/simulator/oracle-erp/promotions",
    description=(
        "Create an AR promotion / discount offer (used by Retain Risky "
        "Customers and Slow-Mover Liquidation playbooks)."
    ),
    request_schema={
        "promo_code": "string?", "name": "string", "discount_pct": "number",
        "applies_to": "object?", "customer_id": "string?",
        "valid_from": "string?", "valid_to": "string?",
        "max_redemptions": "integer?",
    },
    response_schema={"promo_id": "string", "promo_code": "string", "customer_id": "string?"},
    risk_level="high_risk_write",
    tags=["c360", "promotion", "discount"],
))
_reg(ConnectorAPISpec(
    api_id="oracle.kit.create",
    target_system="oracle",
    operation="POST /api/v1/simulator/oracle-erp/kits",
    description=(
        "Bundle SKUs into a single sellable kit (used by inventory "
        "liquidation / expiry-mitigation playbooks)."
    ),
    request_schema={
        "kit_sku": "string?", "name": "string",
        "components": "array<object{sku, quantity}>",
        "list_price": "number?", "discount_pct": "number?",
    },
    response_schema={"kit_id": "string", "kit_sku": "string"},
    risk_level="low_risk_write",
    tags=["inventory", "kit", "liquidation"],
))
_reg(ConnectorAPISpec(
    api_id="oracle.supplier.block",
    target_system="oracle",
    operation="PATCH /api/v1/simulator/oracle-erp/suppliers/{supplier_id}",
    description=(
        "Block / unblock a supplier from new POs (used by maverick-spend "
        "capture, supplier-risk escalation, and ESG breach response)."
    ),
    request_schema={
        "supplier_id": "string", "block": "boolean", "reason": "string?",
        "block_until": "string?",
    },
    response_schema={"supplier_id": "string", "status": "string"},
    risk_level="high_risk_write",
    tags=["procurement", "supplier", "block"],
))


# SAP S/4HANA -------------------------------------------------------------

_reg(ConnectorAPISpec(
    api_id="sap.delivery.expedite",
    target_system="sap",
    operation="PATCH /api/v1/simulator/sap/deliveries/{delivery_id}",
    description="Mark a delivery as expedited (Priority -> Critical) and short-pick if needed.",
    request_schema={"delivery_id": "string", "priority": "string", "reason": "string?"},
    response_schema={"delivery_id": "string", "priority": "string"},
    risk_level="low_risk_write",
    tags=["o2c", "sap", "delivery"],
))
_reg(ConnectorAPISpec(
    api_id="sap.warehouse_transfer.create",
    target_system="sap",
    operation="POST /api/v1/simulator/sap/warehouse-transfers",
    description="Create a stock transfer between two plants.",
    request_schema={"from_plant": "string", "to_plant": "string", "material_id": "string", "quantity": "integer"},
    response_schema={"transfer_id": "string", "status": "string"},
    risk_level="low_risk_write",
    tags=["inventory", "sap", "transfer"],
))
_reg(ConnectorAPISpec(
    api_id="sap.batch.hold",
    target_system="sap",
    operation="PATCH /api/v1/simulator/sap/batches/{batch_id}/hold",
    description="Place or release a quality hold on a batch.",
    request_schema={"batch_id": "string", "hold": "boolean", "reason": "string?", "material_id": "string?"},
    response_schema={"batch_id": "string", "status": "string"},
    risk_level="high_risk_write",
    tags=["pq", "quality", "batch"],
))
_reg(ConnectorAPISpec(
    api_id="sap.production_order.update",
    target_system="sap",
    operation="PATCH /api/v1/simulator/sap/production-orders/{production_order_id}",
    description="Update a production order's status, quantity, or shift assignment.",
    request_schema={"production_order_id": "string", "status": "string?", "quantity": "integer?", "shift_id": "string?"},
    response_schema={"production_order_id": "string"},
    risk_level="high_risk_write",
    tags=["pq", "production"],
))
_reg(ConnectorAPISpec(
    api_id="sap.material_plant.reorder",
    target_system="sap",
    operation="PATCH /api/v1/simulator/sap/material-plants/{material_id}",
    description="Update reorder point / safety stock for a material+plant.",
    request_schema={"material_id": "string", "plant_id": "string", "safety_stock": "integer?", "reorder_point": "integer?"},
    response_schema={"material_id": "string", "plant_id": "string"},
    risk_level="low_risk_write",
    tags=["inventory", "sap"],
))
# Phase 3 - SAP additions for production-quality CAPA + predictive
# maintenance plays.
_reg(ConnectorAPISpec(
    api_id="sap.capa.open",
    target_system="sap",
    operation="POST /api/v1/simulator/sap/capa",
    description=(
        "Open a Corrective-And-Preventive-Action workflow record (used "
        "by CAPA-lifecycle, quality-hold-investigation, and compliance-"
        "breach-response playbooks)."
    ),
    request_schema={
        "subject": "string", "severity": "string",
        "trigger_event_id": "string?", "owner": "string?",
        "linked_entity_type": "string?", "linked_entity_id": "string?",
    },
    response_schema={"capa_id": "string", "status": "string"},
    risk_level="high_risk_write",
    tags=["pq", "capa", "quality"],
))
_reg(ConnectorAPISpec(
    api_id="sap.maintenance.schedule",
    target_system="sap",
    operation="POST /api/v1/simulator/sap/maintenance-orders",
    description=(
        "Schedule a predictive-maintenance work order for a piece of "
        "equipment (used by OEE recovery and predictive-maintenance "
        "playbooks)."
    ),
    request_schema={
        "equipment_id": "string", "scheduled_for": "string",
        "maintenance_type": "string", "estimated_hours": "number?",
        "priority": "string?", "reason": "string?",
    },
    response_schema={"maintenance_order_id": "string"},
    risk_level="low_risk_write",
    tags=["pq", "maintenance", "predictive"],
))


# Salesforce --------------------------------------------------------------

_reg(ConnectorAPISpec(
    api_id="sfdc.account.credit_hold.set",
    target_system="sfdc",
    operation="PATCH /api/v1/simulator/sfdc/accounts/{account_id}/credit-hold",
    description="Place or release a credit hold on a customer account.",
    request_schema={"account_id": "string", "hold": "boolean", "reason": "string?", "approved_by": "string?", "new_credit_limit": "number?", "justification": "string?"},
    response_schema={"account_id": "string", "account_status": "string"},
    risk_level="high_risk_write",
    tags=["o2c", "c360", "credit-hold"],
))
_reg(ConnectorAPISpec(
    api_id="sfdc.case.create",
    target_system="sfdc",
    operation="POST /api/v1/simulator/sfdc/cases",
    description="Open a Case (dispute, complaint, escalation).",
    request_schema={"account_id": "string", "subject": "string", "description": "string", "priority": "string", "opportunity_id": "string?", "invoice_id": "string?"},
    response_schema={"case_id": "string"},
    risk_level="low_risk_write",
    tags=["o2c", "c360", "case"],
))
_reg(ConnectorAPISpec(
    api_id="sfdc.opportunity.update",
    target_system="sfdc",
    operation="PATCH /api/v1/simulator/sfdc/opportunities/{opportunity_id}",
    description="Update opportunity stage / amount / close date.",
    request_schema={"opportunity_id": "string", "stage": "string?", "amount": "number?", "close_date": "string?"},
    response_schema={"opportunity_id": "string"},
    risk_level="high_risk_write",
    tags=["c360", "sales"],
))
_reg(ConnectorAPISpec(
    api_id="sfdc.account.churn_risk.set",
    target_system="sfdc",
    operation="PATCH /api/v1/simulator/sfdc/accounts/{account_id}/health",
    description="Update account health bucket / churn flag.",
    request_schema={"account_id": "string", "health_bucket": "string?", "churn_date": "string?", "churn_reason": "string?"},
    response_schema={"account_id": "string"},
    risk_level="low_risk_write",
    tags=["c360", "churn"],
))
_reg(ConnectorAPISpec(
    api_id="sfdc.forecast_override.create",
    target_system="sfdc",
    operation="POST /api/v1/simulator/sfdc/forecast-overrides",
    description="Create a manual Forecast_Override row (sales team adjustment to AI demand forecast).",
    request_schema={"product_id": "string", "region": "string", "period": "string",
                    "override_qty": "integer", "justification": "string"},
    response_schema={"override_id": "string"},
    risk_level="low_risk_write",
    tags=["forecast", "sfdc", "override"],
))
# Phase 3 - SFDC addition for CSM outreach play.
_reg(ConnectorAPISpec(
    api_id="sfdc.task.create_csm_outreach",
    target_system="sfdc",
    operation="POST /api/v1/simulator/sfdc/tasks",
    description=(
        "Create a CSM outreach Task on an account / opportunity (used by "
        "Retain Risky Customers, At-Risk Save, and Upsell NBA playbooks)."
    ),
    request_schema={
        "account_id": "string", "subject": "string",
        "description": "string?", "priority": "string?",
        "due_date": "string?", "owner_user_id": "string?",
        "outreach_type": "string?",
    },
    response_schema={"task_id": "string"},
    risk_level="low_risk_write",
    tags=["c360", "csm", "task"],
))


# External (notifications, audit, side-effects) ---------------------------

_reg(ConnectorAPISpec(
    api_id="external.dunning_notice.create",
    target_system="external",
    operation="POST /api/v1/simulator/external/dunning-notices",
    description="Send a dunning notice (email/letter/escalation).",
    request_schema={"invoice_id": "string", "level": "string", "customer_id": "string", "days_overdue": "integer"},
    response_schema={"notice_id": "string"},
    risk_level="low_risk_write",
    tags=["o2c", "dunning"],
))
_reg(ConnectorAPISpec(
    api_id="external.audit_event.create",
    target_system="external",
    operation="POST /api/v1/simulator/external/audit-events",
    description="Append an audit-trail entry recording an automation action.",
    request_schema={"actor": "string", "verb": "string", "target": "string", "payload": "object?", "action_type": "string?", "target_id": "string?", "status": "string?"},
    response_schema={"event_id": "string"},
    risk_level="read_only",
    tags=["audit"],
))
_reg(ConnectorAPISpec(
    api_id="external.alert.create",
    target_system="external",
    operation="POST /api/v1/simulator/external/alerts",
    description="Create an operational alert visible in the solution Monitor view.",
    request_schema={"prefix": "string", "severity": "string", "title": "string", "message": "string", "entity_id": "string?", "opportunity_id": "string?", "sla_pct": "number?"},
    response_schema={"alert_id": "string"},
    risk_level="low_risk_write",
    tags=["alert"],
))
_reg(ConnectorAPISpec(
    api_id="external.outcome.write",
    target_system="external",
    operation="POST /api/v1/simulator/external/outcomes",
    description="Append an Outcome_Tracker row recording before/after KPI delta + $ value attributed.",
    request_schema={"prefix": "string", "action_id": "string", "kpi_name": "string", "kpi_before": "number", "kpi_after": "number"},
    response_schema={"outcome_id": "string"},
    risk_level="read_only",
    tags=["outcome"],
))
# Phase 3 - External notification channels for retain / outreach plays.
# These route to simulator endpoints in dev; real channel wiring is out
# of scope for v1 (plan section 13).
_reg(ConnectorAPISpec(
    api_id="external.whatsapp.send_campaign",
    target_system="external",
    operation="POST /api/v1/simulator/external/whatsapp",
    description=(
        "Send a personalized WhatsApp campaign batch to a recipient list "
        "with templated message body (used by Retain Risky Customers and "
        "Churn Prevention playbooks)."
    ),
    request_schema={
        "campaign_id": "string?", "template_id": "string",
        "recipients": "array<object{customer_id, phone, vars?}>",
        "message_body": "string?", "actor": "string?",
    },
    response_schema={"campaign_id": "string", "queued": "integer"},
    risk_level="low_risk_write",
    tags=["notify", "whatsapp", "campaign"],
))
_reg(ConnectorAPISpec(
    api_id="external.email.send_campaign",
    target_system="external",
    operation="POST /api/v1/simulator/external/email",
    description=(
        "Send an email campaign batch (fallback / opt-out channel for "
        "WhatsApp; also used by liquidation and renewal playbooks)."
    ),
    request_schema={
        "campaign_id": "string?", "subject": "string",
        "recipients": "array<object{customer_id, email, vars?}>",
        "body_html": "string?", "body_text": "string?",
        "actor": "string?",
    },
    response_schema={"campaign_id": "string", "queued": "integer"},
    risk_level="low_risk_write",
    tags=["notify", "email", "campaign"],
))
_reg(ConnectorAPISpec(
    api_id="external.slack.post_message",
    target_system="external",
    operation="POST /api/v1/simulator/external/slack",
    description=(
        "Post an operational alert to a Slack channel (used by "
        "supply-chain-risk, OEE-recovery, quality-hold playbooks)."
    ),
    request_schema={
        "channel": "string", "title": "string?", "message": "string",
        "severity": "string?", "actor": "string?",
    },
    response_schema={"message_ts": "string"},
    risk_level="low_risk_write",
    tags=["notify", "slack", "alert"],
))


# TPM (Trade CPQ - sell side) ---------------------------------------------

_reg(ConnectorAPISpec(
    api_id="tpm.quote.create",
    target_system="tpm",
    operation="POST /api/v1/tpm-simulator/quotes",
    description=(
        "Create a Draft Quote_Header plus initial Quote_Line for an account. "
        "Called by the create_quote ReAct tool."
    ),
    request_schema={
        "account_id": "string", "channel": "string?", "material_query": "string?",
        "target_materials": "array<string>?", "qty": "integer?",
        "discount_pct": "number?", "validity_days": "integer?",
    },
    response_schema={"quote_id": "string", "header": "object", "lines": "array<object>"},
    risk_level="low_risk_write",
    tags=["cpq-sell", "quote", "write"],
))
_reg(ConnectorAPISpec(
    api_id="tpm.quote.promotion.apply",
    target_system="tpm",
    operation="POST /api/v1/tpm-simulator/quotes/{quote_id}/promotions",
    description=(
        "Overlay a Salesforce Campaign as a Quote_Promotion on an existing "
        "quote; enforces the 25% stacking cap from pricing-discount-policy."
    ),
    request_schema={"quote_id": "string", "campaign_id": "string"},
    response_schema={"quote_id": "string", "promotion_id": "string"},
    risk_level="low_risk_write",
    tags=["cpq-sell", "promotion", "write"],
))
_reg(ConnectorAPISpec(
    api_id="tpm.quote.approval.route",
    target_system="tpm",
    operation="PATCH /api/v1/tpm-simulator/quotes/{quote_id}/approval",
    description=(
        "Compute and persist the approval chain on a quote per "
        "cpq-quote-approval-policy. Auto-approves when within tier max."
    ),
    request_schema={"quote_id": "string"},
    response_schema={"quote_id": "string", "approval_chain": "array<object>", "status": "string"},
    risk_level="high_risk_write",
    tags=["cpq-sell", "approval", "write"],
))
_reg(ConnectorAPISpec(
    api_id="tpm.quote.convert_to_order",
    target_system="tpm",
    operation="PATCH /api/v1/tpm-simulator/quotes/{quote_id}/convert",
    description=(
        "Transition an Approved quote to Won_Converted and emit the kickoff "
        "event for quote-to-order materialization in Salesforce."
    ),
    request_schema={"quote_id": "string"},
    response_schema={"quote_id": "string", "new_status": "string"},
    risk_level="high_risk_write",
    tags=["cpq-sell", "convert", "write"],
))


# Sourcing (Sourcing CPQ - buy side) --------------------------------------

_reg(ConnectorAPISpec(
    api_id="sourcing.rfx.create",
    target_system="sourcing",
    operation="POST /api/v1/sourcing-simulator/rfx-events",
    description="Create a sourcing RFx_Event for a given spend category and buyer plants.",
    request_schema={
        "category": "string", "plants": "array<string>?",
        "target_qty": "number?", "due_date": "string?", "title": "string?",
    },
    response_schema={"event_id": "string", "event": "object"},
    risk_level="low_risk_write",
    tags=["cpq-buy", "rfx", "write"],
))
_reg(ConnectorAPISpec(
    api_id="sourcing.rfx.invite",
    target_system="sourcing",
    operation="POST /api/v1/sourcing-simulator/rfx-events/{event_id}/invitations",
    description="Create RFx_Invitation rows for a vendor panel on an existing RFx_Event.",
    request_schema={"event_id": "string", "vendor_ids": "array<string>"},
    response_schema={"event_id": "string", "invitations": "array<object>"},
    risk_level="low_risk_write",
    tags=["cpq-buy", "rfx", "write"],
))
_reg(ConnectorAPISpec(
    api_id="sourcing.scenario.create",
    target_system="sourcing",
    operation="POST /api/v1/sourcing-simulator/scenarios",
    description=(
        "Build and persist a Sourcing_Scenario (split award) for an RFx_Event "
        "using a chosen strategy (cost_optimal | risk_balanced | diversified)."
    ),
    request_schema={"event_id": "string", "split_strategy": "string?"},
    response_schema={"scenario_id": "string", "scenario": "object"},
    risk_level="low_risk_write",
    tags=["cpq-buy", "award", "scenario", "write"],
))
_reg(ConnectorAPISpec(
    api_id="sourcing.award.issue",
    target_system="sourcing",
    operation="PATCH /api/v1/sourcing-simulator/awards/{award_id}/issue",
    description=(
        "Mark a Sourcing_Award as Issued and kick off the procurement-order "
        "creation chain."
    ),
    request_schema={"award_id": "string"},
    response_schema={"award_id": "string", "new_status": "string"},
    risk_level="high_risk_write",
    tags=["cpq-buy", "award", "write"],
))


# ---------------------------------------------------------------------------
# Public lookup helpers
#
# Post Phase 2 (data-organization spec alignment), the authoritative
# registry lives in DynamoDB under ``CONNAPI#`` PK rows. These lookup
# helpers still work for legacy sync callers by consulting the in-memory
# ``_GLOBAL_CONNECTOR_APIS`` seed manifest, but the async ``*_async``
# variants read from the DDB-backed service.
# ---------------------------------------------------------------------------

def _seed_specs() -> List[ConnectorAPISpec]:
    """Return every spec baked into this module - the DDB bootstrap seed."""
    return list(_GLOBAL_CONNECTOR_APIS.values())


def get(api_id: str) -> Optional[ConnectorAPISpec]:
    return _GLOBAL_CONNECTOR_APIS.get(api_id)


def list_all() -> List[ConnectorAPISpec]:
    return list(_GLOBAL_CONNECTOR_APIS.values())


def list_for_system(target_system: str) -> List[ConnectorAPISpec]:
    return [s for s in _GLOBAL_CONNECTOR_APIS.values() if s.target_system == target_system]


async def get_async(api_id: str) -> Optional[ConnectorAPISpec]:
    """DDB-first lookup; falls back to the seed manifest on miss."""
    try:
        from src.services.data_plane.connector_api_registry_service import (
            get_connector_api_registry,
            is_ddb_registry_enabled,
        )
        if is_ddb_registry_enabled():
            hit = await get_connector_api_registry().get(api_id)
            if hit is not None:
                return hit
    except Exception:
        pass
    return _GLOBAL_CONNECTOR_APIS.get(api_id)


async def list_all_async() -> List[ConnectorAPISpec]:
    """DDB-first listing; falls back to the seed manifest when DDB empty."""
    try:
        from src.services.data_plane.connector_api_registry_service import (
            get_connector_api_registry,
            is_ddb_registry_enabled,
        )
        if is_ddb_registry_enabled():
            items = await get_connector_api_registry().list_all()
            if items:
                return items
    except Exception:
        pass
    return list(_GLOBAL_CONNECTOR_APIS.values())


async def list_for_system_async(target_system: str) -> List[ConnectorAPISpec]:
    try:
        from src.services.data_plane.connector_api_registry_service import (
            get_connector_api_registry,
            is_ddb_registry_enabled,
        )
        if is_ddb_registry_enabled():
            items = await get_connector_api_registry().list_for_system(target_system)
            if items:
                return items
    except Exception:
        pass
    return [s for s in _GLOBAL_CONNECTOR_APIS.values() if s.target_system == target_system]


def register(spec: ConnectorAPISpec) -> None:
    """Public re-registration hook; safe to call from extension modules.

    This still updates the in-memory seed manifest so future DDB bootstraps
    pick the spec up; DDB writes for runtime CRUD go through
    ``ConnectorApiRegistryService.register`` in the async API surface.
    """
    _reg(spec)


def to_dict(spec: ConnectorAPISpec) -> Dict[str, Any]:
    return {
        "api_id": spec.api_id,
        "target_system": spec.target_system,
        "operation": spec.operation,
        "description": spec.description,
        "request_schema": spec.request_schema,
        "response_schema": spec.response_schema,
        "simulator_writeback": spec.simulator_writeback,
        "risk_level": spec.risk_level,
        "tags": list(spec.tags),
    }
