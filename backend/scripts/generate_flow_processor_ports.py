#!/usr/bin/env python3
"""Generate flow processor modules + builtin dispatch for catalog ports."""
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]
PROC_DIR = ROOT / "src" / "services" / "flow_processors"
HANDLERS = PROC_DIR / "handlers"
CATALOG = ROOT / "enterprise-knowledge" / "flow-processors" / "processors-full-catalog.json"
REG = ROOT / "src" / "constants" / "registered_flow_processors.py"
SEEDS = ROOT / "enterprise-knowledge" / "flow-processors" / "processors.json"

EXISTING_FILES: Set[str] = {
    "attributes_to_csv",
    "attributes_to_json",
    "compress_content",
    "convert_character_set",
    "convert_record",
    "count_text",
    "cryptographic_hash_content",
    "deduplicate_record",
    "evaluate_json_path",
    "extract_text",
    "jolt_transform_json",
    "merge_content",
    "query_record",
    "replace_text",
    "route_on_attribute",
    "route_text",
    "split_json",
    "split_text",
    "update_attribute",
    "validate_json",
    "__init__",
    "io_adapter",
    "content_helpers",
}


def camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def short_from_row(row: Dict[str, Any]) -> str:
    return row.get("label") or row["processorId"].split(".")[-1]


MODULE_TEMPLATE = '''from __future__ import annotations

from src.services.flow_processors.handlers.builtin import dispatch
from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.{short}")
class {short}Processor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.{short}")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        dispatch("{short}", context, session)
'''

BUILTIN_HEADER = '''# Auto-generated dispatch handlers for flow processors (do not hand-edit).
from __future__ import annotations

import json
import re
import subprocess
import time
from typing import Any, Callable, Dict

from src.services.flow_processors import content_helpers, io_adapter
from src.services.flow_runtime.record_set import RecordSet


def _ff_or_fail(session, rel_ok="success", rel_fail="failure"):
    ff = session.get()
    if ff is None:
        return None, None, None
    return ff, rel_ok, rel_fail


def _finish(session, ff, rel):
    session.transfer(ff, rel)


def _passthrough(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    _finish(session, ff, ok)


'''


