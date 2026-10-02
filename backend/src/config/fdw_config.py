"""
FDW (Foreign Data Wrapper) Configuration Module for nexus-backend

This module provides configuration management for PostgreSQL FDW integration,
following the same dataclass + from_environment() + module-level helpers pattern
as LocalStackConfig.

Configuration Loading:
- When FDW_PG_HOST is set, FDW integration is enabled
- When FDW_PG_HOST is not set, FDW integration is disabled and no PostgreSQL code runs
"""

import os
from dataclasses import dataclass
from typing import Optional, List

from loguru import logger

# Import canonical FDWConfigurationError from fdw_errors and re-export it
# so that existing code importing from fdw_config still works.
from src.utils.fdw_errors import FDWConfigurationError  # noqa: F401

fdw_logger = logger.bind(component="fdw")


@dataclass
class FDWConfig:
    """
    Configuration for PostgreSQL FDW integration.

    Attributes:
        enabled: Whether FDW integration is active (FDW_PG_HOST is set)
        host: PostgreSQL host
        port: PostgreSQL port (default: 5432)
        database: PostgreSQL database name
        user: PostgreSQL user
        password: PostgreSQL password
        schema: Default schema (default: "public")
        ssl_mode: SSL mode (default: "prefer")
        pool_min: Minimum pool connections (default: 2)
        pool_max: Maximum pool connections (default: 10)
        query_timeout: Query timeout in seconds (default: 30)
    """

    enabled: bool
    host: str
    port: int
    database: str
    user: str
    password: str
    schema: str
    ssl_mode: str
    pool_min: int
    pool_max: int
    query_timeout: int

    @classmethod
    def from_environment(cls) -> 'FDWConfig':
        """
        Load FDW configuration from environment variables.

        Environment Variables:
            FDW_PG_HOST: PostgreSQL host (enables FDW when set)
            FDW_PG_PORT: PostgreSQL port (default: 5432)
            FDW_PG_DATABASE: Database name (required when enabled)
            FDW_PG_USER: Database user (required when enabled)
            FDW_PG_PASSWORD: Database password (required when enabled)
            FDW_PG_SCHEMA: Default schema (default: "public")
            FDW_PG_SSL_MODE: SSL mode (default: "prefer")
            FDW_PG_POOL_MIN: Min pool connections (default: 2)
            FDW_PG_POOL_MAX: Max pool connections (default: 10)
            FDW_PG_QUERY_TIMEOUT: Query timeout in seconds (default: 30)

        Returns:
            FDWConfig instance with settings from environment

        Raises:
            FDWConfigurationError: When FDW_PG_HOST is set but required params are missing
        """
        host = os.getenv('FDW_PG_HOST', '').strip()

        if not host:
            # FDW is disabled
            fdw_logger.debug("FDW integration disabled - FDW_PG_HOST not set")
            return cls(
                enabled=False,
                host='',
                port=5432,
                database='',
                user='',
                password='',
                schema='public',
                ssl_mode='prefer',
                pool_min=2,
                pool_max=10,
                query_timeout=30,
            )

        # FDW is enabled — read all params
        database = os.getenv('FDW_PG_DATABASE', '').strip()
        user = os.getenv('FDW_PG_USER', '').strip()
        password = os.getenv('FDW_PG_PASSWORD', '').strip()

        # Validate required params
        missing: List[str] = []
        if not database:
            missing.append('FDW_PG_DATABASE')
        if not user:
            missing.append('FDW_PG_USER')
        if not password:
            missing.append('FDW_PG_PASSWORD')

        if missing:
            raise FDWConfigurationError(missing)

        # Parse port with fallback
        port_str = os.getenv('FDW_PG_PORT', '5432').strip()
        try:
            port = int(port_str)
        except ValueError:
            fdw_logger.warning("Invalid FDW_PG_PORT, using default", value=port_str, default=5432)
            port = 5432

        schema = os.getenv('FDW_PG_SCHEMA', 'public').strip()
        ssl_mode = os.getenv('FDW_PG_SSL_MODE', 'prefer').strip()

        # Parse pool sizes with fallback
        pool_min = _parse_int_env('FDW_PG_POOL_MIN', 2)
        pool_max = _parse_int_env('FDW_PG_POOL_MAX', 10)
        query_timeout = _parse_int_env('FDW_PG_QUERY_TIMEOUT', 30)

        config = cls(
            enabled=True,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            schema=schema,
            ssl_mode=ssl_mode,
            pool_min=pool_min,
            pool_max=pool_max,
            query_timeout=query_timeout,
        )

        fdw_logger.info(
            "FDW configuration loaded",
            host=host,
            port=port,
            database=database,
            schema=schema,
            ssl_mode=ssl_mode,
            pool_min=pool_min,
            pool_max=pool_max,
            query_timeout=query_timeout,
        )
        return config

    @property
    def connection_url(self) -> str:
        """
        Get the PostgreSQL connection URL.

        Returns:
            Connection URL in the format:
            postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}
        """
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    def __repr__(self) -> str:
        """String representation (excludes password)."""
        if self.enabled:
            return (
                f"FDWConfig(enabled=True, host={self.host}:{self.port}, "
                f"database={self.database}, schema={self.schema})"
            )
        return "FDWConfig(enabled=False)"


def _parse_int_env(var_name: str, default: int) -> int:
    """Parse an integer environment variable with a fallback default."""
    val = os.getenv(var_name, '').strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        fdw_logger.warning("Invalid environment variable, using default", var_name=var_name, value=val, default=default)
        return default


# Global configuration instance (lazy-loaded)
_global_config: Optional[FDWConfig] = None


def get_fdw_config() -> FDWConfig:
    """
    Get the global FDW configuration instance.

    Returns:
        FDWConfig instance (creates one if not exists)
    """
    global _global_config
    if _global_config is None:
        _global_config = FDWConfig.from_environment()
    return _global_config


def is_fdw_enabled() -> bool:
    """
    Check if FDW integration is enabled.

    Returns:
        True if FDW integration is enabled, False otherwise
    """
    return get_fdw_config().enabled


def reset_fdw_config() -> None:
    """
    Reset the global FDW configuration.

    Useful for testing or when environment variables change.
    """
    global _global_config
    _global_config = None
