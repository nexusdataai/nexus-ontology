"""Tests for the new ``BaseStage.set_kpis`` / ``effective_kpis``
hooks and the job_executor.complete_job persistence path.

We exercise the smallest possible scope to avoid pulling in the full
TransformationJobExecutor + AWS client chain: the dataclass-style
helpers on a stand-in stage with the same attribute surface as
``BaseStage``.
"""

from __future__ import annotations

from typing import Any, Dict


class _MiniStage:
    """Stand-in that exposes the BaseStage methods under test without
    actually depending on the BaseStage's heavy AWS init path."""

    def __init__(self):
        from src.stages.base_stage import BaseStage as _Real
        self._real_set_kpis = _Real.set_kpis
        self._real_effective_kpis = _Real.effective_kpis
        self.kpis: Dict[str, Any] = {}
        self._processor = None

    def set_kpis(self, kpis):
        return self._real_set_kpis(self, kpis)

    def effective_kpis(self):
        return self._real_effective_kpis(self)


def test_set_kpis_records_dict() -> None:
    s = _MiniStage()
    s.set_kpis({"mape": 12, "stockout_rate_pct": 5})
    assert s.kpis == {"mape": 12, "stockout_rate_pct": 5}


def test_set_kpis_copies_input() -> None:
    s = _MiniStage()
    src = {"a": 1}
    s.set_kpis(src)
    src["b"] = 2  # mutate source
    assert "b" not in s.kpis, "set_kpis must copy so source mutations don't leak"


def test_set_kpis_ignores_non_dict() -> None:
    s = _MiniStage()
    s.set_kpis("not a dict")  # type: ignore[arg-type]
    s.set_kpis(None)  # type: ignore[arg-type]
    assert s.kpis == {}


def test_effective_kpis_prefers_explicit_set() -> None:
    s = _MiniStage()
    s._processor = type("P", (), {"_kpis": {"from_processor": True}})()
    s.set_kpis({"explicit": True})
    assert s.effective_kpis() == {"explicit": True}


def test_effective_kpis_falls_back_to_processor_kpis() -> None:
    """The auto-discovery path -- every domain processor exposes
    ``self._kpis`` after _compute_kpis runs. BaseStage picks it up
    without needing per-stage set_kpis call."""
    s = _MiniStage()
    s._processor = type("P", (), {"_kpis": {"dso": 35, "match_rate": 0.92}})()
    assert s.effective_kpis() == {"dso": 35, "match_rate": 0.92}


def test_effective_kpis_returns_empty_when_nothing_set() -> None:
    s = _MiniStage()
    assert s.effective_kpis() == {}


def test_effective_kpis_handles_no_processor_attr() -> None:
    """Stages with no processor attribute at all -- shouldn't raise."""
    s = _MiniStage()
    del s._processor
    assert s.effective_kpis() == {}


def test_effective_kpis_handles_processor_without_kpis() -> None:
    s = _MiniStage()
    s._processor = type("P", (), {})()  # no _kpis attr
    assert s.effective_kpis() == {}


def test_effective_kpis_falls_back_to_processor_metrics() -> None:
    """semantic-rag's processor uses ``_metrics`` not ``_kpis``. The
    fallback path picks it up so the report builder has data to
    aggregate."""
    s = _MiniStage()
    s._processor = type("P", (), {
        "_metrics": {
            "total_onto_documents": 1234,
            "embedding_chunks": 5678,
            "vector_upserted": 5678,
        },
    })()
    out = s.effective_kpis()
    assert out["total_onto_documents"] == 1234
    assert out["embedding_chunks"] == 5678
    assert out["vector_upserted"] == 5678


def test_effective_kpis_handles_bare_processor_attribute() -> None:
    """Some stage subclasses (e.g. semantic_rag) use ``self.processor``
    (no underscore prefix). Both naming conventions must work."""
    s = _MiniStage()
    # Remove the underscore-prefixed attribute and add the bare one.
    del s._processor
    s.processor = type("P", (), {  # type: ignore[attr-defined]
        "_metrics": {"vector_upserted": 999},
    })()
    out = s.effective_kpis()
    assert out == {"vector_upserted": 999}


def test_effective_kpis_prefers_kpis_over_metrics() -> None:
    """When BOTH ``_kpis`` and ``_metrics`` are populated, ``_kpis``
    wins because it's the authoritative finalizer output."""
    s = _MiniStage()
    s._processor = type("P", (), {
        "_kpis": {"primary": True},
        "_metrics": {"telemetry": True},
    })()
    assert s.effective_kpis() == {"primary": True}
