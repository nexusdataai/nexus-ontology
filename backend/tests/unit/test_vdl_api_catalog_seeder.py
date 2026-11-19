from src.services.data_plane.vdl_api_catalog_seeder import build_catalog_read_specs


def test_build_catalog_read_specs_non_empty():
    specs = build_catalog_read_specs()
    assert len(specs) >= 50
    ids = {s.api_id for s in specs}
    assert "vdl.price_book_entry.list" in ids or "vdl.pricebookentry.list" in ids
    assert all(s.verb == "read" for s in specs)