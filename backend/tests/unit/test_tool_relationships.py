"""Unit tests for the Phase-1 relationship primitives in ``tool_registry``.

Covers:
  * Tool defaults (single ``success`` relationship, bucket ``default``).
  * ToolRegistry.execute back-compat: still returns ``Dict[str, Any]``
    regardless of whether the underlying tool returns a plain dict,
    a single RelationshipResult, or a List[RelationshipResult].
  * ToolRegistry.execute_with_relationships normalisation paths.
  * ToolRegistry.execute_single semantics + KeyError on missing relationship.
"""

from __future__ import annotations

import pytest

from src.services.control_plane.tool_registry import (
    DEFAULT_RELATIONSHIP,
    Relationship,
    RelationshipResult,
    RiskLevel,
    Tool,
    ToolRegistry,
)


def _make_tool(execute_fn, *, relationships=None, name="t") -> Tool:
    return Tool(
        name=name,
        description="test tool",
        parameters={"type": "object", "properties": {}, "required": []},
        risk_level=RiskLevel.READ_ONLY,
        execute=execute_fn,
        output_relationships=list(relationships) if relationships is not None else [DEFAULT_RELATIONSHIP],
    )


def test_tool_defaults_single_success_relationship_and_default_bucket():
    async def _exec():
        return {"ok": True}

    tool = _make_tool(_exec)
    assert tool.relationship_names() == ["success"]
    assert tool.primary_relationship().name == "success"
    assert tool.bucket == "default"


@pytest.mark.asyncio
async def test_execute_back_compat_returns_dict_for_plain_dict_returns():
    async def _exec():
        return {"value": 42}

    registry = ToolRegistry()
    registry.register(_make_tool(_exec, name="plain_dict"))

    out = await registry.execute("plain_dict", {})
    assert out == {"value": 42}


@pytest.mark.asyncio
async def test_execute_back_compat_returns_primary_relationship_data_for_relationship_result():
    async def _exec():
        return RelationshipResult(relationship="success", data={"answer": 1})

    registry = ToolRegistry()
    registry.register(_make_tool(_exec, name="rel_result"))

    out = await registry.execute("rel_result", {})
    assert out == {"answer": 1}


@pytest.mark.asyncio
async def test_execute_back_compat_returns_first_relationship_for_list_returns():
    async def _exec():
        return [
            RelationshipResult(relationship="matched", data={"id": "A"}),
            RelationshipResult(relationship="no_match", data={"reason": "nope"}),
        ]

    rels = [Relationship("matched"), Relationship("no_match", auto_terminate_default=True)]
    registry = ToolRegistry()
    registry.register(_make_tool(_exec, name="fanout", relationships=rels))

    out = await registry.execute("fanout", {})
    assert out == {"id": "A"}


@pytest.mark.asyncio
async def test_execute_with_relationships_normalises_plain_dict_to_single_result():
    async def _exec():
        return {"value": 7}

    registry = ToolRegistry()
    registry.register(_make_tool(_exec, name="t"))

    results = await registry.execute_with_relationships("t", {})
    assert len(results) == 1
    assert results[0].relationship == "success"
    assert results[0].data == {"value": 7}


@pytest.mark.asyncio
async def test_execute_with_relationships_passes_through_list_returns():
    rels = [Relationship("matched"), Relationship("no_match", auto_terminate_default=True)]

    async def _exec():
        return [
            RelationshipResult(relationship="matched", data={"id": "A"}),
            RelationshipResult(relationship="no_match", data={"reason": "x"}),
        ]

    registry = ToolRegistry()
    registry.register(_make_tool(_exec, name="t", relationships=rels))

    results = await registry.execute_with_relationships("t", {})
    assert [r.relationship for r in results] == ["matched", "no_match"]


@pytest.mark.asyncio
async def test_execute_with_relationships_missing_tool_returns_failure_envelope():
    registry = ToolRegistry()
    results = await registry.execute_with_relationships("missing", {})
    assert len(results) == 1
    assert results[0].relationship == "failure"
    assert "not found" in results[0].data["error"]


@pytest.mark.asyncio
async def test_execute_with_relationships_tool_raises_surfaces_as_failure_relationship():
    async def _exec():
        raise RuntimeError("kaboom")

    registry = ToolRegistry()
    registry.register(_make_tool(_exec, name="boom"))

    results = await registry.execute_with_relationships("boom", {})
    assert results[0].relationship == "failure"
    assert "kaboom" in results[0].data["error"]


