"""
FDW Integration Lifecycle Management

Handles initialization and shutdown of PostgreSQL FDW services and
registers remote nexus-simulator HTTP clients. Ontology never boots
in-process Redis catalogs.
"""

import os

from loguru import logger

fdw_logger = logger.bind(component="fdw")

_connection_manager = None
_discovery_service = None
_query_service = None


async def initialize_fdw():
    """Initialize FDW services and register remote simulators.

    Returns True if PostgreSQL FDW was initialized, False if disabled.
    Simulator registration is required when SIMULATOR_ENABLED is true
    (the K8s default) and fails fast if SIMULATOR_BASE_URL is missing.
    """
    global _connection_manager, _discovery_service, _query_service

    sim_enabled = os.getenv("SIMULATOR_ENABLED", "true").lower() != "false"
    remote_url = (os.getenv("SIMULATOR_BASE_URL") or "").strip()
    if sim_enabled and not remote_url:
        raise RuntimeError(
            "SIMULATOR_ENABLED is true but SIMULATOR_BASE_URL is not set. "
            "Ontology is remote-only; set SIMULATOR_BASE_URL to the in-cluster "
            "simulator backend, e.g. "
            "http://simulator-local-backend-svc-internal.simulator-local.svc.cluster.local:8000"
        )
    if sim_enabled:
        from src.services.simulator_fdw_client import register_remote_simulators

        register_remote_simulators(remote_url)
        fdw_logger.info("Using remote nexus-simulator", url=remote_url)

    from src.config.fdw_config import is_fdw_enabled, get_fdw_config

    if not is_fdw_enabled():
        fdw_logger.info("FDW integration disabled (FDW_PG_HOST not set)")
        return False

    config = get_fdw_config()
    fdw_logger.info(
        "Initializing FDW integration",
        host=config.host,
        port=config.port,
        database=config.database,
    )

    try:
        from src.services.fdw_connection_manager import PostgreSQLConnectionManager

        _connection_manager = PostgreSQLConnectionManager(config)
        await _connection_manager.initialize()
        fdw_logger.info("PostgreSQL connection manager initialized")

        from src.services.fdw_discovery_service import FDWDiscoveryService

        _discovery_service = FDWDiscoveryService(_connection_manager)
        fdw_logger.info("FDW discovery service initialized")

        from src.services.fdw_query_service import FDWQueryService

        _query_service = FDWQueryService(_connection_manager, _discovery_service)
        fdw_logger.info("FDW query service initialized")

        from src.apis import fdw_api, health_api

        fdw_api.configure(
            connection_manager=_connection_manager,
            discovery_service=_discovery_service,
            query_service=_query_service,
        )
        health_api.configure_fdw(
            connection_manager=_connection_manager,
            discovery_service=_discovery_service,
        )
        fdw_logger.info("FDW integration fully initialized")
        return True

    except Exception as e:
        fdw_logger.warning(
            "FDW initialization failed, running in degraded mode", error=str(e)
        )
        if _connection_manager is not None:
            try:
                from src.apis import health_api

                health_api.configure_fdw(connection_manager=_connection_manager)
            except Exception:
                pass
        return False


async def shutdown_fdw():
    """Shutdown all FDW services. Safe to call even if FDW was not initialized."""
    global _connection_manager

    if _connection_manager is not None:
        try:
            await _connection_manager.close()
            fdw_logger.info("PostgreSQL connection pool closed")
        except Exception as e:
            fdw_logger.warning("Error closing FDW connection pool", error=str(e))
        _connection_manager = None
