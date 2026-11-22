"""Plain-Python processor runner for Nexus Flow journeys (one step = one processor)."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from src.services.flow_runtime.nexus_flow_journey import (
    flowfile_to_state,
    run_processor_step,
    state_to_flowfile,
)
from src.services.flow_runtime.flowfile import FlowFile


class NexusFlowProcessor:
    def __init__(self, *, flow_steps: List[Dict[str, Any]], log_callback: Optional[Callable[..., None]] = None):
        self._steps = {s["id"]: s for s in flow_steps}
        self._log = log_callback or (lambda *a, **k: None)
        self._flow_state: Dict[str, Any] = flowfile_to_state(
            FlowFile(content=b"{}", attributes={"mime.type": "application/json"})
        )

    def run_step(self, step_id: str) -> Dict[str, Any]:
        step = self._steps.get(step_id)
        if not step:
            return {"status": "error", "message": f"Unknown flow step: {step_id}"}
        proc_type = step["processorType"]
        params = step.get("params") or {}
        self._log("INFO", f"Running processor {proc_type}", step_id)
        out = run_processor_step(proc_type, params, self._flow_state)
        if out.get("status") != "ok":
            return {"status": "error", "message": out.get("error", "processor step failed")}
        self._flow_state = out["flowState"]
        ff = state_to_flowfile(self._flow_state)
        return {
            "status": "completed",
            "step_id": step_id,
            "processorType": proc_type,
            "relationship": out.get("relationship"),
            "attributes": ff.attributes,
        }