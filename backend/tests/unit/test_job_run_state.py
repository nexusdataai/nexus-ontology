"""Unit tests for the JobRunState enum + transition table.

The state machine is the contract between the JourneyExecutorBridge
(which writes transitions) and the JourneyStudioView (which reads
``Data.status`` from `/jobs/{job_id}/status`). These tests pin the
allowed transitions so any future refactor surfaces breaks in CI.
"""

from __future__ import annotations

from src.services.control_plane.journey_run_state import (
    JobRunState, ALLOWED_TRANSITIONS, can_transition,
)


def test_wire_format_values() -> None:
    """Enum values are exactly the strings ``Data.status`` carries."""
    assert JobRunState.pending.value == "pending"
    assert JobRunState.in_progress.value == "in_progress"
    assert JobRunState.awaiting_step_approval.value == "awaiting_step_approval"
    assert JobRunState.completed.value == "completed"
    assert JobRunState.failed.value == "failed"
    assert JobRunState.rejected.value == "rejected"
    assert JobRunState.cancelled.value == "cancelled"


def test_terminal_set() -> None:
    terminal = JobRunState.terminal()
    assert terminal == {
        JobRunState.completed,
        JobRunState.failed,
        JobRunState.rejected,
        JobRunState.cancelled,
    }
    assert JobRunState.completed.is_terminal()
    assert JobRunState.rejected.is_terminal()
    assert not JobRunState.in_progress.is_terminal()
    assert not JobRunState.awaiting_step_approval.is_terminal()


def test_pending_can_only_transition_to_in_progress_or_cancelled() -> None:
    assert can_transition(JobRunState.pending, JobRunState.in_progress)
    assert can_transition(JobRunState.pending, JobRunState.cancelled)
    assert not can_transition(JobRunState.pending, JobRunState.completed)
    assert not can_transition(JobRunState.pending, JobRunState.rejected)
    assert not can_transition(JobRunState.pending, JobRunState.failed)


def test_in_progress_transitions() -> None:
    # Awaiting approval is the new path the engine pause wires up.
    assert can_transition(JobRunState.in_progress, JobRunState.awaiting_step_approval)
    # All terminal states are reachable from in_progress.
    assert can_transition(JobRunState.in_progress, JobRunState.completed)
    assert can_transition(JobRunState.in_progress, JobRunState.failed)
    assert can_transition(JobRunState.in_progress, JobRunState.cancelled)
    # in_progress cannot self-loop or jump to pending.
    assert not can_transition(JobRunState.in_progress, JobRunState.in_progress)
    assert not can_transition(JobRunState.in_progress, JobRunState.pending)


def test_awaiting_approval_branches_into_resume_reject_or_cancel() -> None:
    assert can_transition(JobRunState.awaiting_step_approval, JobRunState.in_progress)
    assert can_transition(JobRunState.awaiting_step_approval, JobRunState.rejected)
    assert can_transition(JobRunState.awaiting_step_approval, JobRunState.cancelled)
    # Cannot leap directly from approval-wait to completed / failed.
    assert not can_transition(JobRunState.awaiting_step_approval, JobRunState.completed)
    assert not can_transition(JobRunState.awaiting_step_approval, JobRunState.failed)


def test_terminal_states_have_no_outgoing_transitions() -> None:
    for terminal in JobRunState.terminal():
        for other in JobRunState:
            assert not can_transition(terminal, other), (
                f"{terminal} should not transition to {other}"
            )


def test_no_self_loops_in_allowed_transitions_table() -> None:
    """Defensive: every state's allowed set must exclude itself."""
    for state, allowed in ALLOWED_TRANSITIONS.items():
        assert state not in allowed, f"{state} self-loop slipped in"
