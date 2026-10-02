# Role-Based Access Control Policy

**Policy ID:** POL-RBAC-001
**Version:** 1.4
**Effective Date:** 2024-02-01
**Owner:** IT Security
**Risk Level:** High
**Systems Affected:** Salesforce, Oracle ERP

## 1. Role Definitions

| Role | System Access | Key Permissions |
|---|---|---|
| Sales Representative | Salesforce | Read/Write own accounts; Read all accounts |
| Sales Manager | Salesforce | Read/Write all accounts; Approve credit ≤10% |
| Finance Manager | Salesforce + Oracle | Credit limit approval; AR adjustments; GL access |
| Finance Director | Salesforce + Oracle | All Finance Manager + override authority |
| System Administrator | All | Full access; audit log access |
| Read-Only Analyst | All | Read-only across all systems |

## 2. Credit Override Authorization

Only the following roles may override a customer credit block:

1. **Finance Manager** — for blocks due to AR balance
2. **Finance Director** — for blocks due to risk tier
3. **CFO** — for blocks during financial close window

### Override Requirements
- Written justification (minimum 50 characters)
- Documented in audit log
- Automatic expiry after 30 days (requires re-authorization)
- Email notification to Compliance Officer

## 3. Field-Level Access

| Field | Sales Rep | Sales Mgr | Finance Mgr | Admin |
|---|---|---|---|---|
| Account.Credit_Limit__c | Read | Read | Read/Write | Read/Write |
| Account.Risk_Tier__c | Read | Read | Read/Write | Read/Write |
| Account.Status | Read/Write | Read/Write | Read/Write | Read/Write |
| Oracle AR Balance | — | Read | Read/Write | Read |
| GL Journal Entries | — | — | Read/Write | Read |

## 4. Cross-System Permissions

When an action spans both Salesforce and Oracle:
- User must have permissions in **both** systems
- Highest risk level from either system applies
- Both system audit logs must record the action

## 5. Separation of Duties

- A user who **proposes** a credit limit change cannot **approve** the same change
- AR write-offs above 10,000 USD require two different approvers
- Journal entries above 50,000 USD require Finance Director sign-off

## Related Entities
- Account (Salesforce)
- All entities with risk_level=high

## Related Workflows
- Credit Approval Flow (WORKFLOW_CREDIT_APPROVAL_V1_0)
- Risk Assessment (WORKFLOW_RISK_ASSESSMENT_V1_0)

## Related Integrations
- SF-Oracle Sync (INTEGRATION_SF_ORACLE_SYNC_V1_0)

## Used By Applications
- All applications (governance layer)
