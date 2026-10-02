"""Unit tests for the Phase-1 ConnectionDoc validation rules added to
:class:`JourneyDoc.validate_strict`.

Each test constructs a minimal JourneyDoc with two steps and exercises a
specific rule. The validation reports never raise; tests assert on the
``ValidationReport.errors`` / ``.warnings`` lists.
"""

from __future__ import annotations

import pytest

from src.models.automation_models import (
    ConnectionDoc,
    JourneyDoc,
    StageDoc,
    StepDoc,
)


def _journey(connections, *, with_bucket="default"):
    """Tiny two-step journey: s1 (find_things) -> s2 (consume_thing)."""
    return JourneyDoc(
        use_case_id="phase1.test",
        title="Phase 1 test",
        solution_id="builder",
        bucket=with_bucket,
        stages=[
            StageDoc(
                stage_id="main",
                name="Main",
                order=1,
                steps=[
                    StepDoc(step_id="s1", name="s1", order=1, tool="find_things"),
                    StepDoc(step_id="s2", name="s2", order=2, tool="consume_thing"),
                ],
                connections=connections,
            ),
        ],
    )


def _registries(*, with_relationships=True, with_schemas=True):
    """Caller-supplied tool meta the validator expects."""
    tool_relationships = (
        {"find_things": ["matched", "no_match"], "consume_thing": ["success"]}
        if with_relationships
        else None
    )
    tool_param_schemas = (
        {
            "find_things": {"type": "object", "properties": {}, "required": []},
            "consume_thing": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        }
        if with_schemas
        else None
    )
    return tool_relationships, tool_param_schemas


def test_valid_connection_passes_clean():
    j = _journey([
        ConnectionDoc(from_step="s1", from_relationship="matched", to_step="s2", to_param="customer_id"),
    ])
    rels, schemas = _registries()
    report = j.validate_strict(known_tools={"find_things", "consume_thing"},
                               tool_relationships=rels, tool_param_schemas=schemas)
    assert not report.errors, report.errors


def test_connection_unknown_relationship_emits_warning():
    j = _journey([
        ConnectionDoc(from_step="s1", from_relationship="totally_made_up", to_step="s2", to_param="customer_id"),
    ])
    rels, schemas = _registries()
    report = j.validate_strict(known_tools={"find_things", "consume_thing"},
                               tool_relationships=rels, tool_param_schemas=schemas)
    # Phase 1: warns rather than errors so the canvas can keep emitting
    # connections even when the source handle was originally a hint key
    # rather than a declared relationship.
    error_codes = [iss.code for iss in report.errors]
    warning_codes = [iss.code for iss in report.warnings]
    assert "connection_unknown_relationship" not in error_codes
    assert "connection_unknown_relationship" in warning_codes


def test_connection_unknown_to_param_emits_warning():
    j = _journey([
        ConnectionDoc(from_step="s1", from_relationship="matched", to_step="s2", to_param="never_heard_of_this"),
    ])
    rels, schemas = _registries()
    report = j.validate_strict(known_tools={"find_things", "consume_thing"},
                               tool_relationships=rels, tool_param_schemas=schemas)
    error_codes = [iss.code for iss in report.errors]
    warning_codes = [iss.code for iss in report.warnings]
    assert "connection_unknown_param" not in error_codes
    assert "connection_unknown_param" in warning_codes


def test_connection_unknown_source_step_raises_error():
    j = _journey([
        ConnectionDoc(from_step="ghost", from_relationship="matched", to_step="s2", to_param="customer_id"),
    ])
    rels, schemas = _registries()
    report = j.validate_strict(known_tools={"find_things", "consume_thing"},
                               tool_relationships=rels, tool_param_schemas=schemas)
    codes = [iss.code for iss in report.errors]
    assert "connection_unknown_source" in codes


def test_connection_unknown_target_step_raises_error():
    j = _journey([
        ConnectionDoc(from_step="s1", from_relationship="matched", to_step="ghost", to_param="customer_id"),
    ])
    rels, schemas = _registries()
    report = j.validate_strict(known_tools={"find_things", "consume_thing"},
                               tool_relationships=rels, tool_param_schemas=schemas)
    codes = [iss.code for iss in report.errors]
    assert "connection_unknown_target" in codes


def test_duplicate_input_producer_raises_error():
    j = _journey([
        ConnectionDoc(from_step="s1", from_relationship="matched", to_step="s2", to_param="customer_id"),
        ConnectionDoc(from_step="s1", from_relationship="no_match", to_step="s2", to_param="customer_id"),
    ])
    rels, schemas = _registries()
    report = j.validate_strict(known_tools={"find_things", "consume_thing"},
                               tool_relationships=rels, tool_param_schemas=schemas)
    codes = [iss.code for iss in report.errors]
    assert "duplicate_input_producer" in codes


def test_self_loop_rejected():
    j = _journey([
        ConnectionDoc(from_step="s1", from_relationship="matched", to_step="s1", to_param="customer_id"),
    ])
    rels, schemas = _registries()
    report = j.validate_strict(known_tools={"find_things", "consume_thing"},
                               tool_relationships=rels, tool_param_schemas=schemas)
    codes = [iss.code for iss in report.errors]
    assert "connection_self_loop" in codes


def test_unconsumed_relationship_emits_warning():
    """``no_match`` declared on s1 but not consumed; warning expected (not error)."""
    j = _journey([
        ConnectionDoc(from_step="s1", from_relationship="matched", to_step="s2", to_param="customer_id"),
    ])
    rels, schemas = _registries()
    report = j.validate_strict(known_tools={"find_things", "consume_thing"},
                               tool_relationships=rels, tool_param_schemas=schemas)
    warning_codes = [iss.code for iss in report.warnings]
    assert "relationship_not_consumed" in warning_codes
    # And no error.
    assert "relationship_not_consumed" not in [iss.code for iss in report.errors]


def test_validation_without_registries_skips_phase1_checks():
    """When tool_relationships / tool_param_schemas are not supplied, the
    Phase-1 checks degrade gracefully -- no false negatives, no crash.
    """
    j = _journey([
        ConnectionDoc(from_step="s1", from_relationship="anything", to_step="s2", to_param="anything"),
    ])
    report = j.validate_strict()
    # No relationship-shape errors because the validator had no map.
    codes = [iss.code for iss in report.errors]
    assert "connection_unknown_relationship" not in codes
    assert "connection_unknown_param" not in codes


def test_bucket_defaults_to_default_when_omitted():
    j = JourneyDoc(
        use_case_id="phase1.bucket",
        title="x",
        solution_id="builder",
        stages=[],
    )
    assert j.bucket == "default"
