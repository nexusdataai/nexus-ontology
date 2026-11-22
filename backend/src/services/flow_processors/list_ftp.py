from __future__ import annotations

from src.services.flow_processors.handlers.builtin import dispatch
from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.ListFTP")
class ListFTPProcessor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.ListFTP")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        dispatch("ListFTP", context, session)
