# Customer Lifecycle Policy v2.1

## Customer Creation
When a new enterprise B2B customer is created:
1. Salesforce Account creation (required fields: Name, Industry, BillingAddress)
2. Risk assessment process triggered
3. Initial credit review by Finance team
4. Oracle ERP customer provisioning (AR module)
5. Data enrichment step (DUNS lookup, credit bureau check)

## Sequence Constraints
- Oracle ERP provisioning cannot start until Salesforce Account is created
- Credit review cannot start until risk assessment completes
- Data enrichment runs in parallel with credit review

## Failure Rollback
- If Oracle provisioning fails: Salesforce account marked as "Pending ERP"
- If risk assessment fails: Manual review required, account placed on hold
- Rollback order: reverse of creation order

## Customer Deactivation
- Deactivating a customer in Salesforce impacts Oracle ERP:
  - AR balance must be zero before deactivation
  - Open invoices block deactivation
  - Oracle AR customer status synced to "Inactive"
  - All pending orders are cancelled

## Schema Changes (v2.1)
- Added: Customer_Segment__c field (Enterprise/SMB/Startup)
- Added: Onboarding_Status__c field
- Deprecated: Legacy_Customer_Code__c (replaced by External_Id__c)
- Policy update: Segment determines approval routing
