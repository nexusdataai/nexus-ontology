from __future__ import annotations

import hashlib
import json

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.DeduplicateRecord")
class DeduplicateRecordProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nexus.DeduplicateRecord",
        label="DeduplicateRecord",
        relationships=["success", "failure"],
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        seen_key = context.get_property("Cache Entry Identifier", "nexus.dedupe.hash")
        payload = json.dumps(record.attributes, sort_keys=True).encode() + session.read(record)
        digest = hashlib.sha256(payload).hexdigest()
        if record.attributes.get(seen_key) == digest:
            session.transfer(record, "failure")
            return
        record.put_attribute(seen_key, digest)
        session.transfer(record, "success")