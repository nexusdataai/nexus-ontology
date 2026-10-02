#!/usr/bin/env python3
"""
Migrate dashboards from S3 (legacy DashboardService storage) into the
foundry-workspace DynamoDB table.

Reads each `{prefix}{uid}.json` object from the configured dashboards bucket
and writes it as a DASHBOARD#{uid} / META item via FoundryWorkspaceRepository.
Idempotent: existing items in DDB are skipped unless --force is passed.

Usage:
    python scripts/migrate_dashboards_s3_to_ddb.py [--dry-run] [--force]
                                                   [--bucket NAME] [--prefix dashboards/]
                                                   [--table NAME]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Make `src.*` importable when executed from the repo root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import boto3  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

from src.repositories.foundry_workspace_repository import (  # noqa: E402
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
    dashboard_pk,
)


def _resolve_bucket(arg_bucket: Optional[str]) -> str:
    if arg_bucket:
        return arg_bucket
    env_val = os.getenv("DASHBOARD_S3_BUCKET", "")
    if env_val:
        return env_val
    try:
        from src.config.config_provider import get_config
        return get_config().s3_dashboards_bucket or ""
    except Exception:
        return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate dashboards S3 -> DynamoDB")
    parser.add_argument("--bucket", help="Source S3 bucket (default: config.s3_dashboards_bucket)")
    parser.add_argument("--prefix", default=os.getenv("DASHBOARD_S3_PREFIX", "dashboards/"))
    parser.add_argument("--table", help="Target DDB table (default: config.dynamodb_foundry_workspace_table)")
    parser.add_argument("--dry-run", action="store_true", help="List actions without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing DDB items")
    args = parser.parse_args()

    bucket = _resolve_bucket(args.bucket)
    if not bucket:
        print("ERROR: No source S3 bucket resolved (set DASHBOARD_S3_BUCKET or pass --bucket).", file=sys.stderr)
        return 2

    repo = FoundryWorkspaceRepository(table_name=args.table)
    s3 = boto3.client("s3")

    print(f"Source: s3://{bucket}/{args.prefix}")
    print(f"Target: dynamodb table {repo.table_name}")
    print(f"Mode:   {'DRY-RUN' if args.dry_run else 'WRITE'}{' (force overwrite)' if args.force else ''}")
    print("-" * 60)

    inspected = 0
    migrated = 0
    skipped = 0
    failed = 0

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=args.prefix):
        for obj in page.get("Contents", []) or []:
            key = obj["Key"]
            if not key.endswith(".json"):
                continue
            inspected += 1
            uid = key[len(args.prefix):].replace(".json", "")
            try:
                resp = s3.get_object(Bucket=bucket, Key=key)
                data = json.loads(resp["Body"].read())
            except (ClientError, ValueError) as e:
                print(f"FAIL  {uid}: read error: {e}")
                failed += 1
                continue

            data["uid"] = uid

            existing = None
            try:
                existing = repo.get_meta(dashboard_pk(uid))
            except FoundryWorkspaceRepositoryError as e:
                print(f"FAIL  {uid}: ddb get error: {e}")
                failed += 1
                continue

            if existing and not args.force:
                print(f"SKIP  {uid}: already in ddb")
                skipped += 1
                continue

            attrs = {
                "uid": uid,
                "title": data.get("title", ""),
                "description": data.get("description"),
                "tags": list(data.get("tags") or []),
                "panelCount": len(data.get("panels") or []),
                "version": int(data.get("version", 1) or 1),
                "createdAt": data.get("createdAt", ""),
                "updatedAt": data.get("updatedAt", ""),
                "createdBy": data.get("createdBy", ""),
                # JSON string avoids DDB's float rejection on nested dicts.
                "payloadJson": json.dumps(data, default=str),
            }

            if args.dry_run:
                print(f"DRY   {uid}: would write ({len(data.get('panels') or [])} panels)")
                migrated += 1
                continue

            try:
                repo.put_meta(
                    pk=dashboard_pk(uid),
                    attrs=attrs,
                    gsi1pk="DASHBOARD",
                    gsi1sk=data.get("updatedAt", ""),
                )
                print(f"OK    {uid}: migrated")
                migrated += 1
            except FoundryWorkspaceRepositoryError as e:
                print(f"FAIL  {uid}: ddb write error: {e}")
                failed += 1

    print("-" * 60)
    print(f"Inspected: {inspected}")
    print(f"Migrated:  {migrated}")
    print(f"Skipped:   {skipped}")
    print(f"Failed:    {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
