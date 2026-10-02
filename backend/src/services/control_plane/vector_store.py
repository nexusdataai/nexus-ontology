"""
Vector Store for the AI Control Plane.

Provides CRUD and cosine-similarity search over the control_plane_embeddings
table in BSSMagic Postgres (pgvector).  Reuses the existing FDW connection
pool via SQLAlchemy so no new DB connections are needed.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import text

from src.services.fdw_connection_manager import PostgreSQLConnectionManager

cp_logger = logger.bind(component="control-plane")

TABLE = "control_plane_embeddings"


class VectorStore:
    """pgvector-backed store for schema / policy / TMF embeddings."""

    def __init__(self, connection_manager: PostgreSQLConnectionManager):
        self._conn = connection_manager
        self._schema_ready = False

    async def ensure_schema(self) -> None:
        """Create pgvector extension and embeddings table if missing (local dev bootstrap)."""
        if self._schema_ready:
            return
        statements = [
            "CREATE EXTENSION IF NOT EXISTS vector",
            """CREATE TABLE IF NOT EXISTS control_plane_embeddings (
                id SERIAL PRIMARY KEY,
                content_type VARCHAR(50) NOT NULL,
                source_id VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB DEFAULT '{}',
                embedding vector(1536),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(content_type, source_id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_cpe_content_type ON control_plane_embeddings(content_type)",
        ]
        loop = asyncio.get_event_loop()
        for stmt in statements:
            await loop.run_in_executor(None, lambda s=stmt: self._exec(text(s), {}))
        self._schema_ready = True
        cp_logger.info("control_plane_embeddings schema ensured")

    async def upsert(
        self,
        content_type: str,
        source_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        sql = text(f"""
            INSERT INTO {TABLE} (content_type, source_id, content, embedding, metadata, updated_at)
            VALUES (:ct, :sid, :content, :emb, :meta, NOW())
            ON CONFLICT (content_type, source_id)
            DO UPDATE SET content = EXCLUDED.content,
                          embedding = EXCLUDED.embedding,
                          metadata = EXCLUDED.metadata,
                          updated_at = NOW()
        """)
        params = {
            "ct": content_type,
            "sid": source_id,
            "content": content,
            "emb": _vec_literal(embedding),
            "meta": json.dumps(metadata or {}),
        }
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._exec(sql, params))

    async def upsert_batch(
        self,
        rows: List[Dict[str, Any]],
    ) -> int:
        """Upsert multiple rows. Each dict must have: content_type, source_id, content, embedding, metadata."""
        count = 0
        for row in rows:
            await self.upsert(
                content_type=row["content_type"],
                source_id=row["source_id"],
                content=row["content"],
                embedding=row["embedding"],
                metadata=row.get("metadata"),
            )
            count += 1
        return count

    async def search(
        self,
        query_embedding: List[float],
        content_type: Optional[str] = None,
        limit: int = 10,
        min_similarity: float = 0.3,
        content_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        where = ""
        params: Dict[str, Any] = {
            "emb": _vec_literal(query_embedding),
            "lim": limit,
        }
        if content_type:
            where = "WHERE content_type = :ct"
            params["ct"] = content_type
        elif content_types:
            where = "WHERE content_type = ANY(:cts)"
            params["cts"] = list(content_types)

        sql = text(f"""
            SELECT id, content_type, source_id, content, metadata,
                   1 - (embedding <=> :emb) AS similarity
            FROM {TABLE}
            {where}
            ORDER BY embedding <=> :emb
            LIMIT :lim
        """)

        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, lambda: self._query(sql, params))
        return [r for r in rows if r["similarity"] >= min_similarity]

    async def list(
        self,
        content_type: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
        search_text: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        conditions = []
        params: Dict[str, Any] = {"off": offset, "lim": limit}

        if content_type:
            conditions.append("content_type = :ct")
            params["ct"] = content_type
        if search_text:
            conditions.append("(source_id ILIKE :q OR content ILIKE :q)")
            params["q"] = f"%{search_text}%"

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_sql = text(f"SELECT COUNT(*) as cnt FROM {TABLE} {where}")
        data_sql = text(f"""
            SELECT id, content_type, source_id, content, metadata, updated_at
            FROM {TABLE}
            {where}
            ORDER BY updated_at DESC
            OFFSET :off LIMIT :lim
        """)

        loop = asyncio.get_event_loop()
        count_rows = await loop.run_in_executor(None, lambda: self._query(count_sql, params))
        total = count_rows[0]["cnt"] if count_rows else 0
        rows = await loop.run_in_executor(None, lambda: self._query(data_sql, params))
        return rows, total

    async def get_by_source_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        sql = text(f"""
            SELECT id, content_type, source_id, content, metadata, updated_at
            FROM {TABLE}
            WHERE source_id = :sid
            LIMIT 1
        """)
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, lambda: self._query(sql, {"sid": source_id}))
        return rows[0] if rows else None

    async def max_updated_at(self) -> Optional[str]:
        sql = text(f"SELECT MAX(updated_at) as last_ts FROM {TABLE}")
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, lambda: self._query(sql, {}))
        val = rows[0]["last_ts"] if rows else None
        return str(val) if val else None

    async def delete_by_type(self, content_type: str) -> int:
        sql = text(f"DELETE FROM {TABLE} WHERE content_type = :ct")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._exec_returning_count(sql, {"ct": content_type})
        )

    async def count(self, content_type: Optional[str] = None) -> int:
        if content_type:
            sql = text(f"SELECT COUNT(*) as cnt FROM {TABLE} WHERE content_type = :ct")
            params = {"ct": content_type}
        else:
            sql = text(f"SELECT COUNT(*) as cnt FROM {TABLE}")
            params = {}
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, lambda: self._query(sql, params))
        return rows[0]["cnt"] if rows else 0

    async def count_by_content_type(self) -> Dict[str, int]:
        """Return ``{content_type: count}`` for every content_type in the table.

        Powers the Diagnostics > Automation > Copilot Runtime panel's
        vector-index coverage tile. Single GROUP BY query.
        """
        sql = text(
            f"SELECT content_type, COUNT(*) as cnt FROM {TABLE} GROUP BY content_type"
        )
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, lambda: self._query(sql, {}))
        return {r["content_type"]: int(r["cnt"]) for r in rows}

    def _get_engine(self):
        engine = self._conn.engine
        if engine is None:
            raise RuntimeError("PostgreSQL connection not initialized")
        return engine

    def _exec(self, sql, params):
        with self._get_engine().connect() as conn:
            conn.execute(sql, params)
            conn.commit()

    def _exec_returning_count(self, sql, params) -> int:
        with self._get_engine().connect() as conn:
            result = conn.execute(sql, params)
            conn.commit()
            return result.rowcount

    def _query(self, sql, params) -> List[Dict[str, Any]]:
        with self._get_engine().connect() as conn:
            result = conn.execute(sql, params)
            cols = list(result.keys())
            return [dict(zip(cols, row)) for row in result.fetchall()]


def _vec_literal(embedding: List[float]) -> str:
    return "[" + ",".join(str(v) for v in embedding) + "]"
