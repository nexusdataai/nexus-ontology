"""
Unit tests for Data Plane API router.

Validates: Requirements 2.1-2.6, 3.2, 3.6, 4.3
"""

import asyncio
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import boto3
import pytest
from moto import mock_dynamodb
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from src.services.data_plane_service import DataPlaneService
from src.apis import data_plane_api

TABLE_NAME = "test-foundry-workspace"
REGION = "us-east-1"


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


async def _setup():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = REGION
    _create_table()
    svc = DataPlaneService(table_name=TABLE_NAME)
    svc._region = REGION
    await svc.initialize()
    data_plane_api.configure(svc)
    return _make_app()


FDW_BODY = {"name": "test-fdw", "type": "FDW", "connectionConfig": {
    "host": "pg.local", "port": 5432, "database": "db", "user": "u", "password": "p"
}}
CDC_BODY = {"name": "test-cdc", "type": "CDC", "connectionConfig": {
    "bootstrapServers": "kafka:9092", "topicPrefix": "cdc-", "sourceDatabase": "src"
}}


class TestCreateEndpoint:

    @mock_dynamodb
    def test_create_fdw_returns_201(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.post("/api/data-planes", json=FDW_BODY)
                assert r.status_code == 201
                body = r.json()
                assert body["name"] == "test-fdw"
                assert body["type"] == "FDW"
                assert body["status"] == "connected"
                assert "id" in body
        _run(_test())

    @mock_dynamodb
    def test_create_cdc_returns_201_pending(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.post("/api/data-planes", json=CDC_BODY)
                assert r.status_code == 201
                assert r.json()["status"] == "pending"
        _run(_test())

    @mock_dynamodb
    def test_create_fdw_missing_fields_returns_422(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.post("/api/data-planes", json={
                    "name": "bad", "type": "FDW", "connectionConfig": {"host": "x"}
                })
                assert r.status_code == 422
        _run(_test())


class TestListEndpoint:

    @mock_dynamodb
    def test_list_empty(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/api/data-planes")
                assert r.status_code == 200
                assert r.json() == []
        _run(_test())

    @mock_dynamodb
    def test_list_returns_created(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                await c.post("/api/data-planes", json=FDW_BODY)
                await c.post("/api/data-planes", json=CDC_BODY)
                r = await c.get("/api/data-planes")
                assert r.status_code == 200
                assert len(r.json()) == 2
        _run(_test())


class TestGetEndpoint:

    @mock_dynamodb
    def test_get_existing(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                cr = await c.post("/api/data-planes", json=FDW_BODY)
                dp_id = cr.json()["id"]
                r = await c.get(f"/api/data-planes/{dp_id}")
                assert r.status_code == 200
                assert r.json()["id"] == dp_id
        _run(_test())

    @mock_dynamodb
    def test_get_nonexistent_returns_404(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/api/data-planes/no-such-id")
                assert r.status_code == 404
        _run(_test())


class TestUpdateEndpoint:

    @mock_dynamodb
    def test_update_name(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                cr = await c.post("/api/data-planes", json=FDW_BODY)
                dp_id = cr.json()["id"]
                r = await c.put(f"/api/data-planes/{dp_id}", json={"name": "renamed"})
                assert r.status_code == 200
                assert r.json()["name"] == "renamed"
        _run(_test())


class TestDeleteEndpoint:

    @mock_dynamodb
    def test_delete_returns_204(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                cr = await c.post("/api/data-planes", json=CDC_BODY)
                dp_id = cr.json()["id"]
                r = await c.delete(f"/api/data-planes/{dp_id}")
                assert r.status_code == 204
        _run(_test())

    @mock_dynamodb
    def test_delete_nonexistent_returns_404(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.delete("/api/data-planes/no-such-id")
                assert r.status_code == 404
        _run(_test())


class TestExploreEndpoint:

    @mock_dynamodb
    def test_explore_cdc_returns_mock(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                cr = await c.post("/api/data-planes", json=CDC_BODY)
                dp_id = cr.json()["id"]
                r = await c.get(f"/api/data-planes/{dp_id}/explore")
                assert r.status_code == 200
                body = r.json()
                assert body["servers"] == []
                assert body["message"] is not None
        _run(_test())

    @mock_dynamodb
    def test_explore_nonexistent_returns_404(self):
        async def _test():
            app = await _setup()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/api/data-planes/no-such-id/explore")
                assert r.status_code == 404
        _run(_test())
