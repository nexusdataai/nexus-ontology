"""
Dashboard Diagnostics service.

For every saved dashboard in the workspace, runs each panel's PanelQuery
target through the same VDL stack the dashboard renderer uses, captures
the response, and grades it against a fixed checklist (see
``models/dashboard_diagnostics_models.py``).

Execution model is on-demand synchronous: every call runs the checks live,
no caching layer.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.models.dashboard_diagnostics_models import (
    BackendDiagnostic, BackendsDiagnostic,
    CODE_TO_LEVEL, CheckLevel, DashboardDiagnostic, DashboardIndexEntry,
    EntityDiagnostic, OverallLevel, PanelCheckCode, PanelDiagnostic,
    ScanResult,
)
from src.models.mapping_rule_models import (
    VirtualFilter, VirtualQueryRequest,
)

dd_logger = logger.bind(component="dashboard-diagnostics")


SLOW_QUERY_MS = 5000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _suggest_for(code: PanelCheckCode, entity: str, detail: str = "") -> str:
    if code == PanelCheckCode.NO_MAPPING_RULE:
        return f"Add a VDL mapping rule for `{entity}` (or run the catalogue seed)."
    if code == PanelCheckCode.INACTIVE_RULE:
        return f"Activate the existing mapping rule for `{entity}`."
    if code == PanelCheckCode.BACKEND_UNREACHABLE:
        return f"Backing storage for `{entity}` is unreachable. {detail}".strip()
    if code == PanelCheckCode.QUERY_ERROR:
        return f"Query failed: {detail[:160]}"
    if code == PanelCheckCode.NO_ROWS:
        return (
            f"`{entity}` has 0 rows. Run the relevant journey to populate it, or "
            f"set SOLUTION_FORCE_SEED=true and restart to re-seed demo data."
        )
    if code == PanelCheckCode.MISSING_COLUMNS:
        return f"Returned rows for `{entity}` are missing expected columns: {detail}"
    if code == PanelCheckCode.NULL_GROUP_KEYS:
        return (
            f"All rows of `{entity}` have null in groupBy column(s) {detail}. "
            f"Add the column to the source table or to mapping rule field maps."
        )
    if code == PanelCheckCode.SLOW_QUERY:
        return f"Query took {detail}; consider adding indexes or reducing limit."
    return ""


class DashboardDiagnosticsService:
    """
    Runs the diagnostic checklist against saved dashboards on demand.

    Construction-injected dependencies match what is wired in
    ``mcp_http_gateway.startup_event``:
    """

    def __init__(
        self,
        dashboard_service: Any,
        mapping_rule_service: Any,
        virtual_query_service: Any,
        simulators: Optional[Dict[str, Any]] = None,
        mimir_client: Any = None,
        athena_service: Any = None,
    ) -> None:
        self._dashboard_service = dashboard_service
        self._mapping_rule_service = mapping_rule_service
        self._vqs = virtual_query_service
        self._simulators = simulators or {}
        self._mimir = mimir_client
        self._athena = athena_service

    # ------------------------------------------------------------------
    # Listing (no diagnostic run)
    # ------------------------------------------------------------------

    async def list_index(self) -> List[DashboardIndexEntry]:
        rows = await self._dashboard_service.list_all() if self._dashboard_service else []
        result: List[DashboardIndexEntry] = []
        for r in rows:
            result.append(DashboardIndexEntry(
                uid=r.get("uid") or "",
                title=r.get("title") or "",
                description=r.get("description"),
                tags=list(r.get("tags") or []),
                panelCount=int(r.get("panelCount") or len(r.get("panels") or [])),
                updatedAt=r.get("updatedAt"),
            ))
        return result

    # ------------------------------------------------------------------
    # Per-panel
    # ------------------------------------------------------------------

    async def diagnose_panel(
        self,
        panel: Dict[str, Any],
        target: Dict[str, Any],
        limit: int = 10,
    ) -> PanelDiagnostic:
        entity = (target.get("entity") or "").strip()
        panel_id = int(panel.get("id") or 0)
        panel_title = panel.get("title") or ""
        panel_type = panel.get("type") or ""
        ref_id = target.get("refId") or target.get("ref_id") or "A"
        expected_fields: List[str] = list(target.get("fields") or [])
        group_by: List[str] = list(target.get("groupBy") or target.get("group_by") or [])

        query_payload = {
            "entity": entity, "fields": expected_fields,
            "filters": target.get("filters") or [],
            "groupBy": group_by,
            "aggregation": target.get("aggregation"),
            "limit": min(limit, int(target.get("limit") or limit)),
        }

        # 1. mapping rule check
        if not entity:
            return self._panel_result(
                panel_id, panel_title, panel_type, ref_id, entity,
                code=PanelCheckCode.QUERY_ERROR,
                error="panel target has no entity",
                expected_fields=expected_fields, query_payload=query_payload,
            )

        rule = await self._first_active_rule(entity)
        if rule is None:
            inactive = await self._first_any_rule(entity)
            if inactive is not None:
                return self._panel_result(
                    panel_id, panel_title, panel_type, ref_id, entity,
                    code=PanelCheckCode.INACTIVE_RULE,
                    rule_id=getattr(inactive, "id", None),
                    source_type=getattr(getattr(inactive, "source_type", None), "value", None),
                    expected_fields=expected_fields, query_payload=query_payload,
                )
            return self._panel_result(
                panel_id, panel_title, panel_type, ref_id, entity,
                code=PanelCheckCode.NO_MAPPING_RULE,
                expected_fields=expected_fields, query_payload=query_payload,
            )

        rule_id = getattr(rule, "id", None)
        source_type = getattr(getattr(rule, "source_type", None), "value", None)

        # 2. backend reachability pre-check
        reach_ok, reach_detail = await self._check_backend(rule)
        if not reach_ok:
            return self._panel_result(
                panel_id, panel_title, panel_type, ref_id, entity,
                code=PanelCheckCode.BACKEND_UNREACHABLE,
                rule_id=rule_id, source_type=source_type,
                error=reach_detail,
                expected_fields=expected_fields, query_payload=query_payload,
            )

        # 3. execute the panel query
        filters_list: Optional[List[VirtualFilter]] = None
        raw_filters = target.get("filters") or []
        if raw_filters:
            filters_list = []
            for f in raw_filters:
                try:
                    filters_list.append(VirtualFilter(
                        field=f.get("field"),
                        operator=f.get("operator", "eq"),
                        value=f.get("value"),
                    ))
                except Exception:
                    pass

        vq = VirtualQueryRequest(
            virtual_entity=entity,
            fields=expected_fields or None,
            filters=filters_list,
            group_by=group_by or None,
            aggregation=(
                target.get("aggregation", {}).get("function")
                if isinstance(target.get("aggregation"), dict) else None
            ),
            limit=query_payload["limit"],
        )

        t0 = time.perf_counter()
        try:
            resp = await self._vqs.query_virtual_entity(vq)
        except Exception as e:
            return self._panel_result(
                panel_id, panel_title, panel_type, ref_id, entity,
                code=PanelCheckCode.QUERY_ERROR,
                rule_id=rule_id, source_type=source_type,
                error=f"{type(e).__name__}: {e}",
                latency_ms=int((time.perf_counter() - t0) * 1000),
                expected_fields=expected_fields, query_payload=query_payload,
            )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        rows = list(resp.rows or [])
        row_count = len(rows)

        # 4. row count
        if row_count == 0:
            return self._panel_result(
                panel_id, panel_title, panel_type, ref_id, entity,
                code=PanelCheckCode.NO_ROWS,
                rule_id=rule_id, source_type=source_type,
                row_count=0, latency_ms=latency_ms,
                expected_fields=expected_fields, returned_fields=[],
                query_payload=query_payload,
            )

        # 5. column-shape check
        returned_fields = list(rows[0].keys()) if rows else []
        missing = [f for f in expected_fields if f not in returned_fields and f != "*"]
        if missing:
            return self._panel_result(
                panel_id, panel_title, panel_type, ref_id, entity,
                code=PanelCheckCode.MISSING_COLUMNS,
                rule_id=rule_id, source_type=source_type,
                row_count=row_count, latency_ms=latency_ms,
                expected_fields=expected_fields, returned_fields=returned_fields,
                missing_fields=missing,
                query_payload=query_payload,
            )

        # 6. null group-by keys (a real bug class we've hit)
        null_cols: List[str] = []
        for g in group_by:
            if all((r.get(g) is None) for r in rows):
                null_cols.append(g)
        if null_cols:
            return self._panel_result(
                panel_id, panel_title, panel_type, ref_id, entity,
                code=PanelCheckCode.NULL_GROUP_KEYS,
                rule_id=rule_id, source_type=source_type,
                row_count=row_count, latency_ms=latency_ms,
                expected_fields=expected_fields, returned_fields=returned_fields,
                null_group_columns=null_cols,
                query_payload=query_payload,
            )

        # 7. latency check
        if latency_ms > SLOW_QUERY_MS:
            return self._panel_result(
                panel_id, panel_title, panel_type, ref_id, entity,
                code=PanelCheckCode.SLOW_QUERY,
                rule_id=rule_id, source_type=source_type,
                row_count=row_count, latency_ms=latency_ms,
                expected_fields=expected_fields, returned_fields=returned_fields,
                query_payload=query_payload,
                error=f"{latency_ms}ms (>{SLOW_QUERY_MS}ms threshold)",
            )

        # 8. all green
        return self._panel_result(
            panel_id, panel_title, panel_type, ref_id, entity,
            code=PanelCheckCode.OK,
            rule_id=rule_id, source_type=source_type,
            row_count=row_count, latency_ms=latency_ms,
            expected_fields=expected_fields, returned_fields=returned_fields,
            query_payload=query_payload,
        )

    # ------------------------------------------------------------------
    # Per-dashboard
    # ------------------------------------------------------------------

    async def diagnose_dashboard(
        self,
        uid: str,
        limit_per_panel: int = 10,
    ) -> DashboardDiagnostic:
        t0 = time.perf_counter()
        d = await self._dashboard_service.get(uid)
        if d is None:
            raise KeyError(f"Dashboard not found: {uid}")
        panels = list(d.get("panels") or [])
        targets: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for p in panels:
            for t in (p.get("targets") or []):
                targets.append((p, t))

        results: List[PanelDiagnostic] = []
        if targets:
            tasks = [self.diagnose_panel(p, t, limit_per_panel) for p, t in targets]
            done = await asyncio.gather(*tasks, return_exceptions=False)
            results.extend(done)

        healthy = sum(1 for r in results if r.status == CheckLevel.PASS.value or r.status == CheckLevel.PASS)
        degraded = sum(1 for r in results if r.status == CheckLevel.WARN.value or r.status == CheckLevel.WARN)
        unhealthy = sum(1 for r in results if r.status == CheckLevel.FAIL.value or r.status == CheckLevel.FAIL)
        if unhealthy > 0:
            overall = OverallLevel.UNHEALTHY
        elif degraded > 0:
            overall = OverallLevel.DEGRADED
        else:
            overall = OverallLevel.HEALTHY

        return DashboardDiagnostic(
            uid=uid,
            title=d.get("title") or "",
            description=d.get("description"),
            tags=list(d.get("tags") or []),
            status=overall,
            panelCount=len(panels),
            healthyCount=healthy,
            degradedCount=degraded,
            unhealthyCount=unhealthy,
            panels=results,
            durationMs=int((time.perf_counter() - t0) * 1000),
            scannedAt=_now_iso(),
        )

    async def diagnose_all(
        self,
        dashboard_uids: Optional[List[str]] = None,
        limit_per_panel: int = 10,
        concurrency: int = 8,
    ) -> ScanResult:
        t0 = time.perf_counter()
        index = await self.list_index()
        if dashboard_uids:
            wanted = set(dashboard_uids)
            index = [e for e in index if e.uid in wanted]

        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def _one(uid: str) -> Optional[DashboardDiagnostic]:
            async with semaphore:
                try:
                    return await self.diagnose_dashboard(uid, limit_per_panel)
                except Exception as e:
                    dd_logger.warning("diagnose_dashboard failed for {}: {}", uid, e)
                    return None

        coros = [_one(e.uid) for e in index]
        results: List[DashboardDiagnostic] = []
        for fut in asyncio.as_completed(coros):
            d = await fut
            if d is not None:
                results.append(d)

        healthy = sum(1 for r in results if r.status == OverallLevel.HEALTHY.value or r.status == OverallLevel.HEALTHY)
        degraded = sum(1 for r in results if r.status == OverallLevel.DEGRADED.value or r.status == OverallLevel.DEGRADED)
        unhealthy = sum(1 for r in results if r.status == OverallLevel.UNHEALTHY.value or r.status == OverallLevel.UNHEALTHY)

        return ScanResult(
            total=len(results),
            healthy=healthy, degraded=degraded, unhealthy=unhealthy,
            dashboards=results,
            durationMs=int((time.perf_counter() - t0) * 1000),
            scannedAt=_now_iso(),
        )

    async def diagnose_all_streaming(
        self,
        dashboard_uids: Optional[List[str]] = None,
        limit_per_panel: int = 10,
        concurrency: int = 8,
    ):
        """Async generator that yields each DashboardDiagnostic as it completes."""
        index = await self.list_index()
        if dashboard_uids:
            wanted = set(dashboard_uids)
            index = [e for e in index if e.uid in wanted]
        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def _one(uid: str) -> Optional[DashboardDiagnostic]:
            async with semaphore:
                try:
                    return await self.diagnose_dashboard(uid, limit_per_panel)
                except Exception as e:
                    dd_logger.warning("diagnose_dashboard failed for {}: {}", uid, e)
                    return None

        for fut in asyncio.as_completed([_one(e.uid) for e in index]):
            d = await fut
            if d is not None:
                yield d

    # ------------------------------------------------------------------
    # Backend reachability
    # ------------------------------------------------------------------

    async def diagnose_backends(self) -> BackendsDiagnostic:
        backends: List[BackendDiagnostic] = []

        # Simulators
        for key, sim in (self._simulators or {}).items():
            t0 = time.perf_counter()
            ok = bool(getattr(sim, "loaded", False))
            tables = 0
            try:
                if hasattr(sim, "_tables_with_data"):
                    tables = int(getattr(sim, "_tables_with_data") or 0)
            except Exception:
                pass
            backends.append(BackendDiagnostic(
                name=f"simulator:{key}",
                kind="simulator",
                status=CheckLevel.PASS if ok else CheckLevel.FAIL,
                detail=f"loaded={ok}, tables_with_data={tables}",
                latencyMs=int((time.perf_counter() - t0) * 1000),
                metadata={"loaded": ok, "tables_with_data": tables},
            ))

        # Mimir
        if self._mimir:
            t0 = time.perf_counter()
            ok = False
            err: Optional[str] = None
            try:
                if getattr(self._mimir, "configured", False):
                    out = await self._mimir.instant_query("up", tenant_id=None)
                    ok = isinstance(out, list)
                else:
                    err = "MIMIR_URL not configured"
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
            backends.append(BackendDiagnostic(
                name="mimir",
                kind="tsdb",
                status=CheckLevel.PASS if ok else CheckLevel.WARN,
                detail=err or "ready",
                latencyMs=int((time.perf_counter() - t0) * 1000),
                metadata={"configured": getattr(self._mimir, "configured", False)},
            ))

        # Athena
        if self._athena:
            t0 = time.perf_counter()
            ok = False
            err: Optional[str] = None
            try:
                rows = await self._athena.execute_query(
                    "SELECT 1 AS ok",
                    database=os.getenv("GLUE_DATABASE", "default"),
                )
                ok = isinstance(rows, list)
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
            backends.append(BackendDiagnostic(
                name="athena",
                kind="sql",
                status=CheckLevel.PASS if ok else CheckLevel.WARN,
                detail=err or "ready",
                latencyMs=int((time.perf_counter() - t0) * 1000),
            ))

        if any(b.status == CheckLevel.FAIL.value or b.status == CheckLevel.FAIL for b in backends):
            overall = OverallLevel.UNHEALTHY
        elif any(b.status == CheckLevel.WARN.value or b.status == CheckLevel.WARN for b in backends):
            overall = OverallLevel.DEGRADED
        else:
            overall = OverallLevel.HEALTHY

        return BackendsDiagnostic(
            overall=overall, backends=backends, scannedAt=_now_iso(),
        )

    # ------------------------------------------------------------------
    # Per-entity (lower level)
    # ------------------------------------------------------------------

    async def diagnose_entity(self, entity: str, limit: int = 5) -> EntityDiagnostic:
        t0 = time.perf_counter()
        rule = await self._first_active_rule(entity)
        if rule is None:
            inactive = await self._first_any_rule(entity)
            if inactive is not None:
                return EntityDiagnostic(
                    entity=entity,
                    status=CheckLevel.FAIL,
                    code=PanelCheckCode.INACTIVE_RULE,
                    ruleId=getattr(inactive, "id", None),
                    sourceType=getattr(getattr(inactive, "source_type", None), "value", None),
                    sourceTable=getattr(inactive, "source_table", None),
                    errorMessage=_suggest_for(PanelCheckCode.INACTIVE_RULE, entity),
                    latencyMs=int((time.perf_counter() - t0) * 1000),
                    scannedAt=_now_iso(),
                )
            return EntityDiagnostic(
                entity=entity,
                status=CheckLevel.FAIL,
                code=PanelCheckCode.NO_MAPPING_RULE,
                errorMessage=_suggest_for(PanelCheckCode.NO_MAPPING_RULE, entity),
                latencyMs=int((time.perf_counter() - t0) * 1000),
                scannedAt=_now_iso(),
            )

        try:
            resp = await self._vqs.query_virtual_entity(VirtualQueryRequest(
                virtual_entity=entity, limit=limit,
            ))
        except Exception as e:
            return EntityDiagnostic(
                entity=entity,
                status=CheckLevel.FAIL,
                code=PanelCheckCode.QUERY_ERROR,
                ruleId=getattr(rule, "id", None),
                sourceType=getattr(getattr(rule, "source_type", None), "value", None),
                sourceTable=getattr(rule, "source_table", None),
                errorMessage=f"{type(e).__name__}: {e}",
                latencyMs=int((time.perf_counter() - t0) * 1000),
                scannedAt=_now_iso(),
            )

        rows = list(resp.rows or [])
        if not rows:
            return EntityDiagnostic(
                entity=entity,
                status=CheckLevel.WARN,
                code=PanelCheckCode.NO_ROWS,
                ruleId=getattr(rule, "id", None),
                sourceType=getattr(getattr(rule, "source_type", None), "value", None),
                sourceTable=getattr(rule, "source_table", None),
                rowCount=0,
                errorMessage=_suggest_for(PanelCheckCode.NO_ROWS, entity),
                latencyMs=int((time.perf_counter() - t0) * 1000),
                scannedAt=_now_iso(),
            )
        return EntityDiagnostic(
            entity=entity,
            status=CheckLevel.PASS,
            code=PanelCheckCode.OK,
            ruleId=getattr(rule, "id", None),
            sourceType=getattr(getattr(rule, "source_type", None), "value", None),
            sourceTable=getattr(rule, "source_table", None),
            rowCount=len(rows),
            sampleRows=rows[:limit],
            latencyMs=int((time.perf_counter() - t0) * 1000),
            scannedAt=_now_iso(),
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    async def _first_active_rule(self, entity: str):
        try:
            rules = await self._mapping_rule_service.list_all(virtual_entity=entity)
        except Exception:
            return None
        for r in rules:
            status = getattr(getattr(r, "status", None), "value", None) or str(getattr(r, "status", ""))
            if status == "active":
                return r
        return None

    async def _first_any_rule(self, entity: str):
        try:
            rules = await self._mapping_rule_service.list_all(virtual_entity=entity)
        except Exception:
            return None
        return rules[0] if rules else None

    async def _check_backend(self, rule) -> Tuple[bool, str]:
        source_type = getattr(getattr(rule, "source_type", None), "value", None) or ""
        # FDW / SIMULATOR / ETL routed entities all live in the simulator
        if source_type in ("FDW", "ETL", "CDC"):
            from src.services.virtual_query_service import SCHEMA_TO_SIMULATOR
            schema = getattr(rule, "source_schema", None) or "external_sources"
            sim_key = SCHEMA_TO_SIMULATOR.get(schema, "external")
            sim = self._simulators.get(sim_key)
            if sim is None:
                return False, f"simulator '{sim_key}' not initialised"
            try:
                if hasattr(sim, "ensure_loaded"):
                    await sim.ensure_loaded()
            except Exception as e:
                return False, f"simulator load failed: {e}"
            if not getattr(sim, "loaded", False):
                return False, f"simulator '{sim_key}' not loaded"
            return True, "ok"

        if source_type == "MIMIR":
            if self._mimir is None or not getattr(self._mimir, "configured", False):
                return False, "Mimir client not configured (MIMIR_URL/MIMIR_ENABLED)"
            return True, "ok"

        if source_type == "ATHENA":
            if self._athena is None:
                return False, "Athena service not initialised"
            return True, "ok"

        return True, f"unknown source_type {source_type} - skipped pre-check"

    def _panel_result(
        self,
        panel_id: int,
        panel_title: str,
        panel_type: str,
        ref_id: str,
        entity: str,
        code: PanelCheckCode,
        rule_id: Optional[str] = None,
        source_type: Optional[str] = None,
        row_count: Optional[int] = None,
        latency_ms: Optional[int] = None,
        expected_fields: Optional[List[str]] = None,
        returned_fields: Optional[List[str]] = None,
        missing_fields: Optional[List[str]] = None,
        null_group_columns: Optional[List[str]] = None,
        error: Optional[str] = None,
        query_payload: Optional[Dict[str, Any]] = None,
    ) -> PanelDiagnostic:
        level = CODE_TO_LEVEL[code]
        suggest_detail = ""
        if code == PanelCheckCode.MISSING_COLUMNS:
            suggest_detail = ", ".join(missing_fields or [])
        elif code == PanelCheckCode.NULL_GROUP_KEYS:
            suggest_detail = ", ".join(null_group_columns or [])
        elif code == PanelCheckCode.SLOW_QUERY:
            suggest_detail = error or ""
        elif code in (PanelCheckCode.QUERY_ERROR, PanelCheckCode.BACKEND_UNREACHABLE):
            suggest_detail = error or ""

        return PanelDiagnostic(
            panelId=panel_id,
            panelTitle=panel_title,
            panelType=panel_type,
            targetRefId=ref_id,
            entity=entity,
            sourceType=source_type,
            ruleId=rule_id,
            status=level,
            code=code,
            latencyMs=latency_ms,
            rowCount=row_count,
            expectedFields=expected_fields or [],
            returnedFields=returned_fields or [],
            missingFields=missing_fields or [],
            nullGroupColumns=null_group_columns or [],
            errorMessage=error,
            suggestion=_suggest_for(code, entity, suggest_detail) if code != PanelCheckCode.OK else None,
            queryPayload=query_payload or {},
        )
