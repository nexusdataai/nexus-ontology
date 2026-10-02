"""Tests for the JourneyReportBuilder rollup engine + path resolver.

These exercise the low-level helpers (``_resolve_path``, ``_rollup``,
``_threshold_status``) directly so each rollup/format mapping is
locked in -- a regression here would silently mis-aggregate every
journey type's report.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.services.journey_report_builder import (
    _resolve_path, _rollup, _threshold_status, _coerce_number,
)


# -------------------------- path resolver -------------------------------- #


def test_resolve_simple_path() -> None:
    assert _resolve_path({"a": {"b": 1}}, "a.b") == 1
    assert _resolve_path({"a": {"b": 1}}, "a.c") is None


def test_resolve_list_index() -> None:
    assert _resolve_path({"items": [{"k": "x"}, {"k": "y"}]}, "items.0.k") == "x"
    assert _resolve_path({"items": [{"k": "x"}, {"k": "y"}]}, "items.1.k") == "y"
    assert _resolve_path({"items": []}, "items.0.k") is None
    assert _resolve_path({"items": [1, 2]}, "items.5") is None


def test_resolve_decimal_normalised_to_float() -> None:
    assert _resolve_path({"k": Decimal("3.14")}, "k") == 3.14


def test_resolve_missing_intermediate() -> None:
    assert _resolve_path({"a": "scalar"}, "a.b.c") is None
    assert _resolve_path(None, "a") is None  # type: ignore[arg-type]
    assert _resolve_path({}, "") is None


# -------------------------- rollups -------------------------------------- #


def test_rollup_sum_ignores_non_numeric() -> None:
    assert _rollup([1, 2, "x", None, 4], "sum") == 7


def test_rollup_avg() -> None:
    assert _rollup([10, 20, 30], "avg") == 20


def test_rollup_max_min() -> None:
    assert _rollup([5, 10, 3, 8], "max") == 10
    assert _rollup([5, 10, 3, 8], "min") == 3


def test_rollup_last_skips_none() -> None:
    assert _rollup([None, None, "hello", "world"], "last") == "hello"
    assert _rollup([None, None], "last") is None


def test_rollup_count_distinct() -> None:
    assert _rollup(["a", "b", "a", "c"], "count_distinct") == 3
    assert _rollup([None, "a", None, "a"], "count_distinct") == 1


def test_rollup_empty_list_returns_none() -> None:
    for r in ("sum", "avg", "max", "min", "last", "count_distinct"):
        assert _rollup([], r) is None


def test_rollup_count_distinct_unhashable_falls_back() -> None:
    # Lists / dicts aren't hashable -> fallback counts non-None entries.
    assert _rollup([{"a": 1}, {"b": 2}, None, {"c": 3}], "count_distinct") == 3


def test_rollup_unknown_returns_first_non_none() -> None:
    assert _rollup([None, 42, 99], "wat_is_this") == 42


# -------------------------- threshold ----------------------------------- #


def test_threshold_higher_is_worse() -> None:
    th = {"warn": 5, "critical": 10}
    assert _threshold_status(0, th) == "ok"
    assert _threshold_status(6, th) == "warn"
    assert _threshold_status(11, th) == "critical"


def test_threshold_inverted() -> None:
    # invert: lower is worse (e.g. success rate %).
    th = {"warn": 90, "critical": 75, "invert": True}
    assert _threshold_status(95, th) == "ok"
    assert _threshold_status(89, th) == "warn"
    assert _threshold_status(70, th) == "critical"


def test_threshold_none_when_no_threshold_or_no_value() -> None:
    assert _threshold_status(50, None) is None
    assert _threshold_status(None, {"warn": 5, "critical": 10}) is None
    assert _threshold_status("notanumber", {"warn": 5, "critical": 10}) is None


def test_coerce_number_handles_bool_and_decimal() -> None:
    assert _coerce_number(True) == 1.0
    assert _coerce_number(False) == 0.0
    assert _coerce_number(Decimal("2.5")) == 2.5
    assert _coerce_number("3.14") == 3.14
    assert _coerce_number("not-a-number") is None
    assert _coerce_number(None) is None
