// ============================================================================
// Policy Templates — Energy Drink Supply Chain
// ============================================================================

export const POLICY_TEMPLATES = [
  {
    name: 'Credit Limit Policy',
    filename: 'credit-policy.md',
    content: `# Credit Limit Management Policy

**Policy ID:** POL-CREDIT-001
**Version:** 1.0
**Owner:** Finance Department
**Risk Level:** High
**Systems Affected:** Salesforce, Oracle ERP

## 1. Source of Truth

Salesforce \`Account.Credit_Limit__c\` is the authoritative source for customer credit limits.
Oracle AR receives the credit limit via integration sync but cannot override the Salesforce value.

## 2. Credit Limit Constraints

- Maximum allowed value: 5,000,000 USD (for enterprise distributors)
- Minimum value: 0 (credit hold)
- Currency: Base currency of the customer account

## 3. Approval Thresholds

| Change Magnitude | Approval Required | Approver Role | SLA |
|---|---|---|---|
| ≤ 5% increase | Auto-approved | — | Immediate |
| 5-10% increase | Regional Manager | Sales Manager | 24 hours |
| > 10% increase | Finance VP | Finance VP | 48 hours |
| > 1M USD total | CFO approval | CFO | 72 hours |

## 4. Distributor-Specific Rules

- New distributors start with max 100,000 USD credit
- Volume-based credit increases require 6 months payment history
- Seasonal credit bumps (summer peak) require pre-approval by Q1

## 5. Financial Close Restriction

Credit limit modifications blocked during financial close window (see POL-CLOSE-001).
`,
  },
  {
    name: 'Inventory Management Policy',
    filename: 'inventory-policy.md',
    content: `# Inventory Management Policy

**Policy ID:** POL-INV-001
**Version:** 1.0
**Owner:** Supply Chain Operations
**Risk Level:** High
**Systems Affected:** SAP, Oracle ERP, Salesforce

## 1. Source of Truth

SAP is the authoritative source for all inventory data including stock levels, warehouse locations, and lot tracking.

## 2. Stock Level Thresholds

| Product Category | Min Stock (cases) | Max Stock (cases) | Reorder Point | Lead Time |
|---|---|---|---|---|
| Core SKUs (Cola, Lemon) | 10,000 | 50,000 | 15,000 | 5 days |
| Seasonal (Summer Edition) | 5,000 | 30,000 | 8,000 | 10 days |
| New Launch | 2,000 | 15,000 | 5,000 | 14 days |
| Limited Edition | 1,000 | 5,000 | 2,000 | 21 days |

## 3. Expiry Management

- Energy drinks: 12-month shelf life from production
- Warning threshold: 90 days before expiry → trigger discount workflow
- 30 days before expiry → mandatory markdown to 50%
- Expired stock must be removed from SAP within 48 hours

## 4. Warehouse Allocation

- Primary warehouse: Regional distribution center
- Overflow: 3PL partner warehouses (max 30% of total stock)
- Cross-docking allowed for high-velocity SKUs only

## 5. Sync Rules

- SAP stock levels sync to Salesforce every 15 minutes
- Oracle receives inventory valuation daily for GL posting
`,
  },
  {
    name: 'Distribution Policy',
    filename: 'distribution-policy.md',
    content: `# Distribution & Territory Policy

**Policy ID:** POL-DIST-001
**Version:** 1.0
**Owner:** Commercial Operations
**Risk Level:** Medium
**Systems Affected:** Salesforce, SAP, Google Drive

## 1. Territory Management

- Salesforce manages territory assignments (Account.Territory__c)
- Each region has exclusive distributor agreements stored in Google Drive
- Territory conflicts resolved by Regional VP

## 2. Distributor Tiers

| Tier | Annual Volume | Discount | Payment Terms | Credit Limit |
|---|---|---|---|---|
| Platinum | > 1M cases | 15% | Net 60 | 5,000,000 |
| Gold | 500K-1M cases | 10% | Net 45 | 2,000,000 |
| Silver | 100K-500K cases | 7% | Net 30 | 500,000 |
| Bronze | < 100K cases | 5% | Net 15 | 100,000 |

## 3. Regional Pricing

- Base pricing set in Oracle ERP
- Regional adjustments stored in Salesforce (cspmb__Price_Item__c)
- Promotional pricing requires Marketing VP approval
- Maximum regional discount: 20% off list price

## 4. Delivery SLAs

- Metro areas: Next business day
- Regional: 2-3 business days
- Remote/rural: 5-7 business days
- Peak season (June-August): Add 1 day to all SLAs
`,
  },
  {
    name: 'Financial Close Window',
    filename: 'close-window-policy.md',
    content: `# Financial Close Window Policy

**Policy ID:** POL-CLOSE-001
**Version:** 1.0
**Owner:** Finance Operations
**Risk Level:** High
**Systems Affected:** Salesforce, Oracle ERP, SAP

## 1. Close Window Schedule

| Close Type | Start | End | Duration |
|---|---|---|---|
| Monthly | Last business day, 6 PM | 3rd business day, 9 AM | ~3 days |
| Quarter-end | Last 2 business days | 5th business day next Q | ~5 days |
| Year-end | Dec 28 | Jan 10 | ~13 days |

## 2. Restricted Operations

### Salesforce
- Credit limit modifications
- New distributor account creation
- Territory reassignments

### Oracle ERP
- GL journal postings, AR adjustments, invoice write-offs
- Intercompany transactions

### SAP
- Inventory valuation changes
- Cost center modifications
- New warehouse setup

## 3. SOX Compliance

This policy implements SOX Section 404 internal control requirements.
All violations reported to Audit Committee quarterly.
`,
  },
  {
    name: 'RBAC Policy',
    filename: 'rbac-policy.md',
    content: `# Role-Based Access Control Policy

**Policy ID:** POL-RBAC-001
**Version:** 1.0
**Owner:** IT Security
**Risk Level:** High
**Systems Affected:** Salesforce, Oracle ERP, SAP, Google Drive

## 1. Role Definitions

| Role | Salesforce | Oracle | SAP | Google Drive |
|---|---|---|---|---|
| Sales Rep | Own accounts R/W | — | Stock view | Regional folder |
| Regional Manager | All regional R/W | AR view | Regional stock | Regional folder R/W |
| Finance Manager | Credit R/W | Full AR/AP/GL | Cost centers | Finance folder |
| Supply Chain Mgr | Product view | PO view | Full access | Supply chain folder |
| IT Admin | Full access | Full access | Full access | Full access |

## 2. Cross-System Permissions

When an action spans multiple systems, the user must have permissions in ALL affected systems.
Highest risk level from any system applies.

## 3. Separation of Duties

- Credit proposer ≠ Credit approver
- PO creator ≠ PO approver (> 50,000 USD)
- Journal poster ≠ Journal approver
`,
  },
  {
    name: 'Pricing Policy',
    filename: 'pricing-policy.md',
    content: `# Product Pricing Policy

**Policy ID:** POL-PRICE-001
**Version:** 1.0
**Owner:** Commercial Strategy
**Risk Level:** Medium
**Systems Affected:** Salesforce, Oracle ERP

## 1. Price Structure

- List prices maintained in Salesforce (cspmb__Price_Item__c)
- Transfer prices in Oracle for intercompany
- Distributor prices = List price × (1 - tier discount)

## 2. Promotional Pricing

- Max promotional discount: 30% off list
- Promo duration: Max 90 days
- Requires Marketing VP + Finance approval for > 20%
- Promo prices sync to Oracle within 24 hours

## 3. Regional Price Adjustments

- Emerging markets: Up to 40% below US list price
- Premium markets (EU, Japan): Up to 15% above US list price
- Currency hedging applied quarterly by Treasury
`,
  },
  {
    name: 'Order Fulfillment Policy',
    filename: 'order-fulfillment-policy.md',
    content: `# Order Fulfillment Policy

**Policy ID:** POL-FULFILL-001
**Version:** 1.0
**Owner:** Supply Chain Operations
**Risk Level:** Medium
**Systems Affected:** Oracle ERP, SAP, Salesforce

## 1. Order Processing SLAs

| Order Type | Processing | Shipping | Total |
|---|---|---|---|
| Standard | 4 hours | Per delivery SLA | 1-7 days |
| Rush | 2 hours | Next day | 1-2 days |
| Bulk (> 1000 cases) | 8 hours | 3-5 days | 4-6 days |

## 2. Partial Shipment Rules

- Allowed if > 70% of order can be fulfilled
- Backorder remainder auto-created in Oracle
- Customer notified via Salesforce Activity

## 3. Backorder Handling

- Priority: FIFO by order date
- Max backorder duration: 14 days
- Auto-cancel after 14 days with customer notification
`,
  },
  {
    name: 'Data Quality Policy',
    filename: 'data-quality-policy.md',
    content: `# Data Quality & Governance Policy

**Policy ID:** POL-DQ-001
**Version:** 1.0
**Owner:** Data Governance Team
**Risk Level:** Medium
**Systems Affected:** Salesforce, Oracle ERP, SAP, Google Drive

## 1. Master Data Ownership

| Entity | Source of Truth | Synced To |
|---|---|---|
| Customer | Salesforce Account | Oracle AR, SAP Customer Master |
| Product | Salesforce cspmb__Price_Item__c | Oracle Item Master, SAP Material |
| Pricing | Oracle ERP | Salesforce |
| Inventory | SAP | Salesforce (read-only) |
| Financials | Oracle GL | — (no sync) |

## 2. Duplicate Detection

- Salesforce: Fuzzy match on Company Name + Address (run daily)
- Oracle: Exact match on Tax ID (real-time)
- SAP: Material number uniqueness enforced

## 3. Data Quality Metrics

- Completeness target: > 95% required fields populated
- Accuracy target: < 2% discrepancy in cross-system audits
- Timeliness: Sync lag < 15 minutes for critical fields
`,
  },
];

