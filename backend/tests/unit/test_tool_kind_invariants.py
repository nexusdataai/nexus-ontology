"""
Unit tests for Phase 3 - ``tool_kind`` invariants.

Covers:
- ``automation_models.ToolDoc``: a mutate/notify tool MUST have a
  connector_api; a read/analyze/decide tool MUST NOT.
- ``tool_builder_models.ToolCreate`` / ``ToolUpdate``: same invariant
  applies on the DDB-backed authoring path.
- ``automation_models.JourneyDoc.validate_strict``: emits
  ``step_connector_api_forbidden`` warning for legacy step-level
  connector_api; enforces stage/kind alignment when ``tool_kinds`` map is
  supplied.
- ``tool_registry.Tool.effective_tool_kind``: heuristic default matches
  ``automation_models._infer_tool_kind`` so YAML and code-defined tools
  agree.
"""

from __future__ import annotations

import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.models.automation_models import (
    JourneyDoc,
    StageDoc,
    StepDoc,
    ToolDoc,
    ToolKind,
    ToolRuntime,
    _infer_tool_kind,
)
from src.models.tool_builder_models import (
    RiskLevel,
    ToolCreate,
    ToolUpdate,
    _check_kind_connector_invariant,
)
from src.services.control_plane.tool_registry import RiskLevel as RegistryRiskLevel, Tool


_GOOD_SOURCE = """
async def run(params, vdl, connectors, ctx, log):
    return {"ok": True}
""".strip()


# ---------------------------------------------------------------------------
# automation_models.ToolDoc invariants
# ---------------------------------------------------------------------------

class TestToolDocKindInvariant:
    def test_mutate_without_connector_api_rejected(self) -> None:
        with pytest.raises(ValueError, match="requires connector_api"):
            ToolDoc(
                tool_id="apply_promo_discount",
                display_name="Apply Promo Discount",
                group="customer_360",
                description="x",
                risk_level="high_risk_write",
                tool_kind=ToolKind.MUTATE.value,
                connector_api=None,
            )

    def test_notify_without_connector_api_rejected(self) -> None:
        with pytest.raises(ValueError, match="requires connector_api"):
            ToolDoc(
                tool_id="send_whatsapp_campaign",
                display_name="Send WhatsApp Campaign",
                group="notify",
                description="x",
                risk_level="low_risk_write",
                tool_kind=ToolKind.NOTIFY.value,
                connector_api=None,
            )

    def test_read_with_connector_api_rejected(self) -> None:
        with pytest.raises(ValueError, match="must NOT set connector_api"):
            ToolDoc(
                tool_id="find_churning_customers",
                display_name="Find Churning Customers",
                group="customer_360",
                description="x",
                risk_level="read_only",
                tool_kind=ToolKind.READ.value,
                connector_api="oracle.customer.terms.set",
            )

    def test_analyze_with_connector_api_rejected(self) -> None:
        with pytest.raises(ValueError, match="must NOT set connector_api"):
            ToolDoc(
                tool_id="score_oee_decline",
                display_name="Score OEE",
                group="production_quality",
                description="x",
                risk_level="read_only",
                tool_kind=ToolKind.ANALYZE.value,
                connector_api="sap.production_order.update",
            )

    def test_mutate_with_connector_api_accepted(self) -> None:
        doc = ToolDoc(
            tool_id="apply_promo_discount",
            display_name="Apply Promo Discount",
            group="customer_360",
            description="x",
            risk_level="high_risk_write",
            tool_kind=ToolKind.MUTATE.value,
            connector_api="oracle.promotion.create",
        )
        assert doc.effective_tool_kind() == "mutate"

    def test_invalid_tool_kind_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be one of"):
            ToolDoc(
                tool_id="bogus",
                display_name="Bogus",
                group="x",
                description="x",
                tool_kind="ridiculous",
            )

    def test_inferred_kind_for_legacy_doc_without_explicit_kind(self) -> None:
        # No tool_kind set -> heuristic. read_only + no connector -> "read".
        doc = ToolDoc(
            tool_id="query_helper",
            display_name="Query helper",
            group="virtual_query",
            description="x",
            risk_level="read_only",
        )
        assert doc.tool_kind is None
        assert doc.effective_tool_kind() == "read"

    def test_inferred_kind_for_legacy_write_tool(self) -> None:
        # No tool_kind, has connector_api -> "mutate".
        doc = ToolDoc(
            tool_id="legacy_write",
            display_name="Legacy",
            group="o2c",
            description="x",
            risk_level="high_risk_write",
            connector_api="oracle.invoice.status.set",
        )
        assert doc.effective_tool_kind() == "mutate"


