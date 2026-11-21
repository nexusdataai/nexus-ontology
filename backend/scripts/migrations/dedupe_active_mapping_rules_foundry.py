"""
Dedupe active mapping rules in foundry-workspace (DynamoDB).

Usage:
    cd nexus-ontology/backend && python scripts/migrations/dedupe_active_mapping_rules_foundry.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


async def main() -> int:
    from src.services.mapping_rule_service import MappingRuleService

    svc = MappingRuleService()
    await svc.initialize()
    summary = await svc.dedupe_active_rules()
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))