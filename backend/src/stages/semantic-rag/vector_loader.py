"""
Vector DB Loader

Upserts enriched embedding chunks into the pgvector control_plane_embeddings table.
Initializes VectorStore with proper FDW connection manager.
"""

import asyncio
from typing import List, Dict, Any


class VectorLoader:
    def __init__(self, logger=None, progress_callback=None):
        self._log = logger
        self._progress_callback = progress_callback

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def _emit_progress(self, done, total):
        if self._progress_callback:
            try:
                self._progress_callback(done, total)
            except Exception:
                pass

    def _get_store(self):
        from src.services.fdw_connection_manager import PostgreSQLConnectionManager
        from src.services.control_plane.vector_store import VectorStore
        from src.config.fdw_config import FDWConfig

        config = FDWConfig.from_environment()
        conn_mgr = PostgreSQLConnectionManager(config)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(conn_mgr.initialize())

        return VectorStore(conn_mgr)

    def load(self, embeddings: List[Dict[str, Any]]) -> Dict[str, int]:
        total = len(embeddings)
        self._info(f"Loading {total} embeddings into pgvector control_plane_embeddings")

        try:
            store = self._get_store()
            self._info(f"VectorStore connected to PostgreSQL")
        except Exception as e:
            self._info(f"VectorStore not available: {e}")
            return {"upserted": 0, "errors": 1, "error_message": str(e)}

        try:
            from sqlalchemy import text
            engine = store._conn.engine
            if engine:
                with engine.connect() as conn:
                    conn.execute(text("TRUNCATE TABLE control_plane_embeddings"))
                    conn.commit()
                    self._info(f"Cleared old embeddings from control_plane_embeddings (TRUNCATE)")
        except Exception as e:
            self._info(f"Warning: could not clear old embeddings (non-fatal): {e}")

        upserted = 0
        errors = 0
        content_types: Dict[str, int] = {}

        import time as _time

        loop = asyncio.get_event_loop()
        for i, chunk in enumerate(embeddings):
            success = False
            for retry in range(3):
                try:
                    loop.run_until_complete(store.upsert(
                        content_type=chunk["content_type"],
                        source_id=chunk["source_id"],
                        content=chunk["content"],
                        metadata=chunk["metadata"],
                        embedding=chunk["embedding"],
                    ))
                    upserted += 1
                    ct = chunk.get("content_type", "unknown")
                    content_types[ct] = content_types.get(ct, 0) + 1
                    success = True
                    break
                except Exception as e:
                    if retry < 2:
                        _time.sleep(1)
                        continue
                    errors += 1
                    if errors <= 5:
                        self._info(f"  Failed to upsert {chunk.get('source_id', '?')} after 3 retries: {e}")

            if (i + 1) % 100 == 0:
                self._info(f"  Progress: {upserted}/{i+1} upserted ({errors} errors)")
                self._emit_progress(i + 1, total)

        type_summary = ", ".join(f"{k}={v}" for k, v in sorted(content_types.items()))
        self._info(f"Vector load complete: {upserted}/{total} upserted, {errors} errors")
        self._info(f"  Content types: {type_summary}")
        return {"upserted": upserted, "errors": errors, "total": total, "content_types": content_types}