class TestInferToolKind:
    @pytest.mark.parametrize("risk,connector,expected", [
        ("read_only",       None,                "read"),
        ("low_risk_write",  None,                "analyze"),
        ("high_risk_write", None,                "analyze"),
        ("read_only",       "oracle.invoice.x",  "mutate"),
        ("high_risk_write", "sfdc.account.x",    "mutate"),
        (None,              None,                "analyze"),
    ])
    def test_infer(self, risk: str, connector: str, expected: str) -> None:
        assert _infer_tool_kind(risk_level=risk, connector_api=connector) == expected


class TestToolRuntimeOneOf:
    def test_exactly_one_runtime_required(self) -> None:
        with pytest.raises(ValueError, match="exactly one of"):
            ToolRuntime()
        with pytest.raises(ValueError, match="exactly one of"):
            ToolRuntime(source_code="async def run(): pass", module_path="x.y.z")
        # Each individually is fine.
        assert ToolRuntime(source_code="async def run(): pass").source_code
        assert ToolRuntime(module_path="x.y.z").module_path
        assert ToolRuntime(ddb_ref="tool-foo-abc12345").ddb_ref


# ---------------------------------------------------------------------------
# tool_builder_models invariants (DDB authoring path)
# ---------------------------------------------------------------------------

class TestToolBuilderKindInvariant:
    def test_check_invariant_rejects_mutate_without_connector(self) -> None:
        with pytest.raises(ValueError, match="requires connector_api"):
            _check_kind_connector_invariant("mutate", None)

    def test_check_invariant_rejects_read_with_connector(self) -> None:
        with pytest.raises(ValueError, match="must NOT set connector_api"):
            _check_kind_connector_invariant("read", "sfdc.case.create")

    def test_check_invariant_rejects_unknown_kind(self) -> None:
        with pytest.raises(ValueError, match="must be one of"):
            _check_kind_connector_invariant("ridiculous", None)

    def test_tool_create_mutate_without_connector_rejected(self) -> None:
        with pytest.raises(ValueError, match="requires connector_api"):
            ToolCreate(
                name="apply_promo_discount",
                description="x",
                risk_level=RiskLevel.HIGH_RISK_WRITE,
                connector_api=None,
                tool_kind="mutate",
                source_code=_GOOD_SOURCE,
            )

    def test_tool_create_read_with_connector_rejected(self) -> None:
        with pytest.raises(ValueError, match="must NOT set connector_api"):
            ToolCreate(
                name="find_x",
                description="x",
                risk_level=RiskLevel.READ_ONLY,
                connector_api="sfdc.case.create",
                tool_kind="read",
                source_code=_GOOD_SOURCE,
            )

    def test_tool_create_legacy_no_kind_accepted(self) -> None:
        # When tool_kind is absent, the invariant doesn't fire. Existing
        # callers continue to work unchanged.
        body = ToolCreate(
            name="legacy_create",
            description="x",
            risk_level=RiskLevel.HIGH_RISK_WRITE,
            connector_api="oracle.invoice.status.set",
            source_code=_GOOD_SOURCE,
        )
        assert body.tool_kind is None

    def test_tool_update_with_kind_validates_against_provided_connector(self) -> None:
        with pytest.raises(ValueError, match="requires connector_api"):
            ToolUpdate(tool_kind="mutate", connector_api=None)


# ---------------------------------------------------------------------------
# JourneyDoc.validate_strict
# ---------------------------------------------------------------------------

