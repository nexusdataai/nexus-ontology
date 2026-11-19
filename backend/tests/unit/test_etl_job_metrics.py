from __future__ import annotations

from src.utils.job_executor import derive_etl_pipeline_counts


class _FakeProc:
    def __init__(self, kpis):
        self._kpis = kpis


class _FakeStage:
    def __init__(self, kpis):
        self.processor = _FakeProc(kpis)


def test_derive_etl_pipeline_counts_prefers_loaded():
    stage = _FakeStage(
        {"rows_extracted": 88, "rows_transformed": 88, "rows_loaded": 86}
    )
    processed, total, details = derive_etl_pipeline_counts(stage)
    assert processed == 86
    assert total == 88
    assert details["rowsExtracted"] == 88
    assert details["successfulProcessing"] == 86


def test_derive_etl_pipeline_counts_empty_kpis():
    stage = _FakeStage({})
    processed, total, details = derive_etl_pipeline_counts(stage)
    assert processed == 0
    assert total == 0
    assert details == {}