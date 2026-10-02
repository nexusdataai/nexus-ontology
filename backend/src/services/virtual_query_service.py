"""
Virtual Query Service

Core query propagation engine that translates queries against virtual entities
into FDW queries using mapping rules. Supports graceful degradation when
FDW services are unavailable.
"""

import json
import time
from typing import Any, Dict, List, Optional

from loguru import logger

from src.models.fdw_models import FilterOperator, QueryFilter, QueryRequest
from src.models.mapping_rule_models import (
    VirtualFilter,
    VirtualQueryRequest,
    VirtualQueryResponse,
)

vq_logger = logger.bind(component="virtual-query")

SCHEMA_TO_SIMULATOR: Dict[str, str] = {
    "oracle_erp": "oracle",
    "sap_s4hana": "sap",
    "sfdc_itxp2dev": "simulator",
    "external_sources": "external",
    "tpm_cpq": "tpm",
    "sourcing_cpq": "sourcing",
}

# In-process alias shim retained ONLY for the Oracle_* legacy names introduced
# by scripts/migrations/rename_oracle_virtual_entities.py. The general
# legacy->canonical alias resolution now flows through VdlCatalogService
# (resolve_alias). The Oracle_* names are not in the canonical YAML's
# aliases list (they were a previous-generation back-compat layer pointing
# at AR_Customer / AR_Invoice / ... which are themselves now legacy aliases
# for the canonical Customer / Invoice / ...).
_LEGACY_VIRTUAL_ENTITY_ALIASES: Dict[str, str] = {
    "Oracle_AR_Customer":     "AR_Customer",
    "Oracle_AR_Invoice":      "AR_Invoice",
    "Oracle_AR_Payment":      "AR_Payment",
    "Oracle_AR_Credit_Note":  "AR_Credit_Note",
    "Oracle_GL_Journal":      "GL_Journal",
    "Oracle_GL_Period":       "GL_Period",
    "Oracle_AP_Invoice":      "AP_Invoice",
    "Oracle_AP_Payment":      "AP_Payment",
    "Oracle_Purchase_Order":  "Purchase_Order",
    "Oracle_Cost_Accounting": "Cost_Accounting",
    "Oracle_Fixed_Asset":     "Fixed_Asset",
    "Oracle_Budget":          "Budget",
    "Oracle_Product_Master":  "Product_Master",
}


def _parse_business_logic(rule_business_logic: Optional[str]) -> Dict[str, Any]:
    """
    Mimir mapping rules carry the metric name in `source_table` and a JSON
    blob in `business_logic` with optional keys:

      {
        "label_map": { "<row_column>": "<prom_label>", ... },
        "default_aggregation": "avg" | "sum" | "max" | "min",
        "default_step_seconds": 3600,
        "default_lookback_seconds": 604800,
        "tenant_resolver": "fixed:nexus-default" | "request"
      }

    Returns an empty dict if no JSON is present.
    """
    if not rule_business_logic:
        return {}
    try:
        return json.loads(rule_business_logic)
    except Exception:
        return {}


