"""
Virtual Query Tools for the ReAct Agent

Wraps VirtualQueryService to let the agent query entities by business name
(e.g. Material_Master, AR_Invoice) instead of by physical schema/table.
All queries route through mapping rules to the correct source (FDW or simulator).
"""

import json
from typing import Any, Dict, List, Optional

from loguru import logger

from ..tool_registry import ToolRegistry, RiskLevel, Tool

vq_logger = logger.bind(component="virtual-query-tools")


def register_virtual_query_tools(
    registry: ToolRegistry,
    virtual_query_service,
    mapping_service=None,
):
    async def query_virtual_entity(
        entity_name: str,
        fields: Optional[List[str]] = None,
        limit: int = 20,
    ) -> str:
        """Query a virtual entity by business name. Routes to the correct source via mapping rules."""
        try:
            from src.models.mapping_rule_models import VirtualQueryRequest
            request = VirtualQueryRequest(
                virtual_entity=entity_name,
                fields=fields,
                limit=min(limit, 50),
            )
            result = await virtual_query_service.query_virtual_entity(request)
            data = result.model_dump(by_alias=True) if hasattr(result, "model_dump") else result
            rows = data.get("rows", [])
            metadata = data.get("metadata", {})
            return json.dumps({
                "entity": entity_name,
                "row_count": len(rows),
                "source_table": metadata.get("sourceTable", ""),
                "source_type": metadata.get("sourceType", ""),
                "duration_ms": metadata.get("durationMs", 0),
                "rows": rows[:20],
            }, default=str)
        except ValueError as e:
            return json.dumps({"error": str(e), "hint": "No active mapping rule found. Use search_enterprise_knowledge to learn about this entity."})
        except Exception as e:
            vq_logger.warning(f"Virtual query failed for {entity_name}: {e}")
            return json.dumps({"error": str(e)})

    registry.register(Tool(
        name="query_virtual_entity",
        description=(
            "Query a virtual entity by its business name (e.g. Material_Master, AR_Invoice, Account). "
            "This is the PRIMARY tool for data queries — it automatically routes to the correct source "
            "(FDW, simulator, or mapped table) via mapping rules. Returns rows with virtual field names. "
            "Use this INSTEAD of query_table for any entity in the unified schema."
        ),
        execute=query_virtual_entity,
        risk_level=RiskLevel.READ_ONLY,
        parameters={
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Virtual entity name exactly as defined in the schema (e.g. Material_Master, AR_Invoice, Inventory_Position)",
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of field names to return. If omitted, returns all mapped fields.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max rows to return (default 20, max 50)",
                    "default": 20,
                },
            },
            "required": ["entity_name"],
        },
    ))

    async def list_virtual_entities() -> str:
        """List all virtual entities with their mapping status and source info."""
        try:
            entities = await virtual_query_service.list_virtual_entities()
            if hasattr(entities, "__iter__") and not isinstance(entities, (str, dict)):
                items = []
                for e in entities:
                    if hasattr(e, "model_dump"):
                        items.append(e.model_dump(by_alias=True))
                    elif isinstance(e, dict):
                        items.append(e)
                    else:
                        items.append(str(e))
                return json.dumps({"entities": items, "count": len(items)}, default=str)
            return json.dumps({"entities": entities}, default=str)
        except Exception as e:
            vq_logger.warning(f"List virtual entities failed: {e}")
            return json.dumps({"error": str(e)})

    registry.register(Tool(
        name="list_virtual_entities",
        description=(
            "List all virtual entities in the data layer with their mapping status (mapped, virtual, unmapped), "
            "source system, and active rule count. Use this to understand what data is available before querying."
        ),
        execute=list_virtual_entities,
        risk_level=RiskLevel.READ_ONLY,
        parameters={"type": "object", "properties": {}},
    ))

    async def get_entity_schema(entity_name: str) -> str:
        """Get field definitions, relationships, and policies for a virtual entity from the knowledge base."""
        try:
            from src.services.control_plane.embedding_service import EmbeddingService
            from src.services.control_plane.vector_store import VectorStore
            from src.services.fdw_connection_manager import PostgreSQLConnectionManager
            from src.config.fdw_config import FDWConfig

            config = FDWConfig.from_environment()
            conn_mgr = PostgreSQLConnectionManager(config)
            await conn_mgr.initialize()
            emb_svc = EmbeddingService()
            store = VectorStore(conn_mgr)

            query = f"Schema and fields for {entity_name} entity"
            embedding = emb_svc.embed_text(query)
            results = await store.search(query_embedding=embedding, limit=5, content_type="onto_schema")

            matches = []
            for r in results:
                matches.append({
                    "content": r.get("content", "")[:500],
                    "metadata": r.get("metadata", {}),
                    "similarity": round(r.get("similarity", 0), 3),
                })
            return json.dumps({"entity": entity_name, "schema_matches": matches}, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    registry.register(Tool(
        name="get_entity_schema",
        description=(
            "Get the schema definition, field descriptions, relationships, and associated policies "
            "for a virtual entity. Use this to understand an entity's structure before querying it."
        ),
        execute=get_entity_schema,
        risk_level=RiskLevel.READ_ONLY,
        parameters={
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Entity name (e.g. Material_Master, Vendor_Master, AR_Invoice)",
                },
            },
            "required": ["entity_name"],
        },
    ))

    # Phase 1 -- stamp the infra-query bucket on every tool registered here.
    for tool_name in ("query_virtual_entity", "list_virtual_entities", "get_entity_schema"):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "infra-query"