// ============================================================================
// Workflow Templates — Energy Drink Supply Chain
// ============================================================================

export const WORKFLOW_TEMPLATES = [
  {
    name: 'Credit Approval Flow',
    filename: 'credit-approval.yaml',
    content: `id: WF_CREDIT_APPROVAL_V1
name: Credit Approval Flow
version: "1.0"
system: Salesforce
trigger:
  object: Account
  field: Credit_Limit__c
  condition: "Change exceeds auto-approval threshold"
description: >
  Triggered when a distributor credit limit change exceeds the
  auto-approval threshold. Routes through risk assessment and
  manager approval before syncing to Oracle ERP.

steps:
  - order: 1
    name: Validate Pre-requisites
    system: Salesforce
    action: "Check Risk_Tier__c is current, AR balance below threshold, account active"

  - order: 2
    name: Determine Approval Level
    system: Salesforce
    action: "Calculate change %, route to appropriate approver based on threshold"

  - order: 3
    name: Manager Approval
    system: Salesforce
    action: "Approver reviews and approves/rejects with justification"

  - order: 4
    name: Apply Credit Limit
    system: Salesforce
    action: "Update Account.Credit_Limit__c with new value"

  - order: 5
    name: Sync to Oracle ERP
    system: Oracle
    action: "Push new credit limit to AR_Customer.credit_limit"

  - order: 6
    name: Update SAP Customer Master
    system: SAP
    action: "Update payment terms based on new credit tier"

dependencies:
  - entity: Account
    relationship: "Source object"
  - entity: AR_Customer
    system: Oracle
    relationship: "Sync target"
`,
  },
  {
    name: 'Order to Cash',
    filename: 'order-to-cash.yaml',
    content: `id: WF_ORDER_TO_CASH_V1
name: Order to Cash
version: "1.0"
system: Cross-System
trigger:
  object: Opportunity
  field: StageName
  condition: "Opportunity moves to Closed Won"
description: >
  End-to-end order-to-cash process for energy drink distributors.
  Spans Salesforce (order), Oracle (billing), SAP (fulfillment).

steps:
  - order: 1
    name: Create Sales Order
    system: Salesforce
    action: "Convert Opportunity to Order with line items and pricing"

  - order: 2
    name: Credit Check
    system: Oracle
    action: "Verify customer credit limit covers order value"

  - order: 3
    name: Check Inventory
    system: SAP
    action: "Verify stock availability for all SKUs in order"

  - order: 4
    name: Reserve Inventory
    system: SAP
    action: "Create reservation for order quantities"

  - order: 5
    name: Create Delivery
    system: SAP
    action: "Generate delivery document and shipping plan"

  - order: 6
    name: Ship & Confirm
    system: SAP
    action: "Post goods issue, update stock, confirm shipment"

  - order: 7
    name: Create Invoice
    system: Oracle
    action: "Generate AR invoice based on delivery confirmation"

  - order: 8
    name: Update Salesforce
    system: Salesforce
    action: "Update Order status, create Activity for tracking"

dependencies:
  - entity: Opportunity
    relationship: "Source entity"
  - entity: Account
    relationship: "Customer"
  - entity: AR_Customer
    system: Oracle
    relationship: "Billing target"
`,
  },
  {
    name: 'Customer Onboarding',
    filename: 'customer-onboarding.yaml',
    content: `id: WF_CUSTOMER_ONBOARDING_V1
name: B2B Distributor Onboarding
version: "1.0"
system: Cross-System
trigger:
  object: Lead
  field: Status
  condition: "Lead converted to Account"
description: >
  Onboard new energy drink distributors across Salesforce, Oracle, and SAP.
  Includes credit assessment, payment terms setup, and warehouse assignment.

steps:
  - order: 1
    name: Create Salesforce Account
    system: Salesforce
    action: "Convert Lead to Account with distributor details"

  - order: 2
    name: Credit Assessment
    system: Salesforce
    action: "Run risk scoring based on D&B data and territory"

  - order: 3
    name: Set Initial Credit Limit
    system: Salesforce
    action: "Assign credit limit based on distributor tier"

  - order: 4
    name: Create Oracle Customer
    system: Oracle
    action: "Provision AR customer record with payment terms"

  - order: 5
    name: Create SAP Customer Master
    system: SAP
    action: "Create customer master with delivery addresses and warehouse assignment"

  - order: 6
    name: Upload Distributor Agreement
    system: Google Drive
    action: "Store signed distribution agreement in regional folder"

  - order: 7
    name: Verify & Activate
    system: Cross-System
    action: "Cross-system consistency check, activate customer"

dependencies:
  - entity: Lead
    relationship: "Source"
  - entity: Account
    relationship: "Created entity"
`,
  },
  {
    name: 'Supply Chain Replenishment',
    filename: 'supply-chain-replenishment.yaml',
    content: `id: WF_REPLENISHMENT_V1
name: Supply Chain Replenishment
version: "1.0"
system: SAP
trigger:
  object: Material
  field: Stock_Level
  condition: "Stock falls below reorder point"
description: >
  Automated replenishment when warehouse stock for energy drink SKUs
  falls below the reorder point defined in inventory policy.

steps:
  - order: 1
    name: Detect Low Stock
    system: SAP
    action: "MRP run identifies materials below reorder point"

  - order: 2
    name: Generate Purchase Requisition
    system: SAP
    action: "Auto-create PR for reorder quantity"

  - order: 3
    name: Approve Purchase Order
    system: SAP
    action: "Manager approves PO (auto-approve if < 50K USD)"

  - order: 4
    name: Send to Supplier
    system: SAP
    action: "Transmit PO to bottling plant / supplier via EDI"

  - order: 5
    name: Receive Goods
    system: SAP
    action: "Warehouse receives, quality check, goods receipt posting"

  - order: 6
    name: Update Oracle Financials
    system: Oracle
    action: "Post AP invoice for received goods, update cost centers"

  - order: 7
    name: Update Salesforce Availability
    system: Salesforce
    action: "Sync new stock levels to product availability fields"

dependencies:
  - entity: Material
    system: SAP
    relationship: "Monitored entity"
`,
  },
  {
    name: 'Product Launch',
    filename: 'product-launch.yaml',
    content: `id: WF_PRODUCT_LAUNCH_V1
name: New Product Launch
version: "1.0"
system: Cross-System
trigger:
  object: Product
  field: Status
  condition: "New SKU approved for launch"
description: >
  Launch a new energy drink SKU across all systems — from product
  creation to distributor notification and initial inventory setup.

steps:
  - order: 1
    name: Create Product in Salesforce
    system: Salesforce
    action: "Create cspmb__Price_Item__c with pricing tiers"

  - order: 2
    name: Setup Oracle Item Master
    system: Oracle
    action: "Create item with cost, GL accounts, tax category"

  - order: 3
    name: Create SAP Material
    system: SAP
    action: "Create material master with BOM, warehouse bins, shelf life"

  - order: 4
    name: Initial Inventory Load
    system: SAP
    action: "Goods receipt for initial production batch"

  - order: 5
    name: Upload Product Sheet
    system: Google Drive
    action: "Store product datasheet, images, marketing materials"

  - order: 6
    name: Notify Distributors
    system: Salesforce
    action: "Mass email to distributor contacts with availability date"

dependencies:
  - entity: cspmb__Price_Item__c
    relationship: "Product entity"
`,
  },
  {
    name: 'Risk Assessment',
    filename: 'risk-assessment.yaml',
    content: `id: WF_RISK_ASSESSMENT_V1
name: Customer Risk Assessment
version: "1.0"
system: Salesforce
trigger:
  object: Account
  field: Risk_Tier__c
  condition: "New account or 90-day re-evaluation cycle"
description: >
  Evaluate distributor risk tier based on payment history, volume,
  and external credit scoring. Drives credit limits and collection priority.

steps:
  - order: 1
    name: Gather Financial Data
    system: Salesforce
    action: "Pull Account revenue, payment history from Oracle AR"

  - order: 2
    name: External Credit Check
    system: External
    action: "Query D&B / credit bureau API"

  - order: 3
    name: Calculate Risk Score
    system: Internal
    action: "Weighted model: Payment history 30%, Credit score 25%, AR aging 20%, Volume 15%, Tenure 10%"

  - order: 4
    name: Assign Risk Tier
    system: Salesforce
    action: "Map score to tier: 80-100=Low, 60-79=Medium, 40-59=High, 0-39=Critical"

  - order: 5
    name: Update Downstream
    system: Oracle
    action: "Push Risk_Tier to Oracle AR collection_priority"

dependencies:
  - entity: Account
    relationship: "Target"
`,
  },
];

