"""
Validate, compile, and plan Data Flow graphs for Pipeline Studio.
"""

from __future__ import annotations

import copy
import re
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from src.constants.etl_step_catalog import (
    EXTERNAL_SOURCE_TYPES,
    LIVE_SOURCE_TYPE_BY_NODE,
    NODE_TYPE_TO_RUNTIME_STEP,
    PIPELINE_NODE_CATALOG,
    RUNTIME_STEP_ORDER,
    STUB_NODE_TYPES,
    runtime_steps_for_source,
)
from src.constants.flow_processor_seeds import nexus_catalog_nodes
from src.services.flow_runtime.dag_runner import graph_has_flow_processor_nodes
from src.services.flow_runtime.nexus_flow_journey import compile_graph_to_flow_steps
from src.models.data_flow_models import (
    DataFlowCompileResponse,
    DataFlowEdge,
    DataFlowGraph,
    DataFlowNode,
    DataFlowNodeUi,
    DataFlowPlanResponse,
    DataFlowValidateIssue,
    DataFlowValidateResponse,
    ProposedPatchOp,
)


def get_catalog() -> Dict[str, Any]:
    by_source: Dict[str, List[Dict[str, str]]] = {}
    for st in ("generic", *EXTERNAL_SOURCE_TYPES):
        by_source[st] = runtime_steps_for_source(st)
    flow_nodes = nexus_catalog_nodes()
    return {
        "nodeTypes": PIPELINE_NODE_CATALOG + flow_nodes,
        "runtimeStepsBySource": by_source,
        "runtimeStepOrder": list(RUNTIME_STEP_ORDER),
        "flowProcessorCount": len(flow_nodes),
    }


def all_known_node_types() -> Set[str]:
    return {c["type"] for c in PIPELINE_NODE_CATALOG} | {
        c["type"] for c in nexus_catalog_nodes()
    }


def flow_stub_types() -> Set[str]:
    return set()




def _issue(
    code: str,
    message: str,
    *,
    severity: str = "error",
    node_id: Optional[str] = None,
) -> DataFlowValidateIssue:
    return DataFlowValidateIssue(
        code=code,
        message=message,
        severity=severity,  # type: ignore[arg-type]
        nodeId=node_id,
    )


def _nodes_by_id(graph: DataFlowGraph) -> Dict[str, DataFlowNode]:
    return {n.id: n for n in graph.nodes}


def _adjacency(graph: DataFlowGraph) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    out_adj: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    in_adj: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    for e in graph.edges:
        if e.source in out_adj and e.target in in_adj:
            out_adj[e.source].append(e.target)
            in_adj[e.target].append(e.source)
    return out_adj, in_adj


def _has_cycle(graph: DataFlowGraph) -> bool:
    out_adj, _ = _adjacency(graph)
    visited: Set[str] = set()
    stack: Set[str] = set()

    def dfs(nid: str) -> bool:
        visited.add(nid)
        stack.add(nid)
        for nxt in out_adj.get(nid, []):
            if nxt not in visited:
                if dfs(nxt):
                    return True
            elif nxt in stack:
                return True
        stack.remove(nid)
        return False

    for n in graph.nodes:
        if n.id not in visited and dfs(n.id):
            return True
    return False


def _topo_order(graph: DataFlowGraph) -> Optional[List[str]]:
    if _has_cycle(graph):
        return None
    out_adj, in_adj = _adjacency(graph)
    indeg = {n.id: len(in_adj[n.id]) for n in graph.nodes}
    queue = [nid for nid, d in indeg.items() if d == 0]
    order: List[str] = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for nxt in out_adj.get(nid, []):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(graph.nodes):
        return None
    return order


def _live_source_nodes(graph: DataFlowGraph) -> List[DataFlowNode]:
    return [
        n
        for n in graph.nodes
        if n.type.startswith("source.") and n.type not in STUB_NODE_TYPES and n.type != "source.mapping_rule"
    ]


def _source_type_from_node(n: DataFlowNode) -> Optional[str]:
    if n.type in STUB_NODE_TYPES:
        return None
    if n.type in LIVE_SOURCE_TYPE_BY_NODE and n.type != "source.external_feed" and n.type != "source.fdw":
        return LIVE_SOURCE_TYPE_BY_NODE[n.type]
    st = n.params.get("sourceType") or n.params.get("source_type")
    if st:
        return str(st)
    if n.type in LIVE_SOURCE_TYPE_BY_NODE:
        return LIVE_SOURCE_TYPE_BY_NODE[n.type]
    return None


