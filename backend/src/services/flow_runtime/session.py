from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from src.services.flow_runtime.flowfile import FlowFile


@dataclass
class _PendingTransfer:
    flowfile: FlowFile
    relationship: str


class ProcessSession:
    def __init__(self) -> None:
        self._inbound: List[FlowFile] = []
        self._pending: List[_PendingTransfer] = []
        self._removed: List[str] = []
        self._created: List[FlowFile] = []

    def set_inbound(self, flowfiles: List[FlowFile]) -> None:
        self._inbound = list(flowfiles)

    def get(self) -> Optional[FlowFile]:
        if not self._inbound:
            return None
        return self._inbound.pop(0)

    def read(self, flowfile: FlowFile) -> bytes:
        return flowfile.content

    def write(self, flowfile: FlowFile, contents: bytes) -> FlowFile:
        flowfile.content = bytes(contents)
        return flowfile

    def create(self, content: bytes = b"", attributes: Optional[Dict[str, str]] = None) -> FlowFile:
        ff = FlowFile(content=content, attributes=dict(attributes or {}))
        self._created.append(ff)
        return ff

    def transfer(self, flowfile: FlowFile, relationship: str) -> None:
        self._pending.append(_PendingTransfer(flowfile=flowfile, relationship=relationship))

    def remove(self, flowfile: FlowFile) -> None:
        self._removed.append(flowfile.flowfile_id)

    def commit(self) -> Dict[str, List[FlowFile]]:
        """Drain pending transfers grouped by relationship name."""
        out: Dict[str, List[FlowFile]] = {}
        for pt in self._pending:
            out.setdefault(pt.relationship, []).append(pt.flowfile)
        self._pending.clear()
        return out