from __future__ import annotations

from src.constants.nifi_processor_seeds import (
    live_processor_ids,
    load_processor_seeds,
    nifi_catalog_nodes,
)
from src.constants.etl_step_catalog import PIPELINE_NODE_CATALOG
from src.services.data_flow_service import get_catalog


def test_seeds_loaded():
    seeds = load_processor_seeds()
    assert len(seeds) >= 100
    live = live_processor_ids()
    assert "nifi.UpdateAttribute" in live
    assert "nifi.ConvertRecord" in live


def test_catalog_union():
    cat = get_catalog()
    types = {n["type"] for n in cat["nodeTypes"]}
    assert "source.fdw" in types
    assert "nifi.UpdateAttribute" in types
    assert cat.get("nifiProcessorCount", 0) >= 100
    assert len(cat["nodeTypes"]) == len(PIPELINE_NODE_CATALOG) + len(nifi_catalog_nodes())