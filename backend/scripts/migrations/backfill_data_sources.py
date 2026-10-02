"""
Backfill DATASOURCE# rows from the current UI card set.

Seeds one row per current Data Plane UI card so the new
``/api/v1/data-sources`` API returns the same list the frontend
``DataPlanePage`` hardcodes today.

Idempotent: existing rows are overwritten with the current attrs so it's
safe to re-run.
"""

from __future__ import annotations

import asyncio
import sys

from src.services.data_plane.data_source_service import get_data_source_service


SEED = [
    dict(
        id="sfdc",
        type="FDW",
        name="Salesforce CRM",
        schemaName="sfdc_itxp2dev",
        mode="simulator",
        simulatorKey="sfdc",
        verticals=["crm", "supply_chain"],
        description="Customer accounts, pipeline, contracts",
    ),
    dict(
        id="oracle",
        type="FDW",
        name="Oracle ERP",
        schemaName="oracle_erp",
        mode="simulator",
        simulatorKey="oracle",
        verticals=["crm", "supply_chain"],
        description="Finance, AR/AP, general ledger",
    ),
    dict(
        id="sap",
        type="FDW",
        name="SAP S/4HANA",
        schemaName="sap_s4hana",
        mode="simulator",
        simulatorKey="sap",
        verticals=["supply_chain"],
        description="Inventory, supply chain, production",
    ),
    dict(
        id="google_drive",
        type="CLOUD_DRIVE",
        name="Google Drive",
        schemaName="external_sources",
        mode="simulator",
        simulatorKey="external",
        verticals=["supply_chain"],
        description="Contracts, reports, documents",
    ),
    dict(
        id="file_uploads",
        type="FILE_UPLOAD",
        name="File Uploads",
        schemaName="external_sources",
        mode="simulator",
        simulatorKey="external",
        verticals=["supply_chain"],
        description="Invoices, lab reports, CSV files",
    ),
    dict(
        id="social_listening",
        type="SOCIAL",
        name="Social Listening",
        schemaName="external_sources",
        mode="simulator",
        simulatorKey="external",
        verticals=["supply_chain"],
        description="Market signals, sentiment",
    ),
    dict(
        id="tpm",
        type="FDW",
        name="TPM (Trade CPQ)",
        schemaName="tpm_cpq",
        mode="simulator",
        simulatorKey="tpm",
        verticals=["supply_chain"],
        description="Sell-side Trade Promotion Management",
    ),
    dict(
        id="sourcing",
        type="FDW",
        name="Sourcing CPQ",
        schemaName="sourcing_cpq",
        mode="simulator",
        simulatorKey="sourcing",
        verticals=["supply_chain"],
        description="Buy-side sourcing/procurement",
    ),
]


async def _amain() -> int:
    svc = get_data_source_service()
    for row in SEED:
        await svc.put(row["id"], row)
        print(f"  {row['id']:<20} -> saved")
    print(f"\nDone: {len(SEED)} data sources upserted")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_amain()))