class VirtualQueryService:

    def __init__(self, mapping_service, fdw_query_service=None, fdw_discovery_service=None, simulators: Optional[Dict[str, object]] = None, athena_service=None, mimir_client=None, mode_service=None, catalog=None):
        self._mapping_service = mapping_service
        self._fdw_query_service = fdw_query_service
        self._fdw_discovery_service = fdw_discovery_service
        self._simulators = simulators or {}
        self._athena_service = athena_service
        self._mimir_client = mimir_client
        # Phase 2: explicit per-source routing. When set, replaces the
        # legacy "if simulator and loaded" heuristic in query_virtual_entity.
        self._mode_service = mode_service
        # VDL catalog service for legacy->canonical alias resolution. Falls back
        # to the module-level _LEGACY_VIRTUAL_ENTITY_ALIASES dict (Oracle_* names)
        # when the catalog has no entry, so the Oracle rename shim still works.
        if catalog is None:
            try:
                from src.services.vdl_catalog_service import get_catalog
                catalog = get_catalog()
            except Exception as e:
                vq_logger.warning(f"VDL catalog unavailable; alias resolution limited to legacy shim: {e}")
                catalog = None
        self._catalog = catalog

    def _resolve_canonical_entity(self, name: str) -> str:
        """Resolve a legacy entity name to its canonical form. Returns the
        name unchanged when it's already canonical or unknown to both sources."""
        if self._catalog is not None:
            try:
                canonical = self._catalog.resolve_alias(name)
            except Exception as e:
                vq_logger.debug(f"catalog.resolve_alias({name}) raised: {e}")
                canonical = None
            if canonical:
                return canonical
        return _LEGACY_VIRTUAL_ENTITY_ALIASES.get(name, name)

    async def query_virtual_entity(self, request: VirtualQueryRequest) -> VirtualQueryResponse:
        # Step 1: catalog-driven alias resolution. Legacy entity names
        # (Account, AR_Customer, Material_Master, ...) get rewritten to their
        # canonical form (Customer, Product, ...) before any mapping-rule
        # lookup.
        original_name = request.virtual_entity
        canonical = self._resolve_canonical_entity(original_name)
        if canonical != original_name:
            vq_logger.info(
                "Resolved legacy entity alias to canonical name",
                legacy=original_name,
                canonical=canonical,
            )
            request.virtual_entity = canonical

        rules = await self._mapping_service.list_all(virtual_entity=request.virtual_entity)
        active_rules = [r for r in rules if r.status.value == "active"]

        if not active_rules:
            raise ValueError(
                f"No active mapping rule found for virtual entity: {request.virtual_entity}"
                + (f" (resolved from alias {original_name})" if canonical != original_name else "")
            )

        if len(active_rules) > 1:
            # Each cluster's DDB should contain exactly one active rule per
            # entity. More than one indicates a misconfiguration to clean up
            # via the Mapping Editor UI; we still serve the query using the
            # first rule to avoid hard-failing in production.
            vq_logger.warning(
                "Multiple active mapping rules for the same virtual entity; "
                "expected exactly one per cluster. Using the first.",
                virtual_entity=request.virtual_entity,
                count=len(active_rules),
                rule_ids=[r.id for r in active_rules],
            )

        rule = active_rules[0]

        field_map = {fm.target_field: fm.source_field for fm in rule.field_maps if fm.source_field}
        reverse_map = {v: k for k, v in field_map.items()}

        if request.fields:
            source_columns = [field_map.get(f, f) for f in request.fields]
        else:
            source_columns = None

        translated_filters: Optional[List[QueryFilter]] = None
        if request.filters:
            translated_filters = []
            for vf in request.filters:
                source_col = field_map.get(vf.field, vf.field)
                translated_filters.append(
                    QueryFilter(
                        column=source_col,
                        operator=FilterOperator(vf.operator),
                        value=vf.value,
                    )
                )

        if rule.source_type.value == "FDW":
            query_kwargs = {
                "table": rule.source_table,
                "schema_name": rule.source_schema,
                "filters": translated_filters,
                "limit": request.limit,
                "offset": request.offset,
            }
            if source_columns:
                query_kwargs["columns"] = source_columns
            query_request = QueryRequest(**query_kwargs)

            sim_key = SCHEMA_TO_SIMULATOR.get(rule.source_schema)
            sim = self._simulators.get(sim_key) if sim_key else None

            # Phase 2: explicit per-source mode. When the resolver says
            # "simulator", require the simulator and never silently fall
            # back to real. When it says "real", go straight to FDW.
            mode = "simulator"
            if self._mode_service is not None:
                source = self._mode_service.schema_to_source(rule.source_schema)
                mode = self._mode_service.effective_mode(source) if source else "real"
            elif not (sim and sim_key):
                # Legacy fallback (no resolver wired): preserve old
                # heuristic - prefer simulator if loaded, else FDW.
                mode = "real"

            if mode == "simulator":
                if sim is None:
                    raise ValueError(
                        f"simulator for schema '{rule.source_schema}' not configured (mode=simulator)"
                    )
                if hasattr(sim, "ensure_loaded"):
                    await sim.ensure_loaded()
                if not getattr(sim, "loaded", False):
                    raise ValueError(
                        f"simulator for schema '{rule.source_schema}' is not loaded; "
                        "real mode is disabled - load the simulator or flip to real"
                    )
                vq_logger.info(
                    "Executing simulator query for virtual entity",
                    virtual_entity=request.virtual_entity,
                    source_table=rule.source_table,
                    simulator=sim_key,
                )
                response = await sim.execute_query(query_request)
                source_type_label = "simulator"
            else:
                if self._fdw_query_service is None:
                    # Last-chance fallback: if a simulator is available and
                    # loaded, prefer it over erroring out. This keeps
                    # legacy callers happy in mixed environments.
                    if sim and getattr(sim, "loaded", False):
                        response = await sim.execute_query(query_request)
                        source_type_label = "simulator"
                    else:
                        raise ValueError(
                            f"FDW query service unavailable and no simulator for {rule.source_schema}"
                        )
                else:
                    vq_logger.info(
                        "Executing FDW query for virtual entity",
                        virtual_entity=request.virtual_entity,
                        source_table=rule.source_table,
                    )
                    response = await self._fdw_query_service.execute_query(query_request)
                    source_type_label = "fdw"

            reversed_rows = []
            for row in response.rows:
                reversed_rows.append(
                    {reverse_map.get(k, k): v for k, v in row.items()}
                )

            # Bridge per-call log entry: surfaces virtual-query rows
            # in the per-step Copilot Studio drill-down with the
            # source table + filter shape.
            try:
                from src.services.control_plane.run_context import emit as _emit
                _emit(
                    level="INFO",
                    message=(
                        f"Virtual query {request.virtual_entity} -> "
                        f"{len(reversed_rows)} rows ({source_type_label})"
                    ),
                    details={
                        "virtual_entity": request.virtual_entity,
                        "source_table": rule.source_table,
                        "source_schema": rule.source_schema,
                        "source_type": source_type_label,
                        "row_count": len(reversed_rows),
                        "filters": [
                            getattr(f, "column", None) for f in (translated_filters or [])
                        ],
                    },
                    source="virtual_query",
                )
            except Exception:
                pass

            return VirtualQueryResponse(
                rows=reversed_rows,
                metadata={
                    "source_table": rule.source_table,
                    "source_schema": rule.source_schema,
                    "source_system": rule.source_system,
                    "source_type": source_type_label,
                    "mode": mode,
                    "rule_id": rule.id,
                    "row_count": len(reversed_rows),
                },
                virtual_entity=request.virtual_entity,
            )

        if rule.source_type.value == "ATHENA":
            if not self._athena_service:
                raise ValueError("AthenaQueryService not configured")

            col_str = ", ".join(source_columns) if source_columns else "*"
            sql = f'SELECT {col_str} FROM "{rule.source_table}"'
            where_parts = []
            if translated_filters:
                for qf in translated_filters:
                    if isinstance(qf.value, str):
                        where_parts.append(f"{qf.column} = '{qf.value}'")
                    else:
                        where_parts.append(f"{qf.column} = {qf.value}")
            if where_parts:
                sql += " WHERE " + " AND ".join(where_parts)
            sql += f" LIMIT {request.limit}"

            vq_logger.info("Executing Athena query for virtual entity",
                           virtual_entity=request.virtual_entity,
                           glue_table=rule.source_table)
            rows = await self._athena_service.execute_query(sql, database=rule.source_schema)

            reversed_rows = []
            for row in rows:
                reversed_rows.append(
                    {reverse_map.get(k, k): v for k, v in row.items()}
                )
            return VirtualQueryResponse(
                rows=reversed_rows,
                metadata={
                    "source_table": rule.source_table,
                    "source_schema": rule.source_schema or "glue",
                    "source_system": rule.source_system,
                    "source_type": "athena",
                    "rule_id": rule.id,
                    "row_count": len(reversed_rows),
                },
                virtual_entity=request.virtual_entity,
            )

        if rule.source_type.value in ("ETL", "CDC"):
            query_kwargs = {
                "table": rule.source_table,
                "schema_name": rule.source_schema or "external_sources",
                "filters": translated_filters,
                "limit": request.limit,
                "offset": request.offset,
            }
            if source_columns:
                query_kwargs["columns"] = source_columns
            query_request = QueryRequest(**query_kwargs)

            etl_sim_key = SCHEMA_TO_SIMULATOR.get(rule.source_schema or "external_sources", "external")
            etl_sim = self._simulators.get(etl_sim_key) if etl_sim_key else None

            if etl_sim and hasattr(etl_sim, "ensure_loaded"):
                await etl_sim.ensure_loaded()
            if etl_sim and getattr(etl_sim, "loaded", False):
                vq_logger.info(
                    "Executing ETL-hydrated query via simulator",
                    virtual_entity=request.virtual_entity,
                    source_table=rule.source_table,
                    source_schema=rule.source_schema,
                )
                response = await etl_sim.execute_query(query_request)
                reversed_rows = [
                    {reverse_map.get(k, k): v for k, v in row.items()}
                    for row in response.rows
                ]
                return VirtualQueryResponse(
                    rows=reversed_rows,
                    metadata={
                        "source_table": rule.source_table,
                        "source_schema": rule.source_schema or "external_sources",
                        "source_system": rule.source_system,
                        "source_type": "etl_hydrated",
                        "rule_id": rule.id,
                        "row_count": len(reversed_rows),
                    },
                    virtual_entity=request.virtual_entity,
                )

            if self._athena_service and rule.source_schema:
                vq_logger.info(
                    "Executing ETL-hydrated query via Athena",
                    virtual_entity=request.virtual_entity,
                    glue_table=rule.source_table,
                )
                col_str = ", ".join(source_columns) if source_columns else "*"
                sql = f'SELECT {col_str} FROM "{rule.source_table}"'
                where_parts = []
                if translated_filters:
                    for qf in translated_filters:
                        if isinstance(qf.value, str):
                            where_parts.append(f"{qf.column} = '{qf.value}'")
                        else:
                            where_parts.append(f"{qf.column} = {qf.value}")
                if where_parts:
                    sql += " WHERE " + " AND ".join(where_parts)
                sql += f" LIMIT {request.limit}"
                rows = await self._athena_service.execute_query(sql, database=rule.source_schema)
                reversed_rows = [
                    {reverse_map.get(k, k): v for k, v in row.items()}
                    for row in rows
                ]
                return VirtualQueryResponse(
                    rows=reversed_rows,
                    metadata={
                        "source_table": rule.source_table,
                        "source_schema": rule.source_schema,
                        "source_system": rule.source_system,
                        "source_type": "etl_athena",
                        "rule_id": rule.id,
                        "row_count": len(reversed_rows),
                    },
                    virtual_entity=request.virtual_entity,
                )

            vq_logger.warning(
                "No simulator or Athena available for ETL/CDC query",
                virtual_entity=request.virtual_entity,
            )
            return VirtualQueryResponse(
                rows=[],
                metadata={
                    "message": "ETL/CDC data not available - no hydrated store or Athena configured",
                    "source_type": rule.source_type.value,
                },
                virtual_entity=request.virtual_entity,
            )

        if rule.source_type.value == "MIMIR":
            return await self._query_mimir(rule, request, field_map, reverse_map, source_columns, translated_filters)

        raise ValueError(f"Unsupported source type: {rule.source_type.value}")

    async def _query_mimir(
        self,
        rule,
        request: VirtualQueryRequest,
        field_map: Dict[str, str],
        reverse_map: Dict[str, str],
        source_columns: Optional[List[str]],
        translated_filters: Optional[List[QueryFilter]],
    ) -> VirtualQueryResponse:
        """
        Translate a VDL request against a MIMIR-source mapping rule into a
        Prometheus query_range, then sample-pivot the matrix response into
        the row shape (one row per (sample timestamp x labelset)).
        """
        if not self._mimir_client:
            from src.services.mimir_client import get_default_mimir_client
            self._mimir_client = get_default_mimir_client()

        cfg = _parse_business_logic(rule.business_logic)
        metric_name = rule.source_table
        label_map: Dict[str, str] = cfg.get("label_map", {})
        aggregation = (cfg.get("default_aggregation") or "avg").lower()
        step = int(cfg.get("default_step_seconds", 3600))
        lookback = int(cfg.get("default_lookback_seconds", 604800))
        tenant = cfg.get("tenant_resolver")
        if tenant and tenant.startswith("fixed:"):
            tenant_id: Optional[str] = tenant.split(":", 1)[1]
        else:
            tenant_id = None  # use client default

        end_s = int(time.time())
        start_s = end_s - lookback

        # Build PromQL: optional label matchers from filters, optional by(...) from group_by.
        matchers = []
        if translated_filters:
            for qf in translated_filters:
                prom_label = label_map.get(qf.column, qf.column)
                if qf.operator == FilterOperator.eq:
                    matchers.append(f'{prom_label}="{qf.value}"')
                elif qf.operator == FilterOperator.ne:
                    matchers.append(f'{prom_label}!="{qf.value}"')
                # other ops are not natively supported by PromQL label matchers; skip.
        matcher_str = "{" + ",".join(matchers) + "}" if matchers else ""

        group_by_cols: List[str] = []
        if request.group_by:
            for col in request.group_by:
                group_by_cols.append(label_map.get(col, col))

        agg_func = {
            "avg": "avg",
            "mean": "avg",
            "sum": "sum",
            "max": "max",
            "min": "min",
            "count": "count",
        }.get(aggregation, "avg")

        if group_by_cols:
            promql = f'{agg_func} by ({",".join(group_by_cols)}) ({metric_name}{matcher_str})'
        else:
            promql = f'{metric_name}{matcher_str}'

        vq_logger.info(
            "Executing Mimir query_range",
            virtual_entity=request.virtual_entity,
            metric=metric_name,
            promql=promql,
            tenant=tenant_id or self._mimir_client.tenant_id,
        )
        result_matrix = await self._mimir_client.query_range(
            promql=promql, start=start_s, end=end_s, step=step, tenant_id=tenant_id,
        )

        # Sample-pivot: each entry has {metric: {label: value}, values: [[ts, "value"], ...]}.
        # Emit one row per (timestamp, labelset). Reverse-map labels back to virtual columns.
        rows: List[Dict[str, Any]] = []
        prom_to_virtual = {v: k for k, v in label_map.items()}
        for entry in result_matrix:
            metric_labels = entry.get("metric", {}) or {}
            virtual_labels: Dict[str, Any] = {}
            for lname, lval in metric_labels.items():
                if lname == "__name__":
                    continue
                virtual_col = prom_to_virtual.get(lname, lname)
                virtual_labels[virtual_col] = lval
            for sample in entry.get("values", []) or []:
                ts_s, val_str = sample[0], sample[1]
                try:
                    val = float(val_str)
                except Exception:
                    continue
                row = dict(virtual_labels)
                row["timestamp"] = int(float(ts_s) * 1000)
                row["value"] = val
                rows.append(row)

        # Reverse-map source field names to virtual entity field names (for any
        # field_map entries that don't go via labels - e.g. a stored "value" or
        # "timestamp" pseudo column).
        reversed_rows = [
            {reverse_map.get(k, k): v for k, v in row.items()} for row in rows
        ]

        if request.limit:
            reversed_rows = reversed_rows[: request.limit]

        return VirtualQueryResponse(
            rows=reversed_rows,
            metadata={
                "source_table": metric_name,
                "source_schema": rule.source_schema or "mimir",
                "source_system": rule.source_system,
                "source_type": "mimir",
                "rule_id": rule.id,
                "row_count": len(reversed_rows),
                "promql": promql,
                "step_seconds": step,
            },
            virtual_entity=request.virtual_entity,
        )

    async def list_virtual_entities(self) -> List[dict]:
        rules = await self._mapping_service.list_all()

        grouped: dict = {}
        for rule in rules:
            name = rule.virtual_entity
            if name not in grouped:
                grouped[name] = {"sources": [], "active_count": 0}
            grouped[name]["sources"].append({
                "source_system": rule.source_system,
                "source_table": rule.source_table,
                "source_type": rule.source_type.value,
                "status": rule.status.value,
            })
            if rule.status.value == "active":
                grouped[name]["active_count"] += 1

        return [
            {
                "virtual_entity": name,
                "source_count": len(info["sources"]),
                "active_rules": info["active_count"],
                "sources": info["sources"],
            }
            for name, info in grouped.items()
        ]

    async def preview_entity(self, virtual_entity: str, limit: int = 10) -> VirtualQueryResponse:
        request = VirtualQueryRequest(virtual_entity=virtual_entity, limit=limit)
        return await self.query_virtual_entity(request)
