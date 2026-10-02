# Quality Assurance Policy

**Policy ID:** POL-QA-001
**Version:** 1.0
**Effective Date:** 2024-01-15
**Owner:** Quality Assurance Department
**Risk Level:** Critical
**Systems Affected:** SAP, File Uploads
**SCOR Process:** Make

## 1. Source of Truth

- SAP `Quality_Inspection_Lot` and `Quality_Test_Result` are the **authoritative sources** for structured QC data.
- `Lab_Report_Upload` is authoritative for unstructured lab results.

## 2. Inspection Requirements

- **Incoming materials:** 100% inspection for new vendors; sampling per AQL (Acceptable Quality Level) for established vendors.
- **In-process:** Inspection per production line SOP.
- **Final:** Every batch must be inspected before release.

## 3. Specification Limits

- Each `Material_Master` must have defined specification limits per test.
- Limits are maintained in `Quality_Test_Result` via `Spec_Lower_Limit` and `Spec_Upper_Limit`.
- Any result outside specification limits triggers an **automatic batch hold**.

## 4. Batch Hold and Release

- Any failed test sets `Batch_Master.Status` = **Blocked**.
- Release authority:

| Deviation Severity | Release Approver |
|---|---|
| Minor deviation | QC Manager |
| Major deviation | Quality Director |
| Critical food safety deviation | **No release possible** |

## 5. Repeat Failure Escalation

| Consecutive Batch Failures | Action Required |
|---|---|
| 1 batch fail | QC Supervisor review |
| 2 consecutive | QC Manager + root cause analysis required |
| 3+ consecutive | Production line **STOP** + Plant Manager + Quality Director; line restart requires corrective action approval |

## 6. Recall Procedures

Recall is triggered when:
- Consumer safety risk is confirmed
- Regulatory notification is received
- Systematic contamination is detected

**Recall classification:**

| Class | Type |
|---|---|
| Class I | Voluntary |
| Class II | Mandatory |
| Class III | Precautionary |

- Traceability via `Batch_Master` forward/backward trace must complete in **<30 minutes**.

## 7. Lab Report Processing

- NLP-extracted results from `Lab_Report_Upload` must have `Extraction_Confidence` **>0.85** to auto-populate structured fields.
- Results below the confidence threshold require **manual verification**.

## 8. Audit and Retention

- All QC records are retained for a minimum of **5 years**.
- Regulatory audit access must be provided within **24 hours** of request.

## Related Entities
- Quality_Inspection_Lot (SAP)
- Quality_Test_Result (SAP)
- Batch_Master (SAP)
- Production_Order (SAP)
- Lab_Report_Upload (File_Uploads)

## Related Workflows
- Quality Deviation Response (WORKFLOW_QUALITY_DEVIATION_V1_0)
- Production Scheduling (WORKFLOW_PRODUCTION_SCHEDULING_V1_0)

## Related Integrations
- SAP Inventory Feed (INTEGRATION_SAP_INVENTORY_FEED_V1_0)
- Unstructured Extraction (INTEGRATION_UNSTRUCTURED_EXTRACT_V1_0)

## Used By Applications
- Production & Quality
