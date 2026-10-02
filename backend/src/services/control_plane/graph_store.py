"""
Graph Store for the AI Control Plane.

Provides graph traversal queries over the enterprise ontology relationships.
Supports Apache AGE (PostgreSQL extension) and falls back to the metadata-based
relationship index stored in pgvector.

Used by RAGService.hybrid_search() to expand vector search results with
dependency-aware context (policies, workflows, integration mappings).
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from src.services.fdw_connection_manager import PostgreSQLConnectionManager
from .vector_store import VectorStore

cp_logger = logger.bind(component="control-plane")


class GraphStore:
    """Graph traversal over enterprise ontology relationships."""

    def __init__(self, connection_manager: PostgreSQLConnectionManager, vector_store: VectorStore):
        self._conn = connection_manager
        self._vector = vector_store
        self._age_available: Optional[bool] = None
        self._age_checked_at: float = 0
        self._relationship_cache: Optional[Dict[str, List[Dict]]] = None

    async def expand_neighbors(self, onto_ids: List[str], hops: int = 2) -> List[Dict[str, Any]]:
        """
        Find all documents related to the given onto_ids within N hops.
        Returns list of {onto_id, relation_type, description, hop_distance}.
        """
        if await self._is_age_available():
            return await self._expand_age(onto_ids, hops)
        return await self._expand_metadata(onto_ids, hops)

    async def get_subgraph(self, onto_ids: List[str]) -> Dict[str, Any]:
        """Get all nodes and edges for a set of onto_ids (for visualization)."""
        if await self._is_age_available():
            try:
                return await self._subgraph_age(onto_ids)
            except Exception as e:
                cp_logger.warning(f"AGE subgraph failed, using metadata: {e}")

        index = await self._get_relationship_index()
        nodes = set(onto_ids)
        edges = []
        for oid in onto_ids:
            for rel in index.get(oid, []):
                edges.append({"source": oid, "target": rel["target"],
                              "type": rel["type"], "description": rel.get("description", "")})
                nodes.add(rel["target"])
        return {"nodes": [{"id": n} for n in nodes], "edges": edges}

    async def _subgraph_age(self, onto_ids: List[str]) -> Dict[str, Any]:
        """Fetch edges from Apache AGE for the given node IDs."""
        loop = asyncio.get_event_loop()
        engine = self._conn.engine

        def _query():
            from sqlalchemy import text
            all_edges = []
            all_nodes = set(onto_ids)
            with engine.connect() as conn:
                conn.execute(text("LOAD 'age'"))
                conn.execute(text("SET search_path = ag_catalog, public"))
                for oid in onto_ids:
                    try:
                        rows = conn.execute(text(
                            f"SELECT * FROM cypher('enterprise_onto', $$ "
                            f"MATCH (a:Entity {{onto_id: '{oid}'}})-[r]->(b:Entity) "
                            f"RETURN a.onto_id, type(r), b.onto_id "
                            f"$$) AS (src agtype, rel agtype, tgt agtype)"
                        )).fetchall()
                        for row in rows:
                            src = str(row[0]).strip('"')
                            rel = str(row[1]).strip('"')
                            tgt = str(row[2]).strip('"')
                            all_edges.append({"source": src, "target": tgt, "type": rel, "description": ""})
                            all_nodes.add(tgt)
                    except Exception:
                        pass
                    try:
                        rows = conn.execute(text(
                            f"SELECT * FROM cypher('enterprise_onto', $$ "
                            f"MATCH (a:Entity)-[r]->(b:Entity {{onto_id: '{oid}'}}) "
                            f"RETURN a.onto_id, type(r), b.onto_id "
                            f"$$) AS (src agtype, rel agtype, tgt agtype)"
                        )).fetchall()
                        for row in rows:
                            src = str(row[0]).strip('"')
                            rel = str(row[1]).strip('"')
                            tgt = str(row[2]).strip('"')
                            all_edges.append({"source": src, "target": tgt, "type": rel, "description": ""})
                            all_nodes.add(src)
                    except Exception:
                        pass
            seen = set()
            unique_edges = []
            for e in all_edges:
                key = (e["source"], e["type"], e["target"])
                if key not in seen:
                    seen.add(key)
                    unique_edges.append(e)
            return {"nodes": [{"id": n} for n in all_nodes], "edges": unique_edges}

        return await loop.run_in_executor(None, _query)

    def _reset_age_cache(self):
        """Reset AGE availability cache so the next call re-checks."""
        self._age_available = None
        self._age_checked_at = 0

    async def _is_age_available(self) -> bool:
        import time
        now = time.monotonic()
        if self._age_available is not None and (now - self._age_checked_at) < 60:
            return self._age_available
        try:
            loop = asyncio.get_event_loop()
            engine = self._conn.engine
            if engine is None:
                self._age_available = False
                self._age_checked_at = now
                return False

            def _check():
                from sqlalchemy import text
                with engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT 1 FROM pg_extension WHERE extname = 'age'"
                    ))
                    if result.fetchone() is None:
                        return False
                    try:
                        conn.execute(text("LOAD 'age'"))
                        conn.execute(text("SET search_path = ag_catalog, public"))
                        conn.execute(text(
                            "SELECT * FROM cypher('enterprise_onto', $$ MATCH (n) RETURN count(n) $$) AS (cnt agtype)"
                        ))
                        return True
                    except Exception:
                        return False

            self._age_available = await loop.run_in_executor(None, _check)
            self._age_checked_at = now
            cp_logger.info(f"AGE availability check: {self._age_available}")
        except Exception:
            self._age_available = False
            self._age_checked_at = now
        return self._age_available

    async def _expand_age(self, onto_ids: List[str], hops: int) -> List[Dict[str, Any]]:
        """Traverse Apache AGE graph for neighbors."""
        results = []
        try:
            loop = asyncio.get_event_loop()
            engine = self._conn.engine

            def _query():
                from sqlalchemy import text
                neighbors = []
                with engine.connect() as conn:
                    conn.execute(text("LOAD 'age'"))
                    conn.execute(text("SET search_path = ag_catalog, public"))
                    for oid in onto_ids:
                        for hop in range(1, hops + 1):
                            cypher = (
                                f"MATCH (a:Entity {{onto_id: '{oid}'}})-[r]->{'()-[]->'*(hop-1)}(b:Entity) "
                                f"RETURN DISTINCT b.onto_id AS neighbor, type(r) AS rel_type"
                            ) if hop == 1 else (
                                f"MATCH (a:Entity {{onto_id: '{oid}'}})-[]->(mid)-[r2]->(b:Entity) "
                                f"WHERE a <> b "
                                f"RETURN DISTINCT b.onto_id AS neighbor, type(r2) AS rel_type"
                            )
                            try:
                                sql = (f"SELECT * FROM cypher('enterprise_onto', $$ {cypher} $$) "
                                       f"AS (neighbor agtype, rel_type agtype)")
                                rows = conn.execute(text(sql)).fetchall()
                                for row in rows:
                                    nid = str(row[0]).strip('"')
                                    rtype = str(row[1]).strip('"')
                                    if not any(n["onto_id"] == nid for n in neighbors):
                                        neighbors.append({
                                            "onto_id": nid,
                                            "relation_type": rtype,
                                            "source_id": oid,
                                            "hop_distance": hop,
                                        })
                            except Exception as ex:
                                cp_logger.debug(f"AGE hop-{hop} query failed for {oid}: {ex}")
                return neighbors

            results = await loop.run_in_executor(None, _query)
        except Exception as e:
            cp_logger.warning(f"AGE query failed, resetting cache and falling back to metadata: {e}")
            self._reset_age_cache()
            results = await self._expand_metadata(onto_ids, hops)
        return results

    async def _expand_metadata(self, onto_ids: List[str], hops: int) -> List[Dict[str, Any]]:
        """Traverse metadata-based relationship index."""
        index = await self._get_relationship_index()
        visited: Set[str] = set(onto_ids)
        frontier = list(onto_ids)
        results = []

        for hop in range(1, hops + 1):
            next_frontier = []
            for oid in frontier:
                for rel in index.get(oid, []):
                    target = rel["target"]
                    if target not in visited:
                        visited.add(target)
                        next_frontier.append(target)
                        results.append({
                            "onto_id": target,
                            "relation_type": rel["type"],
                            "description": rel.get("description", ""),
                            "source_id": oid,
                            "hop_distance": hop,
                        })
            frontier = next_frontier

        return results

    async def _get_relationship_index(self) -> Dict[str, List[Dict]]:
        if self._relationship_cache is not None:
            return self._relationship_cache

        try:
            results = await self._vector.search(
                query_embedding=[0.0] * 1536,
                content_type="onto_graph_index",
                limit=1,
                min_similarity=-1.0,
            )
            if results:
                self._relationship_cache = json.loads(results[0].get("content", "{}"))
            else:
                self._relationship_cache = {}
        except Exception:
            self._relationship_cache = {}

        return self._relationship_cache
