"""Unit tests for the Phase-1 buckets API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.apis import buckets_api
from src.services.control_plane.tool_registry import (
    Relationship,
    RiskLevel,
    Tool,
    ToolRegistry,
)


def _t(name: str, *, bucket: str = "default", risk: RiskLevel = RiskLevel.READ_ONLY,
       relationships: Optional[List[Relationship]] = None) -> Tool:
    return Tool(
        name=name,
        description=f"desc:{name}",
        parameters={"type": "object", "properties": {}, "required": []},
        risk_level=risk,
        execute=_noop,
        bucket=bucket,
        output_relationships=relationships or [Relationship("success")],
    )


async def _noop(**_kw):
    return {"ok": True}


def _client(*tools: Tool) -> TestClient:
    registry = ToolRegistry()
    for t in tools:
        registry.register(t)
    buckets_api.configure(tool_registry=registry)
    app = FastAPI()
    app.include_router(buckets_api.router)
    return TestClient(app)


def test_list_buckets_includes_catalogue_defaults_when_registry_is_empty():
    client = _client()
    res = client.get("/api/v1/control-plane/buckets")
    assert res.status_code == 200
    payload = res.json()
    names = {b["name"] for b in payload["buckets"]}
    # All 9 catalogued buckets surface even when no tools registered.
    assert {
        "customer-360", "o2c", "supply-chain", "esg", "platform-rag",
        "notify", "infra-query", "dynamic", "default",
    } <= names


def test_list_buckets_groups_tools_by_bucket_and_reports_counts():
    client = _client(
        _t("a", bucket="customer-360"),
        _t("b", bucket="customer-360"),
        _t("c", bucket="o2c"),
    )
    res = client.get("/api/v1/control-plane/buckets")
    by_name = {b["name"]: b for b in res.json()["buckets"]}
    assert by_name["customer-360"]["tool_count"] == 2
    assert by_name["o2c"]["tool_count"] == 1
    assert "default" in by_name


def test_get_bucket_returns_tools_with_relationships():
    client = _client(
        _t("apply_promo_discount", bucket="customer-360",
           risk=RiskLevel.HIGH_RISK_WRITE,
           relationships=[Relationship("promo_created"), Relationship("failure", auto_terminate_default=True)]),
    )
    res = client.get("/api/v1/control-plane/buckets/customer-360")
    assert res.status_code == 200
    payload = res.json()
    assert payload["tool_count"] == 1
    tool = payload["tools"][0]
    assert tool["name"] == "apply_promo_discount"
    assert [r["name"] for r in tool["output_relationships"]] == ["promo_created", "failure"]
    assert tool["output_relationships"][1]["auto_terminate_default"] is True


def test_get_bucket_404s_for_unknown_uncatalogued_name():
    client = _client(_t("a", bucket="customer-360"))
    res = client.get("/api/v1/control-plane/buckets/not-a-real-bucket")
    assert res.status_code == 404


def test_get_bucket_tools_filters_by_search():
    client = _client(
        _t("find_churning_customers", bucket="customer-360"),
        _t("find_upsell_candidates", bucket="customer-360"),
        _t("apply_promo_discount", bucket="customer-360"),
    )
    res = client.get("/api/v1/control-plane/buckets/customer-360/tools?search=churn")
    payload = res.json()
    assert payload["tool_count"] == 1
    assert payload["tools"][0]["name"] == "find_churning_customers"
