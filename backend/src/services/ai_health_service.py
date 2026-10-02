"""
AI Health Central (AI-OPs plane, Phase 1)

Composes a top-level health snapshot across all five planes and persists it
to the ``{cap}-{env}-health`` DynamoDB table. Consumed by
``/api/v1/ai-health/*``.

Snapshot components:

- ``ai_ops`` : simulator load status + Redis warm-store key counts
- ``data``   : mapping rules count, VDL entities, connector API count,
               data plane count (all foundry-workspace queries)
- ``control``: pgvector row counts by content_type (Knowledge Index),
               Apache AGE availability, policy/workflow/integration counts
- ``reasoning``: ToolRegistry sizes (built-in + user), TOOLREG# count
- ``workspace``: solution/dashboard/view/journey/automation counts, RBAC
                 config presence

Each plane produces a ``{status, details, counts, verdict}`` dict, and a
top-level rollup summarises to ``healthy | degraded | unhealthy``.

The service also owns an internal asyncio loop that snapshots every
``AI_HEALTH_SNAPSHOT_INTERVAL_SECS`` (default 900 = 15 min). ``start()`` is
called once from gateway startup.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from loguru import logger

_RETENTION_DAYS = int(os.getenv("AI_HEALTH_RETENTION_DAYS", "90"))
_SNAPSHOT_INTERVAL = int(os.getenv("AI_HEALTH_SNAPSHOT_INTERVAL_SECS", "900"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AIHealthService:
    """Async facade + background snapshotter."""

    _instance: Optional["AIHealthService"] = None

    def __init__(self, table_name: Optional[str] = None):
        self._table_name = table_name or self._resolve_table_name()
        self._resource = self._build_resource()
        self._table = self._resource.Table(self._table_name)
        self._task: Optional[asyncio.Task] = None
        self._running = False
        logger.info(f"AIHealthService initialized: table={self._table_name}")

    # ------------------------------------------------------------------
    # Boilerplate
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AIHealthService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _resolve_table_name() -> str:
        try:
            from src.config.config_provider import get_config
            return get_config().dynamodb_health_table
        except Exception:
            from src.config.resource_naming import dynamodb_table_name
            return dynamodb_table_name("health")

    @staticmethod
    def _build_resource():
        try:
            from src.config.localstack_config import get_localstack_config, is_localstack_enabled
            if is_localstack_enabled():
                cfg = get_localstack_config()
                return boto3.resource(
                    "dynamodb",
                    endpoint_url=cfg.get_service_endpoint("dynamodb"),
                    region_name=cfg.region,
                    aws_access_key_id=cfg.access_key,
                    aws_secret_access_key=cfg.secret_key,
                )
        except Exception:
            pass
        endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL") or os.environ.get("AWS_ENDPOINT_URL_DYNAMODB")
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        if endpoint_url:
            return boto3.resource("dynamodb", endpoint_url=endpoint_url, region_name=region)
        return boto3.resource("dynamodb", region_name=region)

    # ------------------------------------------------------------------
    # Background snapshotter
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"AI Health snapshotter started (interval={_SNAPSHOT_INTERVAL}s)")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("AI Health snapshotter stopped")

    async def _loop(self) -> None:
        # First snapshot after a short warmup so gateway is fully wired.
        await asyncio.sleep(30)
        while self._running:
            try:
                await self.snapshot(scope="all")
            except Exception as e:
                logger.warning(f"AI Health snapshot failed: {e}")
            try:
                await asyncio.sleep(_SNAPSHOT_INTERVAL)
            except asyncio.CancelledError:
                break

    # ------------------------------------------------------------------
    # Snapshot composition
    # ------------------------------------------------------------------

    async def snapshot(self, scope: str = "all") -> Dict[str, Any]:
        """Compose a snapshot across the requested plane and persist it."""
        started = time.monotonic()
        planes: Dict[str, Any] = {}

        if scope in ("all", "ai_ops"):
            planes["ai_ops"] = await self._plane_ai_ops()
        if scope in ("all", "data"):
            planes["data"] = await self._plane_data()
        if scope in ("all", "control"):
            planes["control"] = await self._plane_control()
        if scope in ("all", "reasoning"):
            planes["reasoning"] = await self._plane_reasoning()
        if scope in ("all", "workspace"):
            planes["workspace"] = await self._plane_workspace()

        verdict = self._rollup(planes)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        snapshot = {
            "scope": scope,
            "iso_ts": _now_iso(),
            "elapsed_ms": elapsed_ms,
            "verdict": verdict,
            "planes": planes,
        }
        await self._persist(snapshot)
        return snapshot

    async def latest(self, scope: str = "all") -> Optional[Dict[str, Any]]:
        try:
            resp = self._table.query(
                KeyConditionExpression=Key("scope").eq(scope),
                ScanIndexForward=False,
                Limit=1,
            )
            items = resp.get("Items", [])
            return self._hydrate(items[0]) if items else None
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                return None
            logger.error(f"AI Health latest({scope}) failed: {e}")
            return None

    async def timeseries(
        self,
        scope: str = "all",
        since: Optional[datetime] = None,
        limit: int = 96,
    ) -> List[Dict[str, Any]]:
        cond = Key("scope").eq(scope)
        if since:
            cond = cond & Key("iso_ts").gte(since.astimezone(timezone.utc).isoformat())
        try:
            resp = self._table.query(
                KeyConditionExpression=cond,
                ScanIndexForward=False,
                Limit=max(1, min(limit, 500)),
            )
            return [self._hydrate(i) for i in resp.get("Items", [])]
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                return []
            logger.error(f"AI Health timeseries({scope}) failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Per-plane snapshotters (best-effort; never raises)
    # ------------------------------------------------------------------

    async def _plane_ai_ops(self) -> Dict[str, Any]:
        details: Dict[str, Any] = {}
        counts: Dict[str, Any] = {}
        errors: List[str] = []

        # Simulator metadata rows
        try:
            from src.services.simulator_fdw_client import (
                get_simulator_http_client,
                simulator_base_url,
            )
            base = simulator_base_url()
            if not base:
                raise RuntimeError("SIMULATOR_BASE_URL is not set")
            client = get_simulator_http_client()
            resp = await client.get(f"{base}/api/v1/simulators")
            catalog = resp.json() if resp.content else {}
            sims = catalog.get("items") or []
            counts["simulator_count"] = len(sims)
            details["simulators"] = [
                {
                    "service": s.get("service"),
                    "tableCount": s.get("table_count") or s.get("tableCount", 0),
                    "totalRowsHint": s.get("total_rows") or s.get("totalRowsHint", 0),
                    "lastLoadedFromS3At": s.get("dump_timestamp") or s.get("lastLoadedFromS3At"),
                }
                for s in sims
            ]
        except Exception as e:
            errors.append(f"simulator_meta: {e}")

        # Redis presence (best-effort)
        try:
            from src.services import redis_client
            ok = await redis_client.is_available()
            details["redis_ok"] = bool(ok)
        except Exception as e:
            details["redis_ok"] = False
            errors.append(f"redis: {e}")

        return self._verdict("ai_ops", details, counts, errors)

    async def _plane_data(self) -> Dict[str, Any]:
        details: Dict[str, Any] = {}
        counts: Dict[str, Any] = {}
        errors: List[str] = []
        try:
            from src.repositories.foundry_workspace_repository import (
                FoundryWorkspaceRepository,
            )
            repo = FoundryWorkspaceRepository()
            counts["data_plane"] = len(repo.list_data_planes())
            counts["data_source"] = len(repo.list_data_sources())
            counts["vdl_entities"] = len(repo.list_vdl_entities())
            counts["vdl_apis"] = len(repo.list_vdl_apis())
            counts["connector_apis"] = len(repo.list_conn_apis())
            counts["mapping_rules"] = len(repo.list_mapping_rules())
        except Exception as e:
            errors.append(f"foundry: {e}")
        return self._verdict("data", details, counts, errors)

    async def _plane_control(self) -> Dict[str, Any]:
        details: Dict[str, Any] = {}
        counts: Dict[str, Any] = {}
        errors: List[str] = []

        try:
            from src.repositories.foundry_workspace_repository import (
                FoundryWorkspaceRepository,
            )
            repo = FoundryWorkspaceRepository()
            counts["policies"] = len(repo.list_policies())
            counts["workflows"] = len(repo.list_workflow_defs())
            counts["integrations"] = len(repo.list_integration_defs())
            counts["knowledge_pipelines"] = len(repo.list_kps())
        except Exception as e:
            errors.append(f"foundry: {e}")

        # pgvector row count (best-effort)
        try:
            from src.services.control_plane.vector_store import VectorStore
            vs = VectorStore()
            n = await vs.count()  # type: ignore[attr-defined]
            counts["pgvector_rows"] = int(n or 0)
        except Exception as e:
            details["pgvector_ok"] = False
            errors.append(f"pgvector: {e}")
        else:
            details["pgvector_ok"] = True

        # Apache AGE presence (best-effort — presence check only)
        try:
            from src.services.control_plane.graph_store import GraphStore
            gs = GraphStore()
            details["age_available"] = bool(getattr(gs, "available", True))
        except Exception as e:
            details["age_available"] = False
            errors.append(f"age: {e}")

        return self._verdict("control", details, counts, errors)

    async def _plane_reasoning(self) -> Dict[str, Any]:
        details: Dict[str, Any] = {}
        counts: Dict[str, Any] = {}
        errors: List[str] = []
        try:
            from src.repositories.foundry_workspace_repository import (
                FoundryWorkspaceRepository,
            )
            repo = FoundryWorkspaceRepository()
            counts["tool_registry_rows"] = len(repo.list_tool_regs())
            # User-authored TOOL# rows via GSI
            counts["user_tools"] = len(repo.query_gsi1("TOOL"))
        except Exception as e:
            errors.append(f"foundry: {e}")
        return self._verdict("reasoning", details, counts, errors)

    async def _plane_workspace(self) -> Dict[str, Any]:
        details: Dict[str, Any] = {}
        counts: Dict[str, Any] = {}
        errors: List[str] = []
        try:
            from src.repositories.foundry_workspace_repository import (
                FoundryWorkspaceRepository,
            )
            repo = FoundryWorkspaceRepository()
            counts["solutions"] = len(repo.query_gsi1("SOLUTION"))
            counts["solution_yaml"] = len(repo.list_solution_yamls())
            counts["views"] = len(repo.query_gsi1("VIEW"))
            counts["dashboards"] = len(repo.query_gsi1("DASHBOARD"))
            counts["journeys"] = len(repo.query_gsi1("JOURNEY"))
            counts["automations"] = len(repo.list_automations())
        except Exception as e:
            errors.append(f"foundry: {e}")
        return self._verdict("workspace", details, counts, errors)

    @staticmethod
    def _verdict(
        plane: str,
        details: Dict[str, Any],
        counts: Dict[str, Any],
        errors: List[str],
    ) -> Dict[str, Any]:
        if errors and not counts:
            status = "unhealthy"
        elif errors:
            status = "degraded"
        else:
            status = "healthy"
        return {
            "plane": plane,
            "status": status,
            "counts": counts,
            "details": details,
            "errors": errors,
        }

    @staticmethod
    def _rollup(planes: Dict[str, Any]) -> str:
        if not planes:
            return "unknown"
        vals = [p.get("status", "unknown") for p in planes.values()]
        if any(v == "unhealthy" for v in vals):
            return "unhealthy"
        if any(v == "degraded" for v in vals):
            return "degraded"
        return "healthy"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _persist(self, snapshot: Dict[str, Any]) -> None:
        expires_at = int(datetime.now(timezone.utc).timestamp()) + _RETENTION_DAYS * 86400
        item: Dict[str, Any] = {
            "scope": snapshot["scope"],
            "iso_ts": snapshot["iso_ts"],
            "verdict": snapshot["verdict"],
            "elapsed_ms": snapshot["elapsed_ms"],
            "snapshotJson": json.dumps(snapshot, default=str),
            "expires_at": expires_at,
        }
        try:
            self._table.put_item(Item=item)
        except ClientError as e:
            logger.warning(f"AI Health persist failed: {e}")

    @staticmethod
    def _hydrate(item: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(item)
        raw = out.pop("snapshotJson", None)
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
                # merge inner planes back to top-level so callers get a
                # symmetric shape whether they read latest() or snapshot().
                out.update({k: v for k, v in data.items() if k not in out})
            except Exception:
                pass
        return out


def get_ai_health_service() -> AIHealthService:
    return AIHealthService.get_instance()
