"""
Data Plane Lifecycle Management

Handles initialization and shutdown of the Data Plane service.
Called from the gateway startup/shutdown events.
"""

from loguru import logger

dp_logger = logger.bind(component="data-plane")

_data_plane_service = None


async def initialize_data_plane():
    """Initialize Data Plane service and configure API."""
    global _data_plane_service
    try:
        from src.services.data_plane_service import DataPlaneService
        from src.apis import data_plane_api

        _data_plane_service = DataPlaneService()
        await _data_plane_service.initialize()
        data_plane_api.configure(service=_data_plane_service)
        dp_logger.info("Data Plane service initialized")
        return True
    except Exception as e:
        dp_logger.warning("Data Plane initialization failed", error=str(e))
        return False


async def shutdown_data_plane():
    """Shutdown Data Plane service."""
    global _data_plane_service
    _data_plane_service = None
