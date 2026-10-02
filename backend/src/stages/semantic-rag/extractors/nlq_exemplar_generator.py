"""
NLQ Exemplar Generator

Produces a corpus of (natural language query, structured VDL query) pairs that
serve as a few-shot retrieval index for the AI Query Builder. Two sources are
combined:

  1. Curated exemplars: enterprise-knowledge/nlq-exemplars.yaml — domain
     experts hand-write high-precision query patterns for critical entities.
     Each entry carries a list of `query_variants` (substantively different
     phrasings of the same intent). The generator multiplies each variant by:
       a) Synonym substitution (using the YAML's `synonyms` map)
       b) Prefix templates ("show ", "list ", "get me ", etc.)
     so one curated entry produces 20-50 indexed rows in the vector store.
     The legacy single-string `query` field is still accepted.
  2. Schema-driven templates: for each canonical entity declared in
     enterprise-knowledge/canonical-entities.yaml, generate canonical query
     patterns (top-N rankings, group-by counts, distributions, time series)
     from the entity's key_fields and their data_type metadata.

Each exemplar is emitted as a dict of:
    content_type : "nlq_exemplar"
    source_id    : "nlq_<entity>_<hash>"
    content      : the natural language query text (gets embedded for similarity search)
    metadata     : the structured panel query answer (entity, fields, filters,
                   aggregation, groupBy, orderBy, limit, panel_type, title)

The generator does NOT compute embeddings or write to the vector store —
callers (the pipeline step or the API endpoint) handle that, so this module
stays I/O-free and unit-testable.
"""

import glob
import hashlib
import os
import re
from typing import Any, Dict, List, Optional

import yaml


NUMERIC_TYPES = {
    "number", "integer", "float", "decimal",
    "currency", "percent", "money",
}
TIME_TYPES = {"datetime", "date", "time", "timestamp"}
CATEGORICAL_TYPES = {"picklist", "text", "string", "id", "lookup", "boolean"}


# Prefix templates applied to each (variant, synonym-substituted) phrasing.
# Empty string keeps the bare form. Skipped when the phrasing already starts
# with one of PREFIX_SKIP_STARTERS to avoid duplications like "show show ...".
PREFIX_TEMPLATES = [
    "",
    "show ",
    "show me ",
    "list ",
    "get ",
    "get me ",
    "give me ",
    "display ",
    "find ",
    "what are ",
    "which are the ",
]

PREFIX_SKIP_STARTERS = (
    "show ", "list ", "get ", "give ", "display ", "find ",
    "what ", "which ", "how ", "where ", "who ",
)


def _find_enterprise_knowledge_dir(override: Optional[str] = None) -> str:
    if override and os.path.isdir(override):
        return override
    candidates = [
        os.path.join(os.environ.get("APP_ROOT", "/app"), "enterprise-knowledge"),
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
            "enterprise-knowledge",
        ),
        "/app/enterprise-knowledge",
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]


def _hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:10]


def _classify_field(data_type: str) -> str:
    dt = (data_type or "").strip().lower()
    if dt in NUMERIC_TYPES:
        return "numeric"
    if dt in TIME_TYPES:
        return "time"
    return "categorical"


