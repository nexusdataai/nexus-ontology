"""
Unit tests for ``services/control_plane/connector_apis_diagnostic.py``.

The five sync helpers are stand-alone (no FastAPI / no live simulator)
so we test them with hand-rolled fakes. ``simulator_coverage`` is async
and walks ``connector_runtime.fetch_rows`` - we don't cover it here
(integration test instead).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.control_plane import connector_apis_diagnostic as cad


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

@dataclass
class FakeSpec:
    api_id: str
    target_system: str = "oracle"
    operation: str = "POST /api/v1/simulator/oracle-erp/credit-notes"
    description: str = ""
    request_schema: Dict[str, str] = field(default_factory=dict)
    response_schema: Dict[str, str] = field(default_factory=dict)
    simulator_writeback: bool = True
    risk_level: str = "low_risk_write"
    tags: List[str] = field(default_factory=list)


@dataclass
class FakeTool:
    name: str
    risk_level: str = "low_risk_write"
    connector_api: Optional[str] = None


class FakeRegistry:
    def __init__(self, tools: List[FakeTool]) -> None:
        self._tools = tools

    def list_tools(self) -> List[FakeTool]:
        return list(self._tools)


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

def test_summary_counts_verified_orphans_and_hints():
    specs = [
        FakeSpec(api_id="a.1", target_system="oracle", risk_level="low_risk_write"),
        FakeSpec(api_id="a.2", target_system="sap", risk_level="high_risk_write"),
        FakeSpec(api_id="a.3", target_system="sfdc", risk_level="read_only"),
    ]
    registry = FakeRegistry([
        FakeTool("t1", connector_api="a.1"),
        FakeTool("t2", connector_api="a.2"),
        # a.3 has no caller -> orphan
    ])
    audit_counts = {"a.1": 5, "a.2": 0, "a.3": 0}
    audit_24h = {"a.1": 2, "a.2": 0, "a.3": 0}
    hints = {"a.1": {"mode": "patch"}, "a.2": {"mode": "post"}}

    out = cad.summary(specs, registry, audit_counts, audit_24h, hints)
    assert out["checked"] == 3
    assert out["verified"] == 1
    assert out["never_invoked"] == 2
    assert out["orphans"] == 1
    assert out["with_hint"] == 2
    assert out["without_hint"] == 1
    assert out["audit_events_24h"] == 2
    assert out["by_target_system"] == {"oracle": 1, "sap": 1, "sfdc": 1}
    assert out["by_risk_level"]["low_risk_write"] == 1
    assert out["overall"] == "degraded"  # orphan exists


def test_summary_healthy_when_no_orphans():
    specs = [FakeSpec(api_id="a.1")]
    registry = FakeRegistry([FakeTool("t1", connector_api="a.1")])
    out = cad.summary(specs, registry, {"a.1": 1}, {"a.1": 0}, {"a.1": {}})
    assert out["overall"] == "healthy"
    assert out["orphans"] == 0


# ---------------------------------------------------------------------------
# catalogue_health
# ---------------------------------------------------------------------------

def test_catalogue_health_flags_invalid_target_and_orphans():
    specs = [
        FakeSpec(api_id="bad.target", target_system="venus"),
        FakeSpec(
            api_id="empty.req",
            target_system="oracle",
            risk_level="low_risk_write",
            request_schema={},
        ),
        FakeSpec(api_id="ok.spec", request_schema={"x": "string"}, response_schema={"y": "string"}),
    ]
    registry = FakeRegistry([
        FakeTool("t1", connector_api="ok.spec"),
        # bad.target and empty.req have no caller
    ])

    out = cad.catalogue_health(specs, registry)
    assert out["totals"]["checked"] == 3
    assert out["totals"]["errors"] >= 1
    assert out["totals"]["warnings"] >= 1
    codes = {iss["code"] for issues in out["issues_by_api"].values() for iss in issues}
    assert "invalid_target_system" in codes
    assert "empty_request_schema" in codes
    assert "orphan_no_tool_caller" in codes


def test_catalogue_health_healthy_when_clean():
    specs = [
        FakeSpec(
            api_id="ok.spec",
            request_schema={"x": "string"},
            response_schema={"y": "string"},
        ),
    ]
    registry = FakeRegistry([FakeTool("t1", connector_api="ok.spec")])
    out = cad.catalogue_health(specs, registry)
    assert out["totals"]["errors"] == 0
    assert out["totals"]["warnings"] == 0
    assert out["overall"] == "healthy"


# ---------------------------------------------------------------------------
# tool_mapping
# ---------------------------------------------------------------------------

def test_tool_mapping_flags_orphan_write_tool_and_dangling_tool():
    specs = [FakeSpec(api_id="a.1"), FakeSpec(api_id="a.2")]
    registry = FakeRegistry([
        FakeTool("good", risk_level="low_risk_write", connector_api="a.1"),
        FakeTool("orphan_writer", risk_level="high_risk_write", connector_api=None),
        FakeTool("dangler", risk_level="low_risk_write", connector_api="a.999"),
        FakeTool("readonly_ok", risk_level="read_only", connector_api=None),
    ])
    out = cad.tool_mapping(specs, registry)
    assert "orphan_writer" in {r["tool_id"] for r in out["orphan_tools"]}
    assert "dangler" in out["dangling_tools"]
    assert out["totals"]["orphan_tools"] == 1
    assert out["totals"]["dangling_tools"] == 1
    assert out["totals"]["orphan_apis"] == 1  # a.2 has no caller
    assert out["overall"] == "degraded"


def test_tool_mapping_healthy_when_all_writers_bound():
    specs = [FakeSpec(api_id="a.1")]
    registry = FakeRegistry([
        FakeTool("writer", risk_level="low_risk_write", connector_api="a.1"),
        FakeTool("reader", risk_level="read_only", connector_api=None),
    ])
    out = cad.tool_mapping(specs, registry)
    assert out["totals"]["orphan_tools"] == 0
    assert out["totals"]["dangling_tools"] == 0
    assert out["overall"] == "healthy"


# ---------------------------------------------------------------------------
# verification_hints
# ---------------------------------------------------------------------------

def test_verification_hints_flags_specs_without_hint():
    specs = [
        FakeSpec(api_id="a.1"),
        FakeSpec(api_id="a.2"),
        FakeSpec(api_id="a.3"),
    ]
    hints = {
        "a.1": {
            "mode": "patch", "schema": "s", "table": "t",
            "pk_col": "id", "pk_arg": "id_arg",
        },
        "a.2": {
            "mode": "post_prefix", "schema": "s",
            "table_prefix_arg": "prefix", "table_suffix": "_X",
            "pk_col": "id",
        },
    }
    out = cad.verification_hints(specs, hints)
    assert out["totals"]["with_hint"] == 2
    assert out["totals"]["without_hint"] == 1
    assert out["non_verifiable_api_ids"] == ["a.3"]
    by_id = {r["api_id"]: r for r in out["rows"]}
    assert by_id["a.1"]["table"] == "t"
    assert by_id["a.2"]["table"] == "{prefix}_X"
    assert by_id["a.3"]["has_hint"] is False
    assert out["overall"] == "degraded"


# ---------------------------------------------------------------------------
# audit_discipline
# ---------------------------------------------------------------------------

def test_audit_discipline_flags_never_called_writes():
    specs = [
        FakeSpec(api_id="a.never", risk_level="low_risk_write"),
        FakeSpec(api_id="a.healthy", risk_level="low_risk_write"),
        FakeSpec(api_id="a.readonly", risk_level="read_only"),
    ]
    counts = {"a.never": 0, "a.healthy": 5, "a.readonly": 0}
    audit_24h = {"a.never": 0, "a.healthy": 1, "a.readonly": 0}
    last_ts = {"a.never": None, "a.healthy": "2026-05-10T10:00:00+00:00", "a.readonly": None}
    out = cad.audit_discipline(specs, counts, audit_24h, last_ts)
    by_id = {r["api_id"]: r for r in out["rows"]}
    assert by_id["a.never"]["smell"] == "never_called"
    assert by_id["a.healthy"]["smell"] == "ok"
    # read_only with zero events still classified as never_called (benign)
    assert by_id["a.readonly"]["smell"] == "never_called"
    assert out["totals"]["ok"] == 1
    assert out["totals"]["never_called"] == 2
