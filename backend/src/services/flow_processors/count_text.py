from __future__ import annotations

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.CountText")
class CountTextProcessor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.CountText", label="CountText")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        text = session.read(record).decode("utf-8", errors="replace")
        attr = context.get_property("Attribute Name", "text.line.count")
        record.put_attribute(attr, str(len(text.splitlines())))
        session.transfer(record, "success")