"""
Policy Compliance Checker Tool for the AI Control Plane.

Validates proposed actions against relevant policies from the indexed
ontology. The agent calls this before executing any write operation to
ensure governance is not bypassed.
"""

from typing import Any, Dict, Optional

from loguru import logger

from ..tool_registry import Tool, RiskLevel
from ..rag_service import RAGService

cp_logger = logger.bind(component="control-plane-policy")


async def _check_policy_compliance(
    rag_service: RAGService,
    action: str,
    entity: str,
    details: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate a proposed action against relevant policies from the ontology.

    Searches for policies that constrain the target entity and evaluates
    whether the proposed action complies with the retrieved rules.
    """
    query = f"policy rules constraints for {action} on {entity}"
    if details:
        query += f" {details}"

    result = await rag_service.hybrid_search(
        query=query,
        content_type="onto_policy",
        limit=10,
    )

    policies_found = []
    for r in result.get("results", []):
        policies_found.append({
            "source_id": r.get("source_id", ""),
            "content": r.get("content", "")[:600],
            "similarity": round(float(r.get("similarity", 0)), 4),
            "via_graph": bool(r.get("_graph_expanded")),
        })

    workflow_query = f"workflow triggered by {action} on {entity}"
    workflow_result = await rag_service.hybrid_search(
        query=workflow_query,
        content_type="onto_workflow",
        limit=5,
    )

    triggered_workflows = [
        {
            "source_id": r.get("source_id", ""),
            "content": r.get("content", "")[:400],
        }
        for r in workflow_result.get("results", [])
    ]

    compliance_status = "REVIEW_REQUIRED"
    if policies_found:
        compliance_status = "POLICIES_FOUND"
    else:
        compliance_status = "NO_POLICIES_FOUND"

    return {
        "action": action,
        "entity": entity,
        "details": details,
        "compliance_status": compliance_status,
        "policies_retrieved": len(policies_found),
        "policies": policies_found,
        "triggered_workflows": triggered_workflows,
        "recommendation": (
            f"Found {len(policies_found)} relevant policies for '{action}' on '{entity}'. "
            f"Review the policy content above to determine if the action is compliant. "
            f"{len(triggered_workflows)} workflows may be triggered."
        ),
    }


def register_policy_compliance_tool(
    registry,
    rag_service: Optional[RAGService] = None,
):
    """Register the policy compliance checker with the tool registry."""

    if not rag_service:
        cp_logger.warning("RAG service not available — policy compliance tool not registered")
        return

    registry.register(Tool(
        name="check_policy_compliance",
        description=(
            "Check whether a proposed action complies with enterprise policies. "
            "Searches the ontology for relevant policies that constrain the target entity "
            "and retrieves applicable rules, thresholds, and approval requirements. "
            "ALWAYS call this before executing any write operation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": (
                        "The proposed action (e.g. 'rebalance inventory', 'update credit limit', "
                        "'hold batch', 'create purchase order', 'apply markdown')"
                    ),
                },
                "entity": {
                    "type": "string",
                    "description": (
                        "The target entity (e.g. 'Inventory_Position', 'Account', "
                        "'Batch_Master', 'Purchase_Order')"
                    ),
                },
                "details": {
                    "type": "string",
                    "description": (
                        "Additional context about the action (e.g. 'transfer value $45K', "
                        "'credit increase 12%', 'batch BATCH-2026-001 failed pH test')"
                    ),
                },
            },
            "required": ["action", "entity"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _check_policy_compliance(rag_service, **kw),
    ))

    tool = registry.get("check_policy_compliance")
    if tool is not None:
        tool.bucket = "platform-rag"

    cp_logger.info("Registered policy compliance checker tool (bucket=platform-rag)")
