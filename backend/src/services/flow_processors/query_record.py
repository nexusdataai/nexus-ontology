from __future__ import annotations

import json

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


def _query_records(rows: list[dict], sql: str) -> list[dict]:
    """Tiny SQL subset: SELECT * WHERE field = 'value' (single predicate)."""
    sql = sql.strip()
    if not sql.upper().startswith("SELECT"):
        return rows
    where_idx = sql.upper().find(" WHERE ")
    if where_idx < 0:
        return rows
    clause = sql[where_idx + 7 :].strip()
    if "=" not in clause:
        return rows
    field, _, val = clause.partition("=")
    field = field.strip()
    val = val.strip().strip("'\"")
    return [r for r in rows if str(r.get(field)) == val]


@register_processor("nexus.QueryRecord")
class QueryRecordProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nexus.QueryRecord",
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        ff = session.get()
        if ff is None:
            return
        sql = context.get_property("SQL", "SELECT *")
        try:
            data = json.loads(session.read(ff))
            rows = data if isinstance(data, list) else [data]
            if not all(isinstance(r, dict) for r in rows):
                session.transfer(ff, "failure")
                return
            result = _query_records(rows, sql)
            session.write(ff, json.dumps(result).encode("utf-8"))
            ff.put_attribute("record.count", str(len(result)))
            session.transfer(ff, "success")
        except json.JSONDecodeError:
            session.transfer(ff, "failure")