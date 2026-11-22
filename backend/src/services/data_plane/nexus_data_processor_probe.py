"""Single-processor probe + source resolution for the Nexus flow processor registry."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.constants.flow_processor_seeds import live_processor_ids
from src.services.flow_runtime.execution_policy import flow_runtime_execution_enabled, require_flow_runtime_execution
from src.services.flow_runtime.flow_record import FlowRecord
from src.services.flow_runtime.processor_ids import canonical_processor_id

_FLOW_PROCESSORS_DIR = Path(__file__).resolve().parents[1] / "flow_processors"

_DEFAULT_CANARIES: Dict[str, Dict[str, Any]] = {
    "nexus.UpdateAttribute": {
        "params": {"probe": "ok", "mime.type": "application/json"},
        "content": "{}",
        "attributes": {},
    },
    "nexus.EvaluateJsonPath": {
        "params": {"destination": "record-attribute", "resultAttributeName": "eval.id", "id": "$.id"},
        "content": '{"id": "42"}',
        "attributes": {"mime.type": "application/json"},
    },
    "nexus.ConvertRecord": {
        "params": {"Record Reader": "json", "Record Writer": "json"},
        "content": '{"name": "nexus"}',
        "attributes": {"mime.type": "application/json"},
    },
    "nexus.JoltTransformJSON": {
        "params": {"Jolt Specification": '[{"operation":"shift","spec":{"id":"value"}}]'},
        "content": '{"id": "x"}',
        "attributes": {"mime.type": "application/json"},
    },
    "nexus.ReplaceText": {
        "params": {"Search Value": "nexus", "Replacement Value": "NEXUS"},
        "content": "hello nexus",
        "attributes": {"mime.type": "text/plain"},
    },
    "nexus.RouteOnAttribute": {
        "params": {"Routing Strategy": "Route to Property name", "route.ok": "${probe:equals('ok')}"},
        "content": "{}",
        "attributes": {"probe": "ok"},
    },
    "nexus.SplitJson": {
        "params": {},
        "content": '[{"a":1},{"a":2}]',
        "attributes": {"mime.type": "application/json"},
    },
    "nexus.MergeContent": {
        "params": {"Merge Strategy": "Bin-Packing Algorithm", "Delimiter Strategy": "Text", "Header Size": "0", "Footer Size": "0"},
        "content": "part",
        "attributes": {},
    },
    "nexus.QueryRecord": {
        "params": {},
        "content": '{"items":[{"id":1}]}',
        "attributes": {"mime.type": "application/json"},
    },
}


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _ensure_flow_processors_imported() -> None:
    from src.services.flow_processors import ensure_all_processors_loaded

    ensure_all_processors_loaded()


def _get_processor_class(processor_id: str):
    _ensure_flow_processors_imported()
    from src.services.flow_runtime.processor import get_processor_class

    return get_processor_class(processor_id)


def _registered_live_ids() -> set:
    _ensure_flow_processors_imported()
    from src.services.flow_runtime.processor import list_registered_processor_ids

    return set(list_registered_processor_ids())


def source_path_for(processor_id: str) -> Optional[Path]:
    cid = canonical_processor_id(processor_id)
    if "." in cid:
        short = cid.split(".", 1)[1]
        path = _FLOW_PROCESSORS_DIR / f"{_camel_to_snake(short)}.py"
        if path.is_file():
            return path
    return None


def read_processor_source(processor_id: str) -> Dict[str, Any]:
    path = source_path_for(processor_id)
    if path is None or not _get_processor_class(processor_id):
        return {
            "processorId": canonical_processor_id(processor_id),
            "available": False,
            "path": "",
            "language": "python",
            "source": "",
            "reason": "Processor is not registered in the Python runtime.",
        }
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "processorId": canonical_processor_id(processor_id),
            "available": False,
            "path": str(path),
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
        "processorId": canonical_processor_id(processor_id),
        "available": True,
        "path": str(rel).replace("\\", "/"),
        "language": "python",
        "source": text,
    }


def default_probe_request(processor_id: str) -> Dict[str, Any]:
    cid = canonical_processor_id(processor_id)
    base = _DEFAULT_CANARIES.get(
        cid,
        _DEFAULT_CANARIES.get(processor_id, {
            "params": {},
            "content": "{}",
            "attributes": {"mime.type": "application/json"},
        }),
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
    cid = canonical_processor_id(processor_id)
    if not flow_runtime_execution_enabled():
        duration_ms = int((time.perf_counter() - started) * 1000)
        return {
            "processorId": cid,
            "status": "skip",
            "duration_ms": duration_ms,
            "reason": "Python flow execution is disabled on this host.",
        }

    if _get_processor_class(cid) is None:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return {
            "processorId": cid,
            "status": "skip",
            "duration_ms": duration_ms,
            "reason": "Processor is not registered for Python execution.",
        }

    defaults = default_probe_request(cid)
    merged_params = {**defaults.get("params", {}), **(params or {})}
    body = content if content is not None else defaults.get("content", "{}")
    attrs = {**defaults.get("attributes", {}), **(attributes or {})}
    if isinstance(body, str):
        raw = body.encode("utf-8")
    else:
        raw = json.dumps(body).encode("utf-8")

    from src.services.flow_runtime.nexus_flow_journey import record_to_state, run_processor_step, state_to_record

    flow_state = record_to_state(FlowRecord(content=raw, attributes=dict(attrs)))
    step_out = run_processor_step(cid, merged_params, flow_state)
    duration_ms = int((time.perf_counter() - started) * 1000)

    if step_out.get("status") != "ok":
        return {
            "processorId": cid,
            "status": "fail",
            "duration_ms": duration_ms,
            "error": step_out.get("error", "step failed"),
            "params": merged_params,
        }

    terminals = []
    if step_out.get("flowState"):
        terminals = [state_to_record(step_out["flowState"]).attributes]
    preview = json.dumps(terminals[0])[:240] if terminals else "no terminal attributes"
    return {
        "processorId": cid,
        "status": "pass",
        "duration_ms": duration_ms,
        "result_preview": preview,
        "terminalCount": len(terminals),
        "terminalAttributes": terminals,
        "nodeStats": [{"nodeId": "probe", "type": cid, "relationship": step_out.get("relationship")}],
        "params": merged_params,
    }


def probe_batch(processor_ids: List[str]) -> Dict[str, Any]:
    require_flow_runtime_execution()
    capped = processor_ids[:12]
    results = [probe_processor(pid) for pid in capped]
    return {
        "total": len(results),
        "results": results,
    }


