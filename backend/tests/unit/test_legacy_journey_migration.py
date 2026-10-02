"""Unit tests for the legacy-journey -> ConnectionDoc converter."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    """Import the migration script as a module despite its dashed path."""
    backend_root = Path(__file__).resolve().parents[2]
    script = backend_root / "scripts" / "migrations" / "migrate_legacy_journey_substitution_to_connections.py"
    spec = importlib.util.spec_from_file_location("legacy_journey_migration", script)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["legacy_journey_migration"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_m = _load_module()


def test_extracts_connection_from_placeholder_string():
    conn = _m._extract_connection(
        to_step="s2", to_param="customer_id",
        value="${steps.s1.results.0.customer_id}",
    )
    assert conn == {
        "from_step": "s1",
        "from_relationship": "success",
        "from_path": "results.0.customer_id",
        "to_step": "s2",
        "to_param": "customer_id",
    }


def test_ignores_non_placeholder_values():
    assert _m._extract_connection(to_step="s2", to_param="x", value="literal") is None
    assert _m._extract_connection(to_step="s2", to_param="x", value=42) is None
    assert _m._extract_connection(to_step="s2", to_param="x", value=None) is None
    # Interpolated string -- not a whole-string placeholder, skip.
    assert _m._extract_connection(to_step="s2", to_param="x", value="prefix-${steps.s1.x}") is None


def test_convert_adds_connections_and_stamps_bucket():
    doc = {
        "use_case_id": "demo.legacy",
        "journey_id": "demo.legacy",
        "title": "Demo legacy",
        "solution_id": "customer-360",
        "stages": [{
            "stage_id": "main",
            "name": "Main",
            "order": 1,
            "steps": [
                {"step_id": "s1", "name": "S1", "order": 1, "tool": "find_x", "params": {}},
                {"step_id": "s2", "name": "S2", "order": 2, "tool": "use_x",
                 "params": {"customer_id": "${steps.s1.results.0.customer_id}",
                            "literal": "abc"}},
            ],
        }],
    }
    new_doc, added, bucket_stamped = _m._convert(doc)
    assert added == 1
    assert bucket_stamped is True
    assert new_doc["bucket"] == "customer-360"
    connections = new_doc["stages"][0]["connections"]
    assert len(connections) == 1
    c = connections[0]
    assert c["from_step"] == "s1"
    assert c["from_relationship"] == "success"
    assert c["from_path"] == "results.0.customer_id"
    assert c["to_step"] == "s2"
    assert c["to_param"] == "customer_id"


def test_convert_idempotent_when_connections_already_present():
    doc = {
        "use_case_id": "demo.idem",
        "journey_id": "demo.idem",
        "title": "Demo idempotent",
        "solution_id": "customer-360",
        "bucket": "customer-360",
        "stages": [{
            "stage_id": "main",
            "name": "Main",
            "order": 1,
            "steps": [
                {"step_id": "s1", "name": "S1", "order": 1, "tool": "find_x", "params": {}},
                {"step_id": "s2", "name": "S2", "order": 2, "tool": "use_x",
                 "params": {"customer_id": "${steps.s1.x}"}},
            ],
            "connections": [
                {"from_step": "s1", "from_relationship": "success",
                 "from_path": "x", "to_step": "s2", "to_param": "customer_id"},
            ],
        }],
    }
    new_doc, added, bucket_stamped = _m._convert(doc)
    assert added == 0
    assert bucket_stamped is False


def test_convert_preserves_unrelated_stage_state():
    doc = {
        "use_case_id": "demo.preserve",
        "journey_id": "demo.preserve",
        "title": "Preserve",
        "solution_id": "order-to-cash",
        "stages": [{
            "stage_id": "main",
            "name": "Main",
            "order": 1,
            "extra_field": "should_survive",
            "steps": [{"step_id": "s1", "name": "S1", "order": 1, "tool": "find_x", "params": {}}],
        }],
    }
    new_doc, added, bucket_stamped = _m._convert(doc)
    assert added == 0
    assert bucket_stamped is True
    assert new_doc["bucket"] == "o2c"
    assert new_doc["stages"][0]["extra_field"] == "should_survive"
