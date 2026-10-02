"""
Policy & Guardrail Engine for the AI Control Plane.

Validates every tool call before execution against:
  - Risk level thresholds (based on intent classification)
  - Step budget (max actions per request)
  - Write operation gates (require explicit approval for high-risk writes)
  - Field-level restrictions (block modification of sensitive fields)
  - Loop detection (prevent repeated identical tool calls)

This is the most critical safety layer — the LLM decides what to do,
but the PolicyEngine enforces what is allowed.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from .tool_registry import RiskLevel, ToolRegistry

cp_logger = logger.bind(component="control-plane")


class PolicyViolation(Exception):
    def __init__(self, reason: str, tool_name: str = "", policy: str = ""):
        self.reason = reason
        self.tool_name = tool_name
        self.policy = policy
        super().__init__(reason)


@dataclass
class PolicyContext:
    """Tracks state across an agent execution for policy enforcement."""
    intent_risk: str = "read_only"
    max_steps: int = 10
    max_write_actions: int = 3
    steps_taken: int = 0
    write_actions_taken: int = 0
    tool_call_history: List[str] = field(default_factory=list)
    blocked_fields: Set[str] = field(default_factory=lambda: {
        "OwnerId", "CreatedById", "SystemModstamp", "IsDeleted",
    })
    require_approval_for: Set[str] = field(default_factory=lambda: {
        RiskLevel.HIGH_RISK_WRITE.value,
    })
    approved_actions: Set[str] = field(default_factory=set)
    dry_run: bool = False


RISK_HIERARCHY = {
    "read_only": RiskLevel.READ_ONLY,
    "low_risk_write": RiskLevel.LOW_RISK_WRITE,
    "high_risk_write": RiskLevel.HIGH_RISK_WRITE,
    "cross_system": RiskLevel.HIGH_RISK_WRITE,
}


class PolicyEngine:
    """Validates tool calls against security policies before execution."""

    def __init__(self, tool_registry: ToolRegistry):
        self._tools = tool_registry

    def validate(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: PolicyContext,
    ) -> None:
        """Validate a tool call. Raises PolicyViolation if blocked."""
        tool = self._tools.get(tool_name)
        if not tool:
            raise PolicyViolation(f"Tool '{tool_name}' not registered", tool_name, "unknown_tool")

        if context.steps_taken >= context.max_steps:
            raise PolicyViolation(
                f"Step budget exhausted ({context.max_steps} steps)",
                tool_name, "step_budget",
            )

        max_allowed = RISK_HIERARCHY.get(context.intent_risk, RiskLevel.READ_ONLY)
        risk_order = [RiskLevel.READ_ONLY, RiskLevel.LOW_RISK_WRITE, RiskLevel.HIGH_RISK_WRITE]
        if risk_order.index(tool.risk_level) > risk_order.index(max_allowed):
            raise PolicyViolation(
                f"Tool '{tool_name}' requires {tool.risk_level.value} but intent is '{context.intent_risk}'",
                tool_name, "risk_level",
            )

        if tool.risk_level in (RiskLevel.LOW_RISK_WRITE, RiskLevel.HIGH_RISK_WRITE):
            if context.write_actions_taken >= context.max_write_actions:
                raise PolicyViolation(
                    f"Write action limit reached ({context.max_write_actions})",
                    tool_name, "write_limit",
                )

        if tool.risk_level == RiskLevel.HIGH_RISK_WRITE:
            if tool.risk_level.value in context.require_approval_for:
                if tool_name not in context.approved_actions:
                    raise PolicyViolation(
                        f"Tool '{tool_name}' requires approval for high-risk write",
                        tool_name, "approval_required",
                    )

        # Per-tool approval gate. The Tool dataclass exposes a
        # `requires_approval` flag; honour it independently of risk-level so
        # automation playbooks can mark a step as requiring approval even
        # when the underlying tool is low-risk (e.g. send_dunning_notice).
        if getattr(tool, "requires_approval", False) and tool_name not in context.approved_actions:
            raise PolicyViolation(
                f"Tool '{tool_name}' is marked requires_approval=True - explicit approval required",
                tool_name, "approval_required",
            )

        self._check_field_restrictions(tool_name, arguments, context)
        self._check_loop_detection(tool_name, arguments, context)

    def _check_field_restrictions(
        self, tool_name: str, arguments: Dict[str, Any], context: PolicyContext,
    ) -> None:
        if tool_name != "query_table":
            return
        filters = arguments.get("filters", [])
        columns = arguments.get("columns", [])
        for col_name in columns or []:
            if col_name in context.blocked_fields:
                raise PolicyViolation(
                    f"Column '{col_name}' is restricted",
                    tool_name, "field_restriction",
                )

    def _check_loop_detection(
        self, tool_name: str, arguments: Dict[str, Any], context: PolicyContext,
    ) -> None:
        call_sig = f"{tool_name}:{sorted(arguments.items())}"
        recent = context.tool_call_history[-5:]
        identical = sum(1 for h in recent if h == call_sig)
        if identical >= 2:
            raise PolicyViolation(
                f"Repeated identical call to '{tool_name}' detected (possible loop)",
                tool_name, "loop_detection",
            )
        context.tool_call_history.append(call_sig)

    def record_execution(self, tool_name: str, context: PolicyContext) -> None:
        """Record a successful tool execution for budget tracking."""
        context.steps_taken += 1
        tool = self._tools.get(tool_name)
        if tool and tool.risk_level in (RiskLevel.LOW_RISK_WRITE, RiskLevel.HIGH_RISK_WRITE):
            context.write_actions_taken += 1
