# CPQ Configuration Policy

**Policy ID:** POL-CPQ-CFG-001
**Version:** 1.0
**Effective Date:** 2026-05-23
**Owner:** Commercial / Trade Marketing
**Risk Level:** High
**Systems Affected:** TPM_Simulator (Trade CPQ), Salesforce, SAP
**SCOR Process:** Plan/Deliver

## 1. Source of Truth

- `Product_Offering`, `Offering_Component`, and `Configuration_Rule` in the Trade CPQ data layer are the authoritative sources for offering definitions and validation rules.
- `Material_Master` in SAP remains the master for SKU attributes (pack size, pack config, shelf life, recycled content, GTIN).
- Channel and tier classification on `Account` (Salesforce) drives configuration eligibility checks.

## 2. Pack and Case Alignment

- Single-serve packs (e.g. 330ml, 500ml cans/PET) **must** ship as case-multiples of 24 for Modern Trade and 12 for General Trade.
- HORECA accepts mixed-pack orders subject to a minimum order quantity of 50 cases.
- E-commerce listings **must** carry a barcoded GTIN-13 and a recyclability score above 2.5.
- Exception requires Commercial Director approval and is logged with the offering and the override justification.

## 3. Channel Eligibility

| Channel | Eligible Offering Types | Pack Restrictions |
|---------|------------------------|-------------------|
| Modern_Trade | Single_SKU, Multi_SKU_Bundle, Listing_Pack | SSCC-palletizable cases only |
| General_Trade | Single_SKU, Multi_SKU_Bundle, Promo_Pack | Mixed pallets allowed |
| HORECA | Single_SKU, Promo_Pack | Single-serve packs only |
| E-commerce | Single_SKU, Multi_SKU_Bundle | GTIN-13 required, no glass for direct-to-consumer |
| Institutional | Bulk pack, Promo_Pack | Volume tiers ≥ 5,000 units |

## 4. Regional Restrictions

- Regulatory bans (e.g. high-sugar SKUs in regions with sugar tax thresholds) **must** appear in `Configuration_Rule` with `Type=Region_Restriction`.
- A regional restriction violation is severity **Error** and blocks the line.
- Plant-to-region serviceability is validated against `Serviceability_Footprint`. Out-of-footprint orders are blocked unless an exception is approved by the Regional Sales Manager.

## 5. Substitution Rules

- A line marked `Substitutable_Flag=true` may be replaced with another SKU in the same category, brand family, and pack size during the configure step.
- Substitutions that change category or brand family require Sales Rep confirmation.
- Free goods (`Component_Role=Free_Good`) cannot be removed by substitution.

## 6. Promotion Stacking

- Per `pricing-discount-policy.md`, campaign + tier discounts are capped at a combined 25 % of list price.
- Promotions in the same `Stacking_Group` cannot stack. Allowed groups: `TIER_DISC`, `CAMPAIGN_DISC`, `BUNDLE`, `VOLUME`, `DISPLAY`.
- BOGO and tier discount cannot stack on the same line.

## 7. Validation Severity

| Severity | Effect |
|----------|--------|
| Error | Blocks quote submission until resolved |
| Warning | Allows submission but escalates approval one level |
| Info | Informational; does not affect approval |

## 8. Audit Requirements

Every configuration violation logged on a quote must record:
- Rule_ID and rule type
- Severity
- Override authority and approver identity (if overridden)
- Timestamp
- Quote_ID and Line_ID

## Related Entities

- Product_Offering, Offering_Component, Configuration_Rule
- Quote_Header, Quote_Line, Quote_Promotion
- Serviceability_Footprint
- Account, Campaign (Salesforce)
- Material_Master, Plant_Master (SAP)

## Related Workflows

- Quote Configure & Validate (WORKFLOW_QUOTE_CONFIGURE_VALIDATE_V1_0)
- Quote Approval Routing (WORKFLOW_QUOTE_APPROVAL_ROUTE_V1_0)

## Related Integrations

- CPQ-Salesforce Sync (INTEGRATION_CPQ_SALESFORCE_V1_0)

## Used By Applications

- Trade CPQ
