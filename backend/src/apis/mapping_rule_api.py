from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from src.models.mapping_rule_models import (
    AutoMapDetail,
    AutoMapResponse,
    FieldMap,
    MappingRuleCreateRequest,
    MappingRuleResponse,
    MappingRuleSourceType,
    MappingRuleStatus,
    MappingRuleUpdateRequest,
    MappingSuggestionRequest,
)
from src.services.mapping_rule_service import (
    MappingRuleNotFoundError,
    MappingRuleStorageError,
    MappingRuleValidationError,
)

mr_logger = logger.bind(component="mapping-rules")

router = APIRouter(prefix="/api/v1/mapping-rules", tags=["mapping-rules"])

_service = None


def configure(service):
    global _service
    _service = service


def _check_service():
    if _service is None:
        raise HTTPException(status_code=503, detail={"error": "Mapping Rule service not initialized"})


@router.post("", response_model=MappingRuleResponse, status_code=201)
async def create_mapping_rule(request: MappingRuleCreateRequest):
    _check_service()
    try:
        return await _service.create(request)
    except MappingRuleValidationError as e:
        raise HTTPException(status_code=422, detail={"error": "Validation error", "detail": str(e)})
    except MappingRuleStorageError as e:
        mr_logger.error("Create failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.get("", response_model=List[MappingRuleResponse])
async def list_mapping_rules(virtual_entity: Optional[str] = None, source_type: Optional[str] = None):
    _check_service()
    try:
        return await _service.list_all(virtual_entity=virtual_entity, source_type=source_type)
    except MappingRuleStorageError as e:
        mr_logger.error("List failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.get("/audit")
async def audit_mapping_rules():
    """Audit all schema entities vs mapping rules vs simulator data."""
    _check_service()

    all_entities = []
    for path in _find_schema_yamls():
        all_entities.extend(_parse_entities_from_schema(path))

    seen = set()
    unique_entities = []
    for ent in all_entities:
        name = ent["fdw_table"]
        if name and name not in seen:
            seen.add(name)
            unique_entities.append(ent)

    rules = await _service.list_all()
    rule_by_entity: Dict[str, Any] = {}
    for r in rules:
        if r.virtual_entity not in rule_by_entity:
            rule_by_entity[r.virtual_entity] = r

    source_tables = await _discover_all_source_tables()

    row_counts: Dict[str, int] = {}
    try:
        from src.apis.fdw_api import _simulators
        for _sim_name, sim in _simulators.items():
            if not sim:
                continue
            try:
                tables = await sim.list_foreign_tables()
                for tbl in tables:
                    tname = getattr(tbl, "table_name", None) or getattr(tbl, "tableName", "")
                    if tname:
                        row_counts[tname] = getattr(tbl, "row_count", 0) or 0
            except Exception:
                pass
    except Exception:
        pass

    entities_out = []
    mapped_count = 0
    unmapped_count = 0
    with_data = 0
    without_data = 0
    summary_by_system: Dict[str, Dict[str, int]] = {}

    for ent in unique_entities:
        name = ent["fdw_table"]
        system = ent["system"]
        schema_fields = ent["fields"]
        rule = rule_by_entity.get(name)
        source = source_tables.get(name.lower())

        issues = []
        if rule:
            mapping_status = "mapped"
            mapped_count += 1
            rule_name = rule.name
            rule_id_val = rule.id
            source_schema = rule.source_schema
            source_table = rule.source_table
            source_type = source["source"] if source else f"rule:{rule.source_type.value}"

            total_fm = len(rule.field_maps)
            matched_fm = sum(1 for fm in rule.field_maps if fm.source_field)
            unmatched_fm = total_fm - matched_fm
            if unmatched_fm > 0:
                issues.append(f"{unmatched_fm} fields have no source column match")

            # Prefer looking up rows by the rule's source_table, then fall
            # back to the schema entity name. Some simulators (Oracle) emit
            # table names prefixed with the system (``Oracle_AP_Invoice``)
            # while the canonical schema uses the un-prefixed form
            # (``AP_Invoice``); the mapping rule captures the correct
            # physical name and is the authoritative link between them.
            rc = row_counts.get(rule.source_table, 0) if rule.source_table else 0
            if rc == 0:
                rc = row_counts.get(name, 0)
            if rc > 0:
                data_status = "has_data"
                with_data += 1
            else:
                data_status = "no_data"
                without_data += 1
                issues.append("Row count is 0")
        else:
            mapping_status = "unmapped"
            unmapped_count += 1
            rule_name = None
            rule_id_val = None
            source_schema = None
            source_table = None
            source_type = None
            matched_fm = 0
            unmatched_fm = len(schema_fields)
            issues.append("No mapping rule found")

            rc = row_counts.get(name, 0)
            if source:
                if rc > 0:
                    data_status = "has_data"
                    with_data += 1
                else:
                    data_status = "no_data"
                    without_data += 1
                    issues.append("Source table found but has 0 rows")
            else:
                data_status = "no_source"
                without_data += 1
                issues.append("No source table in any simulator")

        if system not in summary_by_system:
            summary_by_system[system] = {"mapped": 0, "unmapped": 0, "rows": 0}
        if mapping_status == "mapped":
            summary_by_system[system]["mapped"] += 1
        else:
            summary_by_system[system]["unmapped"] += 1
        summary_by_system[system]["rows"] += rc

        entities_out.append({
            "entity": name, "system": system, "domain": ent.get("domain", ""),
            "schemaFields": len(schema_fields), "mappingStatus": mapping_status,
            "ruleName": rule_name, "ruleId": rule_id_val,
            "sourceSchema": source_schema, "sourceTable": source_table, "sourceType": source_type,
            "mappedFields": matched_fm, "unmappedFields": unmatched_fm,
            "rowCount": rc, "dataStatus": data_status, "issues": issues,
        })

    return {
        "totalEntities": len(unique_entities), "mapped": mapped_count, "unmapped": unmapped_count,
        "withData": with_data, "withoutData": without_data,
        "entities": entities_out, "summaryBySystem": summary_by_system,
    }


@router.get("/{rule_id}", response_model=MappingRuleResponse)
async def get_mapping_rule(rule_id: str):
    _check_service()
    try:
        return await _service.get(rule_id)
    except MappingRuleNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "Mapping rule not found", "detail": rule_id})
    except MappingRuleStorageError as e:
        mr_logger.error("Get failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.put("/{rule_id}", response_model=MappingRuleResponse)
async def update_mapping_rule(rule_id: str, request: MappingRuleUpdateRequest):
    _check_service()
    try:
        return await _service.update(rule_id, request)
    except MappingRuleNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "Mapping rule not found", "detail": rule_id})
    except MappingRuleValidationError as e:
        raise HTTPException(status_code=422, detail={"error": "Validation error", "detail": str(e)})
    except MappingRuleStorageError as e:
        mr_logger.error("Update failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.delete("/{rule_id}", status_code=204)
async def delete_mapping_rule(rule_id: str):
    _check_service()
    try:
        await _service.delete(rule_id)
    except MappingRuleNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "Mapping rule not found", "detail": rule_id})
    except MappingRuleStorageError as e:
        mr_logger.error("Delete failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.post("/{rule_id}/validate")
async def validate_mapping_rule(rule_id: str):
    _check_service()
    try:
        return await _service.validate(rule_id)
    except MappingRuleNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "Mapping rule not found", "detail": rule_id})
    except MappingRuleValidationError as e:
        raise HTTPException(status_code=422, detail={"error": "Validation error", "detail": str(e)})
    except MappingRuleStorageError as e:
        mr_logger.error("Validate failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.post("/suggest")
async def suggest_mappings(request: MappingSuggestionRequest):
    _check_service()
    try:
        return await _service.suggest(request)
    except MappingRuleValidationError as e:
        raise HTTPException(status_code=422, detail={"error": "Validation error", "detail": str(e)})
    except MappingRuleStorageError as e:
        mr_logger.error("Suggest failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


SYSTEM_SCHEMA_MAP: Dict[str, str] = {
    "Salesforce": "sfdc_itxp2dev",
    "SAP": "sap_s4hana",
    "Oracle": "oracle_erp",
    "Google_Drive": "external_sources",
    "Social_Listening": "external_sources",
    "File_Uploads": "external_sources",
    "TPM_Simulator": "tpm_cpq",
    "Sourcing_Simulator": "sourcing_cpq",
}


def _find_schema_yamls() -> List[Path]:
    base = Path(__file__).resolve().parent.parent.parent / "enterprise-knowledge"
    return sorted(base.glob("*schema*.yaml")) if base.exists() else []


def _parse_entities_from_schema(path: Path) -> List[Dict[str, Any]]:
    with open(path) as f:
        schema = yaml.safe_load(f)
    entities = []
    for domain in schema.get("domains", []):
        system = domain.get("system", "Unknown")
        domain_name = domain.get("name", "")
        for table in domain.get("tables", []):
            fields = table.get("key_fields", [])
            entities.append({
                "fdw_table": table.get("fdw_table", ""),
                "physical_source_table": table.get("physical_source_table", ""),
                "system": system,
                "domain": domain_name,
                "virtual": table.get("virtual", False),
                "source": table.get("source", ""),
                "glue_table": table.get("glue_table", ""),
                "glue_database": table.get("glue_database", ""),
                "fields": [f.get("name", "") for f in fields if f.get("name")],
            })
    return entities


# Reuse the rewrite map from the FDW discovery service so that auto-mapped
# mapping rules carry the canonical schema name even when the upstream
# Postgres still exposes a legacy capability-prefixed schema. The raw name
# is supplied by the deployment via the LEGACY_FDW_SCHEMA env var.
from src.services.fdw_discovery_service import canonical_schema as _canonicalise_schema  # noqa: E402


# Virtual entities the auto-mapper must never (re-)create.
#
# Historically this set held ``ContentDocumentLink``, ``ContentVersion``,
# and ``cspmb__Price_Item__c`` because those SFDC custom objects survived
# in the BSS-Magic image as orphan foreign tables with no simulator
# producer. In the current product all three ARE emitted by simulators
# (external -> ContentDocumentLink / ContentVersion; sap -> Price_Item)
# and are declared in ``supply-chain-schema.yaml``, so keeping them in the
# blocklist caused ``/mapping-rules/audit`` to report them as permanent
# ``unmapped`` issues. The blocklist is now empty; add entries here only
# if a schema entity has genuinely no producer and no consumer.
AUTO_MAP_BLOCKLIST: set = set()


async def _discover_all_source_tables() -> Dict[str, Dict[str, Any]]:
    """Discover all tables from FDW + simulators. Returns {lower_name: {schema, table, source, columns}}."""
    tables: Dict[str, Dict[str, Any]] = {}

    try:
        from src.apis.fdw_api import _discovery_service, _simulators

        if _discovery_service:
            try:
                fdw_tables = await _discovery_service.list_foreign_tables()
                for t in fdw_tables:
                    name = t.table_name
                    raw_schema = t.schema_name if hasattr(t, "schema_name") else "public"
                    schema = _canonicalise_schema(raw_schema)
                    cols = []
                    try:
                        col_list = await _discovery_service.get_table_columns(raw_schema, name)
                        cols = [c.column_name for c in col_list]
                    except Exception:
                        pass
                    tables[name.lower()] = {"schema": schema, "table": name, "source": "fdw", "columns": cols}
                mr_logger.info(f"Auto-map: discovered {len(fdw_tables)} FDW tables")
            except Exception as e:
                mr_logger.warning(f"Auto-map: FDW discovery failed: {e}")

        sim_label = {
            "simulator": "Salesforce", "oracle": "Oracle", "sap": "SAP", "external": "External",
            "tpm": "TPM_Simulator", "sourcing": "Sourcing_Simulator",
        }
        for sim_name, sim in _simulators.items():
            if not sim:
                continue
            try:
                await sim.ensure_loaded()
                sim_tables = await sim.list_foreign_tables()
                for t in sim_tables:
                    name = t.table_name if hasattr(t, "table_name") else str(t)
                    schema = t.schema_name if hasattr(t, "schema_name") else sim_name
                    cols = []
                    try:
                        col_list = await sim.get_table_columns(schema, name)
                        cols = [c.column_name for c in col_list]
                    except Exception:
                        pass
                    key = name.lower()
                    if key not in tables:
                        tables[key] = {"schema": schema, "table": name, "source": f"simulator:{sim_label.get(sim_name, sim_name)}", "columns": cols}
                mr_logger.info(f"Auto-map: discovered {len(sim_tables)} tables from {sim_name} simulator")
            except Exception as e:
                mr_logger.warning(f"Auto-map: {sim_name} simulator discovery failed: {e}")
    except Exception as e:
        mr_logger.warning(f"Auto-map: source discovery failed: {e}")

    return tables


def _match_fields(schema_fields: List[str], source_columns: List[str]) -> List[FieldMap]:
    """Match schema key_fields to source table columns by normalized name.
    
    Also maps all source columns that aren't matched by schema fields
    as identity mappings, so all data flows through VDL.
    """
    col_map = {c.lower().replace("-", "_"): c for c in source_columns}
    field_maps = []
    used_cols = set()
    for field_name in schema_fields:
        normalized = field_name.lower().replace("-", "_")
        matched_col = col_map.get(normalized, "")
        if matched_col:
            used_cols.add(matched_col)
        field_maps.append(FieldMap(source_field=matched_col or field_name, target_field=field_name))

    for col in source_columns:
        if col not in used_cols:
            field_maps.append(FieldMap(source_field=col, target_field=col))

    return field_maps


FALLBACK_SYSTEMS: Dict[str, str] = {
    "Google_Drive": "external_sources",
    "Social_Listening": "external_sources",
    "File_Uploads": "external_sources",
}


@router.delete("/auto-map")
async def delete_auto_mapped_rules():
    """Delete all auto-generated mapping rules (name starts with 'Auto: ')."""
    _check_service()
    existing = await _service.list_all()
    deleted = 0
    for rule in existing:
        if rule.name.startswith("Auto: "):
            try:
                await _service.delete(rule.id)
                deleted += 1
            except Exception as e:
                mr_logger.warning(f"Failed to delete auto rule {rule.id}: {e}")
    mr_logger.info(f"Deleted {deleted} auto-mapped rules")
    return {"deleted": deleted}


@router.post("/auto-map", response_model=AutoMapResponse)
async def auto_map_from_schema(force: bool = Query(default=True)):
    """Bulk-create mapping rules for all entities in the supply chain schema.

    Discovers actual FDW + simulator tables, matches them to schema entities
    by name, resolves field mappings by matching column names to key_fields,
    and creates active mapping rules.

    When force=true (default), deletes all existing 'Auto:' rules first so
    mappings are re-created fresh from the current state of FDW + simulators.
    """
    _check_service()

    if force:
        existing = await _service.list_all()
        deleted = 0
        for rule in existing:
            if rule.name.startswith("Auto: "):
                try:
                    await _service.delete(rule.id)
                    deleted += 1
                except Exception:
                    pass
        if deleted:
            mr_logger.info(f"Auto-map force mode: deleted {deleted} existing auto rules")

    schema_files = _find_schema_yamls()
    if not schema_files:
        raise HTTPException(status_code=404, detail={"error": "No schema YAML files found in enterprise-knowledge/"})

    all_entities: List[Dict[str, Any]] = []
    for sf in schema_files:
        try:
            all_entities.extend(_parse_entities_from_schema(sf))
        except Exception as e:
            mr_logger.warning(f"Failed to parse {sf.name}: {e}")

    if not all_entities:
        raise HTTPException(status_code=404, detail={"error": "No entities found in schema files"})

    seen_entities: set = set()
    unique_entities: List[Dict[str, Any]] = []
    for ent in all_entities:
        name = ent.get("fdw_table", "")
        if name and name not in seen_entities:
            seen_entities.add(name)
            unique_entities.append(ent)

    source_tables = await _discover_all_source_tables()
    mr_logger.info(f"Auto-map: {len(source_tables)} source tables discovered, {len(unique_entities)} unique schema entities to map")

    existing_rules = await _service.list_all()
    active_entities = set()
    draft_rules = {}
    for r in existing_rules:
        ve = r.virtual_entity
        status_val = r.status.value if hasattr(r.status, "value") else str(r.status)
        if status_val == "active":
            active_entities.add(ve)
        elif status_val in ("draft", "inactive") and not r.name.startswith("Auto: "):
            draft_rules[ve] = r

    if force and draft_rules:
        for ve, rule in draft_rules.items():
            try:
                await _service.delete(rule.id)
                mr_logger.info(f"Auto-map: deleted draft/inactive rule '{rule.name}' for {ve}")
            except Exception:
                pass

    existing_entities = {r.virtual_entity for r in await _service.list_all()}

    result = AutoMapResponse()

    for ent in unique_entities:
        entity_name = ent["fdw_table"]

        if entity_name in AUTO_MAP_BLOCKLIST:
            result.skipped += 1
            result.details.append(AutoMapDetail(
                entity=entity_name, status="skipped",
                reason="Entity is in AUTO_MAP_BLOCKLIST (legacy / unsupported)",
            ))
            continue

        if entity_name in existing_entities:
            result.skipped += 1
            result.details.append(AutoMapDetail(entity=entity_name, status="skipped", reason="Active rule already exists"))
            continue

        system = ent["system"]
        entity_source = ent.get("source", "")
        glue_table = ent.get("glue_table", "")

        if entity_source == "athena" and glue_table:
            schema_fields = ent.get("fields", [])
            field_maps = [FieldMap(source_field=f, target_field=f) for f in schema_fields] if schema_fields else []
            try:
                req = MappingRuleCreateRequest(
                    name=f"Auto: {entity_name}",
                    virtual_entity=entity_name,
                    source_type=MappingRuleSourceType.FDW,
                    source_system=system,
                    source_table=entity_name,
                    source_schema="external_sources",
                    field_maps=field_maps,
                )
                created_rule = await _service.create(req)
                activate_req = MappingRuleUpdateRequest(status=MappingRuleStatus.active)
                await _service.update(created_rule.id, activate_req)
                existing_entities.add(entity_name)
                result.created += 1
                result.details.append(AutoMapDetail(
                    entity=entity_name, status="created",
                    reason=f"Result object mapped to external simulator ({len(field_maps)} fields, Athena table: {glue_table})",
                ))
            except Exception as e:
                mr_logger.warning(f"Auto-map Athena failed for {entity_name}: {e}")
                result.errors += 1
                result.details.append(AutoMapDetail(entity=entity_name, status="error", reason=str(e)))
            continue

        physical_table = ent.get("physical_source_table") or entity_name
        source = source_tables.get(physical_table.lower())

        if not source and system in FALLBACK_SYSTEMS:
            fallback_schema = FALLBACK_SYSTEMS[system]
            source = {
                "schema": fallback_schema,
                "table": physical_table,
                "source": f"fallback:{system}",
                "columns": [],
            }
            mr_logger.info(f"Auto-map: using fallback for {entity_name} ({system} -> {fallback_schema}, physical={physical_table})")

        if not source:
            result.skipped += 1
            result.details.append(AutoMapDetail(
                entity=entity_name, status="skipped",
                reason=f"No matching source table in FDW or simulators (system: {system})",
            ))
            continue

        source_schema = source["schema"]
        source_table = source["table"]
        source_columns = source.get("columns", [])
        source_origin = source.get("source", "unknown")

        schema_fields = ent.get("fields", [])
        if schema_fields and source_columns:
            field_maps = _match_fields(schema_fields, source_columns)
        elif source_columns:
            field_maps = [FieldMap(source_field=c, target_field=c) for c in source_columns]
        elif schema_fields:
            field_maps = [FieldMap(source_field=f, target_field=f) for f in schema_fields]
        else:
            field_maps = [FieldMap(source_field=entity_name, target_field=entity_name)]

        try:
            req = MappingRuleCreateRequest(
                name=f"Auto: {entity_name}",
                virtual_entity=entity_name,
                source_type=MappingRuleSourceType.FDW,
                source_system=system,
                source_table=source_table,
                source_schema=source_schema,
                field_maps=field_maps,
            )
            created_rule = await _service.create(req)
            activate_req = MappingRuleUpdateRequest(status=MappingRuleStatus.active)
            await _service.update(created_rule.id, activate_req)
            existing_entities.add(entity_name)
            result.created += 1
            result.details.append(AutoMapDetail(
                entity=entity_name, status="created",
                reason=f"Mapped to {source_schema}.{source_table} ({source_origin}, {len(field_maps)} fields)",
            ))
        except Exception as e:
            mr_logger.warning(f"Auto-map failed for {entity_name}: {e}")
            result.errors += 1
            result.details.append(AutoMapDetail(entity=entity_name, status="error", reason=str(e)))

    mr_logger.info(f"Auto-map complete: {result.created} created, {result.skipped} skipped, {result.errors} errors")
    return result
