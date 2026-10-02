"""
Agent Executor for the AI Control Plane.

Implements the ReAct (Reason + Act) loop:
  PLAN -> EXECUTE -> OBSERVE -> REPLAN -> EXECUTE -> OBSERVE

Integrates:
  - PolicyEngine: validates every tool call before execution
  - AuditLogger: logs every action for compliance
  - IntentAnalyzer: classifies risk level to gate tool access
"""

import json
import time
from typing import Any, Dict, List, Optional

from loguru import logger

from .llm_client import LLMClient
from .tool_registry import ToolRegistry, RiskLevel
from .policy_engine import PolicyEngine, PolicyContext, PolicyViolation
from .audit_logger import AuditLogger
from .intent_analyzer import analyze_intent, analyze_intent_async
from .cache import get_cached, set_cached

cp_logger = logger.bind(component="control-plane")

MAX_STEPS = 10

AGENT_SYSTEM_PROMPT = """You are an AI agent for an enterprise data platform with a Virtual Data Layer spanning multiple verticals and systems of record.

VIRTUAL DATA LAYER:
The platform uses a unified schema (enterprise-knowledge YAML) that defines ~45+ business entities across multiple source systems. These entities are mapped to actual data sources (FDW foreign tables, simulators, or integration feeds) via mapping rules. You should query entities by their **business name** using `query_virtual_entity` — the virtual data layer automatically routes to the correct source.

VERTICALS AND SYSTEMS:
- **CRM**: Salesforce CRM + Oracle ERP (customer management, credit, billing)
- **Supply Chain**: Salesforce CRM + SAP S/4HANA + Oracle ERP Finance & Operations (beverage supply chain — Plan, Source, Make, Deliver, Return per SCOR model)
  - Salesforce: Customers (Account), Orders (Opportunity), Campaigns, Forecast Overrides
  - SAP: Materials (Material_Master with GS1 GTIN), Inventory, Batches, Production, Quality, Vendors, Deliveries
  - Oracle Finance: AR (invoices, payments, credit notes), GL (journals, periods)
  - Oracle Operations: AP (vendor invoices, payments), Purchase Orders, Cost Accounting, Fixed Assets, Budgets
  - Unstructured: Contract documents (Google Drive NLP), Lab reports (File Uploads OCR), Market signals (Social Listening)

Your knowledge base contains:
- **Schema metadata**: Unified supply chain schema (~45 entities across 12 SCOR-aligned domains) + CRM entities, all indexed with mapping status (mapped/virtual/unmapped)
- **Business policies**: Inventory management, procurement, quality, supply chain risk, pricing/discount, sustainability, data freshness, order fulfillment, credit, close window, RBAC
- **Workflows**: Demand forecasting, inventory rebalancing, expiry management, order-to-cash monitoring, supplier risk scoring, disruption response, customer churn prediction, procurement spend analysis, invoice processing, production scheduling, quality deviation response, ESG reporting, credit approval, customer onboarding, risk assessment
- **Integration mappings**: SF-Oracle sync, SF-SAP demand sync, SAP-Oracle finance sync, SAP inventory feed, unstructured extraction, social listening feed
- **Mapping rules**: Active rules that connect virtual entities to source tables (FDW or simulators)

TOOL SELECTION STRATEGY:
1. For questions about business rules, policies, approvals, workflows, cross-system dependencies, or "what happens if":
   → Use search_enterprise_knowledge (hybrid vector + graph search across all knowledge types)
2. For questions about entity schemas, field definitions, or data availability:
   → Use get_entity_schema for detailed field info, or search_enterprise_knowledge for broader context
3. For data queries (counts, records, lookups) on ANY entity in the unified schema:
   → Use query_virtual_entity (PRIMARY) — it routes to the correct source via mapping rules
   → Use list_virtual_entities first if unsure what entities are available
4. For direct FDW queries on unmapped physical tables (fallback only):
   → Use discover_tables + discover_columns + query_table
5. For supply chain operations (inventory, orders, suppliers, production):
   → Use get_inventory_position, get_order_lifecycle, score_supplier_risk
6. BEFORE any write operation:
   → ALWAYS call check_policy_compliance first to validate against governance policies
7. For write operations (after policy check):
   → Use create_forecast_override, create_transfer_order, hold_batch, update_customer_credit

ALWAYS prefer search_enterprise_knowledge as your first tool — it retrieves policies, workflows, and integration rules that are critical for safe answers.
For data queries, ALWAYS prefer query_virtual_entity over query_table — it uses the virtual data layer with proper field mapping.

When answering, structure your response to cover ALL applicable dimensions:
- **Source of Truth**: Which system owns the data (Salesforce vs SAP vs Oracle)
- **Data Status**: Whether the entity is mapped (live data), virtual (no direct query), or mapped via rule
- **SCOR Process**: Which supply chain process applies (Plan/Source/Make/Deliver/Return/Enable)
- **Relevant Fields**: Specific field names, GS1 identifiers, and their constraints
- **Policies**: Applicable business rules, approval thresholds, compliance requirements
- **Workflows**: Triggered process flows with steps, SLAs, and escalation paths
- **Integration Dependencies**: Cross-system sync rules (Salesforce ↔ SAP ↔ Oracle)
- **FDW Mapping Status**: Whether the entity is mapped (live FDW), virtual (integration), or unmapped
- **Restrictions**: Close window rules, SOX compliance, RBAC constraints

The search_enterprise_knowledge tool returns a structured retrieval_bundle with schemas, policies, workflows, integrations, and graph_dependencies. USE ALL SECTIONS in your answer.

If the retrieval bundle lacks a dimension, explicitly state it is not covered.
Never answer with just table names — provide the full business context."""