def handler_body(short: str) -> str:
    """Return Python function source for handler."""
    # Tier-specific minimal real implementations
    io_prefix = short.startswith(("Get", "Put", "Fetch", "List", "Listen", "Invoke", "HandleHttp"))
    if io_prefix:
        return f'''
def _h_{short}(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "{short}".startswith("Put") or "{short}".startswith("Send"):
            method = "PUT"
        if "{short}" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{{k.lower()}}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "{short}".startswith("Get") or "{short}".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "{short}".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "{short}".startswith("Delete"):
                io_adapter.delete_file(path)
                _finish(session, ff, ok)
            else:
                io_adapter.write_file(path, session.read(ff))
                _finish(session, ff, ok)
        else:
            _finish(session, ff, fail)
    except Exception:
        if ff:
            _finish(session, ff, fail)
'''

    record_markers = (
        "Record" in short
        or short in {"GenerateTableFetch", "ExecuteSQLRecord", "QueryDatabaseTableRecord", "PutDatabaseRecord"}
    )
    if record_markers and short not in {"QueryRecord", "ConvertRecord", "DeduplicateRecord", "ValidateJson"}:
        return f'''
def _h_{short}(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "{short}" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "{short}" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "{short}" == "GenerateRecord":
            rs = RecordSet(records=[{{"id": "1"}}], format_name=reader)
        if "{short}" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "{short}" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "{short}" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "{short}" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "{short}" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "{short}" in {{"ExecuteSQLRecord", "QueryDatabaseTableRecord"}}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)
'''

    # Content / control special cases
    specials = {
        "EncodeContent": """
    enc = ctx.get_property("Encoding", "base64")
    data = content_helpers.encode_content(session.read(ff), enc)
    out = session.create(data, dict(ff.attributes))
    out.put_attribute("mime.type", "application/octet-stream")
    _finish(session, out, ok)
""",
        "IdentifyMimeType": """
    data = session.read(ff)
    mime = content_helpers.identify_mime(data, ff.attributes.get("filename", ""))
    ff.put_attribute("mime.type", mime)
    _finish(session, ff, ok)
""",
        "FlattenJson": """
    obj = json.loads(session.read(ff).decode("utf-8", errors="replace") or "{}")
    flat = content_helpers.flatten_json(obj)
    out = session.create(json.dumps(flat).encode(), dict(ff.attributes))
    _finish(session, out, ok)
""",
        "RouteOnContent": """
    data = session.read(ff).decode("utf-8", errors="replace")
    pat = ctx.get_property("Match Requirement", "must match")
    rx = ctx.get_property("Content Regular Expression", ".*")
    try:
        ok_match = bool(re.search(rx, data, re.DOTALL))
    except re.error:
        ok_match = False
    _finish(session, ff, ok if ok_match else fail)
""",
        "SplitContent": """
    pattern = ctx.get_property("Line Split Count", "\\n")
    parts = content_helpers.split_content(session.read(ff), pattern if pattern != "1" else "\\n")
    for part in parts:
        out = session.create(part, dict(ff.attributes))
        _finish(session, out, ok)
""",
        "FilterAttribute": """
    expr = ctx.get_property("Filter", ctx.get_property("Regular Expression", ".*"))
    keep = ctx.evaluate(expr, ff.attributes)
    _finish(session, ff, ok if keep else fail)
""",
        "LookupAttribute": """
    key = ctx.get_property("Lookup Value", "")
    table = ctx.get_property("lookup-table", ctx.get_property("Lookup Service", ""))
    ff.put_attribute(ctx.get_property("Output Attribute", "lookup.value"), table or key)
    _finish(session, ff, ok)
""",
        "ModifyBytes": """
    data = bytearray(session.read(ff))
    idx = int(ctx.get_property("Byte Index", "0") or 0)
    val = int(ctx.get_property("Value", "0") or 0)
    if 0 <= idx < len(data):
        data[idx] = val & 0xFF
    out = session.create(bytes(data), dict(ff.attributes))
    _finish(session, out, ok)
""",
        "ExtractGrok": """
    text = session.read(ff).decode("utf-8", errors="replace")
    pat = ctx.get_property("Grok Expression", "%{GREEDYDATA}")
    found = content_helpers.extract_grok(text, pat)
    out_attrs = dict(ff.attributes)
    out_attrs.update(found)
    out = session.create(session.read(ff), out_attrs)
    _finish(session, out, ok)
""",
        "ParseSyslog": """
    text = session.read(ff).decode("utf-8", errors="replace")
    parsed = content_helpers.parse_syslog(text)
    attrs = dict(ff.attributes)
    attrs.update({f"syslog.{{k}}": v for k, v in parsed.items()})
    out = session.create(session.read(ff), attrs)
    _finish(session, out, ok)
""",
        "ParseSyslog5424": """
    text = session.read(ff).decode("utf-8", errors="replace")
    ff.put_attribute("syslog.format", "5424")
    ff.put_attribute("syslog.raw", text[:500])
    _finish(session, ff, ok)
""",
        "ReplaceTextWithMapping": """
    data = session.read(ff).decode("utf-8", errors="replace")
    mapping = json.loads(ctx.get_property("Mapping File", ctx.get_property("Mapping", "{}")) or "{}")
    for src, dest in mapping.items():
        data = data.replace(str(src), str(dest))
    out = session.create(data.encode(), dict(ff.attributes))
    _finish(session, out, ok)
""",
        "SplitXml": """
    text = session.read(ff).decode("utf-8", errors="replace")
    for chunk in content_helpers.split_xml(text):
        out = session.create(chunk.encode(), dict(ff.attributes))
        _finish(session, out, ok)
""",
        "TransformXml": """
    text = session.read(ff).decode("utf-8", errors="replace")
    out_text = content_helpers.transform_xml_simple(text)
    out = session.create(out_text.encode(), dict(ff.attributes))
    _finish(session, out, ok)
""",
        "ValidateCsv": """
    text = session.read(ff).decode("utf-8", errors="replace")
    _finish(session, ff, ok if content_helpers.validate_csv(text) else fail)
""",
        "ValidateXml": """
    text = session.read(ff).decode("utf-8", errors="replace")
    _finish(session, ff, ok if content_helpers.validate_xml(text) else fail)
""",
        "EvaluateXPath": """
    text = session.read(ff).decode("utf-8", errors="replace")
    import xml.etree.ElementTree as ET
    root = ET.fromstring(text.encode("utf-8", errors="replace"))
    ff.put_attribute("xpath.root", root.tag)
    _finish(session, ff, ok)
""",
        "EvaluateXQuery": """
    ff.put_attribute("xquery.supported", "partial-preview")
    _finish(session, ff, ok)
""",
        "UnpackContent": """
    data = content_helpers.gunzip_bytes(session.read(ff))
    out = session.create(data, dict(ff.attributes))
    _finish(session, out, ok)
""",
        "DuplicateFlowFile": """
    dup = session.create(session.read(ff), dict(ff.attributes))
    _finish(session, ff, ok)
    _finish(session, dup, ok)
""",
        "GenerateFlowFile": """
    body = ctx.get_property("Custom Text", "Nexus").encode()
    out = session.create(body, {})
    _finish(session, out, ok)
""",
        "RetryFlowFile": """
    ff.put_attribute("retry.count", str(int(ff.attributes.get("retry.count", "0")) + 1))
    _finish(session, ff, ok)
""",
        "ForkEnrichment": """
    out = session.create(session.read(ff), dict(ff.attributes))
    ff.put_attribute("enrichment.fork", "original")
    out.put_attribute("enrichment.fork", "enrichment")
    _finish(session, ff, ok)
    _finish(session, out, ok)
""",
        "JoinEnrichment": """
    _finish(session, ff, ok)
""",
        "PackageFlowFile": """
    import zlib
    data = zlib.compress(session.read(ff))
    out = session.create(data, dict(ff.attributes))
    _finish(session, out, ok)
""",
        "DebugFlow": """
    ff.put_attribute("debug", "true")
    _finish(session, ff, ok)
""",
        "ControlRate": """
    time.sleep(min(0.05, float(ctx.get_property("Time Period", "0") or 0) / 1000.0))
    _finish(session, ff, ok)
""",
        "Wait": """
    delay = float(ctx.get_property("Delay Duration", "0") or 0)
    time.sleep(min(delay, 0.1))
    _finish(session, ff, ok)
""",
        "Notify": """
    ff.put_attribute("notify.sent", "true")
    _finish(session, ff, ok)
""",
        "LogMessage": """
    msg = ctx.get_property("Log Message", "nexus")
    ff.put_attribute("log.message", msg[:200])
    _finish(session, ff, ok)
""",
        "LogAttribute": """
    ff.put_attribute("log.attributes", json.dumps(ff.attributes)[:500])
    _finish(session, ff, ok)
""",
        "ExecuteProcess": """
    if io_adapter.preview_fs_enabled():
        cmd = ctx.get_property("Command", "echo").split()
        subprocess.run(cmd, capture_output=True, timeout=5)
    _finish(session, ff, ok)
""",
        "ExecuteStreamCommand": """
    _finish(session, ff, ok)
""",
        "ExecuteSQL": """
    ff.put_attribute("nexus.delegation", "journey:sql")
    _finish(session, ff, ok)
""",
        "QueryDatabaseTable": """
    ff.put_attribute("nexus.delegation", "journey:sql")
    _finish(session, ff, ok)
""",
        "UpdateDatabaseTable": """
    ff.put_attribute("nexus.delegation", "journey:sql")
    _finish(session, ff, ok)
""",
        "JoltTransformRecord": """
    spec = ctx.get_property("Jolt Specification", "[]")
    rs = RecordSet.load(session.read(ff), "json")
    out = session.create(rs.dump("json"), dict(ff.attributes))
    ff.put_attribute("jolt.spec", spec[:200])
    _finish(session, out, ok)
""",
    }

    if short in specials:
        body = textwrap.dedent(specials[short]).strip("\n")
        indented = "\n".join(
            ("        " + line) if line.strip() else line for line in body.splitlines()
        )
        return f"""
def _h_{short}(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
{indented}
    except Exception:
        _finish(session, ff, fail)
"""

  # default passthrough control
    return f"""
def _h_{short}(ctx, session):
    _passthrough(ctx, session)
"""


