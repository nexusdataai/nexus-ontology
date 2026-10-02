"""
Drop legacy SFDC mapping rules left over from the deleted call-processing flow.

These rules point at SFDC custom objects that don't exist in any simulator
(``ContentDocumentLink``, ``ContentVersion``, ``cspmb__Price_Item__c``) and
were created by the original auto-mapper before the call-processing
subsystem was removed. They surface in Virtual Data Diagnostics as
``source_table_present: fail``.

Usage (inside a backend pod):

    # Dry run (default - prints what would change, makes no edits)
    kubectl -n nexus-ai-dev exec <pod> -- \
      python3 scripts/migrations/drop_legacy_sfdc_mapping_rules.py

    # Apply
    kubectl -n nexus-ai-dev exec <pod> -- \
      python3 scripts/migrations/drop_legacy_sfdc_mapping_rules.py --apply

The script uses the same FDW_PG_* env vars the live MappingRuleService
uses, so it always targets whatever backing store the running pod is
configured against.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List

LEGACY_ENTITIES: List[str] = [
    "ContentDocumentLink",
    "ContentVersion",
    "cspmb__Price_Item__c",
]


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete the rules. Default is a dry run.",
    )
    args = parser.parse_args()

    from sqlalchemy import text

    engine = _connect()
    select_sql = text(
        "SELECT id, "
        "       data->>'virtualEntity' AS ve, "
        "       data->>'sourceSchema' AS sch, "
        "       data->>'sourceTable' AS tbl, "
        "       data->>'status' AS status "
        "FROM mapping_rules "
        "WHERE data->>'virtualEntity' = ANY(:entities) "
        "ORDER BY data->>'virtualEntity', data->>'status'"
    )
    delete_sql = text(
        "DELETE FROM mapping_rules "
        "WHERE data->>'virtualEntity' = ANY(:entities)"
    )

    with engine.connect() as conn:
        rows = conn.execute(select_sql, {"entities": LEGACY_ENTITIES}).fetchall()

        print(f"Legacy SFDC mapping rules matched: {len(rows)}")
        for r in rows:
            print(f"  {r.id}  ve={r.ve:30}  schema={r.sch}  table={r.tbl}  status={r.status}")

        if not rows:
            print("Nothing to drop.")
            return 0

        if not args.apply:
            print()
            print("Dry run - no changes made. Re-run with --apply to delete.")
            return 0

        result = conn.execute(delete_sql, {"entities": LEGACY_ENTITIES})
        conn.commit()
        print()
        print(f"DELETED rows: {result.rowcount}")

        # Sanity: confirm zero remain.
        remaining = conn.execute(select_sql, {"entities": LEGACY_ENTITIES}).fetchall()
        print(f"Remaining after delete: {len(remaining)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
