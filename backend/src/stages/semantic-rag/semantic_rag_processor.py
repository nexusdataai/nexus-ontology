"""
Knowledge Processor — Core Logic for Enterprise Knowledge Graph Building

This module provides the SemanticRagProcessor class that encapsulates all
semantic RAG pipeline logic for use in the journey stage system.

Mirrors the CallProcessor pattern: config dataclass + processor class with
step methods + SSE integration + log callbacks.

Steps:
 1. extract_fdw          — Pull FDW table/column metadata
 2. extract_policies     — Parse policy documents (Markdown/PDF)
 3. extract_workflows    — Parse workflow definitions (YAML/JSON)
 4. extract_integrations — Parse integration mappings (JSON/YAML)
 5. normalize            — Merge, deduplicate, produce .onto bundle
 6. enrich               — LLM semantic enrichment
 7. chunk_embed          — Semantic chunking + embedding generation
 8. load_vector          — Upsert into pgvector
 9. load_graph           — Load relationships into graph DB
10. validate             — Run black-box test scenarios
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

from loguru import logger

try:
    from ...utils.sse_manager import emit_task_progress, emit_log
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    def emit_task_progress(*args, **kwargs): pass
    def emit_log(*args, **kwargs): pass

try:
    from ...config.config_provider import get_config
    _config = get_config()
    AWS_REGION = _config.aws_region
    CONFIG_PROVIDER_AVAILABLE = True
except (ImportError, Exception):
    CONFIG_PROVIDER_AVAILABLE = False
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')


def _find_ek_dir():
    candidates = [
        os.path.join(os.environ.get("APP_ROOT", "/app"), "enterprise-knowledge"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "enterprise-knowledge"),
        "/app/enterprise-knowledge",
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]

_EK_DIR = _find_ek_dir()


@dataclass
class SemanticRagConfig:
    """Configuration for the Semantic RAG pipeline."""
    policy_path: str = ""
    workflow_path: str = ""
    integration_path: str = ""
    schema_dir: str = ""
    policy_s3_prefix: str = ""
    enrich_with_llm: bool = True
    llm_model: str = "gpt-4o-mini"
    graph_hops: int = 2
    min_similarity: float = 0.20
    aws_region: str = "us-east-1"
    s3_bucket: str = ""
    skip_enrichment: bool = False
    skip_graph: bool = False
    skip_validation: bool = False
    skip_unified_schema: bool = False
    skip_fdw_mapping: bool = False

    def __post_init__(self):
        # Phase 3 (data-organization spec): policies/workflows/integrations
        # live authoritatively in DynamoDB via OntoDataService. Leave the
        # per-category path attributes empty so ``_resolve_path_or_s3`` falls
        # through to the DDB download path. Callers can still override for
        # dev/test with explicit paths.
        #
        # Canonical schemas (canonical-entities.yaml + *schema*.yaml) still
        # live on disk under enterprise-knowledge/ - those are the
        # bootstrap seeds for VDLENTITY# rows.
        if not self.schema_dir and os.path.isdir(_EK_DIR):
            self.schema_dir = _EK_DIR


class SemanticRagProcessor:
    """
    Core processor for the Semantic RAG pipeline.

    Handles all 10 steps of knowledge graph construction:
    extraction, normalization, enrichment, embedding, loading, and validation.
    """

    def __init__(
        self,
        config: SemanticRagConfig,
        log_callback: Optional[Callable] = None,
        job_id: str = "",
        journey_id: str = "",
        flush_callback: Optional[Callable] = None,
    ):
        self.config = config
        self.log_callback = log_callback
        self.job_id = job_id
        self.journey_id = journey_id
        self.flush_callback = flush_callback

        self._extracted_docs: Dict[str, list] = {
            "unified_schema": [], "fdw_mapped": [], "fdw": [],
            "mapping_rules": [],
            "policies": [], "workflows": [], "integrations": [],
        }
        self._bundle = None
        self._embeddings: List[Dict] = []
        self._metrics: Dict[str, Any] = {}

    def _log(self, level: str, message: str, step_id: str = None):
        step_prefix = f"[{step_id}] " if step_id else ""
        formatted = f"{step_prefix}{message}"

        if self.log_callback:
            self.log_callback(level, formatted, step_id)
        else:
            logger.log(level.upper(), formatted)

        if SSE_AVAILABLE and self.job_id and step_id:
            emit_log(self.job_id, step_id, level.upper(), formatted)

    def _set_metric(self, key: str, value: Any):
        self._metrics[key] = value

    def _resolve_path_or_s3(self, local_path: str, category: str, step_id: str) -> str:
        """Resolve a knowledge-content directory for the pipeline.

        Phase 3 (data-organization spec): DynamoDB is the authoritative
        source for policies / workflows / integrations. Local paths are
        honored only when explicitly set (dev/test overrides). The DDB
        download path materializes rows into a temp directory that the
        extractors already consume.
        """
        if local_path and os.path.exists(local_path):
            self._log("INFO", f"Using explicit local override: {local_path}", step_id)
            return local_path

        self._log("INFO", f"Downloading {category} from DynamoDB (foundry-workspace)...", step_id)
        try:
            from src.services.onto_data_service import OntoDataService
            svc = OntoDataService()
            temp_dir = svc.download_category_to_temp(category)
            file_count = len([f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))])
            self._log("INFO", f"Materialized {file_count} {category} files from DDB into {temp_dir}", step_id)
            return temp_dir
        except Exception as e:
            self._log("WARNING", f"DDB download failed for {category}: {e}", step_id)
            return ""

    # ─────────────────────────────────────────────────────────────
    # Step 1A: Extract Unified Schema (Schema-First Approach)
    # ─────────────────────────────────────────────────────────────
    def step_extract_unified_schema(self) -> Dict[str, Any]:
        if self.config.skip_unified_schema:
            self._log("INFO", "Skipping unified schema extraction", "extract_unified_schema")
            return {"status": "completed", "documents_extracted": 0, "skipped": True}

        self._log("INFO", "Extracting unified schema from canonical-entities.yaml...", "extract_unified_schema")

        try:
            from .extractors.unified_schema_extractor import UnifiedSchemaExtractor

            class LogAdapter:
                def __init__(self, processor, step_id):
                    self._p = processor
                    self._s = step_id
                def log_info(self, msg): self._p._log("INFO", msg, self._s)

            extractor = UnifiedSchemaExtractor(
                logger=LogAdapter(self, "extract_unified_schema"),
                schema_dir=self.config.schema_dir,
            )
            docs = extractor.extract()
            self._extracted_docs["unified_schema"] = docs

            systems = list(set(d.system for d in docs))
            scor_processes = list(set(
                d.structured_metadata.get("scor_process", "")
                for d in docs if d.structured_metadata.get("scor_process")
            ))

            self._log("INFO", f"Unified schema: {len(docs)} entities across {systems}", "extract_unified_schema")
            self._set_metric("unified_schema_documents", len(docs))
            self._set_metric("unified_schema_systems", systems)
            self._set_metric("unified_schema_scor_processes", scor_processes)

            return {
                "status": "completed",
                "documents_extracted": len(docs),
                "systems": systems,
                "scor_processes": scor_processes,
            }
        except Exception as e:
            self._log("WARNING", f"Unified schema extraction failed (non-fatal): {e}", "extract_unified_schema")
            return {"status": "completed", "documents_extracted": 0, "note": str(e)}

    # ─────────────────────────────────────────────────────────────
    # Step 1B: FDW Mapping Resolution
    # ─────────────────────────────────────────────────────────────
    def step_resolve_fdw_mapping(self) -> Dict[str, Any]:
        schema_docs = self._extracted_docs.get("unified_schema", [])
        if not schema_docs or self.config.skip_fdw_mapping:
            self._log("INFO", "Skipping FDW mapping resolution", "resolve_fdw_mapping")
            return {"status": "completed", "resolved": 0, "skipped": True}

        self._log("INFO", f"Resolving FDW mappings for {len(schema_docs)} schema entities...", "resolve_fdw_mapping")

        try:
            from .extractors.fdw_mapping_resolver import FDWMappingResolver

            class LogAdapter:
                def __init__(self, processor, step_id):
                    self._p = processor
                    self._s = step_id
                def log_info(self, msg): self._p._log("INFO", msg, self._s)

            resolver = FDWMappingResolver(logger=LogAdapter(self, "resolve_fdw_mapping"))
            resolved_docs = resolver.resolve(schema_docs)
            self._extracted_docs["unified_schema"] = resolved_docs

            status_counts = {}
            for doc in resolved_docs:
                status = doc.structured_metadata.get("fdw_mapping_status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

            self._log("INFO", f"FDW mapping: {status_counts}", "resolve_fdw_mapping")
            self._set_metric("fdw_mapping_status", status_counts)

            return {"status": "completed", "resolved": len(resolved_docs), "mapping_status": status_counts}
        except Exception as e:
            self._log("WARNING", f"FDW mapping resolution failed (non-fatal): {e}", "resolve_fdw_mapping")
            return {"status": "completed", "resolved": 0, "note": str(e)}

    # ─────────────────────────────────────────────────────────────
    # Step 1C: Extract FDW Metadata (Legacy — non-schema tables)
    # ─────────────────────────────────────────────────────────────
    def step_extract_fdw(self) -> Dict[str, Any]:
        schema_docs = self._extracted_docs.get("unified_schema", [])
        if schema_docs:
            schema_names = {d.object_name for d in schema_docs if hasattr(d, 'object_name')}
            self._log("INFO", f"Unified schema already extracted {len(schema_docs)} entities — skipping bulk FDW extraction (only virtual data layer entities are indexed)", "extract_fdw")
            self._extracted_docs["fdw"] = []
            self._set_metric("fdw_documents", 0)
            return {"status": "completed", "documents_extracted": 0, "note": f"Skipped: {len(schema_docs)} entities already in unified schema"}

        self._log("INFO", "Extracting FDW metadata (tables, columns, relationships)...", "extract_fdw")

        try:
            from .extractors.fdw_extractor import FDWExtractor

            class LogAdapter:
                def __init__(self, processor, step_id):
                    self._p = processor
                    self._s = step_id
                def log_info(self, msg): self._p._log("INFO", msg, self._s)
                def log_warning(self, msg): self._p._log("WARNING", msg, self._s)
                def log_error(self, msg): self._p._log("ERROR", msg, self._s)

            if SSE_AVAILABLE and self.job_id:
                emit_task_progress(self.job_id, "extract_fdw", "starting", 0, 1)

            extractor = FDWExtractor(logger=LogAdapter(self, "extract_fdw"))
            docs = extractor.extract()
            self._extracted_docs["fdw"] = docs

            if SSE_AVAILABLE and self.job_id:
                emit_task_progress(self.job_id, "extract_fdw", "complete", 1, 1)

            self._log("INFO", f"Extracted {len(docs)} FDW documents", "extract_fdw")
            self._set_metric("fdw_documents", len(docs))

            return {
                "status": "completed",
                "documents_extracted": len(docs),
                "systems": list(set(d.system for d in docs)),
            }
        except Exception as e:
            self._log("WARNING", f"FDW extraction failed (non-fatal): {e}", "extract_fdw")
            return {"status": "completed", "documents_extracted": 0, "note": str(e)}

    # ─────────────────────────────────────────────────────────────
    # Step 2: Extract Mapping Rules (enrich schema docs)
    # ─────────────────────────────────────────────────────────────
    def step_extract_mapping_rules(self) -> Dict[str, Any]:
        schema_docs = self._extracted_docs.get("unified_schema", [])
        if not schema_docs:
            self._log("INFO", "No unified schema docs — skipping mapping rule extraction", "extract_mapping_rules")
            return {"status": "completed", "enriched": 0, "skipped": True}

        self._log("INFO", f"Enriching {len(schema_docs)} schema entities with active mapping rules...", "extract_mapping_rules")

        try:
            from .extractors.mapping_rule_extractor import MappingRuleExtractor

            class LogAdapter:
                def __init__(self, p, s):
                    self._p, self._s = p, s
                def log_info(self, msg): self._p._log("INFO", msg, self._s)

            extractor = MappingRuleExtractor(logger=LogAdapter(self, "extract_mapping_rules"))
            stats = extractor.enrich_with_mapping_rules(schema_docs)

            self._log("INFO", f"Mapping rule enrichment: {stats}", "extract_mapping_rules")
            self._set_metric("mapping_rules_enriched", stats.get("enriched", 0))

            return {"status": "completed", **stats}
        except Exception as e:
            self._log("WARNING", f"Mapping rule extraction failed (non-fatal): {e}", "extract_mapping_rules")
            return {"status": "completed", "enriched": 0, "note": str(e)}

    # ─────────────────────────────────────────────────────────────
    # Step 3: Extract Policy Documents
    # ─────────────────────────────────────────────────────────────
    def step_extract_policies(self) -> Dict[str, Any]:
        self._log("INFO", "Extracting policy documents...", "extract_policies")

        from .extractors.policy_extractor import PolicyExtractor

        class LogAdapter:
            def __init__(self, p, s):
                self._p, self._s = p, s
            def log_info(self, msg): self._p._log("INFO", msg, self._s)

        resolved_path = self._resolve_path_or_s3(self.config.policy_path, "policies", "extract_policies")

        extractor = PolicyExtractor(
            logger=LogAdapter(self, "extract_policies"),
            local_path=resolved_path,
            s3_prefix=self.config.policy_s3_prefix,
        )
        docs = extractor.extract()
        self._extracted_docs["policies"] = docs

        self._log("INFO", f"Extracted {len(docs)} policy documents", "extract_policies")
        self._set_metric("policy_documents", len(docs))

        return {"status": "completed", "documents_extracted": len(docs)}

    # ─────────────────────────────────────────────────────────────
    # Step 3: Extract Workflow Rules
    # ─────────────────────────────────────────────────────────────
    def step_extract_workflows(self) -> Dict[str, Any]:
        self._log("INFO", "Extracting workflow definitions...", "extract_workflows")

        from .extractors.workflow_extractor import WorkflowExtractor

        class LogAdapter:
            def __init__(self, p, s):
                self._p, self._s = p, s
            def log_info(self, msg): self._p._log("INFO", msg, self._s)

        resolved_path = self._resolve_path_or_s3(self.config.workflow_path, "workflows", "extract_workflows")

        extractor = WorkflowExtractor(
            logger=LogAdapter(self, "extract_workflows"),
            local_path=resolved_path,
        )
        docs = extractor.extract()
        self._extracted_docs["workflows"] = docs

        self._log("INFO", f"Extracted {len(docs)} workflow documents", "extract_workflows")
        self._set_metric("workflow_documents", len(docs))

        return {"status": "completed", "documents_extracted": len(docs)}

    # ─────────────────────────────────────────────────────────────
    # Step 4: Extract Integration Mappings
    # ─────────────────────────────────────────────────────────────
    def step_extract_integrations(self) -> Dict[str, Any]:
        self._log("INFO", "Extracting integration mappings...", "extract_integrations")

        from .extractors.integration_extractor import IntegrationExtractor

        class LogAdapter:
            def __init__(self, p, s):
                self._p, self._s = p, s
            def log_info(self, msg): self._p._log("INFO", msg, self._s)

        resolved_path = self._resolve_path_or_s3(self.config.integration_path, "integrations", "extract_integrations")

        extractor = IntegrationExtractor(
            logger=LogAdapter(self, "extract_integrations"),
            local_path=resolved_path,
        )
        docs = extractor.extract()
        self._extracted_docs["integrations"] = docs

        self._log("INFO", f"Extracted {len(docs)} integration mapping documents", "extract_integrations")
        self._set_metric("integration_documents", len(docs))

        return {"status": "completed", "documents_extracted": len(docs)}

    # ─────────────────────────────────────────────────────────────
    # Step 5: Normalize to .onto Bundle
    # ─────────────────────────────────────────────────────────────
    def step_normalize(self) -> Dict[str, Any]:
        self._log("INFO", "Normalizing to .onto bundle format...", "normalize")

        from .normalizer import Normalizer
        from .onto_model import OntoBundle

        class LogAdapter:
            def __init__(self, p, s):
                self._p, self._s = p, s
            def log_info(self, msg): self._p._log("INFO", msg, self._s)

        all_docs = []
        for source, docs in self._extracted_docs.items():
            self._log("INFO", f"  {source}: {len(docs)} documents", "normalize")
            all_docs.extend(docs)

        if not all_docs:
            self._log("WARNING", "No documents extracted from any source", "normalize")
            self._bundle = OntoBundle(bundle_id=f"onto-{self.job_id}", source="empty")
            return {"status": "completed", "total_documents": 0, "note": "No input documents"}

        normalizer = Normalizer(logger=LogAdapter(self, "normalize"))
        self._bundle = normalizer.normalize(all_docs, bundle_id=f"onto-{self.job_id}")

        stats = self._bundle.compute_statistics()
        self._log("INFO", f"Bundle: {stats['total_documents']} docs, "
                          f"{stats['total_relationships']} relationships", "normalize")
        self._set_metric("total_onto_documents", stats['total_documents'])

        if self.config.s3_bucket:
            self._upload_bundle_to_s3()

        return {"status": "completed", "statistics": stats}

    def _upload_bundle_to_s3(self):
        try:
            import boto3
            s3 = boto3.client('s3', region_name=self.config.aws_region)
            bundle_key = f"onto-bundles/{self.job_id}/bundle.onto"
            s3.put_object(
                Bucket=self.config.s3_bucket,
                Key=bundle_key,
                Body=self._bundle.to_json().encode(),
                ContentType='application/json',
            )
            self._log("INFO", f"Bundle uploaded to s3://{self.config.s3_bucket}/{bundle_key}", "normalize")
        except Exception as e:
            self._log("WARNING", f"S3 upload failed: {e}", "normalize")

    # ─────────────────────────────────────────────────────────────
    # Step 6: LLM Semantic Enrichment
    # ─────────────────────────────────────────────────────────────
    def step_enrich(self) -> Dict[str, Any]:
        if self.config.skip_enrichment or not self._bundle:
            self._log("INFO", "Skipping LLM enrichment", "enrich")
            return {"status": "completed", "enriched": 0, "skipped": True}

        self._log("INFO", f"Enriching {len(self._bundle.documents)} documents with LLM...", "enrich")

        from .enricher import Enricher

        class LogAdapter:
            def __init__(self, p, s):
                self._p, self._s = p, s
            def log_info(self, msg): self._p._log("INFO", msg, self._s)

        def _progress_cb(current, total):
            if SSE_AVAILABLE and self.job_id:
                emit_task_progress(self.job_id, "enrich", "llm_enrichment", current, total)

        enricher = Enricher(
            logger=LogAdapter(self, "enrich"),
            model=self.config.llm_model,
            progress_callback=_progress_cb,
        )
        enriched_count, tokens = enricher.enrich_bundle(self._bundle)

        self._log("INFO", f"Enriched {enriched_count} documents, {tokens} tokens used", "enrich")
        self._set_metric("enriched_documents", enriched_count)
        self._set_metric("llm_tokens_used", tokens)

        return {"status": "completed", "enriched": enriched_count, "tokens_used": tokens}

    # ─────────────────────────────────────────────────────────────
    # Step 7: Chunk & Embed
    # ─────────────────────────────────────────────────────────────
    def step_chunk_embed(self) -> Dict[str, Any]:
        if not self._bundle:
            return {"status": "completed", "chunks": 0, "note": "No bundle"}

        self._log("INFO", f"Chunking and embedding {len(self._bundle.documents)} documents...", "chunk_embed")

        from .chunker import Chunker

        class LogAdapter:
            def __init__(self, p, s):
                self._p, self._s = p, s
            def log_info(self, msg): self._p._log("INFO", msg, self._s)

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "chunk_embed", "chunking", 0, len(self._bundle.documents))

        chunker = Chunker(logger=LogAdapter(self, "chunk_embed"))
        self._embeddings = chunker.chunk_and_embed(self._bundle)

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "chunk_embed", "complete", len(self._embeddings), len(self._embeddings))

        self._log("INFO", f"Generated {len(self._embeddings)} embedding chunks", "chunk_embed")
        self._set_metric("embedding_chunks", len(self._embeddings))

        return {"status": "completed", "chunks": len(self._embeddings)}

    # ─────────────────────────────────────────────────────────────
    # Step 8: Load Vector DB
    # ─────────────────────────────────────────────────────────────
    def step_load_vector(self) -> Dict[str, Any]:
        if not self._embeddings:
            return {"status": "completed", "upserted": 0, "note": "No embeddings"}

        self._log("INFO", f"Loading {len(self._embeddings)} chunks into pgvector...", "load_vector")

        from .vector_loader import VectorLoader

        class LogAdapter:
            def __init__(self, p, s):
                self._p, self._s = p, s
            def log_info(self, msg): self._p._log("INFO", msg, self._s)

        def _vec_progress(current, total):
            if SSE_AVAILABLE and self.job_id:
                emit_task_progress(self.job_id, "load_vector", "loading_vectors", current, total)

        loader = VectorLoader(logger=LogAdapter(self, "load_vector"), progress_callback=_vec_progress)
        stats = loader.load(self._embeddings)

        self._log("INFO", f"Vector DB: {stats.get('upserted', 0)} upserted", "load_vector")
        self._set_metric("vector_upserted", stats.get('upserted', 0))

        return {"status": "completed", **stats}

    # ─────────────────────────────────────────────────────────────
    # Step 8B: Index NLQ Exemplars
    # ─────────────────────────────────────────────────────────────
    def step_index_nlq_exemplars(self) -> Dict[str, Any]:
        """Generate NLQ exemplars (curated YAML + schema templates), embed, and upsert
        into the control_plane_embeddings table with content_type 'nlq_exemplar'.

        Runs AFTER load_vector so that the TRUNCATE in VectorLoader does not wipe
        the exemplars. Uses VectorStore.upsert (ON CONFLICT) directly so it does
        not interfere with other content types in the table.
        """
        self._log("INFO", "Generating and indexing NLQ exemplars...", "index_nlq_exemplars")

        try:
            from .extractors.nlq_exemplar_generator import NLQExemplarGenerator
        except Exception as e:
            self._log("WARNING", f"NLQ exemplar generator unavailable: {e}", "index_nlq_exemplars")
            return {"status": "completed", "generated": 0, "upserted": 0, "skipped": True}

        class LogAdapter:
            def __init__(self, p, s):
                self._p, self._s = p, s
            def log_info(self, msg): self._p._log("INFO", msg, self._s)

        generator = NLQExemplarGenerator(logger=LogAdapter(self, "index_nlq_exemplars"))
        exemplars = generator.generate()

        if not exemplars:
            self._log("INFO", "No NLQ exemplars produced", "index_nlq_exemplars")
            return {"status": "completed", "generated": 0, "upserted": 0}

        try:
            from src.services.fdw_connection_manager import PostgreSQLConnectionManager
            from src.services.control_plane.vector_store import VectorStore
            from src.services.control_plane.embedding_service import EmbeddingService
            from src.config.fdw_config import FDWConfig

            config = FDWConfig.from_environment()
            conn_mgr = PostgreSQLConnectionManager(config)
            embedding_svc = EmbeddingService()
        except Exception as e:
            self._log("WARNING", f"Vector store init failed: {e}", "index_nlq_exemplars")
            return {"status": "completed", "generated": len(exemplars), "upserted": 0, "error": str(e)}

        if not embedding_svc.available:
            self._log("WARNING", "Embedding service not available — skipping NLQ exemplar indexing",
                      "index_nlq_exemplars")
            return {"status": "completed", "generated": len(exemplars), "upserted": 0, "skipped": True}

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(conn_mgr.initialize())
            store = VectorStore(conn_mgr)

            upserted = 0
            errors = 0
            batch_size = 50
            for i in range(0, len(exemplars), batch_size):
                batch = exemplars[i : i + batch_size]
                texts = [ex["content"] for ex in batch]
                try:
                    embeddings = embedding_svc.embed_batch(texts)
                except Exception as e:
                    self._log("WARNING", f"Embedding batch {i} failed: {e}", "index_nlq_exemplars")
                    errors += len(batch)
                    continue

                for ex, emb in zip(batch, embeddings):
                    try:
                        loop.run_until_complete(store.upsert(
                            content_type=ex["content_type"],
                            source_id=ex["source_id"],
                            content=ex["content"],
                            embedding=emb,
                            metadata=ex["metadata"],
                        ))
                        upserted += 1
                    except Exception as e:
                        errors += 1
                        if errors <= 5:
                            self._log("WARNING", f"Upsert failed for {ex.get('source_id')}: {e}",
                                      "index_nlq_exemplars")

                if SSE_AVAILABLE and self.job_id:
                    emit_task_progress(self.job_id, "index_nlq_exemplars", "indexing",
                                        i + len(batch), len(exemplars))

            self._log("INFO",
                      f"NLQ exemplars: {upserted}/{len(exemplars)} upserted ({errors} errors)",
                      "index_nlq_exemplars")
            self._set_metric("nlq_exemplars_upserted", upserted)

            return {
                "status": "completed",
                "generated": len(exemplars),
                "upserted": upserted,
                "errors": errors,
            }
        except Exception as e:
            self._log("WARNING", f"NLQ exemplar indexing failed: {e}", "index_nlq_exemplars")
            return {"status": "completed", "generated": len(exemplars), "upserted": 0, "error": str(e)}

    # ─────────────────────────────────────────────────────────────
    # Step 9: Load Graph DB
    # ─────────────────────────────────────────────────────────────
    def step_load_graph(self) -> Dict[str, Any]:
        if self.config.skip_graph or not self._bundle:
            self._log("INFO", "Skipping graph loading", "load_graph")
            return {"status": "completed", "nodes_created": 0, "skipped": True}

        self._log("INFO", "Loading relationships into graph DB...", "load_graph")

        from .graph_loader import GraphLoader

        class LogAdapter:
            def __init__(self, p, s):
                self._p, self._s = p, s
            def log_info(self, msg): self._p._log("INFO", msg, self._s)

        def _graph_progress(current, total):
            if SSE_AVAILABLE and self.job_id:
                emit_task_progress(self.job_id, "load_graph", "loading_graph", current, total)

        loader = GraphLoader(logger=LogAdapter(self, "load_graph"), progress_callback=_graph_progress)
        stats = loader.load(self._bundle)

        self._log("INFO", f"Graph: {stats.get('nodes_created', 0)} nodes, "
                          f"{stats.get('edges_created', 0)} edges", "load_graph")

        return {"status": "completed", **stats}

    # ─────────────────────────────────────────────────────────────
    # Step 10: Validate Quality
    # ─────────────────────────────────────────────────────────────
    def step_validate(self) -> Dict[str, Any]:
        if self.config.skip_validation:
            self._log("INFO", "Skipping validation", "validate")
            return {"status": "completed", "skipped": True}

        self._log("INFO", "Running 10 black-box test scenarios...", "validate")

        from .validator import SemanticRagValidator

        class LogAdapter:
            def __init__(self, p, s):
                self._p, self._s = p, s
            def log_info(self, msg): self._p._log("INFO", msg, self._s)

        validator = SemanticRagValidator(logger=LogAdapter(self, "validate"))
        report = validator.run_tests()

        avg = report.get("average_score", 0)
        passed = report.get("tests_passed", 0)
        total = report.get("total_tests", 0)

        self._log("INFO", f"Validation: {passed}/{total} tests passed, "
                          f"avg score {avg:.1f}/6.0", "validate")
        self._set_metric("validation_avg_score", avg)

        if self.config.s3_bucket:
            self._upload_report_to_s3(report)

        return {"status": "completed", "report": report}

    def _upload_report_to_s3(self, report):
        try:
            import boto3
            s3 = boto3.client('s3', region_name=self.config.aws_region)
            key = f"onto-bundles/{self.job_id}/validation-report.json"
            s3.put_object(
                Bucket=self.config.s3_bucket,
                Key=key,
                Body=json.dumps(report, indent=2, default=str).encode(),
                ContentType='application/json',
            )
            self._log("INFO", f"Report uploaded to s3://{self.config.s3_bucket}/{key}", "validate")
        except Exception as e:
            self._log("WARNING", f"Report S3 upload failed: {e}", "validate")

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self._metrics)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "extracted": {src: len(docs) for src, docs in self._extracted_docs.items()},
            "total_documents": sum(len(docs) for docs in self._extracted_docs.values()),
            "bundle_documents": len(self._bundle.documents) if self._bundle else 0,
            "embeddings": len(self._embeddings),
            "metrics": self._metrics,
        }
