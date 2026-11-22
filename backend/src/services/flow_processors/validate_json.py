from __future__ import annotations

import json

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.ValidateJson")
class ValidateJsonProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nexus.ValidateJson",
        label="ValidateJson",
        relationships=["valid", "invalid"],
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        try:
            json.loads(session.read(record).decode("utf-8", errors="replace"))
            session.transfer(record, "valid")
        except json.JSONDecodeError:
            session.transfer(record, "invalid")