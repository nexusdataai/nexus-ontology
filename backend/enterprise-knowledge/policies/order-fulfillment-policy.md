# Order Fulfillment Policy

**Policy ID:** POL-OFC-001
**Version:** 1.0
**Effective Date:** 2024-01-15
**Owner:** Order Management / Supply Chain Operations
**Risk Level:** High
**Systems Affected:** Salesforce, SAP, Oracle ERP
**SCOR Process:** Deliver

## 1. Source of Truth

- Salesforce `Opportunity` is **authoritative** for the customer order.
- SAP `Delivery_Document` is authoritative for fulfillment and shipment.
- Oracle `AR_Invoice` is authoritative for billing.
- All three systems **must reconcile**; discrepancies are flagged for resolution per the Three-Way Match rules below.

## 2. Order Acknowledgment SLA

- All `Closed_Won` Opportunities must be acknowledged in SAP within **4 hours**.
- Express / Critical priority orders must be acknowledged within **1 hour**.

## 3. Fulfillment SLA by Priority

| Priority | SLA | Measurement |
|---|---|---|
| Standard | 5 business days from order | `Opportunity.Close_Date` → `Delivery_Document.Actual_Arrival` |
| Express | 2 business days from order | `Opportunity.Close_Date` → `Delivery_Document.Actual_Arrival` |
| Critical | Same day / next day | `Opportunity.Close_Date` → `Delivery_Document.Actual_Arrival` |

## 4. Three-Way Match Tolerance

- Opportunity quantity vs. Delivery quantity vs. Invoice quantity.
- **Tolerance:** Quantity ±2%, Price ±5%.
- Mismatches are flagged and routed per Procurement Policy (POL-PROC-001).
- Unresolved mismatches within **5 business days** are escalated to the **Finance Director**.

## 5. Credit Hold Rules

- If `Account.AR_Balance` exceeds **80%** of `Credit_Limit`: new orders are **held** pending Finance review.
- If Account is on `Credit_Hold` status: **all shipments blocked**.
- Release requires **Finance Manager** approval.

## 6. SLA Breach Escalation

| Trigger | Action |
|---|---|
| 80% of SLA window elapsed with no shipment | Alert fulfillment team |
| 100% of SLA (breach) | Notify Regional SC Manager + customer communication |
| 120% of SLA | VP Supply Chain escalation |

## 7. Partial Shipment Rules

- Partial shipment is allowed if **>70%** of order quantity is available.
- Remaining quantity must ship within original SLA **+ 3 business days**.
- If **<70%** is available, customer must approve the partial shipment or the order is rescheduled.

## 8. Return Processing

- Returns accepted within **30 days** of delivery.
- `Return_Order` must reference the original `Delivery_Document`.
- Credit note generated in Oracle within **5 business days** of return receipt.

## 9. Audit Trail

Complete order lifecycle must be tracked:
- Opportunity creation → SAP delivery creation → shipment → proof of delivery → invoice → payment.
- All timestamps logged for SLA measurement and compliance reporting.

## Related Entities
- Opportunity (Salesforce)
- Delivery_Document (SAP)
- AR_Invoice (Oracle)
- AR_Customer (Oracle)
- Goods_Receipt (SAP)
- Return_Order (SAP)

## Related Workflows
- Order-to-Cash Monitoring (WORKFLOW_ORDER_TO_CASH_V1_0)

## Related Integrations
- SF-Oracle Supply Chain Sync (INTEGRATION_SF_ORACLE_SC_V1_0)
- SAP-Oracle Finance Sync (INTEGRATION_SAP_ORACLE_FINANCE_V1_0)

## Used By Applications
- Order-to-Cash Monitor
