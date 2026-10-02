"""
Rename the 13 Oracle-prefixed virtual entity names to their product-agnostic
short names in the semantic layer.

This is the data-side companion to the schema/code rename:

    Oracle_AR_Customer     -> AR_Customer
    Oracle_AR_Invoice      -> AR_Invoice
    Oracle_AR_Payment      -> AR_Payment
    Oracle_AR_Credit_Note  -> AR_Credit_Note
    Oracle_GL_Journal      -> GL_Journal
    Oracle_GL_Period       -> GL_Period
    Oracle_AP_Invoice      -> AP_Invoice
    Oracle_AP_Payment      -> AP_Payment
    Oracle_Purchase_Order  -> Purchase_Order
    Oracle_Cost_Accounting -> Cost_Accounting
    Oracle_Fixed_Asset     -> Fixed_Asset
    Oracle_Budget          -> Budget
    Oracle_Product_Master  -> Product_Master

Mapping rules are rewritten so that ``virtualEntity`` carries the new short
name. ``sourceTable`` / ``sourceSchema`` / ``sourceSystem`` / ``fieldMaps``
are NOT touched because the physical Oracle tables (e.g. ``Oracle_AR_Invoice``
in ``oracle_erp``) keep their original names.

Saved dashboards in the Foundry workspace DynamoDB table are also rewritten:
panel ``targets[].entity`` and any other ``entity`` field that holds a legacy
name is updated, payloads >256 KB stored in S3 are fetched, rewritten, and put
back.

Usage (inside a backend pod or any environment with the runtime env vars):

    # Dry run (default - prints planned changes)
    python3 scripts/migrations/rename_oracle_virtual_entities.py

    # Apply
    python3 scripts/migrations/rename_oracle_virtual_entities.py --apply

    # Limit to one surface
    python3 scripts/migrations/rename_oracle_virtual_entities.py --only mapping_rules
    python3 scripts/migrations/rename_oracle_virtual_entities.py --only dashboards

The script picks PostgreSQL for ``mapping_rules`` when ``FDW_PG_HOST`` is set,
otherwise DynamoDB (``MAPPING_RULES_TABLE_NAME`` env var, default
``mapping-rules``). Dashboards always go through the Foundry workspace
DynamoDB table (``FOUNDRY_WORKSPACE_TABLE`` env var).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


RENAME_MAP: Dict[str, str] = {
    "Oracle_AR_Customer":     "AR_Customer",
    "Oracle_AR_Invoice":      "AR_Invoice",
    "Oracle_AR_Payment":      "AR_Payment",
    "Oracle_AR_Credit_Note":  "AR_Credit_Note",
    "Oracle_GL_Journal":      "GL_Journal",
    "Oracle_GL_Period":       "GL_Period",
    "Oracle_AP_Invoice":      "AP_Invoice",
    "Oracle_AP_Payment":      "AP_Payment",
    "Oracle_Purchase_Order":  "Purchase_Order",
    "Oracle_Cost_Accounting": "Cost_Accounting",
    "Oracle_Fixed_Asset":     "Fixed_Asset",
    "Oracle_Budget":          "Budget",
    "Oracle_Product_Master":  "Product_Master",
}


# ───────────────────────────── Mapping rules ──────────────────────────────

def _pg_engine():
    from sqlalchemy import create_engine
    host = os.getenv("FDW_PG_HOST", "")
    port = os.getenv("FDW_PG_PORT", "5432")
    db = os.getenv("FDW_PG_DATABASE", "")
    user = os.getenv("FDW_PG_USER", "")
    pw = os.getenv("FDW_PG_PASSWORD", "")
    if not host or not db:
        return None
    url = f"postgresql://{user}:{pw}@{host}:{port}/{db}"
    return create_engine(url, pool_size=2, max_overflow=2)


def _migrate_mapping_rules_pg(apply: bool) -> Dict[str, int]:
    from sqlalchemy import text

    engine = _pg_engine()
    assert engine is not None
    summary = {"scanned": 0, "renamed_entities": 0, "renamed_names": 0}

    select_sql = text(
        "SELECT id, data FROM mapping_rules "
        "WHERE data->>'virtualEntity' = ANY(:names)"
    )
    # Cast :data via the bindparam so PostgreSQL `::jsonb` cast operator
    # cannot collide with the SQLAlchemy bind syntax.
    update_sql = text(
        "UPDATE mapping_rules SET data = cast(:data as jsonb) WHERE id = :rule_id"
    )

    with engine.connect() as conn:
        rows = conn.execute(
            select_sql, {"names": list(RENAME_MAP.keys())}
        ).fetchall()

        plan: List[Tuple[str, str, str, str, str, Dict[str, Any]]] = []
        for r in rows:
            data = r.data if isinstance(r.data, dict) else json.loads(r.data)
            old_ve = data.get("virtualEntity") or ""
            new_ve = RENAME_MAP.get(old_ve)
            if not new_ve:
                continue
            old_name = data.get("name") or ""
            new_name = old_name
            old_auto = f"Auto: {old_ve}"
            new_auto = f"Auto: {new_ve}"
            if old_name == old_auto:
                new_name = new_auto
            new_data = dict(data)
            new_data["virtualEntity"] = new_ve
            if new_name != old_name:
                new_data["name"] = new_name
            plan.append((r.id, old_ve, new_ve, old_name, new_name, new_data))

        summary["scanned"] = len(rows)
        summary["renamed_entities"] = len(plan)
        summary["renamed_names"] = sum(
            1 for _, _, _, on, nn, _ in plan if on != nn
        )

        print(f"[mapping_rules:pg] matched {len(rows)} rows for rename")
        for rule_id, old_ve, new_ve, old_name, new_name, _ in plan[:25]:
            tag = "" if old_name == new_name else f"  name: {old_name} -> {new_name}"
            print(f"  {rule_id}  {old_ve:25} -> {new_ve}{tag}")
        if len(plan) > 25:
            print(f"  ... ({len(plan) - 25} more)")

        if not apply:
            return summary

        for rule_id, _, _, _, _, new_data in plan:
            conn.execute(update_sql, {
                "rule_id": rule_id,
                "data": json.dumps(new_data),
            })
        conn.commit()
        print(f"[mapping_rules:pg] applied: rewrote {len(plan)} rules")
    return summary


def _migrate_mapping_rules_ddb(apply: bool) -> Dict[str, int]:
    import boto3
    from boto3.dynamodb.conditions import Attr

    table_name = os.getenv("MAPPING_RULES_TABLE_NAME", "mapping-rules")
    endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL") or os.environ.get(
        "AWS_ENDPOINT_URL_DYNAMODB"
    )
    region = os.environ.get("AWS_REGION") or os.environ.get(
        "AWS_DEFAULT_REGION"
    ) or "us-east-1"
    if endpoint_url:
        ddb = boto3.resource("dynamodb", endpoint_url=endpoint_url, region_name=region)
    else:
        ddb = boto3.resource("dynamodb", region_name=region)
    table = ddb.Table(table_name)

    summary = {"scanned": 0, "renamed_entities": 0, "renamed_names": 0}
    plan: List[Tuple[str, str, str, str, str, Dict[str, Any]]] = []

    last_key: Optional[Dict[str, Any]] = None
    while True:
        kwargs: Dict[str, Any] = {
            "FilterExpression": Attr("virtualEntity").is_in(list(RENAME_MAP.keys())),
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        resp = table.scan(**kwargs)
        for item in resp.get("Items", []):
            old_ve = str(item.get("virtualEntity") or "")
            new_ve = RENAME_MAP.get(old_ve)
            if not new_ve:
                continue
            old_name = str(item.get("name") or "")
            new_name = old_name
            if old_name == f"Auto: {old_ve}":
                new_name = f"Auto: {new_ve}"
            plan.append((item["id"], old_ve, new_ve, old_name, new_name, item))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break

    summary["scanned"] = len(plan)
    summary["renamed_entities"] = len(plan)
    summary["renamed_names"] = sum(1 for _, _, _, on, nn, _ in plan if on != nn)

    print(f"[mapping_rules:ddb] matched {len(plan)} items for rename")
    for rule_id, old_ve, new_ve, old_name, new_name, _ in plan[:25]:
        tag = "" if old_name == new_name else f"  name: {old_name} -> {new_name}"
        print(f"  {rule_id}  {old_ve:25} -> {new_ve}{tag}")
    if len(plan) > 25:
        print(f"  ... ({len(plan) - 25} more)")

    if not apply:
        return summary

    for rule_id, _, new_ve, _, new_name, _ in plan:
        table.update_item(
            Key={"id": rule_id},
            UpdateExpression="SET virtualEntity = :ve, #n = :nm",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":ve": new_ve, ":nm": new_name},
        )
    print(f"[mapping_rules:ddb] applied: rewrote {len(plan)} rules")
    return summary


# ───────────────────────────── Dashboards ─────────────────────────────────

def _rewrite_entity_strings(node: Any) -> Tuple[Any, int]:
    """Recursively walk a dashboard payload and rewrite entity values that
    match a legacy Oracle_* name. Returns (new_node, hits)."""
    if isinstance(node, dict):
        hits = 0
        new_d: Dict[str, Any] = {}
        for k, v in node.items():
            if (
                k == "entity"
                and isinstance(v, str)
                and v in RENAME_MAP
            ):
                new_d[k] = RENAME_MAP[v]
                hits += 1
            elif (
                k in ("virtualEntity", "virtual_entity")
                and isinstance(v, str)
                and v in RENAME_MAP
            ):
                new_d[k] = RENAME_MAP[v]
                hits += 1
            else:
                nv, h = _rewrite_entity_strings(v)
                new_d[k] = nv
                hits += h
        return new_d, hits
    if isinstance(node, list):
        out: List[Any] = []
        hits = 0
        for it in node:
            nv, h = _rewrite_entity_strings(it)
            out.append(nv)
            hits += h
        return out, hits
    return node, 0


def _foundry_repo():
    from src.repositories.foundry_workspace_repository import (
        FoundryWorkspaceRepository,
    )
    return FoundryWorkspaceRepository()


def _migrate_dashboards(apply: bool) -> Dict[str, int]:
    summary = {"scanned": 0, "rewritten": 0, "hits": 0, "s3_rewritten": 0}

    repo = _foundry_repo()
    try:
        rows = repo.query_gsi1("DASHBOARD", scan_forward=False)
    except Exception as e:
        print(f"[dashboards] list failed: {e}")
        return summary

    summary["scanned"] = len(rows)
    print(f"[dashboards] scanning {len(rows)} dashboards in {repo.table_name}")

    plan: List[Tuple[str, str, int, Optional[str]]] = []  # (uid, pk, hits, s3Ref)
    rewritten_payloads: Dict[str, str] = {}

    for row in rows:
        uid = row.get("uid") or row.get("PK", "").replace("DASHBOARD#", "")
        pk = row.get("PK")
        s3_ref = row.get("s3Ref")
        payload_json = row.get("payloadJson")

        if s3_ref and not payload_json:
            payload_json = _read_s3(s3_ref)
            if payload_json is None:
                continue

        if not payload_json:
            continue

        try:
            data = json.loads(payload_json)
        except Exception as e:
            print(f"  [skip] {uid}: payloadJson parse failed: {e}")
            continue

        new_data, hits = _rewrite_entity_strings(data)
        if hits == 0:
            continue
        plan.append((uid, pk, hits, s3_ref))
        rewritten_payloads[uid] = json.dumps(new_data, default=str)
        summary["hits"] += hits

    summary["rewritten"] = len(plan)
    print(f"[dashboards] {len(plan)} dashboards have legacy entity refs "
          f"({summary['hits']} string rewrites)")
    for uid, _, hits, s3_ref in plan[:25]:
        loc = "S3" if s3_ref else "DDB"
        print(f"  {uid}  hits={hits:3}  store={loc}")
    if len(plan) > 25:
        print(f"  ... ({len(plan) - 25} more)")

    if not apply:
        return summary

    rows_by_pk = {r.get("PK"): r for r in rows}
    for uid, pk, _, s3_ref in plan:
        new_payload = rewritten_payloads[uid]
        if s3_ref:
            ok = _write_s3(s3_ref, new_payload)
            if ok:
                summary["s3_rewritten"] += 1
            else:
                print(f"  [warn] {uid}: failed to rewrite S3 overflow at {s3_ref}")
                continue

        existing = rows_by_pk.get(pk) or {}
        attrs = {
            k: v for k, v in existing.items()
            if k not in ("PK", "SK", "GSI1PK", "GSI1SK")
        }
        if not s3_ref:
            attrs["payloadJson"] = new_payload
        attrs["updatedAt"] = _now_iso()
        try:
            repo.put_meta(
                pk=pk,
                attrs=attrs,
                gsi1pk=existing.get("GSI1PK", "DASHBOARD"),
                gsi1sk=attrs["updatedAt"],
            )
        except Exception as e:
            print(f"  [warn] {uid}: put_meta failed: {e}")
    print(f"[dashboards] applied: rewrote {len(plan)} dashboards "
          f"({summary['s3_rewritten']} via S3)")
    return summary


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _read_s3(s3_uri: str) -> Optional[str]:
    try:
        import boto3
        if not s3_uri.startswith("s3://"):
            return None
        rest = s3_uri[5:]
        bucket, _, key = rest.partition("/")
        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read().decode("utf-8")
    except Exception as e:
        print(f"  [warn] S3 read failed {s3_uri}: {e}")
        return None


def _write_s3(s3_uri: str, body: str) -> bool:
    try:
        import boto3
        if not s3_uri.startswith("s3://"):
            return False
        rest = s3_uri[5:]
        bucket, _, key = rest.partition("/")
        s3 = boto3.client("s3")
        s3.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"))
        return True
    except Exception as e:
        print(f"  [warn] S3 write failed {s3_uri}: {e}")
        return False


# ───────────────────────────── Entrypoint ─────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually rewrite rows. Default is a dry run.",
    )
    parser.add_argument(
        "--only", choices=["mapping_rules", "dashboards"], default=None,
        help="Limit migration to one surface. Default runs both.",
    )
    args = parser.parse_args()

    if not args.only or args.only == "mapping_rules":
        if os.getenv("FDW_PG_HOST"):
            try:
                _migrate_mapping_rules_pg(apply=args.apply)
            except Exception as e:
                print(f"[mapping_rules:pg] failed: {e}", file=sys.stderr)
                return 2
        else:
            try:
                _migrate_mapping_rules_ddb(apply=args.apply)
            except Exception as e:
                print(f"[mapping_rules:ddb] failed: {e}", file=sys.stderr)
                return 2

    if not args.only or args.only == "dashboards":
        try:
            _migrate_dashboards(apply=args.apply)
        except Exception as e:
            print(f"[dashboards] failed: {e}", file=sys.stderr)
            return 2

    if not args.apply:
        print()
        print("Dry run - no changes. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
