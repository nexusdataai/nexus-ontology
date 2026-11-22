from __future__ import annotations

import json

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.MergeContent")
class MergeContentProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nexus.MergeContent",
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        merge_format = context.get_property("Merge Format", "Binary Concatenation")
        ff = session.get()
        if ff is None:
            return
        parts = [session.read(ff)]
        while True:
            nxt = session.get()
            if nxt is None:
                break
            parts.append(session.read(nxt))
            session.remove(nxt)
        if merge_format == "JSON Array":
            merged = b"[" + b",".join(parts) + b"]"
        else:
            delim = context.get_property("Delimiter Strategy", "\n").encode("utf-8")
            merged = delim.join(parts)
        out = session.create(content=merged, attributes=dict(ff.attributes))
        out.put_attribute("fragment.count", str(len(parts)))
        session.transfer(out, "success")
        session.remove(ff)