"""Tests for the ``ReportSchemaCatalog`` YAML loader.

The catalog is the canonical lookup of ``solution_id -> ReportSchema``.
We assert:

1. All 13 bundled YAML schemas under
   ``enterprise-knowledge/report-schemas/`` parse without errors.
2. ``get(unknown_solution)`` returns the ``_default`` schema rather
   than raising.
3. A malformed file in a tmp dir is gracefully skipped (the catalog
   logs a warning and keeps loading the remaining files).
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from src.services.journey_report_catalog import (
    ReportKpi, ReportSchema, ReportSchemaCatalog, ReportSection,
)


REPO_SCHEMA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "enterprise-knowledge", "report-schemas",
)


def test_all_bundled_schemas_load() -> None:
    cat = ReportSchemaCatalog(schema_dir=REPO_SCHEMA_DIR)
    cat.reload()
    known = cat.known_solutions()
    # We ship 12 per-solution schemas plus a _default. ``known_solutions``
    # excludes the default (it's not a real solution).
    assert "call-processing" in known
    assert "order-to-cash" in known
    assert "demand-forecasting" in known
    assert "inventory-optimization" in known
    assert "procurement-analytics" in known
    assert "production-quality" in known
    assert "supply-chain-risk" in known
    assert "customer-360" in known
    assert "esg-sustainability" in known
    assert "semantic-rag" in known
    assert "etl-pipeline" in known
    assert "builder" in known
    # The default schema is loadable through ``get(unknown)``.
    default = cat.get("not-a-real-solution")
    assert isinstance(default, ReportSchema)
    assert default.solution_id == "_default"


def test_each_schema_has_summary_kpis() -> None:
    cat = ReportSchemaCatalog(schema_dir=REPO_SCHEMA_DIR)
    cat.reload()
    for sid in cat.known_solutions():
        s = cat.get(sid)
        assert s.title, f"{sid}: missing title"
        assert s.summary_kpis, f"{sid}: empty summary_kpis"
        # Every summary KPI has the minimum required fields.
        for k in s.summary_kpis:
            assert k.key, f"{sid}: kpi missing key"
            assert k.label, f"{sid}: kpi {k.key} missing label"
            assert k.source, f"{sid}: kpi {k.key} missing source"
            assert k.format in {"percent", "integer", "duration",
                                "currency", "decimal", "text"}, \
                f"{sid}: kpi {k.key} bad format {k.format}"
            assert k.rollup in {"avg", "sum", "last", "max", "min", "count_distinct"}, \
                f"{sid}: kpi {k.key} bad rollup {k.rollup}"


def test_get_unknown_falls_back_to_default() -> None:
    cat = ReportSchemaCatalog(schema_dir=REPO_SCHEMA_DIR)
    cat.reload()
    s = cat.get("totally-unknown-solution")
    assert s.solution_id == "_default"


def test_get_with_none_solution_id() -> None:
    cat = ReportSchemaCatalog(schema_dir=REPO_SCHEMA_DIR)
    cat.reload()
    s = cat.get(None)
    assert s.solution_id == "_default"


def test_malformed_yaml_is_skipped_not_fatal(tmp_path: Path) -> None:
    """A broken file should NOT crash the loader; remaining files keep
    loading and unknown solutions still fall through to the default."""
    good = tmp_path / "good.yaml"
    good.write_text(textwrap.dedent("""
        solution_id: good
        title: Good
        summary_kpis:
          - key: foo
            label: Foo
            source: Data.kpis.foo
    """))
    bad = tmp_path / "bad.yaml"
    bad.write_text("solution_id: bad\nsummary_kpis: [: not valid yaml\n")
    cat = ReportSchemaCatalog(schema_dir=str(tmp_path))
    cat.reload()
    assert "good" in cat.known_solutions()
    # The bad file is silently dropped.
    assert "bad" not in cat.known_solutions()


def test_reload_picks_up_new_files(tmp_path: Path) -> None:
    cat = ReportSchemaCatalog(schema_dir=str(tmp_path))
    cat.reload()
    assert cat.known_solutions() == []
    (tmp_path / "new.yaml").write_text(textwrap.dedent("""
        solution_id: new
        title: New
        summary_kpis:
          - {key: a, label: A, source: derived.total_jobs}
    """))
    cat.reload()
    assert "new" in cat.known_solutions()


def test_schema_from_dict_threshold_round_trip() -> None:
    s = ReportSchema.from_dict({
        "solution_id": "x",
        "title": "X",
        "summary_kpis": [
            {"key": "k", "label": "K", "source": "Data.kpis.k",
             "threshold": {"warn": 50, "critical": 80}},
        ],
        "sections": [
            {"id": "s", "title": "S", "kind": "kpi_grid", "kpis": []},
        ],
    })
    assert s.summary_kpis[0].threshold == {"warn": 50, "critical": 80}
    assert s.sections[0].kind == "kpi_grid"


def test_section_kinds_supported() -> None:
    """Every shipped schema's sections use a kind the builder knows
    how to render. New kinds must be added to the renderer dispatch
    in JourneyReportBuilder before they're allowed in YAML."""
    KNOWN_KINDS = {
        "kpi_grid", "table", "distribution",
        "alerts_list", "timeline", "step_breakdown",
    }
    cat = ReportSchemaCatalog(schema_dir=REPO_SCHEMA_DIR)
    cat.reload()
    for sid in cat.known_solutions() + ["_default"]:
        s = cat.get(sid)
        for sec in s.sections:
            assert sec.kind in KNOWN_KINDS, f"{sid}: section {sec.id} has unknown kind {sec.kind}"
