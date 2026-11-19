"""
Legacy startup hook for external VDL mappings.

When ``VDL_MAPPING_VIA_ETL_ONLY`` is true (default), the HTTP gateway does not
call this module; mappings are created by the ETL pipeline ``register_vdl`` step.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.services.external_vdl_etl_service import RAW_VIRTUAL_TO_TABLE, register_vdl_for_source_type
from src.services.mapping_rule_service import MappingRuleService

__all__ = ["RAW_VIRTUAL_TO_TABLE", "ensure_external_source_vdl_mappings"]


async def ensure_external_source_vdl_mappings(
    mapping_service: MappingRuleService,
    simulators: Optional[Dict[str, Any]] = None,
    *,
    force_recreate: bool = False,
) -> Dict[str, Any]:
    """Register all external raw + warehouse mappings (startup fallback only)."""
    if force_recreate:
        existing = await mapping_service.list_all()
        for rule in existing:
            name = rule.name or ""
            if name.startswith(("ETL External source:", "ETL External warehouse:", "External source VDL:")):
                try:
                    await mapping_service.delete(rule.id)
                except Exception:
                    pass
    return await register_vdl_for_source_type(
        mapping_service,
        simulators or {},
        "external_full",
        job_id="startup-seed",
    )