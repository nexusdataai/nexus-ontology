/**
 * Control Plane: semantic layer stats, knowledge pipelines, knowledge index,
 * semantic explorer, and the policy / workflow / integration editors.
 * (The embedded Knowledge Processor studio reads journey routes; see automation.ts.)
 */
import {
  type SampleRoute, ENTITIES,
  ago, asObj, between, pad, raw, entityByName, systemOf, HOUR, DAY,
} from '../fixtures';

// ---------------------------------------------------------------------------
// Knowledge content: policies, workflows, integrations
// ---------------------------------------------------------------------------

interface Policy { id: string; file: string; title: string; owner: string; risk: string; systems: string[]; sourceOfTruth: string; rules: string[]; table?: string[][] }

const POLICIES: Policy[] = [
  { id: 'POL-CREDIT-001', file: 'credit-policy.md', title: 'Credit Limit Management Policy', owner: 'Finance Department', risk: 'High', systems: ['Salesforce', 'Oracle ERP'],
    sourceOfTruth: 'Salesforce `Account.Credit_Limit__c` is the authoritative credit limit. Oracle receivables receives it by sync and cannot override it.',
    rules: ['New distributors start with a maximum of 100,000 USD credit', 'Volume-based increases need 6 months of payment history', 'Limit changes are blocked during the financial close window (see POL-CLOSE-001)'],
    table: [['Change', 'Approval required', 'Approver', 'SLA'], ['Up to 5% increase', 'Auto-approved', '-', 'Immediate'], ['5-10% increase', 'Yes', 'Regional Sales Manager', '24 hours'], ['Over 10% increase', 'Yes', 'Finance VP', '48 hours'], ['Over 1M USD total', 'Yes', 'CFO', '72 hours']] },
  { id: 'POL-INV-001', file: 'inventory-policy.md', title: 'Inventory Management Policy', owner: 'Supply Chain Operations', risk: 'High', systems: ['SAP', 'Oracle ERP', 'Salesforce'],
    sourceOfTruth: 'SAP is the authoritative source for stock levels, warehouse locations and batch tracking.',
    rules: ['Energy drinks have a 12-month shelf life from production', 'Stock within 90 days of expiry triggers the discount workflow', 'Blocked stock older than 7 days is escalated to Quality'],
    table: [['Category', 'Min stock (cases)', 'Max stock (cases)', 'Reorder point', 'Lead time'], ['Core SKUs', '10,000', '50,000', '15,000', '5 days'], ['Seasonal', '5,000', '30,000', '8,000', '10 days'], ['New launch', '2,000', '15,000', '5,000', '14 days']] },
  { id: 'POL-O2C-002', file: 'dispute-policy.md', title: 'Invoice Dispute Policy', owner: 'Accounts Receivable', risk: 'Medium', systems: ['Oracle ERP', 'Salesforce'],
    sourceOfTruth: 'Oracle receivables holds the invoice and its dispute status. Salesforce shows the dispute on the account.',
    rules: ['Quantity differences above 2% open a dispute case automatically', 'Disputes are resolved within 10 working days', 'Credit notes above 25,000 USD need Finance Controller approval'] },
  { id: 'POL-O2C-004', file: 'dunning-policy.md', title: 'Dunning and Collections Policy', owner: 'Accounts Receivable', risk: 'Medium', systems: ['Oracle ERP', 'Salesforce'],
    sourceOfTruth: 'Oracle receivables is the authoritative source for invoice ageing.',
    rules: ['First notice at 1 day past due, second at 31 days, final at 61 days', 'Accounts above 90 days past due go on credit hold', 'Key accounts are contacted by the account owner before any notice'],
    table: [['Ageing bucket', 'Action', 'Owner'], ['1-30 days', 'Reminder email', 'Collections'], ['31-60 days', 'Second notice and call', 'Collections'], ['61-90 days', 'Final notice', 'Credit Manager'], ['Over 90 days', 'Credit hold', 'Finance VP']] },
  { id: 'POL-CLOSE-001', file: 'close-window-policy.md', title: 'Financial Close Window', owner: 'Finance Department', risk: 'High', systems: ['Oracle ERP', 'SAP', 'Salesforce'],
    sourceOfTruth: 'The Oracle general ledger calendar defines the close window.',
    rules: ['The close window runs from working day -2 to working day +3 of each month', 'Credit limit, price and payment term changes are blocked during the window', 'Exceptions need written CFO approval'] },
  { id: 'POL-PRICE-001', file: 'pricing-policy.md', title: 'Pricing and Discount Policy', owner: 'Commercial Finance', risk: 'High', systems: ['Salesforce', 'SAP'],
    sourceOfTruth: 'The Salesforce price book is the authoritative list price. SAP holds the conditions used for invoicing.',
    rules: ['Quotes below a 15% margin need Finance approval', 'Promotional discounts may not exceed the tier maximum', 'Price changes take effect on the first day of a month'],
    table: [['Discount', 'Approver'], ['Up to 10%', 'Account Manager'], ['10-18%', 'Regional Sales Manager'], ['Over 18%', 'Commercial Director']] },
  { id: 'POL-FULFIL-001', file: 'order-fulfillment-policy.md', title: 'Order Fulfillment Policy', owner: 'Customer Service', risk: 'Medium', systems: ['Salesforce', 'SAP'],
    sourceOfTruth: 'SAP delivery documents are the record of what shipped and when.',
    rules: ['Orders confirmed before 14:00 ship the next working day', 'Partial deliveries are allowed for key accounts only', 'Deliveries more than 2 days late are logged as SLA breaches'] },
  { id: 'POL-DIST-001', file: 'distribution-policy.md', title: 'Distribution and Territory Policy', owner: 'Sales Operations', risk: 'Medium', systems: ['Salesforce'],
    sourceOfTruth: 'Salesforce territories define which distributor serves which region.',
    rules: ['One primary distributor per territory', 'Cross-territory sales need approval from both regional managers', 'Territory changes take effect at quarter start'] },
  { id: 'POL-PROC-001', file: 'procurement-policy.md', title: 'Procurement and Sourcing Policy', owner: 'Procurement', risk: 'High', systems: ['SAP', 'Oracle ERP', 'Google Drive'],
    sourceOfTruth: 'SAP purchase orders are the commitment. The signed contract in Google Drive sets the price.',
    rules: ['Spend above 50,000 USD needs three quotes', 'Purchase order prices may not exceed the contract price by more than 5%', 'Single-source materials need a qualified second source within 12 months'] },
  { id: 'POL-MATCH-001', file: 'three-way-match-policy.md', title: 'Three-Way Match Policy', owner: 'Accounts Payable', risk: 'Medium', systems: ['Oracle ERP', 'SAP'],
    sourceOfTruth: 'Oracle payables holds the supplier invoice. SAP holds the purchase order and goods receipt.',
    rules: ['Invoices are paid only when purchase order, receipt and invoice agree', 'Quantity tolerance is 2%, price tolerance is 1%', 'Mismatches are held and routed to the buyer'] },
  { id: 'POL-QUAL-001', file: 'quality-release-policy.md', title: 'Quality Release Policy', owner: 'Quality Assurance', risk: 'High', systems: ['SAP', 'File Uploads'],
    sourceOfTruth: 'SAP inspection lots record the release decision. Lab reports are stored as uploads.',
    rules: ['No batch ships without a released inspection lot', 'Out-of-specification results quarantine the batch', 'Lab reports are retained for 5 years'] },
  { id: 'POL-DQ-001', file: 'data-quality-policy.md', title: 'Data Quality Policy', owner: 'Data Governance', risk: 'Medium', systems: ['Salesforce', 'Oracle ERP', 'SAP'],
    sourceOfTruth: 'Each entity has one system of record, named in its mapping rule.',
    rules: ['Mandatory fields may have at most 2% null values', 'Customer and supplier records are de-duplicated weekly', 'Mapping rule changes are reviewed by the data owner'] },
  { id: 'POL-RBAC-001', file: 'rbac-policy.md', title: 'Access Control Policy', owner: 'IT Security', risk: 'High', systems: ['Salesforce', 'Oracle ERP', 'SAP'],
    sourceOfTruth: 'The platform role model defines who can read, write and approve.',
    rules: ['High-risk writes need a second approver', 'Access is reviewed every quarter', 'Service accounts may not approve their own actions'] },
  { id: 'POL-ESG-001', file: 'sustainability-policy.md', title: 'Sustainability Reporting Policy', owner: 'Sustainability Office', risk: 'Low', systems: ['SAP', 'Google Drive'],
    sourceOfTruth: 'Plant meters in SAP are the source for energy and water figures.',
    rules: ['Emissions are reported per case produced', 'Recycled content targets are set per packaging type', 'Reports follow GRI and CDP formats'] },
];

