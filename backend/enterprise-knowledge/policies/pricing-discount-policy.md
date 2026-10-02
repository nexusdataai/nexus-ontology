# Pricing & Discount Policy

**Policy ID:** POL-PRICE-001
**Version:** 1.0
**Effective Date:** 2024-01-15
**Owner:** Commercial / Revenue Management
**Risk Level:** High
**Systems Affected:** Salesforce, Oracle ERP
**SCOR Process:** Deliver

## 1. Source of Truth

- Salesforce `Opportunity_Line_Item.Unit_Price` and `Opportunity_Line_Item.Discount_Pct` are the **authoritative sources** for all customer pricing.
- Oracle `AR_Invoice` must reflect Salesforce pricing at the time of order close.
- Any discrepancy between Salesforce and Oracle pricing is resolved in favor of the Salesforce record.

## 2. Maximum Discount by Channel / Tier

| Channel | Tier | Max Discount |
|---|---|---|
| Modern_Trade | Platinum | 18% |
| Modern_Trade | Gold | 15% |
| Modern_Trade | Silver | 12% |
| General_Trade | Platinum | 15% |
| General_Trade | Gold | 12% |
| General_Trade | Silver | 10% |
| HORECA | All | 20% (flat) |
| E-commerce | All | 10% (flat) |

## 3. Minimum Gross Margin Floor

- No transaction may result in a gross margin below **15%** per product category.
- Exception requires **Commercial Director** approval with documented justification including margin impact analysis.
- Margin is calculated using standard cost from `Material_Master.Standard_Cost`.

## 4. Promotion Rules

- Campaign discounts **stack** with tier discount up to a combined maximum of **25%**.
- BOGO promotions are limited to **1 per customer per campaign period**.
- Promotion overlap on substitutable SKUs is **prohibited** — must be flagged by the Demand Forecast workflow before activation.
- All promotions must have a defined start and end date in Salesforce `Campaign`.

## 5. Price Change Approval

| Scenario | Approval Required |
|---|---|
| Within tier max discount | Auto-approved |
| Exceeds tier max by ≤5% | Regional Sales Manager |
| Exceeds tier max by >5% | Commercial Director |
| Any exception below margin floor | CFO |

## 6. Competitive Price Matching

- Price match requests require **documented competitor evidence** (screenshot, published price list, or customer-provided quote).
- Match is limited to **2% below** the verified competitor price.
- Applies only to **Key Value Items** as classified in `Material_Master.KVI_Flag`.
- Price match approval follows the thresholds in Section 5.

## 7. Trade Spend Controls

- Total trade spend per account is capped at **8%** of trailing 12-month revenue.
- Excess requires **VP Sales** approval.
- Trade spend is tracked via Oracle `Cost_Accounting` entries tagged to the customer account.

## 8. Audit Requirements

All pricing exceptions must be logged with:
- Reason for exception
- Approver identity
- Competitive justification (if applicable)
- Margin impact (actual vs. standard)
- Timestamp

## Related Entities
- Account (Salesforce)
- Opportunity (Salesforce)
- Campaign (Salesforce)
- Opportunity_Line_Item (Salesforce)

## Related Workflows
- Demand Forecast Generation (WORKFLOW_DEMAND_FORECAST_V1_0)
- Customer Churn Prediction (WORKFLOW_CUSTOMER_CHURN_V1_0)

## Related Integrations
- SF-SAP Demand Sync (INTEGRATION_SF_SAP_DEMAND_V1_0)

## Used By Applications
- Demand Forecasting
- Customer 360
