"""
Canonical ETL pipeline step and studio node catalog (single source of truth).
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

ETLSourceType = Literal[
    "social_listening",
    "file_uploads",
    "google_drive",
    "external_full",
    "generic",
]

EXTERNAL_SOURCE_TYPES = frozenset(
    {"social_listening", "file_uploads", "google_drive", "external_full"}
)

# Runtime step ids executed by ETLPipelineStage / processor
ETL_RUNTIME_STEPS: List[Dict[str, str]] = [
    {"id": "extract", "name": "Extract Source Data", "description": "Read data from source system (FDW, file, API)"},
    {"id": "validate_schema", "name": "Validate Schema", "description": "Validate source data against mapping rule field definitions"},
    {"id": "transform", "name": "Transform Data", "description": "Apply field mappings and business logic transforms"},
    {"id": "load", "name": "Load Data", "description": "Write transformed data to hydrated storage"},
    {"id": "verify", "name": "Verify Results", "description": "Row count checks, null validation, data quality"},
]

ETL_VDL_RUNTIME_STEPS: List[Dict[str, str]] = [
    {"id": "register_vdl", "name": "Register VDL Mappings", "description": "Create active FDW mapping rules for virtual entities"},
    {"id": "materialize_warehouse", "name": "Materialize Warehouse", "description": "Refresh warehouse snapshot tables from external feeds"},
]


def runtime_steps_for_source(source_type: str) -> List[Dict[str, str]]:
    steps = list(ETL_RUNTIME_STEPS)
    if source_type in EXTERNAL_SOURCE_TYPES:
        steps.extend(ETL_VDL_RUNTIME_STEPS)
    return steps


LIVE_SOURCE_TYPE_BY_NODE: Dict[str, str] = {
    "source.social_listening": "social_listening",
    "source.file_uploads": "file_uploads",
    "source.google_drive": "google_drive",
    "source.external_full": "external_full",
    "source.fdw": "generic",
    "source.external_feed": "generic",
}

STUB_NODE_TYPES = frozenset(
    {
        "source.kafka",
        "source.postgres_cdc",
        "source.s3",
        "ai.classify_llm",
        "ai.redact_pii",
        "ai.extract_fields",
        "ai.embed_vector",
    }
)

# Studio node type -> runtime step id (0..N nodes may map to same step; compiler dedupes)
NODE_TYPE_TO_RUNTIME_STEP: Dict[str, Optional[str]] = {
    "source.external_feed": "extract",
    "source.social_listening": "extract",
    "source.file_uploads": "extract",
    "source.google_drive": "extract",
    "source.external_full": "extract",
    "source.fdw": "extract",
    "source.kafka": None,
    "source.postgres_cdc": None,
    "source.s3": None,
    "source.mapping_rule": None,
    "ai.classify_llm": None,
    "ai.redact_pii": None,
    "ai.extract_fields": None,
    "ai.embed_vector": None,
    "transform.parse_schema": "validate_schema",
    "transform.validate_schema": "validate_schema",
    "transform.map_fields": "transform",
    "transform.filter": "transform",
    "sink.load_fdw": "load",
    "sink.verify": "verify",
    "sink.register_vdl": "register_vdl",
    "sink.materialize_warehouse": "materialize_warehouse",
    "route.dead_letter": None,
}

RUNTIME_STEP_ORDER: List[str] = [
    "extract",
    "validate_schema",
    "transform",
    "load",
    "verify",
    "register_vdl",
    "materialize_warehouse",
]

PIPELINE_NODE_CATALOG: List[Dict[str, Any]] = [
    {
        "type": "source.social_listening",
        "category": "sources",
        "label": "Social listening",
        "description": "Market signals, mentions, competitor alerts",
        "icon": "megaphone-or-rss",
        "defaultParams": {"sourceType": "social_listening", "mode": "incremental", "batchSize": 500},
        "mapsToRuntimeStep": "extract",
        "runtime": "live",
    },
    {
        "type": "source.file_uploads",
        "category": "sources",
        "label": "File uploads",
        "description": "Invoices, lab reports, CSV files",
        "icon": "upload",
        "defaultParams": {"sourceType": "file_uploads", "mode": "full", "batchSize": 1000},
        "mapsToRuntimeStep": "extract",
        "runtime": "live",
    },
    {
        "type": "source.google_drive",
        "category": "sources",
        "label": "Google Drive",
        "description": "Contracts and sustainability reports",
        "icon": "folder",
        "defaultParams": {
            "sourceType": "google_drive",
            "mode": "incremental",
            "batchSize": 200,
            "folderId": "",
            "includeMimeTypes": "application/pdf,text/csv",
        },
        "configFields": [
            {"key": "mode", "type": "enum", "label": "Mode", "enum": ["full", "incremental"], "default": "incremental"},
            {"key": "batchSize", "type": "number", "label": "Batch size", "default": 200, "min": 1},
            {"key": "folderId", "type": "string", "label": "Drive folder ID", "help": "Optional root folder for scans"},
            {"key": "includeMimeTypes", "type": "string", "label": "MIME types", "help": "Comma-separated filter"},
            {"key": "schedule", "type": "string", "label": "Schedule (cron)", "placeholder": "Manual"},
        ],
        "mapsToRuntimeStep": "extract",
        "runtime": "live",
    },
    {
        "type": "source.external_full",
        "category": "sources",
        "label": "External sources (full VDL)",
        "description": "All external feeds, mappings, and warehouse snapshots",
        "icon": "database",
        "defaultParams": {"sourceType": "external_full", "mode": "full", "batchSize": 1000},
        "mapsToRuntimeStep": "extract",
        "runtime": "live",
    },
    {
        "type": "source.fdw",
        "category": "sources",
        "label": "FDW / warehouse table",
        "description": "Salesforce, Oracle, SAP or other Data Plane source",
        "icon": "database",
        "defaultParams": {"sourceType": "generic", "mode": "full", "batchSize": 1000, "dataPlaneId": ""},
        "mapsToRuntimeStep": "extract",
        "runtime": "live",
    },
    {
        "type": "source.external_feed",
        "category": "sources",
        "label": "Generic feed",
        "description": "Custom extract with explicit sourceType",
        "icon": "database",
        "defaultParams": {"sourceType": "generic", "mode": "full", "batchSize": 1000},
        "mapsToRuntimeStep": "extract",
        "runtime": "live",
    },
    {
        "type": "source.mapping_rule",
        "category": "sources",
        "label": "Mapping rule",
        "description": "Bind pipeline to a mapper rule",
        "icon": "shuffle",
        "defaultParams": {"mappingRuleId": ""},
        "mapsToRuntimeStep": None,
        "runtime": "live",
    },
    {
        "type": "source.kafka",
        "category": "sources",
        "label": "Kafka topic",
        "description": "Streaming ingest (not executable yet)",
        "icon": "refresh",
        "defaultParams": {"topic": ""},
        "mapsToRuntimeStep": None,
        "runtime": "stub",
    },
    {
        "type": "source.postgres_cdc",
        "category": "sources",
        "label": "Postgres CDC",
        "description": "Change data capture (not executable yet)",
        "icon": "database",
        "defaultParams": {"schema": "public"},
        "mapsToRuntimeStep": None,
        "runtime": "stub",
    },
    {
        "type": "source.s3",
        "category": "sources",
        "label": "S3 / object store",
        "description": "Object ingest (not executable yet)",
        "icon": "folder",
        "defaultParams": {"bucket": "", "prefix": ""},
        "mapsToRuntimeStep": None,
        "runtime": "stub",
    },
    {
        "type": "transform.parse_schema",
        "category": "transform",
        "label": "Parse / map schema",
        "description": "Infer or apply source schema",
        "icon": "file-json",
        "defaultParams": {},
        "mapsToRuntimeStep": "validate_schema",
    },
    {
        "type": "transform.validate_schema",
        "category": "transform",
        "label": "Validate schema",
        "description": "Validate against mapping rule fields",
        "icon": "check-circle",
        "defaultParams": {},
        "mapsToRuntimeStep": "validate_schema",
    },
    {
        "type": "transform.map_fields",
        "category": "transform",
        "label": "Map fields",
        "description": "Apply field mappings to virtual entity shape",
        "icon": "shuffle",
        "defaultParams": {},
        "mapsToRuntimeStep": "transform",
    },
    {
        "type": "transform.filter",
        "category": "transform",
        "label": "Filter & route",
        "description": "Filter records (preview in studio; processor P1 passthrough)",
        "icon": "filter",
        "defaultParams": {"predicate": ""},
        "mapsToRuntimeStep": "transform",
    },
    {
        "type": "ai.classify_llm",
        "category": "ai",
        "label": "Classify with LLM",
        "description": "Intent / label classification (stub)",
        "icon": "sparkles",
        "defaultParams": {"labels": []},
        "mapsToRuntimeStep": None,
        "runtime": "stub",
    },
    {
        "type": "ai.redact_pii",
        "category": "ai",
        "label": "Redact PII",
        "description": "Mask email, phone, address (stub)",
        "icon": "sparkles",
        "defaultParams": {"fields": ["email", "phone", "address"]},
        "mapsToRuntimeStep": None,
        "runtime": "stub",
    },
    {
        "type": "ai.extract_fields",
        "category": "ai",
        "label": "Extract fields",
        "description": "LLM field extraction (stub)",
        "icon": "file",
        "defaultParams": {},
        "mapsToRuntimeStep": None,
        "runtime": "stub",
    },
    {
        "type": "ai.embed_vector",
        "category": "ai",
        "label": "Embed to vector DB",
        "description": "Write embeddings (stub)",
        "icon": "layers",
        "defaultParams": {},
        "mapsToRuntimeStep": None,
        "runtime": "stub",
    },
    {
        "type": "sink.load_fdw",
        "category": "sinks",
        "label": "Load FDW / hydrate",
        "description": "Load rows into simulator / FDW landing",
        "icon": "database",
        "defaultParams": {},
        "mapsToRuntimeStep": "load",
    },
    {
        "type": "sink.verify",
        "category": "sinks",
        "label": "Verify quality",
        "description": "Row counts and null checks",
        "icon": "check-circle",
        "defaultParams": {},
        "mapsToRuntimeStep": "verify",
    },
    {
        "type": "sink.register_vdl",
        "category": "sinks",
        "label": "Register VDL",
        "description": "Activate mapping rules for virtual entities",
        "icon": "cube",
        "defaultParams": {},
        "mapsToRuntimeStep": "register_vdl",
        "requiresSourceTypes": list(EXTERNAL_SOURCE_TYPES),
    },
    {
        "type": "sink.materialize_warehouse",
        "category": "sinks",
        "label": "Materialize warehouse",
        "description": "Refresh warehouse KPI snapshots",
        "icon": "layers",
        "defaultParams": {},
        "mapsToRuntimeStep": "materialize_warehouse",
        "requiresSourceTypes": list(EXTERNAL_SOURCE_TYPES),
    },
    {
        "type": "route.dead_letter",
        "category": "control",
        "label": "Dead letter",
        "description": "Error branch (visual only in Phase 1)",
        "icon": "alert-triangle",
        "defaultParams": {},
        "mapsToRuntimeStep": None,
    },
]