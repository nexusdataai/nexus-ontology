from __future__ import annotations

from src.constants.etl_step_catalog import PIPELINE_NODE_CATALOG
from src.constants.flow_processor_seeds import (
    live_processor_ids,
    load_processor_seeds,
    nexus_catalog_nodes,
)
from src.services.data_flow_service import get_catalog


def test_seeds_loaded():
    seeds = load_processor_seeds()
    assert len(seeds) == 117
    live = live_processor_ids()
    assert "nexus.UpdateAttribute" in live
    assert "nexus.ConvertRecord" in live


def test_catalog_union():
    cat = get_catalog()
    types = {n["type"] for n in cat["nodeTypes"]}
    assert "source.fdw" in types
    assert "nexus.UpdateAttribute" in types
    assert cat.get("flowProcessorCount", 0) == 117
    assert len(cat["nodeTypes"]) == len(PIPELINE_NODE_CATALOG) + len(nexus_catalog_nodes())