const policyContent = (p: Policy) => [
  `# ${p.title}`, '',
  `**Policy ID:** ${p.id}`, '**Version:** 1.0', `**Owner:** ${p.owner}`, `**Risk Level:** ${p.risk}`, `**Systems Affected:** ${p.systems.join(', ')}`, '',
  '## 1. Source of Truth', '', p.sourceOfTruth, '',
  '## 2. Rules', '', ...p.rules.map(r => `- ${r}`), '',
  ...(p.table ? ['## 3. Thresholds', '', `| ${p.table[0].join(' | ')} |`, `|${p.table[0].map(() => '---').join('|')}|`, ...p.table.slice(1).map(row => `| ${row.join(' | ')} |`), ''] : []),
].join('\n');

interface Workflow { id: string; file: string; name: string; system: string; object: string; field: string; condition: string; description: string; steps: [string, string, string][] }

const WORKFLOWS: Workflow[] = [
  { id: 'WF_ORDER_TO_CASH_V1', file: 'order-to-cash.yaml', name: 'Order to Cash', system: 'Salesforce', object: 'Opportunity', field: 'StageName', condition: 'Stage changes to Closed Won', description: 'From a won order to cash received, across Salesforce, SAP and Oracle.', steps: [['Check credit', 'Salesforce', 'Compare open balance and order value with the credit limit'], ['Create delivery', 'SAP', 'Create the outbound delivery from available stock'], ['Post goods issue', 'SAP', 'Confirm picking and post goods issue'], ['Raise invoice', 'Oracle', 'Create the customer invoice from the delivery'], ['Apply payment', 'Oracle', 'Match the receipt to the invoice']] },
  { id: 'WF_CREDIT_APPROVAL_V1', file: 'credit-approval.yaml', name: 'Credit Approval Flow', system: 'Salesforce', object: 'Account', field: 'Credit_Limit__c', condition: 'Change exceeds the auto-approval threshold', description: 'Routes a credit limit change through risk assessment and approval, then syncs it to Oracle.', steps: [['Validate pre-requisites', 'Salesforce', 'Risk tier is current and the account is active'], ['Determine approval level', 'Salesforce', 'Route by size of change'], ['Approve', 'Salesforce', 'Approver accepts or rejects with a reason'], ['Sync to Oracle', 'Oracle', 'Push the new limit to AR_Customer.credit_limit']] },
  { id: 'WF_CUSTOMER_ONBOARDING_V1', file: 'customer-onboarding.yaml', name: 'Customer Onboarding', system: 'Salesforce', object: 'Account', field: 'Type', condition: 'A new distributor account is created', description: 'Sets up a new customer in all three systems.', steps: [['Collect documents', 'Salesforce', 'Trade licence and bank details'], ['Credit check', 'Salesforce', 'Set the initial risk tier and limit'], ['Create receivables account', 'Oracle', 'Create AR_Customer with payment terms'], ['Create ship-to', 'SAP', 'Create the customer master and ship-to addresses']] },
  { id: 'WF_REPLENISHMENT_V1', file: 'supply-chain-replenishment.yaml', name: 'Supply Chain Replenishment', system: 'SAP', object: 'Inventory_Position', field: 'Unrestricted_Qty', condition: 'Stock falls below the reorder point', description: 'Replenishes a plant by transfer or production.', steps: [['Check surplus plants', 'SAP', 'Find plants above 45 days of supply'], ['Propose transfer', 'SAP', 'Create a stock transport order'], ['Plan production', 'SAP', 'Create a planned order if no surplus exists'], ['Notify sales', 'Salesforce', 'Flag affected open orders']] },
  { id: 'WF_PRODUCT_LAUNCH_V1', file: 'product-launch.yaml', name: 'Product Launch', system: 'SAP', object: 'Material_Master', field: 'Material_Type', condition: 'A new finished good is released', description: 'Brings a new SKU to market.', steps: [['Create material', 'SAP', 'Material master, bill of materials and routing'], ['Set price', 'Salesforce', 'Add to the price book'], ['Build launch stock', 'SAP', 'Production orders for the opening stock'], ['Open listings', 'Salesforce', 'Create launch quotes for key accounts']] },
  { id: 'WF_RISK_ASSESSMENT_V1', file: 'risk-assessment.yaml', name: 'Supplier Risk Assessment', system: 'SAP', object: 'Vendor_Master', field: 'Risk_Score', condition: 'Risk score rises by 15 points or more', description: 'Reviews a supplier whose risk has risen.', steps: [['Gather signals', 'Social Listening', 'Collect recent market signals for the supplier'], ['Review contract', 'Google Drive', 'Check SLA and penalty terms'], ['Decide action', 'SAP', 'Keep, restrict or block the supplier'], ['Qualify second source', 'SAP', 'Start qualification where single-sourced']] },
  { id: 'WF_DUNNING_V1', file: 'dunning.yaml', name: 'Dunning Run', system: 'Oracle', object: 'AR_Invoice', field: 'due_date', condition: 'Invoice passes its due date', description: 'Sends collection notices by ageing bucket.', steps: [['Select invoices', 'Oracle', 'Open invoices past due'], ['Choose notice level', 'Oracle', 'By days past due'], ['Send notice', 'Oracle', 'Email the billing contact'], ['Log on account', 'Salesforce', 'Add the notice to the account timeline']] },
  { id: 'WF_DISPUTE_V1', file: 'invoice-dispute.yaml', name: 'Invoice Dispute Resolution', system: 'Oracle', object: 'AR_Invoice', field: 'status', condition: 'Status changes to Disputed', description: 'Resolves a customer dispute.', steps: [['Open case', 'Salesforce', 'Create a case for the account owner'], ['Check delivery', 'SAP', 'Compare delivered and invoiced quantity'], ['Issue credit note', 'Oracle', 'Credit the difference where justified']] },
  { id: 'WF_THREE_WAY_MATCH_V1', file: 'three-way-match.yaml', name: 'Three-Way Match', system: 'Oracle', object: 'AP_Invoice', field: 'match_status', condition: 'A supplier invoice is received', description: 'Matches invoice, purchase order and goods receipt before payment.', steps: [['Read invoice', 'File Uploads', 'Extract header and lines from the upload'], ['Match to order', 'SAP', 'Compare price and quantity with the purchase order'], ['Match to receipt', 'SAP', 'Compare with goods received'], ['Release or hold', 'Oracle', 'Schedule payment or route to the buyer']] },
  { id: 'WF_PO_APPROVAL_V1', file: 'po-approval.yaml', name: 'Purchase Order Approval', system: 'SAP', object: 'Purchase_Order', field: 'Net_Value', condition: 'Order value exceeds 50,000 USD', description: 'Approves a high-value purchase order.', steps: [['Check contract price', 'Google Drive', 'Compare with the contracted price'], ['Check budget', 'Oracle', 'Confirm cost centre budget'], ['Approve', 'SAP', 'Release the purchase order']] },
  { id: 'WF_CONTRACT_RENEWAL_V1', file: 'contract-renewal.yaml', name: 'Contract Renewal', system: 'Google Drive', object: 'Contract_Document', field: 'Expiry_Date', condition: 'Contract expires within 60 days', description: 'Renews or re-tenders a supplier contract.', steps: [['Review performance', 'SAP', 'Delivery and quality scores over the term'], ['Benchmark price', 'Social Listening', 'Compare with commodity price moves'], ['Decide', 'SAP', 'Renew, renegotiate or run an RFx']] },
  { id: 'WF_QUALITY_HOLD_V1', file: 'quality-hold.yaml', name: 'Quality Hold', system: 'SAP', object: 'Production_Order', field: 'Status', condition: 'A lab result is out of specification', description: 'Quarantines a batch and informs customers.', steps: [['Block stock', 'SAP', 'Move the batch to blocked stock'], ['Retest', 'File Uploads', 'Request a confirmatory lab report'], ['Decide', 'SAP', 'Release, rework or scrap'], ['Inform sales', 'Salesforce', 'Flag affected orders']] },
  { id: 'WF_EXPIRY_DISCOUNT_V1', file: 'expiry-discount.yaml', name: 'Near-Expiry Discount', system: 'SAP', object: 'Inventory_Position', field: 'Stock_Status', condition: 'Stock is within 90 days of expiry', description: 'Sells near-expiry stock at a discount.', steps: [['List stock', 'SAP', 'Batches within 90 days of expiry'], ['Set discount', 'Salesforce', 'Create a clearance promotion'], ['Offer to accounts', 'Salesforce', 'Notify eligible distributors']] },
  { id: 'WF_FORECAST_CONSENSUS_V1', file: 'forecast-consensus.yaml', name: 'Forecast Consensus', system: 'Salesforce', object: 'Opportunity', field: 'Amount', condition: 'Monthly planning cycle starts', description: 'Agrees the demand forecast between sales and supply.', steps: [['Publish AI forecast', 'SAP', 'Baseline by SKU and region'], ['Collect overrides', 'Salesforce', 'Sales adjust for promotions'], ['Approve consensus', 'SAP', 'Planner signs off the final number']] },
  { id: 'WF_PROMO_PLANNING_V1', file: 'promotion-planning.yaml', name: 'Promotion Planning', system: 'Salesforce', object: 'Campaign', field: 'Status', condition: 'A campaign moves to Planned', description: 'Plans stock and price for a promotion.', steps: [['Estimate lift', 'Salesforce', 'Expected uplift by account'], ['Reserve stock', 'SAP', 'Raise production for the promotion period'], ['Set promotional price', 'SAP', 'Create the pricing condition']] },
  { id: 'WF_CREDIT_HOLD_V1', file: 'credit-hold.yaml', name: 'Credit Hold', system: 'Oracle', object: 'AR_Customer', field: 'days_past_due', condition: 'Oldest invoice is more than 90 days past due', description: 'Places and releases a credit hold.', steps: [['Place hold', 'Oracle', 'Set the account to credit hold'], ['Block orders', 'Salesforce', 'Stop new orders from being released'], ['Release on payment', 'Oracle', 'Lift the hold when the balance clears']] },
  { id: 'WF_RETURNS_V1', file: 'returns.yaml', name: 'Customer Returns', system: 'Salesforce', object: 'Opportunity', field: 'StageName', condition: 'A return is requested', description: 'Handles returned goods and the credit.', steps: [['Authorise return', 'Salesforce', 'Check reason and eligibility'], ['Receive goods', 'SAP', 'Post the return delivery'], ['Credit customer', 'Oracle', 'Issue the credit note']] },
  { id: 'WF_STOCK_TRANSFER_V1', file: 'stock-transfer.yaml', name: 'Inter-Plant Stock Transfer', system: 'SAP', object: 'Inventory_Position', field: 'Days_Of_Supply', condition: 'A transfer proposal is approved', description: 'Moves stock between plants.', steps: [['Create transport order', 'SAP', 'From the surplus plant'], ['Ship', 'SAP', 'Post goods issue at the sending plant'], ['Receive', 'SAP', 'Post goods receipt at the receiving plant']] },
  { id: 'WF_SUPPLIER_ONBOARDING_V1', file: 'supplier-onboarding.yaml', name: 'Supplier Onboarding', system: 'SAP', object: 'Vendor_Master', field: 'Status', condition: 'A new supplier is proposed', description: 'Qualifies and sets up a supplier.', steps: [['Collect certificates', 'Google Drive', 'Quality and food safety certificates'], ['Audit', 'SAP', 'Score the supplier audit'], ['Create supplier', 'SAP', 'Create the vendor master'], ['Create payables site', 'Oracle', 'Set payment terms and bank details']] },
  { id: 'WF_MONTH_END_CLOSE_V1', file: 'month-end-close.yaml', name: 'Month-End Close', system: 'Oracle', object: 'AR_Invoice', field: 'invoice_date', condition: 'Working day -2 of the month', description: 'Closes the books for the month.', steps: [['Freeze changes', 'Salesforce', 'Block credit and price changes'], ['Reconcile receivables', 'Oracle', 'Clear unapplied receipts'], ['Reconcile stock', 'SAP', 'Post inventory differences'], ['Close period', 'Oracle', 'Close the ledger period']] },
  { id: 'WF_RFX_AWARD_V1', file: 'rfx-award.yaml', name: 'RFx Award', system: 'SAP', object: 'Purchase_Order', field: 'Vendor_ID', condition: 'Bidding closes', description: 'Compares bids and awards the business.', steps: [['Compare bids', 'SAP', 'Price, lead time and compliance'], ['Model scenarios', 'SAP', 'Savings against concentration risk'], ['Approve award', 'SAP', 'Category director signs off']] },
  { id: 'WF_QUOTE_APPROVAL_V1', file: 'quote-approval.yaml', name: 'Trade Quote Approval', system: 'Salesforce', object: 'Opportunity', field: 'Amount', condition: 'Quote margin is below the floor', description: 'Approves a trade quote below the margin floor.', steps: [['Check margin', 'Salesforce', 'Compare with the 15% floor'], ['Finance review', 'Salesforce', 'Controller approves or returns'], ['Convert to order', 'SAP', 'Create the sales order']] },
  { id: 'WF_ESG_REPORTING_V1', file: 'esg-reporting.yaml', name: 'Sustainability Reporting', system: 'SAP', object: 'Plant_Master', field: 'Energy_kWh_Per_Case', condition: 'Quarter end', description: 'Compiles the quarterly sustainability report.', steps: [['Collect plant data', 'SAP', 'Energy, water and waste per plant'], ['Compare with targets', 'Google Drive', 'Read targets from the last report'], ['Publish', 'Google Drive', 'Store the signed report']] },
];

