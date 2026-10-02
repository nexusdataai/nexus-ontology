"""
Backfill AUTOMATION# rows from ``enterprise-knowledge/automation/`` YAMLs.

Idempotent: skips upsert when rows already exist unless ``--force`` is
passed. Safe to run against a live prod cluster (rows are additive).

Usage:

    python nexus-backend/scripts/migrations/backfill_automation_registry.py
    python nexus-backend/scripts/migrations/backfill_automation_registry.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from src.services.control_plane.automation_registry_service import (
    get_automation_registry,
)


def _default_root() -> Path:
    return Path(__file__).resolve().parents[2] / "enterprise-knowledge" / "automation"


async def _amain(root: Path, force: bool) -> int:
    reg = get_automation_registry()
    written = await reg.bootstrap_from_disk(root, force=force)
    print(f"Wrote {written} AUTOMATION# rows from {root}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(_default_root()))
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    return asyncio.run(_amain(Path(args.root), args.force))


if __name__ == "__main__":
    sys.exit(main())
