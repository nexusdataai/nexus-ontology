from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from src.stages.etl_pipeline.etl_pipeline_processor import ETLPipelineProcessor


def test_register_vdl_step_skipped_for_generic():
    proc = ETLPipelineProcessor(config={"sourceType": "generic"}, log_callback=None)
    out = proc.step_register_vdl({})
    assert out["status"] == "skipped"


def test_register_vdl_step_runs_for_social_listening():
    proc = ETLPipelineProcessor(
        config={"sourceType": "social_listening", "jobId": "job-1"},
        log_callback=None,
    )
    summary = {"created": 3, "skipped": 1, "errors": 0, "detail": []}
    with patch.object(proc, "_run_async", return_value=summary):
        out = proc.step_register_vdl({})
    assert out["status"] == "completed"
    assert out["created"] == 3
    assert proc._kpis["vdl_rules_created"] == 3