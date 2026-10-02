# CPQ Quote Approval Policy

**Policy ID:** POL-CPQ-APR-001
**Version:** 1.0
**Effective Date:** 2026-05-23
**Owner:** Commercial / Revenue Management
**Risk Level:** High
**Systems Affected:** TPM_Simulator (Trade CPQ), Salesforce, Oracle ERP
**SCOR Process:** Deliver

## 1. Source of Truth

- `Quote_Header.Status` and `Quote_Header.Approval_Chain_JSON` are the authoritative sources for the approval state of every trade quote.
- Approval thresholds in this policy extend (and do not override) the discount and trade spend caps defined in `pricing-discount-policy.md`.

## 2. Approval Matrix

| Scenario | Approval Required |
|----------|-------------------|
| Discount ≤ tier max AND margin ≥ 15 % AND slotting fee ≤ $50K | Auto-approve |
| Discount exceeds tier max by ≤ 5 pp | Regional Sales Manager |
| Discount exceeds tier max by > 5 pp OR slotting fee > $50K | Commercial Director |
| Quote line margin below 15 % floor | CFO |
| Trade spend (this quote + trailing 12-month) > 8 % of account revenue | VP Sales |
| Configuration_Rule severity = Error and override requested | Commercial Director |
| Channel eligibility violation override | Commercial Director + Regional Sales Manager |

When multiple thresholds are tripped, the highest-rank approver is required.

## 3. Approval Chain Construction

The approval chain is computed at submission and persisted to `Quote_Header.Approval_Chain_JSON` as an ordered array:

```json
[
  { "role": "RegionalSalesManager", "approver_id": "USER-007", "status": "pending", "due_at": "..." },
  { "role": "CommercialDirector", "approver_id": "USER-002", "status": "pending", "due_at": "..." }
]
```

Each entry advances to `approved` or `rejected` and writes `at` (timestamp). A rejection at any level stops the chain and sets `Quote_Header.Status = Rejected`.

## 4. SLA

| Approver Tier | SLA |
|---------------|-----|
| Regional Sales Manager | 8 business hours |
| Commercial Director | 1 business day |
| CFO | 2 business days |
| VP Sales | 2 business days |

Breaches escalate one level. A 100 % SLA breach pushes the quote into the `In_Review_Escalated` substate and notifies the next-up approver.

## 5. Auto-Approval Conditions

A quote auto-approves only if all of:
- Every `Quote_Line.Discount_Pct` ≤ tier max for the line's `(channel, tier)`.
- Every `Quote_Line.Margin_Pct_Line` ≥ 15 %.
- Total `Listing_Fee + Slotting_Fee` ≤ $50,000.
- No `Configuration_Rule` violation with severity Error remains.
- `Account.Status` ∈ {Active}. Credit hold accounts cannot auto-approve.

## 6. Margin Floor Calculation

Per-line margin uses snapshot cost at quote time:

```
Margin_Pct_Line = (Unit_Price - Price_Book_Entry.Cost_Snapshot) / Unit_Price * 100
```

Blended `Quote_Header.Margin_Pct` is qty-weighted across lines.

## 7. Conversion to Order

- Only `Status=Approved` quotes can be transitioned to `Won_Converted`.
- Transition triggers the `Quote To Order` workflow, which writes Opportunity + Opportunity_Line_Item + Delivery_Document and chains into `order-to-cash-monitoring`.
- A quote in `Expired` status (past `Validity_Date`) cannot be converted; it must be re-quoted.

## 8. Audit Requirements

Every approval event records:
- Approver role and user ID
- Action (approved / rejected / escalated)
- Reason if rejected
- Timestamp
- Pre- and post-approval discount/margin

## Related Entities

- Quote_Header, Quote_Line, Quote_Promotion
- Price_Book_Entry
- Account (Salesforce), AR_Customer (Oracle)
- Configuration_Rule

## Related Workflows

- Quote Price Calculate (WORKFLOW_QUOTE_PRICE_CALCULATE_V1_0)
- Quote Approval Routing (WORKFLOW_QUOTE_APPROVAL_ROUTE_V1_0)
- Quote To Order (WORKFLOW_QUOTE_TO_ORDER_V1_0)

## Related Integrations

- CPQ-Salesforce Sync (INTEGRATION_CPQ_SALESFORCE_V1_0)

## Used By Applications

- Trade CPQ
- Order-to-Cash Monitor
