"""Connector-style I/O for flow processor preview runs (HTTP, file, optional S3)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin

_PREVIEW_ROOT = Path(os.getenv("NEXUS_FLOW_PREVIEW_FS_ROOT", tempfile.gettempdir())) / "nexus-flow-preview"
_UNSAFE_FS = os.getenv("NEXUS_FLOW_UNSAFE_FS", "false").strip().lower() in ("1", "true", "yes")


def preview_fs_enabled() -> bool:
    return _UNSAFE_FS or os.getenv("NEXUS_FLOW_RUNTIME_EXECUTION", "false").strip().lower() in ("1", "true", "yes")


def _safe_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = _PREVIEW_ROOT / p
    if not preview_fs_enabled():
        raise PermissionError("filesystem I/O disabled; set NEXUS_FLOW_UNSAFE_FS=true for local preview")
    _PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def http_request(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    body: bytes = b"",
    timeout_s: float = 30.0,
) -> Tuple[bytes, Dict[str, str], int]:
    import httpx

    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        resp = client.request(method.upper(), url, headers=headers or {}, content=body)
        out_headers = {k: v for k, v in resp.headers.items()}
        return resp.content, out_headers, resp.status_code


def read_file(path: str) -> bytes:
    return _safe_path(path).read_bytes()


def write_file(path: str, data: bytes) -> str:
    dest = _safe_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return str(dest)


def list_directory(path: str) -> list[str]:
    base = _safe_path(path)
    if not base.is_dir():
        return []
    return [p.name for p in base.iterdir()]


def delete_file(path: str) -> None:
    p = _safe_path(path)
    if p.is_file():
        p.unlink()


def s3_get(bucket: str, key: str, *, region: Optional[str] = None) -> bytes:
    import boto3

    client = boto3.client("s3", region_name=region or os.getenv("AWS_REGION"))
    obj = client.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def s3_put(bucket: str, key: str, body: bytes, *, region: Optional[str] = None) -> None:
    import boto3

    client = boto3.client("s3", region_name=region or os.getenv("AWS_REGION"))
    client.put_object(Bucket=bucket, Key=key, Body=body)


def join_url(base: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))