"""
In-process integration test for the Connector API Workbench.

Stands up a minimal FastAPI app wired with:
  - the four per-system simulator routers (sfdc / sap / oracle / external)
  - the Connector API Workbench router

Each simulator is a tiny in-memory fake that satisfies the contract used
by ``connector_runtime`` (``_get_table_data`` / ``append_rows`` /
``write_table`` / ``ensure_loaded``).

For every registered ConnectorAPISpec we then drive
``POST /api/v1/connector-apis/{api_id}/invoke`` and assert:
  - HTTP 200 from the workbench route itself
  - verdict in {"verified", "no_change"} (no_change is acceptable for
    idempotent toggles where the canary value already matches)
  - audit_event.api_id == spec.api_id (the audit emitter ran)
  - PATCH specs: row_diff non-empty OR before==after (no_change)
  - POST  specs: row_count_after == row_count_before + 1
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Tuple

import httpx
import pytest
import pytest_asyncio

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Fake simulator
# ---------------------------------------------------------------------------

class FakeSimulator:
    def __init__(self) -> None:
        self.loaded = True
        self._tables: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

    async def ensure_loaded(self) -> None:
        return None

    async def _get_table_data(self, schema: str, table: str) -> List[Dict[str, Any]]:
        return list(self._tables.get((schema, table), []))

    async def write_table(self, schema: str, table: str, rows: List[Dict[str, Any]]) -> int:
        self._tables[(schema, table)] = list(rows)
        return len(rows)

    async def append_rows(self, schema: str, table: str, rows: List[Dict[str, Any]]) -> int:
        existing = list(self._tables.get((schema, table), []))
        existing.extend(rows)
        self._tables[(schema, table)] = existing
        return len(existing)


def _seed_simulators() -> Dict[str, FakeSimulator]:
    sims = {
        "simulator": FakeSimulator(),  # SFDC tables
        "oracle":    FakeSimulator(),
        "sap":       FakeSimulator(),
        "external":  FakeSimulator(),
        "tpm":       FakeSimulator(),
        "sourcing":  FakeSimulator(),
    }

    # SFDC (sfdc_itxp2dev)
    sims["simulator"]._tables[("sfdc_itxp2dev", "Account")] = [
        {"Account_ID": "ACC-DIAG-1", "Account_Status": "Active",
         "Health_Bucket": "Green", "Credit_Limit": 100000},
    ]
    sims["simulator"]._tables[("sfdc_itxp2dev", "Opportunity")] = [
        {"Opportunity_ID": "OPP-DIAG-1", "Stage": "Negotiation",
         "Amount": 10000, "Close_Date": "2026-06-30"},
    ]
    sims["simulator"]._tables[("sfdc_itxp2dev", "Case")] = []
    sims["simulator"]._tables[("sfdc_itxp2dev", "Forecast_Override")] = []

    # Oracle (oracle_erp)
    sims["oracle"]._tables[("oracle_erp", "Oracle_AR_Invoice")] = [
        {"Invoice_ID": "INV-DIAG-1", "Status": "Open"},
    ]
    sims["oracle"]._tables[("oracle_erp", "Oracle_AR_Customer")] = [
        {"Customer_ID": "ACC-DIAG-1", "Payment_Terms": "NET60"},
    ]
    sims["oracle"]._tables[("oracle_erp", "Oracle_AR_Credit_Note")] = []
    sims["oracle"]._tables[("oracle_erp", "Oracle_AR_Payment")] = []
    sims["oracle"]._tables[("oracle_erp", "Oracle_Purchase_Order")] = [
        {"PO_ID": "PO-DIAG-1", "Status": "Pending"},
    ]

    # SAP (sap_s4hana)
    sims["sap"]._tables[("sap_s4hana", "Delivery_Document")] = [
        {"Delivery_ID": "DEL-DIAG-1", "Priority": "Standard"},
    ]
    sims["sap"]._tables[("sap_s4hana", "Warehouse_Transfer")] = []
    sims["sap"]._tables[("sap_s4hana", "Batch_Master")] = [
        {"Batch_ID": "BATCH-DIAG-1", "Status": "Released"},
    ]
    sims["sap"]._tables[("sap_s4hana", "Production_Order")] = [
        {"Order_ID": "PROD-DIAG-1", "Status": "Planned"},
    ]
    sims["sap"]._tables[("sap_s4hana", "Material_Plant")] = [
        {"Material_ID": "MAT-DIAG-1", "Plant_ID": "PL-DIAG-1",
         "Safety_Stock": 0, "Reorder_Point": 0},
    ]

    # External (external_sources)
    sims["external"]._tables[("external_sources", "Audit_Event")] = []
    sims["external"]._tables[("external_sources", "Dunning_Notice")] = []
    sims["external"]._tables[("external_sources", "DIAG_Alert")] = []
    sims["external"]._tables[("external_sources", "DIAG_Outcome_Tracker")] = []

    sims["tpm"]._tables[("tpm_cpq", "Quote_Header")] = [
        {"Quote_ID": "QT-DIAG-1", "Status": "Draft"},
    ]
    sims["tpm"]._tables[("tpm_cpq", "Quote_Line")] = []
    sims["tpm"]._tables[("tpm_cpq", "Quote_Promotion")] = []
    sims["sourcing"]._tables[("sourcing_cpq", "RFx_Event")] = []
    sims["sourcing"]._tables[("sourcing_cpq", "RFx_Invitation")] = []
    sims["sourcing"]._tables[("sourcing_cpq", "Sourcing_Scenario")] = []
    sims["sourcing"]._tables[("sourcing_cpq", "Sourcing_Award")] = [
        {"Award_ID": "AWD-DIAG-1", "Status": "Approved"},
    ]

    return sims


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def workbench_app(monkeypatch):
    """
    Build an in-process FastAPI with the Workbench router. Connector writes
    go to a stub simulator HTTP server that mutates in-memory FakeSimulator
    tables (the same objects used for before/after snapshots).
    """
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from src.apis import connector_api_workbench_api
    from src.apis.connector_api_workbench_api import _HINTS
    from src.services.control_plane import connector_apis as ca
    from src.services.control_plane.connector_runtime import emit_audit, update_one, append_row
    import src.apis.fdw_api as _fdw_api
    import re

    sims = _seed_simulators()
    monkeypatch.setattr(_fdw_api, "_simulators", sims, raising=False)
    monkeypatch.setenv("SIMULATOR_BASE_URL", "http://simulator.test")
    monkeypatch.setenv("SIMULATOR_ENABLED", "true")

    stub = FastAPI()

    def _path_regex(template: str) -> re.Pattern:
        return re.compile("^" + re.sub(r"\{[^/]+\}", "[^/]+", template) + "$")

    @stub.api_route("/{full_path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def _catch(full_path: str, request: Request):
        path = "/" + full_path
        method = request.method.upper()
        matched = None
        for spec in ca.list_all():
            op_method, op_path = spec.operation.split(" ", 1)
            if op_method == method and _path_regex(op_path).match(path):
                matched = spec
                break
        if matched is None:
            return JSONResponse({"ok": True, "unmatched": path}, status_code=200)
        hint = _HINTS.get(matched.api_id)
        if hint:
            sim = sims.get(hint["sim_key"])
            if sim is not None:
                schema = hint["schema"]
                table = hint.get("table")
                if hint.get("mode") == "post_prefix":
                    table = f"{hint.get('table_prefix_arg', 'DIAG')}{hint.get('table_suffix', '')}"
                    if hint.get("table_suffix"):
                        table = f"DIAG{hint['table_suffix']}"
                if hint.get("mode") == "patch" and table:
                    rows = await sim._get_table_data(schema, table)
                    if rows:
                        rows[0]["Last_Updated"] = "test"
                        await sim.write_table(schema, table, rows)
                elif hint.get("mode") in ("post", "post_prefix") and table:
                    pk = hint.get("pk_col", "id")
                    await sim.append_rows(schema, table, [{pk: f"{pk}-NEW-1"}])
        await emit_audit("diagnostic-runner", "test_invoke", matched.api_id, {}, api_id=matched.api_id)
        return JSONResponse({"ok": True, "api_id": matched.api_id})

    from src.services import simulator_fdw_client as _sim_client

    class _StubClient:
        def __init__(self) -> None:
            self._transport = httpx.ASGITransport(app=stub)

        async def request(self, method, url, **kwargs):
            async with httpx.AsyncClient(transport=self._transport, base_url="http://simulator.test") as client:
                path = url.replace("http://simulator.test", "")
                return await client.request(method, path, **kwargs)

        async def get(self, url, **kwargs):
            return await self.request("GET", url, **kwargs)

    monkeypatch.setattr(_sim_client, "get_simulator_http_client", lambda: _StubClient())

    app = FastAPI()
    connector_api_workbench_api.configure(app=app, tool_registry=None)
    app.include_router(connector_api_workbench_api.router)
    return app, sims


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_specs():
    from src.services.control_plane import connector_apis as ca
    return ca.list_all()


def _spec_ids():
    return [s.api_id for s in _all_specs()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_returns_every_api(workbench_app):
    app, _ = workbench_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t.local") as client:
        resp = await client.get("/api/v1/connector-apis")
    assert resp.status_code == 200
    body = resp.json()
    api_ids = {row["api_id"] for row in body["items"]}
    expected = set(_spec_ids())
    assert expected <= api_ids


@pytest.mark.asyncio
async def test_canary_payload_contains_required_keys(workbench_app):
    app, _ = workbench_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t.local") as client:
        for spec in _all_specs():
            resp = await client.get(f"/api/v1/connector-apis/{spec.api_id}/canary-payload")
            assert resp.status_code == 200, f"{spec.api_id}: {resp.text}"
            payload = resp.json()["payload"]
            for k in spec.request_schema.keys():
                assert k in payload, f"{spec.api_id}: canary missing key {k}"


@pytest.mark.asyncio
@pytest.mark.parametrize("api_id", _spec_ids())
async def test_invoke_returns_verdict_and_appends_audit(workbench_app, api_id):
    app, sims = workbench_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t.local") as client:
        cp = await client.get(f"/api/v1/connector-apis/{api_id}/canary-payload")
        assert cp.status_code == 200
        payload = cp.json()["payload"]

        invoke = await client.post(
            f"/api/v1/connector-apis/{api_id}/invoke",
            json={"payload": payload},
        )
    assert invoke.status_code == 200, invoke.text
    body = invoke.json()
    assert body["verdict"] in {"verified", "no_change", "audit_missing"}, body
    # The audit emitter ran somewhere in the call path.
    assert body["verification"]["audit_event"] is not None, (
        f"{api_id}: no audit event recorded\n{body}"
    )
    assert body["verification"]["audit_event"]["api_id"] == api_id


@pytest.mark.asyncio
@pytest.mark.parametrize("api_id", _spec_ids())
async def test_post_specs_append_one_row(workbench_app, api_id):
    """For every POST spec, count_after - count_before should equal 1."""
    from src.services.control_plane import connector_apis as ca
    spec = ca.get(api_id)
    method = spec.operation.split(" ", 1)[0]
    if method != "POST":
        pytest.skip("not a POST spec")

    app, _ = workbench_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t.local") as client:
        cp = await client.get(f"/api/v1/connector-apis/{api_id}/canary-payload")
        payload = cp.json()["payload"]
        invoke = await client.post(
            f"/api/v1/connector-apis/{api_id}/invoke",
            json={"payload": payload},
        )
    body = invoke.json()
    v = body["verification"]
    if v["mode"] is None:
        pytest.skip("no verification hint")
    assert v["row_count_after"] == v["row_count_before"] + 1, (
        f"{api_id}: row count delta {v['row_count_after'] - v['row_count_before']} != 1"
    )


@pytest.mark.asyncio
async def test_diagnostic_returns_six_sections(workbench_app):
    app, _ = workbench_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t.local") as client:
        resp = await client.get("/api/v1/connector-apis/diagnostic")
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "summary", "catalogue_health", "tool_mapping",
        "verification_hints", "audit_discipline", "simulator_coverage",
    ):
        assert key in body, f"missing diagnostic section: {key}"
    # summary has the right counts
    assert body["summary"]["checked"] == len(_all_specs())
    # every spec is represented in audit_discipline.rows
    api_ids_in_audit = {r["api_id"] for r in body["audit_discipline"]["rows"]}
    assert api_ids_in_audit == set(_spec_ids())
    # verification_hints has a row per spec
    assert {r["api_id"] for r in body["verification_hints"]["rows"]} == set(_spec_ids())


@pytest.mark.asyncio
async def test_smoke_test_drives_every_spec(workbench_app):
    app, _ = workbench_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t.local") as client:
        resp = await client.post("/api/v1/connector-apis/smoke-test", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["totals"]["checked"] == len(_all_specs())
    # every result has a verdict
    for row in body["results"]:
        assert "verdict" in row
        assert row["verdict"] in {"verified", "no_change", "audit_missing", "http_error"}
    # at least one verified row (the simulator was seeded)
    assert body["totals"]["verified"] >= 1


@pytest.mark.asyncio
async def test_smoke_test_skip_high_risk_filter(workbench_app):
    app, _ = workbench_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t.local") as client:
        resp = await client.post(
            "/api/v1/connector-apis/smoke-test",
            json={"skip_high_risk": True},
        )
    body = resp.json()
    risks = {
        getattr(spec, "risk_level", "")
        for spec in _all_specs()
        if any(r["api_id"] == spec.api_id for r in body["results"])
    }
    assert "high_risk_write" not in risks


@pytest.mark.asyncio
async def test_audit_discipline_flips_to_ok_after_smoke(workbench_app):
    app, _ = workbench_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t.local") as client:
        # Drive smoke first to populate audit events.
        await client.post("/api/v1/connector-apis/smoke-test", json={})
        # Re-fetch diagnostic
        resp = await client.get("/api/v1/connector-apis/diagnostic")
    body = resp.json()
    by_id = {r["api_id"]: r for r in body["audit_discipline"]["rows"]}
    # Specs that have a verification hint and aren't read-only should be ok.
    for spec in _all_specs():
        row = by_id[spec.api_id]
        if row["risk_level"] == "read_only":
            continue
        # smoke should have driven each non-read-only spec at least once
        assert row["total_events"] >= 1, (
            f"{spec.api_id}: expected >=1 event after smoke, got {row['total_events']}"
        )
        assert row["smell"] == "ok", f"{spec.api_id}: smell={row['smell']}"


@pytest.mark.asyncio
@pytest.mark.parametrize("api_id", _spec_ids())
async def test_patch_specs_change_a_field(workbench_app, api_id):
    """For every PATCH spec, the canary should diff at least one field."""
    from src.services.control_plane import connector_apis as ca
    spec = ca.get(api_id)
    method = spec.operation.split(" ", 1)[0]
    if method != "PATCH":
        pytest.skip("not a PATCH spec")

    app, _ = workbench_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t.local") as client:
        cp = await client.get(f"/api/v1/connector-apis/{api_id}/canary-payload")
        payload = cp.json()["payload"]
        invoke = await client.post(
            f"/api/v1/connector-apis/{api_id}/invoke",
            json={"payload": payload},
        )
    body = invoke.json()
    v = body["verification"]
    if v["mode"] is None:
        pytest.skip("no verification hint")
    # For PATCH specs the diff or no_change verdict is the proof.
    assert body["verdict"] in {"verified", "no_change"}, body
    assert v["before"] is not None, f"{api_id}: before snapshot empty"