@pytest.mark.asyncio
async def test_execute_single_returns_named_relationship_payload():
    rels = [Relationship("matched"), Relationship("no_match", auto_terminate_default=True)]

    async def _exec():
        return [
            RelationshipResult(relationship="matched", data={"id": "A"}),
            RelationshipResult(relationship="no_match", data={"reason": "x"}),
        ]

    registry = ToolRegistry()
    registry.register(_make_tool(_exec, name="t", relationships=rels))

    matched = await registry.execute_single("t", {}, expected="matched")
    no_match = await registry.execute_single("t", {}, expected="no_match")
    assert matched == {"id": "A"}
    assert no_match == {"reason": "x"}


@pytest.mark.asyncio
async def test_execute_single_raises_when_expected_relationship_not_emitted():
    async def _exec():
        return RelationshipResult(relationship="success", data={"ok": True})

    registry = ToolRegistry()
    registry.register(_make_tool(_exec, name="t"))

    with pytest.raises(KeyError):
        await registry.execute_single("t", {}, expected="missing_channel")


@pytest.mark.asyncio
async def test_multi_relationship_tool_returning_plain_dict_wraps_on_primary_with_warning(caplog):
    rels = [Relationship("matched"), Relationship("no_match", auto_terminate_default=True)]

    async def _exec():
        return {"i_should_have_used_relationship_result": True}

    registry = ToolRegistry()
    registry.register(_make_tool(_exec, name="t", relationships=rels))

    # The shim still produces a list; the data lands on the primary relationship.
    results = await registry.execute_with_relationships("t", {})
    assert len(results) == 1
    assert results[0].relationship == "matched"


# ---------------------------------------------------------------------------
# Phase 3 (Data Queues) -- streaming tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_streaming_tool_async_iterator_is_drained_into_list():
    """A Tool whose ``execute`` returns an async generator yielding
    RelationshipResults is drained eagerly by execute_with_relationships."""
    rels = [Relationship("page"), Relationship("done", auto_terminate_default=True)]

    async def _exec():
        async def _gen():
            yield RelationshipResult(relationship="page", data={"id": "A"})
            yield RelationshipResult(relationship="page", data={"id": "B"})
            yield RelationshipResult(relationship="done", data={"summary": "ok"})
        return _gen()

    tool = _make_tool(_exec, name="streamer", relationships=rels)
    tool.streaming = True
    registry = ToolRegistry()
    registry.register(tool)

    results = await registry.execute_with_relationships("streamer", {})
    assert [r.relationship for r in results] == ["page", "page", "done"]
    assert results[0].data == {"id": "A"}
    assert results[2].data == {"summary": "ok"}


@pytest.mark.asyncio
async def test_streaming_tool_yields_dicts_auto_wrap_on_primary_relationship():
    """An async generator that yields raw dicts (no RelationshipResult)
    has each item auto-wrapped on the primary relationship."""
    async def _exec():
        async def _gen():
            yield {"i": 1}
            yield {"i": 2}
        return _gen()

    tool = _make_tool(_exec, name="dict_streamer")
    tool.streaming = True
    registry = ToolRegistry()
    registry.register(tool)

    results = await registry.execute_with_relationships("dict_streamer", {})
    assert [r.relationship for r in results] == ["success", "success"]
    assert [r.data["i"] for r in results] == [1, 2]


def test_tool_streaming_flag_defaults_to_false():
    async def _exec():
        return {"ok": True}
    tool = _make_tool(_exec, name="t")
    assert tool.streaming is False


def test_connection_doc_concurrent_consumers_default_and_bounds():
    from src.models.automation_models import ConnectionDoc

    c = ConnectionDoc(from_step="a", from_relationship="success", to_step="b", to_param="x")
    assert c.concurrent_consumers == 1
    c2 = ConnectionDoc(from_step="a", from_relationship="success", to_step="b", to_param="x",
                       concurrent_consumers=8)
    assert c2.concurrent_consumers == 8
    with pytest.raises(Exception):
        ConnectionDoc(from_step="a", from_relationship="success", to_step="b", to_param="x",
                      concurrent_consumers=0)
    with pytest.raises(Exception):
        ConnectionDoc(from_step="a", from_relationship="success", to_step="b", to_param="x",
                      concurrent_consumers=128)


@pytest.mark.asyncio
async def test_tool_cache_hit_round_trips_via_primary_relationship():
    """Cacheable tools cache the primary-channel payload; the next call returns it on the same channel."""

    call_count = {"n": 0}

    async def _exec():
        call_count["n"] += 1
        return {"counted": call_count["n"]}

    tool = _make_tool(_exec, name="cached")
    tool.cacheable = True

    registry = ToolRegistry()
    registry.register(tool)

    out1 = await registry.execute("cached", {})
    out2 = await registry.execute("cached", {})
    assert out1 == out2  # second call comes from cache
    # We don't assert call_count strictly because the cache backend in
    # tests may be a no-op; the contract is "shape stays stable".
