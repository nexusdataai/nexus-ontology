"""Gate in-cluster Python flow execution (preview-run, processor probes) on shared dev hosts."""
from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import HTTPException

_ENV_KEY = "NEXUS_FLOW_RUNTIME_EXECUTION"
_LEGACY_ENV_KEY = "NEXUS_NIFI_RUNTIME_EXECUTION"  # deprecated env name only


def flow_runtime_execution_enabled() -> bool:
    raw = os.getenv(_ENV_KEY)
    if raw is None:
        raw = os.getenv(_LEGACY_ENV_KEY, "false")
    return raw.strip().lower() in ("1", "true", "yes", "on")


def runtime_execution_capabilities() -> Dict[str, Any]:
    enabled = flow_runtime_execution_enabled()
    return {
        "runtimeExecution": enabled,
        "envKey": _ENV_KEY,
        "message": (
            "Python flow execution is enabled on this host."
            if enabled
            else (
                "Python flow execution is disabled on this host "
                f"(set {_ENV_KEY}=true to enable local dry-runs; production runs use Nexus journey stage nexus_flow)."
            )
        ),
    }


def require_flow_runtime_execution() -> None:
    if flow_runtime_execution_enabled():
        return
    cap = runtime_execution_capabilities()
    raise HTTPException(
        status_code=503,
        detail={
            "error": "flow_runtime_execution_disabled",
            "message": cap["message"],
            "capabilities": cap,
        },
    )