const workflowContent = (w: Workflow) => [
  `id: ${w.id}`, `name: ${w.name}`, 'version: "1.0"', `system: ${w.system}`,
  'trigger:', `  object: ${w.object}`, `  field: ${w.field}`, `  condition: "${w.condition}"`,
  'description: >', `  ${w.description}`, '',
  'steps:',
  ...w.steps.flatMap(([name, system, action], i) => [`  - order: ${i + 1}`, `    name: ${name}`, `    system: ${system}`, `    action: "${action}"`, '']),
  'dependencies:', `  - entity: ${w.object}`, '    relationship: "Source object"', '',
].join('\n');

interface Integration { id: string; file: string; name: string; source: string; target: string; syncType: string; frequency: string; description: string; sourceObject: string; targetObject: string; fields: [string, string][] }

const INTEGRATIONS: Integration[] = [
  { id: 'INT_SF_ORACLE_CUSTOMER_V1', file: 'sf-oracle-customer-sync.yaml', name: 'Salesforce to Oracle Customer Sync', source: 'Salesforce', target: 'Oracle', syncType: 'bidirectional', frequency: 'Near real-time (15-minute interval)', description: 'Customer master data between Salesforce and Oracle receivables.', sourceObject: 'Account', targetObject: 'AR_Customer', fields: [['Name', 'customer_name'], ['Credit_Limit__c', 'credit_limit'], ['Payment_Terms__c', 'payment_terms'], ['Risk_Tier__c', 'collection_priority']] },
  { id: 'INT_SF_ORACLE_ORDER_V1', file: 'sf-oracle-order-sync.yaml', name: 'Salesforce to Oracle Order Sync', source: 'Salesforce', target: 'Oracle', syncType: 'one_way', frequency: 'Every 15 minutes', description: 'Won orders become invoices in Oracle after delivery.', sourceObject: 'Opportunity', targetObject: 'AR_Invoice', fields: [['Id', 'order_ref'], ['Amount', 'amount'], ['AccountId', 'customer_id']] },
  { id: 'INT_SF_SAP_INVENTORY_V1', file: 'sf-sap-inventory.yaml', name: 'SAP to Salesforce Inventory Availability', source: 'SAP', target: 'Salesforce', syncType: 'one_way', frequency: 'Hourly', description: 'Available stock shown to sales when quoting.', sourceObject: 'Inventory_Position', targetObject: 'Product2', fields: [['Material_ID', 'ProductCode'], ['Unrestricted_Qty', 'Available_Qty__c'], ['Plant', 'Plant__c']] },
  { id: 'INT_SF_SAP_DELIVERY_V1', file: 'sf-sap-delivery.yaml', name: 'Salesforce to SAP Delivery Creation', source: 'Salesforce', target: 'SAP', syncType: 'one_way', frequency: 'Near real-time', description: 'A won order creates an outbound delivery.', sourceObject: 'Opportunity', targetObject: 'Delivery_Document', fields: [['Id', 'Sales_Order_Ref'], ['AccountId', 'Ship_To'], ['CloseDate', 'Planned_GI_Date']] },
  { id: 'INT_ORACLE_SAP_FINANCE_V1', file: 'oracle-sap-finance.yaml', name: 'Oracle to SAP Finance Sync', source: 'Oracle', target: 'SAP', syncType: 'bidirectional', frequency: 'Daily at 02:00', description: 'Supplier invoices and payment status between payables and purchasing.', sourceObject: 'AP_Invoice', targetObject: 'Purchase_Order', fields: [['po_number', 'PO_Number'], ['match_status', 'Status'], ['amount', 'Net_Value']] },
  { id: 'INT_SAP_ORACLE_RECEIPT_V1', file: 'sap-oracle-receipt.yaml', name: 'SAP to Oracle Goods Receipt', source: 'SAP', target: 'Oracle', syncType: 'one_way', frequency: 'Every 30 minutes', description: 'Goods receipts feed the three-way match.', sourceObject: 'Goods_Receipt', targetObject: 'AP_Invoice', fields: [['PO_Number', 'po_number'], ['Received_Qty', 'received_qty'], ['Posting_Date', 'receipt_date']] },
  { id: 'INT_GDRIVE_INGEST_V1', file: 'gdrive-data-ingestion.yaml', name: 'Google Drive Data Ingestion', source: 'Google Drive', target: 'SAP', syncType: 'one_way', frequency: 'Every 6 hours', description: 'Contracts and reports are extracted and linked to suppliers.', sourceObject: 'Contract_Document', targetObject: 'Vendor_Master', fields: [['Vendor_ID', 'Vendor_ID'], ['Contracted_Price', 'Contract_Price'], ['Expiry_Date', 'Contract_End']] },
  { id: 'INT_SOCIAL_RISK_V1', file: 'social-risk-signals.yaml', name: 'Social Listening Risk Signals', source: 'Social Listening', target: 'SAP', syncType: 'one_way', frequency: 'Every 6 hours', description: 'Market signals adjust supplier risk scores.', sourceObject: 'Market_Signal', targetObject: 'Vendor_Master', fields: [['Affected_Commodity', 'Category'], ['Severity', 'Risk_Score']] },
  { id: 'INT_UPLOAD_AP_V1', file: 'upload-ap-invoice.yaml', name: 'Invoice Upload to Oracle Payables', source: 'File Uploads', target: 'Oracle', syncType: 'one_way', frequency: 'On upload', description: 'Validated invoice uploads become supplier invoices.', sourceObject: 'Invoice_Upload', targetObject: 'AP_Invoice', fields: [['Invoice_Number', 'ap_invoice_id'], ['Invoice_Amount', 'amount'], ['PO_Reference', 'po_number']] },
];

