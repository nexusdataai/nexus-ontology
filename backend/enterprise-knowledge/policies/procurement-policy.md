# Procurement Policy

**Policy ID:** POL-PROC-001
**Version:** 1.0
**Effective Date:** 2024-01-15
**Owner:** Procurement Department
**Risk Level:** High
**Systems Affected:** SAP, Oracle ERP, Google Drive
**SCOR Process:** Source

## 1. Source of Truth

- Oracle `Purchase_Order` is the **authoritative source** for all purchase order data.
- SAP `Vendor_Master` is authoritative for vendor data.
- SAP `Source_List` is authoritative for approved vendor-material mapping.

## 2. Approved Vendor List

- All procurement **must** use vendors listed on SAP `Source_List`.
- Purchasing from a non-listed vendor constitutes **maverick spend**.
- Maverick purchases require **VP Procurement** approval.

## 3. Purchase Order Approval Thresholds

| PO Value | Approval Required |
|---|---|
| < $10K | Auto-approved |
| $10K–$50K | Procurement Manager |
| $50K–$250K | Procurement Director |
| > $250K | VP Procurement + CFO |
| > $1M | Board approval |

## 4. Competitive Bidding

- **3+ quotes** required for all purchases exceeding $50K.
- Sole-source procurement is allowed only for:
  - Patented materials
  - Emergency procurement per Supply Chain Risk Policy (POL-SCR-001)
- Full documentation of the bidding process is required.

## 5. Three-Way Match Rules

Purchase Order quantity is matched against GRN quantity and Invoice quantity.

- **Tolerance:** Quantity ±2%, Price ±5%
- Mismatches are routed to the **AP exception queue**.
- Unresolved exceptions are escalated after **5 business days**.

## 6. Maverick Spend Rules

Maverick spend is defined as:
- Any purchase from a non-contracted vendor for a material with an active `Source_List` entry.
- Any purchase at a price **>5% above** the contracted rate.

**Target:** Maverick spend rate must remain below **5% of total spend**.

## 7. Contract Compliance

- Vendor performance is tracked against `Contract_Document` terms.
- Non-compliance is reported **quarterly**.
- **3+ violations** in a reporting period triggers a mandatory vendor review.

## 8. Payment Terms

- **Standard terms:** Net 30.
- Early payment discounts are negotiated per vendor.
- Payment is **not released** until the three-way match is cleared.

## 9. Audit Trail

All purchase orders, approvals, and amendments must be logged with a full audit trail.

## Related Entities
- Vendor_Master (SAP)
- Source_List (SAP)
- Purchase_Requisition (SAP)
- Goods_Receipt (SAP)
- Purchase_Order (Oracle)
- AP_Invoice (Oracle)

## Related Workflows
- Procurement Spend Analysis (WORKFLOW_PROCUREMENT_SPEND_V1_0)
- Invoice Processing (WORKFLOW_INVOICE_PROCESSING_V1_0)

## Related Integrations
- SAP-Oracle Finance Sync (INTEGRATION_SAP_ORACLE_FINANCE_V1_0)
- Unstructured Extraction (INTEGRATION_UNSTRUCTURED_EXTRACT_V1_0)

## Used By Applications
- Procurement Analytics
- Supply Chain Risk