// ============================================================================
// Integration Templates — Energy Drink Supply Chain
// ============================================================================

export const INTEGRATION_TEMPLATES = [
  {
    name: 'SF-Oracle Customer Sync',
    filename: 'sf-oracle-customer-sync.yaml',
    content: `id: INT_SF_ORACLE_CUSTOMER_V1
name: Salesforce to Oracle Customer Sync
version: "1.0"
source_system: Salesforce
target_system: Oracle
sync_type: bidirectional
frequency: "Near real-time (15-minute interval)"
description: >
  Customer master data sync between Salesforce CRM and Oracle AR
  for energy drink distributors. Salesforce is source of truth for
  customer identity; Oracle is source of truth for financials.

mappings:
  - name: Customer Master
    source_object: Account
    target_object: AR_Customer
    direction: Salesforce → Oracle
    fields:
      - source: Account.Name
        target: AR_Customer.customer_name
        direction: "source_to_target"
      - source: Account.Credit_Limit__c
        target: AR_Customer.credit_limit
        direction: "source_to_target"
      - source: Account.Risk_Tier__c
        target: AR_Customer.collection_priority
        direction: "source_to_target"
      - source: Account.BillingAddress
        target: AR_Customer.bill_to_address
        direction: "source_to_target"
      - source: AR_Customer.ar_balance
        target: Account.AR_Balance__c
        direction: "target_to_source"

failure_handling:
  retry_count: 3
  retry_interval: "5 minutes"
  alert_on_failure: "finance-ops@energydrink.com"
  fallback: "Salesforce value is authoritative"

dependencies:
  - entity: Account
    relationship: "Source entity"
`,
  },
  {
    name: 'SF-Oracle Order Sync',
    filename: 'sf-oracle-order-sync.yaml',
    content: `id: INT_SF_ORACLE_ORDER_V1
name: Salesforce to Oracle Order Sync
version: "1.0"
source_system: Salesforce
target_system: Oracle
sync_type: bidirectional
frequency: "Real-time (event-driven)"
description: >
  Order sync from Salesforce Opportunities to Oracle Order Management.
  Invoice data syncs back from Oracle to Salesforce for visibility.

mappings:
  - name: Order Creation
    source_object: Opportunity
    target_object: Oracle_Sales_Order
    direction: Salesforce → Oracle
    fields:
      - source: Opportunity.Amount
        target: Oracle_Sales_Order.order_total
        direction: "source_to_target"
      - source: Opportunity.AccountId
        target: Oracle_Sales_Order.customer_id
        direction: "source_to_target"
      - source: Opportunity.CloseDate
        target: Oracle_Sales_Order.requested_date
        direction: "source_to_target"

  - name: Invoice Back-sync
    source_object: AR_Invoice
    target_object: Opportunity
    direction: Oracle → Salesforce
    fields:
      - source: AR_Invoice.invoice_number
        target: Opportunity.Invoice_Number__c
        direction: "source_to_target"
      - source: AR_Invoice.invoice_amount
        target: Opportunity.Invoice_Amount__c
        direction: "source_to_target"

failure_handling:
  retry_count: 5
  alert_on_failure: "order-ops@energydrink.com"

dependencies:
  - entity: Opportunity
    relationship: "Source entity"
`,
  },
  {
    name: 'SF-SAP Inventory Sync',
    filename: 'sf-sap-inventory.yaml',
    content: `id: INT_SF_SAP_INVENTORY_V1
name: SAP to Salesforce Inventory Sync
version: "1.0"
source_system: SAP
target_system: Salesforce
sync_type: unidirectional
frequency: "Every 15 minutes"
description: >
  Product availability and stock levels from SAP warehouses
  synced to Salesforce for sales team visibility and ATP checks.

mappings:
  - name: Stock Levels
    source_object: SAP_Material_Stock
    target_object: cspmb__Price_Item__c
    direction: SAP → Salesforce
    fields:
      - source: SAP_Material_Stock.available_qty
        target: cspmb__Price_Item__c.Available_Stock__c
        direction: "source_to_target"
      - source: SAP_Material_Stock.warehouse
        target: cspmb__Price_Item__c.Primary_Warehouse__c
        direction: "source_to_target"
      - source: SAP_Material_Stock.next_production_date
        target: cspmb__Price_Item__c.Next_Available__c
        direction: "source_to_target"

failure_handling:
  retry_count: 3
  alert_on_failure: "supply-chain@energydrink.com"

dependencies:
  - entity: cspmb__Price_Item__c
    relationship: "Target entity"
`,
  },
  {
    name: 'Oracle-SAP Finance Sync',
    filename: 'oracle-sap-finance.yaml',
    content: `id: INT_ORACLE_SAP_FINANCE_V1
name: Oracle to SAP Finance Sync
version: "1.0"
source_system: Oracle
target_system: SAP
sync_type: bidirectional
frequency: "Daily batch (overnight)"
description: >
  Financial data sync between Oracle ERP and SAP for cost centers,
  GL journals, and intercompany transactions for the energy drink
  manufacturing and distribution operations.

mappings:
  - name: Cost Center Sync
    source_object: Oracle_Cost_Center
    target_object: SAP_Cost_Center
    direction: Oracle → SAP
    fields:
      - source: Oracle_Cost_Center.cc_code
        target: SAP_Cost_Center.kostl
        direction: "source_to_target"
      - source: Oracle_Cost_Center.description
        target: SAP_Cost_Center.description
        direction: "source_to_target"

  - name: Inventory Valuation
    source_object: SAP_Material_Valuation
    target_object: GL_Journal
    direction: SAP → Oracle
    fields:
      - source: SAP_Material_Valuation.total_value
        target: GL_Journal.amount
        direction: "source_to_target"
      - source: SAP_Material_Valuation.valuation_date
        target: GL_Journal.effective_date
        direction: "source_to_target"

failure_handling:
  retry_count: 3
  alert_on_failure: "finance-integration@energydrink.com"

dependencies:
  - entity: GL_Journal
    system: Oracle
    relationship: "Target"
`,
  },
  {
    name: 'Google Drive Data Ingestion',
    filename: 'gdrive-data-ingestion.yaml',
    content: `id: INT_GDRIVE_INGEST_V1
name: Google Drive Data Ingestion
version: "1.0"
source_system: Google Drive
target_system: Salesforce
sync_type: unidirectional
frequency: "Daily (scheduled 6 AM UTC)"
description: >
  Ingest regional sales reports, demand forecasts, and distributor
  performance data from Google Drive into Salesforce and Oracle
  for analytics and planning.

mappings:
  - name: Regional Sales Reports
    source_object: GDrive_Regional_Sales_CSV
    target_object: Salesforce_Analytics_Object
    direction: Google Drive → Salesforce
    fields:
      - source: GDrive_Regional_Sales_CSV.region
        target: Salesforce_Analytics_Object.Region__c
        direction: "source_to_target"
      - source: GDrive_Regional_Sales_CSV.volume_cases
        target: Salesforce_Analytics_Object.Volume__c
        direction: "source_to_target"
      - source: GDrive_Regional_Sales_CSV.revenue
        target: Salesforce_Analytics_Object.Revenue__c
        direction: "source_to_target"

  - name: Demand Forecasts
    source_object: GDrive_Demand_Forecast
    target_object: SAP_Planned_Demand
    direction: Google Drive → SAP
    fields:
      - source: GDrive_Demand_Forecast.sku
        target: SAP_Planned_Demand.material_number
        direction: "source_to_target"
      - source: GDrive_Demand_Forecast.forecast_qty
        target: SAP_Planned_Demand.planned_quantity
        direction: "source_to_target"

failure_handling:
  retry_count: 2
  alert_on_failure: "data-ops@energydrink.com"

dependencies:
  - entity: Google_Drive_Folder
    system: Google Drive
    relationship: "Source"
`,
  },
];
