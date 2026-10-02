"""Unit tests for JourneyDoc.execution_mode discriminator + the
sequential-mode validate_strict checks added in the AI Engine Execution
Mode plan.
"""

from __future__ import annotations

import pytest

from src.models.automation_models import (
    ConnectionDoc,
    JourneyDoc,
    StageDoc,
    StepDoc,
)


def _journey(*, mode: str, stage_steps, stage_connections=None):
    return JourneyDoc(
        use_case_id="exec.mode.test",
        title="Exec mode test",
        solution_id="builder",
        execution_mode=mode,
        stages=[
            StageDoc(
                stage_id="main",
                name="Main",
                order=1,
                steps=stage_steps,
                connections=stage_connections or [],
            ),
        ],
    )


def test_execution_mode_defaults_to_dataflow_for_back_compat():
    j = JourneyDoc(
        use_case_id="bc.default",
        title="default",
        solution_id="builder",
        stages=[],
    )
    assert j.execution_mode == "dataflow"


def test_execution_mode_accepts_only_sequential_and_dataflow():
    with pytest.raises(Exception):
        JourneyDoc(
            use_case_id="bad.mode",
            title="bad",
            solution_id="builder",
            stages=[],
            execution_mode="bogus",
        )


def test_sequential_journey_with_connections_errors():
    j = _journey(
        mode="sequential",
        stage_steps=[
            StepDoc(step_id="s1", name="s1", order=1, tool="find_x"),
            StepDoc(step_id="s2", name="s2", order=2, tool="use_x"),
        ],
        stage_connections=[
            ConnectionDoc(from_step="s1", from_relationship="success",
                          to_step="s2", to_param="x"),
        ],
    )
    report = j.validate_strict()
    codes = [iss.code for iss in report.errors]
    assert "sequential_journey_has_connections" in codes


def test_sequential_journey_with_steps_substitution_errors():
    j = _journey(
        mode="sequential",
        stage_steps=[
            StepDoc(step_id="s1", name="s1", order=1, tool="find_x"),
            StepDoc(step_id="s2", name="s2", order=2, tool="use_x",
                    params={"x": "${steps.s1.results.0.customer_id}"}),
        ],
    )
    report = j.validate_strict()
    codes = [iss.code for iss in report.errors]
    assert "sequential_journey_has_step_substitution" in codes


def test_sequential_journey_allows_inputs_and_context_namespaces():
    """Only the ``steps`` namespace is forbidden in sequential mode.
    ``${inputs.X}``, ``${params.X}``, ``${context.X}`` remain valid.
    """
    j = _journey(
        mode="sequential",
        stage_steps=[
            StepDoc(step_id="s1", name="s1", order=1, tool="t1",
                    params={"horizon": "${inputs.horizon_days}",
                            "actor":   "${context.user}"}),
        ],
    )
    report = j.validate_strict()
    codes = [iss.code for iss in report.errors]
    assert "sequential_journey_has_step_substitution" not in codes


def test_dataflow_journey_with_connections_is_clean():
    j = _journey(
        mode="dataflow",
        stage_steps=[
            StepDoc(step_id="s1", name="s1", order=1, tool="find_x"),
            StepDoc(step_id="s2", name="s2", order=2, tool="use_x"),
        ],
        stage_connections=[
            ConnectionDoc(from_step="s1", from_relationship="success",
                          to_step="s2", to_param="x"),
        ],
    )
    report = j.validate_strict()
    codes = [iss.code for iss in report.errors]
    assert "sequential_journey_has_connections" not in codes
    assert "sequential_journey_has_step_substitution" not in codes
