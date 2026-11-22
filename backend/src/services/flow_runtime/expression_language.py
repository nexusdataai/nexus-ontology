"""NiFi Expression Language subset for flow processor previews."""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, Mapping

_ATTR = re.compile(r"\$\{([^}]+)\}")
_FUNC = re.compile(r"^([a-zA-Z0-9_.-]+):([a-zA-Z]+)\((.*)\)$")


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _func_handlers(attr_val: str, func: str, arg: str) -> str:
    arg = _unquote(arg)
    if func == "equals":
        return "true" if attr_val == arg else "false"
    if func == "contains":
        return "true" if arg in attr_val else "false"
    if func == "matches":
        try:
            return "true" if re.search(arg, attr_val) else "false"
        except re.error:
            return "false"
    if func in ("isEmpty", "isNull"):
        return "true" if not attr_val else "false"
    if func == "length":
        return str(len(attr_val))
    if func == "toUpper":
        return attr_val.upper()
    if func == "toLower":
        return attr_val.lower()
    if func == "trim":
        return attr_val.strip()
    if func == "substring" and "," in arg:
        start, end = arg.split(",", 1)
        return attr_val[int(start) : int(end) if end else None]
    return attr_val


def evaluate_expression(template: str, attributes: Mapping[str, Any]) -> str:
    if not template:
        return ""

    attrs = {str(k): "" if v is None else str(v) for k, v in attributes.items()}

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1).strip()
        fm = _FUNC.match(inner)
        if fm:
            name, func, arg = fm.group(1), fm.group(2), fm.group(3)
            return _func_handlers(attrs.get(name, ""), func, arg)
        if ":" in inner:
            name, func = inner.split(":", 1)
            if func in ("equals", "contains"):
                return attrs.get(name, "")
        return attrs.get(inner, "")

    return _ATTR.sub(repl, template)


def evaluate_condition(expr: str, attributes: Mapping[str, Any]) -> bool:
    resolved = evaluate_expression(expr, attributes).strip().lower()
    return resolved not in ("", "false", "0", "no", "null")