from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from src.models.mapping_rule_models import MappingRuleSourceType, MappingRuleStatus
from src.services.external_source_vdl_seeder import ensure_external_source_vdl_mappings


class _FakeExternalSim:
    loaded = True

    async def ensure_loaded(self):
        return None

    async def list_foreign_tables(self):
        return [
            SimpleNamespace(schema_name="external_sources", table_name="Market_Signal"),
            SimpleNamespace(schema_name="external_sources", table_name="DF_Forecast_Result"),
        ]

    async def get_table_columns(self, schema, table):
        if table == "Market_Signal":
            return [
                SimpleNamespace(column_name="Signal_ID"),
                SimpleNamespace(column_name="Severity"),
            ]
        return [
            SimpleNamespace(column_name="sku"),
            SimpleNamespace(column_name="forecast_qty"),
        ]


class _FakeMappingService:
    def __init__(self):
        self.rules = []
        self.created = []

    async def list_all(self):
        return list(self.rules)

    async def create(self, req):
        rule = SimpleNamespace(
            id=f"rule-{len(self.rules)}",
            virtual_entity=req.virtual_entity,
            source_table=req.source_table,
            source_schema=req.source_schema,
            status=MappingRuleStatus.draft,
            name=req.name,
            business_logic=req.business_logic,
        )
        self.created.append(req)
        self.rules.append(rule)
        return rule

    async def update(self, rule_id, req):
        for r in self.rules:
            if r.id == rule_id:
                if req.status:
                    r.status = req.status
                if req.business_logic is not None:
                    r.business_logic = req.business_logic
        return self.rules[0]

    async def delete(self, rule_id):
        self.rules = [r for r in self.rules if r.id != rule_id]


def test_external_source_vdl_seeder_creates_raw_and_warehouse_rules():
    svc = _FakeMappingService()
    simulators = {"external": _FakeExternalSim()}
    summary = asyncio.run(
        ensure_external_source_vdl_mappings(svc, simulators, force_recreate=False)
    )
    assert summary["errors"] == 0
    assert summary["created"] >= 2
    entities = {r.virtual_entity for r in svc.created}
    assert "MarketSignal" in entities
    assert "DF_Forecast_Result" in entities
    ms_rule = next(r for r in svc.created if r.virtual_entity == "MarketSignal")
    assert ms_rule.source_table == "Market_Signal"
    assert ms_rule.source_type == MappingRuleSourceType.FDW