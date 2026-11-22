"""Load flow processor catalog seeds from enterprise-knowledge/flow-processors/."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Set

from src.constants.registered_flow_processors import registered_flow_processor_ids
from src.services.flow_runtime.processor_ids import canonical_processor_id

_SEED_DIR = Path(__file__).resolve().parents[2] / "enterprise-knowledge" / "flow-processors"


def nexus_bundle_name(raw: str | None) -> str:
    if not raw:
        return "unknown"
    if raw.startswith("nifi-"):
        return "nexus-" + raw[5:]
    return raw


def normalize_processor_seed(seed: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(seed)
    out["processorId"] = canonical_processor_id(out.get("processorId", ""))
    out["bundle"] = nexus_bundle_name(seed.get("bundle"))
    out["category"] = "nexus"
    out.pop("nifiClass", None)
    return out


@lru_cache(maxsize=1)
def load_processor_seeds() -> List[Dict[str, Any]]:
    path = _SEED_DIR / "processors.json"
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    allowed = registered_flow_processor_ids()
    out = [normalize_processor_seed(s) for s in raw if normalize_processor_seed(s)["processorId"] in allowed]
    for pid in sorted(allowed):
        if not any(p["processorId"] == pid for p in out):
            short = pid.split(".", 1)[-1]
            out.append(
                normalize_processor_seed(
                    {
                        "processorId": pid,
                        "label": short,
                        "bundle": "nexus-standard-bundle",
                        "description": f"Nexus Python processor {short}.",
                        "properties": [],
                        "relationships": [{"name": "success"}, {"name": "failure"}],
                        "runtime": "live",
                    }
                )
            )
    return out


@lru_cache(maxsize=1)
def load_asset_seeds() -> List[Dict[str, Any]]:
    path = _SEED_DIR / "assets.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def live_processor_ids() -> Set[str]:
    return set(registered_flow_processor_ids())


def stub_processor_ids() -> Set[str]:
    return {p["processorId"] for p in load_processor_seeds() if p.get("runtime") != "live"}


def processor_seed(processor_id: str) -> Dict[str, Any] | None:
    want = canonical_processor_id(processor_id)
    for p in load_processor_seeds():
        if p.get("processorId") == want:
            return p
    return None


def seed_to_catalog_node(seed: Dict[str, Any]) -> Dict[str, Any]:
    tags = seed.get("tags") or []
    category = "transform"
    if any(t in {"route", "routing"} for t in tags) or "Route" in seed.get("label", ""):
        category = "route"
    norm = normalize_processor_seed(seed)
    return {
        "type": norm["processorId"],
        "category": category,
        "label": norm.get("label") or norm["processorId"],
        "description": norm.get("description") or "",
        "icon": "shuffle",
        "defaultParams": _default_params(norm),
        "mapsToRuntimeStep": None,
        "runtime": norm.get("runtime", "python-stub"),
        "properties": norm.get("properties") or [],
        "relationships": norm.get("relationships") or [{"name": "success"}, {"name": "failure"}],
    }


def nexus_catalog_nodes() -> List[Dict[str, Any]]:
    return [seed_to_catalog_node(s) for s in load_processor_seeds()]


def _default_params(norm: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for prop in norm.get("properties") or []:
        name = prop.get("name") or prop.get("displayName")
        if not name:
            continue
        if "defaultValue" in prop:
            out[name] = prop["defaultValue"]
    return out