"""
YAML Journey Runner REST API.

Four endpoints surface the :class:`YamlJourneyRunner`:

  * ``POST   /api/v1/yaml-journeys/run``                  -- start a run
  * ``POST   /api/v1/yaml-journeys/{run_id}/approve-step``-- resume after pause
  * ``GET    /api/v1/yaml-journeys/{run_id}``             -- inspect state
  * ``GET    /api/v1/yaml-journeys``                       -- list recent runs

The prefix is ``/api/v1/yaml-journeys`` rather than the more obvious
``/api/v1/journeys/yaml`` because the existing
:pymod:`src.apis.journey_api` router mounted at ``/api/v1/journeys``
declares a wildcard ``GET /{journey_id}`` that would capture
``/api/v1/journeys/yaml`` and route it to the legacy journey loader.

``POST /run`` accepts the journey either as inline YAML text (``yaml``)
or as a JSON-decoded object (``journey``); exactly one MUST be provided.
The response envelope mirrors the Copilot ``awaiting_step_approval``
shape so the existing UI handler can render the pending-step card
without modification.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import yaml as _yaml
from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

from src.models.automation_models import JourneyDoc

yja_logger = logger.bind(component="yaml-journey-api")

router = APIRouter(prefix="/api/v1/yaml-journeys", tags=["YAML Journey"])

_runner = None  # set by :func:`configure`


def configure(runner) -> None:
    """Inject the live :class:`YamlJourneyRunner` from the gateway."""
    global _runner
    _runner = runner


def _check() -> None:
    if _runner is None:
        raise HTTPException(status_code=503, detail="YAML journey runner not initialized")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    """Body of ``POST /run``.

    Exactly one of ``yaml`` (raw YAML text) or ``journey`` (already
    parsed dict) MUST be supplied. ``inputs`` is the top-level inputs
    dict the journey expects.
    """

    yaml: Optional[str] = None
    journey: Optional[Dict[str, Any]] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    auto_approve_steps: List[str] = Field(default_factory=list)
    user: Optional[str] = None


class ApproveStepRequest(BaseModel):
    """Body of ``POST /{run_id}/approve-step``."""

    step_id: str
    approved: bool = True
    user: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_journey(req: RunRequest) -> JourneyDoc:
    """Materialise a :class:`JourneyDoc` from either request shape.

    Raises HTTPException(422) with a structured ``detail`` so the caller
    can surface the exact parse / validation error.
    """
    if req.yaml is None and req.journey is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "missing_body", "message": "provide either 'yaml' or 'journey'"},
        )
    if req.yaml is not None and req.journey is not None:
        raise HTTPException(
            status_code=422,
            detail={"code": "ambiguous_body", "message": "provide exactly one of 'yaml' or 'journey'"},
        )

    raw: Any
    if req.yaml is not None:
        try:
            raw = _yaml.safe_load(req.yaml)
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail={"code": "yaml_parse_error", "message": str(e)},
            )
        if not isinstance(raw, dict):
            raise HTTPException(
                status_code=422,
                detail={"code": "yaml_root_not_object", "message": "top-level YAML must be a mapping"},
            )
    else:
        raw = req.journey

    try:
        return JourneyDoc.model_validate(raw)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail={"code": "journey_schema_error", "message": str(e)},
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/run")
async def run_journey(req: RunRequest) -> Dict[str, Any]:
    """Start a new YAML-journey run; execute until pause or terminal."""
    _check()
    journey = _parse_journey(req)
    envelope = await _runner.run(
        journey=journey,
        inputs=req.inputs,
        user=req.user or "ai-engine",
        auto_approve_steps=req.auto_approve_steps,
    )
    if envelope.get("status") == "failed" and envelope.get("run_id") is None:
        # Validation-only failure -- caller gets 422 with the report.
        raise HTTPException(status_code=422, detail=envelope)
    return envelope


@router.post("/{run_id}/approve-step")
async def approve_step(run_id: str, req: ApproveStepRequest) -> Dict[str, Any]:
    """Approve (or reject) the pending step and resume the run."""
    _check()
    envelope = await _runner.resume(
        run_id=run_id,
        step_id=req.step_id,
        approved=req.approved,
        user=req.user or "ai-engine",
    )
    if envelope.get("status") == "failed" and envelope.get("error") == "run not found":
        raise HTTPException(status_code=404, detail=envelope)
    return envelope


@router.get("/{run_id}")
async def get_run(run_id: str) -> Dict[str, Any]:
    """Return the full persisted state for a run."""
    _check()
    session = _runner.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "run_not_found", "run_id": run_id})
    return {
        "run_id": session.run_id,
        "status": session.status,
        "kind": session.kind,
        "user": session.user,
        "journey": session.journey,
        "inputs": session.inputs,
        "step_results": session.step_results,
        "completed_steps": session.completed_step_ids,
        "approved_steps": session.approved_steps,
        "rejected_steps": session.rejected_steps,
        "pending_step": session.pending_step,
        "error": session.error,
        "events": session.events,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


@router.get("")
async def list_runs(limit: int = Query(default=50, ge=1, le=200)) -> Dict[str, Any]:
    """List recent YAML-journey runs (delegates to the session store)."""
    _check()
    return {"runs": _runner.list_recent(limit=limit), "limit": limit}
