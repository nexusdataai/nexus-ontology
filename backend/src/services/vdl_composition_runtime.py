"""
Execute VDL compositions (simulator in-memory joins + FDW read-only SQL).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.models.fdw_models import QueryRequest
from src.models.vdl_composition_models import VdlCompositionResponse
from src.services.vdl_composition_sql import composition_to_sql

_JOIN_ON = re.compile(
    r"^\s*(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)\s*$",
    re.IGNORECASE,
)


async def _load_table(sim: Any, schema: str, table: str, limit: int) -> List[Dict[str, Any]]:
    req = QueryRequest(table=table, schema_name=schema, limit=limit, offset=0)
    if hasattr(sim, "execute_query"):
        resp = await sim.execute_query(req)
        return list(resp.rows or [])
    return []


def _index_rows(rows: List[Dict[str, Any]], col: str) -> Dict[Any, List[Dict[str, Any]]]:
    out: Dict[Any, List[Dict[str, Any]]] = {}
    for row in rows:
        key = row.get(col)
        out.setdefault(key, []).append(row)
    return out


async def execute_composition_on_simulator(
    composition: VdlCompositionResponse,
    sim: Any,
    *,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Join tables in-memory when all sources share one simulator backend."""
    sources = composition.sources
    if not sources:
        return []

    tables_data: Dict[str, List[Dict[str, Any]]] = {}
    for src in sources:
        tables_data[src.alias] = await _load_table(sim, src.schema, src.table, limit * 10)

    if len(sources) == 1 and not composition.joins:
        alias = sources[0].alias
        rows = tables_data[alias][:limit]
        return _project_rows(composition, rows, alias_prefix=alias)

    working = tables_data.get(sources[0].alias, [])
    for join in composition.joins:
        m = _JOIN_ON.match(join.on or "")
        if not m:
            continue
        la, lc, ra, rc = m.groups()
        right_rows = tables_data.get(ra, [])
        right_idx = _index_rows(right_rows, rc)
        jtype = (join.type or "inner").lower()
        merged: List[Dict[str, Any]] = []
        for left in working:
            key = left.get(lc)
            matches = right_idx.get(key, [])
            if not matches:
                if jtype == "left":
                    merged.append({**left})
                continue
            for right in matches:
                row = {**left}
                for k, v in right.items():
                    row[f"{ra}.{k}"] = v
                    row[k] = v
                merged.append(row)
        working = merged
    return _project_rows(composition, working[:limit], alias_prefix="")


def _project_rows(
    composition: VdlCompositionResponse,
    rows: List[Dict[str, Any]],
    alias_prefix: str,
) -> List[Dict[str, Any]]:
    if composition.projections:
        out: List[Dict[str, Any]] = []
        for row in rows:
            projected: Dict[str, Any] = {}
            for p in composition.projections:
                projected[p.target_field] = _eval_simple_expr(p.expr, row)
            out.append(projected)
        return out

    if composition.field_maps and alias_prefix:
        out = []
        for row in rows:
            projected = {}
            for fm in composition.field_maps:
                key = fm.source_field
                projected[fm.target_field] = row.get(key)
            out.append(projected)
        return out

    return rows


def _eval_simple_expr(expr: str, row: Dict[str, Any]) -> Any:
    """Support alias.column references; pass through literals loosely."""
    expr = (expr or "").strip()
    m = re.match(r"^(\w+)\.\"?(\w+)\"?$", expr)
    if m:
        alias, col = m.groups()
        return row.get(col) or row.get(f"{alias}.{col}")
    m2 = re.match(r"^(\w+)\.(\w+)$", expr)
    if m2:
        alias, col = m2.groups()
        return row.get(col) or row.get(f"{alias}.{col}")
    if expr.startswith("src."):
        col = expr.split(".", 1)[1].strip('"')
        return row.get(col)
    return row.get(expr.strip('"'), None)