const integrationContent = (n: Integration) => [
  `id: ${n.id}`, `name: ${n.name}`, 'version: "1.0"', `source_system: ${n.source}`, `target_system: ${n.target}`,
  `sync_type: ${n.syncType}`, `frequency: "${n.frequency}"`, 'description: >', `  ${n.description}`, '',
  'mappings:', `  - name: ${n.sourceObject} to ${n.targetObject}`, `    source_object: ${n.sourceObject}`, `    target_object: ${n.targetObject}`,
  `    direction: ${n.source} → ${n.target}`, '    fields:',
  ...n.fields.flatMap(([s, t]) => [`      - source: ${n.sourceObject}.${s}`, `        target: ${n.targetObject}.${t}`, '        direction: "source_to_target"']), '',
  'failure_handling:', '  retry_count: 3', '  retry_interval: "5 minutes"', '  alert_on_failure: "integration-ops@kinetiq-beverages.example"', `  fallback: "${n.source} value is authoritative"`, '',
  'dependencies:', `  - entity: ${n.sourceObject}`, '    relationship: "Source entity"', '',
].join('\n');

// ---------------------------------------------------------------------------
// Knowledge files (S3-backed editor)
// ---------------------------------------------------------------------------

interface KnowledgeFile { key: string; filename: string; category: string; content: string; modifiedMin: number }

