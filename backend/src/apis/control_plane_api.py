"""
AI Control Plane REST API

Provides endpoints for:
  - Semantic search over indexed FDW schema / policy metadata
  - Triggering schema re-indexing
  - Health / stats for the control plane intelligence layer
"""

import json as _json

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from loguru import logger

from .session_middleware import get_session_from_cookie

cp_logger = logger.bind(component="control-plane")

router = APIRouter()

from .onto_api import router as onto_router, set_init_fn as _set_onto_init
from .onto_data_api import router as onto_data_router
router.include_router(onto_router)
router.include_router(onto_data_router)

_vector_store = None
_embedding_service = None
_schema_indexer = None
_rag_service = None
_agent_executor = None
_conn_mgr = None
_initialized = False


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language query")
    content_type: Optional[str] = Field(None, description="Filter by content type (fdw_table, fdw_server)")
    limit: int = Field(10, ge=1, le=50)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question about the data platform")
    content_type: Optional[str] = Field(None, description="Limit retrieval to a content type")
    context_limit: int = Field(15, ge=1, le=30, description="Max context documents to retrieve")


class AgentRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question or task for the agent")
    max_steps: int = Field(10, ge=1, le=20, description="Max reasoning steps")
    skip_cache: bool = Field(False, description="Skip response cache and force fresh reasoning")


class SearchResult(BaseModel):
    source_id: str
    content_type: str
    content: str
    similarity: float
    metadata: Dict[str, Any] = {}


_set_onto_init(lambda: _ensure_init())


