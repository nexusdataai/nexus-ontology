"""
JourneyReport schema catalog.

Loads YAML report-schema files from
``enterprise-knowledge/report-schemas/{solution_id}.yaml`` and exposes
them as typed dataclasses so a single generic builder
(`JourneyReportBuilder`) can produce a journey-specific report without
any per-solution Python code.

Schema shape (see plan section 3):

    solution_id: demand-forecasting
    title: "Demand Forecasting Report"
    icon: TrendingUp
    summary_kpis:
      - key, label, icon, format, rollup, source[, threshold]
    sections:
      - id, title, kind, kpis[], source[], grouping[]

Format codes understood by the UI: percent | integer | duration |
currency | decimal | text.

Rollup codes understood by the builder: avg | sum | last | max | min |
count_distinct.

Section kinds: kpi_grid | table | distribution | alerts_list | timeline
| step_breakdown.

When a schema fails to parse, the catalog logs a warning and falls
back to the ``_default`` schema for that solution rather than crashing
the gateway. Unknown solution_ids also resolve to ``_default``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger


# Where the YAML files live -- a sibling of `enterprise-knowledge/
# automation/`. Path is computed relative to the backend repo root so
# the catalog works in dev / pytest / container alike.
_DEFAULT_SCHEMA_DIR_FALLBACK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "enterprise-knowledge",
    "report-schemas",
)


# ---------------------------------------------------------------------------
# Typed schema dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ReportKpi:
    """A single KPI tile / column.

    ``source`` is a dotted path resolved against a JobExecution row's
    ``Data`` (e.g. ``Data.kpis.mape``). The special prefix ``derived.``
    selects a builder-computed field instead (total_jobs, avg_duration,
    success_rate, etc.).
    """

    key: str
    label: str
    icon: Optional[str] = None
    format: str = "integer"  # percent | integer | duration | currency | decimal | text
    rollup: str = "last"  # avg | sum | last | max | min | count_distinct
    source: str = ""
    threshold: Optional[Dict[str, float]] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReportKpi":
        return cls(
            key=str(d.get("key") or ""),
            label=str(d.get("label") or d.get("key") or ""),
            icon=d.get("icon"),
            format=str(d.get("format") or "integer"),
            rollup=str(d.get("rollup") or "last"),
            source=str(d.get("source") or ""),
            threshold=d.get("threshold") if isinstance(d.get("threshold"), dict) else None,
        )


@dataclass
class ReportSection:
    """One detail block under the summary strip."""

    id: str
    title: str
    kind: str  # kpi_grid | table | distribution | alerts_list | timeline | step_breakdown
    kpis: List[ReportKpi] = field(default_factory=list)
    source: Optional[str] = None  # for alerts_list / distribution / table sections
    grouping: Optional[Dict[str, Any]] = None
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReportSection":
        kpis_raw = d.get("kpis") or []
        return cls(
            id=str(d.get("id") or ""),
            title=str(d.get("title") or ""),
            kind=str(d.get("kind") or "kpi_grid"),
            kpis=[ReportKpi.from_dict(k) for k in kpis_raw if isinstance(k, dict)],
            source=d.get("source"),
            grouping=d.get("grouping") if isinstance(d.get("grouping"), dict) else None,
            description=d.get("description"),
        )


@dataclass
class ReportSchema:
    solution_id: str
    title: str
    icon: Optional[str]
    summary_kpis: List[ReportKpi] = field(default_factory=list)
    sections: List[ReportSection] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReportSchema":
        return cls(
            solution_id=str(d.get("solution_id") or "_default"),
            title=str(d.get("title") or "Journey Report"),
            icon=d.get("icon"),
            summary_kpis=[
                ReportKpi.from_dict(k) for k in (d.get("summary_kpis") or []) if isinstance(k, dict)
            ],
            sections=[
                ReportSection.from_dict(s) for s in (d.get("sections") or []) if isinstance(s, dict)
            ],
        )


# ---------------------------------------------------------------------------
# Default fallback schema (used for unknown solution_ids + as a baseline
# Copilot-saved/Journey-Builder template when their YAML isn't bundled).
# ---------------------------------------------------------------------------


def _default_schema(solution_id: str = "_default") -> ReportSchema:
    """A minimal report that works for ANY journey: surfaces job-level
    counters + step breakdown + transition timeline. Uses paths that
    map to the JobExecution row shape every job carries regardless of
    domain."""
    return ReportSchema(
        solution_id=solution_id,
        title="Journey Report",
        icon="BarChart3",
        summary_kpis=[
            ReportKpi(
                key="total_jobs", label="Total Jobs", icon="Layers",
                format="integer", rollup="last", source="derived.total_jobs",
            ),
            ReportKpi(
                key="completed_jobs", label="Completed", icon="CheckCircle",
                format="integer", rollup="last", source="derived.completed_jobs",
            ),
            ReportKpi(
                key="failed_jobs", label="Failed", icon="XCircle",
                format="integer", rollup="last", source="derived.failed_jobs",
            ),
            ReportKpi(
                key="avg_duration", label="Avg Duration", icon="Clock",
                format="duration", rollup="avg", source="derived.avg_duration_seconds",
            ),
        ],
        sections=[
            ReportSection(
                id="performance",
                title="Performance",
                kind="kpi_grid",
                kpis=[
                    ReportKpi(key="success_rate", label="Success Rate",
                              format="percent", rollup="last",
                              source="derived.success_rate"),
                    ReportKpi(key="total_jobs", label="Jobs",
                              format="integer", rollup="last",
                              source="derived.total_jobs"),
                ],
            ),
            ReportSection(
                id="step_breakdown",
                title="Step Breakdown",
                kind="step_breakdown",
                source="Data.stepResults",
            ),
            ReportSection(
                id="timeline",
                title="Run Timeline",
                kind="timeline",
                source="derived.transitions",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class ReportSchemaCatalog:
    """Lazy YAML-backed lookup of ``solution_id -> ReportSchema``.

    The catalog walks ``enterprise-knowledge/report-schemas/*.yaml`` on
    first access and caches the parsed schemas. ``reload()`` re-walks
    the directory and is safe to call at runtime; useful for dev
    iteration where editing a YAML file should reflect in the next
    request without a pod restart (gateway exposes this through an
    admin route in a future PR; today only the catalog is reload-able).
    """

    def __init__(self, schema_dir: Optional[str] = None):
        self._schema_dir = schema_dir or _DEFAULT_SCHEMA_DIR_FALLBACK
        self._cache: Dict[str, ReportSchema] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self.reload()

    def reload(self) -> None:
        self._cache.clear()
        if not os.path.isdir(self._schema_dir):
            logger.info(
                "ReportSchemaCatalog: schema dir not found ({}), only the default "
                "fallback will be served", self._schema_dir,
            )
            self._loaded = True
            return
        loaded = 0
        for fname in sorted(os.listdir(self._schema_dir)):
            if not fname.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(self._schema_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    parsed = yaml.safe_load(fh) or {}
                schema = ReportSchema.from_dict(parsed)
                if not schema.solution_id:
                    logger.warning("ReportSchemaCatalog: {} missing solution_id; skipped", fname)
                    continue
                self._cache[schema.solution_id] = schema
                loaded += 1
            except Exception as e:
                logger.warning(
                    "ReportSchemaCatalog: failed to load {} -- falling back to default for "
                    "that solution: {}", path, e,
                )
        self._loaded = True
        logger.info(
            "ReportSchemaCatalog: loaded {} schema(s) from {}",
            loaded, self._schema_dir,
        )

    def get(self, solution_id: Optional[str]) -> ReportSchema:
        """Return the schema for ``solution_id``. Falls back to the
        default schema when the solution is unknown or the YAML file
        failed to load."""
        self._ensure_loaded()
        if solution_id and solution_id in self._cache:
            return self._cache[solution_id]
        # Cached default schema -- copy so callers can't mutate the singleton.
        if "_default" in self._cache:
            return self._cache["_default"]
        return _default_schema(solution_id or "_default")

    def known_solutions(self) -> List[str]:
        self._ensure_loaded()
        return sorted(k for k in self._cache.keys() if k != "_default")


# ---------------------------------------------------------------------------
# Singleton accessor (initialised by the gateway at startup; exported so
# tests can construct their own instances against a tmp directory)
# ---------------------------------------------------------------------------


_singleton: Optional[ReportSchemaCatalog] = None


def get_catalog() -> ReportSchemaCatalog:
    global _singleton
    if _singleton is None:
        _singleton = ReportSchemaCatalog()
    return _singleton


def set_catalog(catalog: ReportSchemaCatalog) -> None:
    """Replace the singleton (used by the gateway during startup wiring
    + by tests that want to point the catalog at a tmp dir)."""
    global _singleton
    _singleton = catalog
