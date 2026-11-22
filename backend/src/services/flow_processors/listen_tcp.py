from __future__ import annotations

from src.services.flow_processors.handlers.builtin import dispatch
from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.ListenTCP")
class ListenTCPProcessor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.ListenTCP")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        dispatch("ListenTCP", context, session)
