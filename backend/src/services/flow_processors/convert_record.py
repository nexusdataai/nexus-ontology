from __future__ import annotations

import csv
import io
import json

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nifi.ConvertRecord")
class ConvertRecordProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nifi.ConvertRecord",
        nifi_class="org.apache.nifi.processors.standard.ConvertRecord",
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        ff = session.get()
        if ff is None:
            return
        reader = context.get_property("Record Reader", "json")
        writer = context.get_property("Record Writer", "json")
        raw = session.read(ff)
        try:
            if reader.lower() == "csv":
                text = raw.decode("utf-8", errors="replace")
                rows = list(csv.DictReader(io.StringIO(text)))
            else:
                rows = json.loads(raw)
                if isinstance(rows, dict):
                    rows = [rows]
            if writer.lower() == "csv" and rows:
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
                out = buf.getvalue().encode("utf-8")
                ff.put_attribute("mime.type", "text/csv")
            else:
                out = json.dumps(rows if len(rows) != 1 else rows[0]).encode("utf-8")
                ff.put_attribute("mime.type", "application/json")
            session.write(ff, out)
            session.transfer(ff, "success")
        except (json.JSONDecodeError, csv.Error, KeyError):
            session.transfer(ff, "failure")