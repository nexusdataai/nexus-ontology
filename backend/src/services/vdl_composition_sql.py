"""
Build read-only SQL from a VDL composition spec (runtime_sql strategy).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.models.vdl_composition_models import VdlCompositionResponse

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|;"
    r"|--|/\*)\b",
    re.IGNORECASE,
)


def _quote_ident(schema: str, table: str) -> str:
    return f'"{schema}"."{table}"'


def composition_to_sql(
    composition: VdlCompositionResponse,
    *,
    limit: Optional[int] = None,
    extra_where: Optional[str] = None,
) -> Tuple[str, List[str]]:
    """
    Returns (sql, errors). When errors is non-empty, sql may be empty.
    """
    errors: List[str] = []
    sources = composition.sources
    if not sources:
        errors.append("Composition has no source tables")
        return "", errors

    aliases = {s.alias for s in sources}
    for j in composition.joins:
        if j.left not in aliases or j.right not in aliases:
            errors.append(f"Join references unknown alias: {j.left} / {j.right}")
        if _FORBIDDEN.search(j.on or ""):
            errors.append("Join ON clause contains forbidden tokens")

    if composition.filter_expression and _FORBIDDEN.search(composition.filter_expression):
        errors.append("Filter expression contains forbidden tokens")

    select_parts: List[str] = []
    if composition.projections:
        for p in composition.projections:
            if _FORBIDDEN.search(p.expr or ""):
                errors.append(f"Projection for {p.target_field} contains forbidden tokens")
                continue
            select_parts.append(f'{p.expr} AS "{p.target_field}"')
    elif composition.field_maps and len(sources) == 1:
        alias = sources[0].alias
        for fm in composition.field_maps:
            if fm.source_field:
                select_parts.append(f'{alias}."{fm.source_field}" AS "{fm.target_field}"')
    else:
        errors.append("Define projections or field maps for multi-source compositions")

    if errors:
        return "", errors

    primary = sources[0]
    from_clause = f'{_quote_ident(primary.schema, primary.table)} AS {primary.alias}'

    join_clauses: List[str] = []
    joined = {primary.alias}
    for j in composition.joins:
        jtype = (j.type or "inner").upper()
        if jtype not in ("INNER", "LEFT", "RIGHT", "FULL"):
            jtype = "INNER"
        right = next((s for s in sources if s.alias == j.right), None)
        if not right:
            continue
        join_clauses.append(
            f'{jtype} JOIN {_quote_ident(right.schema, right.table)} AS {right.alias} '
            f'ON {j.on}'
        )
        joined.add(j.right)

    for src in sources[1:]:
        if src.alias not in joined and not composition.joins:
            join_clauses.append(
                f'CROSS JOIN {_quote_ident(src.schema, src.table)} AS {src.alias}'
            )

    sql = f"SELECT {', '.join(select_parts)} FROM {from_clause}"
    if join_clauses:
        sql += " " + " ".join(join_clauses)

    where_parts: List[str] = []
    if composition.filter_expression:
        where_parts.append(f"({composition.filter_expression})")
    if extra_where:
        where_parts.append(f"({extra_where})")
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    if limit is not None:
        sql += f" LIMIT {int(limit)}"

    return sql, errors


def mapping_rule_item_to_composition_attrs(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a legacy mapping-rule dict into composition storage attrs."""
    ve = item.get("virtualEntity", "")
    return {
        "virtualEntity": ve,
        "name": item.get("name"),
        "status": item.get("status", "draft"),
        "strategy": "runtime_sql",
        "from": [
            {
                "alias": "src",
                "sourceSystem": item.get("sourceSystem", ""),
                "schema": item.get("sourceSchema", ""),
                "table": item.get("sourceTable", ""),
            }
        ],
        "joins": [],
        "select": [
            {
                "targetField": fm.get("targetField", ""),
                "expr": f'src."{fm.get("sourceField", "")}"',
            }
            for fm in (item.get("fieldMaps") or [])
            if fm.get("targetField")
        ],
        "fieldMaps": item.get("fieldMaps") or [],
        "filterExpression": item.get("filterExpression"),
        "businessLogic": item.get("businessLogic"),
    }