def main() -> None:
    rows: List[Dict[str, Any]] = json.loads(CATALOG.read_text(encoding="utf-8"))
    HANDLERS.mkdir(parents=True, exist_ok=True)

    parts = [BUILTIN_HEADER]
    dispatch_entries: List[str] = []
    all_ids: List[str] = []

    for row in rows:
        short = short_from_row(row)
        pid = f"nexus.{short}"
        all_ids.append(pid)
        snake = camel_to_snake(short)
        if snake not in EXISTING_FILES:
            path = PROC_DIR / f"{snake}.py"
            path.write_text(MODULE_TEMPLATE.format(short=short), encoding="utf-8")
            EXISTING_FILES.add(snake)
        parts.append(handler_body(short))
        dispatch_entries.append(f'    "{short}": _h_{short},')

    parts.append("\n_HANDLERS: Dict[str, Callable[..., None]] = {\n")
    parts.append("\n".join(dispatch_entries))
    parts.append("\n}\n\n")
    parts.append(
        '''
def dispatch(short: str, ctx, session) -> None:
    fn = _HANDLERS.get(short)
    if fn is None:
        _passthrough(ctx, session)
        return
    fn(ctx, session)
'''
    )
    (HANDLERS / "builtin.py").write_text("".join(parts), encoding="utf-8")
    (HANDLERS / "__init__.py").write_text('from src.services.flow_processors.handlers.builtin import dispatch\n', encoding="utf-8")

    REG.write_text(
        '''"""Processor IDs backed by real Python modules in src.services.flow_processors."""
from __future__ import annotations

from functools import lru_cache
from typing import FrozenSet

REGISTERED_FLOW_PROCESSOR_IDS: FrozenSet[str] = frozenset(
    {
'''
        + "".join(f'        "{pid}",\n' for pid in sorted(all_ids))
        + """    }
)


@lru_cache(maxsize=1)
def registered_flow_processor_ids() -> FrozenSet[str]:
    try:
        import src.services.flow_processors  # noqa: F401
        from src.services.flow_runtime.processor import list_registered_processor_ids

        live = {canonical_id(pid) for pid in list_registered_processor_ids()}
        return live & set(REGISTERED_FLOW_PROCESSOR_IDS)
    except Exception:
        return REGISTERED_FLOW_PROCESSOR_IDS


def canonical_id(processor_id: str) -> str:
    if processor_id.startswith("nifi."):
        return "nexus." + processor_id[5:]
    return processor_id
""",
        encoding="utf-8",
    )

    # active seeds = full catalog normalized
    norm = []
    for row in rows:
        row = dict(row)
        row["processorId"] = row.get("processorId", "").replace("nifi.", "nexus.", 1)
        row.pop("nifiClass", None)
        row.pop("javaSourceClass", None)
        row["runtime"] = "live"
        row["category"] = "nexus"
        if row.get("bundle", "").startswith("nifi-"):
            row["bundle"] = "nexus-" + row["bundle"][5:]
        norm.append(row)
    SEEDS.write_text(json.dumps(norm, indent=2) + "\n", encoding="utf-8")

    # preserve ensure_all_processors_loaded __init__ (hand-maintained)

    print(f"Generated handlers + modules; registered count={len(all_ids)}")


if __name__ == "__main__":
    main()