class AgentExecutor:
    """ReAct agent loop with policy enforcement and audit logging."""

    def __init__(self, llm: LLMClient, tool_registry: ToolRegistry):
        self._llm = llm
        self._tools = tool_registry
        self._policy = PolicyEngine(tool_registry)

    async def run(
        self,
        question: str,
        max_steps: int = MAX_STEPS,
        user: str = "anonymous",
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        cache_key = question.strip().lower()
        if not skip_cache:
            cached = await get_cached("agent", cache_key)
            if cached:
                cp_logger.info("Agent cache hit")
                cached["_cached"] = True
                return cached

        intent = await analyze_intent_async(question, self._llm)
        cp_logger.info(f"Intent classified: {intent}")

        policy_ctx = PolicyContext(
            intent_risk=intent,
            max_steps=max_steps,
        )

        audit = AuditLogger()
        session_id = audit.start_session(question, user=user, intent_risk=intent)

        max_risk = {
            "read_only": RiskLevel.READ_ONLY,
            "low_risk_write": RiskLevel.LOW_RISK_WRITE,
            "high_risk_write": RiskLevel.HIGH_RISK_WRITE,
            "cross_system": RiskLevel.HIGH_RISK_WRITE,
        }.get(intent, RiskLevel.READ_ONLY)

        openai_tools = self._tools.to_openai_tools(max_risk=max_risk)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        steps: List[Dict[str, Any]] = []
        total_tokens = 0
        violations: List[str] = []

        for step_num in range(1, max_steps + 1):
            cp_logger.info(f"Agent step {step_num}/{max_steps} (intent={intent})")

            result = await self._llm.achat(
                messages=messages,
                tools=openai_tools if openai_tools else None,
                max_tokens=2048,
                temperature=0.1,
            )
            total_tokens += result.get("usage", {}).get("total_tokens", 0)

            if result.get("tool_calls"):
                assistant_msg: Dict[str, Any] = {
                    "role": "assistant",
                    "content": result.get("content") or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"],
                            },
                        }
                        for tc in result["tool_calls"]
                    ],
                }
                messages.append(assistant_msg)

                for tc in result["tool_calls"]:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        fn_args = {}

                    try:
                        self._policy.validate(fn_name, fn_args, policy_ctx)
                    except PolicyViolation as pv:
                        cp_logger.warning(f"Policy blocked: {pv.reason}")
                        audit.log_policy_violation(fn_name, pv.reason, pv.policy)
                        violations.append(pv.reason)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps({"error": f"Policy violation: {pv.reason}"}),
                        })
                        steps.append({
                            "step": step_num,
                            "tool": fn_name,
                            "blocked": True,
                            "reason": pv.reason,
                        })
                        continue

                    t0 = time.monotonic()
                    tool_result = await self._tools.execute(fn_name, fn_args)
                    duration_ms = (time.monotonic() - t0) * 1000

                    self._policy.record_execution(fn_name, policy_ctx)

                    tool_output = json.dumps(tool_result, default=str)
                    if len(tool_output) > 8000:
                        tool_output = tool_output[:8000] + "\n... (truncated)"

                    audit.log_tool_call(
                        fn_name, fn_args,
                        result_preview=tool_output[:200],
                        duration_ms=duration_ms,
                    )

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_output,
                    })
                    step_entry = {
                        "step": step_num,
                        "tool": fn_name,
                        "args": fn_args,
                        "result_preview": tool_output[:200],
                        "duration_ms": round(duration_ms, 1),
                    }
                    rd = self._extract_retrieval_details(fn_name, tool_result)
                    if rd:
                        step_entry["retrieval_details"] = rd
                    steps.append(step_entry)
            else:
                steps.append({"step": step_num, "tool": None, "action": "final_answer"})
                answer = result["content"]
                audit.log_final_answer(answer[:300], step_num, total_tokens)
                response = {
                    "answer": answer,
                    "intent": intent,
                    "session_id": session_id,
                    "steps": steps,
                    "total_steps": step_num,
                    "total_tokens": total_tokens,
                    "policy_violations": violations,
                }
                if intent == "read_only" and not skip_cache:
                    await set_cached("agent", cache_key, response, ttl_s=300)
                return response

        cp_logger.warning(f"Agent exhausted {max_steps} steps without final answer, forcing completion")
        force_result = await self._llm.achat(
            messages=messages + [{"role": "user", "content": "Please provide your final answer now based on the information gathered so far."}],
            max_tokens=2048,
            temperature=0.1,
        )
        total_tokens += force_result.get("usage", {}).get("total_tokens", 0)
        answer = force_result.get("content", "I was unable to complete the analysis within the allowed steps.")
        steps.append({"step": max_steps + 1, "tool": None, "action": "forced_final_answer"})
        audit.log_final_answer(answer[:300], max_steps + 1, total_tokens)
        return {
            "answer": answer,
            "intent": intent,
            "session_id": session_id,
            "steps": steps,
            "total_steps": max_steps + 1,
            "total_tokens": total_tokens,
            "policy_violations": violations,
            "max_steps_exhausted": True,
        }

    async def run_streaming(
        self,
        question: str,
        max_steps: int = MAX_STEPS,
        user: str = "anonymous",
        skip_cache: bool = False,
    ):
        """Async generator yielding SSE events at each phase of the ReAct loop."""
        cache_key = question.strip().lower()
        if not skip_cache:
            cached = await get_cached("agent", cache_key)
            if cached:
                cached["_cached"] = True
                yield {"type": "cache_hit", "data": cached}
                return

        yield {"type": "status", "message": "Classifying intent..."}
        intent = await analyze_intent_async(question, self._llm)
        yield {"type": "intent", "intent": intent}

        policy_ctx = PolicyContext(intent_risk=intent, max_steps=max_steps)
        audit = AuditLogger()
        session_id = audit.start_session(question, user=user, intent_risk=intent)

        max_risk = {
            "read_only": RiskLevel.READ_ONLY,
            "low_risk_write": RiskLevel.LOW_RISK_WRITE,
            "high_risk_write": RiskLevel.HIGH_RISK_WRITE,
            "cross_system": RiskLevel.HIGH_RISK_WRITE,
        }.get(intent, RiskLevel.READ_ONLY)

        openai_tools = self._tools.to_openai_tools(max_risk=max_risk)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        steps: List[Dict[str, Any]] = []
        total_tokens = 0
        violations: List[str] = []

        for step_num in range(1, max_steps + 1):
            yield {"type": "step_start", "step": step_num, "max_steps": max_steps}

            result = await self._llm.achat(
                messages=messages,
                tools=openai_tools if openai_tools else None,
                max_tokens=2048,
                temperature=0.1,
            )
            total_tokens += result.get("usage", {}).get("total_tokens", 0)

            if result.get("tool_calls"):
                assistant_msg: Dict[str, Any] = {
                    "role": "assistant",
                    "content": result.get("content") or None,
                    "tool_calls": [
                        {"id": tc["id"], "type": "function",
                         "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}}
                        for tc in result["tool_calls"]
                    ],
                }
                messages.append(assistant_msg)

                for tc in result["tool_calls"]:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        fn_args = {}

                    try:
                        self._policy.validate(fn_name, fn_args, policy_ctx)
                    except PolicyViolation as pv:
                        audit.log_policy_violation(fn_name, pv.reason, pv.policy)
                        violations.append(pv.reason)
                        messages.append({"role": "tool", "tool_call_id": tc["id"],
                                         "content": json.dumps({"error": f"Policy violation: {pv.reason}"})})
                        steps.append({"step": step_num, "tool": fn_name, "blocked": True, "reason": pv.reason})
                        yield {"type": "tool_blocked", "step": step_num, "tool": fn_name, "reason": pv.reason}
                        continue

                    yield {"type": "tool_call", "step": step_num, "tool": fn_name, "args": fn_args}

                    t0 = time.monotonic()
                    tool_result = await self._tools.execute(fn_name, fn_args)
                    duration_ms = (time.monotonic() - t0) * 1000

                    self._policy.record_execution(fn_name, policy_ctx)
                    tool_output = json.dumps(tool_result, default=str)
                    if len(tool_output) > 8000:
                        tool_output = tool_output[:8000] + "\n... (truncated)"

                    audit.log_tool_call(fn_name, fn_args, result_preview=tool_output[:200], duration_ms=duration_ms)
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": tool_output})

                    step_entry = {
                        "step": step_num, "tool": fn_name, "args": fn_args,
                        "result_preview": tool_output[:200], "duration_ms": round(duration_ms, 1),
                    }
                    rd = self._extract_retrieval_details(fn_name, tool_result)
                    if rd:
                        step_entry["retrieval_details"] = rd
                    steps.append(step_entry)
                    yield {"type": "tool_result", "step": step_num, "tool": fn_name,
                           "duration_ms": round(duration_ms, 1), "preview": tool_output[:150]}
            else:
                steps.append({"step": step_num, "tool": None, "action": "final_answer"})
                answer = result["content"]
                audit.log_final_answer(answer[:300], step_num, total_tokens)
                response = {
                    "answer": answer, "intent": intent, "session_id": session_id,
                    "steps": steps, "total_steps": step_num,
                    "total_tokens": total_tokens, "policy_violations": violations,
                }
                if intent == "read_only" and not skip_cache:
                    await set_cached("agent", cache_key, response, ttl_s=300)
                yield {"type": "answer", "data": response}
                return

        yield {"type": "status", "message": "Summarizing findings..."}
        force_result = await self._llm.achat(
            messages=messages + [{"role": "user", "content": "Please provide your final answer now based on the information gathered so far."}],
            max_tokens=2048, temperature=0.1,
        )
        total_tokens += force_result.get("usage", {}).get("total_tokens", 0)
        answer = force_result.get("content", "I was unable to complete the analysis within the allowed steps.")
        steps.append({"step": max_steps + 1, "tool": None, "action": "forced_final_answer"})
        audit.log_final_answer(answer[:300], max_steps + 1, total_tokens)
        response = {
            "answer": answer, "intent": intent, "session_id": session_id,
            "steps": steps, "total_steps": max_steps + 1,
            "total_tokens": total_tokens, "policy_violations": violations,
            "max_steps_exhausted": True,
        }
        yield {"type": "answer", "data": response}

    @staticmethod
    def _extract_retrieval_details(tool_name: str, tool_result: Any) -> Optional[Dict[str, Any]]:
        """Extract structured retrieval metadata from RAG tool results."""
        if tool_name not in ("search_enterprise_knowledge", "search_schema_knowledge"):
            return None
        if not isinstance(tool_result, dict):
            return None

        def _slim(items):
            return [
                {
                    "source_id": e.get("source_id", ""),
                    "similarity": e.get("similarity", 0),
                    **({"relation_type": e["relation_type"]} if e.get("relation_type") else {}),
                    **({"via_graph": True} if e.get("via_graph") else {}),
                }
                for e in (items or [])
            ]

        def _slim_phase(phase):
            if not phase:
                return None
            p = {
                "step": phase.get("step", ""),
                "description": phase.get("description", ""),
                "duration_ms": phase.get("duration_ms", 0),
                "results_count": phase.get("results_count", 0),
            }
            if phase.get("top_hits"):
                p["top_hits"] = phase["top_hits"][:6]
            if phase.get("edges_traversed"):
                p["edges_traversed"] = [
                    {"from": e.get("from", "")[:30], "to": e.get("to", "")[:30],
                     "relation": e.get("relation", ""), "hop": e.get("hop", 1)}
                    for e in phase["edges_traversed"][:10]
                ]
            if phase.get("neighbors_found"):
                p["neighbors_found"] = phase["neighbors_found"]
            return p

        bundle = tool_result.get("retrieval_bundle")
        if bundle:
            phases = [_slim_phase(p) for p in tool_result.get("pipeline_phases", []) if p]
            return {
                "vector_hits": tool_result.get("vector_hits", 0),
                "graph_hits": tool_result.get("graph_hits", 0),
                "summary": tool_result.get("summary", ""),
                "graph_traversal_summary": tool_result.get("graph_traversal_summary", ""),
                "pipeline_phases": [p for p in phases if p],
                "schemas": _slim(bundle.get("schemas")),
                "policies": _slim(bundle.get("policies")),
                "workflows": _slim(bundle.get("workflows")),
                "integrations": _slim(bundle.get("integrations")),
            }

        results = tool_result.get("results", [])
        if results:
            return {
                "vector_hits": tool_result.get("total", len(results)),
                "graph_hits": 0,
                "summary": f"{len(results)} results",
                "graph_traversal_summary": "",
                "pipeline_phases": [],
                "schemas": _slim([r for r in results if r.get("content_type") in ("fdw_table", "onto_schema")]),
                "policies": _slim([r for r in results if r.get("content_type") == "onto_policy"]),
                "workflows": _slim([r for r in results if r.get("content_type") == "onto_workflow"]),
                "integrations": _slim([r for r in results if r.get("content_type") == "onto_integration"]),
            }

        return None

        # Reached max steps without final answer — force one
        last_result = self._llm.chat(
            messages=messages + [
                {"role": "user", "content": "Please provide your final answer based on the information gathered so far."}
            ],
            max_tokens=2048,
            temperature=0.1,
        )
        total_tokens += last_result.get("usage", {}).get("total_tokens", 0)
        answer = last_result["content"]
        audit.log_final_answer(answer[:300], max_steps, total_tokens)

        return {
            "answer": answer,
            "intent": intent,
            "session_id": session_id,
            "steps": steps,
            "total_steps": max_steps,
            "total_tokens": total_tokens,
            "policy_violations": violations,
            "note": "Reached max steps, forced final answer",
        }