async def _ensure_init():
    global _vector_store, _embedding_service, _schema_indexer, _rag_service, _agent_executor, _conn_mgr, _initialized
    if _initialized:
        return
    _initialized = True

    try:
        from src.services.control_plane.embedding_service import get_embedding_service
        from src.services.control_plane.vector_store import VectorStore
        from src.services.control_plane.schema_indexer import SchemaIndexer
        from src.services.control_plane.llm_client import get_llm_client
        from src.services.control_plane.rag_service import RAGService
        from src.services.control_plane.tool_registry import ToolRegistry
        from src.services.control_plane.tools.fdw_tools import register_fdw_tools
        from src.services.control_plane.tools.rag_tools import register_rag_tools
        from src.services.control_plane.agent_executor import AgentExecutor
        from src.services.fdw_connection_manager import PostgreSQLConnectionManager
        from src.services.fdw_discovery_service import FDWDiscoveryService
        from src.services.fdw_query_service import FDWQueryService
        from src.config.fdw_config import FDWConfig

        config = FDWConfig.from_environment()
        if not config.enabled:
            cp_logger.warning("Control plane: FDW not enabled, vector store unavailable")
            return

        _conn_mgr = PostgreSQLConnectionManager(config)
        await _conn_mgr.initialize()

        _embedding_service = get_embedding_service()
        _vector_store = VectorStore(_conn_mgr)
        await _vector_store.ensure_schema()

        discovery = FDWDiscoveryService(_conn_mgr)
        _schema_indexer = SchemaIndexer(discovery, _embedding_service, _vector_store)

        from src.services.control_plane.graph_store import GraphStore

        llm = get_llm_client()
        _graph_store = GraphStore(_conn_mgr, _vector_store)
        _rag_service = RAGService(_embedding_service, _vector_store, llm, graph_store=_graph_store)

        from src.apis.onto_api import init_onto_api
        init_onto_api(_rag_service, _vector_store, _graph_store, _embedding_service)

        query_service = FDWQueryService(_conn_mgr, discovery)
        tool_registry = ToolRegistry()

        # Phase 2 (data-source-mode): hand the FDW tools the simulator
        # registry and mode resolver so they can route per-source. Both
        # are optional - the tools fall back to today's behaviour when
        # missing.
        try:
            from src.apis import fdw_api as _fdw_api_mod
            _sims_for_tools = dict(getattr(_fdw_api_mod, "_simulators", {}) or {})
            _mode_for_tools = getattr(_fdw_api_mod, "_mode_service", None)
        except Exception:
            _sims_for_tools = {}
            _mode_for_tools = None

        register_fdw_tools(
            tool_registry,
            discovery=discovery,
            query_service=query_service,
            simulators=_sims_for_tools,
            mode_service=_mode_for_tools,
        )
        register_rag_tools(tool_registry, _embedding_service, _vector_store, rag_service=_rag_service)

        try:
            from src.services.control_plane.tools.virtual_query_tools import register_virtual_query_tools
            if _virtual_query_service:
                register_virtual_query_tools(tool_registry, _virtual_query_service)
                cp_logger.info("Virtual query tools registered")
            else:
                cp_logger.info("Virtual query service not configured — virtual query tools skipped")
        except Exception as e:
            cp_logger.warning(f"Virtual query tools not available: {e}")

        try:
            from src.services.control_plane.tools.supply_chain_tools import register_supply_chain_tools
            register_supply_chain_tools(tool_registry, _rag_service)
            cp_logger.info("Supply chain tools registered")
        except Exception as e:
            cp_logger.warning(f"Supply chain tools not available: {e}")

        try:
            from src.services.control_plane.tools.o2c_tools import register_o2c_tools
            register_o2c_tools(tool_registry, _virtual_query_service)
            cp_logger.info("O2C tools registered")
        except Exception as e:
            cp_logger.warning(f"O2C tools not available: {e}")

        try:
            from src.services.control_plane.tools.demand_forecast_tools import register_demand_forecast_tools
            register_demand_forecast_tools(tool_registry, _virtual_query_service)
            cp_logger.info("Demand forecast tools registered")
        except Exception as e:
            cp_logger.warning(f"Demand forecast tools not available: {e}")

        try:
            from src.services.control_plane.tools.erp_writeback_tools import register_erp_writeback_tools
            register_erp_writeback_tools(tool_registry)
            cp_logger.info("ERP write-back tools registered")
        except Exception as e:
            cp_logger.warning(f"ERP write-back tools not available: {e}")

        # Phase 3 - Cursor-for-data analyzer / mutator / notify families.
        # Each module is independent so a single registration failure does
        # not block the others; mismatches surface in automation_diag.
        try:
            from src.services.control_plane.tools.customer_360_tools import register_customer_360_tools
            register_customer_360_tools(tool_registry)
            cp_logger.info("Customer-360 tools registered")
        except Exception as e:
            cp_logger.warning(f"Customer-360 tools not available: {e}")

        try:
            from src.services.control_plane.tools.inventory_tools import register_inventory_tools
            register_inventory_tools(tool_registry)
            cp_logger.info("Inventory tools registered")
        except Exception as e:
            cp_logger.warning(f"Inventory tools not available: {e}")

        try:
            from src.services.control_plane.tools.supply_chain_risk_tools import register_supply_chain_risk_tools
            register_supply_chain_risk_tools(tool_registry)
            cp_logger.info("Supply-Chain Risk tools registered")
        except Exception as e:
            cp_logger.warning(f"Supply-Chain Risk tools not available: {e}")

        try:
            from src.services.control_plane.tools.procurement_tools import register_procurement_tools
            register_procurement_tools(tool_registry)
            cp_logger.info("Procurement tools registered")
        except Exception as e:
            cp_logger.warning(f"Procurement tools not available: {e}")

        try:
            from src.services.control_plane.tools.cpq_sell_tools import register_cpq_sell_tools
            register_cpq_sell_tools(tool_registry, _virtual_query_service)
            cp_logger.info("Trade CPQ (sell-side) tools registered")
        except Exception as e:
            cp_logger.warning(f"Trade CPQ tools not available: {e}")

        try:
            from src.services.control_plane.tools.cpq_buy_tools import register_cpq_buy_tools
            register_cpq_buy_tools(tool_registry, _virtual_query_service)
            cp_logger.info("Sourcing CPQ (buy-side) tools registered")
        except Exception as e:
            cp_logger.warning(f"Sourcing CPQ tools not available: {e}")

        try:
            from src.services.control_plane.tools.production_quality_tools import register_production_quality_tools
            register_production_quality_tools(tool_registry)
            cp_logger.info("Production-Quality tools registered")
        except Exception as e:
            cp_logger.warning(f"Production-Quality tools not available: {e}")

        try:
            from src.services.control_plane.tools.esg_tools import register_esg_tools
            register_esg_tools(tool_registry)
            cp_logger.info("ESG tools registered")
        except Exception as e:
            cp_logger.warning(f"ESG tools not available: {e}")

        try:
            from src.services.control_plane.tools.notify_tools import register_notify_tools
            register_notify_tools(tool_registry)
            cp_logger.info("Notify tools registered")
        except Exception as e:
            cp_logger.warning(f"Notify tools not available: {e}")

        # User-authored DynamoDB tools - registered LAST so any name
        # collision with a code-defined tool is resolved in favour of
        # the code-defined version (the loader logs + skips on conflict).
        try:
            from src.services.control_plane.tool_store_service import ToolStoreService
            from src.services.control_plane.tools.dynamodb_tools import register_dynamodb_tools
            from src.services.control_plane.connector_runtime import emit_audit
            try:
                from src.apis.connector_api_workbench_api import _invoke as _wb_invoke
            except Exception:
                _wb_invoke = None
            _tool_store = ToolStoreService()
            _dyn_loader = await register_dynamodb_tools(
                tool_registry,
                store=_tool_store,
                virtual_query_service=_virtual_query_service,
                invoke_connector_fn=_wb_invoke,
                emit_audit_fn=emit_audit,
            )
            globals()["_tool_store"] = _tool_store
            globals()["_dynamic_tool_loader"] = _dyn_loader
            cp_logger.info("DynamoDB-backed tools registered")
        except Exception as e:
            cp_logger.warning(f"DynamoDB tools not available: {e}")

        _agent_executor = AgentExecutor(llm, tool_registry)

        cp_logger.info(f"Control plane initialized (RAG + Agent, {len(tool_registry.list_tools())} tools)")
    except Exception as e:
        cp_logger.error(f"Control plane init failed: {e}")


