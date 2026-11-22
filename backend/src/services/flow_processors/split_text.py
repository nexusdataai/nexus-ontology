from __future__ import annotations

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.SplitText")
class SplitTextProcessor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.SplitText", label="SplitText")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        delim = context.get_property("Line Split Count", "1")
        try:
            n = max(1, int(delim))
        except ValueError:
            n = 1
        text = session.read(record).decode("utf-8", errors="replace")
        lines = text.splitlines()
        chunk = "\n".join(lines[:n]).encode("utf-8")
        record.content = chunk
        session.transfer(record, "success")
        for rest in lines[n:]:
            session.transfer(session.create(rest.encode("utf-8"), dict(record.attributes)), "success")