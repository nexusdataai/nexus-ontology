"""Gate NiFi-shaped Python flow execution (preview-run, probes) on shared dev hosts."""
from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import HTTPException

_ENV_KEY = "NEXUS_NIFI_RUNTIME_EXECUTION"


def nifi_runtime_execution_enabled() -> bool:
    return os.getenv(_ENV_KEY, "false").strip().lower() in ("1", "true", "yes", "on")


def runtime_execution_capabilities() -> Dict[str, Any]:
    enabled = nifi_runtime_execution_enabled()
    return {
        "runtimeExecution": enabled,
        "envKey": _ENV_KEY,
        "message": (
            "NiFi/Python flow execution is enabled."
            if enabled
            else (
                "NiFi/Python flow execution is disabled on this host "
                f"(set {_ENV_KEY}=true to enable local dry-runs; production runs use Nexus journey stage nexus_flow)."
            )
        ),
    }


def require_nifi_runtime_execution() -> None:
    if nifi_runtime_execution_enabled():
        return
    cap = runtime_execution_capabilities()
    raise HTTPException(
        status_code=503,
        detail={
            "error": "nifi_runtime_execution_disabled",
            "message": cap["message"],
            "capabilities": cap,
        },
    )