const FILES: KnowledgeFile[] = [
  ...POLICIES.map((p, i) => ({ key: `policies/${p.file}`, filename: p.file, category: 'policies', content: policyContent(p), modifiedMin: HOUR * (9 + i * 31) })),
  ...WORKFLOWS.map((w, i) => ({ key: `workflows/${w.file}`, filename: w.file, category: 'workflows', content: workflowContent(w), modifiedMin: HOUR * (6 + i * 19) })),
  ...INTEGRATIONS.map((n, i) => ({ key: `integrations/${n.file}`, filename: n.file, category: 'integrations', content: integrationContent(n), modifiedMin: HOUR * (14 + i * 44) })),
];
const fileInfo = (f: KnowledgeFile) => ({ key: f.key, filename: f.filename, category: f.category, size: f.content.length, last_modified: ago(f.modifiedMin) });

// ---------------------------------------------------------------------------
// Knowledge index documents
// ---------------------------------------------------------------------------

/** Schemas indexed beyond the entities modelled in fixtures, so counts match the stats (86). */
const MORE_SCHEMAS: Record<string, string[]> = {
  Salesforce: ['Contact', 'Lead', 'Opportunity_Line_Item', 'Product2', 'Pricebook_Entry', 'Quote_Header', 'Quote_Line', 'Contract', 'Order', 'Order_Item', 'Case', 'Task', 'Event', 'Territory', 'User', 'Asset', 'Promotion', 'Product_Offering', 'Forecast_Override'],
  Oracle: ['AR_Credit_Note', 'AR_Receipt_Application', 'AP_Payment', 'AP_Supplier_Site', 'GL_Journal', 'GL_Account', 'GL_Period', 'Cost_Center', 'Fixed_Asset', 'Bank_Account', 'Tax_Code', 'Currency_Rate', 'Dunning_Letter', 'Credit_Memo_Request'],
  SAP: ['Material_Plant', 'Batch_Master', 'Storage_Location', 'Warehouse_Transfer', 'Bill_of_Materials', 'Production_Line', 'Routing', 'Work_Center', 'Quality_Inspection_Lot', 'Quality_Test_Result', 'Source_List', 'Purchase_Requisition', 'Purchasing_Info_Record', 'Sales_Order', 'Sales_Order_Item', 'Shipment', 'Handling_Unit', 'Stock_Transport_Order', 'Planned_Order', 'MRP_Element', 'Capacity_Plan', 'Maintenance_Order', 'Equipment'],
  Google_Drive: ['Quality_Certificate', 'Supplier_Audit_Report', 'Trade_Agreement', 'Product_Specification'],
  Social_Listening: ['Competitor_Activity', 'Weather_Forecast'],
  File_Uploads: ['Delivery_Note_Upload', 'Price_List_Upload'],
};
const DOMAIN_BY_SYSTEM: Record<string, [string, string]> = {
  Salesforce: ['Sales', 'Plan'], Oracle: ['Finance', 'Deliver'], SAP: ['Supply Chain', 'Make'],
  Google_Drive: ['Documents', 'Enable'], Social_Listening: ['Market', 'Plan'], File_Uploads: ['Documents', 'Source'],
};

