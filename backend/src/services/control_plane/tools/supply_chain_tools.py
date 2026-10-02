"""
Supply Chain ReAct Tools for the AI Control Plane.

Provides supply chain-specific read and write operations as agent-callable
tools. Read tools query the ontology and systems of record. Write tools
modify state in Salesforce (via FDW/API) and SAP (via integration layer).
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from ..tool_registry import Tool, RiskLevel
from ..rag_service import RAGService

cp_logger = logger.bind(component="control-plane-supply-chain")


async def _get_inventory_position(
    rag_service: RAGService,
    material_id: str,
    plant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Query inventory positions for a material across plants via ontology."""
    query = f"inventory position for material {material_id}"
    if plant_id:
        query += f" at plant {plant_id}"

    result = await rag_service.hybrid_search(
        query=query,
        content_type="onto_schema",
        limit=10,
    )

    return {
        "query": query,
        "material_id": material_id,
        "plant_id": plant_id,
        "results": [
            {
                "source_id": r.get("source_id", ""),
                "content": r.get("content", "")[:600],
                "similarity": round(float(r.get("similarity", 0)), 4),
            }
            for r in result.get("results", [])
        ],
        "total": result.get("total", 0),
        "note": "Inventory data sourced from SAP via ontology. For live data, SAP FDW connection required.",
    }


async def _get_order_lifecycle(
    rag_service: RAGService,
    order_id: Optional[str] = None,
    account_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Trace an order from Salesforce Opportunity through SAP Delivery to Oracle Invoice."""
    query = "order to cash lifecycle"
    if order_id:
        query += f" for order {order_id}"
    if account_name:
        query += f" for customer {account_name}"

    result = await rag_service.hybrid_search(query=query, limit=15)

    schemas = []
    workflows = []
    integrations = []
    for r in result.get("results", []):
        ct = r.get("content_type", "")
        entry = {
            "source_id": r.get("source_id", ""),
            "content": r.get("content", "")[:400],
            "similarity": round(float(r.get("similarity", 0)), 4),
        }
        if ct == "onto_schema":
            schemas.append(entry)
        elif ct == "onto_workflow":
            workflows.append(entry)
        elif ct == "onto_integration":
            integrations.append(entry)

    return {
        "order_id": order_id,
        "account_name": account_name,
        "lifecycle_entities": schemas,
        "workflows": workflows,
        "integrations": integrations,
        "lifecycle_stages": [
            "1. Salesforce Opportunity (order capture)",
            "2. SAP Delivery_Document (fulfillment)",
            "3. Oracle AR_Invoice (billing)",
            "4. Oracle AR_Payment (collection)",
        ],
    }


async def _score_supplier_risk(
    rag_service: RAGService,
    vendor_id: Optional[str] = None,
    vendor_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve supplier risk scoring workflow and policy context."""
    query = "supplier risk scoring"
    if vendor_name:
        query += f" for vendor {vendor_name}"
    elif vendor_id:
        query += f" for vendor {vendor_id}"

    result = await rag_service.hybrid_search(query=query, limit=15)

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "risk_framework": {
            "delivery_reliability": "30%",
            "financial_health": "20%",
            "geographic_risk": "15%",
            "quality_performance": "15%",
            "contract_compliance": "10%",
            "external_signals": "10%",
        },
        "risk_tiers": {
            "80-100": "Low (standard monitoring)",
            "60-79": "Medium (quarterly review)",
            "40-59": "High (monthly review + improvement plan)",
            "0-39": "Critical (freeze POs, activate alternatives)",
        },
        "related_knowledge": [
            {
                "source_id": r.get("source_id", ""),
                "content": r.get("content", "")[:400],
                "content_type": r.get("content_type", ""),
            }
            for r in result.get("results", [])[:8]
        ],
    }


async def _create_forecast_override(
    rag_service: RAGService,
    product_id: str,
    region: str,
    period: str,
    override_qty: int,
    justification: str,
) -> Dict[str, Any]:
    """Create a Forecast_Override record in Salesforce."""
    cp_logger.info(f"Creating forecast override: {product_id} / {region} / {period} / qty={override_qty}")

    return {
        "status": "pending_implementation",
        "action": "create_forecast_override",
        "record": {
            "product_id": product_id,
            "region": region,
            "period": period,
            "override_qty": override_qty,
            "justification": justification,
        },
        "note": "Requires Salesforce API integration. Override will feed into demand-forecast-generation workflow.",
        "policy_check": "Override quantity has no policy limit, but justification is mandatory.",
    }