class NLQExemplarGenerator:
    """Builds NLQ exemplars from curated YAML + schema-driven templates."""

    def __init__(self, logger=None, schema_dir: str = "", curated_file: str = ""):
        self._log = logger
        self._schema_dir = _find_enterprise_knowledge_dir(schema_dir or None)
        self._curated_file = curated_file or os.path.join(self._schema_dir, "nlq-exemplars.yaml")

    def _info(self, msg: str):
        if self._log:
            try:
                self._log.log_info(msg)
            except Exception:
                pass

    def generate(self) -> List[Dict[str, Any]]:
        exemplars: List[Dict[str, Any]] = []

        curated = self._load_curated()
        self._info(f"Curated NLQ exemplars: {len(curated)}")
        exemplars.extend(curated)

        templated = self._load_templated()
        self._info(f"Templated NLQ exemplars: {len(templated)}")
        exemplars.extend(templated)

        deduped = self._deduplicate(exemplars)
        self._info(f"NLQ exemplar generation complete: {len(deduped)} unique exemplars")
        return deduped

    def _load_curated(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self._curated_file):
            self._info(f"No curated exemplar file at {self._curated_file}")
            return []

        try:
            with open(self._curated_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            self._info(f"Failed to load curated exemplars: {e}")
            return []

        synonyms = self._compile_synonyms(data.get("synonyms") or {})

        out: List[Dict[str, Any]] = []
        for item in data.get("exemplars", []) or []:
            entity = (item.get("entity") or "").strip()
            if not entity:
                continue

            base_variants = self._extract_base_variants(item)
            if not base_variants:
                continue

            structured = {
                "entity": entity,
                "fields": item.get("fields") or None,
                "filters": item.get("filters") or None,
                "aggregation": item.get("aggregation") or None,
                "groupBy": item.get("groupBy") or item.get("group_by") or None,
                "orderBy": item.get("orderBy") or item.get("order_by") or None,
                "limit": item.get("limit") or 100,
            }
            structured = {k: v for k, v in structured.items() if v is not None}

            metadata_template = {
                "structured_query": structured,
                "panel_type": item.get("panel_type") or item.get("suggested_panel_type") or "table",
                "title": item.get("title") or item.get("suggested_title") or "",
                "category": item.get("category") or "curated",
                "source": "curated",
            }

            # Layer 1: variants -> Layer 2: synonym substitution -> Layer 3: prefix templates
            phrasings = self._expand_phrasings(base_variants, synonyms)

            seen_for_entry: set = set()
            for phrase in phrasings:
                norm = phrase.strip().lower()
                if not norm or norm in seen_for_entry:
                    continue
                seen_for_entry.add(norm)
                out.append({
                    "content_type": "nlq_exemplar",
                    "source_id": f"nlq_curated_{entity}_{_hash(phrase)}",
                    "content": phrase,
                    "metadata": dict(metadata_template),
                })
        return out

    @staticmethod
    def _extract_base_variants(item: Dict[str, Any]) -> List[str]:
        """Read query_variants (preferred) or fall back to single query string."""
        variants: List[str] = []
        raw_variants = item.get("query_variants")
        if isinstance(raw_variants, list):
            for v in raw_variants:
                if isinstance(v, str) and v.strip():
                    variants.append(v.strip())
        legacy = item.get("query")
        if isinstance(legacy, str) and legacy.strip():
            variants.append(legacy.strip())
        seen = set()
        unique: List[str] = []
        for v in variants:
            key = v.lower()
            if key not in seen:
                seen.add(key)
                unique.append(v)
        return unique

    @staticmethod
    def _compile_synonyms(raw: Dict[str, Any]) -> List[tuple]:
        """Return list of (compiled_pattern, [substitutes]) pairs.

        Match is case-insensitive with whole-word boundaries so that
        substituting 'order' does not accidentally hit 'orderBy'.
        """
        compiled: List[tuple] = []
        if not isinstance(raw, dict):
            return compiled
        for key, values in raw.items():
            if not isinstance(key, str) or not key.strip():
                continue
            if isinstance(values, str):
                values = [values]
            if not isinstance(values, list):
                continue
            substitutes = [v for v in values if isinstance(v, str) and v.strip()]
            if not substitutes:
                continue
            pattern = re.compile(r"\b" + re.escape(key) + r"\b", flags=re.IGNORECASE)
            compiled.append((pattern, substitutes))
        return compiled

    @staticmethod
    def _expand_phrasings(base_variants: List[str], synonyms: List[tuple]) -> List[str]:
        """Apply synonym substitution (single-term-at-a-time) then prefix templates."""
        # Layer 2: Synonym substitution. For each variant, emit the original plus
        # one extra variant per synonym hit (single substitution per emit). This
        # avoids combinatorial blow-up while still covering common term swaps.
        synonym_expanded: List[str] = []
        for v in base_variants:
            synonym_expanded.append(v)
            for pattern, substitutes in synonyms:
                if not pattern.search(v):
                    continue
                for sub in substitutes:
                    swapped = pattern.sub(sub, v, count=1)
                    if swapped and swapped != v:
                        synonym_expanded.append(swapped)

        # Layer 3: Prefix templates. Skip prefixing variants that already start
        # with an imperative or question word — re-prefixing them sounds wrong.
        prefixed: List[str] = []
        for v in synonym_expanded:
            v_lower = v.lower()
            already_starts = any(v_lower.startswith(s) for s in PREFIX_SKIP_STARTERS)
            if already_starts:
                prefixed.append(v)
                continue
            for prefix in PREFIX_TEMPLATES:
                prefixed.append((prefix + v).strip())
        return prefixed

    def _load_templated(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        # Single canonical catalog file. Fallback glob accommodates a future
        # rename to canonical-*.yaml without re-deploying this file.
        canonical_path = os.path.join(self._schema_dir, "canonical-entities.yaml")
        if os.path.isfile(canonical_path):
            files = [canonical_path]
        else:
            files = sorted(glob.glob(os.path.join(self._schema_dir, "canonical-*.yaml")))

        for path in files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except Exception as e:
                self._info(f"Failed to parse {path}: {e}")
                continue

            for domain in data.get("domains", []) or []:
                domain_name = domain.get("name", "")
                for entity_def in domain.get("entities", []) or []:
                    entity = entity_def.get("name") or ""
                    if not entity:
                        continue
                    semantic = entity_def.get("semantic") or entity_def.get("description") or ""
                    fields = self._extract_fields(entity_def)
                    out.extend(self._templates_for_entity(entity, domain_name, semantic, fields))
        return out

    @staticmethod
    def _extract_fields(table: Dict[str, Any]) -> List[Dict[str, str]]:
        fields = []
        for kf in table.get("key_fields", []) or []:
            name = kf.get("name") or ""
            if not name:
                continue
            fields.append({
                "name": name,
                "data_type": kf.get("data_type") or "Text",
                "semantic": kf.get("semantic") or "",
            })
        return fields

    def _templates_for_entity(
        self,
        entity: str,
        domain_name: str,
        semantic: str,
        fields: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        if not fields:
            return []

        numeric_fields = [f for f in fields if _classify_field(f["data_type"]) == "numeric"]
        time_fields = [f for f in fields if _classify_field(f["data_type"]) == "time"]
        categorical_fields = [f for f in fields if _classify_field(f["data_type"]) == "categorical"]

        out: List[Dict[str, Any]] = []
        entity_phrase = entity.replace("_", " ")

        for nf in numeric_fields[:3]:
            metric_phrase = nf["name"].replace("_", " ").lower()
            queries = [
                f"show top 10 {entity_phrase} by {metric_phrase}",
                f"highest {metric_phrase} in {entity_phrase}",
                f"top {entity_phrase} ranked by {metric_phrase}",
            ]
            structured = {
                "entity": entity,
                "fields": [fields[0]["name"], nf["name"]],
                "orderBy": f"{nf['name']} DESC",
                "limit": 10,
            }
            for q in queries:
                out.append(self._make_entry(
                    entity=entity, query=q, structured=structured,
                    panel_type="bar-chart",
                    title=f"Top 10 {entity_phrase} by {metric_phrase}",
                    category="top_n_ranking",
                    source="templated",
                ))

        for cat in categorical_fields[:2]:
            cat_phrase = cat["name"].replace("_", " ").lower()
            queries = [
                f"count of {entity_phrase} by {cat_phrase}",
                f"how many {entity_phrase} per {cat_phrase}",
                f"breakdown of {entity_phrase} grouped by {cat_phrase}",
            ]
            structured = {
                "entity": entity,
                "fields": [cat["name"]],
                "aggregation": {"function": "count", "field": None},
                "groupBy": [cat["name"]],
                "orderBy": "value DESC",
                "limit": 50,
            }
            for q in queries:
                out.append(self._make_entry(
                    entity=entity, query=q, structured=structured,
                    panel_type="bar-chart",
                    title=f"{entity_phrase} count by {cat_phrase}",
                    category="group_by_count",
                    source="templated",
                ))

        for cat in categorical_fields[:2]:
            for nf in numeric_fields[:2]:
                cat_phrase = cat["name"].replace("_", " ").lower()
                metric_phrase = nf["name"].replace("_", " ").lower()
                queries = [
                    f"total {metric_phrase} by {cat_phrase} in {entity_phrase}",
                    f"sum of {metric_phrase} grouped by {cat_phrase}",
                    f"average {metric_phrase} per {cat_phrase}",
                ]
                for i, q in enumerate(queries):
                    func = "avg" if "average" in q else "sum"
                    structured = {
                        "entity": entity,
                        "fields": [cat["name"], nf["name"]],
                        "aggregation": {"function": func, "field": nf["name"]},
                        "groupBy": [cat["name"]],
                        "orderBy": "value DESC",
                        "limit": 50,
                    }
                    out.append(self._make_entry(
                        entity=entity, query=q, structured=structured,
                        panel_type="bar-chart",
                        title=f"{func.title()} {metric_phrase} by {cat_phrase}",
                        category="group_by_aggregate",
                        source="templated",
                    ))

        if time_fields and numeric_fields:
            tf = time_fields[0]
            for nf in numeric_fields[:2]:
                metric_phrase = nf["name"].replace("_", " ").lower()
                queries = [
                    f"{metric_phrase} over time for {entity_phrase}",
                    f"trend of {metric_phrase} in {entity_phrase}",
                    f"{entity_phrase} {metric_phrase} timeline",
                ]
                structured = {
                    "entity": entity,
                    "fields": [tf["name"], nf["name"]],
                    "aggregation": {"function": "sum", "field": nf["name"]},
                    "groupBy": [tf["name"]],
                    "orderBy": f"{tf['name']} ASC",
                    "limit": 200,
                }
                for q in queries:
                    out.append(self._make_entry(
                        entity=entity, query=q, structured=structured,
                        panel_type="time-series",
                        title=f"{metric_phrase} trend for {entity_phrase}",
                        category="time_series",
                        source="templated",
                    ))

        for nf in numeric_fields[:2]:
            metric_phrase = nf["name"].replace("_", " ").lower()
            queries = [
                f"distribution of {metric_phrase} in {entity_phrase}",
                f"histogram of {metric_phrase} for {entity_phrase}",
            ]
            structured = {
                "entity": entity,
                "fields": [nf["name"]],
                "limit": 1000,
            }
            for q in queries:
                out.append(self._make_entry(
                    entity=entity, query=q, structured=structured,
                    panel_type="histogram",
                    title=f"Distribution of {metric_phrase}",
                    category="distribution",
                    source="templated",
                ))

        queries = [
            f"list all {entity_phrase}",
            f"show {entity_phrase} records",
            f"recent {entity_phrase}",
        ]
        structured = {
            "entity": entity,
            "limit": 100,
        }
        for q in queries:
            out.append(self._make_entry(
                entity=entity, query=q, structured=structured,
                panel_type="table",
                title=f"{entity_phrase} records",
                category="list_all",
                source="templated",
            ))

        return out

    @staticmethod
    def _make_entry(
        entity: str,
        query: str,
        structured: Dict[str, Any],
        panel_type: str,
        title: str,
        category: str,
        source: str,
    ) -> Dict[str, Any]:
        metadata = {
            "structured_query": structured,
            "panel_type": panel_type,
            "title": title,
            "category": category,
            "source": source,
        }
        return {
            "content_type": "nlq_exemplar",
            "source_id": f"nlq_{source}_{entity}_{_hash(query)}",
            "content": query,
            "metadata": metadata,
        }

    @staticmethod
    def _deduplicate(exemplars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        out: List[Dict[str, Any]] = []
        for ex in exemplars:
            key = (ex["content"].strip().lower(), ex["metadata"]["structured_query"].get("entity", ""))
            if key in seen:
                continue
            seen.add(key)
            out.append(ex)
        return out
