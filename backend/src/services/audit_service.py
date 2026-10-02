"""
Audit Logging Service

Logs security-relevant events (login, MFA, role changes, user management)
to a DynamoDB table for compliance and monitoring.
"""

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class AuditEvent:
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    MFA_VERIFIED = "MFA_VERIFIED"
    MFA_SETUP = "MFA_SETUP"
    MFA_FAILED = "MFA_FAILED"
    USER_CREATED = "USER_CREATED"
    USER_DISABLED = "USER_DISABLED"
    ROLE_CHANGED = "ROLE_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    LOGOUT = "LOGOUT"
    BYPASS_ATTEMPT = "BYPASS_ATTEMPT"
    PERMISSION_DENIED = "PERMISSION_DENIED"


class AuditService:
    """Writes audit events to DynamoDB."""

    def __init__(self):
        self._ddb = None
        self._table_name = None
        self._table_ready = False

    @property
    def _table(self):
        if self._ddb is None and BOTO3_AVAILABLE:
            region = os.getenv("AWS_REGION", "us-east-1")
            self._ddb = boto3.resource("dynamodb", region_name=region)
        cap = os.getenv("CAPABILITY_NAME", "call-processing")
        env = os.getenv("ENVIRONMENT", "prod")
        self._table_name = f"{cap}-{env}-audit-log"
        table = self._ddb.Table(self._table_name)

        if not self._table_ready:
            self._create_table_if_missing()
            self._table_ready = True

        return table

    def _create_table_if_missing(self):
        try:
            self._ddb.meta.client.describe_table(TableName=self._table_name)
        except Exception:
            try:
                self._ddb.create_table(
                    TableName=self._table_name,
                    KeySchema=[
                        {"AttributeName": "event_id", "KeyType": "HASH"},
                        {"AttributeName": "timestamp", "KeyType": "RANGE"},
                    ],
                    AttributeDefinitions=[
                        {"AttributeName": "event_id", "AttributeType": "S"},
                        {"AttributeName": "timestamp", "AttributeType": "N"},
                    ],
                    BillingMode="PAY_PER_REQUEST",
                )
                waiter = self._ddb.meta.client.get_waiter("table_exists")
                waiter.wait(TableName=self._table_name, WaiterConfig={"Delay": 2, "MaxAttempts": 30})
                logger.info(f"Created audit log table: {self._table_name}")
            except Exception as e:
                logger.warning(f"Could not create audit table: {e}")

    def log(
        self,
        action: str,
        user_email: str = "",
        details: Optional[Dict[str, Any]] = None,
        ip_address: str = "",
        user_agent: str = "",
        success: bool = True,
    ) -> None:
        """Log an audit event. Fire-and-forget — never raises."""
        try:
            item = {
                "event_id": str(uuid.uuid4()),
                "timestamp": int(time.time() * 1000),
                "action": action,
                "user_email": user_email,
                "success": success,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "iso_time": datetime.now(timezone.utc).isoformat(),
                "details": details or {},
            }
            self._table.put_item(Item=item)
        except Exception as e:
            logger.warning(f"Audit log write failed: {e}")

    def get_recent(self, limit: int = 50) -> list:
        """Get recent audit events (for admin dashboard)."""
        try:
            resp = self._table.scan(Limit=limit)
            items = resp.get("Items", [])
            items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            return items[:limit]
        except Exception as e:
            logger.warning(f"Audit log read failed: {e}")
            return []


_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
