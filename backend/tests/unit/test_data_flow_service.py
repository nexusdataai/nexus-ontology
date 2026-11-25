"""Golden-graph tests for Pipeline Studio compile/validate."""

import pytest

from src.models.data_flow_models import DataFlowEdge, DataFlowGraph, DataFlowNode, DataFlowNodeUi
from src.constants.etl_step_catalog import EXTERNAL_SOURCE_TYPES
from src.services import data_flow_service


def _linear_graph(source_type: str, *, mapping_rule_id: str = "rule-1") -> DataFlowGraph:
    nodes = [
        DataFlowNode(
            id="n1",
            type="source.external_feed",
            params={"sourceType": source_type, "mode": "full", "batchSize": 500, "mappingRuleId": mapping_rule_id},
            ui=DataFlowNodeUi(position={"x": 0, "y": 0}),
        ),
        DataFlowNode(
            id="n2",
            type="transform.validate_schema",
            ui=DataFlowNodeUi(position={"x": 0, "y": 100}),
        ),
        DataFlowNode(
            id="n3",
            type="transform.map_fields",
            params={"mappingRuleId": mapping_rule_id},
            ui=DataFlowNodeUi(position={"x": 0, "y": 200}),
        ),
        DataFlowNode(
            id="n4",
            type="sink.load_fdw",
            ui=DataFlowNodeUi(position={"x": 0, "y": 300}),
        ),
        DataFlowNode(
            id="n5",
            type="sink.verify",
            ui=DataFlowNodeUi(position={"x": 0, "y": 400}),
        ),
    ]
    if source_type in EXTERNAL_SOURCE_TYPES:
        nodes.extend(
            [
                DataFlowNode(
                    id="n6",
                    type="sink.register_vdl",
                    ui=DataFlowNodeUi(position={"x": 0, "y": 500}),
                ),
                DataFlowNode(
                    id="n7",
                    type="sink.materialize_warehouse",
                    ui=DataFlowNodeUi(position={"x": 0, "y": 600}),
                ),
            ]
        )
    edges = []
    for i in range(len(nodes) - 1):
        edges.append(
            DataFlowEdge(id=f"e{i}", source=nodes[i].id, target=nodes[i + 1].id)
        )
    return DataFlowGraph(nodes=nodes, edges=edges)


@pytest.mark.parametrize("source_type", ["generic", "social_listening", "external_full"])
def test_compile_valid_linear_graph(source_type):
    graph = _linear_graph(source_type)
    result = data_flow_service.compile_graph(graph, inject_missing=False)
    assert result.valid
    assert result.config["sourceType"] == source_type
    assert result.enabled_steps[0] == "extract"
    assert "verify" in result.enabled_steps
    if source_type != "generic":
        assert "register_vdl" in result.enabled_steps
        assert "materialize_warehouse" in result.enabled_steps


def test_validate_rejects_cycle():
    graph = DataFlowGraph(
        nodes=[
            DataFlowNode(id="a", type="source.external_feed", params={"sourceType": "generic"}),
            DataFlowNode(id="b", type="sink.load_fdw"),
        ],
        edges=[
            DataFlowEdge(id="e1", source="a", target="b"),
            DataFlowEdge(id="e2", source="b", target="a"),
        ],
    )
    v = data_flow_service.validate_graph(graph)
    assert not v.valid
    assert any(i.code == "cycle" for i in v.issues)


def test_inject_missing_vdl_steps():
    graph = _linear_graph("social_listening")
    graph.nodes = [n for n in graph.nodes if n.type not in ("sink.register_vdl", "sink.materialize_warehouse")]
    graph.edges = [e for e in graph.edges if e.target not in ("n6", "n7")]
    injected = data_flow_service.inject_missing_nodes(graph)
    types = {n.type for n in injected.nodes}
    assert "sink.register_vdl" in types
    assert "sink.materialize_warehouse" in types


def test_plan_dedupe_prompt():
    graph = _linear_graph("generic")
    plan = data_flow_service.plan_from_prompt(graph, "Finance says orders are double-counted, dedupe(order_id, 5m)")
    assert plan.patches
    assert any(p.op == "add_node" for p in plan.patches)


def test_execution_graph_compiler():
    graph = _linear_graph("generic")
    ex = data_flow_service.compile_to_execution_graph(graph, journey_id="JRN-1")
    assert ex["runtime"] == "ai_engine"
    assert len(ex["nodes"]) >= 5
    assert ex["nodes"][0]["tool"] == "etl.extract"


def test_empty_graph_validate_is_warning():
    v = data_flow_service.validate_graph(DataFlowGraph(nodes=[], edges=[]))
    assert v.valid
    assert any(i.code == "empty_graph" for i in v.warnings)


def test_compile_empty_invalid():
    r = data_flow_service.compile_graph(DataFlowGraph(nodes=[], edges=[]))
    assert not r.valid


def test_two_live_sources_invalid_etl():
    graph = DataFlowGraph(
        nodes=[
            DataFlowNode(id="a", type="source.social_listening", params={"sourceType": "social_listening"}),
            DataFlowNode(id="b", type="source.file_uploads", params={"sourceType": "file_uploads"}),
            DataFlowNode(id="c", type="sink.load_fdw"),
        ],
        edges=[
            DataFlowEdge(id="e1", source="a", target="c"),
            DataFlowEdge(id="e2", source="b", target="c"),
        ],
    )
    v = data_flow_service.validate_graph(graph)
    assert not v.valid
    assert any(i.code == "multiple_live_sources" for i in v.issues)


def test_illegal_edge_source_to_source():
    graph = DataFlowGraph(
        nodes=[
            DataFlowNode(id="a", type="source.google_drive", params={"sourceType": "google_drive"}),
            DataFlowNode(id="b", type="source.file_uploads", params={"sourceType": "file_uploads"}),
        ],
        edges=[DataFlowEdge(id="e", source="a", target="b")],
    )
    v = data_flow_service.validate_graph(graph)
    assert not v.valid
    assert any(i.code == "illegal_edge" for i in v.issues)


def test_stub_kafka_is_warning():
    graph = DataFlowGraph(
        nodes=[
            DataFlowNode(id="k", type="source.kafka", params={"topic": "orders"}),
            DataFlowNode(id="t", type="transform.map_fields", params={"mappingRuleId": "r1"}),
        ],
        edges=[DataFlowEdge(id="e", source="k", target="t")],
    )
    v = data_flow_service.validate_graph(graph)
    assert v.valid
    assert any(i.code == "stub_node" for i in v.warnings)