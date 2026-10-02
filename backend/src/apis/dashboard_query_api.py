"""
Dashboard Query API

Provides batch query execution for dashboard panels and entity field metadata
for the query editor. Routes queries through VirtualQueryService.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

from src.models.dashboard_models import (
    BatchQueryRequest,
    BatchQueryResponse,
    BatchQueryResultItem,
    EntityFieldsResponse,
    FieldDescriptor,
)
from pydantic import BaseModel, Field as PydField

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard Query"])

_virtual_query_service = None


def configure(vqs):
    global _virtual_query_service
    _virtual_query_service = vqs


def _vqs():
    if not _virtual_query_service:
        raise HTTPException(status_code=503, detail="VDL not available")
    return _virtual_query_service


@router.post("/query")
async def batch_query(request: BatchQueryRequest):
    results: Dict[str, Any] = {}

    for q in request.queries:
        ref_id = q.ref_id
        try:
            from src.models.mapping_rule_models import VirtualQueryRequest, VirtualFilter

            filters_list = None
            if q.filters:
                filters_list = [
                    VirtualFilter(field=f.field, operator=f.operator, value=f.value)
                    for f in q.filters
                ]

            vq = VirtualQueryRequest(
                virtual_entity=q.entity,
                fields=q.fields,
                filters=filters_list,
                limit=q.limit,
            )
            resp = await _vqs().query_virtual_entity(vq)
            rows = resp.rows

            if q.aggregation and q.group_by:
                rows = _aggregate(
                    rows,
                    column=q.aggregation.field,
                    aggregation=q.aggregation.function,
                    group_by=q.group_by,
                )

            if q.order_by:
                rows = _sort(rows, q.order_by)

            if q.limit and len(rows) > q.limit:
                rows = rows[: q.limit]

            results[ref_id] = {
                "ref_id": ref_id,
                "rows": rows,
                "total": len(rows),
                "source": resp.metadata.get("source_type", "unknown") if resp.metadata else "unknown",
            }
        except Exception as e:
            logger.warning(f"Batch query failed for {ref_id} ({q.entity}): {e}")
            results[ref_id] = {
                "ref_id": ref_id,
                "rows": [],
                "total": 0,
                "error": str(e),
            }

    return {"results": results}


@router.get("/datasource/vdl/entities/{entity}/fields")
async def get_entity_fields(entity: str):
    try:
        from src.models.mapping_rule_models import VirtualQueryRequest
        vq = VirtualQueryRequest(virtual_entity=entity, limit=10)
        resp = await _vqs().query_virtual_entity(vq)

        if not resp.rows:
            return EntityFieldsResponse(entity=entity, fields=[])

        fields = []
        sample_row = resp.rows[0]
        for key in sample_row.keys():
            samples = [r.get(key) for r in resp.rows[:5] if r.get(key) is not None]
            field_type = _infer_type(samples)
            fields.append(FieldDescriptor(
                name=key,
                type=field_type,
                sampleValues=samples[:3],
            ))

        return EntityFieldsResponse(entity=entity, fields=fields)
    except Exception as e:
        logger.warning(f"Entity fields fetch failed for {entity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _infer_type(samples: list) -> str:
    for v in samples:
        if v is None:
            continue
        if isinstance(v, bool):
            return "boolean"
        if isinstance(v, (int, float)):
            return "number"
        if isinstance(v, str):
            if len(v) >= 10 and v[:4].isdigit() and v[4] == "-":
                return "time"
            try:
                float(v)
                return "number"
            except (ValueError, TypeError):
                pass
        return "string"
    return "string"


def _aggregate(
    rows: List[Dict],
    column: Optional[str],
    aggregation: str,
    group_by: List[str],
) -> List[Dict]:
    groups: Dict[str, list] = {}
    for row in rows:
        key = "|".join(str(row.get(g, "unknown")) for g in group_by)
        groups.setdefault(key, []).append(row)

    agg = aggregation.lower()
    result = []
    for group_rows in groups.values():
        out: Dict[str, Any] = {}
        for g in group_by:
            out[g] = group_rows[0].get(g)

        if agg == "count":
            out["value"] = len(group_rows)
        elif agg in ("sum", "avg", "min", "max") and column:
            nums = []
            for r in group_rows:
                try:
                    nums.append(float(r.get(column, 0)))
                except (ValueError, TypeError):
                    pass
            if agg == "sum":
                out["value"] = sum(nums)
            elif agg == "avg":
                out["value"] = sum(nums) / len(nums) if nums else 0
            elif agg == "min":
                out["value"] = min(nums) if nums else 0
            elif agg == "max":
                out["value"] = max(nums) if nums else 0
        else:
            out["value"] = len(group_rows)

        result.append(out)
    return result


def _sort(rows: List[Dict], order_by: str) -> List[Dict]:
    desc = False
    field = order_by
    if " DESC" in order_by.upper():
        desc = True
        field = order_by.upper().replace(" DESC", "").strip()
    elif " ASC" in order_by.upper():
        field = order_by.upper().replace(" ASC", "").strip()

    field_lower = field.lower()
    actual_field = field
    for row in rows:
        for k in row.keys():
            if k.lower() == field_lower:
                actual_field = k
                break
        break

    def sort_key(r):
        val = r.get(actual_field)
        if val is None:
            return 0
        try:
            return float(val)
        except (ValueError, TypeError):
            return str(val)

    return sorted(rows, key=sort_key, reverse=desc)


# --- Natural Language Query Translation ---


class NLQueryRequest(BaseModel):
    query: str
    available_entities: Optional[List[str]] = None
    current_entity: Optional[str] = None


class NLQueryResponse(BaseModel):
    panel_query: Dict[str, Any] = PydField(default_factory=dict)
    suggested_panel_type: str = "table"
    suggested_title: str = ""
    explanation: str = ""
    error: Optional[str] = None


NL_SYSTEM_PROMPT = """You are a query builder assistant for a Virtual Data Layer (VDL) system.
You translate natural language questions into structured panel queries.

