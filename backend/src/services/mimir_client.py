"""
Grafana Mimir client.

Two responsibilities:

1. ``MimirRemoteWriteClient.write_samples(...)`` -> POSTs Prometheus
   ``remote_write`` payloads to Mimir's ``/api/v1/push`` endpoint.
   Used by historian / KPI-trend journeys to push metric samples.

2. ``MimirRemoteWriteClient.query_range(...)`` and ``.instant_query(...)`` ->
   thin wrappers over Mimir's ``/prometheus/api/v1/query[_range]`` HTTP API.
   Used by ``MimirAdapter`` (in ``virtual_query_service``) to back the
   ``MIMIR`` source type for the VDL.

Configuration via env / SSM:

- ``MIMIR_URL``          : base URL of Mimir HTTP API (default
  ``http://mimir-svc.<ns>.svc.cluster.local:8080``)
- ``MIMIR_TENANT_ID``    : default ``X-Scope-OrgID`` header value
- ``MIMIR_ENABLED``      : ``true`` / ``false`` to short-circuit calls

The remote_write encoder is a minimal hand-rolled Prometheus WriteRequest
protobuf serializer so we do not require the upstream ``prometheus_pb2``
generated code. Snappy compression is applied via the optional
``python-snappy`` package; if it is not installed the writer logs a warning
and silently drops the write (callers fall back to the simulator/Athena
sink which is still populated by ``ResultSink``).
"""

from __future__ import annotations

import os
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
from loguru import logger

mimir_logger = logger.bind(component="mimir")


# ---------------------------------------------------------------------------
# Minimal Prometheus remote_write protobuf encoder
# ---------------------------------------------------------------------------
#
# Reference: https://github.com/prometheus/prometheus/blob/main/prompb/types.proto
#
#   message WriteRequest {
#       repeated TimeSeries timeseries = 1;
#   }
#   message TimeSeries {
#       repeated Label labels = 1;
#       repeated Sample samples = 2;
#   }
#   message Label  { string name = 1; string value = 2; }
#   message Sample { double value = 1; int64 timestamp = 2; }


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _tag(field_num: int, wire_type: int) -> bytes:
    return _varint((field_num << 3) | wire_type)


def _string_field(field_num: int, value: str) -> bytes:
    data = value.encode("utf-8")
    return _tag(field_num, 2) + _varint(len(data)) + data


def _double_field(field_num: int, value: float) -> bytes:
    return _tag(field_num, 1) + struct.pack("<d", value)


def _sint64_field(field_num: int, value: int) -> bytes:
    if value < 0:
        value = (1 << 64) + value
    return _tag(field_num, 0) + _varint(value)


def _embedded_field(field_num: int, payload: bytes) -> bytes:
    return _tag(field_num, 2) + _varint(len(payload)) + payload


def _encode_label(name: str, value: str) -> bytes:
    return _string_field(1, name) + _string_field(2, value)


def _encode_sample(value: float, timestamp_ms: int) -> bytes:
    return _double_field(1, value) + _sint64_field(2, timestamp_ms)


def _encode_timeseries(labels: Dict[str, str], samples: List[Tuple[float, int]]) -> bytes:
    body = b""
    for name, val in labels.items():
        body += _embedded_field(1, _encode_label(name, val))
    for value, ts in samples:
        body += _embedded_field(2, _encode_sample(value, ts))
    return body


def _encode_write_request(series_list: Iterable[Tuple[Dict[str, str], List[Tuple[float, int]]]]) -> bytes:
    body = b""
    for labels, samples in series_list:
        body += _embedded_field(1, _encode_timeseries(labels, samples))
    return body


