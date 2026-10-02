"""
Audit Logger for the AI Control Plane.

Logs every agent action (tool invocations, policy decisions, final answers)
to DynamoDB for compliance and traceability.  Each agent run creates a
session record; each tool call within that session is logged as an item.

Table: control-plane-audit (operator-provisioned; falls back to silent no-op
                            if the table is missing).
  PK: session_id (UUID string)
  SK: step (zero-padded 4-digit string, e.g. "0001")
"""

import os
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

cp_logger = logger.bind(component="control-plane")

TABLE_NAME = os.getenv("CONTROL_PLANE_AUDIT_TABLE", "control-plane-audit")


class AuditLogger:
    """Logs agent actions to DynamoDB for compliance."""

    def __init__(self):
        self._table = None
        self._session_id: Optional[str] = None
        self._step_counter = 0
        self._region = os.getenv("AWS_REGION", "us-east-1")

    def start_session(self, question: str, user: str = "anonymous", intent_risk: str = "read_only") -> str:
        self._session_id = str(uuid.uuid4())
        self._step_counter = 0
        self._log_item({
            "event": "session_start",
            "question": question[:500],
            "user": user,
            "intent_risk": intent_risk,
        })
        return self._session_id

    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result_preview: str = "",
        duration_ms: float = 0,
        policy_result: str = "allowed",
    ) -> None:
        self._log_item({
            "event": "tool_call",
            "tool": tool_name,
            "arguments": _truncate(str(arguments), 500),
            "result_preview": _truncate(result_preview, 300),
            "duration_ms": round(duration_ms, 1),
            "policy_result": policy_result,
        })

    def log_policy_violation(self, tool_name: str, reason: str, policy: str) -> None:
        self._log_item({
            "event": "policy_violation",
            "tool": tool_name,
            "reason": reason,
            "policy": policy,
        })

    def log_final_answer(self, answer_preview: str, total_steps: int, total_tokens: int) -> None:
        self._log_item({
            "event": "session_end",
            "answer_preview": _truncate(answer_preview, 300),
            "total_steps": total_steps,
            "total_tokens": total_tokens,
        })

    def _log_item(self, data: Dict[str, Any]) -> None:
        self._step_counter += 1
        item = {
            "session_id": self._session_id or "unknown",
            "step": f"{self._step_counter:04d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }

        cp_logger.info(f"Audit: {item.get('event', '?')} | {item.get('tool', '-')}")

        if not BOTO3_AVAILABLE:
            return
        try:
            table = self._get_table()
            if table:
                table.put_item(Item=_sanitize_dynamo(item))
        except Exception as e:
            cp_logger.debug(f"Audit write skipped: {e}")

    def _get_table(self):
        if self._table is not None:
            return self._table
        try:
            dynamodb = boto3.resource("dynamodb", region_name=self._region)
            self._table = dynamodb.Table(TABLE_NAME)
            self._table.load()
            return self._table
        except Exception:
            self._table = False
            return None


def _truncate(s: str, max_len: int) -> str:
    return s[:max_len] + "..." if len(s) > max_len else s


def _sanitize_dynamo(item: Dict[str, Any]) -> Dict[str, Any]:
    """Remove empty strings and convert floats for DynamoDB."""
    from decimal import Decimal
    clean = {}
    for k, v in item.items():
        if isinstance(v, str) and v == "":
            continue
        if isinstance(v, float):
            clean[k] = Decimal(str(round(v, 2)))
        elif isinstance(v, dict):
            clean[k] = _sanitize_dynamo(v)
        else:
            clean[k] = v
    return clean