The VDL has virtual entities (like database tables). Each entity has fields (columns).
Queries support: entity selection, field projection, filters, aggregation (count/sum/avg/min/max), group by, order by, and limit.

Available panel types for visualization:
- kpi-card: Single numeric value with optional trend (use for single KPI metrics)
- bar-chart: Vertical bars comparing categories
- line-chart: Line chart for time series
- time-series: Multi-series line/area/bar over time
- pie-chart: Distribution/proportion visualization
- histogram: Value distribution as bucketed bars
- heatmap: Color grid for two-dimensional patterns
- table: Data table with rows and columns
- gauge: Progress toward a goal
- bar-gauge: Multiple horizontal/vertical gauges
- state-timeline: State changes over time
- status-history: Periodic status grid
- xy-chart: Scatter/bubble plot
- trend: Ordinal X-axis chart
- candlestick: OHLC financial chart
- node-graph: Network visualization
- alert-list: List of alerts
- text-markdown: Static text
- annotations-list: Event timeline
- geomap: Geographic map with markers

Output ONLY valid JSON with this exact structure:
{
  "entity": "entity_name",
  "fields": ["field1", "field2"],
  "filters": [{"field": "name", "operator": "eq", "value": "x"}],
  "aggregation": {"function": "count", "field": null},
  "groupBy": ["field1"],
  "orderBy": "field1 DESC",
  "limit": 10,
  "suggested_panel_type": "bar-chart",
  "suggested_title": "Title Here",
  "explanation": "Brief explanation"
}

