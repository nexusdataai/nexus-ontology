# Data Freshness & Latency Policy

**Policy ID:** POL-DATA-001
**Version:** 1.0
**Effective Date:** 2024-01-15
**Owner:** Data Engineering / IT Operations
**Risk Level:** Medium
**Systems Affected:** All (Salesforce, SAP, Oracle, Google Drive, Social Listening, File Uploads)
**SCOR Process:** Enable

## 1. Purpose

This policy defines the maximum acceptable data latency for each source system feeding the semantic ontology layer. Stale data beyond the defined SLA triggers alerts and **disqualifies** affected data from AI workflow inputs until freshness is restored.

## 2. Structured System SLAs

| Source System | Data Scope | Freshness SLA |
|---|---|---|
| Salesforce CRM | Accounts, Opportunities, Campaigns | Near real-time (<5 min) |
| SAP Inventory | `Inventory_Position`, `Batch_Master` | Daily (by 06:00 UTC) |
| SAP Master Data | `Material_Master`, `Vendor_Master`, `Plant_Master` | On-change + daily full sync |
| SAP Transactions | `Production_Order`, `Goods_Receipt`, `Delivery_Document` | Near real-time (<15 min) |
| Oracle Finance | `AR_Invoice`, `AR_Payment`, `GL_Journal` | 15-minute sync interval |
| Oracle Operations | `AP_Invoice`, `Purchase_Order`, `Cost_Accounting` | 15-minute sync interval |

## 3. Unstructured Source SLAs

| Source System | Data Scope | Freshness SLA |
|---|---|---|
| Google Drive | `Contract_Document`, `Sustainability_Report` | On-upload + daily scan for new files |
| File Uploads | `Invoice_Upload`, `Lab_Report_Upload` | On-upload, processing within 30 minutes |
| Social Listening | `Market_Signal`, `Brand_Sentiment`, `Commodity_Price` | 4-hour refresh cycle |

## 4. Staleness Detection

- Each data feed is monitored for its **last-successful-sync** timestamp.
- If the sync gap exceeds **2× SLA**, an alert is raised to Data Engineering.
- If the sync gap exceeds **3× SLA**, affected data is marked as **stale** and excluded from AI workflow inputs.

## 5. Impact on AI Workflows

| Workflow Type | Data Requirement | Max Tolerable Latency |
|---|---|---|
| Demand Forecasting | SAP inventory data | <24 hours |
| Real-time workflows (O2C monitoring, disruption response) | Transaction data | <15 minutes |
| Batch workflows (spend analysis, churn prediction) | All sources | Up to 24 hours |

## 6. Monitoring and Alerting

- **Data freshness dashboard** maintained per source system.
- Automated alerts triggered at the **2× SLA** threshold.
- Weekly freshness report distributed to the Data Engineering lead.

## Related Entities
- All data source entities across Salesforce, SAP, Oracle, Google_Drive, Social_Listening, File_Uploads

## Related Workflows
- All 12 supply chain workflows

## Related Integrations
- All 6 integrations

## Used By Applications
- All 8 supply chain applications
