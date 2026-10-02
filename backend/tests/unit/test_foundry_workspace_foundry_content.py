"""
Unit tests for the Supply Chain Foundry DDB content CRUD added to
``FoundryWorkspaceRepository`` and the ``OntoDataService`` refactor that
backs the ``/api/v1/control-plane/onto-data/*`` API with DynamoDB
instead of S3.

Validates: Stage 2 foundry consolidation (canonical entities, policies,
workflow defs, integration defs).
"""

from __future__ import annotations

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import boto3
import pytest
from moto import mock_aws as mock_dynamodb

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    integration_def_pk,
    policy_pk,
    vdl_entity_pk,
    workflow_def_pk,
)


TABLE_NAME = "test-foundry-workspace"
REGION = "us-east-1"


def _create_table():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )


def _make_repo() -> FoundryWorkspaceRepository:
    return FoundryWorkspaceRepository(table_name=TABLE_NAME)


# ---------------------------------------------------------------------------
# Key builders — trivial regression guards
# ---------------------------------------------------------------------------


def test_policy_pk_format():
    assert policy_pk("credit-policy") == "POLICY#credit-policy"


def test_workflow_def_pk_format():
    assert workflow_def_pk("rfx-launch") == "WORKFLOWDEF#rfx-launch"


def test_integration_def_pk_format():
    assert integration_def_pk("sap-oracle-finance-sync") == "INTEGRATIONDEF#sap-oracle-finance-sync"


def test_vdl_entity_pk_format():
    assert vdl_entity_pk("Customer") == "VDLENTITY#Customer"


# ---------------------------------------------------------------------------
# Canonical entity CRUD (round-trip on moto)
# ---------------------------------------------------------------------------


@mock_dynamodb
def test_canonical_entity_round_trip():
    _create_table()
    repo = _make_repo()

    entity = {
        "name": "Customer",
        "aliases": ["Account", "AR_Customer"],
        "domain": "Customer & Sales",
        "semantic": "Customer master",
        "riskLevel": "high",
        "fields": [{"name": "Account_ID", "dataType": "ID"}],
        "relationships": [],
    }
    repo.put_canonical_entity("Customer", entity)

    fetched = repo.get_canonical_entity("Customer")
    assert fetched is not None
    assert fetched["name"] == "Customer"
    assert fetched["GSI1PK"] == "VDLENTITY"
    assert fetched["GSI1SK"] == "customer"  # name|lower
    assert fetched["aliases"] == ["Account", "AR_Customer"]


@mock_dynamodb
def test_canonical_entity_list_lists_only_meta_rows():
    _create_table()
    repo = _make_repo()
    repo.put_canonical_entity("Customer", {"name": "Customer"})
    repo.put_canonical_entity("Product", {"name": "Product"})

    rows = repo.list_canonical_entities()
    names = sorted(r["name"] for r in rows)
    assert names == ["Customer", "Product"]


@mock_dynamodb
def test_canonical_entity_delete_cascades_to_mapping_links():
    """delete_canonical_entity should remove the META row AND any
    MAPPING#... link rows that mapping rules wrote under the same PK."""
    _create_table()
    repo = _make_repo()

    # Set up a canonical + a mapping rule whose target is that canonical
    repo.put_canonical_entity("Customer", {"name": "Customer"})
    repo.put_mapping_rule(
        rule_id="MR-test-1",
        source_dp_id="Salesforce.sfdc_itxp2dev.Account",
        target_vdl_name="Customer",
        attrs={"id": "MR-test-1", "name": "Test rule"},
    )

    # Both META row and the MAPPING# link row should exist under Customer's PK
    rows = repo.query_pk(vdl_entity_pk("Customer"))
    sks = sorted(r["SK"] for r in rows)
    assert "META" in sks
    assert any(sk.startswith("MAPPING#") for sk in sks)

    deleted = repo.delete_canonical_entity("Customer")
    assert deleted >= 2

    rows_after = repo.query_pk(vdl_entity_pk("Customer"))
    assert rows_after == []


# ---------------------------------------------------------------------------
# Policy / Workflow / Integration CRUD
# ---------------------------------------------------------------------------


@mock_dynamodb
@pytest.mark.parametrize(
    "put_fn,get_fn,list_fn,del_fn,gsi1pk,slug",
    [
        ("put_policy", "get_policy", "list_policies", "delete_policy", "POLICY", "credit-policy"),
        ("put_workflow_def", "get_workflow_def", "list_workflow_defs", "delete_workflow_def", "WORKFLOWDEF", "rfx-launch"),
        ("put_integration_def", "get_integration_def", "list_integration_defs", "delete_integration_def", "INTEGRATIONDEF", "sf-oracle-sync"),
    ],
)
def test_content_crud_round_trip(put_fn, get_fn, list_fn, del_fn, gsi1pk, slug):
    _create_table()
    repo = _make_repo()

    attrs = {
        "slug": slug,
        "filename": f"{slug}.md",
        "category": gsi1pk.lower() + "s",
        "contentText": f"# {slug}\nbody here",
        "sizeBytes": 20,
        "updatedAt": "2026-01-01T00:00:00Z",
    }
    getattr(repo, put_fn)(slug, attrs)

    fetched = getattr(repo, get_fn)(slug)
    assert fetched is not None
    assert fetched["slug"] == slug
    assert fetched["GSI1PK"] == gsi1pk
    assert fetched["GSI1SK"] == slug.lower()
    assert fetched["contentText"].startswith("# ")

    rows = getattr(repo, list_fn)()
    assert len(rows) == 1
    assert rows[0]["slug"] == slug

    getattr(repo, del_fn)(slug)
    assert getattr(repo, get_fn)(slug) is None
    assert getattr(repo, list_fn)() == []


