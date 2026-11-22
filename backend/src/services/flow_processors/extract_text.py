from __future__ import annotations

import re

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.ExtractText")
class ExtractTextProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nexus.ExtractText",
        label="ExtractText",
        relationships=["success", "failure"],
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        pattern = context.get_property("Regular Expression", "")
        group = int(context.get_property("Capture group", "0") or 0)
        text = session.read(record).decode("utf-8", errors="replace")
        try:
            m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
            if not m:
                session.transfer(record, "failure")
                return
            extracted = m.group(group) if m.lastindex and group <= m.lastindex else m.group(0)
            record.put_attribute("extract.text", extracted)
            session.transfer(record, "success")
        except re.error:
            session.transfer(record, "failure")