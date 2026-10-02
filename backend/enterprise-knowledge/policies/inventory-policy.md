# Inventory Management Policy

**Policy ID:** POL-INV-001
**Version:** 1.0
**Effective Date:** 2024-01-15
**Owner:** Supply Chain Operations
**Risk Level:** High
**Systems Affected:** SAP, Oracle ERP
**SCOR Process:** Plan

## 1. Source of Truth

SAP `Inventory_Position` is the **authoritative source** for all inventory quantities and locations.
Oracle `Cost_Accounting` is authoritative for inventory valuation and costing.

## 2. Safety Stock Rules

- **Minimum days-of-supply by ABC classification:**

| ABC Class | Minimum Days-of-Supply |
|---|---|
| A | 7 days |
| B | 14 days |
| C | 21 days |

- Dynamic safety stock is **recalculated weekly** based on demand forecast variance.
- Any safety stock breach triggers **emergency replenishment** workflow.

## 3. Reorder Point Management

Reorder point is calculated as:

**Reorder Point = Average Daily Demand × Lead Time + Safety Stock**

- Reorder is triggered when `Unrestricted_Qty` falls below the calculated reorder point.

## 4. Expiry Management Windows

| Days to Expiry | Required Action |
|---|---|
| 90 days | Flag for accelerated sales |
| 60 days | Markdown/redistribution mandatory |
| 30 days | Final action required |
| 7 days | Donate or destroy |

## 5. FIFO Enforcement

- All outbound shipments **must** use the oldest batch first (First-In-First-Out).
- Any exception to FIFO requires **Supply Chain Manager** approval.

## 6. Stock Rebalancing Rules

- **Imbalance threshold:** Transfer triggered when Plant A has >45 days of supply AND Plant B has <5 days of supply for the same SKU.
- **Transfer approval:**

| Transfer Value | Approval Required |
|---|---|
| < $50K | Auto-approved |
| > $50K | Supply Chain Manager |

## 7. Markdown Authority

| Markdown Percentage | Approver |
|---|---|
| 0–15% | Store/Depot Manager |
| 15–30% | Regional Manager |
| > 30% | Supply Chain Director |

## 8. Cycle Count Requirements

| ABC Class | Cycle Count Frequency |
|---|---|
| A | Monthly |
| B | Quarterly |
| C | Semi-annual |

- Variance exceeding **5%** triggers a formal investigation.

## 9. Audit Requirements

All inventory adjustments must be logged with:
- Reason for adjustment
- Approver identity
- Timestamp

## Related Entities
- Inventory_Position (SAP)
- Material_Plant (SAP)
- Batch_Master (SAP)
- Plant_Master (SAP)
- Warehouse_Transfer (SAP)
- Storage_Location (SAP)

## Related Workflows
- Inventory Rebalancing (WORKFLOW_INVENTORY_REBALANCING_V1_0)
- Expiry Management (WORKFLOW_EXPIRY_MANAGEMENT_V1_0)

## Related Integrations
- SAP Inventory Feed (INTEGRATION_SAP_INVENTORY_FEED_V1_0)

## Used By Applications
- Inventory Optimization
- Demand Forecasting
- Production & Quality
