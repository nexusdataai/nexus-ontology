from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from src.services.flow_runtime.flow_record import FlowRecord


@dataclass
class _PendingTransfer:
    record: FlowRecord
    relationship: str


class ProcessSession:
    def __init__(self) -> None:
        self._inbound: List[FlowRecord] = []
        self._pending: List[_PendingTransfer] = []
        self._removed: List[str] = []
        self._created: List[FlowRecord] = []

    def set_inbound(self, records: List[FlowRecord]) -> None:
        self._inbound = list(records)

    def get(self) -> Optional[FlowRecord]:
        if not self._inbound:
            return None
        return self._inbound.pop(0)

    def read(self, record: FlowRecord) -> bytes:
        return record.content

    def write(self, record: FlowRecord, contents: bytes) -> FlowRecord:
        record.content = bytes(contents)
        return record

    def create(self, content: bytes = b"", attributes: Optional[Dict[str, str]] = None) -> FlowRecord:
        ff = FlowRecord(content=content, attributes=dict(attributes or {}))
        self._created.append(ff)
        return ff

    def transfer(self, record: FlowRecord, relationship: str) -> None:
        self._pending.append(_PendingTransfer(record=record, relationship=relationship))

    def remove(self, record: FlowRecord) -> None:
        self._removed.append(record.record_id)

    def commit(self) -> Dict[str, List[FlowRecord]]:
        """Drain pending transfers grouped by relationship name."""
        out: Dict[str, List[FlowRecord]] = {}
        for pt in self._pending:
            out.setdefault(pt.relationship, []).append(pt.record)
        self._pending.clear()
        return out