async def _create_transfer_order(
    rag_service: RAGService,
    from_plant: str,
    to_plant: str,
    material_id: str,
    quantity: int,
    batch_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a Warehouse_Transfer record in SAP for stock rebalancing."""
    cp_logger.info(f"Creating transfer order: {material_id} qty={quantity} from {from_plant} to {to_plant}")

    return {
        "status": "pending_implementation",
        "action": "create_transfer_order",
        "record": {
            "from_plant": from_plant,
            "to_plant": to_plant,
            "material_id": material_id,
            "quantity": quantity,
            "batch_id": batch_id or "FIFO_AUTO",
        },
        "approval_rules": {
            "auto_approved": "Transfer value < $50K per inventory-policy Section 6",
            "requires_approval": "Transfer value >= $50K requires Supply Chain Manager approval",
        },
        "note": "Requires SAP integration layer. Transfer triggers inventory-rebalancing workflow.",
    }


async def _hold_batch(
    rag_service: RAGService,
    batch_id: str,
    material_id: str,
    reason: str,
) -> Dict[str, Any]:
    """Set Batch_Master.Status = Blocked in SAP for quality hold."""
    cp_logger.info(f"Holding batch {batch_id} for material {material_id}: {reason}")

    return {
        "status": "pending_implementation",
        "action": "hold_batch",
        "record": {
            "batch_id": batch_id,
            "material_id": material_id,
            "new_status": "Blocked",
            "reason": reason,
        },
        "policy_reference": "quality-policy Section 4: Batch Hold and Release",
        "escalation": {
            "minor_deviation": "QC Manager can release",
            "major_deviation": "Quality Director required",
            "critical_food_safety": "No release possible",
        },
        "note": "Requires SAP integration layer. Hold triggers quality-deviation-response workflow.",
    }


async def _update_customer_credit(
    rag_service: RAGService,
    account_id: str,
    new_credit_limit: float,
    justification: str,
) -> Dict[str, Any]:
    """Update Account.Credit_Limit in Salesforce — triggers credit approval workflow."""
    cp_logger.info(f"Updating credit limit for {account_id} to {new_credit_limit}")

    return {
        "status": "pending_implementation",
        "action": "update_customer_credit",
        "record": {
            "account_id": account_id,
            "new_credit_limit": new_credit_limit,
            "justification": justification,
        },
        "approval_rules": {
            "auto_approved": "Change <= 5% increase",
            "sales_manager": "Change 5-10% increase (24h SLA)",
            "finance_manager": "Change > 10% increase (48h SLA)",
        },
        "policy_reference": "credit-policy (POL-CREDIT-001)",
        "downstream_impact": "Credit limit syncs to Oracle AR_Customer via sf-oracle-supply-chain-sync integration.",
        "note": "Requires Salesforce API. Triggers Credit Approval Flow workflow.",
    }


def register_supply_chain_tools(
    registry,
    rag_service: Optional[RAGService] = None,
):
    """Register all supply chain tools with the tool registry."""

    if not rag_service:
        cp_logger.warning("RAG service not available — supply chain tools not registered")
        return

    registry.register(Tool(
        name="get_inventory_position",
        description=(
            "Query inventory positions for a material/SKU across plants and warehouses. "
            "Returns stock levels, batch information, and days of supply from the supply chain ontology. "
            "Use this to check if rebalancing is needed."
        ),
        parameters={
            "type": "object",
            "properties": {
                "material_id": {
                    "type": "string",
                    "description": "Material/SKU identifier (e.g. 'PEPSI_500ML', 'TROPICANA_1L')",
                },
                "plant_id": {
                    "type": "string",
                    "description": "Optional plant/warehouse ID to filter to a specific location",
                },
            },
            "required": ["material_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _get_inventory_position(rag_service, **kw),
    ))

    registry.register(Tool(
        name="get_order_lifecycle",
        description=(
            "Trace an order's full lifecycle from Salesforce Opportunity through SAP Delivery "
            "to Oracle AR Invoice and Payment. Shows cross-system entities, workflows, and integrations involved."
        ),
        parameters={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Salesforce Opportunity ID",
                },
                "account_name": {
                    "type": "string",
                    "description": "Customer account name to search by",
                },
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _get_order_lifecycle(rag_service, **kw),
    ))

    registry.register(Tool(
        name="score_supplier_risk",
        description=(
            "Retrieve the supplier risk scoring framework and related policies for a vendor. "
            "Shows the weighted risk model (delivery 30%, financial 20%, geographic 15%, "
            "quality 15%, contract 10%, external 10%) and risk tier thresholds."
        ),
        parameters={
            "type": "object",
            "properties": {
                "vendor_id": {
                    "type": "string",
                    "description": "SAP Vendor ID",
                },
                "vendor_name": {
                    "type": "string",
                    "description": "Vendor name to search by",
                },
            },
            "required": [],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _score_supplier_risk(rag_service, **kw),
    ))

    registry.register(Tool(
        name="create_forecast_override",
        description=(
            "Create a manual forecast override for a product in a region and period. "
            "Overrides the AI-generated demand forecast with a sales team adjustment. "
            "Requires justification text."
        ),
        parameters={
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "Product/SKU ID"},
                "region": {"type": "string", "description": "Geographic region"},
                "period": {"type": "string", "description": "Forecast period (e.g. '2026-W14')"},
                "override_qty": {"type": "integer", "description": "Override quantity"},
                "justification": {"type": "string", "description": "Business justification for the override"},
            },
            "required": ["product_id", "region", "period", "override_qty", "justification"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _create_forecast_override(rag_service, **kw),
        connector_api="sfdc.forecast_override.create",
        tags=["forecast", "override"],
    ))

    registry.register(Tool(
        name="create_transfer_order",
        description=(
            "Create an inter-warehouse stock transfer order to rebalance inventory. "
            "Transfers material from a surplus plant to a deficit plant. "
            "Auto-approved if value < $50K per inventory policy."
        ),
        parameters={
            "type": "object",
            "properties": {
                "from_plant": {"type": "string", "description": "Source plant/warehouse ID"},
                "to_plant": {"type": "string", "description": "Destination plant/warehouse ID"},
                "material_id": {"type": "string", "description": "Material/SKU to transfer"},
                "quantity": {"type": "integer", "description": "Quantity to transfer"},
                "batch_id": {"type": "string", "description": "Specific batch (default: FIFO auto-selection)"},
            },
            "required": ["from_plant", "to_plant", "material_id", "quantity"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _create_transfer_order(rag_service, **kw),
        connector_api="sap.warehouse_transfer.create",
        tags=["inventory", "transfer"],
    ))

    registry.register(Tool(
        name="hold_batch",
        description=(
            "Place a quality hold on a batch, blocking it from shipment or sale. "
            "Sets Batch_Master.Status to Blocked in SAP. "
            "Triggers quality-deviation-response workflow. HIGH RISK \u2014 requires justification."
        ),
        parameters={
            "type": "object",
            "properties": {
                "batch_id": {"type": "string", "description": "Batch/lot ID to hold"},
                "material_id": {"type": "string", "description": "Material/SKU of the batch"},
                "reason": {"type": "string", "description": "Reason for the quality hold"},
            },
            "required": ["batch_id", "material_id", "reason"],
        },
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _hold_batch(rag_service, **kw),
        connector_api="sap.batch.hold",
        requires_approval=True,
        tags=["quality", "batch"],
    ))

    registry.register(Tool(
        name="update_customer_credit",
        description=(
            "Update a customer's credit limit in Salesforce. "
            "Triggers credit approval workflow based on change magnitude: "
            "<=5% auto-approved, 5-10% needs Sales Manager, >10% needs Finance Manager. "
            "HIGH RISK \u2014 syncs to Oracle AR."
        ),
        parameters={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Salesforce Account ID"},
                "new_credit_limit": {"type": "number", "description": "New credit limit amount in USD"},
                "justification": {"type": "string", "description": "Business justification (mandatory for changes > 10%)"},
            },
            "required": ["account_id", "new_credit_limit", "justification"],
        },
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _update_customer_credit(rag_service, **kw),
        connector_api="sfdc.account.credit_hold.set",
        requires_approval=True,
        tags=["credit", "account"],
    ))

    # Phase 1 -- stamp the supply-chain bucket on every tool registered here.
    for tool_name in (
        "get_inventory_position", "get_order_lifecycle", "score_supplier_risk",
        "create_forecast_override", "create_transfer_order", "hold_batch",
        "update_customer_credit",
    ):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "supply-chain"

    cp_logger.info("Registered 7 supply chain tools (3 read, 2 low-risk write, 2 high-risk write)")
