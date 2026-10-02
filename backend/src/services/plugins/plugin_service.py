"""
Plugin Service

Manages plugin lifecycle: registration, activation, deactivation.
Parses plugin manifests, registers tools and journeys dynamically.
"""

import json
import os
import uuid
import zipfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

from .plugin_models import (
    JourneyDefinition,
    JourneyStep,
    PluginManifest,
    PluginRecord,
    PluginStatus,
    ToolDefinition,
    ToolImplementation,
)
from .yaml_tool_executor import YAMLToolExecutor

plugin_logger = logger.bind(component="plugin-service")


class PluginService:

    def __init__(self, virtual_query_service=None, tool_registry=None):
        self._vq = virtual_query_service
        self._tool_registry = tool_registry
        self._plugins: Dict[str, PluginRecord] = {}
        self._executor = YAMLToolExecutor(virtual_query_service)

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": p.id, "name": p.manifest.name, "version": p.manifest.version,
                "description": p.manifest.description, "author": p.manifest.author,
                "status": p.status.value, "use_case": p.manifest.use_case,
                "tool_count": len(p.tools), "journey_count": len(p.journeys),
                "registered_at": p.registered_at.isoformat(),
                "activated_at": p.activated_at.isoformat() if p.activated_at else None,
            }
            for p in self._plugins.values()
        ]

    def get_plugin(self, plugin_id: str) -> Optional[PluginRecord]:
        return self._plugins.get(plugin_id)

    def register_from_dict(self, manifest_dict: Dict[str, Any],
                           tools: List[Dict] = None, journeys: List[Dict] = None) -> PluginRecord:
        manifest = PluginManifest(**manifest_dict)
        plugin_id = f"plugin-{manifest.name}-{uuid.uuid4().hex[:8]}"

        tool_defs = [ToolDefinition(**t) for t in (tools or [])]
        journey_defs = [JourneyDefinition(**j) for j in (journeys or [])]

        record = PluginRecord(
            id=plugin_id, manifest=manifest, status=PluginStatus.REGISTERED,
            tools=tool_defs, journeys=journey_defs, registered_at=datetime.now(timezone.utc),
        )
        self._plugins[plugin_id] = record
        plugin_logger.info(f"Plugin registered: {manifest.name} ({plugin_id}), {len(tool_defs)} tools, {len(journey_defs)} journeys")
        return record

    def register_from_zip(self, zip_content: bytes) -> PluginRecord:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "plugin.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_content)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)

            return self.register_from_directory(tmpdir)

    def register_from_directory(self, dir_path: str) -> PluginRecord:
        base = Path(dir_path)

        manifest_path = base / "plugin.json"
        if not manifest_path.exists():
            for child in base.iterdir():
                if child.is_dir() and (child / "plugin.json").exists():
                    base = child
                    manifest_path = base / "plugin.json"
                    break

        if not manifest_path.exists():
            raise ValueError("plugin.json not found in plugin directory")

        with open(manifest_path) as f:
            manifest_dict = json.load(f)

        manifest = PluginManifest(**manifest_dict)

        tools_dir = base / manifest.tools.get("directory", "tools")
        tool_defs = []
        if tools_dir.exists():
            for yf in sorted(tools_dir.glob("*.yaml")) + sorted(tools_dir.glob("*.yml")):
                with open(yf) as f:
                    tool_data = yaml.safe_load(f)
                if tool_data and isinstance(tool_data, dict):
                    tool_defs.append(ToolDefinition(**tool_data))

        journeys_dir = base / manifest.journeys.get("directory", "journeys")
        journey_defs = []
        if journeys_dir.exists():
            for yf in sorted(journeys_dir.glob("*.yaml")) + sorted(journeys_dir.glob("*.yml")):
                with open(yf) as f:
                    journey_data = yaml.safe_load(f)
                if journey_data and isinstance(journey_data, dict):
                    journey_defs.append(JourneyDefinition(**journey_data))

        plugin_id = f"plugin-{manifest.name}-{uuid.uuid4().hex[:8]}"
        record = PluginRecord(
            id=plugin_id, manifest=manifest, status=PluginStatus.REGISTERED,
            tools=tool_defs, journeys=journey_defs, registered_at=datetime.now(timezone.utc),
        )
        self._plugins[plugin_id] = record
        plugin_logger.info(f"Plugin registered from directory: {manifest.name} ({plugin_id}), {len(tool_defs)} tools, {len(journey_defs)} journeys")
        return record

    def activate(self, plugin_id: str) -> PluginRecord:
        record = self._plugins.get(plugin_id)
        if not record:
            raise ValueError(f"Plugin not found: {plugin_id}")

        if self._tool_registry:
            from src.services.control_plane.tool_registry import Tool, RiskLevel
            risk_map = {"read_only": RiskLevel.READ_ONLY, "low_risk_write": RiskLevel.LOW_RISK_WRITE, "high_risk_write": RiskLevel.HIGH_RISK_WRITE}

            for tool_def in record.tools:
                risk = risk_map.get(tool_def.risk_level, RiskLevel.READ_ONLY)
                prefix = record.manifest.tools.get("prefix", "")
                full_name = f"{prefix}_{tool_def.name}" if prefix else tool_def.name

                async def _handler(td=tool_def, **kwargs):
                    return await self._executor.execute(td, kwargs)

                tool = Tool(
                    name=full_name, description=tool_def.description,
                    parameters=tool_def.parameters, risk_level=risk,
                    execute=_handler,
                )
                self._tool_registry.register(tool)
                plugin_logger.info(f"Registered plugin tool: {full_name}")

        record.status = PluginStatus.ACTIVE
        record.activated_at = datetime.now(timezone.utc)
        plugin_logger.info(f"Plugin activated: {record.manifest.name} ({plugin_id})")
        return record

    def deactivate(self, plugin_id: str) -> PluginRecord:
        record = self._plugins.get(plugin_id)
        if not record:
            raise ValueError(f"Plugin not found: {plugin_id}")
        record.status = PluginStatus.INACTIVE
        plugin_logger.info(f"Plugin deactivated: {record.manifest.name}")
        return record

    def delete(self, plugin_id: str) -> bool:
        if plugin_id in self._plugins:
            name = self._plugins[plugin_id].manifest.name
            del self._plugins[plugin_id]
            plugin_logger.info(f"Plugin deleted: {name}")
            return True
        return False

    def get_journey_definitions(self, plugin_id: Optional[str] = None) -> List[JourneyDefinition]:
        if plugin_id:
            record = self._plugins.get(plugin_id)
            return record.journeys if record else []
        result = []
        for record in self._plugins.values():
            if record.status == PluginStatus.ACTIVE:
                result.extend(record.journeys)
        return result
