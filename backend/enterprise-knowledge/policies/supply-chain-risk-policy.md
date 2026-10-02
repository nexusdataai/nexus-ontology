# Supply Chain Risk Management Policy

**Policy ID:** POL-SCR-001
**Version:** 1.0
**Effective Date:** 2024-01-15
**Owner:** Supply Chain Risk Management
**Risk Level:** High
**Systems Affected:** SAP, Oracle ERP, Social Listening, Google Drive
**SCOR Process:** Source/Enable

## 1. Risk Score Framework

Composite risk score (0–100) is calculated by the Supplier Risk Scoring workflow.

**Weight allocation:**

| Risk Factor | Weight |
|---|---|
| Delivery Reliability | 30% |
| Financial Health | 20% |
| Geographic Risk | 15% |
| Quality Performance | 15% |
| Contract Compliance | 10% |
| External Signals | 10% |

## 2. Risk Tier Thresholds

| Score Range | Risk Tier | Action |
|---|---|---|
| 80–100 | Low | Standard monitoring |
| 60–79 | Medium | Quarterly review |
| 40–59 | High | Monthly review + improvement plan required |
| 0–39 | Critical | Immediate action: freeze new POs, activate alternatives, executive escalation |

## 3. Single-Source Prohibition

- No critical material (ABC Class A) may have only **one** approved vendor in `Source_List`.
- If single-source is detected, Procurement must qualify an alternative within **90 days**.
- Exception: Patented ingredients with written **VP Procurement** approval.

## 4. Disruption Response SLA

| Signal Severity | Impact Assessment | Mitigation Plan |
|---|---|---|
| Critical | 2 hours | 4 hours |
| High | 8 hours | 24 hours |
| Medium | 48 hours | — |

## 5. Alternative Supplier Activation

- When a primary vendor's `Risk_Rating` enters **Critical**: activate secondary vendor from `Source_List`.
- If no secondary vendor exists: trigger **Emergency procurement** via the Disruption Response workflow.

## 6. Contract Compliance Monitoring

- Vendor performance is tracked against `Contract_Document` SLAs.
- **3+ violations** in 12 months triggers a mandatory vendor review.
- **5+ violations** in 12 months triggers a vendor suspension recommendation.

## 7. Commodity Price Monitoring

- Alert is triggered when `Commodity_Price` `Change_Pct_30D` exceeds **±15%**.
- Exceeding the threshold triggers a **hedging review** with Finance.

## 8. Re-evaluation Cycle

- All active vendors are re-scored **monthly**.
- New vendors must be scored within **5 business days** of `Vendor_Master` creation.

## Related Entities
- Vendor_Master (SAP)
- Source_List (SAP)
- Market_Signal (Social_Listening)
- Commodity_Price (Social_Listening)
- Contract_Document (Google_Drive)

## Related Workflows
- Supplier Risk Scoring (WORKFLOW_SUPPLIER_RISK_SCORING_V1_0)
- Disruption Response (WORKFLOW_DISRUPTION_RESPONSE_V1_0)

## Related Integrations
- Social Listening Feed (INTEGRATION_SOCIAL_LISTENING_V1_0)
- Unstructured Extraction (INTEGRATION_UNSTRUCTURED_EXTRACT_V1_0)

## Used By Applications
- Supply Chain Risk
