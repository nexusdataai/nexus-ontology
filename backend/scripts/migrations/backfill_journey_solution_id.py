"""
One-shot backfill of ``Data.solution_id`` on existing journey rows.

Each ``JOURNEY#<id>/METADATA`` item in the journeys DynamoDB table needs a
``Data.solution_id`` value so the Studio header can pick the right per-solution
KPI definition (label / icon / color) from
``src/services/journey_kpi_catalog.py``.

New journeys created after the deploy already carry ``solution_id`` directly
from the create dialogs. This script handles existing rows, deriving
``solution_id`` from a small mapping table keyed on the journey name (and
``odaComponentType`` as a tie-breaker for very generic names).

The mapping comes straight from the ``Create*Dialog.tsx`` files that produced
those rows in the first place:

    Order-to-Cash Monitor              -> order-to-cash
    Demand Forecasting Engine          -> demand-forecasting
    Inventory Optimization             -> inventory-optimization
    Procurement & Spend Analytics      -> procurement-analytics
    Production & Quality Copilot       -> production-quality
    Supply Chain Risk Radar            -> supply-chain-risk
    Customer 360 & Revenue Growth      -> customer-360
    ESG & Sustainability Tracker       -> esg-sustainability
    Knowledge Processor                -> semantic-rag (no KPI catalog row;
                                          falls back to _default at render time)
    everything else                    -> call-processing

Usage (inside a backend pod or any environment with the runtime env vars):

    # Dry run (default - prints planned changes)
    python3 scripts/migrations/backfill_journey_solution_id.py

    # Apply
    python3 scripts/migrations/backfill_journey_solution_id.py --apply

Env vars (mirrors manage_journey.py):
    DYNAMODB_TABLE       (default: ``TransformationSystem``)
    AWS_REGION           (default: ``us-east-1``)
    AWS_PROFILE          (optional; e.g. ``ptr-tech``)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Tuple


# ───────────────────────────── Derivation rules ───────────────────────────


def _derive_solution_id(name: Optional[str], oda_component: Optional[str]) -> str:
    """Map an existing journey row to a canonical solution_id.

    The order matters: more specific name patterns first; oda_component is
    only consulted as a final fallback.
    """
    n = (name or "").lower()
    oda = (oda_component or "").lower()

    if re.search(r"order[- ]to[- ]cash|\bo2c\b", n):
        return "order-to-cash"
    if re.search(r"demand[- ]forecast|forecasting engine", n):
        return "demand-forecasting"
    if re.search(r"inventory[- ]optimi[sz]ation|stock optimi", n):
        return "inventory-optimization"
    if re.search(r"procurement|spend analyt", n):
        return "procurement-analytics"
    if re.search(r"production.*quality|quality copilot", n):
        return "production-quality"
    if re.search(r"supply[- ]chain[- ]risk|risk radar", n):
        return "supply-chain-risk"
    if re.search(r"customer[- ]?360|revenue growth", n):
        return "customer-360"
    if re.search(r"\besg\b|sustainabilit", n):
        return "esg-sustainability"
    if re.search(r"semantic|\brag\b|knowledge[- ](processor|index)", n):
        # No catalog row yet; UI will render the _default fallback. Tag
        # explicitly so it is searchable later.
        return "semantic-rag"
    if oda == "data-pipeline" or re.search(r"\betl\b|data[- ]pipeline", n):
        # ETL/data-pipeline journeys: no catalog row, falls back to _default
        # "Items Processed" label which is the right neutral KPI for ETL.
        return "etl-pipeline"

    return "call-processing"


# ───────────────────────────── DynamoDB scan ──────────────────────────────


def _ddb_table():
    import boto3

    region = os.environ.get("AWS_REGION", "us-east-1")
    table_name = os.environ.get("DYNAMODB_TABLE", "TransformationSystem")

    profile = os.environ.get("AWS_PROFILE")
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
    else:
        session = boto3.Session(region_name=region)

    print(f"📋 Using DynamoDB table: {table_name} (region={region}, profile={profile or '<default>'})")
    return session.resource("dynamodb").Table(table_name)


def _iter_journey_metadata(table) -> List[Dict]:
    """Scan and return every JOURNEY#*/METADATA row."""
    items: List[Dict] = []
    last_key = None
    while True:
        kwargs = {
            "FilterExpression": "begins_with(PK, :pk_prefix) AND SK = :sk",
            "ExpressionAttributeValues": {":pk_prefix": "JOURNEY#", ":sk": "METADATA"},
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
    return items


# ─────────────────────────────── Update path ──────────────────────────────


def _plan_updates(items: List[Dict]) -> List[Tuple[str, str, str, str, Optional[str]]]:
    """Return list of (PK, journey_name, oda_component, derived_solution_id, existing_solution_id)."""
    rows: List[Tuple[str, str, str, str, Optional[str]]] = []
    for item in items:
        pk = item.get("PK", "")
        data = item.get("Data") or {}
        if not isinstance(data, dict):
            continue
        existing = data.get("solution_id")
        name = data.get("name") or ""
        oda = data.get("odaComponentType") or ""
        derived = _derive_solution_id(name, oda)
        rows.append((pk, name, oda, derived, existing))
    return rows


def _apply_updates(table, planned: List[Tuple[str, str, str, str, Optional[str]]]) -> int:
    written = 0
    for pk, name, oda, derived, existing in planned:
        if existing == derived:
            continue
        try:
            table.update_item(
                Key={"PK": pk, "SK": "METADATA"},
                UpdateExpression="SET #d.solution_id = :sid, UpdatedAt = :ts",
                ExpressionAttributeNames={"#d": "Data"},
                ExpressionAttributeValues={
                    ":sid": derived,
                    ":ts": _now_iso(),
                },
            )
            written += 1
            print(f"  ✅ {pk}: {name!r} → solution_id={derived}")
        except Exception as e:
            print(f"  ❌ {pk}: update failed: {e}")
    return written


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ─────────────────────────────────── CLI ──────────────────────────────────


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill Data.solution_id on existing journey rows in DynamoDB."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to DynamoDB. Without this flag, runs in dry-run mode.",
    )
    args = parser.parse_args(argv)

    table = _ddb_table()
    items = _iter_journey_metadata(table)
    print(f"📊 Found {len(items)} journey metadata rows")

    planned = _plan_updates(items)

    needs_update = [r for r in planned if r[4] != r[3]]
    already_set = [r for r in planned if r[4] == r[3]]

    print(f"   {len(already_set)} already have correct solution_id")
    print(f"   {len(needs_update)} need an update\n")

    if not needs_update:
        print("✅ Nothing to do.")
        return 0

    print("📋 Planned updates:")
    for pk, name, oda, derived, existing in needs_update:
        existing_repr = "<unset>" if existing is None else repr(existing)
        print(f"  {pk}  name={name!r}  oda={oda!r}  {existing_repr} → {derived!r}")

    if not args.apply:
        print("\nDry-run (default). Re-run with --apply to write.")
        return 0

    print("\n💾 Applying updates...")
    written = _apply_updates(table, needs_update)
    print(f"\n✅ Wrote {written} of {len(needs_update)} planned updates.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
