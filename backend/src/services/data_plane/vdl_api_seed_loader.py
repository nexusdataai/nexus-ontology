"""
Load ``enterprise-knowledge/vdl-apis/*.yaml`` into ``VdlApiSpec`` objects for
bootstrapping the DDB registry.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

import yaml
from loguru import logger

from src.models.vdl_api_models import DirectSqlBinding, ImplBinding, VdlApiSpec


def _seed_dir() -> Path:
    override = os.getenv("VDL_API_SEED_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "enterprise-knowledge" / "vdl-apis"


def load_seed_specs() -> List[VdlApiSpec]:
    """Read all YAML files under the seed directory and return a list of
    ``VdlApiSpec`` instances. Malformed files are skipped with a warning."""
    seed_dir = _seed_dir()
    if not seed_dir.is_dir():
        logger.debug(f"VDL API seed dir missing: {seed_dir}")
        return []
    out: List[VdlApiSpec] = []
    for yml in sorted(seed_dir.glob("*.yaml")):
        try:
            with yml.open("r") as fh:
                raw = yaml.safe_load(fh) or {}
            impl = [ImplBinding(**b) for b in (raw.get("impl") or [])]
            direct_sql = (
                DirectSqlBinding(**raw["direct_sql"])
                if isinstance(raw.get("direct_sql"), dict)
                else None
            )
            spec = VdlApiSpec(
                api_id=str(raw.get("api_id") or yml.stem),
                verb=str(raw.get("verb") or "read"),
                virtual_entity=str(raw.get("virtual_entity") or ""),
                parameters_schema=dict(raw.get("parameters_schema") or {}),
                impl=impl,
                direct_sql=direct_sql,
                risk_level=str(raw.get("risk_level") or "read_only"),
                description=str(raw.get("description") or ""),
                tags=list(raw.get("tags") or []),
            )
            out.append(spec)
        except Exception as e:
            logger.warning(f"VDL API seed parse failed for {yml}: {e}")
    return out
