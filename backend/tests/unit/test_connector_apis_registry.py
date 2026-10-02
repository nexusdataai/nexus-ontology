"""
Unit tests for ``services/control_plane/connector_apis.py``.

Asserts every registered ConnectorAPISpec is well-formed:
  - target_system in the closed set {oracle, sap, sfdc, external}
  - operation parses as "<METHOD> <PATH>" with valid method + leading slash
  - risk_level in the closed set
  - request_schema non-empty for write operations
  - simulator_writeback flag set
"""

from __future__ import annotations

import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.control_plane import connector_apis as ca

VALID_TARGET_SYSTEMS = {"oracle", "sap", "sfdc", "external"}
VALID_RISK_LEVELS = {"read_only", "low_risk_write", "high_risk_write"}
VALID_HTTP_METHODS = {"GET", "POST", "PATCH", "PUT", "DELETE"}


def _all_specs():
    return ca.list_all()


@pytest.mark.parametrize("spec", _all_specs(), ids=lambda s: s.api_id)
def test_target_system_is_valid(spec):
    assert spec.target_system in VALID_TARGET_SYSTEMS, (
        f"{spec.api_id}: target_system={spec.target_system!r}"
    )


@pytest.mark.parametrize("spec", _all_specs(), ids=lambda s: s.api_id)
def test_operation_is_well_formed(spec):
    parts = spec.operation.split(" ", 1)
    assert len(parts) == 2, f"{spec.api_id}: operation lacks method+path"
    method, path = parts
    assert method in VALID_HTTP_METHODS, f"{spec.api_id}: bad method {method!r}"
    assert path.startswith("/"), f"{spec.api_id}: path should start with /"


@pytest.mark.parametrize("spec", _all_specs(), ids=lambda s: s.api_id)
def test_risk_level_is_valid(spec):
    assert spec.risk_level in VALID_RISK_LEVELS, (
        f"{spec.api_id}: risk_level={spec.risk_level!r}"
    )


@pytest.mark.parametrize("spec", _all_specs(), ids=lambda s: s.api_id)
def test_write_specs_have_request_schema(spec):
    if spec.risk_level == "read_only":
        return
    assert isinstance(spec.request_schema, dict)
    assert len(spec.request_schema) > 0, (
        f"{spec.api_id}: write spec must have a request_schema"
    )


@pytest.mark.parametrize("spec", _all_specs(), ids=lambda s: s.api_id)
def test_simulator_writeback_is_bool(spec):
    assert isinstance(spec.simulator_writeback, bool)


def test_api_ids_are_unique():
    ids = [s.api_id for s in _all_specs()]
    assert len(ids) == len(set(ids)), "duplicate api_id detected"


def test_to_dict_round_trip_preserves_keys():
    expected_keys = {
        "api_id", "target_system", "operation", "description",
        "request_schema", "response_schema", "simulator_writeback",
        "risk_level", "tags",
    }
    for s in _all_specs():
        d = ca.to_dict(s)
        assert expected_keys <= set(d.keys()), (
            f"{s.api_id}: to_dict missing keys "
            f"{expected_keys - set(d.keys())}"
        )


# ---------------------------------------------------------------------------
# Phase 3 - presence + binding of the 9 new connector APIs.
#
# Each of these is referenced by a Phase-3 mutator/notify tool (see plan
# section 31.2/31.3). The tools themselves land in PR3c/3d; this test
# locks in the contract today so a tool author cannot reference a tool
# kind ``mutate``/``notify`` whose api_id was never registered.
# ---------------------------------------------------------------------------

PHASE3_API_IDS_BY_SYSTEM = {
    "oracle": [
        "oracle.promotion.create",
        "oracle.kit.create",
        "oracle.supplier.block",
    ],
    "sap": [
        "sap.capa.open",
        "sap.maintenance.schedule",
    ],
    "sfdc": [
        "sfdc.task.create_csm_outreach",
    ],
    "external": [
        "external.whatsapp.send_campaign",
        "external.email.send_campaign",
        "external.slack.post_message",
    ],
}

PHASE3_API_IDS_FLAT = [
    api_id for ids in PHASE3_API_IDS_BY_SYSTEM.values() for api_id in ids
]


@pytest.mark.parametrize("api_id", PHASE3_API_IDS_FLAT)
def test_phase3_api_registered(api_id: str):
    spec = ca.get(api_id)
    assert spec is not None, f"Phase 3 api_id '{api_id}' is not registered"


@pytest.mark.parametrize("api_id", PHASE3_API_IDS_FLAT)
def test_phase3_api_target_system_matches(api_id: str):
    expected = next(
        sys
        for sys, ids in PHASE3_API_IDS_BY_SYSTEM.items()
        if api_id in ids
    )
    assert ca.get(api_id).target_system == expected


@pytest.mark.parametrize("api_id", PHASE3_API_IDS_FLAT)
def test_phase3_api_is_writeback(api_id: str):
    """Every Phase-3 connector mutates a simulator table (or the Audit
    log via the same path); the mutate/notify tool kind requires it."""
    assert ca.get(api_id).simulator_writeback is True


def test_phase3_api_count_total_is_nine():
    flat = PHASE3_API_IDS_FLAT
    assert len(flat) == 9, f"Expected 9 Phase-3 APIs, got {len(flat)}"
    assert len(set(flat)) == 9, "duplicate api_ids in Phase-3 list"
