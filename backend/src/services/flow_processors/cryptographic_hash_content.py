from __future__ import annotations

import hashlib

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.CryptographicHashContent")
class CryptographicHashContentProcessor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.CryptographicHashContent", label="CryptographicHashContent")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        algo = context.get_property("Hash Algorithm Name", "SHA-256").lower().replace("-", "")
        attr = context.get_property("Attribute Name", "hash.value")
        h = hashlib.new(algo, session.read(record)).hexdigest()
        record.put_attribute(attr, h)
        session.transfer(record, "success")