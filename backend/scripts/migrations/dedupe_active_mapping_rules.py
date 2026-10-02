"""
Dedupe active mapping rules per virtual_entity.

Auto-mapper has been run multiple times across redeploys, leaving many
``virtual_entity`` rows with N>1 active mapping rules. ``VirtualQueryService``
picks ``active_rules[0]`` (storage-order dependent), which is fragile and
shows up as ``active_rule_count_multi: warn`` in the Virtual Data
Diagnostics report.

This script keeps the best rule active per entity and deactivates the rest:

  Score = 1000 * len(field_maps)
        + 100  if sourceSchema in CANONICAL_SCHEMAS
        +  10  if sourceType == "FDW"
        +   1  per second of recency (newer wins on ties)

The chosen rule remains ``status='active'``; every other active rule for
the same ``virtual_entity`` is set to ``status='inactive'`` (rules are
preserved so the change is reversible).

Usage (inside a backend pod):

    # Dry run (default - prints planned changes)
    kubectl -n nexus-ai-dev exec <pod> -- \
      python3 scripts/migrations/dedupe_active_mapping_rules.py

    # Apply
    kubectl -n nexus-ai-dev exec <pod> -- \
      python3 scripts/migrations/dedupe_active_mapping_rules.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Tuple

CANONICAL_SCHEMAS = {
    "sfdc_itxp2dev",
    "sap_s4hana",
    "oracle_erp",
    "external_sources",
}


def _connect():
    from sqlalchemy import create_engine
    host = os.getenv("FDW_PG_HOST", "")
    port = os.getenv("FDW_PG_PORT", "5432")
    db = os.getenv("FDW_PG_DATABASE", "")
    user = os.getenv("FDW_PG_USER", "")
    pw = os.getenv("FDW_PG_PASSWORD", "")
    if not host or not db:
        print(f"ERROR: FDW_PG_HOST/FDW_PG_DATABASE not set "
              f"(host={host!r} db={db!r})", file=sys.stderr)
        sys.exit(2)
    url = f"postgresql://{user}:{pw}@{host}:{port}/{db}"
    return create_engine(url, pool_size=2, max_overflow=2)


def _score(rule_data: Dict[str, Any]) -> Tuple[int, int, int, int]:
    """Higher tuple wins. Lexicographic order across the 4 components."""
    field_count = len(rule_data.get("fieldMaps") or [])
    schema_bonus = 100 if rule_data.get("sourceSchema") in CANONICAL_SCHEMAS else 0
    type_bonus = 10 if rule_data.get("sourceType") == "FDW" else 0
    # Recency: epoch seconds parsed from ISO updatedAt (best-effort).
    updated_at = rule_data.get("updatedAt") or rule_data.get("createdAt") or ""
    recency = 0
    try:
        from datetime import datetime
        recency = int(datetime.fromisoformat(
            updated_at.replace("Z", "+00:00")
        ).timestamp())
    except Exception:
        recency = 0
    return (field_count, schema_bonus, type_bonus, recency)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually deactivate duplicates. Default is a dry run.")
    args = parser.parse_args()

    from sqlalchemy import text
    engine = _connect()
    select_sql = text(
        "SELECT id, data FROM mapping_rules "
        "WHERE data->>'status' = 'active' "
        "ORDER BY data->>'virtualEntity', id"
    )
    update_sql = text(
        "UPDATE mapping_rules "
        "SET data = jsonb_set(data, '{status}', '\"inactive\"'::jsonb) "
        "WHERE id = :rule_id"
    )

    with engine.connect() as conn:
        rows = conn.execute(select_sql).fetchall()
        per_entity: Dict[str, List[Tuple[str, Dict[str, Any]]]] = defaultdict(list)
        for r in rows:
            data = r.data if isinstance(r.data, dict) else json.loads(r.data)
            ve = data.get("virtualEntity") or "<unknown>"
            per_entity[ve].append((r.id, data))

        affected_entities = 0
        rules_to_deactivate: List[Tuple[str, str, str]] = []
        keepers: List[Tuple[str, str]] = []

        for ve, items in per_entity.items():
            if len(items) <= 1:
                continue
            affected_entities += 1
            scored = sorted(items, key=lambda kv: _score(kv[1]), reverse=True)
            keep_id, keep_data = scored[0]
            keepers.append((ve, keep_id))
            for rid, _ in scored[1:]:
                rules_to_deactivate.append((ve, rid, keep_id))

        print(f"Active rules total: {sum(len(v) for v in per_entity.values())}")
        print(f"Distinct virtual entities: {len(per_entity)}")
        print(f"Entities with >1 active rule: {affected_entities}")
        print(f"Rules to deactivate: {len(rules_to_deactivate)}")
        print()

        if rules_to_deactivate:
            print("Plan:")
            for ve, drop_id, keep_id in rules_to_deactivate[:25]:
                print(f"  {ve:35}  drop {drop_id}  keep {keep_id}")
            if len(rules_to_deactivate) > 25:
                print(f"  ... ({len(rules_to_deactivate) - 25} more)")

        if not args.apply:
            print()
            print("Dry run - no changes. Re-run with --apply.")
            return 0

        for _, drop_id, _ in rules_to_deactivate:
            conn.execute(update_sql, {"rule_id": drop_id})
        conn.commit()
        print()
        print(f"DEACTIVATED {len(rules_to_deactivate)} rules across "
              f"{affected_entities} virtual entities.")

        # Sanity: every entity should now have exactly one active rule.
        rows_after = conn.execute(select_sql).fetchall()
        per_entity_after: Dict[str, int] = defaultdict(int)
        for r in rows_after:
            data = r.data if isinstance(r.data, dict) else json.loads(r.data)
            per_entity_after[data.get("virtualEntity") or "<unknown>"] += 1
        bad = {ve: n for ve, n in per_entity_after.items() if n > 1}
        if bad:
            print(f"WARNING: {len(bad)} entities still have >1 active rule:")
            for ve, n in list(bad.items())[:10]:
                print(f"  {ve}: {n}")
        else:
            print("All entities now have <=1 active rule.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
