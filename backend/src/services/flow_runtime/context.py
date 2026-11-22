from __future__ import annotations

from typing import Any, Dict, Mapping

from src.services.flow_runtime.expression_language import evaluate_condition, evaluate_expression


class ProcessContext:
    """Resolved processor configuration (attribute expression subset)."""

    def __init__(self, properties: Mapping[str, Any]):
        self._properties = dict(properties)

    def get_property(self, name: str, default: str = "") -> str:
        val = self._properties.get(name, default)
        return str(val) if val is not None else default

    def resolve(self, template: str, flowfile_attrs: Dict[str, str]) -> str:
        return evaluate_expression(template, flowfile_attrs)

    def evaluate(self, template: str, flowfile_attrs: Dict[str, str]) -> bool:
        return evaluate_condition(template, flowfile_attrs)