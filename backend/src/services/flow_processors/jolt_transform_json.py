from __future__ import annotations

import json

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


def _jolt_shift(doc: dict, spec: dict) -> dict:
    out: dict = {}
    for src, tgt in spec.items():
        if isinstance(tgt, dict) and isinstance(doc.get(src), dict):
            out.update(_jolt_shift(doc[src], tgt))
        elif isinstance(tgt, str):
            if src in doc:
                out[tgt] = doc[src]
    return out


def _apply_jolt(doc: object, chain: list) -> object:
    cur = doc
    for step in chain:
        op = step.get("operation")
        spec = step.get("spec") or {}
        if op == "shift" and isinstance(cur, dict):
            cur = _jolt_shift(cur, spec)
        elif op == "default" and isinstance(cur, dict):
            cur = {**spec, **cur}
    return cur


@register_processor("nexus.JoltTransformJSON")
class JoltTransformJSONProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nexus.JoltTransformJSON",
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        ff = session.get()
        if ff is None:
            return
        spec_text = context.get_property("Jolt Specification", "[]")
        try:
            doc = json.loads(session.read(ff))
            chain = json.loads(spec_text) if spec_text.strip() else []
            if isinstance(chain, dict):
                chain = [chain]
            result = _apply_jolt(doc, chain)
            session.write(ff, json.dumps(result).encode("utf-8"))
            session.transfer(ff, "success")
        except (json.JSONDecodeError, TypeError):
            session.transfer(ff, "failure")