"""
Copilot Journey Engine

RAG-guided planning, step execution with feedback, replanning, and save-as-journey.
Blends the ReAct agent's dynamic reasoning with the Journey stage's deterministic execution.
"""

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

cp_logger = logger.bind(component="copilot-engine")

PLANNING_PROMPT = """You are a journey planning AI for an enterprise data platform.

Given the user's goal and retrieved context (workflows, policies, schemas, integration rules),
generate a step-by-step execution plan using ONLY the available ReAct tools.

Available tools:
{tool_catalog}

Retrieved enterprise knowledge context:
{rag_context}

{playbook_section}
User goal: {goal}
{use_case_hint}

Generate a JSON array of steps. Each step must have:
- "id": short identifier like "s1", "s2"
- "name": human-readable step name
- "tool": exact tool name from the available tools list
- "params": parameters object matching the tool's parameter schema
- "rationale": why this step is needed (reference policies/workflows when applicable)
- "foreach": (optional) "$previous_step_id.results" if iterating over prior results
- "requires_approval": (optional bool) if the step is sensitive (write to a system of record)
- "use_case_id" / "stage_id" / "step_id": (optional) when the step is taken verbatim from the playbook above

PLAYBOOK PRIORITY: When the section "Matched Automation Playbook" is present, prefer those exact stages and steps in order. Adapt only when the user goal calls out a deviation. Never invent a step that has no tool entry in "Available tools".

Consider:
1. Data dependencies - query data before matching/scoring
2. Policy constraints - check policies before write operations
3. Optimal ordering - resolve entities before analysis
4. Output storage - include an s3_write step at the end if the goal implies persistent results

Return ONLY valid JSON array, no explanation text."""

REPLAN_PROMPT = """You are replanning a journey mid-execution.

Completed steps and their results:
{completed_context}

User feedback: {feedback}

Remaining planned steps:
{remaining_steps}

Available tools:
{tool_catalog}

Based on the observations from completed steps and user feedback, revise the remaining steps.
You may add, remove, or modify steps. Return ONLY a valid JSON array of revised steps."""


class CopilotSession:
    def __init__(self, session_id: str, goal: str):
        self.session_id = session_id
        self.goal = goal
        self.plan: List[Dict] = []
        self.completed_steps: List[Dict] = []
        # ``step_results`` keeps the legacy primary-relationship-only
        # view (Dict[step_id, dict]) so every existing prompt / summary
        # / save-as-journey path reads the same shape.
        self.step_results: Dict[str, Any] = {}
        # Phase 1 -- per-step, per-relationship output map. Populated
        # alongside ``step_results`` so downstream ConnectionDoc
        # routing (when the LLM-generated plan emits connections) can
        # route by relationship name. Empty for legacy plans.
        self.relationship_outputs: Dict[str, Dict[str, Any]] = {}
        self.status = "planning"
        self.rag_context: List[str] = []
        # When CopilotEngine.plan retrieves a matching automation use case,
        # the structured playbook (use_case + stages + steps + bindings +
        # apis) is captured here so the UI can display "selected playbook"
        # and downstream tooling can audit which playbook drove the plan.
        self.playbook_context: Optional[Dict[str, Any]] = None
        # Step-level approval state. When PolicyEngine raises an
        # approval_required violation we record the pending step here and
        # the journey waits for the client to call approve_step / feedback.
        self.pending_step: Optional[Dict[str, Any]] = None
        self.approved_steps: List[str] = []
        self.created_at = datetime.now(timezone.utc)
        self.events: List[Dict] = []
        # When this session originated from a saved-journey run (via
        # POST /journeys/{id}/run), the JourneyExecutorBridge mints a
        # job_id in the transformation-system DDB table so the existing
        # /api/v1/journeys/{id}/jobs/{job_id}/logs framework can surface
        # per-step logs identically to regular Journeys. ``None`` for
        # ad-hoc Copilot chat sessions.
        self.job_id: Optional[str] = None

    def add_event(self, event: Dict):
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.events.append(event)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "goal": self.goal,
            "plan": self.plan,
            "completed_steps": self.completed_steps,
            "step_results": self.step_results,
            "relationship_outputs": self.relationship_outputs,
            "status": self.status,
            "rag_context": self.rag_context,
            "playbook_context": self.playbook_context,
            "pending_step": self.pending_step,
            "approved_steps": self.approved_steps,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "events": self.events,
            "job_id": self.job_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CopilotSession":
        s = cls(data.get("session_id", ""), data.get("goal", ""))
        s.plan = data.get("plan", []) or []
        s.completed_steps = data.get("completed_steps", []) or []
        s.step_results = data.get("step_results", {}) or {}
        s.relationship_outputs = data.get("relationship_outputs", {}) or {}
        s.status = data.get("status", "planning")
        s.rag_context = data.get("rag_context", []) or []
        s.playbook_context = data.get("playbook_context")
        s.pending_step = data.get("pending_step")
        s.approved_steps = data.get("approved_steps", []) or []
        ca = data.get("created_at")
        if isinstance(ca, str):
            try:
                s.created_at = datetime.fromisoformat(ca.replace("Z", "+00:00"))
            except Exception:
                s.created_at = datetime.now(timezone.utc)
        s.events = data.get("events", []) or []
        s.job_id = data.get("job_id")
        return s