Rules:
- filters is optional (omit or empty array if none needed)
- aggregation is optional (omit if not aggregating)
- groupBy is optional (only when aggregating)
- orderBy is optional
- limit defaults to 100
- Choose the best panel type based on the data shape
- For single values, use kpi-card
- For comparisons across categories, use bar-chart
- For distributions, use pie-chart
- For time-based data, use time-series or line-chart
- For ranked lists, use table or bar-chart with orderBy
- Keep field names exactly as provided in the schema
"""


async def _get_schema_context(entities: Optional[List[str]] = None, current_entity: Optional[str] = None) -> str:
    """Build schema context string for the LLM from available entities and fields."""
    vqs = _vqs()
    parts = []

    try:
        from src.models.mapping_rule_models import VirtualQueryRequest

        entity_list = []
        if current_entity:
            entity_list = [current_entity]
        elif entities:
            entity_list = entities[:10]
        else:
            all_entities = await vqs.list_virtual_entities()
            entity_list = [e["virtual_entity"] for e in all_entities[:15]] if all_entities else []

        parts.append(f"Available entities: {', '.join(entity_list)}")

        for ent_name in entity_list[:5]:
            try:
                vq = VirtualQueryRequest(virtual_entity=ent_name, limit=5)
                resp = await vqs.query_virtual_entity(vq)
                if resp.rows:
                    sample = resp.rows[0]
                    field_info = []
                    for key, val in sample.items():
                        ftype = "string"
                        if isinstance(val, (int, float)):
                            ftype = "number"
                        elif isinstance(val, bool):
                            ftype = "boolean"
                        elif isinstance(val, str) and len(val) >= 10 and val[:4].isdigit():
                            ftype = "time"
                        field_info.append(f"{key} ({ftype})")
                    parts.append(f"\nEntity '{ent_name}' fields: {', '.join(field_info)}")
            except Exception:
                parts.append(f"\nEntity '{ent_name}': unable to fetch fields")

    except Exception as e:
        parts.append(f"Schema discovery failed: {e}")

    return "\n".join(parts)


EXEMPLAR_MIN_SIMILARITY = 0.45
EXEMPLAR_HIGH_CONFIDENCE = 0.75
EXEMPLAR_TOP_K = 8
EXEMPLAR_MAJORITY_VOTE_K = 3
EXEMPLAR_MAJORITY_VOTE_THRESHOLD = 2


async def _retrieve_nlq_exemplars(query: str, top_k: int = EXEMPLAR_TOP_K) -> List[Dict[str, Any]]:
    """Retrieve top-K most similar NLQ exemplars from the control plane vector store."""
    try:
        from src.apis import control_plane_api
        await control_plane_api._ensure_init()
        vs = control_plane_api._vector_store
        es = control_plane_api._embedding_service
        if vs is None or es is None or not getattr(es, "available", False):
            return []

        import asyncio as _asyncio
        loop = _asyncio.get_event_loop()
        emb = await loop.run_in_executor(None, lambda: es.embed_text(query))
        results = await vs.search(
            query_embedding=emb,
            content_type="nlq_exemplar",
            limit=top_k,
            min_similarity=EXEMPLAR_MIN_SIMILARITY,
        )
        return results
    except Exception as e:
        logger.debug(f"NLQ exemplar retrieval failed (non-fatal): {e}")
        return []


def _exemplar_entity(ex: Dict[str, Any]) -> Optional[str]:
    """Extract the structured-query entity from a vector-store exemplar row."""
    meta = ex.get("metadata") or {}
    if isinstance(meta, str):
        import json as _jm
        try:
            meta = _jm.loads(meta)
        except Exception:
            return None
    sq = meta.get("structured_query") or {}
    return sq.get("entity") or None


def _select_biased_entity(exemplars: List[Dict[str, Any]]) -> Optional[str]:
    """Decide whether to bias entity selection based on retrieved exemplars.

    Two conditions trigger entity bias:
      1. Top-1 similarity is at or above EXEMPLAR_HIGH_CONFIDENCE.
      2. A majority of the top-K (EXEMPLAR_MAJORITY_VOTE_K) exemplars agree
         on the same entity, even if individual similarities are moderate.
    Returns the entity name to bias toward, or None if neither condition holds.
    """
    if not exemplars:
        return None

    top_sim = float(exemplars[0].get("similarity", 0))
    if top_sim >= EXEMPLAR_HIGH_CONFIDENCE:
        return _exemplar_entity(exemplars[0])

    head = exemplars[: EXEMPLAR_MAJORITY_VOTE_K]
    counts: Dict[str, int] = {}
    for ex in head:
        ent = _exemplar_entity(ex)
        if ent:
            counts[ent] = counts.get(ent, 0) + 1
    if not counts:
        return None
    winner, votes = max(counts.items(), key=lambda kv: kv[1])
    if votes >= EXEMPLAR_MAJORITY_VOTE_THRESHOLD:
        return winner
    return None


def _format_exemplars(exemplars: List[Dict[str, Any]]) -> str:
    """Render retrieved exemplars as a few-shot block for the LLM."""
    if not exemplars:
        return ""

    import json as json_mod
    lines = []
    for i, ex in enumerate(exemplars, 1):
        meta = ex.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json_mod.loads(meta)
            except Exception:
                meta = {}

        structured = meta.get("structured_query") or {}
        answer = {
            "entity": structured.get("entity", ""),
            "fields": structured.get("fields"),
            "filters": structured.get("filters"),
            "aggregation": structured.get("aggregation"),
            "groupBy": structured.get("groupBy"),
            "orderBy": structured.get("orderBy"),
            "limit": structured.get("limit", 100),
            "suggested_panel_type": meta.get("panel_type", "table"),
            "suggested_title": meta.get("title", ""),
        }
        answer = {k: v for k, v in answer.items() if v is not None}

        sim = round(float(ex.get("similarity", 0)), 3)
        lines.append(
            f"Example {i} (similarity {sim}):\n"
            f"  Query: \"{ex.get('content', '')}\"\n"
            f"  Answer: {json_mod.dumps(answer, separators=(',', ':'))}"
        )
    return "\n\n".join(lines)


@router.post("/nl-query")
async def nl_query(request: NLQueryRequest):
    """Translate a natural language query into a structured VDL panel query using LLM,
    grounded by retrieval of similar NLQ exemplars from the control plane knowledge base."""
    try:
        from src.services.control_plane.llm_client import get_llm_client
    except ImportError:
        return NLQueryResponse(error="LLM service not available").dict()

    llm = get_llm_client()
    if not llm.available:
        return NLQueryResponse(error="LLM API key not configured").dict()

    exemplars = await _retrieve_nlq_exemplars(request.query, top_k=EXEMPLAR_TOP_K)

    high_confidence_entity: Optional[str] = _select_biased_entity(exemplars)

    schema_context = await _get_schema_context(
        entities=request.available_entities,
        current_entity=request.current_entity or high_confidence_entity,
    )

    exemplar_context = _format_exemplars(exemplars)

    system_content = NL_SYSTEM_PROMPT
    if exemplar_context:
        system_content += (
            "\n\n## Similar Query Examples (from indexed knowledge base)\n"
            "Use these as primary guidance when a similar query exists. "
            "Match the entity, field names, and structure when the example is similar.\n\n"
            + exemplar_context
        )
    system_content += "\n\n## Available Schema\n" + schema_context

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": request.query},
    ]

    try:
        result = await llm.achat(messages, max_tokens=1024, temperature=0.1)
        content = result.get("content", "")

        import json as json_mod
        content_clean = content.strip()
        if content_clean.startswith("```"):
            content_clean = content_clean.split("\n", 1)[-1]
            if content_clean.endswith("```"):
                content_clean = content_clean[:-3].strip()

        parsed = json_mod.loads(content_clean)

        panel_query = {
            "entity": parsed.get("entity", ""),
            "fields": parsed.get("fields"),
            "filters": parsed.get("filters"),
            "aggregation": parsed.get("aggregation"),
            "groupBy": parsed.get("groupBy"),
            "orderBy": parsed.get("orderBy"),
            "limit": parsed.get("limit", 100),
        }
        panel_query = {k: v for k, v in panel_query.items() if v is not None}

        retrieved_summary = [
            {
                "source_id": ex.get("source_id", ""),
                "similarity": round(float(ex.get("similarity", 0)), 4),
            }
            for ex in exemplars[:3]
        ]

        return {
            "panel_query": panel_query,
            "suggested_panel_type": parsed.get("suggested_panel_type", "table"),
            "suggested_title": parsed.get("suggested_title", ""),
            "explanation": parsed.get("explanation", ""),
            "retrieved_exemplars": retrieved_summary,
        }

    except json_mod.JSONDecodeError:
        return NLQueryResponse(
            error="Failed to parse LLM response as structured query",
            explanation=content if 'content' in dir() else "",
        ).dict()
    except Exception as e:
        logger.warning(f"NL query translation failed: {e}")
        return NLQueryResponse(error=str(e)).dict()


# --- NLQ Exemplar Knowledge Base Management ---


class ExemplarUpsertRequest(BaseModel):
    query: str
    entity: str
    fields: Optional[List[str]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    aggregation: Optional[Dict[str, Any]] = None
    groupBy: Optional[List[str]] = None
    orderBy: Optional[str] = None
    limit: Optional[int] = 100
    panel_type: Optional[str] = "table"
    title: Optional[str] = ""
    category: Optional[str] = "user_added"


def _load_nlq_generator_class():
    """Dynamically import NLQExemplarGenerator (parent dir contains a hyphen)."""
    import importlib.util
    import os as _os
    src_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    path = _os.path.join(src_dir, "stages", "semantic-rag", "extractors", "nlq_exemplar_generator.py")
    spec = importlib.util.spec_from_file_location("nlq_exemplar_generator", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.NLQExemplarGenerator


async def _get_cp_services():
    """Return (vector_store, embedding_service) from the initialized control plane, or raise 503."""
    from src.apis import control_plane_api
    await control_plane_api._ensure_init()
    vs = control_plane_api._vector_store
    es = control_plane_api._embedding_service
    if vs is None or es is None:
        raise HTTPException(status_code=503, detail="Control plane not initialized")
    if not getattr(es, "available", False):
        raise HTTPException(status_code=503, detail="Embedding service not available (OpenAI key missing)")
    return vs, es


def _build_exemplar_chunk(req: ExemplarUpsertRequest) -> Dict[str, Any]:
    import hashlib as _h
    structured = {
        "entity": req.entity,
        "fields": req.fields,
        "filters": req.filters,
        "aggregation": req.aggregation,
        "groupBy": req.groupBy,
        "orderBy": req.orderBy,
        "limit": req.limit or 100,
    }
    structured = {k: v for k, v in structured.items() if v is not None}

    qhash = _h.md5(req.query.strip().encode("utf-8")).hexdigest()[:10]
    return {
        "content_type": "nlq_exemplar",
        "source_id": f"nlq_user_{req.entity}_{qhash}",
        "content": req.query.strip(),
        "metadata": {
            "structured_query": structured,
            "panel_type": req.panel_type or "table",
            "title": req.title or "",
            "category": req.category or "user_added",
            "source": "user_added",
        },
    }


@router.post("/nl-query/exemplars")
async def upsert_exemplar(request: ExemplarUpsertRequest):
    """Add or update a single curated NLQ exemplar in the knowledge base."""
    vs, es = await _get_cp_services()
    chunk = _build_exemplar_chunk(request)

    import asyncio as _asyncio
    loop = _asyncio.get_event_loop()
    try:
        emb = await loop.run_in_executor(None, lambda: es.embed_text(chunk["content"]))
        await vs.upsert(
            content_type=chunk["content_type"],
            source_id=chunk["source_id"],
            content=chunk["content"],
            embedding=emb,
            metadata=chunk["metadata"],
        )
        return {"status": "ok", "source_id": chunk["source_id"]}
    except Exception as e:
        logger.warning(f"Exemplar upsert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nl-query/exemplars")
async def list_exemplars(
    offset: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
):
    """List indexed NLQ exemplars."""
    vs, _ = await _get_cp_services()
    try:
        rows, total = await vs.list(
            content_type="nlq_exemplar",
            offset=offset,
            limit=limit,
            search_text=search,
        )

        import json as _jm
        items = []
        for r in rows:
            meta = r.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = _jm.loads(meta)
                except Exception:
                    meta = {}
            items.append({
                "source_id": r.get("source_id", ""),
                "query": r.get("content", ""),
                "structured_query": meta.get("structured_query") or {},
                "panel_type": meta.get("panel_type", "table"),
                "title": meta.get("title", ""),
                "category": meta.get("category", ""),
                "source": meta.get("source", ""),
                "updated_at": str(r.get("updated_at", "")),
            })
        return {"items": items, "total": total, "offset": offset, "limit": limit}
    except Exception as e:
        logger.warning(f"Exemplar list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/nl-query/exemplars/{source_id}")
async def delete_exemplar(source_id: str):
    """Delete a single NLQ exemplar by source_id."""
    vs, _ = await _get_cp_services()
    try:
        from sqlalchemy import text as _text
        engine = vs._conn.engine
        if engine is None:
            raise HTTPException(status_code=503, detail="Vector store engine unavailable")

        import asyncio as _asyncio

        def _do_delete():
            with engine.connect() as conn:
                result = conn.execute(
                    _text(
                        "DELETE FROM control_plane_embeddings "
                        "WHERE content_type = 'nlq_exemplar' AND source_id = :sid"
                    ),
                    {"sid": source_id},
                )
                conn.commit()
                return result.rowcount

        loop = _asyncio.get_event_loop()
        deleted = await loop.run_in_executor(None, _do_delete)
        return {"status": "ok", "deleted": deleted}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Exemplar delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class IndexExemplarsRequest(BaseModel):
    rebuild: bool = False


@router.post("/nl-query/index")
async def index_exemplars(request: Optional[IndexExemplarsRequest] = None):
    """Generate NLQ exemplars from curated YAML + schema templates and upsert into the vector store.

    If `rebuild` is true, all existing nlq_exemplar rows are deleted first.
    """
    vs, es = await _get_cp_services()
    rebuild = bool(request and request.rebuild)

    try:
        Generator = _load_nlq_generator_class()
        gen = Generator()
        exemplars = gen.generate()
    except Exception as e:
        logger.warning(f"Exemplar generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    deleted = 0
    if rebuild:
        try:
            deleted = await vs.delete_by_type("nlq_exemplar")
        except Exception as e:
            logger.warning(f"Failed to clear existing exemplars: {e}")

    if not exemplars:
        return {
            "status": "ok",
            "generated": 0,
            "upserted": 0,
            "deleted": deleted,
            "note": "No exemplars produced (no curated YAML and no schema files)",
        }

    import asyncio as _asyncio
    loop = _asyncio.get_event_loop()

    upserted = 0
    errors = 0
    batch_size = 50

    try:
        for i in range(0, len(exemplars), batch_size):
            batch = exemplars[i : i + batch_size]
            texts = [ex["content"] for ex in batch]
            try:
                embeddings = await loop.run_in_executor(
                    None, lambda t=texts: es.embed_batch(t)
                )
            except Exception as e:
                logger.warning(f"Embedding batch {i} failed: {e}")
                errors += len(batch)
                continue

            for ex, emb in zip(batch, embeddings):
                try:
                    await vs.upsert(
                        content_type=ex["content_type"],
                        source_id=ex["source_id"],
                        content=ex["content"],
                        embedding=emb,
                        metadata=ex["metadata"],
                    )
                    upserted += 1
                except Exception as e:
                    logger.warning(f"Upsert failed for {ex.get('source_id')}: {e}")
                    errors += 1
    except Exception as e:
        logger.warning(f"NLQ exemplar indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "ok",
        "generated": len(exemplars),
        "upserted": upserted,
        "errors": errors,
        "deleted": deleted,
    }