def _source_type_from_graph(graph: DataFlowGraph) -> str:
    types: List[str] = []
    for n in _live_source_nodes(graph):
        st = _source_type_from_node(n)
        if st:
            types.append(st)
    if not types:
        return "generic"
    unique = list(dict.fromkeys(types))
    if len(unique) == 1:
        return unique[0]
    if any(t in EXTERNAL_SOURCE_TYPES for t in unique):
        return "external_full"
    return unique[0]


def _config_from_graph(graph: DataFlowGraph) -> Dict[str, Any]:
    source_type = _source_type_from_graph(graph)
    config: Dict[str, Any] = {
        "sourceType": source_type,
        "mode": "full",
        "batchSize": 1000,
        "mappingRuleId": "",
    }
    for n in graph.nodes:
        if n.type.startswith("source.") or n.type in ("transform.map_fields", "source.mapping_rule"):
            for key in ("mode", "batchSize", "schedule", "mappingRuleId", "sourceQuery", "dataPlaneId"):
                if key in n.params and n.params[key] not in (None, ""):
                    config[key] = n.params[key]
    return config


def _runtime_steps_from_graph_order(graph: DataFlowGraph, source_type: str) -> List[str]:
    order = _topo_order(graph)
    by_id = _nodes_by_id(graph)
    if not order:
        return []

    steps: List[str] = []
    seen: Set[str] = set()
    for nid in order:
        node = by_id.get(nid)
        if not node:
            continue
        step_id = NODE_TYPE_TO_RUNTIME_STEP.get(node.type)
        if step_id and step_id not in seen:
            steps.append(step_id)
            seen.add(step_id)

    required = [s["id"] for s in runtime_steps_for_source(source_type)]
    for rid in required:
        if rid not in seen:
            steps.append(rid)
    steps.sort(key=lambda s: RUNTIME_STEP_ORDER.index(s) if s in RUNTIME_STEP_ORDER else 999)
    return steps


def validate_graph(
    graph: DataFlowGraph,
    *,
    mapping_rule_exists: Optional[Any] = None,
) -> DataFlowValidateResponse:
    issues: List[DataFlowValidateIssue] = []
    warnings: List[DataFlowValidateIssue] = []

    if not graph.nodes:
        warnings.append(_issue("empty_graph", "Drag a source onto the canvas to start", severity="warning"))

    known_types = all_known_node_types()
    flow_mode = graph_has_flow_processor_nodes(graph)
    sources = [n for n in graph.nodes if n.type.startswith("source.")]
    live_sources = _live_source_nodes(graph)
    if graph.nodes and len(sources) == 0 and not flow_mode:
        issues.append(_issue("missing_source", "Add a source node"))
    elif len(live_sources) > 1:
        warnings.append(
            _issue(
                "multiple_sources",
                "Multiple sources compile to one ETL job (external_full when mixed feeds)",
                severity="warning",
            )
        )

    stub_types = STUB_NODE_TYPES | flow_stub_types()
    for n in graph.nodes:
        if n.type in stub_types:
            warnings.append(
                _issue(
                    "stub_node",
                    f"{n.type} is not executable yet; deploy is blocked until this step is implemented",
                    severity="warning",
                    node_id=n.id,
                )
            )

    for n in graph.nodes:
        if n.type not in known_types:
            issues.append(_issue("unknown_node_type", f"Unknown node type: {n.type}", node_id=n.id))

    edge_nodes = {n.id for n in graph.nodes}
    for e in graph.edges:
        if e.source not in edge_nodes or e.target not in edge_nodes:
            issues.append(_issue("dangling_edge", f"Edge {e.id} references missing node", node_id=e.target))

    if graph.nodes and graph.edges and _has_cycle(graph):
        issues.append(_issue("cycle", "Graph must be acyclic (DAG)"))

    source_type = _source_type_from_graph(graph)
    if source_type not in ("generic", *EXTERNAL_SOURCE_TYPES):
        issues.append(_issue("invalid_source_type", f"Invalid sourceType: {source_type}"))

    order = _topo_order(graph)
    if graph.nodes and order is None and not any(i.code == "cycle" for i in issues):
        issues.append(_issue("not_dag", "Could not linearize graph; check connectivity"))

    config = _config_from_graph(graph)
    rule_id = config.get("mappingRuleId") or ""
    if source_type != "external_full" and not rule_id:
        warnings.append(
            _issue(
                "missing_mapping_rule",
                "No mapping rule selected; runs may fail at validate_schema",
                severity="warning",
            )
        )
    elif rule_id and mapping_rule_exists is not None:
        try:
            exists = mapping_rule_exists(rule_id)
            if not exists:
                issues.append(_issue("mapping_not_found", f"Mapping rule not found: {rule_id}"))
        except Exception:
            pass

    enabled = _runtime_steps_from_graph_order(graph, source_type) if not issues else []
    if order and enabled:
        pos = {s: i for i, s in enumerate(RUNTIME_STEP_ORDER)}
        last = -1
        for step in enabled:
            p = pos.get(step, 999)
            if p < last:
                issues.append(
                    _issue(
                        "step_order",
                        f"Runtime step order violation: {step} appears before an earlier mandatory step",
                    )
                )
                break
            last = max(last, p)

    dl_nodes = [n for n in graph.nodes if n.type == "route.dead_letter"]
    if dl_nodes:
        warnings.append(
            _issue(
                "dead_letter_visual",
                "Dead-letter nodes are visual-only in Phase 1; errors are handled in verify",
                severity="warning",
            )
        )

    valid = len(issues) == 0
    return DataFlowValidateResponse(valid=valid, issues=issues, warnings=warnings)


