"""Data flow API helpers — draft save semantics."""

from src.models.data_flow_models import DataFlowEdge, DataFlowGraph, DataFlowNode
from src.services import data_flow_service


def test_invalid_graph_can_validate_with_snapshot_shape():
    graph = DataFlowGraph(
        nodes=[
            DataFlowNode(id="a", type="source.google_drive", params={"sourceType": "google_drive"}),
            DataFlowNode(id="b", type="source.social_listening", params={"sourceType": "social_listening"}),
        ],
        edges=[DataFlowEdge(id="e", source="a", target="b")],
    )
    v = data_flow_service.validate_graph(graph)
    snap = v.model_dump(by_alias=True)
    assert snap["valid"] is False
    assert "issues" in snap
    assert any(i["code"] == "illegal_edge" for i in snap["issues"])