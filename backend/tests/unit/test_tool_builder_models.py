"""
Unit tests for ``models/tool_builder_models.py``.

Covers the AST + JSON Schema validation that gates every tool create/
update so a malformed source string never reaches the registry.
"""

from __future__ import annotations

import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.models.tool_builder_models import (
    SOURCE_CODE_MAX_BYTES,
    ToolCreate,
    ToolUpdate,
    source_hash,
)


_GOOD_SOURCE = """
async def run(params, vdl, connectors, ctx, log):
    return {"ok": True}
""".strip()


def test_create_accepts_valid_tool():
    body = ToolCreate(
        name="my_tool",
        description="hello",
        risk_level="read_only",
        source_code=_GOOD_SOURCE,
        parameters={"type": "object", "properties": {}, "required": []},
    )
    assert body.name == "my_tool"
    assert body.risk_level.value == "read_only"


def test_create_rejects_invalid_name():
    for bad in ["My_Tool", "1tool", "tool with space", "tool-dash"]:
        with pytest.raises(Exception):
            ToolCreate(
                name=bad,
                risk_level="read_only",
                source_code=_GOOD_SOURCE,
            )


def test_create_rejects_collision_with_code_tool():
    with pytest.raises(Exception):
        ToolCreate(
            name="discover_tables",
            risk_level="read_only",
            source_code=_GOOD_SOURCE,
        )


def test_create_rejects_source_without_run():
    with pytest.raises(Exception):
        ToolCreate(
            name="my_tool",
            risk_level="read_only",
            source_code="x = 1\n",
        )


def test_create_rejects_run_with_wrong_args():
    bad_source = "async def run(only_one):\n    return {}\n"
    with pytest.raises(Exception):
        ToolCreate(
            name="my_tool",
            risk_level="read_only",
            source_code=bad_source,
        )


def test_create_rejects_oversized_source():
    big = "async def run(params, vdl, connectors, ctx, log):\n    return {}\n"
    big = big + ("    # padding\n" * (SOURCE_CODE_MAX_BYTES // 12))
    with pytest.raises(Exception):
        ToolCreate(
            name="my_tool",
            risk_level="read_only",
            source_code=big,
        )


def test_create_rejects_invalid_parameters_schema():
    with pytest.raises(Exception):
        ToolCreate(
            name="my_tool",
            risk_level="read_only",
            source_code=_GOOD_SOURCE,
            parameters={"type": "array"},  # not object
        )
    with pytest.raises(Exception):
        ToolCreate(
            name="my_tool",
            risk_level="read_only",
            source_code=_GOOD_SOURCE,
            parameters={"type": "object", "required": ["missing"], "properties": {}},
        )


def test_update_validates_source_when_present():
    body = ToolUpdate(source_code=_GOOD_SOURCE)
    assert body.source_code is not None
    with pytest.raises(Exception):
        ToolUpdate(source_code="x = 1")


def test_update_allows_partial_payload():
    body = ToolUpdate(description="just a doc tweak")
    assert body.description == "just a doc tweak"
    assert body.source_code is None
    assert body.parameters is None


def test_source_hash_is_deterministic():
    a = source_hash(_GOOD_SOURCE)
    b = source_hash(_GOOD_SOURCE)
    assert a == b
    assert len(a) == 64
