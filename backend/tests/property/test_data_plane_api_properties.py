"""
Property-based tests for Data Plane API router.

Properties 3, 4, 8, 11
"""

import asyncio
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import boto3
import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from hypothesis.strategies import composite
from moto import mock_dynamodb
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from src.models.data_plane_models import DataPlaneCreateRequest, DataPlaneType, DataPlaneStatus
from src.services.data_plane_service import DataPlaneService
from src.apis import data_plane_api

TABLE_NAME = "test-foundry-workspace"
REGION = "us-east-1"

_safe_text = st.text(
    min_size=1, max_size=30,
    alphabet=st.characters(whitelist_categories=("L", "N"), blacklist_characters="\x00"),
).filter(lambda s: s.strip() != "")

_fdw_config_st = st.fixed_dictionaries({
    "host": _safe_text, "port": st.integers(1, 65535),
    "database": _safe_text, "user": _safe_text, "password": _safe_text,
})

_cdc_config_st = st.fixed_dictionaries({
    "bootstrapServers": _safe_text, "topicPrefix": _safe_text, "sourceDatabase": _safe_text,
})


def _create_table():
    """Foundry-workspace shape (PK/SK + GSI1) — see test_data_plane_service.py."""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_app():
    app = FastAPI()
    app.include_router(data_plane_api.router)
    return app


async def _setup_service():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = REGION
    _create_table()
    svc = DataPlaneService(table_name=TABLE_NAME)
    svc._region = REGION
    await svc.initialize()
    data_plane_api.configure(svc)
    return svc


class TestNonExistentIdReturns404:
    """Property 3: Non-existent ID returns 404. Validates: Requirements 1.5, 2.6"""

    @given(fake_id=st.uuids().map(str))
    @settings(max_examples=3, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @mock_dynamodb
    def test_get_nonexistent_returns_404(self, fake_id):
        async def _test():
            await _setup_service()
            app = _make_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get(f"/api/data-planes/{fake_id}")
                assert r.status_code == 404
                assert "error" in r.json()["detail"]
        _run(_test())

    @given(fake_id=st.uuids().map(str))
    @settings(max_examples=3, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @mock_dynamodb
    def test_delete_nonexistent_returns_404(self, fake_id):
        async def _test():
            await _setup_service()
            app = _make_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(f"/api/data-planes/{fake_id}")
                assert r.status_code == 404
        _run(_test())


class TestDeleteRemovesRecord:
    """Property 4: Delete removes record. Validates: Requirements 2.5"""

    @given(name=_safe_text, config=_cdc_config_st)
    @settings(max_examples=3, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @mock_dynamodb
    def test_delete_then_get_returns_404(self, name, config):
        async def _test():
            await _setup_service()
            app = _make_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                create_r = await client.post("/api/data-planes", json={
                    "name": name, "type": "CDC", "connectionConfig": config
                })
                assert create_r.status_code == 201
                dp_id = create_r.json()["id"]
                del_r = await client.delete(f"/api/data-planes/{dp_id}")
                assert del_r.status_code == 204
                get_r = await client.get(f"/api/data-planes/{dp_id}")
                assert get_r.status_code == 404
        _run(_test())


class TestCDCETLExploreReturnsMock:
    """Property 8: CDC/ETL exploration returns mock. Validates: Requirements 4.3, 4.4"""

    @given(
        name=_safe_text,
        dp_type=st.sampled_from(["CDC", "ETL"]),
        config=_cdc_config_st,
    )
    @settings(max_examples=3, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @mock_dynamodb
    def test_explore_cdc_etl_returns_mock(self, name, dp_type, config):
        async def _test():
            await _setup_service()
            app = _make_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                create_r = await client.post("/api/data-planes", json={
                    "name": name, "type": dp_type, "connectionConfig": config
                })
                assert create_r.status_code == 201
                dp_id = create_r.json()["id"]
                explore_r = await client.get(f"/api/data-planes/{dp_id}/explore")
                assert explore_r.status_code == 200
                body = explore_r.json()
                assert body["servers"] == []
                assert body["message"] is not None
        _run(_test())


class TestErrorResponseStructure:
    """Property 11: Error responses have consistent structure. Validates: Requirements 6.2"""

    @mock_dynamodb
    def test_404_has_error_key(self):
        async def _test():
            await _setup_service()
            app = _make_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/api/data-planes/nonexistent")
                assert r.status_code == 404
                body = r.json()
                assert "error" in body.get("detail", {})
        _run(_test())