def inject_missing_nodes(graph: DataFlowGraph) -> DataFlowGraph:
    """Insert studio nodes for mandatory runtime steps missing from the graph."""
    source_type = _source_type_from_graph(graph)
    required = [s["id"] for s in runtime_steps_for_source(source_type)]
    present_steps = set()
    by_id = _nodes_by_id(graph)
    for n in graph.nodes:
        rid = NODE_TYPE_TO_RUNTIME_STEP.get(n.type)
        if rid:
            present_steps.add(rid)

    step_to_type = {
        "extract": "source.external_feed",
        "validate_schema": "transform.validate_schema",
        "transform": "transform.map_fields",
        "load": "sink.load_fdw",
        "verify": "sink.verify",
        "register_vdl": "sink.register_vdl",
        "materialize_warehouse": "sink.materialize_warehouse",
    }

    g = copy.deepcopy(graph)
    y = 0
    for n in g.nodes:
        y = max(y, n.ui.position.get("y", 0))
    last_id: Optional[str] = g.nodes[-1].id if g.nodes else None

    for rid in required:
        if rid in present_steps:
            continue
        ntype = step_to_type.get(rid)
        if not ntype:
            continue
        nid = f"auto-{rid}-{uuid.uuid4().hex[:8]}"
        y += 120
        params: Dict[str, Any] = {}
        if ntype == "source.external_feed":
            params = {"sourceType": source_type, "mode": "full", "batchSize": 1000}
        g.nodes.append(
            DataFlowNode(
                id=nid,
                type=ntype,
                params=params,
                ui=DataFlowNodeUi(position={"x": 80, "y": y}),
                autoInserted=True,
            )
        )
        if last_id:
            g.edges.append(
                DataFlowEdge(id=f"e-{last_id}-{nid}", source=last_id, target=nid)
            )
        last_id = nid
        present_steps.add(rid)

    return g


def compile_graph(
    graph: DataFlowGraph,
    *,
    inject_missing: bool = True,
    mapping_rule_exists: Optional[Any] = None,
) -> DataFlowCompileResponse:
    if not graph.nodes:
        return DataFlowCompileResponse(
            valid=False,
            issues=[_issue("empty_graph", "Pipeline graph must contain at least one node")],
        )
    flow_mode = graph_has_flow_processor_nodes(graph)
    should_inject = inject_missing and not flow_mode
    working = inject_missing_nodes(graph) if should_inject else graph
    validation = validate_graph(working, mapping_rule_exists=mapping_rule_exists)
    if not validation.valid:
        return DataFlowCompileResponse(
            valid=False,
            issues=validation.issues,
            graphWithInjections=working if inject_missing else None,
        )

    source_type = _source_type_from_graph(working)
    config = _config_from_graph(working)
    if flow_mode:
        flow_steps = compile_graph_to_flow_steps(working)
        enabled_steps = [s["id"] for s in flow_steps]
        config["compileMode"] = "nexus_flow"
        config["flowSteps"] = flow_steps
        config["enabledSteps"] = enabled_steps
    else:
        enabled_steps = _runtime_steps_from_graph_order(working, source_type)
        config["enabledSteps"] = enabled_steps
        config["compileMode"] = "etl_linear"

    metadata_patch = {
        "dataFlowGraph": working.model_dump(by_alias=True),
        "studioLayout": "v1",
        "config": config,
        "sourceType": source_type,
        "frontendType": "etl-pipeline" if not flow_mode else "nexus-flow",
    }

    return DataFlowCompileResponse(
        valid=True,
        issues=[],
        config=config,
        enabledSteps=enabled_steps,
        runtimeSteps=runtime_steps_for_source(source_type) if not flow_mode else [],
        metadataPatch=metadata_patch,
        graphWithInjections=working if should_inject else None,
    )


