# Auto-generated dispatch handlers for flow processors (do not hand-edit).
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



def _h_AttributesToCSV(ctx, session):
    _passthrough(ctx, session)

def _h_AttributesToJSON(ctx, session):
    _passthrough(ctx, session)

def _h_CalculateRecordStats(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "CalculateRecordStats" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "CalculateRecordStats" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "CalculateRecordStats" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "CalculateRecordStats" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "CalculateRecordStats" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "CalculateRecordStats" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "CalculateRecordStats" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "CalculateRecordStats" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "CalculateRecordStats" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_CompressContent(ctx, session):
    _passthrough(ctx, session)

def _h_ControlRate(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        time.sleep(min(0.05, float(ctx.get_property("Time Period", "0") or 0) / 1000.0))
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ConvertCharacterSet(ctx, session):
    _passthrough(ctx, session)

def _h_ConvertRecord(ctx, session):
    _passthrough(ctx, session)

def _h_CountText(ctx, session):
    _passthrough(ctx, session)

def _h_CryptographicHashContent(ctx, session):
    _passthrough(ctx, session)

def _h_DebugFlow(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        ff.put_attribute("debug", "true")
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_DeleteFile(ctx, session):
    _passthrough(ctx, session)

def _h_DeleteSFTP(ctx, session):
    _passthrough(ctx, session)

def _h_DetectDuplicate(ctx, session):
    _passthrough(ctx, session)

def _h_DeduplicateRecord(ctx, session):
    _passthrough(ctx, session)

def _h_DistributeLoad(ctx, session):
    _passthrough(ctx, session)

def _h_DuplicateFlowFile(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        dup = session.create(session.read(ff), dict(ff.attributes))
        _finish(session, ff, ok)
        _finish(session, dup, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_EncodeContent(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        enc = ctx.get_property("Encoding", "base64")
        data = content_helpers.encode_content(session.read(ff), enc)
        out = session.create(data, dict(ff.attributes))
        out.put_attribute("mime.type", "application/octet-stream")
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_EnforceOrder(ctx, session):
    _passthrough(ctx, session)

def _h_EvaluateJsonPath(ctx, session):
    _passthrough(ctx, session)

def _h_EvaluateXPath(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        text = session.read(ff).decode("utf-8", errors="replace")
        import xml.etree.ElementTree as ET
        root = ET.fromstring(text.encode("utf-8", errors="replace"))
        ff.put_attribute("xpath.root", root.tag)
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_EvaluateXQuery(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        ff.put_attribute("xquery.supported", "partial-preview")
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ExecuteProcess(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        if io_adapter.preview_fs_enabled():
            cmd = ctx.get_property("Command", "echo").split()
            subprocess.run(cmd, capture_output=True, timeout=5)
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ExecuteSQL(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        ff.put_attribute("nexus.delegation", "journey:sql")
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ExecuteSQLRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "ExecuteSQLRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ExecuteSQLRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "ExecuteSQLRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "ExecuteSQLRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "ExecuteSQLRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "ExecuteSQLRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ExecuteSQLRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "ExecuteSQLRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ExecuteSQLRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ExecuteStreamCommand(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ExtractGrok(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        text = session.read(ff).decode("utf-8", errors="replace")
        pat = ctx.get_property("Grok Expression", "%{GREEDYDATA}")
        found = content_helpers.extract_grok(text, pat)
        out_attrs = dict(ff.attributes)
        out_attrs.update(found)
        out = session.create(session.read(ff), out_attrs)
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ExtractRecordSchema(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "ExtractRecordSchema" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ExtractRecordSchema" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "ExtractRecordSchema" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "ExtractRecordSchema" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "ExtractRecordSchema" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "ExtractRecordSchema" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ExtractRecordSchema" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "ExtractRecordSchema" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ExtractRecordSchema" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ExtractText(ctx, session):
    _passthrough(ctx, session)

def _h_FetchDistributedMapCache(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "FetchDistributedMapCache".startswith("Put") or "FetchDistributedMapCache".startswith("Send"):
            method = "PUT"
        if "FetchDistributedMapCache" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "FetchDistributedMapCache".startswith("Get") or "FetchDistributedMapCache".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "FetchDistributedMapCache".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "FetchDistributedMapCache".startswith("Delete"):
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

def _h_FetchFile(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "FetchFile".startswith("Put") or "FetchFile".startswith("Send"):
            method = "PUT"
        if "FetchFile" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "FetchFile".startswith("Get") or "FetchFile".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "FetchFile".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "FetchFile".startswith("Delete"):
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

def _h_FetchFTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "FetchFTP".startswith("Put") or "FetchFTP".startswith("Send"):
            method = "PUT"
        if "FetchFTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "FetchFTP".startswith("Get") or "FetchFTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "FetchFTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "FetchFTP".startswith("Delete"):
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

def _h_FetchSFTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "FetchSFTP".startswith("Put") or "FetchSFTP".startswith("Send"):
            method = "PUT"
        if "FetchSFTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "FetchSFTP".startswith("Get") or "FetchSFTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "FetchSFTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "FetchSFTP".startswith("Delete"):
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

def _h_FilterAttribute(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        expr = ctx.get_property("Filter", ctx.get_property("Regular Expression", ".*"))
        keep = ctx.evaluate(expr, ff.attributes)
        _finish(session, ff, ok if keep else fail)
    except Exception:
        _finish(session, ff, fail)

def _h_FlattenJson(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        obj = json.loads(session.read(ff).decode("utf-8", errors="replace") or "{}")
        flat = content_helpers.flatten_json(obj)
        out = session.create(json.dumps(flat).encode(), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ForkRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "ForkRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ForkRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "ForkRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "ForkRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "ForkRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "ForkRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ForkRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "ForkRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ForkRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ForkEnrichment(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        out = session.create(session.read(ff), dict(ff.attributes))
        ff.put_attribute("enrichment.fork", "original")
        out.put_attribute("enrichment.fork", "enrichment")
        _finish(session, ff, ok)
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_GenerateRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "GenerateRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "GenerateRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "GenerateRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "GenerateRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "GenerateRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "GenerateRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "GenerateRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "GenerateRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "GenerateRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_GenerateFlowFile(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        body = ctx.get_property("Custom Text", "Nexus").encode()
        out = session.create(body, {})
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_GenerateTableFetch(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "GenerateTableFetch" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "GenerateTableFetch" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "GenerateTableFetch" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "GenerateTableFetch" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "GenerateTableFetch" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "GenerateTableFetch" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "GenerateTableFetch" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "GenerateTableFetch" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "GenerateTableFetch" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_GetFile(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "GetFile".startswith("Put") or "GetFile".startswith("Send"):
            method = "PUT"
        if "GetFile" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "GetFile".startswith("Get") or "GetFile".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "GetFile".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "GetFile".startswith("Delete"):
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

def _h_GetFileResource(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "GetFileResource".startswith("Put") or "GetFileResource".startswith("Send"):
            method = "PUT"
        if "GetFileResource" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "GetFileResource".startswith("Get") or "GetFileResource".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "GetFileResource".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "GetFileResource".startswith("Delete"):
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

def _h_GetFTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "GetFTP".startswith("Put") or "GetFTP".startswith("Send"):
            method = "PUT"
        if "GetFTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "GetFTP".startswith("Get") or "GetFTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "GetFTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "GetFTP".startswith("Delete"):
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

def _h_GetSFTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "GetSFTP".startswith("Put") or "GetSFTP".startswith("Send"):
            method = "PUT"
        if "GetSFTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "GetSFTP".startswith("Get") or "GetSFTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "GetSFTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "GetSFTP".startswith("Delete"):
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

def _h_HandleHttpRequest(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "HandleHttpRequest".startswith("Put") or "HandleHttpRequest".startswith("Send"):
            method = "PUT"
        if "HandleHttpRequest" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "HandleHttpRequest".startswith("Get") or "HandleHttpRequest".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "HandleHttpRequest".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "HandleHttpRequest".startswith("Delete"):
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

def _h_HandleHttpResponse(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "HandleHttpResponse".startswith("Put") or "HandleHttpResponse".startswith("Send"):
            method = "PUT"
        if "HandleHttpResponse" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "HandleHttpResponse".startswith("Get") or "HandleHttpResponse".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "HandleHttpResponse".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "HandleHttpResponse".startswith("Delete"):
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

def _h_IdentifyMimeType(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        data = session.read(ff)
        mime = content_helpers.identify_mime(data, ff.attributes.get("filename", ""))
        ff.put_attribute("mime.type", mime)
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_InvokeHTTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "InvokeHTTP".startswith("Put") or "InvokeHTTP".startswith("Send"):
            method = "PUT"
        if "InvokeHTTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "InvokeHTTP".startswith("Get") or "InvokeHTTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "InvokeHTTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "InvokeHTTP".startswith("Delete"):
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

def _h_JoinEnrichment(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ListDatabaseTables(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "ListDatabaseTables".startswith("Put") or "ListDatabaseTables".startswith("Send"):
            method = "PUT"
        if "ListDatabaseTables" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "ListDatabaseTables".startswith("Get") or "ListDatabaseTables".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListDatabaseTables".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListDatabaseTables".startswith("Delete"):
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

def _h_ListenFTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "ListenFTP".startswith("Put") or "ListenFTP".startswith("Send"):
            method = "PUT"
        if "ListenFTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "ListenFTP".startswith("Get") or "ListenFTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenFTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenFTP".startswith("Delete"):
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

def _h_ListenHTTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "ListenHTTP".startswith("Put") or "ListenHTTP".startswith("Send"):
            method = "PUT"
        if "ListenHTTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "ListenHTTP".startswith("Get") or "ListenHTTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenHTTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenHTTP".startswith("Delete"):
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

def _h_ListenSyslog(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "ListenSyslog".startswith("Put") or "ListenSyslog".startswith("Send"):
            method = "PUT"
        if "ListenSyslog" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "ListenSyslog".startswith("Get") or "ListenSyslog".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenSyslog".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenSyslog".startswith("Delete"):
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

def _h_ListenTCP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "ListenTCP".startswith("Put") or "ListenTCP".startswith("Send"):
            method = "PUT"
        if "ListenTCP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "ListenTCP".startswith("Get") or "ListenTCP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenTCP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenTCP".startswith("Delete"):
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

def _h_ListenUDP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "ListenUDP".startswith("Put") or "ListenUDP".startswith("Send"):
            method = "PUT"
        if "ListenUDP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "ListenUDP".startswith("Get") or "ListenUDP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenUDP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenUDP".startswith("Delete"):
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

def _h_ListenUDPRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "ListenUDPRecord".startswith("Put") or "ListenUDPRecord".startswith("Send"):
            method = "PUT"
        if "ListenUDPRecord" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "ListenUDPRecord".startswith("Get") or "ListenUDPRecord".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenUDPRecord".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListenUDPRecord".startswith("Delete"):
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

def _h_ListFile(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "ListFile".startswith("Put") or "ListFile".startswith("Send"):
            method = "PUT"
        if "ListFile" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "ListFile".startswith("Get") or "ListFile".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListFile".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListFile".startswith("Delete"):
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

def _h_ListFTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "ListFTP".startswith("Put") or "ListFTP".startswith("Send"):
            method = "PUT"
        if "ListFTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "ListFTP".startswith("Get") or "ListFTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListFTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListFTP".startswith("Delete"):
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

def _h_ListSFTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "ListSFTP".startswith("Put") or "ListSFTP".startswith("Send"):
            method = "PUT"
        if "ListSFTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "ListSFTP".startswith("Get") or "ListSFTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListSFTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "ListSFTP".startswith("Delete"):
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

def _h_LogAttribute(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        ff.put_attribute("log.attributes", json.dumps(ff.attributes)[:500])
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_LogMessage(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        msg = ctx.get_property("Log Message", "nexus")
        ff.put_attribute("log.message", msg[:200])
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_LookupAttribute(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        key = ctx.get_property("Lookup Value", "")
        table = ctx.get_property("lookup-table", ctx.get_property("Lookup Service", ""))
        ff.put_attribute(ctx.get_property("Output Attribute", "lookup.value"), table or key)
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_LookupRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "LookupRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "LookupRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "LookupRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "LookupRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "LookupRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "LookupRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "LookupRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "LookupRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "LookupRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_MergeContent(ctx, session):
    _passthrough(ctx, session)

def _h_MergeRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "MergeRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "MergeRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "MergeRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "MergeRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "MergeRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "MergeRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "MergeRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "MergeRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "MergeRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ModifyBytes(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        data = bytearray(session.read(ff))
        idx = int(ctx.get_property("Byte Index", "0") or 0)
        val = int(ctx.get_property("Value", "0") or 0)
        if 0 <= idx < len(data):
            data[idx] = val & 0xFF
        out = session.create(bytes(data), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_MonitorActivity(ctx, session):
    _passthrough(ctx, session)

def _h_Notify(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        ff.put_attribute("notify.sent", "true")
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_PackageFlowFile(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        import zlib
        data = zlib.compress(session.read(ff))
        out = session.create(data, dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ParseSyslog(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        text = session.read(ff).decode("utf-8", errors="replace")
        parsed = content_helpers.parse_syslog(text)
        attrs = dict(ff.attributes)
        attrs.update({f"syslog.{{k}}": v for k, v in parsed.items()})
        out = session.create(session.read(ff), attrs)
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ParseSyslog5424(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        text = session.read(ff).decode("utf-8", errors="replace")
        ff.put_attribute("syslog.format", "5424")
        ff.put_attribute("syslog.raw", text[:500])
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_PartitionRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "PartitionRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "PartitionRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "PartitionRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "PartitionRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "PartitionRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "PartitionRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "PartitionRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "PartitionRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "PartitionRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_PutDatabaseRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutDatabaseRecord".startswith("Put") or "PutDatabaseRecord".startswith("Send"):
            method = "PUT"
        if "PutDatabaseRecord" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutDatabaseRecord".startswith("Get") or "PutDatabaseRecord".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutDatabaseRecord".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutDatabaseRecord".startswith("Delete"):
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

def _h_PutDistributedMapCache(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutDistributedMapCache".startswith("Put") or "PutDistributedMapCache".startswith("Send"):
            method = "PUT"
        if "PutDistributedMapCache" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutDistributedMapCache".startswith("Get") or "PutDistributedMapCache".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutDistributedMapCache".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutDistributedMapCache".startswith("Delete"):
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

def _h_PutEmail(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutEmail".startswith("Put") or "PutEmail".startswith("Send"):
            method = "PUT"
        if "PutEmail" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutEmail".startswith("Get") or "PutEmail".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutEmail".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutEmail".startswith("Delete"):
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

def _h_PutFile(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutFile".startswith("Put") or "PutFile".startswith("Send"):
            method = "PUT"
        if "PutFile" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutFile".startswith("Get") or "PutFile".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutFile".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutFile".startswith("Delete"):
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

def _h_PutFTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutFTP".startswith("Put") or "PutFTP".startswith("Send"):
            method = "PUT"
        if "PutFTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutFTP".startswith("Get") or "PutFTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutFTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutFTP".startswith("Delete"):
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

def _h_PutRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutRecord".startswith("Put") or "PutRecord".startswith("Send"):
            method = "PUT"
        if "PutRecord" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutRecord".startswith("Get") or "PutRecord".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutRecord".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutRecord".startswith("Delete"):
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

def _h_PutSFTP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutSFTP".startswith("Put") or "PutSFTP".startswith("Send"):
            method = "PUT"
        if "PutSFTP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutSFTP".startswith("Get") or "PutSFTP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutSFTP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutSFTP".startswith("Delete"):
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

def _h_PutSQL(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutSQL".startswith("Put") or "PutSQL".startswith("Send"):
            method = "PUT"
        if "PutSQL" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutSQL".startswith("Get") or "PutSQL".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutSQL".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutSQL".startswith("Delete"):
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

def _h_PutSyslog(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutSyslog".startswith("Put") or "PutSyslog".startswith("Send"):
            method = "PUT"
        if "PutSyslog" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutSyslog".startswith("Get") or "PutSyslog".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutSyslog".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutSyslog".startswith("Delete"):
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

def _h_PutTCP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutTCP".startswith("Put") or "PutTCP".startswith("Send"):
            method = "PUT"
        if "PutTCP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutTCP".startswith("Get") or "PutTCP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutTCP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutTCP".startswith("Delete"):
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

def _h_PutUDP(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    try:
        if ff is None:
            return
        url = ctx.resolve(ctx.get_property("URL", ""), ff.attributes)
        path = ctx.resolve(ctx.get_property("File", ctx.get_property("Filename", "")), ff.attributes)
        method = "GET"
        if "PutUDP".startswith("Put") or "PutUDP".startswith("Send"):
            method = "PUT"
        if "PutUDP" == "InvokeHTTP":
            method = ctx.get_property("HTTP Method", "GET")
        if url:
            body = session.read(ff) if method not in ("GET", "HEAD") else b""
            data, hdrs, status = io_adapter.http_request(method, url, body=body)
            out = session.create(data, dict(ff.attributes))
            out.put_attribute("http.status.code", str(status))
            for k, v in list(hdrs.items())[:20]:
                out.put_attribute(f"http.headers.{k.lower()}", str(v))
            _finish(session, out, ok if status < 400 else fail)
        elif path:
            if "PutUDP".startswith("Get") or "PutUDP".startswith("Fetch"):
                data = io_adapter.read_file(path)
                out = session.create(data, dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutUDP".startswith("List"):
                names = io_adapter.list_directory(path)
                out = session.create(json.dumps(names).encode(), dict(ff.attributes))
                _finish(session, out, ok)
            elif "PutUDP".startswith("Delete"):
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

def _h_QueryDatabaseTable(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        ff.put_attribute("nexus.delegation", "journey:sql")
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_QueryDatabaseTableRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "QueryDatabaseTableRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "QueryDatabaseTableRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "QueryDatabaseTableRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "QueryDatabaseTableRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "QueryDatabaseTableRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "QueryDatabaseTableRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "QueryDatabaseTableRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "QueryDatabaseTableRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "QueryDatabaseTableRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_QueryRecord(ctx, session):
    _passthrough(ctx, session)

def _h_RemoveRecordField(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "RemoveRecordField" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "RemoveRecordField" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "RemoveRecordField" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "RemoveRecordField" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "RemoveRecordField" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "RemoveRecordField" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "RemoveRecordField" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "RemoveRecordField" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "RemoveRecordField" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_RenameRecordField(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "RenameRecordField" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "RenameRecordField" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "RenameRecordField" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "RenameRecordField" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "RenameRecordField" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "RenameRecordField" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "RenameRecordField" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "RenameRecordField" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "RenameRecordField" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ReplaceText(ctx, session):
    _passthrough(ctx, session)

def _h_ReplaceTextWithMapping(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        data = session.read(ff).decode("utf-8", errors="replace")
        mapping = json.loads(ctx.get_property("Mapping File", ctx.get_property("Mapping", "{}")) or "{}")
        for src, dest in mapping.items():
            data = data.replace(str(src), str(dest))
        out = session.create(data.encode(), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_RetryFlowFile(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        ff.put_attribute("retry.count", str(int(ff.attributes.get("retry.count", "0")) + 1))
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_RouteOnAttribute(ctx, session):
    _passthrough(ctx, session)

def _h_RouteOnContent(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        data = session.read(ff).decode("utf-8", errors="replace")
        pat = ctx.get_property("Match Requirement", "must match")
        rx = ctx.get_property("Content Regular Expression", ".*")
        try:
            ok_match = bool(re.search(rx, data, re.DOTALL))
        except re.error:
            ok_match = False
        _finish(session, ff, ok if ok_match else fail)
    except Exception:
        _finish(session, ff, fail)

def _h_RouteText(ctx, session):
    _passthrough(ctx, session)

def _h_SampleRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "SampleRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "SampleRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "SampleRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "SampleRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "SampleRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "SampleRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "SampleRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "SampleRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "SampleRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ScanAttribute(ctx, session):
    _passthrough(ctx, session)

def _h_ScanContent(ctx, session):
    _passthrough(ctx, session)

def _h_SegmentContent(ctx, session):
    _passthrough(ctx, session)

def _h_SplitContent(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        pattern = ctx.get_property("Line Split Count", "\n")
        parts = content_helpers.split_content(session.read(ff), pattern if pattern != "1" else "\n")
        for part in parts:
            out = session.create(part, dict(ff.attributes))
            _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_SplitJson(ctx, session):
    _passthrough(ctx, session)

def _h_SplitRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "SplitRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "SplitRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "SplitRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "SplitRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "SplitRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "SplitRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "SplitRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "SplitRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "SplitRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_SplitText(ctx, session):
    _passthrough(ctx, session)

def _h_SplitXml(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        text = session.read(ff).decode("utf-8", errors="replace")
        for chunk in content_helpers.split_xml(text):
            out = session.create(chunk.encode(), dict(ff.attributes))
            _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_TailFile(ctx, session):
    _passthrough(ctx, session)

def _h_TransformXml(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        text = session.read(ff).decode("utf-8", errors="replace")
        out_text = content_helpers.transform_xml_simple(text)
        out = session.create(out_text.encode(), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_UnpackContent(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        data = content_helpers.gunzip_bytes(session.read(ff))
        out = session.create(data, dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_UpdateCounter(ctx, session):
    _passthrough(ctx, session)

def _h_UpdateDatabaseTable(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        ff.put_attribute("nexus.delegation", "journey:sql")
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_UpdateGauge(ctx, session):
    _passthrough(ctx, session)

def _h_UpdateRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "UpdateRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "UpdateRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "UpdateRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "UpdateRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "UpdateRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "UpdateRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "UpdateRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "UpdateRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "UpdateRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ValidateCsv(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        text = session.read(ff).decode("utf-8", errors="replace")
        _finish(session, ff, ok if content_helpers.validate_csv(text) else fail)
    except Exception:
        _finish(session, ff, fail)

def _h_ValidateJson(ctx, session):
    _passthrough(ctx, session)

def _h_ValidateRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "ValidateRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ValidateRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "ValidateRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "ValidateRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "ValidateRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "ValidateRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ValidateRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "ValidateRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "ValidateRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_ValidateXml(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        text = session.read(ff).decode("utf-8", errors="replace")
        _finish(session, ff, ok if content_helpers.validate_xml(text) else fail)
    except Exception:
        _finish(session, ff, fail)

def _h_Wait(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    try:
        delay = float(ctx.get_property("Delay Duration", "0") or 0)
        time.sleep(min(delay, 0.1))
        _finish(session, ff, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_JoltTransformJSON(ctx, session):
    _passthrough(ctx, session)

def _h_JoltTransformRecord(ctx, session):
    ff, ok, fail = _ff_or_fail(session)
    if ff is None:
        return
    reader = ctx.get_property("Record Reader", ctx.get_property("record-reader", "json"))
    writer = ctx.get_property("Record Writer", ctx.get_property("record-writer", "json"))
    try:
        rs = RecordSet.load(session.read(ff), reader)
        if "JoltTransformRecord" == "ForkRecord":
            for branch in rs.fork(int(ctx.get_property("Number of Splits", "2") or 2)):
                out = session.create(branch.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "JoltTransformRecord" == "MergeRecord":
            _finish(session, ff, ok)
            return
        if "JoltTransformRecord" == "GenerateRecord":
            rs = RecordSet(records=[{"id": "1"}], format_name=reader)
        if "JoltTransformRecord" == "UpdateRecord":
            field = ctx.get_property("Record Field", "/value")
            val = ctx.get_property("Replacement Value", "")
            for rec in rs.records:
                rec[field.lstrip("/")] = ctx.resolve(val, ff.attributes)
        if "JoltTransformRecord" == "ValidateRecord":
            rel = ok if rs.records else fail
            out = session.create(rs.dump(writer), dict(ff.attributes))
            _finish(session, out, rel)
            return
        if "JoltTransformRecord" == "PartitionRecord":
            key = ctx.get_property("Partition By Field", "id")
            for _, part in rs.partition(key).items():
                out = session.create(part.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "JoltTransformRecord" == "SampleRecord":
            rs = rs.sample(float(ctx.get_property("Sampling Ratio", "1.0") or 1.0))
        if "JoltTransformRecord" == "SplitRecord":
            size = max(1, int(ctx.get_property("Records Per Split", "1") or 1))
            for i in range(0, len(rs.records), size):
                chunk = RecordSet(records=rs.records[i : i + size], format_name=reader)
                out = session.create(chunk.dump(writer), dict(ff.attributes))
                _finish(session, out, ok)
            return
        if "JoltTransformRecord" in {"ExecuteSQLRecord", "QueryDatabaseTableRecord"}:
            ff.put_attribute("nexus.delegation", "journey:nexus_flow/sql")
            _finish(session, ff, ok)
            return
        out = session.create(rs.dump(writer), dict(ff.attributes))
        _finish(session, out, ok)
    except Exception:
        _finish(session, ff, fail)

def _h_UpdateAttribute(ctx, session):
    _passthrough(ctx, session)

_HANDLERS: Dict[str, Callable[..., None]] = {
    "AttributesToCSV": _h_AttributesToCSV,
    "AttributesToJSON": _h_AttributesToJSON,
    "CalculateRecordStats": _h_CalculateRecordStats,
    "CompressContent": _h_CompressContent,
    "ControlRate": _h_ControlRate,
    "ConvertCharacterSet": _h_ConvertCharacterSet,
    "ConvertRecord": _h_ConvertRecord,
    "CountText": _h_CountText,
    "CryptographicHashContent": _h_CryptographicHashContent,
    "DebugFlow": _h_DebugFlow,
    "DeleteFile": _h_DeleteFile,
    "DeleteSFTP": _h_DeleteSFTP,
    "DetectDuplicate": _h_DetectDuplicate,
    "DeduplicateRecord": _h_DeduplicateRecord,
    "DistributeLoad": _h_DistributeLoad,
    "DuplicateFlowFile": _h_DuplicateFlowFile,
    "EncodeContent": _h_EncodeContent,
    "EnforceOrder": _h_EnforceOrder,
    "EvaluateJsonPath": _h_EvaluateJsonPath,
    "EvaluateXPath": _h_EvaluateXPath,
    "EvaluateXQuery": _h_EvaluateXQuery,
    "ExecuteProcess": _h_ExecuteProcess,
    "ExecuteSQL": _h_ExecuteSQL,
    "ExecuteSQLRecord": _h_ExecuteSQLRecord,
    "ExecuteStreamCommand": _h_ExecuteStreamCommand,
    "ExtractGrok": _h_ExtractGrok,
    "ExtractRecordSchema": _h_ExtractRecordSchema,
    "ExtractText": _h_ExtractText,
    "FetchDistributedMapCache": _h_FetchDistributedMapCache,
    "FetchFile": _h_FetchFile,
    "FetchFTP": _h_FetchFTP,
    "FetchSFTP": _h_FetchSFTP,
    "FilterAttribute": _h_FilterAttribute,
    "FlattenJson": _h_FlattenJson,
    "ForkRecord": _h_ForkRecord,
    "ForkEnrichment": _h_ForkEnrichment,
    "GenerateRecord": _h_GenerateRecord,
    "GenerateFlowFile": _h_GenerateFlowFile,
    "GenerateTableFetch": _h_GenerateTableFetch,
    "GetFile": _h_GetFile,
    "GetFileResource": _h_GetFileResource,
    "GetFTP": _h_GetFTP,
    "GetSFTP": _h_GetSFTP,
    "HandleHttpRequest": _h_HandleHttpRequest,
    "HandleHttpResponse": _h_HandleHttpResponse,
    "IdentifyMimeType": _h_IdentifyMimeType,
    "InvokeHTTP": _h_InvokeHTTP,
    "JoinEnrichment": _h_JoinEnrichment,
    "ListDatabaseTables": _h_ListDatabaseTables,
    "ListenFTP": _h_ListenFTP,
    "ListenHTTP": _h_ListenHTTP,
    "ListenSyslog": _h_ListenSyslog,
    "ListenTCP": _h_ListenTCP,
    "ListenUDP": _h_ListenUDP,
    "ListenUDPRecord": _h_ListenUDPRecord,
    "ListFile": _h_ListFile,
    "ListFTP": _h_ListFTP,
    "ListSFTP": _h_ListSFTP,
    "LogAttribute": _h_LogAttribute,
    "LogMessage": _h_LogMessage,
    "LookupAttribute": _h_LookupAttribute,
    "LookupRecord": _h_LookupRecord,
    "MergeContent": _h_MergeContent,
    "MergeRecord": _h_MergeRecord,
    "ModifyBytes": _h_ModifyBytes,
    "MonitorActivity": _h_MonitorActivity,
    "Notify": _h_Notify,
    "PackageFlowFile": _h_PackageFlowFile,
    "ParseSyslog": _h_ParseSyslog,
    "ParseSyslog5424": _h_ParseSyslog5424,
    "PartitionRecord": _h_PartitionRecord,
    "PutDatabaseRecord": _h_PutDatabaseRecord,
    "PutDistributedMapCache": _h_PutDistributedMapCache,
    "PutEmail": _h_PutEmail,
    "PutFile": _h_PutFile,
    "PutFTP": _h_PutFTP,
    "PutRecord": _h_PutRecord,
    "PutSFTP": _h_PutSFTP,
    "PutSQL": _h_PutSQL,
    "PutSyslog": _h_PutSyslog,
    "PutTCP": _h_PutTCP,
    "PutUDP": _h_PutUDP,
    "QueryDatabaseTable": _h_QueryDatabaseTable,
    "QueryDatabaseTableRecord": _h_QueryDatabaseTableRecord,
    "QueryRecord": _h_QueryRecord,
    "RemoveRecordField": _h_RemoveRecordField,
    "RenameRecordField": _h_RenameRecordField,
    "ReplaceText": _h_ReplaceText,
    "ReplaceTextWithMapping": _h_ReplaceTextWithMapping,
    "RetryFlowFile": _h_RetryFlowFile,
    "RouteOnAttribute": _h_RouteOnAttribute,
    "RouteOnContent": _h_RouteOnContent,
    "RouteText": _h_RouteText,
    "SampleRecord": _h_SampleRecord,
    "ScanAttribute": _h_ScanAttribute,
    "ScanContent": _h_ScanContent,
    "SegmentContent": _h_SegmentContent,
    "SplitContent": _h_SplitContent,
    "SplitJson": _h_SplitJson,
    "SplitRecord": _h_SplitRecord,
    "SplitText": _h_SplitText,
    "SplitXml": _h_SplitXml,
    "TailFile": _h_TailFile,
    "TransformXml": _h_TransformXml,
    "UnpackContent": _h_UnpackContent,
    "UpdateCounter": _h_UpdateCounter,
    "UpdateDatabaseTable": _h_UpdateDatabaseTable,
    "UpdateGauge": _h_UpdateGauge,
    "UpdateRecord": _h_UpdateRecord,
    "ValidateCsv": _h_ValidateCsv,
    "ValidateJson": _h_ValidateJson,
    "ValidateRecord": _h_ValidateRecord,
    "ValidateXml": _h_ValidateXml,
    "Wait": _h_Wait,
    "JoltTransformJSON": _h_JoltTransformJSON,
    "JoltTransformRecord": _h_JoltTransformRecord,
    "UpdateAttribute": _h_UpdateAttribute,
}


def dispatch(short: str, ctx, session) -> None:
    fn = _HANDLERS.get(short)
    if fn is None:
        _passthrough(ctx, session)
        return
    fn(ctx, session)
