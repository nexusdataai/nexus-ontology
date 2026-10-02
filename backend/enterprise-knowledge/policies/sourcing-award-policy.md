# Sourcing Award Policy

**Policy ID:** POL-CPQ-AWD-001
**Version:** 1.0
**Effective Date:** 2026-05-23
**Owner:** Procurement / Sourcing
**Risk Level:** High
**Systems Affected:** Sourcing_Simulator (Sourcing CPQ), SAP, Oracle
**SCOR Process:** Source

## 1. Source of Truth

- `Sourcing_Scenario.Split_JSON` and `Sourcing_Award.Status` in the Sourcing CPQ layer are authoritative for award decisions.
- `Source_List` in SAP is updated only on award approval; until then, vendor-material assignments are unchanged.
- This policy **extends** (does not override) the existing `procurement-policy.md` and `supply-chain-risk-policy.md`.

## 2. Single-Source Prohibition

- No ABC-class A material (per `Material_Plant.ABC_Classification`) may have only one approved vendor in `Source_List`.
- Exception requires VP Procurement approval and is time-bound (≤ 90 days) with a documented qualification plan.
- A `Sourcing_Award` whose `Sourcing_Scenario.Concentration_Pct` = 100 on a Class-A material is blocked.

## 3. Vendor Concentration Ceiling

- Per category and per material, no single vendor may receive more than **60 %** of awarded volume.
- Categories: Raw_Material, Packaging, Co_Packer, Logistics, Services, Equipment.
- Concentrations >60 % are blocked unless override by Procurement Director with documented rationale; ≥85 % requires VP Procurement.

## 4. Should-Cost Variance

| Variance vs Should-Cost | Approver |
|--------------------------|----------|
| Better than +0 % (savings) | Auto-approve |
| 0 % to +5 % | Procurement Manager |
| +5 % to +10 % | Procurement Director |
| +10 % to +20 % | VP Procurement |
| > +20 % | VP Procurement + CFO |

Should-cost variance = `(Awarded_Unit_Price - Should_Cost_Model.Modeled_Cost) / Should_Cost_Model.Modeled_Cost`.

## 5. Sustainability Certifications

- Packaging awards **must** carry a vendor with at least one of: `ISO_14001`, `FSC`, `PEFC`, `Recycled_Content_Cert`.
- Awards without certification require Sustainability lead sign-off in addition to procurement approvals.

## 6. Risk Tier Constraints

Reusing the existing risk tiers from `supply-chain-risk-policy.md`:

| Vendor Risk Tier | Award Rules |
|-------------------|-------------|
| Low (80-100) | No constraints |
| Medium (60-79) | Max 40 % concentration per material |
| High (40-59) | Max 25 % concentration; requires Procurement Director |
| Critical (0-39) | Block; emergency override only with VP Procurement + SC Risk Lead |

## 7. Award Approval Matrix

| Award Value | Approver |
|-------------|----------|
| ≤ $50 K total | Procurement Manager |
| $50K - $250K | Procurement Director |
| $250K - $1M | VP Procurement + CFO |
| > $1M | VP Procurement + CFO + Board |

These extend the PO approval thresholds in `procurement-policy.md`; the higher-rank approver applies when both fire.

## 8. SLA

| Approver Tier | SLA |
|---------------|-----|
| Procurement Manager | 1 business day |
| Procurement Director | 2 business days |
| VP Procurement | 3 business days |
| CFO | 3 business days |
| VP Procurement + CFO + Board | 10 business days |

## 9. Award Issue and Contract

- An `Approved` award **must** generate a draft `Contract_Document` in Google Drive within 24 hours of approval.
- An `Issued` award **must** create `Purchase_Order` records in SAP within 48 hours.
- The corresponding `Source_List` priority is updated atomically with the award issue.

## 10. Audit Requirements

Every approval, override, and award action records:
- Approver role and user ID
- Action (approved / rejected / overridden / cancelled)
- Should-cost variance, concentration, risk tier
- Timestamp
- Reference to `Sourcing_Scenario.Scenario_ID` chosen

## Related Entities

- RFx_Event, RFx_Line, RFx_Invitation
- Vendor_Quote, Vendor_Quote_Line
- Should_Cost_Model
- Sourcing_Scenario, Sourcing_Award
- Vendor_Master, Source_List, Material_Plant (ABC class)

## Related Workflows

- RFx Launch (WORKFLOW_RFX_LAUNCH_V1_0)
- RFx Bid Evaluation (WORKFLOW_RFX_BID_EVALUATE_V1_0)
- RFx Award (WORKFLOW_RFX_AWARD_V1_0)
- Contract Generation (WORKFLOW_CONTRACT_GENERATION_V1_0)

## Related Integrations

- Sourcing CPQ ↔ SAP Ariba Sync (INTEGRATION_SOURCING_SAP_ARIBA_V1_0)

## Used By Applications

- Sourcing CPQ
- Procurement Analytics
- Supply Chain Risk Radar
