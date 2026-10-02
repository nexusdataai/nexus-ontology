"""
Dashboard Persistence Service

Stores dashboards in the Foundry Workspace DynamoDB table. The full dashboard
JSON is stored inline as a `payload` attribute on the META item. If a payload
exceeds DDB-friendly inline size, it is offloaded to S3 (when an S3 dashboards
bucket is configured) and only the s3Ref is kept on the DDB item.

The public API surface (create / get / update / delete / list_all / clone) is
preserved so the existing dashboard_api router does not need changes.
"""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
    dashboard_pk,
)

ds_logger = logger.bind(component="dashboard-service")

# Inline payload soft-cap. DDB max item size is 400KB; we keep headroom for
# meta attributes and DDB serialization overhead.
INLINE_PAYLOAD_MAX_BYTES = 350 * 1024


class DashboardService:

    def __init__(self, repository: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repository or FoundryWorkspaceRepository()
        self._s3_bucket = self._resolve_bucket()
        self._s3_prefix = os.getenv("DASHBOARD_S3_PREFIX", "dashboards/")
        self._use_s3_overflow = bool(self._s3_bucket)
        ds_logger.info(
            "Dashboard storage: DynamoDB",
            table=self._repo.table_name,
            s3_overflow_bucket=self._s3_bucket or "(disabled)",
        )

    @staticmethod
    def _resolve_bucket() -> str:
        env_val = os.getenv("DASHBOARD_S3_BUCKET", "")
        if env_val:
            return env_val
        try:
            from src.config.config_provider import get_config
            return get_config().s3_dashboards_bucket or ""
        except Exception:
            return ""

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def create(self, payload: dict, user: str = "anonymous") -> dict:
        uid = payload.get("uid") or str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        dashboard = {
            **payload,
            "uid": uid,
            "version": 1,
            "createdAt": now,
            "updatedAt": now,
            "createdBy": user,
        }
        await self._save(uid, dashboard)
        ds_logger.info("Dashboard created", uid=uid, title=payload.get("title"))
        return dashboard

    async def get(self, uid: str) -> Optional[dict]:
        return await self._load(uid)

    async def update(self, uid: str, payload: dict, user: str = "anonymous") -> dict:
        existing = await self._load(uid)
        if not existing:
            raise ValueError(f"Dashboard not found: {uid}")

        incoming_version = payload.get("version", 0)
        if incoming_version != 0 and incoming_version != existing.get("version", 0):
            raise ValueError(
                f"Version conflict: expected {existing.get('version')}, got {incoming_version}"
            )

        now = datetime.now(timezone.utc).isoformat()
        updated = {
            **payload,
            "uid": uid,
            "version": existing.get("version", 0) + 1,
            "createdAt": existing.get("createdAt", now),
            "updatedAt": now,
            "createdBy": existing.get("createdBy", user),
        }
        await self._save(uid, updated)
        ds_logger.info("Dashboard updated", uid=uid, version=updated["version"])
        return updated

    async def delete(self, uid: str) -> bool:
        item = self._repo.get_meta(dashboard_pk(uid))
        if item and item.get("s3Ref"):
            self._delete_s3_overflow(uid)
        try:
            self._repo.delete_pk(dashboard_pk(uid))
        except FoundryWorkspaceRepositoryError as e:
            ds_logger.warning(f"DDB delete failed for {uid}: {e}")
        return True

    async def list_all(self, search: str = "", tags: Optional[List[str]] = None) -> List[dict]:
        try:
            rows = self._repo.query_gsi1("DASHBOARD", scan_forward=False)
        except FoundryWorkspaceRepositoryError as e:
            ds_logger.warning(f"DDB list failed: {e}")
            rows = []

        dashboards: List[dict] = []
        for row in rows:
            try:
                dashboards.append(self._item_to_dashboard(row))
            except Exception as e:
                ds_logger.warning(f"Failed to hydrate dashboard {row.get('PK')}: {e}")

        if search:
            search_lower = search.lower()
            dashboards = [
                d for d in dashboards
                if search_lower in (d.get("title") or "").lower()
                or search_lower in (d.get("description") or "").lower()
            ]

        if tags:
            tag_set = set(tags)
            dashboards = [
                d for d in dashboards
                if tag_set.intersection(set(d.get("tags", [])))
            ]

        dashboards.sort(key=lambda d: d.get("updatedAt", ""), reverse=True)
        return dashboards

    async def clone(self, uid: str, user: str = "anonymous") -> dict:
        existing = await self._load(uid)
        if not existing:
            raise ValueError(f"Dashboard not found: {uid}")

        cloned = {
            **existing,
            "title": f"{existing.get('title', 'Dashboard')} (Copy)",
        }
        for k in ("uid", "version", "createdAt", "updatedAt"):
            cloned.pop(k, None)
        return await self.create(cloned, user=user)

    # -----------------------------------------------------------------------
    # Persistence helpers
    # -----------------------------------------------------------------------

    async def _save(self, uid: str, data: dict) -> None:
        title = data.get("title", "")
        description = data.get("description")
        tags = data.get("tags", []) or []
        panel_count = len(data.get("panels", []) or [])

        attrs: Dict[str, Any] = {
            "uid": uid,
            "title": title,
            "description": description,
            "tags": tags,
            "panelCount": panel_count,
            "version": data.get("version", 1),
            "createdAt": data.get("createdAt", ""),
            "updatedAt": data.get("updatedAt", ""),
            "createdBy": data.get("createdBy", ""),
        }

        payload_json = json.dumps(data, default=str)
        if len(payload_json.encode("utf-8")) > INLINE_PAYLOAD_MAX_BYTES and self._use_s3_overflow:
            s3_key = self._write_s3_overflow(uid, payload_json)
            attrs["s3Ref"] = f"s3://{self._s3_bucket}/{s3_key}"
            ds_logger.info("Dashboard payload offloaded to S3", uid=uid, key=s3_key)
        else:
            # Store as JSON string. DynamoDB's resource layer rejects Python
            # floats (panel JSON often contains float options/fieldConfig
            # values), and a single string attribute also avoids any nested
            # empty-set / mixed-type edge cases.
            attrs["payloadJson"] = payload_json

        try:
            self._repo.put_meta(
                pk=dashboard_pk(uid),
                attrs=attrs,
                gsi1pk="DASHBOARD",
                gsi1sk=data.get("updatedAt", ""),
            )
        except FoundryWorkspaceRepositoryError as e:
            ds_logger.error(f"DDB save failed for {uid}: {e}")
            raise

    async def _load(self, uid: str) -> Optional[dict]:
        item = self._repo.get_meta(dashboard_pk(uid))
        if not item:
            return None
        return self._item_to_dashboard(item)

    def _item_to_dashboard(self, item: Dict[str, Any]) -> dict:
        payload_json = item.get("payloadJson")
        if payload_json:
            try:
                return json.loads(payload_json)
            except Exception as e:
                ds_logger.warning(f"payloadJson parse failed for {item.get('uid')}: {e}")
        if "payload" in item and item["payload"] is not None:
            return self._normalize(item["payload"])
        s3_ref = item.get("s3Ref")
        if s3_ref and self._use_s3_overflow:
            try:
                payload = self._read_s3_overflow(s3_ref)
                if payload is not None:
                    return self._normalize(payload)
            except Exception as e:
                ds_logger.warning(f"S3 overflow read failed for {item.get('uid')}: {e}")

        # Fallback: hydrate the minimal projection from DDB attrs.
        return {
            "uid": item.get("uid") or str(item.get("PK", "")).split("#", 1)[-1],
            "title": item.get("title", ""),
            "description": item.get("description"),
            "tags": list(item.get("tags", []) or []),
            "panels": [],
            "time": {"from": "now-6h", "to": "now"},
            "variables": [],
            "version": int(item.get("version", 0) or 0),
            "createdAt": item.get("createdAt", ""),
            "updatedAt": item.get("updatedAt", ""),
            "createdBy": item.get("createdBy", ""),
        }

    @staticmethod
    def _normalize(value: Any) -> Any:
        """Convert DynamoDB Decimals back to ints/floats for JSON consumers."""
        if isinstance(value, list):
            return [DashboardService._normalize(v) for v in value]
        if isinstance(value, dict):
            return {k: DashboardService._normalize(v) for k, v in value.items()}
        if isinstance(value, Decimal):
            int_val = int(value)
            if Decimal(int_val) == value:
                return int_val
            return float(value)
        return value

    # -----------------------------------------------------------------------
    # S3 overflow helpers
    # -----------------------------------------------------------------------

    def _s3_client(self):
        import boto3
        return boto3.client("s3")

    def _write_s3_overflow(self, uid: str, body: str) -> str:
        key = f"{self._s3_prefix}{uid}.json"
        self._s3_client().put_object(
            Bucket=self._s3_bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
        return key

    def _read_s3_overflow(self, s3_ref: str) -> Optional[dict]:
        if not s3_ref.startswith("s3://"):
            return None
        without_scheme = s3_ref[len("s3://"):]
        bucket, _, key = without_scheme.partition("/")
        if not bucket or not key:
            return None
        resp = self._s3_client().get_object(Bucket=bucket, Key=key)
        return json.loads(resp["Body"].read())

    def _delete_s3_overflow(self, uid: str) -> None:
        if not self._use_s3_overflow:
            return
        try:
            key = f"{self._s3_prefix}{uid}.json"
            self._s3_client().delete_object(Bucket=self._s3_bucket, Key=key)
        except Exception as e:
            ds_logger.warning(f"S3 overflow delete failed for {uid}: {e}")
