from __future__ import annotations

import json

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.SplitJson")
class SplitJsonProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nexus.SplitJson",
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        ff = session.get()
        if ff is None:
            return
        array_path = context.get_property("JsonPath Expression", "$")
        try:
            doc = json.loads(session.read(ff))
            items = doc
            if array_path == "$" and isinstance(doc, list):
                items = doc
            elif isinstance(doc, dict) and array_path.startswith("$."):
                key = array_path[2:]
                items = doc.get(key, [])
            if not isinstance(items, list):
                session.transfer(ff, "failure")
                return
            session.remove(ff)
            for idx, entry in enumerate(items):
                child = session.create(
                    content=json.dumps(entry).encode("utf-8"),
                    attributes=dict(ff.attributes),
                )
                child.put_attribute("fragment.index", str(idx))
                child.put_attribute("fragment.count", str(len(items)))
                session.transfer(child, "success")
        except json.JSONDecodeError:
            session.transfer(ff, "failure")