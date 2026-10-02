# Financial Close Window Policy

**Policy ID:** POL-CLOSE-001
**Version:** 2.1
**Effective Date:** 2024-03-01
**Owner:** Finance Operations
**Risk Level:** High
**Compliance:** SOX Section 404
**Systems Affected:** Salesforce, Oracle ERP

## 1. Purpose

Restricts modifications to financial data during month-end and quarter-end close periods
to ensure data integrity for financial reporting under SOX compliance.

## 2. Close Window Schedule

| Close Type | Start | End | Duration |
|---|---|---|---|
| Monthly close | Last business day of month, 6 PM | 3rd business day of next month, 9 AM | ~3 days |
| Quarter-end close | Last 2 business days of quarter | 5th business day of next quarter | ~5 days |
| Year-end close | Dec 28 | Jan 10 | ~13 days |

## 3. Restricted Operations During Close

The following operations are **blocked** when `close_period_active = true`:

### Salesforce
- Credit limit modifications (`Account.Credit_Limit__c`)
- Customer status changes (`Account.Status`)
- New customer creation (B2B enterprise tier)
- Risk tier overrides

### Oracle ERP
- GL journal postings
- AR adjustments
- Credit memo creation
- Invoice write-offs
- Intercompany transactions

## 4. Environment Flag

- **Flag:** `close_period_active`
- **Location:** SSM Parameter Store `/call-processing/{env}/finance/close_period_active`
- **Values:** `true` | `false`
- **Updated by:** Finance Operations team via scheduled automation

## 5. Override Authorization

Emergency overrides during close window require:
- CFO or VP Finance written approval
- Documented business justification
- Audit trail entry with override reason
- Post-close reconciliation check

## 6. SOX Compliance Note

This policy implements SOX Section 404 internal control requirements.
All violations are reported to the Audit Committee quarterly.

## Related Entities
- GL_Journal (Oracle)
- GL_Period (Oracle)
- AR_Invoice (Oracle)

## Related Workflows
- Order-to-Cash Monitoring (WORKFLOW_ORDER_TO_CASH_V1_0)

## Related Integrations
- SAP-Oracle Finance Sync (INTEGRATION_SAP_ORACLE_FINANCE_V1_0)

## Used By Applications
- Order-to-Cash Monitor
- Regulatory Compliance
