"""
JobRunState -- typed lifecycle states for a Copilot-saved-journey
JobExecution row in the transformation-system DDB.

The bridge (`JourneyExecutorBridge`) drives transitions and records each
one as a JOBTXN# item so the studio surface can render a full audit
trail. The enum values are wire-format strings matching what the legacy
``/api/v1/journeys/{id}/jobs/{job_id}/status`` endpoint already returns,
so no UI translation layer is needed.

State diagram
-------------

    pending --> in_progress
    in_progress --> awaiting_step_approval (step requires_approval)
    awaiting_step_approval --> in_progress  (user approves)
    awaiting_step_approval --> rejected     (user rejects)
    in_progress --> completed               (all steps ok)
    in_progress --> failed                  (any step failed)
    in_progress --> cancelled               (user cancel)

Terminal states: completed, failed, rejected, cancelled. The UI stops
polling when one of these is observed.
"""

from __future__ import annotations

from enum import Enum
from typing import Set


class JobRunState(str, Enum):
    """Wire-format state names for a JobExecution row."""

    pending = "pending"
    in_progress = "in_progress"
    awaiting_step_approval = "awaiting_step_approval"
    completed = "completed"
    failed = "failed"
    rejected = "rejected"
    cancelled = "cancelled"

    @classmethod
    def terminal(cls) -> Set["JobRunState"]:
        return {cls.completed, cls.failed, cls.rejected, cls.cancelled}

    def is_terminal(self) -> bool:
        return self in self.terminal()


# Allowed transitions. Wholly defensive -- the bridge never mutates a
# row that is already terminal, and the engine wires only those
# transitions the user actually triggers. Listed here so the test
# suite + future state-machine reviewers see the invariants in one
# place.
ALLOWED_TRANSITIONS = {
    JobRunState.pending: {
        JobRunState.in_progress,
        JobRunState.cancelled,  # immediate cancel before any step ran
    },
    JobRunState.in_progress: {
        JobRunState.awaiting_step_approval,
        JobRunState.completed,
        JobRunState.failed,
        JobRunState.cancelled,
    },
    JobRunState.awaiting_step_approval: {
        JobRunState.in_progress,  # approve
        JobRunState.rejected,
        JobRunState.cancelled,
    },
    # Terminal states cannot transition further; the bridge skips writes
    # rather than raising so a duplicate approve / reject is harmless.
    JobRunState.completed: set(),
    JobRunState.failed: set(),
    JobRunState.rejected: set(),
    JobRunState.cancelled: set(),
}


def can_transition(from_state: JobRunState, to_state: JobRunState) -> bool:
    """Return True iff ``from_state -> to_state`` is allowed."""
    if from_state == to_state:
        return False
    return to_state in ALLOWED_TRANSITIONS.get(from_state, set())
