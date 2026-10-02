"""
Plane taxonomy.

Maps the five conceptual planes from
``nexus-docs/docs/architecture/data-organization.md`` to concrete
foundry-workspace PK prefixes. Consumed by:

- ``nexus-deployer/backup-restore/plane_backup.py`` for plane-scoped TAR
  packaging.
- ``AIHealthService`` for per-plane row-count metrics.
- Audit tagging / plane labeling in the frontend.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, Optional


class Plane(str, Enum):
    AI_OPS = "ai_ops"
    DATA = "data"
    CONTROL = "control"
    REASONING = "reasoning"
    WORKSPACE = "workspace"


# Foundry-workspace PK prefixes (no trailing ``#``) grouped by owning plane.
# Keep in sync with the header table in
# ``src/repositories/foundry_workspace_repository.py``.
FOUNDRY_PK_PREFIXES_BY_PLANE: Dict[Plane, FrozenSet[str]] = {
    Plane.AI_OPS: frozenset({
        "SIM",
    }),
    Plane.DATA: frozenset({
        "DATAPLANE",
        "DATASOURCE",
        "VDLENTITY",
        "VDLAPI",
        "CONNECTOR",
        "CONNAPI",
        "CONNECTORSETTING",
        "MAPPINGRULE",
    }),
    Plane.CONTROL: frozenset({
        "POLICY",
        "WORKFLOWDEF",
        "INTEGRATIONDEF",
        "KP",
    }),
    Plane.REASONING: frozenset({
        "TOOL",
        "TOOLREG",
    }),
    Plane.WORKSPACE: frozenset({
        "SOLUTION",
        "SOLUTIONYAML",
        "VIEW",
        "DASHBOARD",
        "JOURNEY",
        "AUTOMATION",
    }),
}

# Reverse index: PK prefix -> Plane. Built at module import.
PLANE_BY_FOUNDRY_PK_PREFIX: Dict[str, Plane] = {
    prefix: plane
    for plane, prefixes in FOUNDRY_PK_PREFIXES_BY_PLANE.items()
    for prefix in prefixes
}


def plane_for_pk(pk: str) -> Optional[Plane]:
    """Return the owning plane for a foundry-workspace PK string.

    ``pk`` may be either the bare prefix (``"DATAPLANE"``) or a full PK
    (``"DATAPLANE#supply-chain-1"``). Returns ``None`` for unknown prefixes.
    """
    if not pk:
        return None
    prefix = pk.split("#", 1)[0]
    return PLANE_BY_FOUNDRY_PK_PREFIX.get(prefix)


def all_foundry_pk_prefixes() -> FrozenSet[str]:
    """Every foundry-workspace PK prefix known to the plane taxonomy."""
    return frozenset(PLANE_BY_FOUNDRY_PK_PREFIX.keys())


# Names of DDB tables (as returned by ``ConfigProvider``) that are scoped to
# each plane. Used by backup/restore to know which whole tables to bundle
# alongside the plane's foundry-workspace slice.
EXTERNAL_TABLES_BY_PLANE: Dict[Plane, FrozenSet[str]] = {
    Plane.AI_OPS: frozenset({"diagnostics", "health"}),
    Plane.DATA: frozenset(),
    Plane.CONTROL: frozenset(),
    Plane.REASONING: frozenset(),
    # RBAC is workspace-owned per the spec.
    Plane.WORKSPACE: frozenset({"rbac"}),
}


__all__ = [
    "Plane",
    "FOUNDRY_PK_PREFIXES_BY_PLANE",
    "PLANE_BY_FOUNDRY_PK_PREFIX",
    "EXTERNAL_TABLES_BY_PLANE",
    "plane_for_pk",
    "all_foundry_pk_prefixes",
]
