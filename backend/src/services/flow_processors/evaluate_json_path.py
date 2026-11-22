from __future__ import annotations

import json

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


def _json_path_one(payload: object, path: str) -> str:
    """Minimal JsonPath: $.a.b or $[0].field."""
    path = path.strip()
    if not path.startswith("$"):
        return ""
    cur = payload
    parts = path[1:].strip(".").split(".") if len(path) > 1 else []
    for part in parts:
        if not part:
            continue
        if part.startswith("[") and part.endswith("]"):
            idx = int(part[1:-1])
            if isinstance(cur, list) and 0 <= idx < len(cur):
                cur = cur[idx]
            else:
                return ""
        else:
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return ""
    if cur is None:
        return ""
    if isinstance(cur, (dict, list)):
        return json.dumps(cur)
    return str(cur)


@register_processor("nexus.EvaluateJsonPath")
class EvaluateJsonPathProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nexus.EvaluateJsonPath",
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        ff = session.get()
        if ff is None:
            return
        try:
            payload = json.loads(session.read(ff))
        except json.JSONDecodeError:
            session.transfer(ff, "failure")
            return
        props = context._properties  # noqa: SLF001
        for attr, jp in props.items():
            if attr in ("Destination", "Return Type", "Path Not Found Behavior", "Null Value Representation"):
                continue
            val = _json_path_one(payload, str(jp))
            ff.put_attribute(attr, val)
        session.transfer(ff, "success")