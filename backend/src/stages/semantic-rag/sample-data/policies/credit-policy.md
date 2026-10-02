# Credit Limit Management Policy v3.2

## Source of Truth
Salesforce Account.Credit_Limit__c is the authoritative source for customer credit limits.
Oracle AR receives credit limit updates via integration sync but cannot override the Salesforce value.

## Field Definition
- Object: Salesforce Account
- Field: Credit_Limit__c
- Data Type: Currency(18,2)
- Maximum Allowed Value: 1,000,000 USD

## Approval Thresholds
- Changes up to 10%: Auto-approved, no workflow triggered
- Changes between 10% and 25%: Requires Finance Manager approval
- Changes above 25%: Requires VP Finance approval
- SLA for approval: 24 hours

## Credit Approval Workflow
When a credit limit change exceeds the 10% threshold:
1. Submit for approval via Credit Approval Flow
2. Assigned approver: Finance Manager (or VP Finance for >25%)
3. Upon approval: sync to Oracle AR via AR_Customer_Sync integration
4. Audit log entry created

## Financial Close Restriction
- Credit limits CANNOT be modified during financial close window
- Environment flag: close_period_active
- SOX compliance requirement: All modifications during close are blocked
- Applies to both Salesforce and Oracle

## Risk Tier Dependency
- Risk_Tier__c must be evaluated before any credit limit increase
- Risk tier determines the maximum allowable credit exposure
- High risk: max 100,000 USD
- Medium risk: max 500,000 USD
- Low risk: max 1,000,000 USD

## Credit Block Override
- Only Finance Manager role can override a credit block
- Override requires documented justification
- All overrides are logged to audit trail
- RBAC mapping: Finance Manager -> credit_block_override permission

## Required Justification
- Any credit limit change above 10% requires a written justification
- Justification stored in Credit_Change_Justification__c field
