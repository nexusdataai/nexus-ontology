from __future__ import annotations

import re

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.ReplaceText")
class ReplaceTextProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nexus.ReplaceText",
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        ff = session.get()
        if ff is None:
            return
        search = context.get_property("Search Value", "")
        replacement = context.get_property("Replacement Value", "")
        strategy = context.get_property("Replacement Strategy", "Regex Replace")
        text = session.read(ff).decode("utf-8", errors="replace")
        if strategy == "Regex Replace" and search:
            try:
                text = re.sub(search, replacement, text)
            except re.error:
                text = text.replace(search, replacement)
        else:
            text = text.replace(search, replacement)
        session.write(ff, text.encode("utf-8"))
        session.transfer(ff, "success")