"""
Regression tests for FoundryWorkspaceRepository._to_attr().

These tests guard against the silent data-corruption bug observed in
prod where a Pydantic FieldMap model passed through _to_attr() fell
into the str() fallback and was persisted to DynamoDB as a string repr
("source_field='X' target_field='Y' transform=None default_value=None")
instead of a proper Map. After the corruption, MappingRuleResponse
validation rejected the round-trip on read, taking out the
/api/v1/control-plane/virtual/entities endpoint.

The fix added an explicit branch in _to_attr() that detects Pydantic v2
BaseModels (via the model_dump attribute) and recursively serializes
their dict form. These tests pin that behavior.
"""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.repositories.foundry_workspace_repository import FoundryWorkspaceRepository


def test_to_attr_serializes_pydantic_model_as_map():
    """A Pydantic BaseModel must round-trip as a DynamoDB Map, not a String."""
    from src.models.mapping_rule_models import FieldMap

    fm = FieldMap(source_field="account_id", target_field="account_id")

    result = FoundryWorkspaceRepository._to_attr(fm)

    assert "M" in result, (
        f"Pydantic model must be serialized as a Map, got: {result}"
    )
    assert "S" not in result, (
        f"Pydantic model must NOT fall through to str() repr, got: {result}"
    )
    # FieldMap dumps with by_alias=True (matching mapping_rule_service.create()
    # at line 126), so keys are camelCase on the wire.
    assert result["M"]["sourceField"] == {"S": "account_id"}
    assert result["M"]["targetField"] == {"S": "account_id"}


def test_to_attr_serializes_list_of_pydantic_models_as_list_of_maps():
    """List[FieldMap] (the exact shape on the corruption path) must produce L of M."""
    from src.models.mapping_rule_models import FieldMap

    field_maps = [
        FieldMap(source_field="id", target_field="id"),
        FieldMap(source_field="name", target_field="name"),
    ]

    result = FoundryWorkspaceRepository._to_attr(field_maps)

    assert "L" in result
    assert len(result["L"]) == 2
    for entry in result["L"]:
        assert "M" in entry, (
            f"each list entry must be a Map (the bug serialized them as Strings), got: {entry}"
        )
        assert "sourceField" in entry["M"]
        assert "targetField" in entry["M"]


def test_to_attr_plain_dict_still_works():
    """Regression guard: plain dicts must continue to work unchanged."""
    result = FoundryWorkspaceRepository._to_attr({"a": 1, "b": "two"})
    assert result == {"M": {"a": {"N": "1"}, "b": {"S": "two"}}}


def test_to_attr_unknown_object_still_falls_through_to_string():
    """A truly opaque object (no model_dump) keeps the str() fallback."""

    class Opaque:
        def __str__(self) -> str:
            return "opaque-value"

    result = FoundryWorkspaceRepository._to_attr(Opaque())
    assert result == {"S": "opaque-value"}
