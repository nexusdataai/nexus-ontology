"""
Diagnostics history persistence (AI-OPs plane, Phase 1)

Small async facade over the dedicated ``{cap}-{env}-diagnostics`` DynamoDB
table. Diagnostic route modules call ``record()`` after computing their
result; the ``/api/v1/diagnostics/history`` endpoint reads it back.

Table schema (provisioned by kube-operator):

    HASH  scope     string   e.g. "o2c", "simulators", "react-tools",
                               "automation", "virtual-data", "dashboard",
                               "connector-apis"
    RANGE run_id    string   ISO ts + short uuid, monotonic-ish

Optional TTL attr ``expires_at`` (epoch seconds, 30 days by default) lets
DynamoDB auto-prune old rows if TTL is enabled on the table.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from loguru import logger


_RETENTION_DAYS = int(os.getenv("DIAGNOSTICS_RETENTION_DAYS", "30"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_run_id() -> str:
    return f"{_now_iso()}#{uuid.uuid4().hex[:8]}"


class DiagnosticsHistoryService:
    """Async CRUD facade for the diagnostics history table."""

    def __init__(self, table_name: Optional[str] = None):
        self._table_name = table_name or self._resolve_table_name()
        self._resource = self._build_resource()
        self._table = self._resource.Table(self._table_name)
        logger.info(f"DiagnosticsHistoryService initialized: table={self._table_name}")

    @staticmethod
    def _resolve_table_name() -> str:
        try:
            from src.config.config_provider import get_config
            return get_config().dynamodb_diagnostics_table
        except Exception:
            from src.config.resource_naming import dynamodb_table_name
            return dynamodb_table_name("diagnostics")

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

    @property
    def table_name(self) -> str:
        return self._table_name

    async def record(
        self,
        scope: str,
        result: Any,
        *,
        summary: Optional[Dict[str, Any]] = None,
        succeeded: Optional[bool] = None,
    ) -> str:
        """Persist a diagnostic run and return the assigned ``run_id``.

        ``result`` may be any JSON-serialisable value; large blobs are stored
        as a serialized string under ``resultJson``.
        """
        run_id = _new_run_id()
        try:
            payload_json = json.dumps(result, default=str)
        except Exception as e:
            logger.warning(f"DiagnosticsHistory record({scope}) serialize failed: {e}")
            payload_json = json.dumps({"error": f"serialize failed: {e}"})

        expires_at = int(datetime.now(timezone.utc).timestamp()) + _RETENTION_DAYS * 86400

        item: Dict[str, Any] = {
            "scope": scope,
            "run_id": run_id,
            "recordedAt": _now_iso(),
            "resultJson": payload_json,
            "expires_at": expires_at,
        }
        if summary:
            item["summary"] = summary
        if succeeded is not None:
            item["succeeded"] = bool(succeeded)

        try:
            self._table.put_item(Item=item)
        except ClientError as e:
            logger.warning(f"DiagnosticsHistory record({scope}) DDB write failed: {e}")
        return run_id

    async def list(self, scope: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            resp = self._table.query(
                KeyConditionExpression=Key("scope").eq(scope),
                ScanIndexForward=False,  # newest first
                Limit=max(1, min(limit, 500)),
            )
            return [self._hydrate(i) for i in resp.get("Items", [])]
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                return []
            logger.error(f"DiagnosticsHistory list({scope}) failed: {e}")
            return []

    async def get(self, scope: str, run_id: str) -> Optional[Dict[str, Any]]:
        try:
            resp = self._table.get_item(Key={"scope": scope, "run_id": run_id})
            item = resp.get("Item")
            return self._hydrate(item) if item else None
        except ClientError as e:
            logger.error(f"DiagnosticsHistory get({scope},{run_id}) failed: {e}")
            return None

    async def scopes(self) -> List[str]:
        """Best-effort distinct scope list.

        DynamoDB has no cheap distinct so this scans; safe for the low
        row-count expected here but callers should cache.
        """
        seen: List[str] = []
        try:
            last_key = None
            while True:
                kwargs: Dict[str, Any] = {"ProjectionExpression": "#s", "ExpressionAttributeNames": {"#s": "scope"}}
                if last_key:
                    kwargs["ExclusiveStartKey"] = last_key
                resp = self._table.scan(**kwargs)
                for it in resp.get("Items", []):
                    s = it.get("scope")
                    if s and s not in seen:
                        seen.append(s)
                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break
        except ClientError as e:
            logger.debug(f"DiagnosticsHistory scopes scan failed: {e}")
        return sorted(seen)

    @staticmethod
    def _hydrate(item: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ``resultJson`` back into a dict for callers."""
        out = dict(item)
        raw = out.pop("resultJson", None)
        if isinstance(raw, str):
            try:
                out["result"] = json.loads(raw)
            except Exception:
                out["result"] = raw
        return out


# Module-level singleton (lazy)
_singleton: Optional[DiagnosticsHistoryService] = None


def get_diagnostics_history_service() -> DiagnosticsHistoryService:
    global _singleton
    if _singleton is None:
        _singleton = DiagnosticsHistoryService()
    return _singleton


async def record_diagnostic(scope: str, result: Any, **kwargs: Any) -> str:
    """Convenience wrapper for callers that don't want to hold a service handle."""
    return await get_diagnostics_history_service().record(scope, result, **kwargs)
