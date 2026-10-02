# Credit Limit Management Policy

**Policy ID:** POL-CREDIT-001
**Version:** 3.2
**Effective Date:** 2024-01-15
**Owner:** Finance Department
**Risk Level:** High
**Systems Affected:** Salesforce, Oracle ERP

## 1. Source of Truth

Salesforce `Account.Credit_Limit__c` is the **authoritative source** for customer credit limits.
Oracle AR receives the credit limit via integration sync but **cannot override** the Salesforce value.

## 2. Credit Limit Constraints

- **Maximum allowed value:** 1,000,000 USD
- **Minimum value:** 0 (credit hold)
- **Currency:** Base currency of the customer account

## 3. Approval Thresholds

| Change Magnitude | Approval Required | Approver Role | SLA |
|---|---|---|---|
| ≤ 5% increase | Auto-approved | — | Immediate |
| 5%–10% increase | Team Lead approval | Sales Manager | 24 hours |
| > 10% increase | Finance Manager approval | Finance Manager | 48 hours |
| Any decrease | Auto-approved | — | Immediate |
| Credit hold (set to 0) | Finance Manager approval | Finance Manager | 4 hours |

## 4. Pre-requisites for Credit Limit Change

Before any credit limit modification:

1. `Risk_Tier__c` must be evaluated and current (within last 90 days)
2. Customer must not have outstanding disputes exceeding 10% of current limit
3. AR balance must be below 80% of current credit limit
4. Customer account status must be "Active"

## 5. Financial Close Window Restriction

Credit limit modifications are **blocked** during the financial close window.
See Close Window Policy (POL-CLOSE-001) for schedule.

## 6. Oracle ERP Sync Condition

After credit limit approval:
1. New value syncs to Oracle `AR_Customer.credit_limit` within 15 minutes
2. Oracle AR collection priority is recalculated
3. If sync fails, Salesforce value is authoritative; manual Oracle update required

## 7. Audit Requirements

All credit limit changes must be logged with:
- Previous value
- New value
- Approver identity
- Justification text (mandatory for changes > 10%)
- Timestamp

## Related Entities
- Account (Salesforce)
- AR_Customer (Oracle)
- AR_Invoice (Oracle)

## Related Workflows
- Credit Approval Flow (WORKFLOW_CREDIT_APPROVAL_V1_0)
- Order-to-Cash Monitoring (WORKFLOW_ORDER_TO_CASH_V1_0)

## Related Integrations
- SF-Oracle Supply Chain Sync (INTEGRATION_SF_ORACLE_SC_V1_0)

## Used By Applications
- Order-to-Cash Monitor
- Customer 360
