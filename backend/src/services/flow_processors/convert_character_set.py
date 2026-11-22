from __future__ import annotations

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.ConvertCharacterSet")
class ConvertCharacterSetProcessor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.ConvertCharacterSet", label="ConvertCharacterSet")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        src = context.get_property("Input Character Set", "UTF-8")
        dst = context.get_property("Output Character Set", "UTF-8")
        try:
            raw = session.read(record).decode(src).encode(dst)
            record = session.write(record, raw)
            session.transfer(record, "success")
        except (LookupError, UnicodeError):
            session.transfer(record, "failure")