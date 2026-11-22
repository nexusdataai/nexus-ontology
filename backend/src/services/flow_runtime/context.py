from __future__ import annotations

import re
from typing import Any, Dict, Mapping

_EL_ATTR = re.compile(r"\$\{([a-zA-Z0-9_.-]+)\}")


class ProcessContext:
    """Resolved processor configuration (subset of NiFi Expression Language)."""

    def __init__(self, properties: Mapping[str, Any]):
        self._properties = dict(properties)

    def get_property(self, name: str, default: str = "") -> str:
        val = self._properties.get(name, default)
        return str(val) if val is not None else default

    def resolve(self, template: str, flowfile_attrs: Dict[str, str]) -> str:
        if not template:
            return ""

        def repl(m: re.Match[str]) -> str:
            return flowfile_attrs.get(m.group(1), "")

        return _EL_ATTR.sub(repl, template)