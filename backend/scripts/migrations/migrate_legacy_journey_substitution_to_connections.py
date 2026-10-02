#!/usr/bin/env python3
"""Phase 1 -- convert legacy ``${steps.X.y}`` params on persisted
JourneyDocs into first-class ``ConnectionDoc`` rows.

Operates on every journey row in the Foundry-workspace DynamoDB table
via :class:`JourneyStoreService`. Idempotent: a journey whose stage
already carries a ``connections`` list with the same edges is left
untouched. Use ``--dry-run`` to preview without writing.

What gets converted, per stage:

  For every step ``s`` in the stage, walk ``s.params``. Any string
  value matching ``${steps.<from_step>.<dotted_path>}`` becomes a
  ConnectionDoc:

    {
      from_step:         <from_step>,
      from_relationship: "success",
      from_path:         <dotted_path>,
      to_step:           s.step_id,
      to_param:          <param_key>,
    }

  The placeholder string is left in ``params`` for back-compat (the
  runner walks connections first; substitution fallback still resolves
  the same value if connections are dropped). Also stamps ``bucket``
  from ``solution_id`` when missing.

Usage:
  AWS_PROFILE=... python migrate_legacy_journey_substitution_to_connections.py --dry-run
  AWS_PROFILE=... python migrate_legacy_journey_substitution_to_connections.py
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Allow ``python scripts/...`` invocation by inserting the backend root onto sys.path.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


_PLACEHOLDER_RX = re.compile(
    r"""^\s*\$\{\s*steps\.([a-zA-Z0-9_-]+)\.([^}\s]+)\s*\}\s*$""",
)


# ``solution_id`` -> bucket. Same map as the YAML rewrite script.
SOLUTION_TO_BUCKET = {
    "order-to-cash": "o2c",
    "customer-360": "customer-360",
    "demand-forecasting": "supply-chain",
    "inventory-optimization": "supply-chain",
    "procurement-analytics": "supply-chain",
    "production-quality": "supply-chain",
    "supply-chain-risk": "supply-chain",
    "esg-sustainability": "esg",
    "builder": "default",
}


def _extract_connection(
    *, to_step: str, to_param: str, value: Any,
) -> Dict[str, Any] | None:
    """Return a ConnectionDoc dict when ``value`` is a ${steps.X.Y} placeholder."""
    if not isinstance(value, str):
        return None
    m = _PLACEHOLDER_RX.match(value)
    if not m:
        return None
    return {
        "from_step": m.group(1),
        "from_relationship": "success",
        "from_path": m.group(2),
        "to_step": to_step,
        "to_param": to_param,
    }


def _scan_stage(stage: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return ConnectionDocs derived from ${steps.X.y} markers inside the stage."""
    derived: List[Dict[str, Any]] = []
    for step in stage.get("steps") or []:
        sid = step.get("step_id")
        if not sid:
            continue
        for k, v in (step.get("params") or {}).items():
            conn = _extract_connection(to_step=sid, to_param=k, value=v)
            if conn is not None:
                derived.append(conn)
    return derived


def _connections_equivalent(a: List[Dict[str, Any]], b: List[Dict[str, Any]]) -> bool:
    """Same set of (from_step, from_relationship, from_path, to_step, to_param)?"""
    def _key(c: Dict[str, Any]) -> Tuple:
        return (
            c.get("from_step"), c.get("from_relationship"),
            c.get("from_path"), c.get("to_step"), c.get("to_param"),
        )
    return {_key(c) for c in a} == {_key(c) for c in b}


def _convert(doc: Dict[str, Any]) -> Tuple[Dict[str, Any], int, bool]:
    """Returns ``(new_doc, connections_added, bucket_stamped)``."""
    out = dict(doc)
    bucket_stamped = False
    if not out.get("bucket"):
        bucket = SOLUTION_TO_BUCKET.get(str(out.get("solution_id") or ""))
        if bucket:
            out["bucket"] = bucket
            bucket_stamped = True

    new_stages: List[Dict[str, Any]] = []
    added = 0
    for stage in out.get("stages") or []:
        new_stage = dict(stage)
        derived = _scan_stage(stage)
        existing = list(stage.get("connections") or [])
        if derived and not _connections_equivalent(existing, derived):
            # Merge: keep existing + append any derived that aren't already present.
            existing_keys = {
                (c.get("from_step"), c.get("from_relationship"),
                 c.get("from_path"), c.get("to_step"), c.get("to_param"))
                for c in existing
            }
            for d in derived:
                k = (d["from_step"], d["from_relationship"],
                     d.get("from_path"), d["to_step"], d["to_param"])
                if k not in existing_keys:
                    existing.append(d)
                    added += 1
            new_stage["connections"] = existing
        new_stages.append(new_stage)
    out["stages"] = new_stages
    return out, added, bucket_stamped


async def _run(*, dry_run: bool) -> int:
    try:
        from src.services.journey_store_service import JourneyStoreService
    except Exception as e:
        print(f"error: JourneyStoreService import failed: {e}", file=sys.stderr)
        return 2

    store = JourneyStoreService()

    try:
        rows = await store.list_all()
    except Exception as e:
        print(f"error: store.list_all failed: {e}", file=sys.stderr)
        return 3

    print(f"Scanning {len(rows)} persisted journeys{' (dry-run)' if dry_run else ''}")
    migrated, skipped, conflicts = 0, 0, 0
    for r in rows:
        new_doc, added, bucket_stamped = _convert(r)
        if not added and not bucket_stamped:
            skipped += 1
            continue
        jid = new_doc.get("journey_id") or new_doc.get("use_case_id") or "<unknown>"
        print(
            f"  + {jid}  [+{added} connections, bucket={'set' if bucket_stamped else 'present'}]"
        )
        if dry_run:
            migrated += 1
            continue
        try:
            await store.update(new_doc.get("journey_id") or new_doc.get("use_case_id"), new_doc, user="migration")
            migrated += 1
        except Exception as e:
            conflicts += 1
            print(f"  ! {jid}: update failed -> {e}", file=sys.stderr)

    print()
    print(f"  migrated:  {migrated}")
    print(f"  skipped:   {skipped}")
    print(f"  conflicts: {conflicts}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert ${steps.X.y} params to ConnectionDocs.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return asyncio.run(_run(dry_run=args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
