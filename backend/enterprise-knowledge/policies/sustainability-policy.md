# Sustainability & ESG Policy

**Policy ID:** POL-ESG-001
**Version:** 1.0
**Effective Date:** 2024-01-15
**Owner:** Sustainability & Corporate Affairs
**Risk Level:** Medium
**Systems Affected:** SAP, Oracle ERP, Social Listening, Google Drive
**SCOR Process:** Enable

## 1. Carbon Intensity Targets

- Year-over-year reduction target: **5%** in kg CO₂e per liter of beverage produced.
- Scope 1+2 baseline established from `Plant_Master` energy consumption data.
- Scope 3 estimated from Oracle `Purchase_Order` supplier volumes and industry emission factors.
- Each plant must report monthly carbon intensity to the Sustainability Lead.

## 2. Water Usage Targets

- Water ratio target: **<2.0 liters of water per liter of beverage** by 2027.
- Current baseline tracked per `Plant_Master.Water_Ratio`.
- Plants exceeding **2.5 L/L** for any week require an immediate investigation and corrective action plan.

## 3. Packaging Sustainability

| Metric | 2025 Target | 2026 Target | 2027 Target |
|---|---|---|---|
| Recycled content (%) | 30% | 40% | 50% |

- Tracked via `Material_Master.Recycled_Content_Pct`.
- All new product launches **must** achieve a minimum **25%** recycled content.
- `Recyclability_Score` target: **>3.5** average across the product portfolio.

## 4. Energy Efficiency

- Measured as **kWh per 1,000 liters produced**.
- Target: **3%** year-over-year improvement.
- Plants exceeding energy budget by **>10%** are flagged for a mandatory energy audit.

## 5. Waste Reduction

- Perishable waste target: **<3%** of production volume.
- Tracked via `Batch_Master` expiry dates and `Inventory_Position` write-offs.
- Food donation rate target: **>40%** of near-expiry product deemed safe for donation.

## 6. ESG Reporting Obligations

- **Quarterly:** Internal sustainability dashboard update.
- **Annually:** GRI / SASB / CDP disclosure.
- `Sustainability_Report` documents extracted for trend comparison.
- All data must have a **complete audit trail** from source system to reported metric.

## 7. Negative Sentiment Response

- If `Brand_Sentiment` score on ESG-related topics drops below **30** for **7+ consecutive days**, Corporate Affairs must be notified within **24 hours** for response plan activation.
- Monitored via the Social Listening integration.

## 8. Non-Compliance Escalation

| Scope | Action | Timeline |
|---|---|---|
| Plant-level target miss | Plant Manager + Sustainability Lead review | Within 10 days |
| Corporate-level target miss | Board ESG Committee briefing | Within 30 days |

## Related Entities
- Plant_Master (SAP)
- Material_Master (SAP)
- Shipment (SAP)
- Delivery_Document (SAP)
- Brand_Sentiment (Social_Listening)
- Sustainability_Report (Google_Drive)

## Related Workflows
- ESG Reporting (WORKFLOW_ESG_REPORTING_V1_0)

## Related Integrations
- SAP Inventory Feed (INTEGRATION_SAP_INVENTORY_FEED_V1_0)
- Social Listening Feed (INTEGRATION_SOCIAL_LISTENING_V1_0)

## Used By Applications
- ESG & Sustainability Tracker