@router.post("/search", response_model=List[SearchResult])
async def semantic_search(
    request: SearchRequest,
    session: Optional[Dict] = Depends(get_session_from_cookie),
):
    """Semantic search over indexed schema / policy knowledge."""
    await _ensure_init()
    if _vector_store is None or _embedding_service is None:
        raise HTTPException(status_code=503, detail="Control plane not available (FDW disabled or init failed)")
    if not _embedding_service.available:
        raise HTTPException(status_code=503, detail="Embedding service not available (OpenAI key missing)")

    try:
        query_emb = _embedding_service.embed_text(request.query)
        results = await _vector_store.search(
            query_embedding=query_emb,
            content_type=request.content_type,
            limit=request.limit,
        )
        return [
            SearchResult(
                source_id=r["source_id"],
                content_type=r["content_type"],
                content=r["content"],
                similarity=round(float(r["similarity"]), 4),
                metadata=r.get("metadata") or {},
            )
            for r in results
        ]
    except Exception as e:
        cp_logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.post("/ask")
async def ask_question(
    request: AskRequest,
    session: Optional[Dict] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """Ask a natural language question about the data platform.

    Uses RAG: retrieves relevant schema context from the vector store,
    then asks the LLM to answer grounded in that context.
    """
    await _ensure_init()
    if _rag_service is None:
        raise HTTPException(status_code=503, detail="RAG service not available")

    try:
        result = await _rag_service.ask(
            question=request.question,
            content_type=request.content_type,
            context_limit=request.context_limit,
        )
        return result
    except Exception as e:
        cp_logger.error(f"RAG ask failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ask failed: {e}")


@router.post("/agent")
async def agent_query(
    request: AgentRequest,
    session: Optional[Dict] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """Run the ReAct agent with policy enforcement and audit logging.

    The agent autonomously:
    1. Classifies intent risk (read_only / write / cross_system)
    2. Gates available tools based on risk level
    3. Validates every tool call via PolicyEngine before execution
    4. Logs every action to audit trail
    5. Returns a grounded answer with steps, intent, and any violations
    """
    await _ensure_init()
    if _agent_executor is None:
        raise HTTPException(status_code=503, detail="Agent not available")

    user = "anonymous"
    if session:
        user = session.get("email", session.get("username", "anonymous"))

    try:
        result = await _agent_executor.run(
            question=request.question,
            max_steps=request.max_steps,
            user=user,
            skip_cache=request.skip_cache,
        )
        return result
    except Exception as e:
        cp_logger.error(f"Agent failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")


@router.post("/agent/stream")
async def agent_query_stream(
    request: AgentRequest,
    session: Optional[Dict] = Depends(get_session_from_cookie),
):
    """SSE streaming variant of /agent — emits progress events during the ReAct loop."""
    await _ensure_init()
    if _agent_executor is None:
        raise HTTPException(status_code=503, detail="Agent not available")

    user = "anonymous"
    if session:
        user = session.get("email", session.get("username", "anonymous"))

    async def event_generator():
        try:
            async for event in _agent_executor.run_streaming(
                question=request.question,
                max_steps=request.max_steps,
                user=user,
                skip_cache=request.skip_cache,
            ):
                yield f"data: {_json.dumps(event, default=str)}\n\n"
        except Exception as e:
            cp_logger.error(f"Agent stream failed: {e}")
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/index")
async def run_indexing(
    session: Optional[Dict] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """Trigger schema re-indexing from FDW discovery into vector store."""
    await _ensure_init()
    if _schema_indexer is None:
        raise HTTPException(status_code=503, detail="Control plane not available")
    if not _embedding_service or not _embedding_service.available:
        raise HTTPException(status_code=503, detail="Embedding service not available")

    try:
        stats = await _schema_indexer.index_all()
        return {"status": "ok", "indexed": stats}
    except Exception as e:
        cp_logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")


async def _compute_virtual_data_layer_stats() -> Dict[str, Any]:
    """Compute virtual entity counts, mapping rule counts, per-system breakdown, and simulator status."""
    result: Dict[str, Any] = {
        "virtual_entities": 0,
        "mapped_entities": 0,
        "virtual_only_entities": 0,
        "unmapped_entities": 0,
        "mapping_rules_total": 0,
        "mapping_rules_active": 0,
        "entities_by_system": {},
        "simulator_status": {},
    }

    try:
        global _cached_entities
        if _cached_entities is None:
            _cached_entities = _parse_schema_entities()

        entities = _cached_entities or []
        result["virtual_entities"] = len(entities)

        by_system: Dict[str, int] = {}
        mapped = 0
        virtual_only = 0
        unmapped = 0
        for e in entities:
            sys_name = e.get("system", "Unknown")
            by_system[sys_name] = by_system.get(sys_name, 0) + 1
            status = e.get("fdwMappingStatus", "unmapped")
            if status == "mapped":
                mapped += 1
            elif status == "virtual":
                virtual_only += 1
            else:
                unmapped += 1

        result["mapped_entities"] = mapped
        result["virtual_only_entities"] = virtual_only
        result["unmapped_entities"] = unmapped
        result["entities_by_system"] = by_system
    except Exception as ex:
        cp_logger.warning(f"VDL stats - entity parse failed: {ex}")

    try:
        from src.apis.mapping_rule_api import _service as mr_service
        if mr_service:
            rules = await mr_service.list_all()
            result["mapping_rules_total"] = len(rules)
            active_rules = [r for r in rules if r.status.value == "active"]
            result["mapping_rules_active"] = len(active_rules)
            mapped_by_rule = len(set(r.virtual_entity for r in active_rules))
            if mapped_by_rule > result["mapped_entities"]:
                result["mapped_entities"] = mapped_by_rule
                result["unmapped_entities"] = max(0, result["virtual_entities"] - mapped_by_rule - result["virtual_only_entities"])
        else:
            cp_logger.info("VDL stats - mapping rule service not configured")
    except Exception as ex:
        cp_logger.warning(f"VDL stats - mapping rules failed: {ex}")

    try:
        from src.apis.fdw_api import _simulators
        sim_label = {"simulator": "sfdc", "oracle": "oracle", "sap": "sap"}
        for name, sim in _simulators.items():
            key = sim_label.get(name, name)
            loaded = bool(sim and getattr(sim, "loaded", False))
            table_count = 0
            total_rows = 0
            if loaded:
                try:
                    table_count = len(sim._tables) if hasattr(sim, "_tables") else 0
                    total_rows = sum(len(rows) for rows in (sim._data or {}).values()) if hasattr(sim, "_data") else 0
                except Exception:
                    pass
            result["simulator_status"][key] = {
                "loaded": loaded,
                "tables": table_count,
                "rows": total_rows,
            }
    except Exception as ex:
        cp_logger.warning(f"VDL stats - simulator status failed: {ex}")

    return result


@router.get("/stats")
async def get_stats(
    session: Optional[Dict] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """Return counts of indexed embeddings by type plus virtual data layer stats."""
    await _ensure_init()
    if _vector_store is None:
        raise HTTPException(status_code=503, detail="Control plane not available")

    try:
        total = await _vector_store.count()
        servers = await _vector_store.count("fdw_server")
        tables = await _vector_store.count("fdw_table")
        onto_schema = await _vector_store.count("onto_schema")
        onto_policy = await _vector_store.count("onto_policy")
        onto_workflow = await _vector_store.count("onto_workflow")
        onto_integration = await _vector_store.count("onto_integration")

        graph_nodes = 0
        graph_edges = 0
        try:
            from sqlalchemy import text
            engine = _conn_mgr.engine if _conn_mgr else None
            if engine:
                import asyncio
                def _count_graph():
                    with engine.connect() as conn:
                        try:
                            conn.execute(text("LOAD 'age'"))
                            conn.execute(text("SET search_path = ag_catalog, public"))
                            nr = conn.execute(text(
                                "SELECT * FROM cypher('enterprise_onto', $$ MATCH (n) RETURN count(n) $$) AS (cnt agtype)"
                            )).fetchone()
                            er = conn.execute(text(
                                "SELECT * FROM cypher('enterprise_onto', $$ MATCH ()-[r]->() RETURN count(r) $$) AS (cnt agtype)"
                            )).fetchone()
                            return (int(str(nr[0])) if nr else 0, int(str(er[0])) if er else 0)
                        except Exception:
                            return (0, 0)
                loop = asyncio.get_event_loop()
                graph_nodes, graph_edges = await loop.run_in_executor(None, _count_graph)
        except Exception:
            pass

        vdl = await _compute_virtual_data_layer_stats()

        return {
            "total_embeddings": total,
            "fdw_servers": servers,
            "fdw_tables": tables,
            "onto_schema": onto_schema,
            "onto_policy": onto_policy,
            "onto_workflow": onto_workflow,
            "onto_integration": onto_integration,
            "graph_nodes": graph_nodes,
            "graph_edges": graph_edges,
            "embedding_model": "text-embedding-3-small",
            "dimensions": 1536,
            "embedding_available": _embedding_service.available if _embedding_service else False,
            **vdl,
        }
    except Exception as e:
        cp_logger.error(f"Stats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stats")


@router.get("/tools")
async def list_tools(
    session: Optional[Dict] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """List all registered tools with their risk levels and parameter schemas."""
    await _ensure_init()
    if _agent_executor is None:
        raise HTTPException(status_code=503, detail="Agent not available")

    tools = _agent_executor._tools.list_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level.value,
                "requires_approval": t.requires_approval,
                "cacheable": getattr(t, "cacheable", False),
                "connector_api": getattr(t, "connector_api", None),
                "tags": list(getattr(t, "tags", []) or []),
                "parameters": t.parameters,
            }
            for t in tools
        ],
        "total": len(tools),
    }


@router.post("/tools/{tool_name}/execute")
async def execute_tool(
    tool_name: str,
    body: Dict[str, Any],
    session: Optional[Dict] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """Execute a single tool with the provided arguments (bypasses ReAct loop)."""
    await _ensure_init()
    if _agent_executor is None:
        raise HTTPException(status_code=503, detail="Agent not available")

    tool = _agent_executor._tools.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    arguments = body.get("arguments", {})

    import time
    start = time.time()
    try:
        result = await _agent_executor._tools.execute(tool_name, arguments)
        elapsed_ms = round((time.time() - start) * 1000)
        return {
            "tool": tool_name,
            "risk_level": tool.risk_level.value,
            "success": "error" not in result,
            "result": result,
            "elapsed_ms": elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = round((time.time() - start) * 1000)
        cp_logger.error(f"Tool execute '{tool_name}' failed: {e}")
        return {
            "tool": tool_name,
            "risk_level": tool.risk_level.value,
            "success": False,
            "result": {"error": str(e)},
            "elapsed_ms": elapsed_ms,
        }


# ============================================================================
# Virtual Data Layer — Query Propagation
# ============================================================================

_virtual_query_service = None


def configure_virtual_query(service):
    """Configure the VirtualQueryService. Called during app startup."""
    global _virtual_query_service
    _virtual_query_service = service


@router.post("/virtual/query")
async def query_virtual_entity(request: Dict[str, Any]):
    """Query a virtual entity — translates to FDW queries via mapping rules."""
    if _virtual_query_service is None:
        raise HTTPException(status_code=503, detail="Virtual query service not initialized")
    try:
        from src.models.mapping_rule_models import VirtualQueryRequest
        vq_request = VirtualQueryRequest(**request)
        result = await _virtual_query_service.query_virtual_entity(vq_request)
        return result.model_dump(by_alias=True) if hasattr(result, "model_dump") else result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        cp_logger.error(f"Virtual query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/virtual/entities")
async def list_virtual_entities():
    """List all virtual entities with their mapping status."""
    if _virtual_query_service is None:
        raise HTTPException(status_code=503, detail="Virtual query service not initialized")
    try:
        return await _virtual_query_service.list_virtual_entities()
    except Exception as e:
        cp_logger.error(f"List virtual entities failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/virtual/entities/{entity_id}/preview")
async def preview_virtual_entity(entity_id: str, limit: int = Query(default=10, ge=1, le=100)):
    """Preview data for a virtual entity (first N rows via mapping)."""
    if _virtual_query_service is None:
        raise HTTPException(status_code=503, detail="Virtual query service not initialized")
    try:
        result = await _virtual_query_service.preview_entity(entity_id, limit=limit)
        return result.model_dump(by_alias=True) if hasattr(result, "model_dump") else result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        cp_logger.error(f"Preview virtual entity failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Entity Explorer — Schema YAML parser
# ============================================================================
#
# Delegates to VdlCatalogService which loads canonical-entities.yaml first
# and falls back to legacy *schema*.yaml for any entity not yet migrated.
# The `system` field on each entity is no longer read from the YAML for
# canonical entries — it's derived at request time from the active mapping
# rule (see /entities/{name}/binding if/when added).

def _parse_schema_entities() -> List[Dict[str, Any]]:
    """Return the merged VDL entity catalog (canonical + legacy fallback)."""
    from src.services.vdl_catalog_service import get_catalog
    return get_catalog().list_entities()


_cached_entities: Optional[List[Dict[str, Any]]] = None


@router.get("/entities")
async def list_schema_entities():
    """List all virtual entities parsed from enterprise-knowledge schema YAMLs."""
    global _cached_entities
    if _cached_entities is None:
        _cached_entities = _parse_schema_entities()
    return _cached_entities


@router.get("/entities/graph")
async def get_entity_graph():
    """Return full knowledge graph: nodes (entities) + edges (relationships) for visualization."""
    global _cached_entities
    if _cached_entities is None:
        _cached_entities = _parse_schema_entities()

    entity_names = {e["name"] for e in _cached_entities}
    nodes = []
    edges = []
    edge_id = 0

    for e in _cached_entities:
        degree = len(e.get("relationships", []))
        nodes.append({
            "id": e["name"],
            "system": e["system"],
            "domain": e.get("domain", ""),
            "riskLevel": e.get("riskLevel", "medium"),
            "fieldCount": len(e.get("fields", [])),
            "isVirtual": e.get("isVirtual", False),
            "fdwMappingStatus": e.get("fdwMappingStatus", "unmapped"),
            "degree": degree,
        })
        for rel in e.get("relationships", []):
            target = rel.get("targetEntity", "")
            edges.append({
                "id": f"e{edge_id}",
                "source": e["name"],
                "target": target,
                "type": rel.get("type", ""),
                "category": rel.get("targetCategory", ""),
                "description": rel.get("description", ""),
                "targetExists": target in entity_names,
            })
            edge_id += 1

    systems = list({n["system"] for n in nodes})
    rel_types = list({ed["type"] for ed in edges if ed["type"]})

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "nodeCount": len(nodes),
            "edgeCount": len(edges),
            "systems": systems,
            "relationshipTypes": rel_types,
        },
    }


@router.get("/entities/{entity_name}")
async def get_schema_entity(entity_name: str):
    """Get a single entity by name."""
    global _cached_entities
    if _cached_entities is None:
        _cached_entities = _parse_schema_entities()
    for e in _cached_entities:
        if e["name"] == entity_name:
            return e
    raise HTTPException(status_code=404, detail=f"Entity '{entity_name}' not found")


@router.post("/entities/refresh")
async def refresh_schema_entities():
    """Force re-parse of schema YAML files (canonical + legacy fallback)."""
    from src.services.vdl_catalog_service import get_catalog
    global _cached_entities
    catalog = get_catalog()
    catalog.refresh()
    _cached_entities = catalog.list_entities()
    return {"count": len(_cached_entities), "entities": [e["name"] for e in _cached_entities]}
