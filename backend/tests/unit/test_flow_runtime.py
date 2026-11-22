"""Unit tests for Nexus flow runtime."""
from __future__ import annotations

import json
import os

os.environ.setdefault("NEXUS_FLOW_RUNTIME_EXECUTION", "true")

from src.models.data_flow_models import DataFlowEdge, DataFlowGraph, DataFlowNode, DataFlowNodeUi
from src.services import flow_processors  # noqa: F401
from src.services.flow_processors.update_attribute import UpdateAttributeProcessor
from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.flow_record import FlowRecord
from src.services.flow_runtime.nexus_flow_journey import run_nexus_flow_linear
from src.services.flow_runtime.processor import get_processor_class
from src.services.flow_runtime.session import ProcessSession


def test_update_attribute_sets_dynamic_property():
    proc = UpdateAttributeProcessor()
    record = FlowRecord(content=b"{}", attributes={})
    session = ProcessSession()
    session.set_inbound([record])
    ctx = ProcessContext({"region": "US", "tenant": "${missing}"})
    proc.on_trigger(ctx, session)
    out = session.commit()
    assert "success" in out
    assert out["success"][0].attributes.get("region") == "US"


def test_registered_live_processors():
    from src.services.flow_processors import ensure_all_processors_loaded
    from src.services.flow_runtime.processor import list_registered_processor_ids

    ensure_all_processors_loaded()
    ids = list_registered_processor_ids()
    assert len(ids) == 117
    assert get_processor_class("nexus.UpdateAttribute") is not None
    assert get_processor_class("nexus.JoltTransformJSON") is not None


def test_registry_probe_update_attribute():
    from src.services.data_plane.nexus_data_processor_probe import probe_processor, read_processor_source

    src = read_processor_source("nexus.UpdateAttribute")
    assert src["available"] is True
    assert "UpdateAttribute" in src["source"]
    out = probe_processor("nexus.UpdateAttribute")
    assert out["status"] == "pass"


def test_dag_update_attribute_chain():
    g = DataFlowGraph(
        nodes=[
            DataFlowNode(
                id="a",
                type="nexus.UpdateAttribute",
                params={"status": "ok"},
                ui=DataFlowNodeUi(position={"x": 0, "y": 0}),
            ),
            DataFlowNode(
                id="b",
                type="nexus.EvaluateJsonPath",
                params={"id": "$.id"},
                ui=DataFlowNodeUi(position={"x": 200, "y": 0}),
            ),
        ],
        edges=[
            DataFlowEdge(id="e1", source="a", target="b", relationship="success"),
        ],
    )
    initial = [FlowRecord(content=json.dumps({"id": "42"}).encode(), attributes={})]
    result = run_nexus_flow_linear(g, initial_records=initial)
    assert result["ok"] is True
    assert result["terminalCount"] == 1