# ---------------------------------------------------------------------------
# OntoDataService — exercises the DDB-backing refactor through the
# preserved S3-era public API surface (list_files, upload_file, etc.)
# ---------------------------------------------------------------------------


@mock_dynamodb
def test_onto_data_service_round_trip_via_ddb():
    _create_table()

    # Inject the moto-backed repo into the service. The constructor lazily
    # builds the repo via os.environ-driven config, so we set the table
    # name env var first.
    os.environ["FOUNDRY_WORKSPACE_TABLE"] = TABLE_NAME
    try:
        from src.services.onto_data_service import OntoDataService
        svc = OntoDataService()

        # Upload one of each kind
        svc.upload_file("policies", "credit-policy.md", b"# Credit Policy\nfoo", "text/markdown")
        svc.upload_file("workflows", "rfx-launch.yaml", b"workflows:\n  - id: rfx_launch", "text/yaml")
        svc.upload_file("integrations", "sf-oracle-sync.yaml", b"integrations:\n  - name: x", "text/yaml")

        # list_files
        all_files = svc.list_files()
        assert len(all_files) == 3
        cats = sorted(f["category"] for f in all_files)
        assert cats == ["integrations", "policies", "workflows"]

        # list_files with category filter
        pol = svc.list_files("policies")
        assert len(pol) == 1
        assert pol[0]["filename"] == "credit-policy.md"
        assert pol[0]["key"] == "policies/credit-policy.md"

        # download
        content = svc.download_file("policies/credit-policy.md")
        assert content == b"# Credit Policy\nfoo"

        # get_info
        info = svc.get_info()
        assert info["total_files"] == 3
        assert info["by_category"] == {"policies": 1, "workflows": 1, "integrations": 1}
        assert info["storage"] == "dynamodb"
        assert info["bucket"] == TABLE_NAME  # back-compat: "bucket" key now reports DDB table

        # delete + verify
        assert svc.delete_file("policies/credit-policy.md") is True
        assert svc.download_file("policies/credit-policy.md") is None
        assert svc.list_files("policies") == []
    finally:
        os.environ.pop("FOUNDRY_WORKSPACE_TABLE", None)


@mock_dynamodb
def test_onto_data_service_upload_preserves_created_at_across_overwrites():
    _create_table()
    os.environ["FOUNDRY_WORKSPACE_TABLE"] = TABLE_NAME
    try:
        from src.services.onto_data_service import OntoDataService
        svc = OntoDataService()

        svc.upload_file("policies", "p.md", b"v1", "text/markdown")
        info1 = svc.list_files("policies")[0]
        created_at_1 = info1["last_modified"]
        assert created_at_1

        # Overwrite
        svc.upload_file("policies", "p.md", b"v2 longer content", "text/markdown")
        rows = svc.list_files("policies")
        assert len(rows) == 1  # still one file
        assert rows[0]["size"] == len(b"v2 longer content")

        # The DDB row's createdAt should be preserved across overwrites
        from src.repositories.foundry_workspace_repository import FoundryWorkspaceRepository
        repo = FoundryWorkspaceRepository(table_name=TABLE_NAME)
        row = repo.get_policy("p")
        assert row is not None
        assert row.get("createdAt") == created_at_1
        # updatedAt should advance (or at least equal createdAt on a same-tick rewrite)
        assert row.get("updatedAt") >= row.get("createdAt")
    finally:
        os.environ.pop("FOUNDRY_WORKSPACE_TABLE", None)


# ---------------------------------------------------------------------------
# foundry_backup.py helper-function unit tests
# ---------------------------------------------------------------------------


def _import_foundry_backup_module():
    """Load nexus-deployer/backup-restore/foundry_backup.py as a module
    without installing the deployer package."""
    import importlib.util
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.normpath(
        os.path.join(here, "..", "nexus-deployer", "backup-restore", "foundry_backup.py")
    )
    spec = importlib.util.spec_from_file_location("foundry_backup", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_foundry_backup_classify_known_prefixes():
    mod = _import_foundry_backup_module()
    assert mod._classify("POLICY#credit-policy") == "POLICY"
    assert mod._classify("WORKFLOWDEF#rfx-launch") == "WORKFLOWDEF"
    assert mod._classify("INTEGRATIONDEF#sf-oracle-sync") == "INTEGRATIONDEF"
    assert mod._classify("VDLENTITY#Customer") == "VDLENTITY"
    assert mod._classify("MAPPINGRULE#MR-abc-123") == "MAPPINGRULE"
    assert mod._classify("SOLUTION#sol-1") == "SOLUTION"


def test_foundry_backup_classify_unknown_falls_through_to_other():
    mod = _import_foundry_backup_module()
    assert mod._classify("FUTUREENTITY#xyz") == "OTHER"
    assert mod._classify("") == "OTHER"


def test_foundry_backup_decimalize_keeps_strings_and_bools():
    mod = _import_foundry_backup_module()
    from decimal import Decimal

    out = mod._decimalize({"s": "x", "b": True, "n": 1, "f": 1.5, "nested": [1, "y", {"k": 2}]})
    assert out["s"] == "x"
    assert out["b"] is True
    assert out["n"] == Decimal("1")
    assert out["f"] == Decimal("1.5")
    assert out["nested"][0] == Decimal("1")
    assert out["nested"][1] == "y"
    assert out["nested"][2]["k"] == Decimal("2")


def test_foundry_backup_json_default_handles_decimal():
    mod = _import_foundry_backup_module()
    from decimal import Decimal

    assert mod._json_default(Decimal("1")) == 1
    assert mod._json_default(Decimal("1.5")) == 1.5
    assert mod._json_default({1, 2}) in ([1, 2], [2, 1])  # set ordering
