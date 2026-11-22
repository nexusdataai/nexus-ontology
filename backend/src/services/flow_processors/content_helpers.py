from __future__ import annotations

import base64
import binascii
import csv
import gzip
import hashlib
import io
import json
import mimetypes
import re
import zlib
from typing import Any, Dict, List, Optional, Tuple


def identify_mime(data: bytes, filename: str = "") -> str:
    if data.startswith(b"\x1f\x8b"):
        return "application/gzip"
    if data[:1] in (b"{", b"["):
        return "application/json"
    guess, _ = mimetypes.guess_type(filename)
    if guess:
        return guess
    if b"<" in data[:200] and b">" in data[:200]:
        return "application/xml"
    try:
        data.decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        return "application/octet-stream"


def encode_content(data: bytes, encoding: str) -> bytes:
    enc = (encoding or "base64").lower()
    if enc == "base64":
        return base64.b64encode(data)
    if enc == "hex":
        return binascii.hexlify(data)
    return data


def flatten_json(obj: Any, prefix: str = "", sep: str = ".") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}{sep}{k}" if prefix else str(k)
            out.update(flatten_json(v, key, sep))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten_json(v, f"{prefix}{sep}{i}" if prefix else str(i), sep))
    else:
        if prefix:
            out[prefix] = obj
    return out


def split_content(data: bytes, pattern: str) -> List[bytes]:
    if pattern == "null" or pattern == "\\n":
        return [p for p in data.split(b"\n") if p]
    try:
        rx = re.compile(pattern.encode("utf-8") if isinstance(pattern, str) else pattern)
        return [p for p in rx.split(data) if p]
    except re.error:
        return [data]


def extract_grok(text: str, pattern: str) -> Dict[str, str]:
    grok_map = {
        "%{NUMBER}": r"(?P<NUMBER>[-+]?[0-9]*\.?[0-9]+)",
        "%{WORD}": r"(?P<WORD>\w+)",
        "%{DATA}": r"(?P<DATA>.+?)",
        "%{GREEDYDATA}": r"(?P<GREEDYDATA>.*)",
    }
    pat = pattern
    for g, r in grok_map.items():
        pat = pat.replace(g, r)
    m = re.match(pat, text)
    return {k: v for k, v in (m.groupdict() if m else {}).items() if v is not None}


def parse_syslog(text: str) -> Dict[str, str]:
    m = re.match(r"<(?P<priority>\d+)>(?P<content>.+)", text.strip())
    return m.groupdict() if m else {"raw": text}


def validate_csv(text: str) -> bool:
    try:
        list(csv.reader(io.StringIO(text)))
        return True
    except csv.Error:
        return False


def validate_xml(text: str) -> bool:
    try:
        import xml.etree.ElementTree as ET

        ET.fromstring(text.encode("utf-8", errors="replace"))
        return True
    except Exception:
        return False


def transform_xml_simple(text: str, xpath_hint: str = "") -> str:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(text.encode("utf-8", errors="replace"))
    return ET.tostring(root, encoding="unicode")


def split_xml(text: str) -> List[str]:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(text.encode("utf-8", errors="replace"))
    return [ET.tostring(child, encoding="unicode") for child in list(root)]


def gzip_bytes(data: bytes) -> bytes:
    return gzip.compress(data)


def gunzip_bytes(data: bytes) -> bytes:
    return gzip.decompress(data)