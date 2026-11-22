from __future__ import annotations

import json

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.AttributesToJSON")
class AttributesToJSONProcessor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.AttributesToJSON", label="AttributesToJSON")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        dest = context.get_property("Destination", "flowfile-attribute")
        payload = json.dumps(record.attributes, indent=2).encode("utf-8")
        if str(dest).lower() == "flowfile-content":
            record.content = payload
            record.put_attribute("mime.type", "application/json")
            session.transfer(record, "success")
        else:
            record.put_attribute("attributes.json", json.dumps(record.attributes))
            session.transfer(record, "success")