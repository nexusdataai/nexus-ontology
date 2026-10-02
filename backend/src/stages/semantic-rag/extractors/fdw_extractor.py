"""
FDW Metadata Extractor

Pulls table, column, and foreign key metadata from the FDW discovery service
and converts them into OntoDocument objects. Optionally loads an enterprise
schema overlay (schema.yaml) to enrich documents with semantic annotations
and cross-entity relationships.
"""

import asyncio
import os
import sys
from typing import Dict, List, Any, Optional

_current_dir = os.path.dirname(os.path.abspath(__file__))
_stage_dir = os.path.dirname(_current_dir)
if _stage_dir not in sys.path:
    sys.path.insert(0, _stage_dir)

from onto_model import OntoDocument, OntoRelationship


def _find_enterprise_knowledge():
    """Locate the enterprise-knowledge directory."""
    candidates = [
        os.path.join(os.environ.get("APP_ROOT", "/app"), "enterprise-knowledge"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_stage_dir)))), "enterprise-knowledge"),
        "/app/enterprise-knowledge",
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]

_ENTERPRISE_KNOWLEDGE_DIR = _find_enterprise_knowledge()


class FDWExtractor:
    def __init__(self, logger=None, schema_overlay_path: str = ""):
        self._log = logger
        self._schema_overlay_path = schema_overlay_path or os.path.join(
            _ENTERPRISE_KNOWLEDGE_DIR, "supply-chain-schema.yaml"
        )
        self._overlay: Optional[Dict] = None
        self._table_overlay: Dict[str, Dict] = {}

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def _load_overlay(self):
        if self._overlay is not None:
            return
        try:
            import yaml
            if os.path.isfile(self._schema_overlay_path):
                with open(self._schema_overlay_path) as f:
                    self._overlay = yaml.safe_load(f) or {}
                for domain in self._overlay.get("domains", []):
                    for tbl in domain.get("tables", []):
                        key = tbl["fdw_table"]
                        if tbl.get("merge_with_existing") and key in self._table_overlay:
                            existing = self._table_overlay[key]
                            existing.setdefault("key_fields", []).extend(tbl.get("key_fields", []))
                            existing.setdefault("relationships", []).extend(tbl.get("relationships", []))
                        else:
                            self._table_overlay[key] = {
                                **tbl,
                                "domain": domain.get("name", ""),
                                "domain_system": domain.get("system", ""),
                                "domain_description": domain.get("description", ""),
                            }
                self._info(f"Schema overlay loaded: {len(self._table_overlay)} table definitions from {len(self._overlay.get('domains', []))} domains")
            else:
                self._overlay = {}
                self._info("No schema overlay found — extracting raw FDW metadata only")
        except Exception as e:
            self._overlay = {}
            self._info(f"Schema overlay load failed ({e}) — extracting raw FDW metadata only")

    def _build_relationships(self, overlay_entry: Dict, server_system: str) -> List[OntoRelationship]:
        rels = []
        for r in overlay_entry.get("relationships", []):
            target_name = r.get("target_entity", "")
            target_cat = r.get("target_category", "schema")
            target_system = r.get("target_system", "")

            if target_cat == "schema":
                sys = target_system or server_system
                target_id = OntoDocument.generate_id(sys, target_name, entity_type="Schema")
            elif target_cat == "workflow":
                target_id = OntoDocument.generate_id("Internal", target_name, entity_type="Workflow")
            elif target_cat == "policy":
                target_id = OntoDocument.generate_id("Internal", target_name, entity_type="Policy")
            elif target_cat == "integration":
                sys = target_system or "Salesforce"
                target_id = OntoDocument.generate_id(sys, target_name, entity_type="Integration")
            else:
                target_id = OntoDocument.generate_id(server_system, target_name)

            rels.append(OntoRelationship(
                relation_type=r.get("type", "depends_on"),
                target_id=target_id,
                description=r.get("description", ""),
            ))
        return rels

    def _enrich_content(self, base_content: str, overlay_entry: Dict) -> str:
        parts = [base_content]
        if overlay_entry.get("semantic"):
            parts.append(f"\nSemantic Description: {overlay_entry['semantic']}")
        if overlay_entry.get("domain"):
            parts.append(f"Domain: {overlay_entry['domain']}")
        for kf in overlay_entry.get("key_fields", []):
            line = f"Key Field: {kf['name']}"
            if kf.get("semantic"):
                line += f" — {kf['semantic']}"
            if kf.get("constraints"):
                line += "\n  Constraints: " + "; ".join(kf["constraints"])
            parts.append(line)
        return "\n".join(parts)

    def extract(self) -> List[OntoDocument]:
        try:
            return asyncio.get_event_loop().run_until_complete(self._extract_async())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._extract_async())
            finally:
                loop.close()

    def _get_loaded_simulators(self) -> Dict[str, Any]:
        """Get simulator services that are loaded with data from the app lifecycle."""
        simulators = {}
        try:
            from src.apis.fdw_api import _simulators
            for name, sim in _simulators.items():
                if sim and getattr(sim, 'loaded', False):
                    simulators[name] = sim
        except Exception:
            pass
        return simulators

    async def _extract_from_simulator(self, sim, sim_name: str) -> List[OntoDocument]:
        """Extract metadata from a loaded simulator service."""
        docs = []
        try:
            await sim.ensure_loaded()
            tables = await sim.list_foreign_tables()
            self._info(f"  Simulator '{sim_name}': {len(tables)} tables")

            for table in tables:
                table_name = table.table_name if hasattr(table, 'table_name') else str(table)
                schema_name = table.schema_name if hasattr(table, 'schema_name') else sim_name

                try:
                    columns = await sim.get_table_columns(schema_name, table_name)
                except Exception:
                    columns = []

                col_descriptions = []
                for col in columns:
                    col_name = col.column_name if hasattr(col, 'column_name') else str(col)
                    col_type = col.data_type if hasattr(col, 'data_type') else "unknown"
                    nullable = col.is_nullable if hasattr(col, 'is_nullable') else True
                    col_descriptions.append(f"  - {col_name} ({col_type}, nullable={nullable})")

                content = (
                    f"Simulator Table: {schema_name}.{table_name}\n"
                    f"Source: {sim_name} simulator\n"
                    f"Columns:\n" + "\n".join(col_descriptions)
                )

                overlay = self._table_overlay.get(table_name, {})
                relationships = self._build_relationships(overlay, sim_name)
                risk_level = overlay.get("risk_level", "medium")

                if overlay:
                    content = self._enrich_content(content, overlay)

                doc = OntoDocument(
                    id=OntoDocument.generate_id(sim_name, table_name, entity_type="Schema"),
                    system=overlay.get("domain_system") or sim_name,
                    entity_type="Schema",
                    object_name=table_name,
                    category="schema",
                    content=content,
                    source="simulator",
                    risk_level=risk_level,
                    structured_metadata={
                        "schema": schema_name,
                        "server": sim_name,
                        "simulator": True,
                        "simulator_source": sim_name,
                        "domain": overlay.get("domain", ""),
                        "column_count": len(columns),
                        "columns": [
                            {
                                "name": c.column_name if hasattr(c, 'column_name') else str(c),
                                "type": c.data_type if hasattr(c, 'data_type') else "unknown",
                            }
                            for c in columns
                        ],
                    },
                    relationships=relationships,
                )
                docs.append(doc)
        except Exception as e:
            self._info(f"  Simulator '{sim_name}' extraction failed: {e}")
        return docs

    async def _extract_async(self) -> List[OntoDocument]:
        from src.services.fdw_connection_manager import PostgreSQLConnectionManager
        from src.services.fdw_discovery_service import FDWDiscoveryService
        from src.config.fdw_config import FDWConfig

        self._load_overlay()

        docs: List[OntoDocument] = []
        enriched_count = 0
        rel_count = 0
        last_server_system = "unknown"

        try:
            config = FDWConfig.from_environment()
            conn_mgr = PostgreSQLConnectionManager(config)
            await conn_mgr.initialize()
            discovery = FDWDiscoveryService(conn_mgr)

            servers = await discovery.list_foreign_servers()
            self._info(f"Found {len(servers)} FDW servers")

            for server in servers:
                server_system = server.server_name or "unknown"
                last_server_system = server_system
                tables = await discovery.list_foreign_tables(server.server_name)
                self._info(f"  Server '{server_system}': {len(tables)} tables")

                for table in tables:
                    table_name = table.table_name if hasattr(table, 'table_name') else str(table)
                    schema_name = table.schema_name if hasattr(table, 'schema_name') else "public"

                    columns = await discovery.get_table_columns(schema_name, table_name)
                    col_descriptions = []
                    for col in columns:
                        col_name = col.column_name if hasattr(col, 'column_name') else str(col)
                        col_type = col.data_type if hasattr(col, 'data_type') else "unknown"
                        nullable = col.is_nullable if hasattr(col, 'is_nullable') else True
                        col_descriptions.append(f"  - {col_name} ({col_type}, nullable={nullable})")

                    content = (
                        f"Table: {schema_name}.{table_name}\n"
                        f"Server: {server_system}\n"
                        f"Columns:\n" + "\n".join(col_descriptions)
                    )

                    overlay = self._table_overlay.get(table_name, {})
                    relationships = self._build_relationships(overlay, server_system)
                    risk_level = overlay.get("risk_level", "medium")

                    if overlay:
                        content = self._enrich_content(content, overlay)
                        enriched_count += 1
                        rel_count += len(relationships)

                    doc = OntoDocument(
                        id=OntoDocument.generate_id(server_system, table_name, entity_type="Schema"),
                        system=overlay.get("domain_system") or server_system,
                        entity_type="Schema",
                        object_name=table_name,
                        category="schema",
                        content=content,
                        source="fdw",
                        risk_level=risk_level,
                        structured_metadata={
                            "schema": schema_name,
                            "server": server_system,
                            "domain": overlay.get("domain", ""),
                            "column_count": len(columns),
                            "columns": [
                                {
                                    "name": c.column_name if hasattr(c, 'column_name') else str(c),
                                    "type": c.data_type if hasattr(c, 'data_type') else "unknown",
                                }
                                for c in columns
                            ],
                        },
                        relationships=relationships,
                    )
                    docs.append(doc)
        except Exception as e:
            self._info(f"FDW extraction failed ({e}) — continuing with simulators only")

        fdw_count = len(docs)

        simulators = self._get_loaded_simulators()
        sim_count = 0
        if simulators:
            self._info(f"Found {len(simulators)} loaded simulators: {list(simulators.keys())}")
            seen_tables = {d.object_name.lower() for d in docs}
            for sim_name, sim in simulators.items():
                sim_docs = await self._extract_from_simulator(sim, sim_name)
                for sd in sim_docs:
                    if sd.object_name.lower() not in seen_tables:
                        docs.append(sd)
                        seen_tables.add(sd.object_name.lower())
                        sim_count += 1
        else:
            self._info("No loaded simulators found")

        virtual_docs = self._extract_virtual_entities(last_server_system)
        docs.extend(virtual_docs)

        self._info(f"FDW extraction complete: {len(docs)} documents "
                   f"({fdw_count} FDW, {sim_count} simulator, {len(virtual_docs)} virtual, "
                   f"{enriched_count} enriched, {rel_count} relationships)")
        return docs

    def _extract_virtual_entities(self, default_system: str) -> List[OntoDocument]:
        """Create OntoDocuments for virtual entities defined in the overlay (e.g. Oracle tables)."""
        docs = []
        for domain in (self._overlay or {}).get("domains", []):
            for tbl in domain.get("tables", []):
                if not tbl.get("virtual"):
                    continue
                name = tbl["fdw_table"]
                system = domain.get("system", default_system)
                overlay = {**tbl, "domain": domain.get("name", ""), "domain_system": system}

                field_lines = []
                for kf in tbl.get("key_fields", []):
                    line = f"  - {kf['name']} ({kf.get('data_type', 'unknown')})"
                    if kf.get("semantic"):
                        line += f": {kf['semantic']}"
                    field_lines.append(line)

                content = f"Virtual Entity: {name}\nSystem: {system}\n"
                if tbl.get("semantic"):
                    content += f"Description: {tbl['semantic']}\n"
                if field_lines:
                    content += "Fields:\n" + "\n".join(field_lines)

                relationships = self._build_relationships(overlay, default_system)

                doc = OntoDocument(
                    id=OntoDocument.generate_id(system, name, entity_type="Schema"),
                    system=system,
                    entity_type="Schema",
                    object_name=name,
                    category="schema",
                    content=content,
                    source="enterprise_schema",
                    risk_level=tbl.get("risk_level", "medium"),
                    structured_metadata={
                        "virtual": True,
                        "domain": domain.get("name", ""),
                        "key_fields": [kf["name"] for kf in tbl.get("key_fields", [])],
                    },
                    relationships=relationships,
                )
                docs.append(doc)
        return docs
