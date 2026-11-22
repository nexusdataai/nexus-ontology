from __future__ import annotations

import csv
import io
import re

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.AttributesToCSV")
class AttributesToCSVProcessor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.AttributesToCSV", label="AttributesToCSV")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        record = session.get()
        if record is None:
            return
        attr_list = context.get_property("Attribute List", "")
        regex = context.get_property("Attributes Regular Expression", "")
        keys = list(record.attributes.keys())
        if attr_list.strip():
            keys = [k.strip() for k in attr_list.split(",") if k.strip()]
        elif regex.strip():
            try:
                pat = re.compile(regex)
                keys = [k for k in keys if pat.search(k)]
            except re.error:
                pass
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(keys)
        writer.writerow([record.attributes.get(k, "") for k in keys])
        body = buf.getvalue().encode("utf-8")
        out = session.create(body, dict(record.attributes))
        out.put_attribute("mime.type", "text/csv")
        session.transfer(out, "success")