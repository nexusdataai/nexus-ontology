"""Single-processor probe + source resolution for the Nexus processor registry."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.constants.nifi_processor_seeds import live_processor_ids
from src.services.flow_runtime.execution_policy import nifi_runtime_execution_enabled, require_nifi_runtime_execution
from src.services.flow_runtime.flowfile import FlowFile

_FLOW_PROCESSORS_DIR = Path(__file__).resolve().parents[1] / "flow_processors"

_DEFAULT_CANARIES: Dict[str, Dict[str, Any]] = {
    "nifi.UpdateAttribute": {
        "params": {"probe": "ok", "mime.type": "application/json"},
        "content": "{}",
        "attributes": {},
    },
    "nifi.EvaluateJsonPath": {
        "params": {"destination": "flowfile-attribute", "resultAttributeName": "eval.id", "id": "$.id"},
        "content": '{"id": "42"}',
        "attributes": {"mime.type": "application/json"},
    },
    "nifi.ConvertRecord": {
        "params": {"Record Reader": "json", "Record Writer": "json"},
        "content": '{"name": "nexus"}',
        "attributes": {"mime.type": "application/json"},
    },
    "nifi.JoltTransformJSON": {
        "params": {"Jolt Specification": '[{"operation":"shift","spec":{"id":"value"}}]'},
        "content": '{"id": "x"}',
        "attributes": {"mime.type": "application/json"},
    },
    "nifi.ReplaceText": {
        "params": {"Search Value": "nexus", "Replacement Value": "NEXUS"},
        "content": "hello nexus",
        "attributes": {"mime.type": "text/plain"},
    },
    "nifi.RouteOnAttribute": {
        "params": {"Routing Strategy": "Route to Property name", "route.ok": "${probe:equals('ok')}"},
        "content": "{}",
        "attributes": {"probe": "ok"},
    },
    "nifi.SplitJson": {
        "params": {},
        "content": '[{"a":1},{"a":2}]',
        "attributes": {"mime.type": "application/json"},
    },
    "nifi.MergeContent": {
        "params": {"Merge Strategy": "Bin-Packing Algorithm", "Delimiter Strategy": "Text", "Header Size": "0", "Footer Size": "0"},
        "content": "part",
        "attributes": {},
    },
    "nifi.QueryRecord": {
        "params": {},
        "content": '{"items":[{"id":1}]}',
        "attributes": {"mime.type": "application/json"},
    },
}


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _ensure_flow_processors_imported() -> None:
    import src.services.flow_processors  # noqa: F401


def _get_processor_class(processor_id: str):
    _ensure_flow_processors_imported()
    from src.services.flow_runtime.processor import get_processor_class

    return get_processor_class(processor_id)


def _registered_live_ids() -> set:
    if nifi_runtime_execution_enabled():
        _ensure_flow_processors_imported()
        from src.services.flow_runtime.processor import list_registered_processor_ids

        return set(list_registered_processor_ids())
    return live_processor_ids()


def source_path_for(processor_id: str) -> Optional[Path]:
    if not processor_id.startswith("nifi."):
        return None
    short = processor_id.split(".", 1)[1]
    path = _FLOW_PROCESSORS_DIR / f"{_camel_to_snake(short)}.py"
    return path if path.is_file() else None


def read_processor_source(processor_id: str) -> Dict[str, Any]:
    path = source_path_for(processor_id)
    if path is None:
        return {
            "processorId": processor_id,
            "available": False,
            "path": "",
            "language": "python",
            "source": "",
            "reason": "No Python implementation in flow_processors (stub or not ported yet).",
        }
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "processorId": processor_id,
            "available": False,
            "path": str(path.relative_to(Path(__file__).resolve().parents[3])),
            "language": "python",
            "source": "",
            "reason": str(exc),
        }
    rel = path
    try:
        rel = path.relative_to(Path(__file__).resolve().parents[3])
    except ValueError:
        rel = path
    return {
        "processorId": processor_id,
        "available": True,
        "path": str(rel).replace("\\", "/"),
        "language": "python",
        "source": text,
    }


def default_probe_request(processor_id: str) -> Dict[str, Any]:
    base = _DEFAULT_CANARIES.get(
        processor_id,
        {
            "params": {},
            "content": "{}",
            "attributes": {"mime.type": "application/json"},
        },
    )
    return dict(base)


def probe_processor(
    processor_id: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    content: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    started = time.perf_counter()
    if not nifi_runtime_execution_enabled():
        duration_ms = int((time.perf_counter() - started) * 1000)
        return {
            "processorId": processor_id,
            "status": "skip",
            "duration_ms": duration_ms,
            "reason": "NiFi runtime execution is disabled on this host.",
        }

    if _get_processor_class(processor_id) is None:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return {
            "processorId": processor_id,
            "status": "skip",
            "duration_ms": duration_ms,
            "reason": "Processor is a catalog stub (no live Python runtime).",
        }

    defaults = default_probe_request(processor_id)
    merged_params = {**defaults.get("params", {}), **(params or {})}
    body = content if content is not None else defaults.get("content", "{}")
    attrs = {**defaults.get("attributes", {}), **(attributes or {})}
    if isinstance(body, str):
        raw = body.encode("utf-8")
    else:
        raw = json.dumps(body).encode("utf-8")

    from src.services.flow_runtime.nexus_flow_journey import flowfile_to_state, run_processor_step, state_to_flowfile

    flow_state = flowfile_to_state(FlowFile(content=raw, attributes=dict(attrs)))
    step_out = run_processor_step(processor_id, merged_params, flow_state)
    duration_ms = int((time.perf_counter() - started) * 1000)

    if step_out.get("status") != "ok":
        return {
            "processorId": processor_id,
            "status": "fail",
            "duration_ms": duration_ms,
            "error": step_out.get("error", "step failed"),
            "params": merged_params,
        }

    terminals = []
    if step_out.get("flowState"):
        terminals = [state_to_flowfile(step_out["flowState"]).attributes]
    preview = json.dumps(terminals[0])[:240] if terminals else "no terminal attributes"
    return {
        "processorId": processor_id,
        "status": "pass",
        "duration_ms": duration_ms,
        "result_preview": preview,
        "terminalCount": len(terminals),
        "terminalAttributes": terminals,
        "nodeStats": [{"nodeId": "probe", "type": processor_id, "relationship": step_out.get("relationship")}],
        "params": merged_params,
    }


def probe_batch(processor_ids: List[str]) -> Dict[str, Any]:
    require_nifi_runtime_execution()
    # Cap batch size to avoid fork-bombing a small dev host.
    capped = processor_ids[:12]
    results = [probe_processor(pid) for pid in capped]
    return {
        "total": len(results),
        "results": results,
    }