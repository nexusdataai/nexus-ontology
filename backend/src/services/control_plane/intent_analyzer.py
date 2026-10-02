"""
Intent & Risk Analyzer for the AI Control Plane.

Classifies user requests before the agent loop begins:
  - read_only: Querying data, inspecting schemas, asking questions
  - low_risk_write: Creating notes, updating non-critical fields
  - high_risk_write: Financial changes, customer creation, record deletion
  - cross_system: Changes spanning multiple systems (Salesforce + ERP)

Uses a fast LLM call with a classification prompt.
Falls back to keyword heuristics if LLM is unavailable.
"""

import re
from typing import Optional

from loguru import logger

from .llm_client import LLMClient

cp_logger = logger.bind(component="control-plane")

VALID_INTENTS = {"read_only", "low_risk_write", "high_risk_write", "cross_system"}

CLASSIFICATION_PROMPT = """Classify the following user request into exactly one category.
Return ONLY the category name, nothing else.

Categories:
- read_only: Querying, searching, listing, inspecting, describing data or schemas
- low_risk_write: Creating notes, adding tags, updating descriptions or non-critical fields
- high_risk_write: Creating/deleting records, updating financial fields (credit, revenue, billing), changing ownership
- cross_system: Operations that span multiple systems (e.g. "sync to ERP", "update Salesforce and Oracle")

User request: {question}

Category:"""


async def analyze_intent_async(question: str, llm: Optional[LLMClient] = None) -> str:
    """Async intent analysis -- tries fast heuristic first, LLM only if ambiguous."""
    heuristic = _heuristic_intent(question)
    if heuristic:
        cp_logger.debug(f"Intent from heuristic: {heuristic}")
        return heuristic

    if llm and llm.available:
        try:
            result = await llm.achat(
                messages=[{"role": "user", "content": CLASSIFICATION_PROMPT.format(question=question)}],
                max_tokens=20,
                temperature=0.0,
            )
            intent = result["content"].strip().lower().replace(" ", "_")
            if intent in VALID_INTENTS:
                return intent
        except Exception as e:
            cp_logger.warning(f"LLM intent classification failed: {e}")
    return _keyword_fallback(question)


def _heuristic_intent(question: str) -> Optional[str]:
    """Fast keyword-based classification for obvious cases (no LLM needed)."""
    q = question.lower()
    write_signals = ["create", "update", "delete", "modify", "change", "set", "override", "hold", "transfer"]
    cross_signals = ["sync", "replicate", "propagate", "both systems", "salesforce and oracle", "sap and oracle"]
    if any(w in q for w in cross_signals):
        return "cross_system"
    if any(w in q for w in write_signals):
        return "low_risk_write"
    read_signals = ["what", "which", "how", "where", "who", "list", "show", "get", "find", "search",
                     "describe", "explain", "count", "source of truth", "schema", "table", "field"]
    if any(w in q for w in read_signals):
        return "read_only"
    return None


def analyze_intent(question: str, llm: Optional[LLMClient] = None) -> str:
    heuristic = _heuristic_intent(question)
    if heuristic:
        return heuristic
    if llm and llm.available:
        try:
            result = llm.chat(
                messages=[{"role": "user", "content": CLASSIFICATION_PROMPT.format(question=question)}],
                max_tokens=20,
                temperature=0.0,
            )
            intent = result["content"].strip().lower().replace(" ", "_")
            if intent in VALID_INTENTS:
                return intent
        except Exception as e:
            cp_logger.debug(f"LLM intent classification failed, using heuristics: {e}")

    return _heuristic_classify(question)


_WRITE_PATTERNS = re.compile(
    r"\b(create|update|delete|remove|insert|modify|change|set|assign|transfer|move)\b",
    re.IGNORECASE,
)
_HIGH_RISK_PATTERNS = re.compile(
    r"\b(credit|revenue|billing|financial|payment|delete|remove|ownership|merge)\b",
    re.IGNORECASE,
)
_CROSS_SYSTEM_PATTERNS = re.compile(
    r"\b(sync|erp|oracle|sap|cross.system|both.systems)\b",
    re.IGNORECASE,
)


def _heuristic_classify(question: str) -> str:
    if _CROSS_SYSTEM_PATTERNS.search(question):
        return "cross_system"
    if _HIGH_RISK_PATTERNS.search(question):
        return "high_risk_write"
    if _WRITE_PATTERNS.search(question):
        return "low_risk_write"
    return "read_only"
