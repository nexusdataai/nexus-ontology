#!/usr/bin/env python3
"""Phase 1 -- stamp ``bucket:`` onto every JourneyDoc YAML on disk.

Walks ``enterprise-knowledge/automation/<solution>/*.yaml`` and inserts a
``bucket:`` header right after ``solution_id:`` (preserving original key
order and comments via the ``ruamel.yaml`` round-trip parser when
available). Mapping from ``solution_id`` -> bucket mirrors the live tool
registry's bucket assignments.

Idempotent: a file that already declares ``bucket:`` is skipped. Files
that don't parse, or whose solution_id is unknown, are skipped with a
warning.

Usage:
  python scripts/migrations/rewrite_yaml_to_dataflow_format.py --dry-run
  python scripts/migrations/rewrite_yaml_to_dataflow_format.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# ``solution_id`` -> bucket. Mirrors the live ToolRegistry assignments
# stamped by each ``register_*_tools`` function.
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


def _resolve_bucket(solution_id: str) -> Optional[str]:
    return SOLUTION_TO_BUCKET.get(solution_id)


def _round_trip_loader():
    """Prefer ``ruamel.yaml`` so comments + key order survive; fall back to PyYAML."""
    try:
        from ruamel.yaml import YAML  # type: ignore

        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.width = 4096
        yaml.indent(mapping=2, sequence=4, offset=2)
        return ("ruamel", yaml)
    except Exception:
        import yaml  # type: ignore

        return ("pyyaml", yaml)


def _process_file(path: Path, *, dry_run: bool) -> str:
    """Returns one of: ``stamped``, ``skipped_present``, ``skipped_unknown_solution``,
    ``skipped_no_solution``, ``skipped_parse_error``.
    """
    flavour, loader = _round_trip_loader()
    text = path.read_text()
    try:
        if flavour == "ruamel":
            doc = loader.load(text)
        else:
            doc = loader.safe_load(text)
    except Exception as e:
        print(f"  ! {path.relative_to(path.parents[3])}: parse error -> {e}", file=sys.stderr)
        return "skipped_parse_error"

    if not isinstance(doc, dict):
        return "skipped_parse_error"

    if "bucket" in doc:
        return "skipped_present"

    solution_id = doc.get("solution_id")
    if not solution_id:
        return "skipped_no_solution"

    bucket = _resolve_bucket(str(solution_id))
    if not bucket:
        print(
            f"  ? {path.relative_to(path.parents[3])}: unknown solution_id '{solution_id}', skipping",
            file=sys.stderr,
        )
        return "skipped_unknown_solution"

    # Insert ``bucket`` right after ``solution_id`` to keep the header
    # block contiguous and readable. ruamel preserves the rest of the
    # mapping; PyYAML re-emits without comments.
    if flavour == "ruamel":
        # ruamel CommentedMap supports ``insert(pos, key, value, comment=...)``.
        # Find the index of ``solution_id`` and insert just after it.
        keys = list(doc.keys())
        try:
            idx = keys.index("solution_id") + 1
        except ValueError:
            idx = len(keys)
        doc.insert(idx, "bucket", bucket, comment="Phase 1 registry bucket")
    else:
        # PyYAML loses comments + ordering on emit; insert key into the
        # dict and accept the round-trip cost. ``dict`` is ordered in
        # CPython 3.7+ so order is preserved if we rebuild.
        rebuilt = {}
        for k, v in doc.items():
            rebuilt[k] = v
            if k == "solution_id":
                rebuilt["bucket"] = bucket
        doc = rebuilt

    if dry_run:
        return "stamped"

    if flavour == "ruamel":
        import io

        buf = io.StringIO()
        loader.dump(doc, buf)
        path.write_text(buf.getvalue())
    else:
        path.write_text(loader.safe_dump(doc, sort_keys=False))
    return "stamped"


def main() -> int:
    parser = argparse.ArgumentParser(description="Stamp bucket: on Journey YAML files.")
    parser.add_argument("--dry-run", action="store_true", help="Report counts without writing.")
    parser.add_argument(
        "--root",
        default="enterprise-knowledge/automation",
        help="Root directory to walk (relative to the backend root).",
    )
    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parents[2]
    root = (backend_root / args.root).resolve()
    if not root.exists():
        print(f"error: {root} does not exist", file=sys.stderr)
        return 2

    counts = {
        "stamped": 0,
        "skipped_present": 0,
        "skipped_no_solution": 0,
        "skipped_unknown_solution": 0,
        "skipped_parse_error": 0,
    }
    files = sorted(root.rglob("*.yaml"))
    print(f"Walking {len(files)} YAML files under {root}{' (dry-run)' if args.dry_run else ''}")
    for f in files:
        outcome = _process_file(f, dry_run=args.dry_run)
        counts[outcome] += 1
        prefix = "+" if outcome == "stamped" else "."
        print(f"  {prefix} {f.relative_to(backend_root)}  [{outcome}]")

    print()
    for k, v in counts.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