interface OntoDoc { source_id: string; content_type: string; content: string; metadata: Record<string, any>; updated_at: string }

const schemaId = (system: string, name: string) => `${system.toUpperCase()}_${name.toUpperCase()}_V1_0`;

const SCHEMA_DOCS: OntoDoc[] = [
  ...ENTITIES.map((e, i) => {
    const sys = systemOf(e).system;
    return {
      source_id: schemaId(sys, e.name),
      content_type: 'onto_schema',
      content: [
        `Entity: ${e.name}`, `System: ${systemOf(e).label}`, `Domain: ${e.domain} (${e.scorProcess})`, '',
        e.semantic, '', 'Fields:',
        ...e.cols.map(col => `  - ${col.name} (${col.dataType}): ${col.semantic}`), '',
        'Relationships:', ...e.relationships.map(r => `  - ${r.type} ${r.targetEntity}: ${r.description}`),
      ].join('\n'),
      metadata: {
        object_name: e.name, source_system: sys, domain: e.domain, scor_process: e.scorProcess, risk_level: e.riskLevel,
        fdw_mapping_status: e.fdwMappingStatus, field_count: e.cols.length,
        key_field_details: e.cols.slice(0, 5).map(col => ({ name: col.name, data_type: col.dataType, semantic: col.semantic })),
      },
      updated_at: ago(380 + i * 3),
    };
  }),
  ...Object.entries(MORE_SCHEMAS).flatMap(([system, names]) => names.map((name, i) => ({
    source_id: schemaId(system, name),
    content_type: 'onto_schema',
    content: `Entity: ${name}\nSystem: ${system.replace(/_/g, ' ')}\nDomain: ${DOMAIN_BY_SYSTEM[system][0]}\n\n${name.replace(/_/g, ' ')} as held in ${system.replace(/_/g, ' ')}. Indexed from the canonical schema; not yet exposed as a virtual entity.`,
    metadata: { object_name: name, source_system: system, domain: DOMAIN_BY_SYSTEM[system][0], scor_process: DOMAIN_BY_SYSTEM[system][1], risk_level: 'low', fdw_mapping_status: 'mapped', field_count: between(`fc-${name}`, 6, 28) },
    updated_at: ago(384 + i * 2),
  }))),
];
const POLICY_DOCS: OntoDoc[] = POLICIES.map((p, i) => ({
  source_id: `${p.id.replace(/-/g, '_')}_V1_0`, content_type: 'onto_policy', content: policyContent(p),
  metadata: { object_name: p.title, policy_id: p.id, owner: p.owner, risk_level: p.risk.toLowerCase(), source_system: 'Internal', domain: p.owner, systems: p.systems, file: `policies/${p.file}` },
  updated_at: ago(HOUR * (9 + i * 31)),
}));
const WORKFLOW_DOCS: OntoDoc[] = WORKFLOWS.map((w, i) => ({
  source_id: `${w.id}_0`, content_type: 'onto_workflow', content: workflowContent(w),
  metadata: { object_name: w.name, workflow_id: w.id, source_system: w.system.replace(/ /g, '_'), domain: w.object, step_count: w.steps.length, systems: [...new Set(w.steps.map(s => s[1]))], file: `workflows/${w.file}` },
  updated_at: ago(HOUR * (6 + i * 19)),
}));
const INTEGRATION_DOCS: OntoDoc[] = INTEGRATIONS.map((n, i) => ({
  source_id: `${n.id}_0`, content_type: 'onto_integration', content: integrationContent(n),
  metadata: { object_name: n.name, integration_id: n.id, source_system: n.source.replace(/ /g, '_'), target_system: n.target.replace(/ /g, '_'), domain: `${n.sourceObject} to ${n.targetObject}`, sync_type: n.syncType, frequency: n.frequency, file: `integrations/${n.file}` },
  updated_at: ago(HOUR * (14 + i * 44)),
}));
const ALL_DOCS = [...SCHEMA_DOCS, ...POLICY_DOCS, ...WORKFLOW_DOCS, ...INTEGRATION_DOCS];

const ontoStats = () => ({
  total_embeddings: 5630,
  onto_documents: ALL_DOCS.length,
  by_content_type: { onto_schema: SCHEMA_DOCS.length, onto_policy: POLICY_DOCS.length, onto_workflow: WORKFLOW_DOCS.length, onto_integration: INTEGRATION_DOCS.length },
  legacy_embeddings: 0,
  last_indexed_at: ago(380),
});

