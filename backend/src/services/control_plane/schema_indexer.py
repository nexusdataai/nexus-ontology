"""
Schema Indexer for the AI Control Plane.

Pulls metadata from FDW Discovery Service (foreign servers, tables, columns)
and indexes it as embeddings in the vector store.  Also indexes virtual entities
from enterprise-knowledge schema YAML files.

Content types stored:
  - "fdw_table"   : per-table schema (columns, types, server)
  - "fdw_server"  : per-server metadata (wrapper type, options)
  - "onto_schema" : virtual entity from unified schema YAML
  - "tmf_spec"    : TMF API spec summaries (if available)
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.services.fdw_discovery_service import FDWDiscoveryService
from .embedding_service import EmbeddingService
from .vector_store import VectorStore

cp_logger = logger.bind(component="control-plane")


class SchemaIndexer:
    """Indexes FDW schema metadata into the vector store."""

    def __init__(
        self,
        discovery: FDWDiscoveryService,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
    ):
        self._discovery = discovery
        self._embeddings = embedding_service
        self._vector = vector_store

    async def index_all(self) -> Dict[str, int]:
        """Run full indexing: servers + tables + columns + virtual entities."""
        stats = {"servers": 0, "tables": 0, "virtual_entities": 0, "errors": 0}

        servers = await self._discovery.list_foreign_servers()
        tables = await self._discovery.list_foreign_tables()

        server_rows = await self._index_servers(servers)
        stats["servers"] = server_rows

        table_rows = await self._index_tables(tables)
        stats["tables"] = table_rows

        virtual_rows = await self._index_virtual_entities()
        stats["virtual_entities"] = virtual_rows

        cp_logger.info(
            f"Schema indexing complete: {stats['servers']} servers, "
            f"{stats['tables']} tables, {stats['virtual_entities']} virtual entities indexed"
        )
        return stats

    async def _index_servers(self, servers) -> int:
        if not servers:
            return 0

        docs = []
        texts = []
        for srv in servers:
            content = self._server_to_text(srv)
            texts.append(content)
            docs.append({
                "content_type": "fdw_server",
                "source_id": srv.server_name,
                "content": content,
                "metadata": {
                    "server_name": srv.server_name,
                    "wrapper": srv.wrapper_type,
                    "options": srv.server_options,
                },
            })

        embeddings = self._embeddings.embed_batch(texts)
        for doc, emb in zip(docs, embeddings):
            doc["embedding"] = emb

        return await self._vector.upsert_batch(docs)

    async def _index_tables(self, tables) -> int:
        if not tables:
            return 0

        docs = []
        texts = []
        for tbl in tables:
            try:
                columns = await self._discovery.get_table_columns(tbl.schema_name, tbl.table_name)
            except Exception as e:
                cp_logger.warning(f"Failed to get columns for {tbl.schema_name}.{tbl.table_name}: {e}")
                columns = []

            content = self._table_to_text(tbl, columns)
            texts.append(content)
            docs.append({
                "content_type": "fdw_table",
                "source_id": f"{tbl.schema_name}.{tbl.table_name}",
                "content": content,
                "metadata": {
                    "schema": tbl.schema_name,
                    "table": tbl.table_name,
                    "server": tbl.server_name,
                    "column_count": len(columns),
                    "columns": [
                        {"name": c.column_name, "type": c.data_type, "nullable": c.is_nullable}
                        for c in columns
                    ],
                },
            })

        embeddings = self._embeddings.embed_batch(texts)
        for doc, emb in zip(docs, embeddings):
            doc["embedding"] = emb

        return await self._vector.upsert_batch(docs)

    @staticmethod
    def _server_to_text(srv) -> str:
        opts = ", ".join(f"{k}={v}" for k, v in (srv.server_options or {}).items())
        return (
            f"Foreign data server '{srv.server_name}' "
            f"using wrapper '{srv.wrapper_type}'. "
            f"Options: {opts or 'none'}."
        )

    @staticmethod
    def _table_to_text(tbl, columns) -> str:
        col_descs = []
        for c in columns:
            nullable = "nullable" if c.is_nullable == "YES" else "not null"
            col_descs.append(f"  - {c.column_name} ({c.data_type}, {nullable})")
        cols_text = "\n".join(col_descs) if col_descs else "  (no columns discovered)"
        return (
            f"Foreign table '{tbl.schema_name}.{tbl.table_name}' "
            f"on server '{tbl.server_name}'.\n"
            f"Columns:\n{cols_text}"
        )

    async def _index_virtual_entities(self) -> int:
        """Index virtual entities from enterprise-knowledge schema YAML files."""
        try:
            import yaml
        except ImportError:
            cp_logger.warning("pyyaml not installed — skipping virtual entity indexing")
            return 0

        ek_candidates = [
            os.path.join(os.environ.get("APP_ROOT", "/app"), "enterprise-knowledge"),
            str(Path(__file__).resolve().parent.parent.parent.parent / "enterprise-knowledge"),
            "/app/enterprise-knowledge",
        ]
        ek_dir = None
        for c in ek_candidates:
            if os.path.isdir(c):
                ek_dir = c
                break
        if not ek_dir:
            return 0

        schema_files = sorted(Path(ek_dir).glob("*schema*.yaml"))
        if not schema_files:
            return 0

        docs = []
        texts = []
        for sf in schema_files:
            try:
                with open(sf) as f:
                    schema = yaml.safe_load(f)
                for domain in schema.get("domains", []):
                    system = domain.get("system", "Unknown")
                    domain_name = domain.get("name", "")
                    for table in domain.get("tables", []):
                        name = table.get("fdw_table", "")
                        if not name:
                            continue
                        is_virtual = table.get("virtual", False)
                        fields = table.get("key_fields", [])
                        field_lines = [f"  - {kf.get('name', '?')} ({kf.get('data_type', '?')})" for kf in fields]
                        content = (
                            f"Virtual entity '{name}' in {system} system.\n"
                            f"Domain: {domain_name}\n"
                            f"Virtual: {'Yes' if is_virtual else 'No (has FDW table)'}\n"
                        )
                        if table.get("semantic"):
                            content += f"Description: {table['semantic']}\n"
                        scor = domain.get("scor_process", "")
                        if scor:
                            content += f"SCOR Process: {scor}\n"
                        if field_lines:
                            content += "Key Fields:\n" + "\n".join(field_lines)

                        texts.append(content)
                        docs.append({
                            "content_type": "onto_schema",
                            "source_id": f"virtual:{system}:{name}",
                            "content": content,
                            "metadata": {
                                "system": system,
                                "domain": domain_name,
                                "entity_name": name,
                                "virtual": is_virtual,
                                "field_count": len(fields),
                                "source_file": sf.name,
                            },
                        })
            except Exception as e:
                cp_logger.warning(f"Failed to parse {sf.name}: {e}")

        if not docs:
            return 0

        cp_logger.info(f"Indexing {len(docs)} virtual entities from {len(schema_files)} schema files")
        embeddings = self._embeddings.embed_batch(texts)
        for doc, emb in zip(docs, embeddings):
            doc["embedding"] = emb

        return await self._vector.upsert_batch(docs)
