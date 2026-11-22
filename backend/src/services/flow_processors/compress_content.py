from __future__ import annotations

import gzip
import zlib

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.CompressContent")
class CompressContentProcessor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.CompressContent", label="CompressContent")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        mode = context.get_property("Mode", "compress").lower()
        algo = context.get_property("Compression Format", "gzip").lower()
        raw = session.read(record)
        try:
            if mode == "decompress":
                out = gzip.decompress(raw) if algo == "gzip" else zlib.decompress(raw)
            else:
                out = gzip.compress(raw) if algo == "gzip" else zlib.compress(raw)
        except Exception:
            session.transfer(record, "failure")
            return
        record = session.write(record, out)
        record.put_attribute("mime.type", "application/octet-stream")
        session.transfer(record, "success")