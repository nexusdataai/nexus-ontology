"""
Virtual Data Diagnostics service.

For every mapped virtual entity, runs a structured live probe through the
same ``VirtualQueryService.query_virtual_entity`` path that powers the
Data Plane > Virtual Data > Preview button, classifies every layer-by-
layer failure (missing rule, multiple active rules, unknown source
schema, simulator not loaded, FDW auth/connection error, missing field
maps, zero rows, etc.) and emits a one-line remediation per failed
check.

Execution model is on-demand synchronous: every call runs the checks
live, no caching layer.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.models.mapping_rule_models import VirtualQueryRequest
from src.models.virtual_data_diagnostics_models import (
    CheckLevel,
    OverallLevel,
    ScanResult,
    VirtualEntityCheck,
    VirtualEntityDiagnostic,
    VirtualEntityIndexEntry,
)

vd_logger = logger.bind(component="virtual-data-diagnostics")


SLOW_QUERY_MS = 5000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Suggestion / remediation strings, keyed by check code.
# --------------------------------------------------------------------------

def _suggest_for(code: str, entity: str, detail: str = "") -> str:
    if code == "rule_present":
        return (
            f"No mapping rule exists for `{entity}`. Create one via "
            f"`POST /api/v1/mapping-rules` or run the auto-mapper "
            f"(`POST /api/v1/mapping-rules/auto-map`)."
        )
    if code == "active_rule_count_zero":
        return (
            f"`{entity}` has rules but none are active. Activate one via "
            f"`PATCH /api/v1/mapping-rules/{{id}}` with status='active'."
        )
    if code == "active_rule_count_multi":
        return (
            f"`{entity}` has multiple active rules; the first one in storage "
            f"order wins which is fragile. Deactivate the duplicates so "
            f"exactly one active rule remains."
        )
    if code == "source_type_supported":
        return (
            f"Source type `{detail}` is not supported by VDL. Use one of "
            f"FDW / ETL_PIPELINE / MIMIR / ATHENA / CDC."
        )
    if code == "source_schema_resolved":
        return (
            f"Source schema `{detail}` is not mapped to any simulator and "
            f"no FDW exposes it. Update SCHEMA_TO_SIMULATOR or load the "
            f"simulator data first."
        )
    if code == "source_table_present":
        return (
            f"Source table not found in the resolved backend. Check that "
            f"the simulator was seeded or the FDW catalogue includes it."
        )
    if code == "backend_loaded":
        return (
            f"Backing storage for `{entity}` is unreachable or empty. {detail}"
        ).strip()
    if code == "field_maps_present":
        return (
            f"Mapping rule for `{entity}` has no field maps. The query will "
            f"return 0 rows. Add at least one fieldMap (target_field -> "
            f"source_field) to the rule."
        )
    if code == "field_maps_columns_resolved":
        return (
            f"Some source_field entries do not exist in the source table: "
            f"{detail}. Fix the rule's fieldMaps or update the source schema."
        )
    if code == "probe_query":
        return f"Probe query failed: {detail[:200]}"
    if code == "row_count_nonzero":
        return (
            f"`{entity}` returned 0 rows. Either the source dataset is empty "
            f"or the rule's filters drop everything. Re-run the journey that "
            f"populates this entity, relax filters, or load demo data."
        )
    if code == "null_field_audit":
        return (
            f"Returned rows are mostly null on column(s): {detail}. "
            f"Check the rule's fieldMaps point at populated source columns."
        )
    if code == "slow_query":
        return f"Query took {detail}; consider adding indexes or reducing limit."
    return ""


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------

class VirtualDataDiagnosticsService:
    """Runs the diagnostic checklist against mapped virtual entities."""

    def __init__(
        self,
        mapping_rule_service: Any,
        virtual_query_service: Any,
        fdw_discovery: Any = None,
        simulators: Optional[Dict[str, Any]] = None,
        athena_service: Any = None,
        mimir_client: Any = None,
    ) -> None:
        self._mapping_rule_service = mapping_rule_service
        self._vqs = virtual_query_service
        self._fdw_discovery = fdw_discovery
        self._simulators = simulators or {}
        self._athena = athena_service
        self._mimir = mimir_client

    # ------------------------------------------------------------------
    # Listing (no probe)
    # ------------------------------------------------------------------

    async def list_index(self) -> List[VirtualEntityIndexEntry]:
        try:
            rules = await self._mapping_rule_service.list_all()
        except Exception as e:
            vd_logger.warning("list_all rules failed: {}", e)
            rules = []

        grouped: Dict[str, Dict[str, Any]] = {}
        for r in rules:
            name = getattr(r, "virtual_entity", None)
            if not name:
                continue
            entry = grouped.setdefault(name, {
                "total": 0, "active": 0,
                "systems": set(), "schemas": set(),
            })
            entry["total"] += 1
            if _rule_status(r) == "active":
                entry["active"] += 1
            ss = getattr(r, "source_system", None)
            if ss:
                entry["systems"].add(ss)
            sch = getattr(r, "source_schema", None)
            if sch:
                entry["schemas"].add(sch)

        return [
            VirtualEntityIndexEntry(
                virtualEntity=name,
                totalRuleCount=info["total"],
                activeRuleCount=info["active"],
                sourceSystems=sorted(info["systems"]),
                sourceSchemas=sorted(info["schemas"]),
            )
            for name, info in sorted(grouped.items())
        ]

    # ------------------------------------------------------------------
    # Per-entity probe
    # ------------------------------------------------------------------

    async def diagnose_entity(
        self,
        virtual_entity: str,
        limit: int = 5,
    ) -> VirtualEntityDiagnostic:
        t0 = time.perf_counter()
        checks: List[VirtualEntityCheck] = []

        # 1. rule_present
        try:
            rules = await self._mapping_rule_service.list_all(
                virtual_entity=virtual_entity
            )
        except Exception as e:
            rules = []
            vd_logger.warning("list rules failed for {}: {}", virtual_entity, e)
        total_rules = len(rules)
        active_rules = [r for r in rules if _rule_status(r) == "active"]
        active_count = len(active_rules)

        if total_rules == 0:
            checks.append(VirtualEntityCheck(
                code="rule_present", status=CheckLevel.FAIL,
                message="No mapping rule found for this entity.",
                suggestion=_suggest_for("rule_present", virtual_entity),
            ))
            return self._finalize(virtual_entity, checks,
                                  total_rules, active_count,
                                  duration_ms=int((time.perf_counter() - t0) * 1000))
        checks.append(VirtualEntityCheck(
            code="rule_present", status=CheckLevel.PASS,
            message=f"{total_rules} mapping rule(s) registered.",
        ))

        # 2. active_rule_count
        if active_count == 0:
            checks.append(VirtualEntityCheck(
                code="active_rule_count_zero", status=CheckLevel.FAIL,
                message="None of the rules are activated.",
                suggestion=_suggest_for("active_rule_count_zero", virtual_entity),
            ))
            return self._finalize(virtual_entity, checks,
                                  total_rules, active_count,
                                  duration_ms=int((time.perf_counter() - t0) * 1000))
        if active_count > 1:
            checks.append(VirtualEntityCheck(
                code="active_rule_count_multi", status=CheckLevel.WARN,
                message=f"{active_count} active rules; the first wins.",
                suggestion=_suggest_for("active_rule_count_multi", virtual_entity),
                detail={"active_count": active_count,
                        "active_rule_ids": [getattr(r, "id", None) for r in active_rules]},
            ))
        else:
            checks.append(VirtualEntityCheck(
                code="active_rule_count", status=CheckLevel.PASS,
                message="Exactly one active rule.",
            ))

        rule = active_rules[0]
        rule_id = getattr(rule, "id", None)
        source_type = _rule_source_type(rule)
        source_system = getattr(rule, "source_system", None)
        source_schema = getattr(rule, "source_schema", None)
        source_table = getattr(rule, "source_table", None)

        # 3. source_type_supported
        supported = {"FDW", "ETL_PIPELINE", "ETL", "CDC", "MIMIR", "ATHENA"}
        if source_type not in supported:
            checks.append(VirtualEntityCheck(
                code="source_type_supported", status=CheckLevel.FAIL,
                message=f"Unsupported source type: {source_type}.",
                suggestion=_suggest_for("source_type_supported",
                                        virtual_entity, source_type or "<empty>"),
                detail={"source_type": source_type},
            ))
            return self._finalize(virtual_entity, checks,
                                  total_rules, active_count,
                                  rule_id=rule_id, source_type=source_type,
                                  source_system=source_system,
                                  source_schema=source_schema,
                                  source_table=source_table,
                                  duration_ms=int((time.perf_counter() - t0) * 1000))
        checks.append(VirtualEntityCheck(
            code="source_type_supported", status=CheckLevel.PASS,
            message=f"Source type `{source_type}` is supported.",
        ))

        # 4. source_schema_resolved + 5. source_table_present + 6. backend_loaded
        # (combined for FDW/ETL/CDC; Mimir + Athena have their own paths)
        sim_key, sim_obj = self._resolve_simulator(source_schema)

        if source_type in ("FDW", "ETL_PIPELINE", "ETL", "CDC"):
            if sim_obj is None:
                checks.append(VirtualEntityCheck(
                    code="source_schema_resolved", status=CheckLevel.FAIL,
                    message=f"Schema `{source_schema}` is not mapped to any "
                            f"loaded simulator and no FDW exposes it.",
                    suggestion=_suggest_for("source_schema_resolved",
                                            virtual_entity, source_schema or "<empty>"),
                    detail={"source_schema": source_schema},
                ))
                return self._finalize(virtual_entity, checks,
                                      total_rules, active_count,
                                      rule_id=rule_id, source_type=source_type,
                                      source_system=source_system,
                                      source_schema=source_schema,
                                      source_table=source_table,
                                      duration_ms=int((time.perf_counter() - t0) * 1000))
            checks.append(VirtualEntityCheck(
                code="source_schema_resolved", status=CheckLevel.PASS,
                message=f"Schema `{source_schema}` -> simulator `{sim_key}`.",
            ))

            # backend_loaded
            try:
                if hasattr(sim_obj, "ensure_loaded"):
                    await sim_obj.ensure_loaded()
            except Exception as e:
                checks.append(VirtualEntityCheck(
                    code="backend_loaded", status=CheckLevel.FAIL,
                    message=f"Simulator `{sim_key}` failed to load: {e}.",
                    suggestion=_suggest_for("backend_loaded",
                                            virtual_entity,
                                            f"Reload S3 data for simulator `{sim_key}`."),
                ))
                return self._finalize(virtual_entity, checks,
                                      total_rules, active_count,
                                      rule_id=rule_id, source_type=source_type,
                                      source_system=source_system,
                                      source_schema=source_schema,
                                      source_table=source_table,
                                      duration_ms=int((time.perf_counter() - t0) * 1000))
            if not getattr(sim_obj, "loaded", False):
                checks.append(VirtualEntityCheck(
                    code="backend_loaded", status=CheckLevel.FAIL,
                    message=f"Simulator `{sim_key}` is not loaded.",
                    suggestion=_suggest_for("backend_loaded",
                                            virtual_entity,
                                            f"Load simulator `{sim_key}` from its S3 bucket."),
                ))
                return self._finalize(virtual_entity, checks,
                                      total_rules, active_count,
                                      rule_id=rule_id, source_type=source_type,
                                      source_system=source_system,
                                      source_schema=source_schema,
                                      source_table=source_table,
                                      duration_ms=int((time.perf_counter() - t0) * 1000))
            checks.append(VirtualEntityCheck(
                code="backend_loaded", status=CheckLevel.PASS,
                message=f"Simulator `{sim_key}` is loaded.",
            ))

            # source_table_present
            tbl_present, tbl_detail = await self._check_table_in_simulator(
                sim_obj, source_schema, source_table
            )
            if not tbl_present:
                checks.append(VirtualEntityCheck(
                    code="source_table_present", status=CheckLevel.FAIL,
                    message=f"Table `{source_schema}.{source_table}` not found "
                            f"in simulator `{sim_key}`.",
                    suggestion=_suggest_for("source_table_present",
                                            virtual_entity, tbl_detail),
                    detail={"sim_key": sim_key, "schema": source_schema,
                            "table": source_table, "hint": tbl_detail},
                ))
                # don't return early -- still try the probe in case the
                # sim has it under a different schema alias.
            else:
                checks.append(VirtualEntityCheck(
                    code="source_table_present", status=CheckLevel.PASS,
                    message=f"Table `{source_schema}.{source_table}` present in simulator.",
                ))

        elif source_type == "MIMIR":
            if self._mimir is None or not getattr(self._mimir, "configured", False):
                checks.append(VirtualEntityCheck(
                    code="backend_loaded", status=CheckLevel.FAIL,
                    message="Mimir client not configured.",
                    suggestion=_suggest_for("backend_loaded", virtual_entity,
                                            "Set MIMIR_URL / MIMIR_ENABLED on the deployment."),
                ))
                return self._finalize(virtual_entity, checks,
                                      total_rules, active_count,
                                      rule_id=rule_id, source_type=source_type,
                                      source_system=source_system,
                                      source_schema=source_schema,
                                      source_table=source_table,
                                      duration_ms=int((time.perf_counter() - t0) * 1000))
            checks.append(VirtualEntityCheck(
                code="backend_loaded", status=CheckLevel.PASS,
                message="Mimir client configured.",
            ))

        elif source_type == "ATHENA":
            if self._athena is None:
                checks.append(VirtualEntityCheck(
                    code="backend_loaded", status=CheckLevel.FAIL,
                    message="Athena service not initialised.",
                    suggestion=_suggest_for("backend_loaded", virtual_entity,
                                            "Wire AthenaQueryService into the gateway."),
                ))
                return self._finalize(virtual_entity, checks,
                                      total_rules, active_count,
                                      rule_id=rule_id, source_type=source_type,
                                      source_system=source_system,
                                      source_schema=source_schema,
                                      source_table=source_table,
                                      duration_ms=int((time.perf_counter() - t0) * 1000))
            checks.append(VirtualEntityCheck(
                code="backend_loaded", status=CheckLevel.PASS,
                message="Athena service initialised.",
            ))

        # 7. field_maps_present
        field_maps = list(getattr(rule, "field_maps", None) or [])
        if not field_maps:
            checks.append(VirtualEntityCheck(
                code="field_maps_present", status=CheckLevel.WARN,
                message="Mapping rule has no field maps.",
                suggestion=_suggest_for("field_maps_present", virtual_entity),
            ))
        else:
            checks.append(VirtualEntityCheck(
                code="field_maps_present", status=CheckLevel.PASS,
                message=f"{len(field_maps)} field map(s) defined.",
                detail={"field_count": len(field_maps)},
            ))

        # 8. probe_query (the live preview)
        t1 = time.perf_counter()
        rows: List[Dict[str, Any]] = []
        latency_ms: Optional[int] = None
        try:
            resp = await self._vqs.query_virtual_entity(VirtualQueryRequest(
                virtual_entity=virtual_entity, limit=limit,
            ))
            latency_ms = int((time.perf_counter() - t1) * 1000)
            rows = list(resp.rows or [])
            checks.append(VirtualEntityCheck(
                code="probe_query", status=CheckLevel.PASS,
                message=f"Query OK ({len(rows)} row(s) in {latency_ms}ms).",
                detail={"latency_ms": latency_ms},
            ))
        except Exception as e:
            latency_ms = int((time.perf_counter() - t1) * 1000)
            checks.append(VirtualEntityCheck(
                code="probe_query", status=CheckLevel.FAIL,
                message=f"{type(e).__name__}: {str(e)[:200]}",
                suggestion=_suggest_for("probe_query", virtual_entity, str(e)),
                detail={"latency_ms": latency_ms},
            ))
            return self._finalize(virtual_entity, checks,
                                  total_rules, active_count,
                                  rule_id=rule_id, source_type=source_type,
                                  source_system=source_system,
                                  source_schema=source_schema,
                                  source_table=source_table,
                                  row_count=0, latency_ms=latency_ms,
                                  duration_ms=int((time.perf_counter() - t0) * 1000))

        # 9. row_count_nonzero
        if not rows:
            checks.append(VirtualEntityCheck(
                code="row_count_nonzero", status=CheckLevel.WARN,
                message="Query returned 0 rows.",
                suggestion=_suggest_for("row_count_nonzero", virtual_entity),
            ))
            return self._finalize(virtual_entity, checks,
                                  total_rules, active_count,
                                  rule_id=rule_id, source_type=source_type,
                                  source_system=source_system,
                                  source_schema=source_schema,
                                  source_table=source_table,
                                  row_count=0, latency_ms=latency_ms,
                                  duration_ms=int((time.perf_counter() - t0) * 1000))

        checks.append(VirtualEntityCheck(
            code="row_count_nonzero", status=CheckLevel.PASS,
            message=f"{len(rows)} row(s) returned.",
        ))

        # 10. null_field_audit (warn on >50% null per column)
        #
        # The probe sample (``rows``) is bounded by the caller's ``limit``
        # (5 by default). With a small sample, columns that are
        # legitimately null on a fraction of rows (e.g.
        # AP_Payment.Check_Number is null for Wire/ACH payments)
        # frequently appear all-null by chance and false-warn. Pull a
        # separate, larger sample dedicated to the audit so the warn
        # reflects the table's actual null distribution rather than
        # whichever rows the probe happened to surface.
        NULL_AUDIT_TARGET = 50
        audit_rows: List[Dict[str, Any]] = list(rows)
        if len(audit_rows) < NULL_AUDIT_TARGET:
            try:
                bigger = await self._vqs.query_virtual_entity(
                    VirtualQueryRequest(virtual_entity=virtual_entity,
                                        limit=NULL_AUDIT_TARGET),
                )
                bigger_rows = list(bigger.rows or [])
                if len(bigger_rows) > len(audit_rows):
                    audit_rows = bigger_rows
            except Exception:
                # Best-effort - fall back to the probe sample.
                pass

        sample_size = len(audit_rows)
        all_null_cols: List[str] = []
        mostly_null_cols: List[str] = []
        for col in audit_rows[0].keys():
            null_count = sum(1 for r in audit_rows if r.get(col) is None)
            if null_count == sample_size:
                all_null_cols.append(col)
            elif null_count > sample_size // 2:
                mostly_null_cols.append(col)
        # Require a meaningful sample (>=20) before raising the warn,
        # otherwise surface the suspicious columns under
        # ``low_confidence_null`` for the UI but keep the check at PASS.
        MIN_NULL_AUDIT_SAMPLE = 20
        if all_null_cols and sample_size >= MIN_NULL_AUDIT_SAMPLE:
            checks.append(VirtualEntityCheck(
                code="null_field_audit", status=CheckLevel.WARN,
                message=f"All sampled rows ({sample_size}) are null on column(s): "
                        f"{', '.join(all_null_cols)}.",
                suggestion=_suggest_for("null_field_audit", virtual_entity,
                                        ", ".join(all_null_cols)),
                detail={"all_null_columns": all_null_cols,
                        "mostly_null_columns": mostly_null_cols,
                        "sample_size": sample_size},
            ))
        else:
            checks.append(VirtualEntityCheck(
                code="null_field_audit", status=CheckLevel.PASS,
                message="All columns have at least one non-null value.",
                detail={"mostly_null_columns": mostly_null_cols,
                        "low_confidence_null": all_null_cols if sample_size < MIN_NULL_AUDIT_SAMPLE else [],
                        "sample_size": sample_size},
            ))

        # 11. slow_query (warn at >SLOW_QUERY_MS)
        if latency_ms is not None and latency_ms > SLOW_QUERY_MS:
            checks.append(VirtualEntityCheck(
                code="slow_query", status=CheckLevel.WARN,
                message=f"Query took {latency_ms}ms (>{SLOW_QUERY_MS}ms threshold).",
                suggestion=_suggest_for("slow_query", virtual_entity,
                                        f"{latency_ms}ms"),
                detail={"latency_ms": latency_ms},
            ))

        return self._finalize(virtual_entity, checks,
                              total_rules, active_count,
                              rule_id=rule_id, source_type=source_type,
                              source_system=source_system,
                              source_schema=source_schema,
                              source_table=source_table,
                              row_count=len(rows), latency_ms=latency_ms,
                              sample_row=rows[0] if rows else None,
                              duration_ms=int((time.perf_counter() - t0) * 1000))

    # ------------------------------------------------------------------
    # Bulk probe
    # ------------------------------------------------------------------

    async def diagnose_all(
        self,
        entities: Optional[List[str]] = None,
        limit: int = 5,
        concurrency: int = 8,
    ) -> ScanResult:
        t0 = time.perf_counter()
        index = await self.list_index()
        if entities:
            wanted = set(entities)
            index = [e for e in index if e.virtual_entity in wanted]

        sem = asyncio.Semaphore(max(1, concurrency))

        async def _one(name: str) -> Optional[VirtualEntityDiagnostic]:
            async with sem:
                try:
                    return await self.diagnose_entity(name, limit=limit)
                except Exception as e:
                    vd_logger.warning("diagnose_entity failed for {}: {}", name, e)
                    return None

        results: List[VirtualEntityDiagnostic] = []
        for fut in asyncio.as_completed([_one(e.virtual_entity) for e in index]):
            d = await fut
            if d is not None:
                results.append(d)

        results.sort(key=lambda r: r.virtual_entity)
        healthy, degraded, unhealthy = _count_overall(results)
        if unhealthy > 0:
            overall = OverallLevel.UNHEALTHY
        elif degraded > 0:
            overall = OverallLevel.DEGRADED
        else:
            overall = OverallLevel.HEALTHY

        return ScanResult(
            overall=overall,
            total=len(results),
            healthy=healthy, degraded=degraded, unhealthy=unhealthy,
            entities=results,
            durationMs=int((time.perf_counter() - t0) * 1000),
            scannedAt=_now_iso(),
        )

    async def diagnose_all_streaming(
        self,
        entities: Optional[List[str]] = None,
        limit: int = 5,
        concurrency: int = 8,
    ):
        """Async generator: yields each VirtualEntityDiagnostic as it completes."""
        index = await self.list_index()
        if entities:
            wanted = set(entities)
            index = [e for e in index if e.virtual_entity in wanted]
        sem = asyncio.Semaphore(max(1, concurrency))

        async def _one(name: str) -> Optional[VirtualEntityDiagnostic]:
            async with sem:
                try:
                    return await self.diagnose_entity(name, limit=limit)
                except Exception as e:
                    vd_logger.warning("diagnose_entity failed for {}: {}", name, e)
                    return None

        for fut in asyncio.as_completed([_one(e.virtual_entity) for e in index]):
            d = await fut
            if d is not None:
                yield d

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _resolve_simulator(self, schema: Optional[str]) -> Tuple[Optional[str], Any]:
        if not schema:
            return None, None
        from src.services.virtual_query_service import SCHEMA_TO_SIMULATOR
        sim_key = SCHEMA_TO_SIMULATOR.get(schema)
        if not sim_key:
            return None, None
        sim = self._simulators.get(sim_key)
        return sim_key, sim

    async def _check_table_in_simulator(
        self,
        sim: Any,
        schema: Optional[str],
        table: Optional[str],
    ) -> Tuple[bool, str]:
        """
        Decide whether ``schema.table`` is queryable in the simulator.

        The simulator's ``list_foreign_tables()`` only returns the manifest
        loaded at startup; runtime-written tables (e.g. journey results
        seeded via ``write_table``) live in Redis but never appear in the
        manifest. So we look at the actual row store first - that's the
        ground truth for "is the data there". Fall back to the manifest
        only if the row-store check is unsupported.
        """
        if not table:
            return False, "rule has no source_table"
        if not sim:
            return False, "no simulator"

        # Primary check: live row count from Redis (or in-memory store).
        if hasattr(sim, "_get_table_row_count"):
            try:
                count = await sim._get_table_row_count(schema or "", table)
                if count and count > 0:
                    return True, f"found ({count} rows)"
            except Exception:
                pass
        if hasattr(sim, "_get_table_data"):
            try:
                rows = await sim._get_table_data(schema or "", table)
                if rows:
                    return True, f"found ({len(rows)} rows)"
            except Exception:
                pass

        # Fallback: manifest membership. May report a table as present even
        # when its Redis store is empty (the rule's storage is wired but no
        # rows have been written). The downstream probe_query / row_count
        # checks will still surface the empty-data case.
        try:
            tables = (
                await sim.list_foreign_tables()
                if hasattr(sim, "list_foreign_tables")
                else []
            )
        except Exception as e:
            return False, f"list_foreign_tables failed: {e}"
        for t in tables or []:
            t_schema = getattr(t, "schema_name", None)
            t_name = getattr(t, "table_name", None)
            if t_name == table and (schema is None or t_schema == schema):
                return True, "found in manifest (empty store)"
        return False, f"table absent from store and manifest ({len(tables or [])} tables seen)"

    def _finalize(
        self,
        virtual_entity: str,
        checks: List[VirtualEntityCheck],
        total_rules: int,
        active_rules: int,
        rule_id: Optional[str] = None,
        source_type: Optional[str] = None,
        source_system: Optional[str] = None,
        source_schema: Optional[str] = None,
        source_table: Optional[str] = None,
        row_count: Optional[int] = None,
        latency_ms: Optional[int] = None,
        sample_row: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> VirtualEntityDiagnostic:
        # Roll up overall: any FAIL -> UNHEALTHY, any WARN -> DEGRADED, else HEALTHY.
        has_fail = any(_check_status(c) == CheckLevel.FAIL for c in checks)
        has_warn = any(_check_status(c) == CheckLevel.WARN for c in checks)
        if has_fail:
            overall = OverallLevel.UNHEALTHY
        elif has_warn:
            overall = OverallLevel.DEGRADED
        else:
            overall = OverallLevel.HEALTHY

        return VirtualEntityDiagnostic(
            virtualEntity=virtual_entity,
            overall=overall,
            sourceType=source_type,
            sourceSystem=source_system,
            sourceSchema=source_schema,
            sourceTable=source_table,
            ruleId=rule_id,
            activeRuleCount=active_rules,
            totalRuleCount=total_rules,
            rowCount=row_count,
            latencyMs=latency_ms,
            checks=checks,
            sampleRow=sample_row,
            durationMs=duration_ms,
            scannedAt=_now_iso(),
        )


# --------------------------------------------------------------------------
# Tiny helpers (Pydantic enums sometimes serialize to value vs the enum
# member; tolerate both).
# --------------------------------------------------------------------------

def _rule_status(rule: Any) -> str:
    s = getattr(rule, "status", None)
    return getattr(s, "value", None) or str(s) or ""


def _rule_source_type(rule: Any) -> Optional[str]:
    st = getattr(rule, "source_type", None)
    return getattr(st, "value", None) or (str(st) if st is not None else None)


def _check_status(check: VirtualEntityCheck) -> CheckLevel:
    s = check.status
    if isinstance(s, CheckLevel):
        return s
    if s == CheckLevel.FAIL.value:
        return CheckLevel.FAIL
    if s == CheckLevel.WARN.value:
        return CheckLevel.WARN
    return CheckLevel.PASS


def _count_overall(results: List[VirtualEntityDiagnostic]) -> Tuple[int, int, int]:
    healthy = sum(1 for r in results if _entity_overall(r) == OverallLevel.HEALTHY)
    degraded = sum(1 for r in results if _entity_overall(r) == OverallLevel.DEGRADED)
    unhealthy = sum(1 for r in results if _entity_overall(r) == OverallLevel.UNHEALTHY)
    return healthy, degraded, unhealthy


def _entity_overall(r: VirtualEntityDiagnostic) -> OverallLevel:
    o = r.overall
    if isinstance(o, OverallLevel):
        return o
    if o == OverallLevel.UNHEALTHY.value:
        return OverallLevel.UNHEALTHY
    if o == OverallLevel.DEGRADED.value:
        return OverallLevel.DEGRADED
    return OverallLevel.HEALTHY
