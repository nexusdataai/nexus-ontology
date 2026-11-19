from src.services.simulator_hydration_service import _needs_hydration


def test_needs_hydration_empty_stats():
    need, reason = _needs_hydration({"table_count": 9, "tables_with_data": 0, "total_rows": 0}, 0)
    assert need is True
    assert reason == "empty_catalogue_stats"


def test_needs_hydration_cache_miss():
    need, reason = _needs_hydration({"table_count": 9, "tables_with_data": 5, "total_rows": 1000}, 0)
    assert need is True
    assert reason == "cache_miss_despite_manifest"


def test_needs_hydration_ok():
    need, _ = _needs_hydration({"table_count": 9, "tables_with_data": 5, "total_rows": 100}, 3)
    assert need is False