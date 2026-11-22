"""In-memory record batches for record-oriented flow processors."""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional


@dataclass
class RecordSet:
    records: List[Dict[str, Any]] = field(default_factory=list)
    format_name: str = "json"

    @classmethod
    def load(cls, raw: bytes, reader: str) -> "RecordSet":
        fmt = (reader or "json").strip().lower()
        text = raw.decode("utf-8", errors="replace")
        records: List[Dict[str, Any]] = []
        if fmt == "csv":
            for row in csv.DictReader(io.StringIO(text)):
                records.append(dict(row))
        else:
            data = json.loads(text or "[]")
            if isinstance(data, dict):
                records = [data]
            elif isinstance(data, list):
                records = [r if isinstance(r, dict) else {"value": r} for r in data]
        return cls(records=records, format_name=fmt)

    def dump(self, writer: Optional[str] = None) -> bytes:
        fmt = (writer or self.format_name or "json").strip().lower()
        if fmt == "csv":
            if not self.records:
                return b""
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=list(self.records[0].keys()))
            w.writeheader()
            w.writerows(self.records)
            return buf.getvalue().encode("utf-8")
        return json.dumps(self.records, indent=2).encode("utf-8")

    def schema_fields(self) -> List[str]:
        keys: List[str] = []
        for rec in self.records:
            for k in rec.keys():
                if k not in keys:
                    keys.append(k)
        return keys

    def fork(self, count: int) -> List["RecordSet"]:
        if count <= 1:
            return [RecordSet(records=list(self.records), format_name=self.format_name)]
        size = max(1, len(self.records) // count)
        out: List[RecordSet] = []
        for i in range(0, len(self.records), size):
            out.append(RecordSet(records=self.records[i : i + size], format_name=self.format_name))
        return out or [RecordSet(format_name=self.format_name)]

    def merge(self, other: "RecordSet") -> None:
        self.records.extend(other.records)

    def partition(self, key: str) -> Dict[str, "RecordSet"]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for rec in self.records:
            k = str(rec.get(key, ""))
            groups.setdefault(k, []).append(rec)
        return {k: RecordSet(records=v, format_name=self.format_name) for k, v in groups.items()}

    def sample(self, ratio: float) -> "RecordSet":
        import random

        ratio = max(0.0, min(1.0, ratio))
        n = max(1, int(len(self.records) * ratio)) if self.records else 0
        if n >= len(self.records):
            return RecordSet(records=list(self.records), format_name=self.format_name)
        return RecordSet(records=random.sample(self.records, n), format_name=self.format_name)

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self.records)