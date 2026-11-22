"""Canonical Nexus flow processor identifiers (pure Python catalog)."""
from __future__ import annotations


def canonical_processor_id(processor_id: str) -> str:
    """Map legacy harvested ids to Nexus ids."""
    if processor_id.startswith("nifi."):
        return "nexus." + processor_id[5:]
    return processor_id


def processor_short_name(processor_id: str) -> str:
    cid = canonical_processor_id(processor_id)
    if "." in cid:
        return cid.split(".", 1)[1]
    return cid