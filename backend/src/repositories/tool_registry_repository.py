"""
Tool Registry Repository.

DynamoDB single-table access layer for user-authored ReAct tools. Reuses
the existing Foundry-workspace table layout (same PK/SK + GSI1 pattern
as Solutions / Views / Dashboards / Journeys) so we don't introduce new
infra.

Item layout:

| Entity              | PK                  | SK                  | GSI1PK         | GSI1SK                  |
|---------------------|---------------------|---------------------|----------------|-------------------------|
| Tool metadata       | TOOL#{tool_id}      | META                | TOOL           | {updatedAt}             |
| Tool version snap.  | TOOL#{tool_id}      | VERSION#{:06d}      | TOOL_VERSION   | {tool_id}#{:06d}        |
| Tool tag link       | TOOL#{tool_id}      | TAG#{tag}           | TAG#{tag}      | TOOL#{tool_id}          |

Each version row carries a full source-code snapshot + sha256 so we can
diff and restore. The META row carries the *current* source for fast
boot-time loading by ``DynamicToolLoader``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError
from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
    tool_pk,
    tool_tag_sk,
    tool_version_sk,
)


class ToolRegistryRepositoryError(Exception):
    """Raised on tool-registry repository failures."""


class ToolRegistryRepository:
    """DynamoDB repository for user-authored ReAct tools."""

    GSI1PK_TOOL = "TOOL"
    GSI1PK_VERSION = "TOOL_VERSION"

    def __init__(self, base: Optional[FoundryWorkspaceRepository] = None) -> None:
        self._base = base or FoundryWorkspaceRepository()
        logger.info(
            "ToolRegistryRepository initialized: table={}",
            self._base.table_name,
        )

    @property
    def table_name(self) -> str:
        return self._base.table_name

    # ------------------------------------------------------------------
    # META row
    # ------------------------------------------------------------------

    def put_tool_meta(
        self,
        tool_id: str,
        attrs: Dict[str, Any],
        *,
        condition_not_exists: bool = False,
        if_unchanged_updated_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persist the META row for a tool. ``if_unchanged_updated_at`` enables
        optimistic locking - the write succeeds only if the row's prior
        ``updatedAt`` matches.
        """
        item: Dict[str, Any] = {
            "PK": tool_pk(tool_id),
            "SK": self._base.META_SK,
            "GSI1PK": self.GSI1PK_TOOL,
            "GSI1SK": str(attrs.get("updatedAt") or ""),
            **attrs,
        }
        kwargs: Dict[str, Any] = {"Item": item}
        if condition_not_exists:
            kwargs["ConditionExpression"] = "attribute_not_exists(PK)"
        elif if_unchanged_updated_at is not None:
            kwargs["ConditionExpression"] = "updatedAt = :prev OR attribute_not_exists(PK)"
            kwargs["ExpressionAttributeValues"] = {":prev": if_unchanged_updated_at}
        try:
            self._base.table.put_item(**kwargs)
            return item
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "ConditionalCheckFailedException":
                raise ToolRegistryRepositoryError(
                    f"Tool {tool_id} concurrent-modification conflict"
                )
            logger.error("put_tool_meta({}) failed: {}", tool_id, e)
            raise ToolRegistryRepositoryError(str(e))

    def get_tool_meta(self, tool_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self._base.get_meta(tool_pk(tool_id))
        except FoundryWorkspaceRepositoryError as e:
            raise ToolRegistryRepositoryError(str(e))

    def list_active_tools(self) -> List[Dict[str, Any]]:
        """All META rows with status != deleted, sorted by updatedAt desc."""
        try:
            rows = self._base.query_gsi1(self.GSI1PK_TOOL, scan_forward=False)
        except FoundryWorkspaceRepositoryError as e:
            raise ToolRegistryRepositoryError(str(e))
        return [r for r in rows if str(r.get("status", "active")) != "deleted"]

    def soft_delete_tool(self, tool_id: str, *, deleted_by: str, deleted_at: str) -> None:
        meta = self.get_tool_meta(tool_id)
        if not meta:
            return
        meta["status"] = "deleted"
        meta["deletedBy"] = deleted_by
        meta["deletedAt"] = deleted_at
        meta["updatedAt"] = deleted_at
        self.put_tool_meta(tool_id, meta)

    def hard_delete_tool(self, tool_id: str) -> int:
        try:
            return self._base.delete_pk(tool_pk(tool_id))
        except FoundryWorkspaceRepositoryError as e:
            raise ToolRegistryRepositoryError(str(e))

    # ------------------------------------------------------------------
    # VERSION rows
    # ------------------------------------------------------------------

    def put_tool_version(
        self,
        tool_id: str,
        version: int,
        attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "PK": tool_pk(tool_id),
            "SK": tool_version_sk(version),
            "GSI1PK": self.GSI1PK_VERSION,
            "GSI1SK": f"{tool_id}#{version:06d}",
            "version": int(version),
            **attrs,
        }
        try:
            self._base.table.put_item(Item=item)
            return item
        except ClientError as e:
            logger.error("put_tool_version({}, {}) failed: {}", tool_id, version, e)
            raise ToolRegistryRepositoryError(str(e))

    def get_tool_version(self, tool_id: str, version: int) -> Optional[Dict[str, Any]]:
        try:
            resp = self._base.table.get_item(
                Key={"PK": tool_pk(tool_id), "SK": tool_version_sk(version)}
            )
            return resp.get("Item")
        except ClientError as e:
            logger.error("get_tool_version({}, {}) failed: {}", tool_id, version, e)
            raise ToolRegistryRepositoryError(str(e))

    def list_tool_versions(self, tool_id: str) -> List[Dict[str, Any]]:
        try:
            rows = self._base.query_pk(tool_pk(tool_id), sk_prefix="VERSION#")
            rows.sort(key=lambda r: int(r.get("version", 0)), reverse=True)
            return rows
        except FoundryWorkspaceRepositoryError as e:
            raise ToolRegistryRepositoryError(str(e))

    # ------------------------------------------------------------------
    # TAG rows
    # ------------------------------------------------------------------

    def put_tool_tags(self, tool_id: str, tags: List[str]) -> None:
        """Replace all tag rows for a tool."""
        # Delete existing tag rows then write new ones - small N, simple is fine.
        try:
            existing = self._base.query_pk(tool_pk(tool_id), sk_prefix="TAG#")
            with self._base.table.batch_writer() as batch:
                for r in existing:
                    batch.delete_item(Key={"PK": r["PK"], "SK": r["SK"]})
            for t in tags or []:
                self._base.table.put_item(Item={
                    "PK": tool_pk(tool_id),
                    "SK": tool_tag_sk(t),
                    "GSI1PK": f"TAG#{t}",
                    "GSI1SK": tool_pk(tool_id),
                    "tag": t,
                })
        except (ClientError, FoundryWorkspaceRepositoryError) as e:
            logger.error("put_tool_tags({}) failed: {}", tool_id, e)
            raise ToolRegistryRepositoryError(str(e))

    def list_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        try:
            rows = self._base.query_gsi1(f"TAG#{tag}")
            tool_ids = sorted({r["PK"].replace("TOOL#", "") for r in rows if "PK" in r})
            return [self.get_tool_meta(tid) for tid in tool_ids if self.get_tool_meta(tid)]
        except FoundryWorkspaceRepositoryError as e:
            raise ToolRegistryRepositoryError(str(e))
