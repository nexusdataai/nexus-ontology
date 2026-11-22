from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from src.models.data_flow_models import DataFlowEdge, DataFlowGraph, DataFlowNode
from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.flowfile import FlowFile
from src.services.flow_runtime.processor import AbstractProcessor, get_processor_class
from src.services.flow_runtime.session import ProcessSession


def _adjacency_with_relationship(
    graph: DataFlowGraph,
) -> Tuple[Dict[str, List[Tuple[str, str]]], Dict[str, List[str]]]:
    """out_adj[node] -> list of (target, relationship)."""
    out_adj: Dict[str, List[Tuple[str, str]]] = {n.id: [] for n in graph.nodes}
    in_adj: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    by_id = {n.id: n for n in graph.nodes}
    for e in graph.edges:
        rel = getattr(e, "relationship", None) or "success"
        if e.source in out_adj and e.target in in_adj:
            out_adj[e.source].append((e.target, rel))
            in_adj[e.target].append(e.source)
    return out_adj, in_adj


def _topo_order(graph: DataFlowGraph) -> Optional[List[str]]:
    _, in_adj = _adjacency_with_relationship(graph)
    out_count: Dict[str, int] = {n.id: 0 for n in graph.nodes}
    for nid, ins in in_adj.items():
        out_count[nid] = len(ins)
    q = deque([nid for nid, d in out_count.items() if d == 0])
    order: List[str] = []
    out_adj, _ = _adjacency_with_relationship(graph)
    while q:
        nid = q.popleft()
        order.append(nid)
        for tgt, _ in out_adj.get(nid, []):
            out_count[tgt] -= 1
            if out_count[tgt] == 0:
                q.append(tgt)
    return order if len(order) == len(graph.nodes) else None


def graph_has_nifi_nodes(graph: DataFlowGraph) -> bool:
    return any(n.type.startswith("nifi.") for n in graph.nodes)


def run_nifi_dag(
    graph: DataFlowGraph,
    *,
    initial_flowfiles: Optional[List[FlowFile]] = None,
    _skip_execution_policy: bool = False,
) -> Dict[str, Any]:
    """Deprecated: use ``run_nexus_flow_linear`` (journey steps, not NiFi DAG engine)."""
    if not _skip_execution_policy:
        from src.services.flow_runtime.execution_policy import nifi_runtime_execution_enabled

        if not nifi_runtime_execution_enabled():
            return {
                "ok": False,
                "error": "nifi_runtime_execution_disabled",
                "nodeStats": [],
            }

    from src.services.flow_runtime.nexus_flow_journey import run_nexus_flow_linear

    return run_nexus_flow_linear(graph, initial_flowfiles=initial_flowfiles)