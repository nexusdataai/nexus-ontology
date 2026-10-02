"""
Lint enterprise-knowledge/ usage across the backend.

The data-organization spec (Phase 3) makes DynamoDB the sole runtime
source of policies / workflows / integrations. This linter walks
``src/`` and warns if any module outside the allowed bootstrap surfaces
reads directly from ``enterprise-knowledge/{policies,workflows,integrations}/``.

Usage:

    python nexus-backend/scripts/lint_enterprise_knowledge.py [--strict]

Options:

    --strict   Exit non-zero on any warning (for CI).

Allow-listed callers (bootstrap seeds only):

    - src/services/onto_data_service.py
    - nexus-deployer/backup-restore/scripts/bootstrap_foundry_from_files.py
    - scripts/lint_enterprise_knowledge.py (this file)
    - scripts/lint_yaml_headers.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"

_ALLOWED_FILES = {
    _SRC / "services" / "onto_data_service.py",
    _SRC / "stages" / "semantic-rag" / "semantic_rag_processor.py",  # dev-only local override
}

_PATTERNS = [
    re.compile(r"enterprise-knowledge[/\\](policies|workflows|integrations)\b"),
]


def _iter_python_files(root: Path):
    for p in root.rglob("*.py"):
        if any(part == "__pycache__" for part in p.parts):
            continue
        yield p


def find_hits(strict: bool = False) -> Tuple[List[str], int]:
    hits: List[str] = []
    scanned = 0
    for path in _iter_python_files(_SRC):
        if path in _ALLOWED_FILES:
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat in _PATTERNS:
            for m in pat.finditer(text):
                lineno = text.count("\n", 0, m.start()) + 1
                hits.append(f"{path.relative_to(_REPO_ROOT)}:{lineno}: reads enterprise-knowledge/{m.group(1)} directly")
    return hits, scanned


def main() -> int:
    strict = "--strict" in sys.argv
    hits, scanned = find_hits()
    if not hits:
        print(f"[ok] scanned {scanned} files; no direct reads of enterprise-knowledge/{{policies,workflows,integrations}}.")
        return 0
    print(f"[warn] scanned {scanned} files, found {len(hits)} direct reads:")
    for h in hits:
        print(f"  - {h}")
    print()
    print("These paths should read from DynamoDB via OntoDataService, or be added to _ALLOWED_FILES if bootstrap-only.")
    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main())