def _journey_with_step(step_kw: dict) -> JourneyDoc:
    """Build a minimal JourneyDoc with a single act-stage step."""
    return JourneyDoc(
        use_case_id="o2c.test",
        title="Test",
        solution_id="order-to-cash",
        stages=[
            StageDoc(
                stage_id="act",
                name="Act",
                order=1,
                steps=[StepDoc(step_id="s1", name="step", order=1, **step_kw)],
            ),
        ],
    )


class TestJourneyDocValidateStrict:
    def test_step_connector_api_emits_warning(self) -> None:
        # Legacy step still carrying connector_api - should warn (not error).
        j = _journey_with_step(dict(tool="place_credit_hold",
                                    connector_api="sfdc.account.credit_hold.set"))
        report = j.validate_strict()
        warning_codes = [w.code for w in report.warnings]
        assert "step_connector_api_forbidden" in warning_codes
        # The legacy field should not block validation overall.
        assert report.ok

    def test_clean_step_no_warning(self) -> None:
        j = _journey_with_step(dict(tool="place_credit_hold"))
        report = j.validate_strict()
        warning_codes = [w.code for w in report.warnings]
        assert "step_connector_api_forbidden" not in warning_codes

    def test_act_stage_with_only_read_tools_is_error(self) -> None:
        j = _journey_with_step(dict(tool="query_virtual_entity"))
        report = j.validate_strict(
            tool_kinds={"query_virtual_entity": "read"},
        )
        codes = [e.code for e in report.errors]
        assert "act_stage_no_mutator" in codes
        assert not report.ok

    def test_act_stage_with_mutator_passes(self) -> None:
        j = _journey_with_step(dict(tool="place_credit_hold"))
        report = j.validate_strict(
            tool_kinds={"place_credit_hold": "mutate"},
        )
        codes = [e.code for e in report.errors]
        assert "act_stage_no_mutator" not in codes

    def test_resolve_stage_with_mutator_is_error(self) -> None:
        # Build a journey where the resolve stage has a mutate-kind tool.
        j = JourneyDoc(
            use_case_id="o2c.test",
            title="Test",
            solution_id="order-to-cash",
            stages=[
                StageDoc(
                    stage_id="resolve",
                    name="Resolve",
                    order=1,
                    steps=[StepDoc(step_id="s1", name="step", order=1,
                                    tool="place_credit_hold")],
                ),
            ],
        )
        report = j.validate_strict(
            tool_kinds={"place_credit_hold": "mutate"},
        )
        codes = [e.code for e in report.errors]
        assert "resolve_stage_has_mutator" in codes
        assert not report.ok


# ---------------------------------------------------------------------------
# tool_registry.Tool heuristic
# ---------------------------------------------------------------------------

async def _noop(**_kw):
    return {"ok": True}


class TestRegistryToolEffectiveKind:
    def test_explicit_kind_wins(self) -> None:
        t = Tool(
            name="explicit",
            description="x",
            parameters={"type": "object", "properties": {}},
            risk_level=RegistryRiskLevel.READ_ONLY,
            execute=_noop,
            tool_kind="analyze",
        )
        assert t.effective_tool_kind() == "analyze"

    def test_inferred_mutate_when_connector_api_set(self) -> None:
        t = Tool(
            name="legacy_writer",
            description="x",
            parameters={"type": "object", "properties": {}},
            risk_level=RegistryRiskLevel.HIGH_RISK_WRITE,
            execute=_noop,
            connector_api="oracle.invoice.status.set",
        )
        assert t.effective_tool_kind() == "mutate"

    def test_inferred_read_for_read_only(self) -> None:
        t = Tool(
            name="reader",
            description="x",
            parameters={"type": "object", "properties": {}},
            risk_level=RegistryRiskLevel.READ_ONLY,
            execute=_noop,
        )
        assert t.effective_tool_kind() == "read"

    def test_inferred_analyze_default(self) -> None:
        t = Tool(
            name="analyzer",
            description="x",
            parameters={"type": "object", "properties": {}},
            risk_level=RegistryRiskLevel.LOW_RISK_WRITE,
            execute=_noop,
        )
        assert t.effective_tool_kind() == "analyze"
