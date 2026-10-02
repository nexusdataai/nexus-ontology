"""
ResultSink - unified writer for journey-emitted result entities.

Encapsulates the three storage targets used by the Solution Four Views
expansion (see plan section 3.2 / 3.6):

  * write_metric(...)            -> Mimir (TSDB) via remote_write
  * write_rows(...)              -> S3 partitioned JSON (Athena-queryable)
  * write_simulator_table(...)   -> Redis-backed simulator (existing path)

In addition, each writer auto-creates the matching VDL mapping rule the
first time an entity is written so dashboards can immediately query it
through `/api/v1/dashboard/query`.

The sink degrades gracefully:

- If Mimir is unreachable / disabled, write_metric is a no-op (logs a
  warning) and journeys can still proceed - the equivalent rows-shape
  data lands in the simulator/Athena via write_rows / write_simulator_table.
- If the S3 client / bucket env are not set, write_rows skips the S3 write
  but still stores in the simulator (so dashboards see the data).
- If the mapping-rule service is not initialised, mapping creation is
  skipped silently.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from loguru import logger

from src.services.mimir_client import MimirRemoteWriteClient, Sample, get_default_mimir_client

sink_logger = logger.bind(component="result-sink")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ymd_now() -> Dict[str, str]:
    now = datetime.now(timezone.utc)
    return {"year": now.strftime("%Y"), "month": now.strftime("%m"), "day": now.strftime("%d")}


class ResultSink:
    """
    Per-journey writer instance.

    Construct once per journey run with the run's job_id / journey_id /
    boto3 S3 client / config so all writes carry consistent metadata.

    Usage::

        sink = ResultSink(job_id=jid, journey_id=jrn, s3_client=s3, config=cfg)
        await sink.write_metric("o2c_dso", labels={"region":"EMEA"}, value=34.2)
        await sink.write_rows("O2C_Action_Log", rows=[...], partition="2026/05/03")
        await sink.write_simulator_table("external_sources", "O2C_KPI_Snapshot", rows=[...])
    """

    DEFAULT_SCHEMA = "external_sources"

    def __init__(
        self,
        job_id: str = "",
        journey_id: str = "",
        s3_client: Any = None,
        config: Any = None,
        mimir_client: Optional[MimirRemoteWriteClient] = None,
        mapping_service: Any = None,
        simulators: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.job_id = job_id
        self.journey_id = journey_id
        self._s3 = s3_client
        self._config = config
        self._mimir = mimir_client or get_default_mimir_client()
        self._mapping_service = mapping_service
        self._simulators = simulators or {}
        self._mapping_rules_created: set = set()

    # ------------------------------------------------------------------
    # Mimir (metric-shaped history)
    # ------------------------------------------------------------------

    async def write_metric(
        self,
        metric: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        timestamp_ms: Optional[int] = None,
        tenant_id: Optional[str] = None,
        virtual_entity: Optional[str] = None,
        label_map: Optional[Dict[str, str]] = None,
    ) -> bool:
        return await self.write_metric_batch(
            [Sample(metric=metric, labels=dict(labels or {}), value=float(value), timestamp_ms=timestamp_ms)],
            tenant_id=tenant_id,
            virtual_entity=virtual_entity,
            label_map=label_map,
        )

    async def write_metric_batch(
        self,
        samples: Iterable[Sample],
        tenant_id: Optional[str] = None,
        virtual_entity: Optional[str] = None,
        label_map: Optional[Dict[str, str]] = None,
    ) -> bool:
        sample_list = list(samples)
        if not sample_list:
            return True

        # Always mirror the samples as flat rows in the Redis simulator. This
        # keeps the simulator-mode VDL adapter populated even when Mimir is
        # disabled or unreachable, AND gives the production-mode Mimir
        # adapter a reproducible queryable cache.
        if virtual_entity:
            row_table = virtual_entity
        else:
            row_table = sample_list[0].metric
        rows = []
        for s in sample_list:
            row = dict(s.labels or {})
            row["value"] = s.value
            row["timestamp"] = s.timestamp_ms
            rows.append(row)
        try:
            await self.write_simulator_table(self.DEFAULT_SCHEMA, row_table, rows)
        except Exception as e:
            sink_logger.debug("Mirror to simulator failed for {}: {}", row_table, e)

        ok = await self._mimir.write_samples(sample_list, tenant_id=tenant_id)
        # Only register the MIMIR mapping rule in production-storage mode.
        # In simulator mode (the default) the catalogue routes the entity
        # through FDW; auto-creating a competing MIMIR rule here causes the
        # VDL to pick the unreachable Mimir backend over the populated
        # simulator mirror.
        if virtual_entity and os.getenv("SOLUTION_STORAGE_MODE", "simulator").lower() == "production":
            metric_name = sample_list[0].metric
            await self._ensure_mimir_mapping_rule(virtual_entity, metric_name, label_map or {})
        return ok

    # ------------------------------------------------------------------
    # S3 + Athena (relational rows)
    # ------------------------------------------------------------------

    async def write_rows(
        self,
        entity: str,
        rows: List[Dict[str, Any]],
        prefix: Optional[str] = None,
        bucket: Optional[str] = None,
        register_glue: bool = True,
        virtual_entity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persist `rows` as a single JSON object under
        ``s3://<bucket>/<prefix>/year=YYYY/month=MM/day=DD/<entity>_<job_id>.json``.

        Returns ``{"s3": "...", "rows": N, "skipped": bool}``. Always also
        writes to the simulator (so the demo dashboards still see the data
        even when no S3 bucket is configured) - see write_simulator_table.
        """
        if not rows:
            return {"s3": None, "rows": 0, "skipped": True, "reason": "empty"}

        sim_count = await self.write_simulator_table(self.DEFAULT_SCHEMA, entity, rows)

        bucket = bucket or self._resolve_bucket()
        if not bucket or not self._s3:
            return {"s3": None, "rows": sim_count, "skipped": True, "reason": "no_bucket_or_s3"}

        ymd = _ymd_now()
        prefix = prefix or self._default_prefix(entity)
        key = (
            f"{prefix.rstrip('/')}"
            f"/year={ymd['year']}/month={ymd['month']}/day={ymd['day']}"
            f"/{entity}_{self.job_id or 'manual'}.json"
        )
        try:
            self._s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps({"rows": rows, "job_id": self.job_id, "written_at": _now_iso()}, default=str),
                ContentType="application/json",
            )
            sink_logger.info("Wrote {} rows of {} to s3://{}/{}", len(rows), entity, bucket, key)
        except Exception as e:
            sink_logger.warning("S3 put_object failed for {}: {}", entity, e)
            return {"s3": None, "rows": sim_count, "skipped": True, "reason": str(e)}

        if register_glue:
            try:
                await self._register_glue_partition(entity, bucket, prefix, ymd)
            except Exception as e:
                sink_logger.warning("Glue partition register failed for {} (non-fatal): {}", entity, e)

        if virtual_entity:
            await self._ensure_athena_mapping_rule(virtual_entity, entity, sample_row=rows[0])

        return {"s3": f"s3://{bucket}/{key}", "rows": len(rows), "skipped": False}

    # ------------------------------------------------------------------
    # Redis-backed simulator (small lookup tables, demo data)
    # ------------------------------------------------------------------

    async def write_simulator_table(
        self,
        schema: str,
        table: str,
        rows: List[Dict[str, Any]],
        virtual_entity: Optional[str] = None,
    ) -> int:
        """
        Replace the (schema, table) contents inside the matching simulator
        through ``BaseSimulatorService.write_table``. Returns the row count.
        """
        sim = self._resolve_simulator(schema)
        if sim is None:
            sink_logger.debug("No simulator available for schema {} - dropping table {}", schema, table)
            return 0
        if hasattr(sim, "ensure_loaded"):
            try:
                await sim.ensure_loaded()
            except Exception:
                pass
        if not hasattr(sim, "write_table"):
            sink_logger.warning(
                "Simulator for schema {} has no write_table() method - skipping {}", schema, table
            )
            return 0
        try:
            count = await sim.write_table(schema, table, rows)
            sink_logger.debug("Stored {} rows in simulator {}.{}", count, schema, table)
        except Exception as e:
            sink_logger.warning("Simulator write_table failed for {}.{}: {}", schema, table, e)
            return 0

        if virtual_entity:
            await self._ensure_simulator_mapping_rule(virtual_entity, schema, table, sample_row=rows[0] if rows else None)

        return count

    async def append_simulator_rows(
        self,
        schema: str,
        table: str,
        rows: List[Dict[str, Any]],
    ) -> int:
        sim = self._resolve_simulator(schema)
        if sim is None or not hasattr(sim, "append_rows"):
            return await self.write_simulator_table(schema, table, rows)
        try:
            return await sim.append_rows(schema, table, rows)
        except Exception as e:
            sink_logger.warning("Simulator append_rows failed for {}.{}: {}", schema, table, e)
            return 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_bucket(self) -> str:
        bucket = ""
        if self._config:
            bucket = (
                getattr(self._config, "solution_results_bucket", "")
                or getattr(self._config, "s3_recordings_bucket", "")
            )
        if not bucket:
            bucket = (
                os.getenv("SOLUTION_RESULTS_BUCKET", "")
                or os.getenv("S3_RECORDINGS_BUCKET", "")
            )
        return bucket

    def _default_prefix(self, entity: str) -> str:
        # snake-case partition prefix, e.g. O2C_Action_Log -> o2c_action_log
        return f"solution-results/{entity.lower()}"

    def _resolve_simulator(self, schema: str):
        if not self._simulators:
            try:
                from src.apis.fdw_api import _simulators as fdw_sims
                self._simulators = fdw_sims
            except Exception:
                self._simulators = {}
        from src.services.virtual_query_service import SCHEMA_TO_SIMULATOR
        sim_key = SCHEMA_TO_SIMULATOR.get(schema, "external")
        return self._simulators.get(sim_key)

    async def _register_glue_partition(self, entity: str, bucket: str, prefix: str, ymd: Dict[str, str]) -> None:
        # Light Glue partition registration. Reuses O2CGlueCatalog if present;
        # otherwise no-op so the journey still succeeds.
        try:
            from src.stages.order_to_cash.o2c_glue_catalog import O2CGlueCatalog
        except Exception:
            return
        try:
            glue = O2CGlueCatalog(
                region_name=getattr(self._config, "aws_region", os.getenv("AWS_REGION", "us-east-1")),
                database_name=getattr(self._config, "glue_database_name", os.getenv("GLUE_DATABASE", "")),
            )
            table_name = entity.lower()
            partition_path = f"{prefix.rstrip('/')}/year={ymd['year']}/month={ymd['month']}/day={ymd['day']}/"
            if hasattr(glue, "ensure_table"):
                glue.ensure_table(bucket, table_name)
            if hasattr(glue, "add_partition"):
                glue.add_partition(table_name, bucket, partition_path, ymd["year"], ymd["month"], ymd["day"])
        except Exception as e:
            sink_logger.debug("Glue partition register skipped for {}: {}", entity, e)

    async def _ensure_mimir_mapping_rule(
        self,
        virtual_entity: str,
        metric_name: str,
        label_map: Dict[str, str],
    ) -> None:
        cache_key = f"MIMIR:{virtual_entity}"
        if cache_key in self._mapping_rules_created:
            return
        svc = await self._resolve_mapping_service()
        if svc is None:
            return
        try:
            existing = await svc.list_all(virtual_entity=virtual_entity)
            if any(r.source_type.value == "MIMIR" for r in existing):
                self._mapping_rules_created.add(cache_key)
                return
            from src.models.mapping_rule_models import (
                MappingRuleCreateRequest, MappingRuleUpdateRequest,
                MappingRuleSourceType, MappingRuleStatus, FieldMap,
            )
            field_maps = [FieldMap(source_field=src, target_field=tgt) for tgt, src in label_map.items()]
            field_maps.append(FieldMap(source_field="__value__", target_field="value"))
            field_maps.append(FieldMap(source_field="__timestamp__", target_field="timestamp"))
            business_logic = json.dumps({
                "label_map": label_map,
                "default_aggregation": "avg",
                "default_step_seconds": 3600,
                "default_lookback_seconds": 7 * 24 * 3600,
                "tenant_resolver": "fixed:" + (self._mimir.tenant_id if self._mimir else "nexus-default"),
            })
            rule = await svc.create(MappingRuleCreateRequest(
                name=f"Auto Mimir: {virtual_entity}",
                virtual_entity=virtual_entity,
                source_type=MappingRuleSourceType.MIMIR,
                source_system="mimir",
                source_table=metric_name,
                source_schema="mimir",
                field_maps=field_maps,
                business_logic=business_logic,
            ))
            await svc.update(rule.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
            self._mapping_rules_created.add(cache_key)
            sink_logger.info("Created Mimir VDL mapping rule for {} -> {}", virtual_entity, metric_name)
        except Exception as e:
            sink_logger.warning("Mimir mapping rule create failed for {}: {}", virtual_entity, e)

    async def _ensure_athena_mapping_rule(
        self,
        virtual_entity: str,
        glue_table: str,
        sample_row: Dict[str, Any],
    ) -> None:
        cache_key = f"ATHENA:{virtual_entity}"
        if cache_key in self._mapping_rules_created:
            return
        svc = await self._resolve_mapping_service()
        if svc is None:
            return
        try:
            existing = await svc.list_all(virtual_entity=virtual_entity)
            if any(r.source_type.value == "ATHENA" for r in existing):
                self._mapping_rules_created.add(cache_key)
                return
            from src.models.mapping_rule_models import (
                MappingRuleCreateRequest, MappingRuleUpdateRequest,
                MappingRuleSourceType, MappingRuleStatus, FieldMap,
            )
            fields = list(sample_row.keys()) if sample_row else []
            field_maps = [FieldMap(source_field=f, target_field=f) for f in fields]
            db = getattr(self._config, "glue_database_name", "") or os.getenv("GLUE_DATABASE", "default")
            rule = await svc.create(MappingRuleCreateRequest(
                name=f"Auto Athena: {virtual_entity}",
                virtual_entity=virtual_entity,
                source_type=MappingRuleSourceType.ATHENA,
                source_system="athena",
                source_table=glue_table.lower(),
                source_schema=db,
                field_maps=field_maps,
            ))
            await svc.update(rule.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
            self._mapping_rules_created.add(cache_key)
        except Exception as e:
            sink_logger.warning("Athena mapping rule create failed for {}: {}", virtual_entity, e)

    async def _ensure_simulator_mapping_rule(
        self,
        virtual_entity: str,
        schema: str,
        table: str,
        sample_row: Optional[Dict[str, Any]],
    ) -> None:
        cache_key = f"SIM:{virtual_entity}"
        if cache_key in self._mapping_rules_created:
            return
        svc = await self._resolve_mapping_service()
        if svc is None:
            return
        try:
            existing = await svc.list_all(virtual_entity=virtual_entity)
            if any(r.source_type.value == "FDW" for r in existing):
                self._mapping_rules_created.add(cache_key)
                return
            from src.models.mapping_rule_models import (
                MappingRuleCreateRequest, MappingRuleUpdateRequest,
                MappingRuleSourceType, MappingRuleStatus, FieldMap,
            )
            fields = list(sample_row.keys()) if sample_row else []
            field_maps = [FieldMap(source_field=f, target_field=f) for f in fields]
            rule = await svc.create(MappingRuleCreateRequest(
                name=f"Auto Sim: {virtual_entity}",
                virtual_entity=virtual_entity,
                source_type=MappingRuleSourceType.FDW,
                source_system=schema,
                source_table=table,
                source_schema=schema,
                field_maps=field_maps,
            ))
            await svc.update(rule.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
            self._mapping_rules_created.add(cache_key)
        except Exception as e:
            sink_logger.warning("Simulator mapping rule create failed for {}: {}", virtual_entity, e)

    async def _resolve_mapping_service(self):
        if self._mapping_service is not None:
            return self._mapping_service
        try:
            from src.apis.mapping_rule_api import _service as mr_service
            self._mapping_service = mr_service
        except Exception:
            self._mapping_service = None
        return self._mapping_service
