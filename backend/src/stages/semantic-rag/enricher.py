"""
LLM Semantic Enricher

Smart enrichment strategy:
- Schema entities (FDW tables/columns): auto-generate descriptions from structured metadata (instant, no LLM cost)
- Policies, workflows, integrations: LLM enrichment via gpt-4o-mini (parallel)

This reduces LLM calls from ~1680 to ~50, cutting enrichment from 20+ min to <1 min.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Callable, Optional, List
from onto_model import OntoBundle, OntoDocument

ENRICHMENT_PROMPT_TEMPLATE = """You are an enterprise knowledge engineer. Given the raw metadata below,
generate a concise semantic description that captures:

1. What this entity represents in business terms
2. Business rules and constraints that apply
3. Dependent workflows or processes
4. Cross-system impacts (if any)
5. Who owns it and what approvals are needed

Keep the description factual and structured. Use bullet points for rules/constraints.
Do NOT invent information not present in the raw metadata.

"""

CONCURRENCY = 8
MAX_RETRIES = 3
LLM_TIMEOUT = 30.0
SCHEMA_CATEGORIES = {"schema", "fdw", "database", "table", "column"}


class Enricher:
    def __init__(self, logger=None, model: str = "gpt-4o-mini",
                 progress_callback: Optional[Callable[[int, int], None]] = None):
        self._log = logger
        self._model = model
        self._total_tokens = 0
        self._progress_callback = progress_callback

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def _emit_progress(self, done: int, total: int):
        if self._progress_callback:
            try:
                self._progress_callback(done, total)
            except Exception:
                pass

    def enrich_bundle(self, bundle: OntoBundle) -> Tuple[int, int]:
        total = len(bundle.documents)
        schema_docs: List[OntoDocument] = []
        llm_docs: List[OntoDocument] = []

        for doc in bundle.documents:
            if self._is_schema_entity(doc):
                schema_docs.append(doc)
            else:
                llm_docs.append(doc)

        self._info(f"Enrichment plan: {len(schema_docs)} schema (auto-generate) + {len(llm_docs)} complex (LLM) = {total} total")

        start_time = time.time()
        enriched = 0

        for doc in schema_docs:
            doc.content = self._auto_enrich_schema(doc)
            enriched += 1

        self._emit_progress(enriched, total)
        schema_elapsed = time.time() - start_time
        self._info(f"Schema auto-enrichment: {len(schema_docs)} docs in {schema_elapsed:.1f}s")

        tokens = 0
        if llm_docs:
            llm_enriched, tokens = self._enrich_with_llm(llm_docs, enriched, total)
            enriched += llm_enriched

        self._append_cross_references(bundle)

        elapsed = time.time() - start_time
        self._info(
            f"Enrichment complete: {enriched}/{total} in {elapsed:.1f}s, "
            f"{len(llm_docs)} LLM calls, {tokens:,} tokens"
        )
        self._emit_progress(total, total)
        self._total_tokens = tokens
        return enriched, tokens

    def _append_cross_references(self, bundle: OntoBundle):
        """Append cross-reference metadata to content for better retrieval coverage."""
        for doc in bundle.documents:
            meta = doc.structured_metadata or {}
            additions = []

            related_entities = meta.get("related_entities", [])
            if related_entities and isinstance(related_entities, list):
                additions.append("Related Entities: " + ", ".join(str(e) for e in related_entities[:15]))

            related_policies = meta.get("related_policies", [])
            if related_policies and isinstance(related_policies, list):
                additions.append("Related Policies: " + ", ".join(str(p) for p in related_policies[:10]))

            related_workflows = meta.get("related_workflows", [])
            if related_workflows and isinstance(related_workflows, list):
                additions.append("Related Workflows: " + ", ".join(str(w) for w in related_workflows[:10]))

            triggered_by = meta.get("triggered_by_workflows", [])
            if triggered_by and isinstance(triggered_by, list):
                additions.append("Triggered By Workflows: " + ", ".join(str(w) for w in triggered_by[:10]))

            used_by = meta.get("used_by_apps", [])
            if used_by and isinstance(used_by, list):
                additions.append("Used By Applications: " + ", ".join(str(a) for a in used_by[:10]))

            use_case = meta.get("use_case", "")
            if use_case and use_case not in doc.content:
                additions.append(f"Use Case: {use_case}")

            scor = meta.get("scor_process", "")
            if scor and scor not in doc.content:
                additions.append(f"SCOR Process: {scor}")

            if additions:
                doc.content += "\n" + "\n".join(additions)

    def _is_schema_entity(self, doc: OntoDocument) -> bool:
        if doc.category and doc.category.lower() in SCHEMA_CATEGORIES:
            return True
        if doc.entity_type and doc.entity_type.lower() in ("schema", "table", "column", "view"):
            return True
        if doc.source and doc.source.lower() in ("fdw", "unified_schema", "enterprise_schema"):
            return True
        return False

    def _auto_enrich_schema(self, doc: OntoDocument) -> str:
        meta = doc.structured_metadata or {}
        cols = meta.get("columns", []) or meta.get("fdw_columns", [])
        server = meta.get("server", doc.system or "unknown")
        schema = meta.get("schema", "public")
        col_count = meta.get("column_count", meta.get("fdw_column_count", len(cols)))

        parts = []

        if doc.source in ("unified_schema", "enterprise_schema"):
            parts.append(doc.content)
        else:
            parts.append(f"Database table '{doc.object_name}' in {server} system ({schema} schema).")
            parts.append(f"Contains {col_count} columns.")

        domain = meta.get("domain", "")
        if domain and doc.source not in ("unified_schema", "enterprise_schema"):
            parts.append(f"Domain: {domain}")

        scor = meta.get("scor_process", "")
        if scor:
            parts.append(f"SCOR Process: {scor}")

        gs1 = meta.get("gs1_standard", "")
        if gs1:
            parts.append(f"GS1 Standard: {gs1}")

        fdw_status = meta.get("fdw_mapping_status", "")
        mapping_source = meta.get("mapping_source", "")
        if fdw_status == "mapped":
            if mapping_source and mapping_source.startswith("simulator:"):
                parts.append(f"Data Status: SIMULATOR — data available via {mapping_source} in-memory simulator.")
            else:
                fdw_col_count = meta.get("fdw_column_count", 0)
                parts.append(f"Data Status: LIVE FDW — connected to foreign table with {fdw_col_count} queryable columns.")
        elif fdw_status == "mapped_via_rule":
            rule_name = meta.get("mapping_rule_name", "")
            source_table = meta.get("mapping_source_table", "")
            source_schema = meta.get("mapping_source_schema", "")
            parts.append(f"Data Status: MAPPED VIA RULE — '{rule_name}' routes queries to {source_schema}.{source_table}.")
        elif fdw_status == "virtual":
            parts.append("Data Status: VIRTUAL — data flows via integration sync, not direct query.")
        elif fdw_status == "unmapped":
            parts.append("Data Status: PENDING — no live foreign table or simulator connected yet.")

        if cols and doc.source not in ("unified_schema", "enterprise_schema"):
            col_lines = [f"  - {c.get('name', '?')} ({c.get('type', '?')})" for c in cols[:30]]
            parts.append("Columns:\n" + "\n".join(col_lines))
            if len(cols) > 30:
                parts.append(f"  ... and {len(cols) - 30} more columns")

        key_fields = meta.get("key_fields", []) or meta.get("key_field_details", [])
        if key_fields:
            kf_lines = []
            for kf in key_fields[:25]:
                if isinstance(kf, dict):
                    line = f"  - {kf.get('name', '?')} ({kf.get('data_type', '?')})"
                    if kf.get("semantic"):
                        line += f": {kf['semantic']}"
                    if kf.get("risk_level") and kf["risk_level"] != "medium":
                        line += f" [risk: {kf['risk_level']}]"
                    constraints = kf.get("constraints", [])
                    if constraints:
                        line += "\n    Constraints: " + "; ".join(str(c) for c in constraints[:5])
                    kf_lines.append(line)
                else:
                    kf_lines.append(f"  - {kf}")
            parts.append("Key Fields:\n" + "\n".join(kf_lines))
            if len(key_fields) > 25:
                parts.append(f"  ... and {len(key_fields) - 25} more fields")

        mapping_field_maps = meta.get("mapping_field_maps", [])
        if mapping_field_maps:
            fm_lines = [f"  - {fm.get('source', '?')} -> {fm.get('target', '?')}" for fm in mapping_field_maps[:15]]
            parts.append("Field Mappings (from mapping rule):\n" + "\n".join(fm_lines))

        rels = doc.relationships
        if rels:
            rel_lines = [f"  - {r.relation_type} -> {r.target_id}" for r in rels[:10]]
            parts.append("Relationships:\n" + "\n".join(rel_lines))

        if doc.source in ("unified_schema", "enterprise_schema"):
            source_label = "Unified schema overlay (virtual data layer)"
        elif doc.source == "fdw":
            source_label = "FDW foreign data wrapper"
        else:
            source_label = doc.source or "unknown"
        parts.append(f"Source: {source_label}.")
        parts.append(f"Category: {doc.category or 'schema'}")

        return "\n".join(parts)

    def _enrich_with_llm(self, docs: List[OntoDocument], base_done: int, total: int) -> Tuple[int, int]:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            try:
                from src.config.config_provider import get_config
                config = get_config()
                api_key = config.openai_api_key or ""
            except Exception:
                pass

        if not api_key:
            self._info("No OpenAI API key — skipping LLM enrichment for complex docs")
            return len(docs), 0

        try:
            import openai
            client = openai.OpenAI(api_key=api_key, timeout=LLM_TIMEOUT)
        except ImportError:
            self._info("openai package not installed — skipping LLM enrichment")
            return len(docs), 0

        self._info(f"LLM enrichment: {len(docs)} documents, concurrency={CONCURRENCY}")

        enriched = 0
        failed = 0
        tokens = 0
        start_time = time.time()

        def _process_doc(idx_doc):
            idx, doc = idx_doc
            try:
                result, usage = self._call_llm(client, doc)
                return (idx, result, usage, None)
            except Exception as e:
                return (idx, None, 0, e)

        with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            futures = {
                executor.submit(_process_doc, (i, doc)): (i, doc)
                for i, doc in enumerate(docs)
            }
            for future in as_completed(futures):
                idx, doc = futures[future]
                result_idx, result, usage, err = future.result()
                if result:
                    doc.content = result
                    enriched += 1
                    tokens += usage
                else:
                    failed += 1
                    if failed <= 5 and err:
                        self._info(f"  Failed doc {doc.id}: {err}")

                done = enriched + failed
                self._emit_progress(base_done + done, total)

        elapsed = time.time() - start_time
        self._info(
            f"LLM enrichment done: {enriched}/{len(docs)} in {elapsed:.1f}s, "
            f"{tokens:,} tokens"
        )
        return enriched, tokens

    def _call_llm(self, client, doc: OntoDocument) -> Tuple[str, int]:
        prompt = (
            ENRICHMENT_PROMPT_TEMPLATE
            + "Raw metadata:\n"
            + doc.content[:2000]
            + f"\n\nEntity type: {doc.entity_type}"
            + f"\nSystem: {doc.system}"
            + f"\nCategory: {doc.category}"
            + "\n\nGenerate the enriched semantic description:"
        )

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=400,
                )
                usage = response.usage.total_tokens if response.usage else 0
                content = response.choices[0].message.content.strip()
                return content, usage
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
        raise last_error
