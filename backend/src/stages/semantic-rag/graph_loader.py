"""
Graph DB Loader

Loads OntoDocument relationships into a graph store.
Tries Apache AGE, falls back to metadata-based relationship index in pgvector.
Properly initializes connections with FDW config.
"""

import asyncio
import json
from typing import Dict, Any
from onto_model import OntoBundle, OntoDocument


class GraphLoader:
    def __init__(self, logger=None, progress_callback=None):
        self._log = logger
        self._progress_callback = progress_callback
        self._use_age = False
        self._conn = None

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def _emit_progress(self, done, total):
        if self._progress_callback:
            try:
                self._progress_callback(done, total)
            except Exception:
                pass

    def _get_conn_mgr(self):
        from src.services.fdw_connection_manager import PostgreSQLConnectionManager
        from src.config.fdw_config import FDWConfig
        config = FDWConfig.from_environment()
        conn_mgr = PostgreSQLConnectionManager(config)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(conn_mgr.initialize())
        return conn_mgr

    def _init_age(self):
        try:
            conn_mgr = self._get_conn_mgr()
            engine = conn_mgr.engine
            if engine is None:
                raise RuntimeError("No engine")

            from sqlalchemy import text
            with engine.connect() as conn:
                self._info("Creating AGE extension...")
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS age"))
                conn.execute(text("LOAD 'age'"))
                conn.execute(text("SET search_path = ag_catalog, public"))
                try:
                    conn.execute(text("SELECT drop_graph('enterprise_onto', true)"))
                    self._info("Dropped old enterprise_onto graph (fresh load)")
                except Exception:
                    pass
                try:
                    conn.execute(text("SELECT create_graph('enterprise_onto')"))
                    self._info("Created new enterprise_onto graph")
                except Exception:
                    self._info("enterprise_onto graph already exists")
                conn.commit()

            self._conn = engine
            self._use_age = True
            self._info("Apache AGE initialized — will use Cypher graph backend")
        except Exception as e:
            self._info(f"Apache AGE not available ({e}) — using metadata-based relationships")
            self._use_age = False

    def load(self, bundle: OntoBundle) -> Dict[str, int]:
        self._init_age()

        if self._use_age:
            return self._load_age(bundle)
        else:
            return self._load_metadata(bundle)

    @staticmethod
    def _cypher_props(props: Dict[str, Any]) -> str:
        """Build a Cypher map literal: {key: 'value', key2: 'value2'}"""
        parts = []
        for k, v in props.items():
            escaped = str(v).replace("\\", "\\\\").replace("'", "\\'")
            parts.append(f"{k}: '{escaped}'")
        return "{" + ", ".join(parts) + "}"

    def _load_age(self, bundle: OntoBundle) -> Dict[str, int]:
        nodes_created = 0
        node_errors = 0
        edges_created = 0
        edge_errors = 0
        from sqlalchemy import text

        total_docs = len(bundle.documents)
        total_rels = sum(len(d.relationships) for d in bundle.documents)
        self._info(f"AGE: Loading {total_docs} nodes and {total_rels} edges into enterprise_onto graph")

        with self._conn.connect() as conn:
            conn.execute(text("LOAD 'age'"))
            conn.execute(text("SET search_path = ag_catalog, public"))

            for i, doc in enumerate(bundle.documents):
                created = False
                for retry in range(3):
                    try:
                        props = self._cypher_props({
                            "onto_id": doc.id, "system": doc.system,
                            "entity_type": doc.entity_type, "object_name": doc.object_name,
                            "category": doc.category, "risk_level": doc.risk_level,
                        })
                        cypher = f"MERGE (n:Entity {{onto_id: '{doc.id}'}}) SET n += {props}"
                        conn.execute(text(
                            f"SELECT * FROM cypher('enterprise_onto', $$ {cypher} $$) AS (v agtype)"
                        ))
                        nodes_created += 1
                        created = True
                        break
                    except Exception as e:
                        conn.rollback()
                        conn.execute(text("LOAD 'age'"))
                        conn.execute(text("SET search_path = ag_catalog, public"))
                        if retry < 2:
                            import time as _time
                            _time.sleep(1)
                            continue
                        node_errors += 1
                        if node_errors <= 3:
                            self._info(f"  Node error [{doc.id}] after 3 retries: {e}")

                if (i + 1) % 200 == 0:
                    conn.commit()
                    conn.execute(text("LOAD 'age'"))
                    conn.execute(text("SET search_path = ag_catalog, public"))
                    self._info(f"  AGE nodes: {nodes_created}/{i+1} created ({node_errors} errors)")
                    self._emit_progress(i + 1, total_docs + total_rels)

            conn.commit()
            self._info(f"AGE nodes complete: {nodes_created}/{total_docs} ({node_errors} errors)")
            self._emit_progress(total_docs, total_docs + total_rels)

            conn.execute(text("LOAD 'age'"))
            conn.execute(text("SET search_path = ag_catalog, public"))
            for doc in bundle.documents:
                for rel in doc.relationships:
                    for retry in range(3):
                        try:
                            rel_type = rel.relation_type.upper().replace(" ", "_").replace("-", "_")
                            cypher = (
                                f"MATCH (a:Entity {{onto_id: '{doc.id}'}}), "
                                f"(b:Entity {{onto_id: '{rel.target_id}'}}) "
                                f"MERGE (a)-[r:{rel_type}]->(b)"
                            )
                            conn.execute(text(
                                f"SELECT * FROM cypher('enterprise_onto', $$ {cypher} $$) AS (v agtype)"
                            ))
                            edges_created += 1
                            break
                        except Exception as e:
                            conn.rollback()
                            conn.execute(text("LOAD 'age'"))
                            conn.execute(text("SET search_path = ag_catalog, public"))
                            if retry < 2:
                                import time as _time
                                _time.sleep(1)
                                continue
                            edge_errors += 1
                            if edge_errors <= 3:
                                self._info(f"  Edge error [{doc.id}]->{rel.target_id} after 3 retries: {e}")
            conn.commit()

        self._info(f"AGE graph complete: {nodes_created} nodes, {edges_created} edges "
                   f"({node_errors} node errors, {edge_errors} edge errors)")
        return {
            "nodes_created": nodes_created, "edges_created": edges_created,
            "node_errors": node_errors, "edge_errors": edge_errors,
            "backend": "apache_age",
        }

    def _load_metadata(self, bundle: OntoBundle) -> Dict[str, int]:
        nodes = len(bundle.documents)
        edges = sum(len(doc.relationships) for doc in bundle.documents)

        self._info(f"Metadata fallback: indexing {nodes} nodes, {edges} edges into pgvector")

        relationship_index = {}
        for doc in bundle.documents:
            for rel in doc.relationships:
                relationship_index.setdefault(doc.id, []).append({
                    "type": rel.relation_type,
                    "target": rel.target_id,
                    "description": rel.description,
                })

        docs_with_rels = len(relationship_index)
        self._info(f"  {docs_with_rels} documents have relationships")

        try:
            from src.services.control_plane.vector_store import VectorStore
            conn_mgr = self._get_conn_mgr()
            store = VectorStore(conn_mgr)

            async def _upsert_index():
                await store.upsert(
                    content_type="onto_graph_index",
                    source_id="relationship_index",
                    content=json.dumps(relationship_index),
                    metadata={"total_nodes": nodes, "total_edges": edges},
                    embedding=[0.0] * 1536,
                )

            try:
                asyncio.run(_upsert_index())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_upsert_index())
                finally:
                    loop.close()
            self._info(f"Metadata graph index stored in pgvector: {nodes} nodes, {edges} edges")
        except Exception as e:
            self._info(f"Failed to store graph index: {e}")

        return {"nodes_created": nodes, "edges_created": edges, "backend": "metadata_fallback"}
