"""
Linear Nexus journey execution for catalog flow processors.

Each step is a plain Python class (flow_processors), run one at a time in
topological order.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional

from src.models.data_flow_models import DataFlowGraph, DataFlowNode
from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.dag_runner import _topo_order
from src.services.flow_runtime.flow_record import FlowRecord
from src.services.flow_runtime.processor import get_processor_class
from src.services.flow_runtime.processor_ids import canonical_processor_id


def _ensure_processors():
    import src.services.flow_processors  # noqa: F401


def record_to_state(ff: FlowRecord) -> Dict[str, Any]:
    return {
        "contentB64": base64.b64encode(ff.content).decode("ascii"),
        "attributes": dict(ff.attributes),
    }


def state_to_record(state: Dict[str, Any]) -> FlowRecord:
    raw = base64.b64decode(state.get("contentB64") or b"")
    return FlowRecord(content=raw, attributes=dict(state.get("attributes") or {}))


def compile_graph_to_flow_steps(graph: DataFlowGraph) -> List[Dict[str, Any]]:
    order = _topo_order(graph)
    if order is None:
        return []
    by_id: Dict[str, DataFlowNode] = {n.id: n for n in graph.nodes}
    steps: List[Dict[str, Any]] = []
    for idx, nid in enumerate(order):
        node = by_id.get(nid)
        if node is None or not (
            node.type.startswith("nexus.") or node.type.startswith("nifi.")
        ):
            continue
        ptype = canonical_processor_id(node.type)
        steps.append(
            {
                "id": nid,
                "name": (node.ui.label if node.ui else None) or node.type,
                "processorType": ptype,
                "params": dict(node.params or {}),
                "order": idx,
            }
        )
    return steps


def run_processor_step(
    processor_type: str,
    params: Dict[str, Any],
    flow_state: Dict[str, Any],
) -> Dict[str, Any]:
    """Single journey step: one Python processor, one FlowRecord."""
    _ensure_processors()
    from src.services.flow_runtime.session import ProcessSession

    proc_cls = get_processor_class(processor_type)
    if proc_cls is None:
        return {"status": "error", "error": f"no python processor for {processor_type}"}

    ff = state_to_record(flow_state)
    session = ProcessSession()
    session.set_inbound([ff])
    ctx = ProcessContext(params or {})
    try:
        proc = proc_cls()
        proc.on_trigger(ctx, session)
        by_rel = session.commit()
        success = by_rel.get("success") or []
        if success:
            return {"status": "ok", "relationship": "success", "flowState": record_to_state(success[0])}
        for rel, ffs in by_rel.items():
            if ffs:
                return {"status": "ok", "relationship": rel, "flowState": record_to_state(ffs[0])}
        return {"status": "error", "error": "processor produced no output records"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:500]}


def run_nexus_flow_linear(
    graph: DataFlowGraph,
    *,
    initial_records: Optional[List[FlowRecord]] = None,
) -> Dict[str, Any]:
    steps = compile_graph_to_flow_steps(graph)
    if not steps:
        return {"ok": False, "error": "no flow processor steps in graph", "nodeStats": []}

    if initial_records:
        state = record_to_state(initial_records[0])
    else:
        state = record_to_state(FlowRecord(content=b"{}", attributes={"mime.type": "application/json"}))

    node_stats: List[Dict[str, Any]] = []
    for step in steps:
        out = run_processor_step(step["processorType"], step["params"], state)
        if out.get("status") != "ok":
            node_stats.append(
                {
                    "nodeId": step["id"],
                    "type": step["processorType"],
                    "error": out.get("error"),
                }
            )
            return {
                "ok": False,
                "error": out.get("error", "step failed"),
                "nodeStats": node_stats,
                "executionMode": "nexus_journey_linear",
            }
        state = out["flowState"]
        node_stats.append({"nodeId": step["id"], "type": step["processorType"], "relationship": out.get("relationship")})

    ff = state_to_record(state)
    return {
        "ok": True,
        "terminalCount": 1,
        "terminalAttributes": [ff.attributes],
        "nodeStats": node_stats,
        "executionMode": "nexus_journey_linear",
        "preview": json.dumps(ff.attributes)[:240],
    }


flowfile_to_state = record_to_state
state_to_flowfile = state_to_record