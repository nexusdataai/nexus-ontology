"""
Diagnostic-sentinel seed rows for the ReAct Tools canary runner.

Every ID literal that appears in :pydata:`react_tools_diagnostics.CANARY_PARAMS`
for a write tool must resolve to a real row in the matching simulator,
otherwise ``update_one`` raises 404 and the canary fails. This module is
the single source of truth for those sentinel rows so the canary catalogue
and the simulator seed cannot drift apart.

Per-simulator helper: each simulator's ``seed_data()`` calls
``apply_sentinels(simulator_key, data_map)`` after building its synthetic
rows; sentinels are appended to the named tables (created on demand).

Sentinel rows use ``*-DIAG-1`` PKs so they never collide with the curated
ID pools in :pymod:`supply_chain_seed_pools` and so audit-event filters
on ``actor='diagnostic-runner'`` can isolate canary side effects.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

SENTINEL_IDS: Dict[str, str] = {
    "po": "PO-DIAG-1",
    "invoice": "INV-DIAG-1",
    "customer": "ACC-DIAG-1",
    "account": "ACC-DIAG-1",
    "opportunity": "OPP-DIAG-1",
    "material": "MAT-DIAG-1",
    "plant": "PL-DIAG-1",
    "production_order": "PROD-DIAG-1",
    "delivery": "DEL-DIAG-1",
    "batch": "BATCH-DIAG-1",
}


# Keyed by (simulator_key, table_name) -> rows.
# ``simulator_key`` is the logical-system tag each simulator passes when it
# calls :pyfunc:`apply_sentinels` from its ``seed_data()`` ("oracle",
# "sap", or "sfdc"). It is independent of the registration key inside
# :pydata:`fdw_api._simulators` (which is "oracle" / "sap" / "simulator").
DIAGNOSTIC_SENTINELS: Dict[Tuple[str, str], List[Dict]] = {
    ("oracle", "Oracle_Purchase_Order"): [
        {
            "PO_ID": SENTINEL_IDS["po"],
            "Vendor_ID": "VND-DIAG-1",
            "Material_ID": SENTINEL_IDS["material"],
            "Plant_ID": SENTINEL_IDS["plant"],
            "Quantity": 1,
            "Unit_Price": 1.0,
            "Total_Amount": 1.0,
            "PO_Date": "2026-01-01",
            "Status": "Open",
            "Contract_ID": "",
            "Currency": "USD",
        },
    ],
    ("oracle", "Oracle_AR_Invoice"): [
        {
            "Invoice_ID": SENTINEL_IDS["invoice"],
            "Customer_ID": SENTINEL_IDS["customer"],
            "Invoice_Date": "2026-01-01",
            "Due_Date": "2026-02-01",
            "Amount": 1.0,
            "Status": "Open",
            "Linked_Delivery_ID": SENTINEL_IDS["delivery"],
            "Currency": "USD",
        },
    ],
    ("oracle", "Oracle_AR_Customer"): [
        {
            "Customer_ID": SENTINEL_IDS["customer"],
            "Customer_Name": "Diagnostic Customer",
            "Credit_Limit": 1000.0,
            "Payment_Terms": "Net_30",
            "Currency": "USD",
            "Status": "Active",
        },
    ],
    ("sap", "Material_Plant"): [
        {
            "Material_ID": SENTINEL_IDS["material"],
            "Plant_ID": SENTINEL_IDS["plant"],
            "Safety_Stock": 0,
            "Reorder_Point": 0,
            "MRP_Type": "Manual",
            "Lead_Time_Days": 1,
            "Lot_Size": 1,
            "ABC_Classification": "C",
        },
    ],
    # The ERP writeback tool _update_production_order does
    # update_one(... pk_col="Order_ID" ...) while the rest of the SAP
    # schema and seeds use "Production_Order_ID". Include both keys so
    # the sentinel matches whichever column the caller looks up by.
    ("sap", "Production_Order"): [
        {
            "Production_Order_ID": SENTINEL_IDS["production_order"],
            "Order_ID": SENTINEL_IDS["production_order"],
            "Material_ID": SENTINEL_IDS["material"],
            "Plant_ID": SENTINEL_IDS["plant"],
            "Production_Line": "LINE-DIAG-1",
            "Quantity": 1,
            "Start_Date": "2026-01-01",
            "End_Date": "2026-01-02",
            "Status": "Planned",
            "Yield_Pct": 100.0,
            "Shift_ID": "S1",
        },
    ],
    ("sap", "Delivery_Document"): [
        {
            "Delivery_ID": SENTINEL_IDS["delivery"],
            "Sales_Order_ID": SENTINEL_IDS["opportunity"],
            "Ship_To_Account_ID": SENTINEL_IDS["account"],
            "Material_ID": SENTINEL_IDS["material"],
            "Batch_ID": SENTINEL_IDS["batch"],
            "Quantity": 1,
            "Delivery_Date": "2026-01-01",
            "Status": "Created",
            "Priority": "Standard",
            "Carrier": "Local_Fleet",
            "Delay_Reason": "",
        },
    ],
    ("sap", "Batch_Master"): [
        {
            "Batch_ID": SENTINEL_IDS["batch"],
            "Material_ID": SENTINEL_IDS["material"],
            "Production_Order_ID": SENTINEL_IDS["production_order"],
            "Plant_ID": SENTINEL_IDS["plant"],
            "Production_Date": "2026-01-01",
            "Expiry_Date": "2027-01-01",
            "Quantity": 1,
            "Status": "Released",
        },
    ],
    ("sfdc", "Account"): [
        {
            "Account_ID": SENTINEL_IDS["account"],
            "Account_Name": "Diagnostic Account",
            "Industry": "Diagnostic",
            "Region": "NA",
            "Country": "US",
            "Channel_Type": "Direct",
            "Tier": "Bronze",
            "Annual_Revenue": 1.0,
            "Account_Status": "Active",
            "Credit_Limit": 1000.0,
            "Credit_Hold_Status": "Active",
            "Churn_Date": "",
            "Churn_Reason": "",
            "Health_Bucket": "Green",
            "Health_Score": 100.0,
            "Latitude": 0.0,
            "Longitude": 0.0,
        },
    ],
    ("sfdc", "Opportunity"): [
        {
            "Opportunity_ID": SENTINEL_IDS["opportunity"],
            "Account_ID": SENTINEL_IDS["account"],
            "Opportunity_Name": "Diagnostic Opportunity",
            "Amount": 1.0,
            "Stage": "Prospecting",
            "Close_Date": "2026-12-31",
            "Region": "NA",
            "Product_Category": "Diagnostic",
            "Campaign_ID": "",
            "Stage_Entered_At_Prospect": "2026-01-01",
            "Stage_Entered_At_Negotiation": "",
            "Stage_Entered_At_Closed_Won": "",
            "Stage_Entered_At_Fulfilled": "",
        },
    ],
}


def apply_sentinels(simulator_key: str, data_map: Dict[str, List[Dict]]) -> None:
    """Append diagnostic sentinel rows to ``data_map`` for one simulator.

    Tables that do not yet exist in ``data_map`` are created. Idempotent:
    if the sentinel PK is already present for a table, the row is left
    untouched so reload-from-S3 paths do not duplicate it.
    """
    for (sim_key, table), rows in DIAGNOSTIC_SENTINELS.items():
        if sim_key != simulator_key:
            continue
        existing = data_map.setdefault(table, [])
        for sentinel in rows:
            pk_field, pk_value = _first_pk(sentinel)
            if pk_field is None:
                existing.append(dict(sentinel))
                continue
            if any(str(r.get(pk_field, "")) == str(pk_value) for r in existing):
                continue
            existing.append(dict(sentinel))


def _first_pk(row: Dict) -> Tuple[str, str]:
    for k in ("PO_ID", "Invoice_ID", "Customer_ID", "Account_ID",
              "Opportunity_ID", "Production_Order_ID", "Order_ID",
              "Material_ID", "Delivery_ID", "Batch_ID"):
        if k in row:
            return k, str(row[k])
    return None, None  # type: ignore[return-value]
