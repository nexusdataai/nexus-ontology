from __future__ import annotations

import re

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.RouteText")
class RouteTextProcessor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.RouteText", label="RouteText")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        text = session.read(record).decode("utf-8", errors="replace")
        matched = None
        for key, pattern in context._properties.items():  # noqa: SLF001
            if not key.startswith("route."):
                continue
            rel = key.split(".", 1)[-1]
            try:
                if re.search(str(pattern), text):
                    matched = rel
                    break
            except re.error:
                continue
        session.transfer(record, matched or "unmatched")