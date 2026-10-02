"""
PostgreSQL Connection Manager for FDW Integration

Manages a SQLAlchemy engine with connection pooling for the FDW-enabled
PostgreSQL database. Uses synchronous psycopg2 driver wrapped in
asyncio.run_in_executor() to avoid blocking the FastAPI event loop.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from src.config.fdw_config import FDWConfig
from src.utils.fdw_errors import FDWConnectionError

fdw_logger = logger.bind(component="fdw")


class PostgreSQLConnectionManager:
    """
    Manages a SQLAlchemy connection pool to the FDW-enabled PostgreSQL database.

    Uses synchronous psycopg2 via create_engine, with all blocking operations
    dispatched to asyncio's default thread pool executor so the FastAPI event
    loop is never blocked.
    """

    def __init__(self, config: FDWConfig):
        self._config = config
        self._engine: Optional[Engine] = None

    @property
    def engine(self) -> Optional[Engine]:
        """Access the underlying SQLAlchemy engine (None if not initialized or degraded)."""
        return self._engine

    async def initialize(self) -> None:
        """
        Create the SQLAlchemy engine with connection pool.

        Retries up to 3 times with exponential backoff (1s, 2s, 4s).
        On total failure, logs a warning and leaves engine as None (degraded mode)
        so the backend can still start with FDW features unavailable.
        """
        max_retries = 3
        backoff_base = 1  # seconds

        for attempt in range(1, max_retries + 1):
            try:
                loop = asyncio.get_event_loop()
                engine = await loop.run_in_executor(None, self._create_engine)

                # Verify connectivity with a test query
                await loop.run_in_executor(None, self._test_connection, engine)

                self._engine = engine
                fdw_logger.info(
                    "PostgreSQL connection pool initialized",
                    host=self._config.host,
                    port=self._config.port,
                    database=self._config.database,
                    pool_size=self._config.pool_min,
                    max_overflow=self._config.pool_max - self._config.pool_min,
                )
                return

            except Exception as e:
                wait_time = backoff_base * (2 ** (attempt - 1))
                fdw_logger.warning(
                    "PostgreSQL connection attempt failed",
                    attempt=attempt,
                    max_retries=max_retries,
                    wait_seconds=wait_time,
                    host=self._config.host,
                    port=self._config.port,
                    error=str(e),
                )
                if attempt < max_retries:
                    await asyncio.sleep(wait_time)

        # All retries exhausted — degraded mode
        fdw_logger.warning(
            "PostgreSQL connection pool initialization failed after all retries. "
            "FDW features will be unavailable (degraded mode).",
            host=self._config.host,
            port=self._config.port,
        )
        self._engine = None

    def _create_engine(self) -> Engine:
        """Create a SQLAlchemy engine with connection pooling (runs in executor)."""
        pool_size = self._config.pool_min
        max_overflow = self._config.pool_max - self._config.pool_min

        engine = create_engine(
            self._config.connection_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=10,
            pool_pre_ping=True,
        )
        return engine

    def _test_connection(self, engine: Engine) -> None:
        """Verify the engine can actually connect (runs in executor)."""
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    async def close(self) -> None:
        """Dispose of the engine and all pooled connections."""
        if self._engine is not None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._engine.dispose)
            fdw_logger.info("PostgreSQL connection pool closed")
            self._engine = None

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Connection, None]:
        """
        Acquire a connection from the pool, yield it, then release.

        Runs synchronous psycopg2 operations in asyncio's default executor
        so the event loop is not blocked.

        Raises:
            FDWConnectionError: If the engine is not initialized (degraded mode)
                or if connection acquisition fails.
        """
        if self._engine is None:
            raise FDWConnectionError(
                "PostgreSQL connection pool is not initialized (degraded mode)",
                host=self._config.host,
                port=self._config.port,
            )

        loop = asyncio.get_event_loop()
        try:
            conn = await loop.run_in_executor(None, self._engine.connect)
        except Exception as e:
            raise FDWConnectionError(
                f"Failed to acquire connection from pool: {e}",
                host=self._config.host,
                port=self._config.port,
                original_error=e,
            )

        try:
            yield conn
        finally:
            await loop.run_in_executor(None, conn.close)

    async def health_check(self) -> Dict[str, Any]:
        """
        Execute SELECT 1 and return connectivity status with latency.

        Returns:
            Dict with "status" ("healthy" or "unhealthy") and "latency_ms".
            On failure, includes "error" key with the failure reason.
        """
        if self._engine is None:
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "error": "Connection pool not initialized",
            }

        start = time.monotonic()
        try:
            async with self.get_connection() as conn:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: conn.execute(text("SELECT 1")))
            elapsed_ms = (time.monotonic() - start) * 1000
            return {
                "status": "healthy",
                "latency_ms": round(elapsed_ms, 2),
            }
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            fdw_logger.error(
                "Health check failed",
                host=self._config.host,
                port=self._config.port,
                error=str(e),
            )
            return {
                "status": "unhealthy",
                "latency_ms": round(elapsed_ms, 2),
                "error": str(e),
            }