def _maybe_snappy_compress(data: bytes) -> Tuple[bytes, bool]:
    try:
        import snappy  # type: ignore
        return snappy.compress(data), True
    except Exception:
        return data, False


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class Sample:
    """A single Prometheus sample (one labelset + one (value, timestamp) point)."""

    metric: str
    labels: Dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    timestamp_ms: Optional[int] = None

    def fingerprint(self) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        return (self.metric, tuple(sorted(self.labels.items())))


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class MimirRemoteWriteClient:
    """
    Low-level client for Mimir HTTP API.

    Safe by construction: every method is async and tolerates Mimir being
    unreachable. Callers receive booleans / row lists rather than raised
    exceptions for transport failures, so a journey step that loses
    connectivity to Mimir does not abort the whole pipeline.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        tenant_id: Optional[str] = None,
        enabled: Optional[bool] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout: float = 10.0,
    ) -> None:
        self.url = (url or os.environ.get("MIMIR_URL", "")).rstrip("/")
        self.tenant_id = tenant_id or os.environ.get("MIMIR_TENANT_ID", "nexus-default")
        if enabled is None:
            enabled = os.environ.get("MIMIR_ENABLED", "true").lower() == "true"
        self.enabled = bool(enabled and self.url)
        self._client = http_client
        self._timeout = timeout
        self._owned_client = http_client is None

    @property
    def configured(self) -> bool:
        return self.enabled

    def _client_or_new(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def aclose(self) -> None:
        if self._owned_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _headers(self, tenant_id: Optional[str], extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"X-Scope-OrgID": tenant_id or self.tenant_id}
        if extra:
            h.update(extra)
        return h

    # ---- write -------------------------------------------------------------

    async def write_samples(
        self,
        samples: List[Sample],
        tenant_id: Optional[str] = None,
    ) -> bool:
        """
        Push a batch of samples to Mimir via Prometheus remote_write.

        Returns True on success, False on any failure (logged). Never raises.
        """
        if not self.enabled:
            mimir_logger.debug("Mimir disabled - skipping write of {} samples", len(samples))
            return False
        if not samples:
            return True

        # Group samples by (metric, labelset) so each TimeSeries payload is well-formed.
        grouped: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], List[Tuple[float, int]]] = {}
        labels_for: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Dict[str, str]] = {}
        now_ms = int(time.time() * 1000)
        for s in samples:
            ts = s.timestamp_ms if s.timestamp_ms is not None else now_ms
            full_labels = dict(s.labels)
            full_labels["__name__"] = s.metric
            key = (s.metric, tuple(sorted(full_labels.items())))
            grouped.setdefault(key, []).append((float(s.value), int(ts)))
            labels_for[key] = full_labels

        series_iter = ((labels_for[k], pts) for k, pts in grouped.items())
        body = _encode_write_request(series_iter)
        compressed, compressed_ok = _maybe_snappy_compress(body)
        if not compressed_ok:
            mimir_logger.warning(
                "python-snappy not installed - dropping {} samples (install python-snappy "
                "to enable Mimir remote_write)",
                len(samples),
            )
            return False

        headers = self._headers(
            tenant_id,
            {
                "Content-Type": "application/x-protobuf",
                "Content-Encoding": "snappy",
                "X-Prometheus-Remote-Write-Version": "0.1.0",
            },
        )
        try:
            cli = self._client_or_new()
            resp = await cli.post(f"{self.url}/api/v1/push", content=compressed, headers=headers)
            if resp.status_code in (200, 204):
                mimir_logger.debug(
                    "Wrote {} samples ({} series) to Mimir tenant={}",
                    len(samples),
                    len(grouped),
                    tenant_id or self.tenant_id,
                )
                return True
            mimir_logger.error(
                "Mimir remote_write failed: status={} body={}", resp.status_code, resp.text[:300]
            )
            return False
        except Exception as e:
            mimir_logger.error("Mimir remote_write exception: {}", e)
            return False

    # ---- read --------------------------------------------------------------

    async def instant_query(
        self,
        promql: str,
        tenant_id: Optional[str] = None,
        time_s: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Run a PromQL instant query, return raw Prometheus results array."""
        if not self.enabled:
            return []
        params = {"query": promql}
        if time_s is not None:
            params["time"] = str(time_s)
        try:
            cli = self._client_or_new()
            resp = await cli.get(
                f"{self.url}/prometheus/api/v1/query",
                params=params,
                headers=self._headers(tenant_id),
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload.get("data", {}).get("result", []) or []
        except Exception as e:
            mimir_logger.error("Mimir instant_query failed: {}", e)
            return []

    async def query_range(
        self,
        promql: str,
        start: int,
        end: int,
        step: int,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Run a PromQL range query, return raw Prometheus matrix results array."""
        if not self.enabled:
            return []
        params = {
            "query": promql,
            "start": str(start),
            "end": str(end),
            "step": str(step),
        }
        try:
            cli = self._client_or_new()
            resp = await cli.get(
                f"{self.url}/prometheus/api/v1/query_range",
                params=params,
                headers=self._headers(tenant_id),
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload.get("data", {}).get("result", []) or []
        except Exception as e:
            mimir_logger.error("Mimir query_range failed: {}", e)
            return []


# Module-level singleton getter (lazy) ----------------------------------------

_default_client: Optional[MimirRemoteWriteClient] = None


def get_default_mimir_client() -> MimirRemoteWriteClient:
    global _default_client
    if _default_client is None:
        _default_client = MimirRemoteWriteClient()
    return _default_client
