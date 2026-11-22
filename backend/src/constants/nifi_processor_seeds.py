"""Load harvested NiFi processor seeds from enterprise-knowledge/nifi/."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Set

_SEED_DIR = Path(__file__).resolve().parents[2] / "enterprise-knowledge" / "nifi"


def nexus_bundle_name(raw: str | None) -> str:
    """Display harvested Apache NiFi NAR names as Nexus bundle names."""
    if not raw:
        return "unknown"
    if raw.startswith("nifi-"):
        return "nexus-" + raw[5:]
    return raw


def normalize_processor_seed(seed: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(seed)
    out["bundle"] = nexus_bundle_name(seed.get("bundle"))
    out["category"] = "nexus"
    return out


@lru_cache(maxsize=1)
def load_processor_seeds() -> List[Dict[str, Any]]:
    path = _SEED_DIR / "processors.json"
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [normalize_processor_seed(s) for s in raw]


@lru_cache(maxsize=1)
def load_asset_seeds() -> List[Dict[str, Any]]:
    path = _SEED_DIR / "assets.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def live_processor_ids() -> Set[str]:
    return {p["processorId"] for p in load_processor_seeds() if p.get("runtime") == "live"}


def stub_processor_ids() -> Set[str]:
    return {p["processorId"] for p in load_processor_seeds() if p.get("runtime") == "stub"}


def processor_seed(processor_id: str) -> Dict[str, Any] | None:
    for p in load_processor_seeds():
        if p.get("processorId") == processor_id:
            return p
    return None


def seed_to_catalog_node(seed: Dict[str, Any]) -> Dict[str, Any]:
    """Map a NiFi seed into Pipeline Studio catalog node shape."""
    tags = seed.get("tags") or []
    category = "transform"
    if any(t in {"route", "routing"} for t in tags) or "Route" in seed.get("label", ""):
        category = "route"
    elif any(t in {"split", "merge"} for t in tags):
        category = "transform"
    norm = normalize_processor_seed(seed)
    return {
        "type": norm["processorId"],
        "category": category,
        "label": norm.get("label") or norm["processorId"],
        "description": norm.get("description") or "",
        "icon": "shuffle",
        "defaultParams": _default_params(norm),
        "mapsToRuntimeStep": None,
        "runtime": norm.get("runtime", "stub"),
        "nifiClass": norm.get("nifiClass"),
        "properties": norm.get("properties") or [],
        "relationships": norm.get("relationships") or [{"name": "success"}, {"name": "failure"}],
        "bundle": norm.get("bundle"),
    }


def _default_params(seed: Dict[str, Any]) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for prop in seed.get("properties") or []:
        name = prop.get("name")
        if name:
            params[name] = prop.get("default", "")
    return params


def nifi_catalog_nodes() -> List[Dict[str, Any]]:
    return [seed_to_catalog_node(s) for s in load_processor_seeds()]