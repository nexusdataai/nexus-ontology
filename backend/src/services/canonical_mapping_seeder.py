"""
Seed active FDW mapping rules for canonical VDL entities (canonical-entities.yaml).

Without these rules, VirtualQueryService returns "No active mapping rule found"
when the Knowledge Graph data preview queries entities like Customer or Invoice.
Idempotent: skips canonicals that already have any mapping rule row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from src.models.mapping_rule_models import (
    FieldMap,
    MappingRuleCreateRequest,
    MappingRuleSourceType,
    MappingRuleStatus,
    MappingRuleUpdateRequest,
)
from src.services.mapping_rule_service import MappingRuleService
from src.services.vdl_catalog_service import get_catalog

seed_logger = logger.bind(component="canonical-mapping-seeder")

DOMAIN_TO_SIM: Dict[str, List[str]] = {
    "Finance - General Ledger": ["oracle"],
    "Finance - Receivables": ["oracle"],
    "Finance - Payables": ["oracle"],
    "Procurement": ["oracle", "sap"],
    "Customer & Sales": ["sfdc", "oracle"],
    "Inventory": ["sap"],
    "Product Master": ["sap", "oracle"],
    "Production & Quality": ["sap"],
    "Logistics": ["sap"],
    "Commercial CPQ": ["tpm"],
    "Strategic Sourcing": ["sourcing"],
    "Document Management": ["external"],
    "External Signals": ["external"],
    "File Capture": ["external"],
    "Order-to-Cash Results": ["external"],
}

SIM_INFO: Dict[str, Dict[str, str]] = {
    "sfdc": {"schema": "sfdc_schema"},
    "oracle": {"schema": "oracle_erp"},
    "sap": {"schema": "sap_s4hana"},
    "external": {"schema": "external_sources"},
    "tpm": {"schema": "tpm_cpq"},
    "sourcing": {"schema": "sourcing_cpq"},
}

# FDW registry key in fdw_api._simulators (sfdc data uses "simulator").
SIM_REGISTRY_KEY: Dict[str, str] = {
    "sfdc": "simulator",
    "oracle": "oracle",
    "sap": "sap",
    "external": "external",
    "tpm": "tpm",
    "sourcing": "sourcing",
}

PREFIX_BY_SIM: Dict[str, str] = {
    "oracle": "Oracle_",
}


@dataclass
class Match:
    sim_key: str
    sim_schema: str
    sim_table: str
    via_alias: str


def _candidate_names(canonical: Dict[str, Any]) -> List[str]:
    """Prefer alias / physical table names before the canonical label."""
    aliases = [a for a in (canonical.get("aliases") or []) if a]
    name = (canonical.get("name") or "").strip()
    out = list(aliases)
    if name and name not in out:
        out.append(name)
    return out


def resolve_match(
    canonical: Dict[str, Any],
    sim_tables: Dict[str, Dict[str, Set[str]]],
) -> Optional[Match]:
    domain = (canonical.get("domain") or "").strip()
    sim_keys = DOMAIN_TO_SIM.get(domain, [])
    if not sim_keys:
        sim_keys = list(SIM_INFO.keys())

    candidates = _candidate_names(canonical)

    for sim_key in sim_keys:
        info = SIM_INFO.get(sim_key)
        if not info:
            continue
        schema = info["schema"]
        tables = sim_tables.get(sim_key, {}).get(schema) or set()
        if not tables:
            continue
        prefix = PREFIX_BY_SIM.get(sim_key, "")
        for cand in candidates:
            if cand in tables:
                return Match(sim_key, schema, cand, via_alias=cand)
            if prefix and f"{prefix}{cand}" in tables:
                return Match(sim_key, schema, f"{prefix}{cand}", via_alias=cand)
    return None


async def _collect_simulator_tables(simulators: Dict[str, Any]) -> Dict[str, Dict[str, Set[str]]]:
    out: Dict[str, Dict[str, Set[str]]] = {}
    for sim_key, info in SIM_INFO.items():
        registry_key = SIM_REGISTRY_KEY.get(sim_key, sim_key)
        sim = simulators.get(registry_key)
        schema = info["schema"]
        by_schema: Dict[str, Set[str]] = {schema: set()}
        if sim is None:
            out[sim_key] = by_schema
            continue
        try:
            if hasattr(sim, "ensure_loaded"):
                await sim.ensure_loaded()
            if not getattr(sim, "loaded", True):
                seed_logger.warning("Simulator not loaded for canonical seed", sim_key=sim_key)
                out[sim_key] = by_schema
                continue
            if hasattr(sim, "list_foreign_tables"):
                tables = await sim.list_foreign_tables()
                for t in tables:
                    sch = getattr(t, "schema_name", None) or getattr(t, "schemaName", "")
                    tn = getattr(t, "table_name", None) or getattr(t, "tableName", "")
                    if sch and tn:
                        by_schema.setdefault(sch, set()).add(tn)
        except Exception as exc:
            seed_logger.warning(
                "Failed to list simulator tables for canonical seed",
                sim_key=sim_key,
                error=str(exc),
            )
        out[sim_key] = by_schema
    return out


async def ensure_canonical_mapping_rules(
    mapping_service: MappingRuleService,
    simulators: Optional[Dict[str, Any]] = None,
    *,
    force_recreate: bool = False,
) -> Dict[str, Any]:
    """
    Create and activate FDW mapping rules for canonical entities missing rules.
    """
    simulators = simulators or {}
    canonicals = get_catalog().list_entities()
    existing_rules = await mapping_service.list_all()
    existing_by_ve: Dict[str, Any] = {}
    for rule in existing_rules:
        existing_by_ve[rule.virtual_entity] = rule

    sim_tables = await _collect_simulator_tables(simulators)

    created = 0
    skipped = 0
    no_source = 0
    errors = 0
    detail: List[Dict[str, Any]] = []

    for canon in canonicals:
        name = canon.get("name") or ""
        if not name:
            continue

        match = resolve_match(canon, sim_tables)

        existing = existing_by_ve.get(name)
        if existing and not force_recreate:
            if (
                match
                and existing.name.startswith("Canonical:")
                and (
                    existing.source_table != match.sim_table
                    or existing.source_schema != match.sim_schema
                )
            ):
                try:
                    await mapping_service.delete(existing.id)
                    seed_logger.info(
                        "Replaced canonical mapping rule with better table match",
                        entity=name,
                        old_table=f"{existing.source_schema}.{existing.source_table}",
                        new_table=f"{match.sim_schema}.{match.sim_table}",
                    )
                except Exception as exc:
                    seed_logger.warning(
                        "Failed to replace canonical mapping rule",
                        entity=name,
                        error=str(exc),
                    )
                    errors += 1
                    continue
            else:
                skipped += 1
                continue

        if match is None:
            no_source += 1
            detail.append(
                {
                    "entity": name,
                    "status": "no_source_table",
                    "domain": canon.get("domain"),
                }
            )
            continue

        fields = canon.get("fields") or []
        field_maps = [
            FieldMap(source_field=f["name"], target_field=f["name"])
            for f in fields
            if f.get("name")
        ]

        try:
            rule = await mapping_service.create(
                MappingRuleCreateRequest(
                    name=f"Canonical: {name}",
                    virtual_entity=name,
                    source_type=MappingRuleSourceType.FDW,
                    source_system=match.sim_key,
                    source_schema=match.sim_schema,
                    source_table=match.sim_table,
                    field_maps=field_maps,
                )
            )
            await mapping_service.update(
                rule.id,
                MappingRuleUpdateRequest(status=MappingRuleStatus.active),
            )
            created += 1
            detail.append(
                {
                    "entity": name,
                    "status": "created",
                    "table": f"{match.sim_schema}.{match.sim_table}",
                    "via": match.via_alias,
                }
            )
        except Exception as exc:
            errors += 1
            seed_logger.warning("Canonical mapping rule create failed", entity=name, error=str(exc))
            detail.append({"entity": name, "status": "error", "reason": str(exc)})

    summary = {
        "created": created,
        "skipped": skipped,
        "no_source_table": no_source,
        "errors": errors,
        "detail": detail[:30],
    }
    seed_logger.info(
        "Canonical mapping rules ensured: created={} skipped={} no_source={} errors={}",
        created,
        skipped,
        no_source,
        errors,
    )
    return summary