// ---------------------------------------------------------------------------
// Search and graph
// ---------------------------------------------------------------------------

/** Rank documents by simple word overlap, so different questions give different results. */
export function searchDocs(query: string, limit = 10, contentType?: string | null) {
  const words = String(query || '').toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 2);
  const scored = ALL_DOCS
    .filter(d => !contentType || d.content_type === contentType)
    .map(d => {
      const hay = `${d.source_id} ${d.metadata.object_name} ${d.content}`.toLowerCase();
      const title = String(d.metadata.object_name).toLowerCase();
      const hits = words.reduce((n, w) => n + (title.includes(w) ? 3 : hay.includes(w) ? 1 : 0), 0);
      return { d, hits };
    })
    .sort((a, b) => b.hits - a.hits);
  const top = (scored[0]?.hits ? scored.filter(s => s.hits > 0) : scored).slice(0, limit);
  const max = Math.max(1, top[0]?.hits || 1);
  return top.map((s, i) => ({
    source_id: s.d.source_id,
    content_type: s.d.content_type,
    content: s.d.content.slice(0, 600),
    similarity: Math.max(0.41, Math.round((0.93 - i * 0.035) * (0.75 + 0.25 * (s.hits / max)) * 100) / 100),
    metadata: s.d.metadata,
    graph_expanded: i >= Math.ceil(top.length * 0.6),
  }));
}

function hybridSearch(body: Record<string, any>) {
  const results = searchDocs(body.query, Number(body.limit) || 10, body.content_type);
  const by_category: Record<string, typeof results> = {};
  for (const r of results) (by_category[r.content_type] ||= []).push(r);
  return {
    total: results.length,
    vector_hits: results.filter(r => !r.graph_expanded).length,
    graph_hits: results.filter(r => r.graph_expanded).length,
    by_category,
    results,
  };
}

/** Neighbourhood of a document in the knowledge graph. */
function graphNeighborhood(ontoId: string, hops: number) {
  const doc = ALL_DOCS.find(d => d.source_id === ontoId);
  const idOf = (name: string) => {
    const e = entityByName(name);
    if (e) return schemaId(systemOf(e).system, e.name);
    return ALL_DOCS.find(d => d.source_id.startsWith(name.replace(/-/g, '_')))?.source_id || name;
  };
  const edges: { source: string; target: string; type: string; description: string }[] = [];
  const addEntityEdges = (name: string) => {
    const e = entityByName(name);
    if (!e) return;
    const from = schemaId(systemOf(e).system, e.name);
    for (const r of e.relationships) edges.push({ source: from, target: idOf(r.targetEntity), type: r.type, description: r.description });
    for (const other of ENTITIES) {
      for (const r of other.relationships) {
        if (r.targetEntity === e.name) edges.push({ source: schemaId(systemOf(other).system, other.name), target: from, type: r.type, description: r.description });
      }
    }
  };
  const objectName = String(doc?.metadata.object_name || '');
  if (doc?.content_type === 'onto_schema') {
    addEntityEdges(objectName);
  } else if (doc) {
    // Policies, workflows and integrations link to the entities they mention.
    for (const e of ENTITIES) {
      if (doc.content.includes(e.name) || doc.content.includes(e.name.replace(/_/g, ' '))) {
        edges.push({ source: doc.source_id, target: schemaId(systemOf(e).system, e.name), type: doc.content_type === 'onto_policy' ? 'constrained_by' : doc.content_type === 'onto_workflow' ? 'triggers' : 'syncs_to', description: `${doc.metadata.object_name} refers to ${e.name}` });
      }
    }
  }
  if (hops > 1) {
    const firstRing = [...new Set(edges.flatMap(ed => [ed.source, ed.target]))].filter(id => id !== ontoId).slice(0, 4);
    for (const id of firstRing) {
      const name = ALL_DOCS.find(d => d.source_id === id)?.metadata.object_name;
      if (name && entityByName(name)) addEntityEdges(name);
    }
  }
  const seen = new Set<string>();
  const unique = edges.filter(ed => { const k = `${ed.source}|${ed.target}|${ed.type}`; return !seen.has(k) && seen.add(k); }).slice(0, 40);
  const nodeIds = [...new Set([ontoId, ...unique.flatMap(ed => [ed.source, ed.target])])];
  return { center: ontoId, hops, nodes: nodeIds.map(id => ({ id })), edges: unique, neighbor_count: nodeIds.length - 1 };
}

// ---------------------------------------------------------------------------
// Knowledge pipelines registry
// ---------------------------------------------------------------------------

const KNOWLEDGE_PIPELINES = [
  { pipelineId: 'kp-schema-index', name: 'Schema index', description: 'Unified schema, FDW mapping and mapping rules into virtual entity documents.', stageIds: ['extract_unified_schema', 'resolve_fdw_mapping', 'extract_mapping_rules'], outputs: ['onto_schema'], updatedAt: ago(380) },
  { pipelineId: 'kp-policy-index', name: 'Policy index', description: 'Business policy documents parsed into rules and thresholds.', stageIds: ['extract_policies', 'normalize'], outputs: ['onto_policy'], updatedAt: ago(380) },
  { pipelineId: 'kp-workflow-index', name: 'Workflow index', description: 'Workflow definitions parsed into steps and dependencies.', stageIds: ['extract_workflows', 'normalize'], outputs: ['onto_workflow'], updatedAt: ago(380) },
  { pipelineId: 'kp-integration-index', name: 'Integration index', description: 'Field-level sync mappings between systems.', stageIds: ['extract_integrations', 'normalize'], outputs: ['onto_integration'], updatedAt: ago(380) },
  { pipelineId: 'kp-embeddings', name: 'Embeddings', description: 'Semantic chunking and embedding of every knowledge document.', stageIds: ['enrich', 'chunk_embed', 'load_vector'], outputs: ['pgvector'], updatedAt: ago(380) },
  { pipelineId: 'kp-graph', name: 'Knowledge graph', description: 'Relationships between entities, policies, workflows and integrations.', stageIds: ['load_graph'], outputs: ['graph'], updatedAt: ago(380) },
  { pipelineId: 'kp-nlq-exemplars', name: 'Question exemplars', description: 'Example questions per entity, used to plan natural-language queries.', stageIds: ['index_nlq_exemplars', 'validate'], outputs: ['nlq_exemplar'], updatedAt: ago(DAY * 3) },
];

