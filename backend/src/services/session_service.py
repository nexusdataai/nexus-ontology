"""
DynamoDB-backed Session Service

Replaces in-memory session storage with DynamoDB for cross-pod persistence.
Sessions have a 12-hour TTL enforced by DynamoDB TTL.
"""

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from ..config.config_provider import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


SESSION_TTL_SECONDS = 12 * 60 * 60  # 12 hours


class SessionService:
    """Manages user sessions in DynamoDB."""

    def __init__(self):
        self._ddb = None
        self._table_name = None
        self._config = get_config() if CONFIG_AVAILABLE else None
        self._ensure_table_exists = False

    @property
    def _table(self):
        if self._ddb is None and BOTO3_AVAILABLE:
            region = self._config.aws_region if self._config else os.getenv("AWS_REGION", "us-east-1")
            self._ddb = boto3.resource("dynamodb", region_name=region)
        cap = os.getenv("CAPABILITY_NAME", "call-processing")
        env = os.getenv("ENVIRONMENT", "prod")
        self._table_name = f"{cap}-{env}-sessions"
        table = self._ddb.Table(self._table_name)

        if not self._ensure_table_exists:
            self._create_table_if_missing()
            self._ensure_table_exists = True

        return table

    def _create_table_if_missing(self):
        try:
            self._ddb.meta.client.describe_table(TableName=self._table_name)
        except Exception:
            try:
                self._ddb.create_table(
                    TableName=self._table_name,
                    KeySchema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
                    AttributeDefinitions=[{"AttributeName": "session_id", "AttributeType": "S"}],
                    BillingMode="PAY_PER_REQUEST",
                )
                waiter = self._ddb.meta.client.get_waiter("table_exists")
                waiter.wait(TableName=self._table_name, WaiterConfig={"Delay": 2, "MaxAttempts": 30})
                self._ddb.meta.client.update_time_to_live(
                    TableName=self._table_name,
                    TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at_epoch"},
                )
                logger.info(f"Created sessions table: {self._table_name}")
            except Exception as e:
                logger.warning(f"Could not create sessions table: {e}")

    def create_session(
        self,
        user_sub: str,
        email: str,
        role: str,
        permissions: List[str],
        groups: List[str],
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new session and return the session_id."""
        session_id = str(uuid.uuid4())
        now = int(time.time())
        expires = now + SESSION_TTL_SECONDS

        item = {
            "session_id": session_id,
            "user_sub": user_sub,
            "email": email,
            "role": role,
            "permissions": permissions,
            "groups": groups,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_active": now,
            "expires_at_epoch": expires,
        }
        if extra:
            item.update(extra)

        try:
            self._table.put_item(Item=item)
            logger.debug(f"Session created: {session_id[:8]}... for {email}")
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and validate a session. Returns None if expired or missing."""
        if not session_id:
            return None
        try:
            resp = self._table.get_item(Key={"session_id": session_id})
            item = resp.get("Item")
            if not item:
                return None
            if int(item.get("expires_at_epoch", 0)) < int(time.time()):
                self.delete_session(session_id)
                return None
            # Update last_active
            try:
                self._table.update_item(
                    Key={"session_id": session_id},
                    UpdateExpression="SET last_active = :now",
                    ExpressionAttributeValues={":now": int(time.time())},
                )
            except Exception:
                pass
            return item
        except Exception as e:
            logger.warning(f"Session lookup failed: {e}")
            return None

    def delete_session(self, session_id: str) -> None:
        """Delete a session (logout)."""
        try:
            self._table.delete_item(Key={"session_id": session_id})
        except Exception as e:
            logger.warning(f"Session delete failed: {e}")

    def delete_user_sessions(self, user_sub: str) -> None:
        """Delete all sessions for a user (force logout)."""
        try:
            resp = self._table.scan(
                FilterExpression="user_sub = :sub",
                ExpressionAttributeValues={":sub": user_sub},
                ProjectionExpression="session_id",
            )
            for item in resp.get("Items", []):
                self._table.delete_item(Key={"session_id": item["session_id"]})
        except Exception as e:
            logger.warning(f"Bulk session delete failed: {e}")


_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
