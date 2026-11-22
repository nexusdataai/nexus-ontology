from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class FlowFile:
    attributes: Dict[str, str] = field(default_factory=dict)
    content: bytes = b""
    flowfile_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def get_attribute(self, key: str, default: str = "") -> str:
        return self.attributes.get(key, default)

    def put_attribute(self, key: str, value: str) -> None:
        self.attributes[key] = str(value)