const pipelineRuns = (pipelineId: string, limit: number) => {
  const idx = Math.max(0, KNOWLEDGE_PIPELINES.findIndex(p => p.pipelineId === pipelineId));
  const count = Math.min(limit, idx === 6 ? 2 : 5);
  const counts: Record<string, number>[] = [
    { documents: 86, mapped: 71 }, { documents: 14, rules: 42 }, { documents: 23, steps: 81 }, { documents: 9, field_mappings: 28 },
    { chunks: 5630, embeddings: 5630 }, { nodes: 412, edges: 1287 }, { exemplars: 344 },
  ];
  return Array.from({ length: count }, (_, k) => {
    const recordedAt = ago(380 + k * DAY + (idx === 6 ? DAY * 3 : 0));
    return {
      pipelineId,
      journeyId: 'jr-rag-01',
      jobId: `JOB-${pad(41 - k)}`,
      counts: counts[idx],
      success: !(idx === 4 && k === 2),
      recordedAt,
      SK: `RUN#${recordedAt}`,
    };
  });
};

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

export const controlPlaneRoutes: SampleRoute[] = [
  // Knowledge pipelines registry
  { method: 'GET', path: '/api/v1/knowledge-pipelines', handle: () => ({ total: KNOWLEDGE_PIPELINES.length, items: KNOWLEDGE_PIPELINES }) },
  {
    method: 'GET', path: /^\/api\/v1\/knowledge-pipelines\/([^/]+)\/runs$/,
    handle: ({ match, query }) => {
      const id = decodeURIComponent(match[1]);
      const items = pipelineRuns(id, Number(query.get('limit')) || 20);
      return { pipelineId: id, total: items.length, items };
    },
  },
  {
    method: 'GET', path: /^\/api\/v1\/knowledge-pipelines\/([^/]+)$/,
    handle: ({ match }) => KNOWLEDGE_PIPELINES.find(p => p.pipelineId === decodeURIComponent(match[1])) || KNOWLEDGE_PIPELINES[0],
  },

  // Knowledge index
  { method: 'GET', path: '/api/v1/control-plane/onto/stats', handle: () => ontoStats() },
  {
    method: 'GET', path: '/api/v1/control-plane/onto/documents',
    handle: ({ query }) => {
      const type = query.get('content_type');
      const q = (query.get('q') || '').toLowerCase();
      const offset = Number(query.get('offset')) || 0;
      const limit = Number(query.get('limit')) || 50;
      const all = ALL_DOCS.filter(d => (!type || d.content_type === type)
        && (!q || `${d.source_id} ${d.metadata.object_name} ${d.content}`.toLowerCase().includes(q)));
      return { documents: all.slice(offset, offset + limit), total: all.length, offset, limit };
    },
  },
  {
    method: 'GET', path: /^\/api\/v1\/control-plane\/onto\/documents\/(.+)$/,
    handle: ({ match }) => ALL_DOCS.find(d => d.source_id === decodeURIComponent(match[1])) || ALL_DOCS[0],
  },
  {
    method: 'GET', path: /^\/api\/v1\/control-plane\/onto\/graph\/(.+)$/,
    handle: ({ match, query }) => graphNeighborhood(decodeURIComponent(match[1]), Number(query.get('hops')) || 2),
  },
  {
    method: 'GET', path: '/api/v1/control-plane/onto/bundles',
    handle: () => ({
      bucket: 'kinetiq-nexus-knowledge',
      bundles: Array.from({ length: 6 }, (_, k) => ({ job_id: `JOB-${pad(41 - k)}`, key: `onto-bundles/JOB-${pad(41 - k)}/bundle.onto`, size: between(`bundle-${k}`, 380, 460) * 1024, created_at: ago(380 + k * DAY), documents: ALL_DOCS.length - k })),
    }),
  },
  { method: 'POST', path: '/api/v1/control-plane/onto/search', handle: ({ body }) => hybridSearch(asObj(body)) },
  { method: 'POST', path: '/api/v1/control-plane/search', handle: ({ body }) => searchDocs(asObj(body).query, Number(asObj(body).limit) || 10) },

  // Knowledge files (policy, workflow and integration editors; Knowledge Data dialog)
  {
    method: 'GET', path: '/api/v1/control-plane/onto-data/files',
    handle: ({ query }) => {
      const files = FILES.filter(f => !query.get('category') || f.category === query.get('category')).map(fileInfo);
      return { files, total: files.length };
    },
  },
  {
    // File content is read as text, not JSON.
    method: 'GET', path: /^\/api\/v1\/control-plane\/onto-data\/files\/(.+)$/,
    handle: ({ match }) => {
      const key = decodeURIComponent(match[1]);
      const file = FILES.find(f => f.key === key);
      return raw(file ? file.content : `# ${key.split('/').pop()}\n\nThis file has no sample content.\n`);
    },
  },
  {
    method: 'POST', path: '/api/v1/control-plane/onto-data/files',
    handle: () => ({ success: true, message: 'File saved (sample data: nothing is stored)' }),
  },
  {
    method: 'POST', path: '/api/v1/control-plane/onto-data/seed',
    handle: () => ({ success: true, counts: { policies: POLICIES.length, workflows: WORKFLOWS.length, integrations: INTEGRATIONS.length } }),
  },
  {
    method: 'GET', path: '/api/v1/control-plane/onto-data/info',
    handle: () => ({
      bucket: 'kinetiq-nexus-knowledge', prefix: 'onto-data/', total_files: FILES.length,
      by_category: { policies: POLICIES.length, workflows: WORKFLOWS.length, integrations: INTEGRATIONS.length },
      last_modified: ago(HOUR * 6),
    }),
  },

  // Read by the Journey Studio header
  { method: 'GET', path: '/api/v1/config/wxcc-mode', handle: () => ({ simulator_enabled: true, mode: 'simulator', source: 'ssm' }) },
];

// Re-exported for the Reasoning plane (agent answers quote the same knowledge).
export { POLICIES, WORKFLOWS, INTEGRATIONS, ALL_DOCS };
