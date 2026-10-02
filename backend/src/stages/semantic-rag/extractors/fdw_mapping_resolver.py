"""
FDW Mapping Resolver

After the UnifiedSchemaExtractor produces OntoDocuments for all schema
entities, this resolver matches them against live FDW foreign tables
discovered via FDWDiscoveryService.

Entities are annotated with:
  - "mapped"   — a live FDW foreign table exists and is queryable
  - "virtual"  — entity is virtual (SAP/Oracle/unstructured), no FDW expected
  - "unmapped" — entity should have a FDW table but none was found
"""

import asyncio
import os
import sys
from typing import Dict, List

_current_dir = os.path.dirname(os.path.abspath(__file__))
_stage_dir = os.path.dirname(_current_dir)
if _stage_dir not in sys.path:
    sys.path.insert(0, _stage_dir)

from onto_model import OntoDocument


DEFAULT_SCHEMA = os.environ.get("FDW_SCHEMA", "sfdc_itxp2dev")


class FDWMappingResolver:
    """Resolves unified schema entities to live FDW foreign tables."""

    def __init__(self, logger=None):
        self._log = logger

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def resolve(self, schema_docs: List[OntoDocument]) -> List[OntoDocument]:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(self._resolve_sync, schema_docs)
                    return future.result()
            return loop.run_until_complete(self._resolve_async(schema_docs))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._resolve_async(schema_docs))
            finally:
                loop.close()

    def _resolve_sync(self, schema_docs: List[OntoDocument]) -> List[OntoDocument]:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._resolve_async(schema_docs))
        finally:
            loop.close()

    def _collect_simulator_tables(self) -> Dict[str, str]:
        """Collect table names from all loaded simulators via the app lifecycle. Returns {lower_name: source_label}."""
        sim_tables: Dict[str, str] = {}
        label_map = {"simulator": "simulator:Salesforce", "oracle": "simulator:Oracle", "sap": "simulator:SAP"}
        try:
            from src.apis.fdw_api import _simulators
            for name, sim in _simulators.items():
                if not sim or not getattr(sim, 'loaded', False):
                    continue
                source_label = label_map.get(name, f"simulator:{name}")
                try:
                    tables = sim.list_tables() if hasattr(sim, 'list_tables') else []
                    for t in tables:
                        tname = t.table_name if hasattr(t, "table_name") else str(t)
                        sim_tables[tname.lower()] = source_label
                except Exception:
                    pass
        except Exception:
            pass
        return sim_tables

    async def _resolve_async(self, schema_docs: List[OntoDocument]) -> List[OntoDocument]:
        fdw_table_names: Dict = {}
        discovery = None
        try:
            from src.services.fdw_connection_manager import PostgreSQLConnectionManager
            from src.services.fdw_discovery_service import FDWDiscoveryService
            from src.config.fdw_config import FDWConfig

            config = FDWConfig.from_environment()
            conn_mgr = PostgreSQLConnectionManager(config)
            await conn_mgr.initialize()
            discovery = FDWDiscoveryService(conn_mgr)

            fdw_tables = await discovery.list_foreign_tables()
            fdw_table_names = {t.table_name.lower(): t for t in fdw_tables}
            self._info(f"FDW discovery found {len(fdw_table_names)} foreign tables")
        except Exception as e:
            self._info(f"FDW discovery unavailable ({e})")

        sim_tables = self._collect_simulator_tables()
        if sim_tables:
            self._info(f"Simulator discovery found {len(sim_tables)} tables across simulators")

        all_sources: Dict[str, str] = {}
        for name in fdw_table_names:
            all_sources[name] = "fdw"
        for name, label in sim_tables.items():
            if name not in all_sources:
                all_sources[name] = label

        self._info(f"Total resolvable tables: {len(all_sources)} (FDW: {len(fdw_table_names)}, Simulator: {len(sim_tables)})")

        mapped_count = 0
        virtual_count = 0
        unmapped_count = 0
        sim_mapped_count = 0

        for doc in schema_docs:
            meta = doc.structured_metadata
            fdw_table = meta.get("fdw_table", "")
            is_virtual = meta.get("virtual", False)

            # Canonical entities expose source-coupled names via aliases
            # (e.g. Customer -> [Account, AR_Customer]). When the canonical
            # name itself has no live FDW/sim table, try each alias before
            # giving up; record which alias produced the hit.
            candidate_names = [fdw_table] + [a for a in (meta.get("aliases") or []) if a]
            resolved_name = ""
            source = ""
            for cand in candidate_names:
                if not cand:
                    continue
                cand_source = all_sources.get(cand.lower(), "")
                if cand_source:
                    resolved_name = cand
                    source = cand_source
                    break

            if source and resolved_name and resolved_name != fdw_table:
                meta["resolved_via_alias"] = resolved_name

            if source == "fdw":
                meta["fdw_mapping_status"] = "mapped"
                meta["mapping_source"] = "fdw"
                mapped_count += 1

                if discovery:
                    try:
                        table_info = fdw_table_names[resolved_name.lower()]
                        schema_name = table_info.schema_name if hasattr(table_info, "schema_name") else DEFAULT_SCHEMA
                        columns = await discovery.get_table_columns(schema_name, resolved_name)
                        meta["fdw_columns"] = [{"name": c.column_name, "type": c.data_type} for c in columns]
                        meta["fdw_column_count"] = len(columns)
                        meta["fdw_schema"] = schema_name
                        meta["fdw_resolved_table"] = resolved_name
                        doc.content += (
                            f"\nFDW Mapping: LIVE — foreign table '{resolved_name}' in schema "
                            f"'{schema_name}' with {len(columns)} columns available for direct query."
                        )
                    except Exception as e:
                        self._info(f"  Column fetch failed for {resolved_name}: {e}")
                        doc.content += f"\nFDW Mapping: LIVE — foreign table '{resolved_name}' exists but column metadata unavailable."

            elif source.startswith("simulator:"):
                meta["fdw_mapping_status"] = "mapped"
                meta["mapping_source"] = source
                meta["fdw_resolved_table"] = resolved_name
                sim_mapped_count += 1
                doc.content += (
                    f"\nFDW Mapping: SIMULATOR — data available via {source} "
                    f"in-memory simulator (table '{resolved_name}')."
                )

            elif is_virtual:
                meta["fdw_mapping_status"] = "virtual"
                virtual_count += 1

            else:
                meta["fdw_mapping_status"] = "unmapped"
                unmapped_count += 1
                doc.content += "\nFDW Mapping: PENDING — no live foreign table or simulator connected yet."

        self._info(
            f"FDW mapping resolution: {mapped_count} FDW mapped, "
            f"{sim_mapped_count} simulator mapped, "
            f"{virtual_count} virtual, {unmapped_count} unmapped"
        )
        return schema_docs
