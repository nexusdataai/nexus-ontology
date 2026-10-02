"""
Register user-authored DDB tools into the live ``ToolRegistry``.

Called once at the end of ``control_plane_api._ensure_init`` AFTER the
code-defined ``register_*tools`` calls. Code-defined tools win on name
conflict (we log a warning and skip the DDB version).

The injected ``invoke_connector_fn`` is the Workbench's in-process
``_invoke`` so user tools go through the same verification+audit path as
direct REST calls. ``emit_audit_fn`` is ``connector_runtime.emit_audit``.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from loguru import logger

from src.services.control_plane.dynamic_tool_loader import DynamicToolLoader
from src.services.control_plane.tool_registry import ToolRegistry

ddb_logger = logger.bind(component="dynamodb-tools")


async def register_dynamodb_tools(
    registry: ToolRegistry,
    *,
    store: Any,
    virtual_query_service: Any = None,
    invoke_connector_fn: Optional[Callable[[str, dict], Awaitable[dict]]] = None,
    emit_audit_fn: Optional[Callable[..., Awaitable[Any]]] = None,
) -> "DynamicToolLoader":
    """Wire a ``DynamicToolLoader`` and register every active DDB tool.

    Returns the loader so callers (the API router, the cache invalidator)
    can keep a handle on it for ``invalidate(tool_id)`` calls.
    """
    loader = DynamicToolLoader(
        store=store,
        virtual_query_service=virtual_query_service,
        invoke_connector_fn=invoke_connector_fn,
        emit_audit_fn=emit_audit_fn,
    )
    try:
        count = await loader.register_all_active(registry)
        ddb_logger.info("Registered {} DynamoDB tools", count)
    except Exception as e:
        ddb_logger.warning("DynamoDB tools registration failed (non-fatal): {}", e)
    return loader