def apply_patches(graph: DataFlowGraph, patches: List[ProposedPatchOp]) -> DataFlowGraph:
    g = copy.deepcopy(graph)
    by_id = {n.id: n for n in g.nodes}

    for p in patches:
        if p.op == "add_node" and p.node:
            g.nodes.append(p.node)
            by_id[p.node.id] = p.node
        elif p.op == "remove_node" and p.node_id:
            g.nodes = [n for n in g.nodes if n.id != p.node_id]
            g.edges = [e for e in g.edges if e.source != p.node_id and e.target != p.node_id]
            by_id.pop(p.node_id, None)
        elif p.op == "update_node" and p.node:
            if p.node.id in by_id:
                idx = next(i for i, n in enumerate(g.nodes) if n.id == p.node.id)
                g.nodes[idx] = p.node
                by_id[p.node.id] = p.node
        elif p.op == "add_edge" and p.edge:
            g.edges.append(p.edge)
        elif p.op == "remove_edge":
            if p.edge:
                g.edges = [e for e in g.edges if e.id != p.edge.id]
        elif p.op == "update_params" and p.node_id and p.params is not None:
            if p.node_id in by_id:
                by_id[p.node_id].params.update(p.params)

    return g


def plan_from_prompt(graph: DataFlowGraph, prompt: str) -> DataFlowPlanResponse:
    """
    Rule-based copilot for Phase 2 (LLM can be wired via AI_ENGINE later).
  Understands dedupe / filter test orders / mapping hints from mockups.
    """
    text = prompt.strip().lower()
    patches: List[ProposedPatchOp] = []
    explanation_parts: List[str] = []

    dedupe_m = re.search(r"dedupe(?:licate)?\s*\(\s*(\w+)\s*,\s*(\d+)\s*([mhd])?\)", text)
    if dedupe_m or "deduplicate" in text or "double-count" in text:
        field = dedupe_m.group(1) if dedupe_m else "order_id"
        window = "5m"
        if dedupe_m:
            window = f"{dedupe_m.group(2)}{dedupe_m.group(3) or 'm'}"
        nid = f"proposed-dedupe-{uuid.uuid4().hex[:8]}"
        patches.append(
            ProposedPatchOp(
                op="add_node",
                node=DataFlowNode(
                    id=nid,
                    type="transform.filter",
                    params={"predicate": f"dedupe({field}, {window})", "copilot": True},
                    ui=DataFlowNodeUi(
                        position={"x": 280, "y": 200},
                        label=f"Deduplicate {field}",
                        proposed=True,
                    ),
                ),
                summary=f"+ Deduplicate({field}, {window})",
            )
        )
        explanation_parts.append(
            f"Detected duplicate-key concern; propose filter/dedupe on {field} within {window}."
        )

    if "drop test" in text and "order" in text:
        nid = f"proposed-filter-{uuid.uuid4().hex[:8]}"
        patches.append(
            ProposedPatchOp(
                op="add_node",
                node=DataFlowNode(
                    id=nid,
                    type="transform.filter",
                    params={"predicate": "order_id NOT LIKE 'test-%'", "copilot": True},
                    ui=DataFlowNodeUi(
                        position={"x": 280, "y": 80},
                        label="Drop test orders",
                        proposed=True,
                    ),
                ),
                summary="+ Filter test orders",
            )
        )
        explanation_parts.append("Proposed filter to exclude test orders.")

    if "mapping" in text or "map field" in text:
        patches.append(
            ProposedPatchOp(
                op="update_params",
                node_id=next((n.id for n in graph.nodes if n.type == "transform.map_fields"), None),
                params={"note": "Review mapping rule bindings"},
                summary="~ Review map_fields params",
            )
        )
        explanation_parts.append("Suggested reviewing map_fields / mapping rule binding.")

    if not patches:
        explanation_parts.append(
            "No rule matched this prompt. Describe filters, dedupe keys, or mapping changes."
        )

    impact = {"volumeDeltaPct": -2.3 if dedupe_m or "deduplicate" in text else 0, "latencyDeltaMs": 3}
    return DataFlowPlanResponse(
        patches=patches,
        explanation=" ".join(explanation_parts),
        impact=impact,
    )


def compile_to_execution_graph(
    graph: DataFlowGraph,
    *,
    journey_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Phase 3: map enabled runtime steps to AI Engine execution nodes."""
    compiled = compile_graph(graph, inject_missing=True)
    if not compiled.valid:
        raise ValueError("Graph invalid; cannot compile to execution graph")

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    prev: Optional[str] = None
    for step in compiled.enabled_steps:
        nid = f"etl-{step}"
        nodes.append(
            {
                "id": nid,
                "kind": "TOOL_CALL",
                "tool": f"etl.{step}",
                "params": {"journeyId": journey_id, "config": compiled.config},
            }
        )
        if prev:
            edges.append({"source": prev, "target": nid})
        prev = nid

    return {
        "journeyId": journey_id,
        "nodes": nodes,
        "edges": edges,
        "runtime": "ai_engine",
    }