class CopilotEngine:

    def __init__(self, rag_service=None, tool_registry=None, virtual_query_service=None,
                 automation_indexer=None, session_store=None, policy_engine=None,
                 automation_kg=None, journey_executor_bridge=None, ai_engine_client=None):
        self._rag = rag_service
        self._tools = tool_registry
        self._vq = virtual_query_service
        # AutomationIndexer used to fetch the structured playbook (use case
        # -> stages -> steps -> tool bindings -> connector apis) once a
        # candidate use case has been retrieved by RAG.
        self._automation = automation_indexer
        self._sessions: Dict[str, CopilotSession] = {}
        self._llm_client = None
        # Phase 2: cross-replica persistence. When PG is configured the
        # store mirrors session state to a JSONB row so restart / load-
        # balanced requests don't lose the journey context.
        self._session_store = session_store
        # Phase 2: per-step policy gate (besides the existing risk-level
        # heuristic in _step_needs_approval).
        self._policy_engine = policy_engine
        # Phase 2: graph-driven playbook hydration. When set, _retrieve_playbook
        # consults the knowledge graph first (vector metadata -> AGE Cypher when
        # available -> filesystem). When None, falls back to the indexer.
        self._automation_kg = automation_kg
        # JourneyExecutorBridge -- adapts saved-journey runs into the
        # existing ai-engine JobExecution + LIVELOG framework so the
        # Copilot Saved studio surface can reuse the same /jobs/{id}/
        # logs / aggregate-report endpoints as regular Journeys. When
        # ``None`` the engine simply does not mirror runs to that
        # framework (graceful degradation; the engine still works).
        self._bridge = journey_executor_bridge
        # AiEngineClient -- when AI_ENGINE_EXECUTION_ENABLED, saved-journey
        # runs delegate to POST /api/v1/executions/ and the in-process tool
        # loop is not used (v1.0.0 Copilot decoupling).
        self._ai_engine_client = ai_engine_client

    def _ai_engine_enabled(self) -> bool:
        client = self._ai_engine_client
        return client is not None and client.configured

    async def _submit_to_ai_engine(self, session: "CopilotSession", journey_id: str) -> Dict[str, Any]:
        from src.services.ai_engine_client import AiEngineClientError

        variables: Dict[str, Any] = {}
        inputs = session.step_results.get("inputs")
        if isinstance(inputs, dict):
            variables = inputs
        labels = {
            "triggered_by": "copilot_engine",
            "session_id": session.session_id,
            "source": "saved_journey",
        }
        try:
            payload = await self._ai_engine_client.submit_execution(
                journey_id=journey_id,
                variables=variables,
                labels=labels,
            )
        except AiEngineClientError as exc:
            cp_logger.error("AI Engine submit failed for journey {}: {}", journey_id, exc)
            session.status = "failed"
            session.add_event({"phase": "ai_engine_failed", "error": str(exc)})
            self._persist_session(session)
            return {
                "session_id": session.session_id,
                "error": "ai_engine_submit_failed",
                "message": str(exc),
                "journey_id": journey_id,
            }

        session.status = str(payload.get("status", "submitted")).lower()
        session.add_event(
            {
                "phase": "ai_engine_submitted",
                "execution_id": payload.get("execution_id"),
                "journey_id": journey_id,
            }
        )
        self._persist_session(session)
        return {
            "session_id": session.session_id,
            "status": session.status,
            "execution_id": payload.get("execution_id"),
            "journey_id": payload.get("journey_id", journey_id),
            "tenant_id": payload.get("tenant_id"),
            "links": payload.get("links", {}),
            "via": "ai_engine",
            "job_id": session.job_id,
        }

    def _persist_session(self, session: "CopilotSession") -> None:
        if self._session_store is None:
            return
        try:
            self._session_store.save(session.session_id, session.to_dict())
        except Exception as e:
            cp_logger.warning(f"Session persist failed for {session.session_id}: {e}")

    def _load_or_get_session(self, session_id: str) -> Optional["CopilotSession"]:
        if session_id in self._sessions:
            return self._sessions[session_id]
        if self._session_store is None:
            return None
        try:
            data = self._session_store.load(session_id)
        except Exception as e:
            cp_logger.warning(f"Session load failed for {session_id}: {e}")
            return None
        if not data:
            return None
        session = CopilotSession.from_dict(data)
        self._sessions[session_id] = session
        return session

    def _get_llm(self):
        # Resolve the key fresh on every call so AWS Secrets Manager
        # rotations propagate without a pod restart. We still cache the
        # openai.OpenAI client across calls and only rebuild it when the
        # underlying key has actually changed.
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            try:
                from src.config.config_provider import get_config
                api_key = get_config().openai_api_key or ""
            except Exception:
                pass
        if not api_key:
            return None
        if self._llm_client is None or getattr(self, "_llm_client_key", None) != api_key:
            import openai
            self._llm_client = openai.OpenAI(api_key=api_key, timeout=60.0)
            self._llm_client_key = api_key
        return self._llm_client

    def _get_tool_catalog(self) -> str:
        if not self._tools:
            return "No tools available"
        tools = self._tools.list_tools()
        lines = []
        for t in tools:
            params_desc = json.dumps(t.parameters.get("properties", {}), indent=None)[:200] if t.parameters else "{}"
            lines.append(f"- {t.name} ({t.risk_level.value}): {t.description[:100]}... Params: {params_desc}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Phase 2 - Strict plan validation + auto-repair
    # ------------------------------------------------------------------

    def _known_tool_names(self) -> set:
        if not self._tools:
            return set()
        try:
            return {t.name for t in self._tools.list_tools()}
        except Exception:
            return set()

    def _known_connector_apis(self) -> set:
        try:
            from . import connector_apis as _ca
            return {s.api_id for s in _ca.list_all()}
        except Exception:
            return set()

    def _validate_plan_steps(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate plan steps against the live ToolRegistry + connector_apis.

        Returns ``{ok: bool, errors: [{step_id, code, message}], warnings: [...]}.``
        """
        errors: List[Dict[str, str]] = []
        warnings: List[Dict[str, str]] = []
        known_tools = self._known_tool_names()
        known_apis = self._known_connector_apis()
        seen_ids: set = set()

        for idx, step in enumerate(plan):
            sid = step.get("id") or f"s{idx+1}"
            if sid in seen_ids:
                errors.append({"step_id": sid, "code": "duplicate_id", "message": f"Duplicate step id '{sid}'"})
            seen_ids.add(sid)

            tname = step.get("tool")
            if not tname:
                # An LLM-only / decision step - allowed but warned.
                warnings.append({"step_id": sid, "code": "no_tool", "message": "Step has no tool (LLM-only)"})
                continue
            if known_tools and tname not in known_tools:
                errors.append({
                    "step_id": sid, "code": "unknown_tool",
                    "message": f"Tool '{tname}' is not registered. Pick from the Available tools list."
                })
                continue

            # Tool exists - check connector_api hint when present.
            cap = step.get("connector_api")
            if cap and known_apis and cap not in known_apis:
                errors.append({
                    "step_id": sid, "code": "unknown_connector_api",
                    "message": f"connector_api '{cap}' is not registered."
                })

            # Required-param presence check.
            if self._tools is not None:
                tool = self._tools.get(tname)
                if tool and isinstance(tool.parameters, dict):
                    required = tool.parameters.get("required") or []
                    params = step.get("params") or {}
                    for r in required:
                        v = params.get(r)
                        if v is None or v == "":
                            warnings.append({
                                "step_id": sid, "code": "missing_required_param",
                                "message": f"Required param '{r}' missing/empty for tool '{tname}'.",
                            })

        return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _format_validation_report(self, report: Dict[str, Any]) -> str:
        """Render the validation report for re-feeding into the LLM."""
        lines = []
        for e in report.get("errors", []):
            lines.append(f"  ERROR step={e['step_id']} {e['code']}: {e['message']}")
        for w in report.get("warnings", []):
            lines.append(f"  WARN  step={w['step_id']} {w['code']}: {w['message']}")
        return "\n".join(lines) or "  (no issues)"

    async def create_session(self, goal: str, use_case: str = "") -> CopilotSession:
        session_id = f"copilot-{uuid.uuid4().hex[:12]}"
        session = CopilotSession(session_id, goal)
        self._sessions[session_id] = session
        self._persist_session(session)
        cp_logger.info(f"Copilot session created: {session_id}, goal: {goal[:80]}")
        return session

    def get_session(self, session_id: str) -> Optional[CopilotSession]:
        return self._load_or_get_session(session_id)

    async def plan(self, session_id: str, use_case: str = "") -> Dict[str, Any]:
        session = self._load_or_get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        session.status = "planning"

        # 1. Use-case-first retrieval: search the structured playbook index
        #    BEFORE the generic enterprise-knowledge fallback. If we hit a
        #    high-confidence match the planner gets a deterministic
        #    stage/step/tool/api graph to follow.
        playbook = await self._retrieve_playbook(session.goal, hint=use_case)
        playbook_section = ""
        if playbook is not None:
            session.playbook_context = playbook
            playbook_section = self._format_playbook_for_prompt(playbook)

        # 2. Existing flat hybrid retrieval (schemas / policies / workflows).
        rag_context = ""
        if self._rag:
            try:
                result = await self._rag.hybrid_search(query=session.goal, limit=10)
                rag_docs = result.get("results", [])
                context_parts = []
                for r in rag_docs[:8]:
                    content = r.get("content", "")[:300]
                    source = r.get("source_id", "")
                    context_parts.append(f"[{source}] {content}")
                rag_context = "\n".join(context_parts)
                session.rag_context = [r.get("source_id", "") for r in rag_docs[:8]]
            except Exception as e:
                cp_logger.warning(f"RAG search failed: {e}")
                rag_context = "RAG context not available"

        tool_catalog = self._get_tool_catalog()
        hint = f"Use case hint: {use_case}" if use_case else ""

        prompt = PLANNING_PROMPT.format(
            tool_catalog=tool_catalog, rag_context=rag_context,
            playbook_section=playbook_section,
            goal=session.goal, use_case_hint=hint,
        )

        llm = self._get_llm()
        if not llm:
            session.plan = self._fallback_plan(session.goal)
            session.status = "planned"
            return {"session_id": session_id, "plan": session.plan, "rag_context": session.rag_context, "source": "fallback"}

        # Phase 2: strict-output planner with validate -> auto-repair retry.
        # The LLM may invent tools / connector_apis or omit required params.
        # We validate against the live registries and feed the report back
        # for at most 2 corrective turns before accepting whatever it
        # produced (better a partial plan than a hard fail).
        messages: List[Dict[str, str]] = [{"role": "user", "content": prompt}]
        steps: Optional[List[Dict[str, Any]]] = None
        last_report: Optional[Dict[str, Any]] = None

        for attempt in range(3):
            try:
                response = llm.chat.completions.create(
                    model="gpt-4o-mini", messages=messages,
                    temperature=0.2, max_tokens=2000,
                )
                content = (response.choices[0].message.content or "").strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                parsed = json.loads(content)
                steps_attempt = parsed if isinstance(parsed, list) else parsed.get("steps", [parsed])
            except Exception as e:
                cp_logger.warning(f"LLM planning attempt {attempt+1} failed: {e}")
                break

            report = self._validate_plan_steps(steps_attempt)
            last_report = report
            if report["ok"]:
                steps = steps_attempt
                break

            cp_logger.info(
                "Plan attempt {} had {} errors; sending repair prompt",
                attempt + 1, len(report["errors"]),
            )
            # Append the LLM's previous output + a strict repair instruction
            # so the next turn knows exactly what to fix.
            messages.append({"role": "assistant", "content": json.dumps(steps_attempt)})
            messages.append({"role": "user", "content": (
                "The plan failed validation against the live tool registry.\n"
                f"Issues:\n{self._format_validation_report(report)}\n"
                "Return a corrected JSON array of steps. Use ONLY tools that appear in 'Available tools'. "
                "If you reference a connector_api, it must be one already registered. "
                "Output JSON only, no prose."
            )})
            steps = steps_attempt  # keep latest as fallback

        if steps is None:
            steps = self._fallback_plan(session.goal)
            last_report = self._validate_plan_steps(steps)

        session.plan = steps
        session.status = "planned"
        session.add_event({
            "phase": "planning",
            "steps": len(session.plan),
            "validation": {
                "ok": bool(last_report and last_report.get("ok")),
                "errors": (last_report or {}).get("errors", []),
                "warnings": (last_report or {}).get("warnings", []),
            },
        })
        self._persist_session(session)
        return {
            "session_id": session_id, "plan": session.plan,
            "rag_context": session.rag_context,
            "playbook_context": session.playbook_context,
            "estimated_steps": len(session.plan),
            "validation": (last_report or {}),
        }

    # ------------------------------------------------------------------
    # Playbook retrieval helpers
    # ------------------------------------------------------------------

    async def _retrieve_playbook(
        self,
        goal: str,
        hint: str = "",
        score_threshold: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Return the best-matching structured Use Case as a dict containing
        ``use_case``, ``stages``, ``steps``, ``tool_bindings``,
        ``connector_apis`` so the planner can follow it verbatim.
        """
        if self._rag is None:
            return None
        try:
            result = await self._rag.hybrid_search(
                query=f"{goal} {hint}".strip(),
                content_type="onto_use_case",
                limit=3,
            )
        except TypeError:
            # Older hybrid_search signature; fall back without filter.
            try:
                result = await self._rag.hybrid_search(query=goal, limit=10)
            except Exception:
                return None
        except Exception as e:
            cp_logger.warning("Playbook retrieval failed: {}", e)
            return None

        hits = []
        for r in (result or {}).get("results", []) or []:
            ct = r.get("content_type") or (r.get("metadata") or {}).get("content_type")
            if ct == "onto_use_case":
                hits.append(r)
        if not hits:
            return None
        top = hits[0]
        score = float(top.get("score") or top.get("similarity") or 0)
        if score < score_threshold:
            return None

        meta = top.get("metadata") or {}
        use_case_id = meta.get("use_case_id") or top.get("source_id")
        if not use_case_id:
            return None

        # Phase 2: prefer the knowledge graph (vector metadata + relations)
        # over the on-disk YAML so plan synthesis tracks the indexed truth.
        if self._automation_kg is not None:
            try:
                kg_doc = await self._automation_kg.get_journey_graph(use_case_id)
            except Exception as e:
                cp_logger.warning(f"automation_kg.get_journey_graph failed: {e}")
                kg_doc = None
            if kg_doc:
                kg_doc.setdefault("score", score)
                kg_doc.setdefault("use_case", meta)
                return kg_doc

        if self._automation is None:
            return {"use_case": meta, "stages": [], "score": score}
        try:
            doc = await self._automation.get_use_case(use_case_id)
        except Exception:
            doc = None
        if doc is None:
            return {"use_case": meta, "stages": [], "score": score}
        return self._serialize_playbook(doc, score=score)

    def _serialize_playbook(self, doc: Any, score: float = 0.0) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "use_case_id": doc.use_case_id,
            "title": doc.title,
            "solution_id": doc.solution_id,
            "description": doc.description,
            "tags": list(doc.tags),
            "kpi_impact": list(doc.kpi_impact),
            "score": score,
            "stages": [],
        }
        for stage in doc.stages:
            stage_out = {
                "stage_id": stage.stage_id,
                "name": stage.name,
                "order": stage.order,
                "description": stage.description,
                "steps": [],
            }
            for step in stage.steps:
                bindings = step.effective_bindings()
                stage_out["steps"].append({
                    "step_id": step.step_id,
                    "name": step.name,
                    "order": step.order,
                    "description": step.description,
                    "requires_approval": step.requires_approval,
                    "tool_bindings": [
                        {"tool": b.tool, "params": b.params, "connector_api": b.connector_api}
                        for b in bindings
                    ],
                })
            out["stages"].append(stage_out)
        out["connector_apis"] = [
            {"api_id": api.api_id, "target_system": api.target_system, "operation": api.operation,
             "risk_level": api.risk_level}
            for api in doc.connector_apis
        ]
        return out

    @staticmethod
    def _format_playbook_for_prompt(playbook: Dict[str, Any]) -> str:
        if not playbook or not playbook.get("stages"):
            return ""
        lines = [
            "Matched Automation Playbook:",
            f"  use_case_id: {playbook.get('use_case_id')}",
            f"  title:       {playbook.get('title')}",
            f"  solution_id: {playbook.get('solution_id')}",
            f"  score:       {playbook.get('score'):.3f}" if playbook.get('score') else "",
            "  stages:",
        ]
        for stage in playbook.get("stages", []):
            lines.append(f"    - [{stage['order']}] {stage['stage_id']}: {stage['name']}")
            for step in stage.get("steps", []):
                approval = " (requires_approval)" if step.get("requires_approval") else ""
                tools = ", ".join(b["tool"] for b in step.get("tool_bindings", []))
                apis = ", ".join(b["connector_api"] for b in step.get("tool_bindings", [])
                                 if b.get("connector_api"))
                line = f"        - [{step['order']}] {step['step_id']}: {step['name']}{approval}"
                if tools:
                    line += f"  -> tools: {tools}"
                if apis:
                    line += f"  -> apis: {apis}"
                lines.append(line)
        if playbook.get("connector_apis"):
            lines.append("  connector_apis:")
            for api in playbook["connector_apis"]:
                lines.append(f"    - {api['api_id']} ({api['target_system']}, {api['risk_level']}): {api['operation']}")
        return "\n".join(lines) + "\n"

    def _fallback_plan(self, goal: str) -> List[Dict]:
        goal_lower = goal.lower()
        if "order" in goal_lower and "cash" in goal_lower:
            return [
                {"id": "s1", "name": "Load Orders", "tool": "query_virtual_entity", "params": {"entity": "Opportunity", "filter": {"Stage": "Closed_Won"}}, "rationale": "Load closed orders for O2C analysis"},
                {"id": "s2", "name": "Match Orders", "tool": "match_order_delivery_invoice", "foreach": "$s1.results", "params": {"opportunity_id": "$item.Opportunity_ID"}, "rationale": "Three-way match per policy"},
                {"id": "s3", "name": "Project Cash Flow", "tool": "project_cash_flow", "params": {}, "rationale": "Forecast AR collections"},
                {"id": "s4", "name": "Generate Alerts", "tool": "generate_o2c_alerts", "params": {}, "rationale": "Evaluate alert rules"},
            ]
        if "inventory" in goal_lower:
            return [
                {"id": "s1", "name": "Load Inventory", "tool": "query_virtual_entity", "params": {"entity": "Inventory_Position"}, "rationale": "Get current stock levels"},
                {"id": "s2", "name": "Check Materials", "tool": "query_virtual_entity", "params": {"entity": "Material_Master"}, "rationale": "Get product details"},
            ]
        return [
            {"id": "s1", "name": "Search Knowledge", "tool": "search_enterprise_knowledge", "params": {"query": goal}, "rationale": "Understand the domain"},
        ]

    async def execute_plan(self, session_id: str, emit_callback: Optional[Callable] = None) -> Dict[str, Any]:
        session = self._load_or_get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        # v1.0.0: when AI Engine execution is enabled, Copilot does not run
        # the in-process tool loop. Saved journeys delegate to the engine;
        # ad-hoc sessions are rejected (v100-I2).
        if self._ai_engine_enabled():
            journey_id = None
            if session.playbook_context and session.playbook_context.get("source") == "saved_journey":
                journey_id = session.playbook_context.get("journey_id")
            if journey_id:
                session.status = "executing"
                self._persist_session(session)
                return await self._submit_to_ai_engine(session, journey_id)
            cp_logger.warning(
                "In-process execute_plan blocked for session {} (AI_ENGINE_EXECUTION_ENABLED)",
                session_id,
            )
            session.status = "blocked"
            self._persist_session(session)
            return {
                "session_id": session_id,
                "error": "in_process_execution_disabled",
                "message": (
                    "AI_ENGINE_EXECUTION_ENABLED is set: use POST /journeys/{id}/run "
                    "for saved journeys. Ad-hoc Copilot execute_plan is disabled."
                ),
            }

        session.status = "executing"
        results = []

        # JourneyExecutorBridge -- if this session originated from a
        # saved-journey run, mirror the run into the existing ai-engine
        # JobExecution + LIVELOG framework so /api/v1/journeys/{id}/jobs
        # surfaces it identically to regular Journeys. Only mint a new
        # ``job_id`` the FIRST time we hit execute_plan; subsequent
        # resume-after-approval calls reuse the same job_id.
        bridge_journey_id: Optional[str] = None
        if (
            self._bridge is not None
            and session.playbook_context
            and session.playbook_context.get("source") == "saved_journey"
        ):
            bridge_journey_id = session.playbook_context.get("journey_id")
            if bridge_journey_id and session.job_id is None:
                try:
                    self._bridge.ensure_metadata(
                        bridge_journey_id,
                        title=(session.playbook_context.get("use_case") or {}).get("title") or bridge_journey_id,
                        solution_id=(session.playbook_context.get("use_case") or {}).get("solution_id"),
                        kind=(session.playbook_context.get("use_case") or {}).get("kind") or "user_authored",
                    )
                    session.job_id = self._bridge.start_job(
                        journey_id=bridge_journey_id,
                        plan_steps=session.plan,
                    )
                    if session.job_id:
                        self._persist_session(session)
                except Exception as _e:
                    cp_logger.warning(f"JourneyExecutorBridge bootstrap failed: {_e}")

        # Resume from where we paused if the session is mid-flight after an
        # approve_step / reject_step round-trip.
        start_index = len(session.completed_steps)
        for i in range(start_index, len(session.plan)):
            step = session.plan[i]
            step_id = step.get("id", f"s{i+1}")
            tool_name = step.get("tool", "")
            params = dict(step.get("params", {}))

            # Per-step approval gate.
            if self._step_needs_approval(step, tool_name) and step_id not in session.approved_steps:
                session.pending_step = {
                    "step_index": i,
                    "step_id": step_id,
                    "step_name": step.get("name"),
                    "tool": tool_name,
                    "params": params,
                    "rationale": step.get("rationale"),
                    "connector_api": self._tool_connector_api(tool_name),
                    "risk_level": self._tool_risk(tool_name),
                }
                session.status = "awaiting_step_approval"
                if emit_callback:
                    emit_callback({"phase": "awaiting_step_approval", **session.pending_step})
                session.add_event({"phase": "awaiting_step_approval", "step_id": step_id})
                self._persist_session(session)
                # Phase-2: flip the JobExecution row's Data.status so
                # /api/v1/journeys/{id}/jobs/{job_id}/status reports
                # awaiting_step_approval (was: stuck on in_progress).
                # The studio uses this signal to render the inline
                # PendingStepCard without a second round-trip.
                if self._bridge is not None and bridge_journey_id and session.job_id:
                    try:
                        self._bridge.mark_awaiting_approval(
                            bridge_journey_id, session.job_id, step_id,
                            pending_payload=session.pending_step,
                        )
                    except Exception as _e:
                        cp_logger.debug(f"bridge mark_awaiting_approval failed: {_e}")
                return {
                    "session_id": session_id,
                    "status": "awaiting_step_approval",
                    "pending_step": session.pending_step,
                    "steps": [r for r in (session.completed_steps + results) if r.get("step_id") != step_id],
                    "job_id": session.job_id,
                }

            if emit_callback:
                emit_callback({"phase": "executing", "step_id": step_id, "step_name": step.get("name"), "status": "running", "step_index": i, "total_steps": len(session.plan)})

            # Bridge: mark step in_progress so polling /jobs/{id}/status
            # sees movement. Set the run_context so deep sub-call sites
            # (virtual queries, connector APIs, custom-code tools) emit
            # log lines under (job_id, step_id).
            run_ctx_token = None
            if self._bridge is not None and bridge_journey_id and session.job_id:
                try:
                    self._bridge.mark_step_in_progress(
                        bridge_journey_id, session.job_id, step_id, i,
                    )
                    self._bridge.write_step_log(
                        bridge_journey_id, session.job_id, step_id,
                        level="INFO",
                        message=f"Tool {tool_name} dispatched",
                        details={"params": params},
                        source="copilot_engine",
                    )
                    from .run_context import RunContext, set_current as _set_run
                    run_ctx_token = _set_run(RunContext(
                        journey_id=bridge_journey_id,
                        job_id=session.job_id,
                        step_id=step_id,
                        bridge=self._bridge,
                        meta={"tool": tool_name},
                    ))
                except Exception as _e:
                    cp_logger.debug(f"bridge step start emit failed: {_e}")

            start = time.monotonic()
            try:
                tool_result = await self._execute_tool(tool_name, params, session.step_results, step.get("foreach"))
                elapsed = round((time.monotonic() - start) * 1000)

                step_record = {"step_id": step_id, "tool": tool_name, "status": "completed", "result_preview": self._preview(tool_result), "duration_ms": elapsed, "result": tool_result}
                session.step_results[step_id] = tool_result
                session.completed_steps.append(step_record)
                results.append(step_record)

                if emit_callback:
                    emit_callback({"phase": "executing", "step_id": step_id, "status": "completed", "result_preview": step_record["result_preview"], "duration_ms": elapsed})

                if self._bridge is not None and bridge_journey_id and session.job_id:
                    try:
                        self._bridge.mark_step_completed(
                            bridge_journey_id, session.job_id, step_id, i,
                            duration_ms=elapsed,
                            result_preview=step_record["result_preview"],
                        )
                    except Exception as _e:
                        cp_logger.debug(f"bridge step complete emit failed: {_e}")

            except Exception as e:
                cp_logger.error(f"Step {step_id} failed: {e}")
                step_record = {"step_id": step_id, "tool": tool_name, "status": "failed", "error": str(e)}
                session.completed_steps.append(step_record)
                results.append(step_record)
                if emit_callback:
                    emit_callback({"phase": "executing", "step_id": step_id, "status": "failed", "error": str(e)})
                if self._bridge is not None and bridge_journey_id and session.job_id:
                    try:
                        self._bridge.mark_step_failed(
                            bridge_journey_id, session.job_id, step_id, i,
                            error=str(e),
                        )
                    except Exception as _e:
                        cp_logger.debug(f"bridge step fail emit failed: {_e}")
            finally:
                if run_ctx_token is not None:
                    try:
                        from .run_context import reset as _reset_run
                        _reset_run(run_ctx_token)
                    except Exception:
                        pass

        session.status = "completed"
        session.pending_step = None
        summary = self._build_summary(session)

        if emit_callback:
            emit_callback({"phase": "completed", "summary": summary, "total_steps": len(results)})

        session.add_event({"phase": "completed", "steps_executed": len(results)})
        self._persist_session(session)

        # Bridge: finalise the JobExecution row. Choose complete_run vs
        # fail_run based on whether ANY step failed -- mirrors the
        # summary line the UI already shows.
        if self._bridge is not None and bridge_journey_id and session.job_id:
            try:
                steps_failed = sum(
                    1 for s in session.completed_steps if s.get("status") == "failed"
                )
                total = len(session.completed_steps)
                if steps_failed > 0:
                    self._bridge.fail_run(
                        bridge_journey_id, session.job_id,
                        error=f"{steps_failed} of {total} steps failed",
                    )
                else:
                    self._bridge.complete_run(
                        bridge_journey_id, session.job_id,
                        items_processed=total, items_total=total,
                    )
            except Exception as _e:
                cp_logger.debug(f"bridge complete_run emit failed: {_e}")

        # Return the FULL session history (not just this-call ``results``)
        # so the UI's per-step drill-down has every record after an
        # approve / resume cycle, not just the last batch.
        return {
            "session_id": session_id,
            "status": "completed",
            "steps": session.completed_steps,
            "summary": summary,
            # Surface the bridge-minted job_id so callers (Copilot Saved
            # studio) can attach SSE / status polling immediately without
            # discovering the row through /jobs.
            "job_id": session.job_id,
        }

    def approve_step(self, session_id: str, step_id: str, approved: bool = True) -> Dict[str, Any]:
        """Resolve a pending step gate. Subsequent execute_plan continues from there."""
        session = self._load_or_get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        if not session.pending_step or session.pending_step.get("step_id") != step_id:
            return {"error": f"No pending approval for step {step_id}"}
        if approved:
            if step_id not in session.approved_steps:
                session.approved_steps.append(step_id)
            session.pending_step = None
            session.status = "executing"
            session.add_event({"phase": "approved_step", "step_id": step_id})
            self._persist_session(session)
            return {"session_id": session_id, "status": "approved", "step_id": step_id}
        # rejected -> mark plan as cancelled at this step
        session.completed_steps.append({"step_id": step_id, "tool": session.pending_step.get("tool"),
                                          "status": "rejected"})
        session.pending_step = None
        session.status = "rejected"
        session.add_event({"phase": "rejected_step", "step_id": step_id})
        self._persist_session(session)
        # Phase-2: flip the JobExecution row to "rejected" so the
        # studio's status poll terminates and the card's Failed
        # counter increments. Without this the row would stay on
        # awaiting_step_approval forever even though the session
        # has effectively ended.
        if self._bridge is not None and session.job_id:
            try:
                bridge_journey_id = (
                    session.playbook_context.get("journey_id")
                    if session.playbook_context else None
                )
                if bridge_journey_id:
                    self._bridge.reject_run(
                        bridge_journey_id, session.job_id, step_id,
                        reason="step rejected by user",
                    )
            except Exception as _e:
                cp_logger.debug(f"bridge reject_run failed: {_e}")
        return {"session_id": session_id, "status": "rejected", "step_id": step_id, "job_id": session.job_id}

    def _step_needs_approval(self, step: Dict[str, Any], tool_name: str) -> bool:
        """A step needs approval if marked so OR the tool is high-risk-write OR Tool.requires_approval is set."""
        if step.get("requires_approval") is True:
            return True
        if not self._tools or not tool_name:
            return False
        tool = self._tools.get(tool_name)
        if not tool:
            return False
        try:
            from .tool_registry import RiskLevel
            if tool.risk_level == RiskLevel.HIGH_RISK_WRITE:
                return True
        except Exception:
            pass
        return bool(getattr(tool, "requires_approval", False))

    def _tool_connector_api(self, tool_name: str) -> Optional[str]:
        if not self._tools:
            return None
        tool = self._tools.get(tool_name)
        return getattr(tool, "connector_api", None) if tool else None

    def _tool_risk(self, tool_name: str) -> Optional[str]:
        if not self._tools:
            return None
        tool = self._tools.get(tool_name)
        if not tool:
            return None
        try:
            return tool.risk_level.value
        except Exception:
            return None

    async def _execute_tool(self, tool_name: str, params: Dict, context: Dict, foreach: Optional[str] = None) -> Any:
        # ``_resolve_var`` is the canonical $-expression resolver that lives
        # in the YAML tool executor module. It was historically re-exported
        # by o2c_tools but that re-export has been removed -- importing
        # straight from the source module avoids ImportError at runtime
        # (which previously made every Copilot-engine step fail).
        from src.services.plugins.yaml_tool_executor import _resolve_var as resolve_var

        resolved_params = {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("$"):
                resolved_params[k] = resolve_var(v, context)
            else:
                resolved_params[k] = v

        if foreach:
            items = resolve_var(foreach, context)
            if not isinstance(items, list):
                items = [items] if items else []
            results = []
            for item in items[:100]:
                item_ctx = {**context, "item": item}
                item_params = {}
                for k, v in params.items():
                    if isinstance(v, str) and v.startswith("$"):
                        item_params[k] = resolve_var(v, item_ctx)
                    else:
                        item_params[k] = v
                r = await self._call_tool(tool_name, item_params)
                results.append(r)
            return {"results": results, "count": len(results)}

        return await self._call_tool(tool_name, resolved_params)

    async def _call_tool(self, tool_name: str, params: Dict) -> Any:
        if self._tools:
            tool = self._tools.get(tool_name)
            if tool:
                # Phase 1 -- route through execute_with_relationships
                # so the registry normalises fan-out tools' returns
                # (matched / failure / ...) into a clean list. The
                # engine still hands the PRIMARY relationship's data
                # back to existing callers so every prompt / summary /
                # save-as-journey path keeps working unchanged.
                #
                # Falls back to ``tool.execute(**params)`` if the
                # registry surface is missing (e.g. lightweight mock
                # registries in unit tests) so the engine stays usable
                # against any object that quacks like the Tool dataclass.
                exec_with_rels = getattr(self._tools, "execute_with_relationships", None)
                if callable(exec_with_rels):
                    results = await exec_with_rels(tool_name, params)
                    if not results:
                        return {}
                    return results[0].data
                return await tool.execute(**params)

        if tool_name == "query_virtual_entity" and self._vq:
            from src.models.mapping_rule_models import VirtualQueryRequest, VirtualFilter
            entity = params.get("entity", "")
            filters = params.get("filter", {})
            vf = [VirtualFilter(field=k, operator="eq", value=v) for k, v in filters.items()] if filters else None
            req = VirtualQueryRequest(virtual_entity=entity, filters=vf, limit=params.get("limit", 500))
            resp = await self._vq.query_virtual_entity(req)
            return {"results": resp.rows, "count": len(resp.rows)}

        if tool_name == "search_enterprise_knowledge" and self._rag:
            result = await self._rag.hybrid_search(query=params.get("query", ""), limit=10)
            return {"results": [{"source": r.get("source_id"), "content": r.get("content", "")[:200]} for r in result.get("results", [])]}

        return {"error": f"Tool not found: {tool_name}"}

    async def replan(self, session_id: str, feedback: str) -> Dict[str, Any]:
        session = self._load_or_get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        completed_ctx = json.dumps([{"step": s["step_id"], "result": s.get("result_preview", "")} for s in session.completed_steps], indent=2)
        remaining = [s for s in session.plan if s.get("id") not in {c["step_id"] for c in session.completed_steps}]

        llm = self._get_llm()
        if not llm:
            return {"session_id": session_id, "revised_plan": remaining, "source": "unchanged"}

        prompt = REPLAN_PROMPT.format(
            completed_context=completed_ctx, feedback=feedback,
            remaining_steps=json.dumps(remaining, indent=2), tool_catalog=self._get_tool_catalog(),
        )

        try:
            response = llm.chat.completions.create(
                model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}],
                temperature=0.2, max_tokens=1500,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            revised = json.loads(content)
            if isinstance(revised, list):
                completed_ids = {c["step_id"] for c in session.completed_steps}
                session.plan = [s for s in session.plan if s.get("id") in completed_ids] + revised
                return {"session_id": session_id, "revised_plan": revised, "total_steps": len(session.plan)}
        except Exception as e:
            cp_logger.warning(f"Replan failed: {e}")

        return {"session_id": session_id, "revised_plan": remaining, "source": "unchanged"}

    async def save_as_journey(self, session_id: str, name: str = "", journey_store=None) -> Dict[str, Any]:
        """Persist the planned journey to the Foundry workspace DDB so it
        appears in the Journeys tab and can be re-run via
        ``POST /api/v1/journeys/{id}/run``.

        ``journey_store`` is optional - tests pass a stub; production wiring
        injects the singleton from mcp_http_gateway.
        """
        session = self._load_or_get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        import uuid as _uuid
        journey_id = f"copilot-{_uuid.uuid4().hex[:12]}"
        title = name or session.goal[:60]
        playbook_meta = (session.playbook_context or {}).get("use_case") or {}
        base_use_case_id = playbook_meta.get("use_case_id") if isinstance(playbook_meta, dict) else None
        solution_id = playbook_meta.get("solution_id") if isinstance(playbook_meta, dict) else None

        # Materialise plan steps as a single-stage JourneyDoc; richer
        # multi-stage shaping arrives once Copilot output is constrained
        # to the JourneyDoc schema (Phase 2 / strict-output planner).
        steps_doc = []
        for idx, s in enumerate(session.plan):
            step_entry: Dict[str, Any] = {
                "step_id": s.get("id") or f"s{idx+1}",
                "name": s.get("name") or f"Step {idx+1}",
                "order": idx + 1,
                "tool": s.get("tool"),
                "params": s.get("params") or {},
                "requires_approval": bool(s.get("requires_approval")),
            }
            if s.get("rationale"):
                step_entry["description"] = s["rationale"]
            if s.get("foreach"):
                step_entry["params"]["__foreach__"] = s["foreach"]
            steps_doc.append(step_entry)

        journey_doc: Dict[str, Any] = {
            "journey_id": journey_id,
            "use_case_id": base_use_case_id or journey_id,
            "title": title,
            "solution_id": solution_id or "order-to-cash",
            "description": f"Generated by Copilot from goal: {session.goal}",
            "kind": "copilot_generated",
            "tags": ["copilot"],
            "stages": [
                {
                    "stage_id": "main",
                    "name": "Main",
                    "order": 1,
                    "steps": steps_doc,
                }
            ],
            "provenance": {
                "source": "copilot",
                "session_id": session_id,
                "base_use_case_id": base_use_case_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        import yaml
        yaml_str = yaml.dump(journey_doc, default_flow_style=False, sort_keys=False)

        persisted: Optional[Dict[str, Any]] = None
        if journey_store is not None:
            try:
                persisted = await journey_store.create(journey_doc)
            except Exception as e:
                cp_logger.warning(f"Journey persistence failed for {journey_id}: {e}")

        session.add_event({"phase": "saved_as_journey", "journey_id": journey_id})
        self._persist_session(session)

        return {
            "journey_id": journey_id,
            "session_id": session_id,
            "journey_definition": journey_doc,
            "yaml": yaml_str,
            "persisted": persisted is not None,
        }

    def _preview(self, result: Any) -> str:
        if isinstance(result, dict):
            if "results" in result and isinstance(result["results"], list):
                return f"{len(result['results'])} results"
            if "count" in result:
                return f"{result['count']} items"
            if "error" in result:
                return f"Error: {result['error']}"
            keys = list(result.keys())[:5]
            return f"Dict with keys: {', '.join(keys)}"
        if isinstance(result, list):
            return f"{len(result)} items"
        return str(result)[:100]

    def _build_summary(self, session: CopilotSession) -> str:
        completed = len(session.completed_steps)
        failed = sum(1 for s in session.completed_steps if s.get("status") == "failed")
        return f"Executed {completed} steps ({failed} failed) for goal: {session.goal[:60]}"
