"""
Tools Registry service (Reasoning plane, Phase 3.3)

DDB-backed catalog of every ReAct tool. The spec requires ReAct tool
definitions to live in the ReAct Tool Registry in DynamoDB - this service
provides that shape while keeping the executable Python for built-in
tools in-repo (referenced via ``codeRef=python://module.path.func``).

Row layout:
- ``TOOLREG#{tool_id}`` / ``META``
    - toolId, description, group, riskLevel, requiresApproval, cacheable
    - parameters (JSON Schema)
    - tags, connectorApi, toolKind
    - relationships[], bucket
    - codeRef       - python://module.path.func for built-ins, or
                       ddb://TOOL#{id}/VERSION#{n}/source_code for user tools
    - source        - "python" | "user" | "yaml"

Consumers:
- ``/api/v1/tools-registry``       - list + get from DDB
- ``rtd.registry_health()``        - stays on the in-memory registry for now;
  the DDB rows are a projection for backup + external reads.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _python_code_ref(execute_fn: Any) -> str:
    mod = getattr(execute_fn, "__module__", "") or ""
    name = getattr(execute_fn, "__qualname__", None) or getattr(execute_fn, "__name__", "unknown")
    return f"python://{mod}.{name}"


class ToolsRegistryService:
    _instance: Optional["ToolsRegistryService"] = None

    def __init__(self, repo: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repo or FoundryWorkspaceRepository()

    @classmethod
    def get_instance(cls) -> "ToolsRegistryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------- reads -------

    async def list(self, group: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            return self._repo.list_tool_regs(group)
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"ToolsRegistry list failed: {e}")
            return []

    async def get(self, tool_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self._repo.get_tool_reg(tool_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"ToolsRegistry get({tool_id}) failed: {e}")
            return None

    # ------- writes -------

    async def upsert(
        self,
        tool_id: str,
        attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        attrs = dict(attrs)
        attrs.setdefault("toolId", tool_id)
        attrs.setdefault("updatedAt", _now_iso())
        try:
            return self._repo.put_tool_reg(tool_id, attrs)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"ToolsRegistry upsert({tool_id}) failed: {e}")
            raise

    async def delete(self, tool_id: str) -> int:
        try:
            return self._repo.delete_tool_reg(tool_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"ToolsRegistry delete({tool_id}) failed: {e}")
            return 0

    # ------- bootstrap -------

    async def sync_from_in_memory(self, tool_registry: Any) -> int:
        """Project every tool from the in-memory ``ToolRegistry`` into a
        ``TOOLREG#`` row. Called from startup after code + user tools are
        registered."""
        if tool_registry is None:
            return 0
        try:
            tools = list(tool_registry.list_tools())
        except Exception as e:
            logger.warning(f"ToolsRegistry sync: list_tools failed: {e}")
            return 0

        written = 0
        for tool in tools:
            try:
                risk = getattr(tool, "risk_level", None)
                risk_str = risk.value if hasattr(risk, "value") else str(risk or "read_only")
                attrs: Dict[str, Any] = {
                    "toolId": tool.name,
                    "description": getattr(tool, "description", ""),
                    "parameters": getattr(tool, "parameters", {}) or {},
                    "riskLevel": risk_str,
                    "requiresApproval": bool(getattr(tool, "requires_approval", False)),
                    "cacheable": bool(getattr(tool, "cacheable", False)),
                    "connectorApi": getattr(tool, "connector_api", None),
                    "tags": list(getattr(tool, "tags", []) or []),
                    "toolKind": (
                        tool.effective_tool_kind()
                        if hasattr(tool, "effective_tool_kind")
                        else getattr(tool, "tool_kind", None)
                    ),
                    "bucket": getattr(tool, "bucket", "default"),
                    "group": getattr(tool, "bucket", "default"),  # tab grouping
                    "relationships": [
                        {"name": r.name, "description": getattr(r, "description", "")}
                        for r in getattr(tool, "output_relationships", []) or []
                    ],
                    "streaming": bool(getattr(tool, "streaming", False)),
                    "codeRef": _python_code_ref(tool.execute),
                    "source": "python",
                }
                await self.upsert(tool.name, attrs)
                written += 1
            except Exception as e:
                logger.warning(f"ToolsRegistry sync failed for {getattr(tool, 'name', '?')}: {e}")
        if written:
            logger.info(f"ToolsRegistry synced {written} tools into DDB (TOOLREG#)")
        return written


def get_tools_registry_service() -> ToolsRegistryService:
    return ToolsRegistryService.get_instance()
