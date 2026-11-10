/**
 * Shared sample fixtures: the demo company, its systems, entities and journeys.
 * Every route file reads from here so the same names appear on every screen.
 *
 * Demo company: a consumer-goods (energy drink) maker running Salesforce,
 * SAP S/4HANA, Oracle ERP, Google Drive, social listening and file uploads.
 */

export interface SampleRoute {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string | RegExp;
  handle: (ctx: { path: string; query: URLSearchParams; body: unknown; match: string[] }) => unknown | Promise<unknown>;
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

export const HOUR = 60;
export const DAY = 60 * 24;

/** ISO timestamp `minutes` ago (relative to now, so data never looks stale). */
export const ago = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString();
/** ISO timestamp `minutes` from now. */
export const ahead = (minutes: number) => new Date(Date.now() + minutes * 60_000).toISOString();
/** YYYY-MM-DD, `days` ago (negative = in the future). */
export const dayAgo = (days: number) => new Date(Date.now() - days * 86_400_000).toISOString().slice(0, 10);

/** Deterministic pseudo-random number in [0, 1) for a seed. Same seed, same value. */
export function rnd(seed: string | number): number {
  const s = String(seed);
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  h ^= h >>> 13;
  h = Math.imul(h, 0x5bd1e995);
  h ^= h >>> 15;
  return (h >>> 0) / 4294967296;
}

export const round = (n: number, decimals = 2) => {
  const f = Math.pow(10, decimals);
  return Math.round(n * f) / f;
};
/** Deterministic number between lo and hi. */
export const between = (seed: string | number, lo: number, hi: number, decimals = 0) =>
  round(lo + rnd(seed) * (hi - lo), decimals);
export const pick = <T,>(arr: readonly T[], i: number): T => arr[((i % arr.length) + arr.length) % arr.length];
/** Weighted pick: earlier items are more likely. */
export const pickSeeded = <T,>(arr: readonly T[], seed: string | number): T =>
  arr[Math.min(arr.length - 1, Math.floor(Math.pow(rnd(seed), 1.6) * arr.length))];
export const pad = (n: number, width = 4) => String(n).padStart(width, '0');

/** Body of a POST/PUT as a plain object (the plugin passes `unknown`). */
export const asObj = (body: unknown): Record<string, any> =>
  body && typeof body === 'object' ? (body as Record<string, any>) : {};

/**
 * Non-JSON response. The plugin sends `__raw` as-is with `__contentType`
 * instead of JSON-encoding it (needed for file contents and event streams).
 */
export const raw = (body: string, contentType = 'text/plain; charset=utf-8') => ({ __raw: body, __contentType: contentType });
/** A complete Server-Sent-Events body, delivered in one piece. */
export const sse = (events: unknown[]) =>
  raw(events.map(e => `data: ${JSON.stringify(e)}\n\n`).join(''), 'text/event-stream; charset=utf-8');

// ---------------------------------------------------------------------------
// Master data
// ---------------------------------------------------------------------------

export const COMPANY = 'Kinetiq Beverages';
export const ADMIN_EMAIL = 'priya.raman@kinetiq-beverages.example';

export const CUSTOMERS = [
  'Harbor Wholesale Group', 'Meridian Foodservice', 'BrightMart Retail', 'Cascade Convenience Stores',
  'Summit Distribution Co.', 'Lakeshore Grocers', 'Pioneer Cash & Carry', 'Redwood Vending Services',
  'Atlas Travel Retail', 'Evergreen Supermarkets', 'Coastal Beverage Partners', 'UrbanFuel Kiosks',
] as const;

export const VENDORS = [
  'Alucan Packaging GmbH', 'Pacific Sweeteners Ltd', 'NutraChem Ingredients', 'Borealis Flavours',
  'TransGlobal Freight', 'Helix Labels & Film', 'Carbonix Gases', 'Sierra Pallet & Crate',
  'Orbis Co-Packing', 'Vantage Cold Storage',
] as const;

export const PRODUCTS = [
  { id: 'FG-1001', name: 'Kinetiq Original 250ml', category: 'Energy' },
  { id: 'FG-1002', name: 'Kinetiq Zero Sugar 250ml', category: 'Energy' },
  { id: 'FG-1003', name: 'Kinetiq Citrus Surge 500ml', category: 'Carbonated' },
  { id: 'FG-1004', name: 'Kinetiq Tropical 355ml', category: 'Juice' },
  { id: 'FG-1005', name: 'Kinetiq Focus Tea 330ml', category: 'Tea' },
  { id: 'FG-1006', name: 'Kinetiq Hydrate Sport 500ml', category: 'Sports' },
  { id: 'FG-1007', name: 'Kinetiq Still Water 600ml', category: 'Water' },
  { id: 'FG-1008', name: 'Kinetiq Protein Bites 45g', category: 'Snacks' },
] as const;

export const RAW_MATERIALS = [
  { id: 'RM-2001', name: 'Aluminium can 250ml', category: 'Packaging' },
  { id: 'RM-2002', name: 'Taurine premix', category: 'Raw_Materials' },
  { id: 'RM-2003', name: 'Cane sugar, bulk', category: 'Raw_Materials' },
  { id: 'RM-2004', name: 'Caffeine anhydrous', category: 'Raw_Materials' },
  { id: 'RM-2005', name: 'Shrink film 450mm', category: 'Packaging' },
  { id: 'RM-2006', name: 'CO2, food grade', category: 'Utilities' },
] as const;

export const PLANTS = [
  { id: 'PL01', name: 'Rotterdam', country: 'NL' },
  { id: 'PL02', name: 'Leeds', country: 'GB' },
  { id: 'PL03', name: 'Austin', country: 'US' },
  { id: 'PL04', name: 'Monterrey', country: 'MX' },
  { id: 'PL05', name: 'Penang', country: 'MY' },
] as const;

export const REGIONS = ['North', 'South', 'East', 'West', 'Central'] as const;
export const PRODUCT_CATEGORIES = ['Energy', 'Carbonated', 'Juice', 'Water', 'Sports', 'Tea', 'Snacks'] as const;
export const SPEND_CATEGORIES = ['Raw_Materials', 'Packaging', 'Logistics', 'Services', 'Equipment', 'Utilities'] as const;
export const PEOPLE = [
  'Priya Raman', 'Daniel Okafor', 'Sofia Lindqvist', 'Marcus Chen', 'Elena Petrova',
  'Tomás Herrera', 'Aisha Rahman', 'Jonas Becker', 'Mei Tanaka', 'Oliver Grant',
] as const;
export const emailOf = (name: string) =>
  `${name.toLowerCase().normalize('NFD').replace(/[^a-z ]/g, '').trim().replace(/\s+/g, '.')}@kinetiq-beverages.example`;

// ---------------------------------------------------------------------------
// Systems
// ---------------------------------------------------------------------------

export interface SystemDef {
  /** Short key used on the home page and in connector APIs. */
  key: 'sfdc' | 'sap' | 'oracle' | 'gdrive' | 'social' | 'files';
  /** System name as the entity catalogue and knowledge graph spell it. */
  system: string;
  label: string;
  schema: string;
  /** `source` query value the FDW endpoints receive for this system. */
  fdwSource: 'simulator' | 'sap' | 'oracle' | 'external';
  server: string;
  wrapper: string;
  /** Key in /api/v1/data-source-mode. */
  modeKey: string;
  mode: 'simulator' | 'real';
}

export const SYSTEMS: SystemDef[] = [
  { key: 'sfdc', system: 'Salesforce', label: 'Salesforce CRM', schema: 'sfdc_itxp2dev', fdwSource: 'simulator', server: 'sfdc_server', wrapper: 'multicorn (Salesforce REST)', modeKey: 'sfdc', mode: 'simulator' },
  { key: 'sap', system: 'SAP', label: 'SAP S/4HANA', schema: 'sap_s4hana', fdwSource: 'sap', server: 'sap_s4_server', wrapper: 'hdb_fdw', modeKey: 'sap', mode: 'simulator' },
  { key: 'oracle', system: 'Oracle', label: 'Oracle ERP', schema: 'oracle_erp', fdwSource: 'oracle', server: 'oracle_erp_server', wrapper: 'oracle_fdw', modeKey: 'oracle', mode: 'simulator' },
  { key: 'gdrive', system: 'Google_Drive', label: 'Google Drive', schema: 'external_sources', fdwSource: 'external', server: 'external_server', wrapper: 'file_fdw (extracted)', modeKey: 'google_drive', mode: 'real' },
  { key: 'social', system: 'Social_Listening', label: 'Social Listening', schema: 'external_sources', fdwSource: 'external', server: 'external_server', wrapper: 'file_fdw (extracted)', modeKey: 'social_listening', mode: 'real' },
  { key: 'files', system: 'File_Uploads', label: 'File Uploads', schema: 'external_sources', fdwSource: 'external', server: 'external_server', wrapper: 'file_fdw (extracted)', modeKey: 'file_uploads', mode: 'simulator' },
];
export const systemByKey = (key: string) => SYSTEMS.find(s => s.key === key)!;

// ---------------------------------------------------------------------------
// Entities (virtual data layer). One definition drives the entity catalogue,
// FDW tables/columns, previews, mapping rules, the knowledge graph and audits.
// ---------------------------------------------------------------------------

type Risk = 'low' | 'medium' | 'high';
interface ColDef {
  name: string;
  dataType: string;
  semantic: string;
  riskLevel: Risk;
  gen: (i: number) => unknown;
}
const c = (name: string, dataType: string, semantic: string, gen: (i: number) => unknown, riskLevel: Risk = 'low'): ColDef =>
  ({ name, dataType, semantic, gen, riskLevel });

export interface EntityDef {
  name: string;
  systemKey: SystemDef['key'];
  domain: string;
  scorProcess: string;
  semantic: string;
  riskLevel: Risk;
  /** mapped = live source table, virtual = no physical table yet, unmapped = no rule. */
  fdwMappingStatus: 'mapped' | 'virtual' | 'unmapped';
  /** Row count shown in audits and diagnostics. */
  totalRows: number;
  cols: ColDef[];
  relationships: { type: string; targetEntity: string; targetCategory: string; description: string }[];
}

const rel = (type: string, targetEntity: string, description: string, targetCategory = 'onto_schema') =>
  ({ type, targetEntity, targetCategory, description });

const cust = (i: number) => pick(CUSTOMERS, i);
const vend = (i: number) => pick(VENDORS, i);
const prod = (i: number) => pick(PRODUCTS, i);
const plant = (i: number) => pick(PLANTS, i);

export const ENTITIES: EntityDef[] = [
  // ---- Salesforce ---------------------------------------------------------
  {
    name: 'Account', systemKey: 'sfdc', domain: 'Customer', scorProcess: 'Deliver', riskLevel: 'high',
    semantic: 'Distributor or retail customer. Source of truth for credit limit and risk tier.',
    fdwMappingStatus: 'mapped', totalRows: 1284,
    cols: [
      c('Id', 'varchar(18)', 'Salesforce account id', i => `ACC-${1001 + i}`),
      c('Name', 'varchar(255)', 'Customer legal name', i => cust(i)),
      c('Type', 'varchar(40)', 'Channel type', i => pick(['Distributor', 'Retail Chain', 'Foodservice', 'Convenience'], i)),
      c('Region__c', 'varchar(40)', 'Sales region', i => pick(REGIONS, i)),
      c('Credit_Limit__c', 'numeric(14,2)', 'Approved credit limit in USD', i => between(`acc-cl-${i}`, 10, 200) * 25000, 'high'),
      c('Risk_Tier__c', 'varchar(20)', 'Credit risk tier', i => pickSeeded(['Low', 'Medium', 'High'], `acc-rt-${i}`), 'medium'),
      c('Payment_Terms__c', 'varchar(20)', 'Agreed payment terms', i => pick(['Net 30', 'Net 45', 'Net 60'], i)),
      c('AnnualRevenue', 'numeric(16,2)', 'Trailing 12-month revenue', i => between(`acc-rev-${i}`, 400, 9800) * 1000),
      c('OwnerName', 'varchar(120)', 'Account owner', i => pick(PEOPLE, i + 2)),
      c('LastModifiedDate', 'timestamp', 'Last change in Salesforce', i => ago(90 + i * 137)),
    ],
    relationships: [
      rel('syncs_to', 'AR_Customer', 'Credit limit and payment terms sync to Oracle receivables'),
      rel('triggers', 'Opportunity', 'An account owns its opportunities'),
      rel('constrained_by', 'POL-CREDIT-001', 'Credit limit changes follow the credit policy', 'onto_policy'),
    ],
  },
  {
    name: 'Opportunity', systemKey: 'sfdc', domain: 'Sales', scorProcess: 'Plan', riskLevel: 'medium',
    semantic: 'Sales order or pipeline deal. The starting point of the order-to-cash flow.',
    fdwMappingStatus: 'mapped', totalRows: 5310,
    cols: [
      c('Id', 'varchar(18)', 'Salesforce opportunity id', i => `OPP-${10231 + i}`),
      c('Name', 'varchar(255)', 'Deal name', i => `${cust(i)} - ${pick(['Q4 replenishment', 'Summer Surge promo', 'New store rollout', 'Annual contract renewal'], i)}`),
      c('AccountId', 'varchar(18)', 'Owning account', i => `ACC-${1001 + (i % CUSTOMERS.length)}`),
      c('StageName', 'varchar(40)', 'Pipeline stage', i => pick(['Closed Won', 'Negotiation', 'Proposal', 'Closed Won', 'Prospecting', 'Closed Lost'], i)),
      c('Amount', 'numeric(14,2)', 'Order value in USD', i => between(`opp-amt-${i}`, 18, 640) * 1000, 'medium'),
      c('CloseDate', 'date', 'Expected or actual close date', i => dayAgo(i * 3 - 12)),
      c('Probability', 'integer', 'Win probability %', i => pick([100, 75, 50, 100, 20, 0], i)),
      c('Product_Family__c', 'varchar(40)', 'Main product family', i => prod(i).category),
      c('OwnerName', 'varchar(120)', 'Opportunity owner', i => pick(PEOPLE, i + 4)),
    ],
    relationships: [
      rel('depends_on', 'Account', 'Every opportunity belongs to an account'),
      rel('triggers', 'Delivery_Document', 'A won order creates deliveries in SAP'),
      rel('triggers', 'AR_Invoice', 'A delivered order is invoiced in Oracle'),
      rel('constrained_by', 'WF_ORDER_TO_CASH_V1', 'Order-to-cash workflow', 'onto_workflow'),
    ],
  },
  {
    name: 'Campaign', systemKey: 'sfdc', domain: 'Marketing', scorProcess: 'Plan', riskLevel: 'low',
    semantic: 'Trade promotion or marketing campaign used as a demand driver.',
    fdwMappingStatus: 'mapped', totalRows: 86,
    cols: [
      c('Id', 'varchar(18)', 'Campaign id', i => `CMP-${301 + i}`),
      c('Name', 'varchar(255)', 'Campaign name', i => pick(['Summer Surge 2026', 'Zero Sugar launch wave 2', 'Back-to-campus bundles', 'Travel retail takeover', 'Citrus Surge sampling', 'Year-end distributor rebate'], i)),
      c('Type', 'varchar(40)', 'Campaign type', i => pick(['Trade promotion', 'Product launch', 'Sampling', 'Rebate'], i)),
      c('Status', 'varchar(20)', 'Campaign status', i => pick(['Active', 'Planned', 'Completed', 'Active'], i)),
      c('StartDate', 'date', 'Start date', i => dayAgo(40 - i * 9)),
      c('EndDate', 'date', 'End date', i => dayAgo(10 - i * 9)),
      c('BudgetedCost', 'numeric(12,2)', 'Budget in USD', i => between(`cmp-b-${i}`, 20, 400) * 1000),
      c('Expected_Lift_Pct__c', 'numeric(5,2)', 'Expected volume lift %', i => between(`cmp-l-${i}`, 4, 28, 1)),
    ],
    relationships: [rel('triggers', 'Opportunity', 'Promotions lift order volume')],
  },
  // ---- Oracle ERP ---------------------------------------------------------
  {
    name: 'AR_Customer', systemKey: 'oracle', domain: 'Finance', scorProcess: 'Deliver', riskLevel: 'high',
    semantic: 'Receivables customer account, kept in step with the Salesforce account.',
    fdwMappingStatus: 'mapped', totalRows: 1279,
    cols: [
      c('customer_id', 'number(12)', 'Oracle customer id', i => 40001 + i),
      c('customer_name', 'varchar2(240)', 'Customer name', i => cust(i)),
      c('sfdc_account_id', 'varchar2(18)', 'Linked Salesforce account', i => `ACC-${1001 + (i % CUSTOMERS.length)}`),
      c('credit_limit', 'number(14,2)', 'Credit limit synced from Salesforce', i => between(`acc-cl-${i % CUSTOMERS.length}`, 10, 200) * 25000, 'high'),
      c('payment_terms', 'varchar2(20)', 'Payment terms', i => pick(['Net 30', 'Net 45', 'Net 60'], i)),
      c('ar_balance', 'number(14,2)', 'Open receivables balance', i => between(`arc-b-${i}`, 12, 900) * 1000, 'medium'),
      c('days_past_due', 'number(4)', 'Oldest invoice days past due', i => pick([0, 0, 12, 0, 47, 3, 0, 91], i)),
      c('status', 'varchar2(20)', 'Account status', i => pick(['Active', 'Active', 'Active', 'Credit hold', 'Active', 'Under review'], i)),
    ],
    relationships: [
      rel('depends_on', 'Account', 'Created from the Salesforce account'),
      rel('constrained_by', 'INT_SF_ORACLE_CUSTOMER_V1', 'Customer sync mapping', 'onto_integration'),
    ],
  },
  {
    name: 'AR_Invoice', systemKey: 'oracle', domain: 'Finance', scorProcess: 'Deliver', riskLevel: 'high',
    semantic: 'Customer invoice raised after delivery. Drives DSO and open receivables.',
    fdwMappingStatus: 'mapped', totalRows: 18420,
    cols: [
      c('invoice_id', 'varchar2(20)', 'Invoice number', i => `INV-${88120 + i}`),
      c('customer_id', 'number(12)', 'Billed customer', i => 40001 + (i % CUSTOMERS.length)),
      c('customer_name', 'varchar2(240)', 'Customer name', i => cust(i)),
      c('order_ref', 'varchar2(18)', 'Salesforce order reference', i => `OPP-${10231 + i}`),
      c('invoice_date', 'date', 'Invoice date', i => dayAgo(4 + i * 2)),
      c('due_date', 'date', 'Payment due date', i => dayAgo(i * 2 - 26)),
      c('amount', 'number(14,2)', 'Invoice total in USD', i => between(`opp-amt-${i}`, 18, 640) * 1000, 'medium'),
      c('amount_due', 'number(14,2)', 'Unpaid amount', i => (i % 3 === 1 ? 0 : between(`inv-due-${i}`, 5, 400) * 1000), 'medium'),
      c('currency', 'varchar2(3)', 'Currency', () => 'USD'),
      c('status', 'varchar2(20)', 'Invoice status', i => pick(['Open', 'Paid', 'Overdue', 'Open', 'Disputed', 'Partially paid'], i)),
    ],
    relationships: [
      rel('depends_on', 'Opportunity', 'Invoiced against a won order'),
      rel('depends_on', 'Delivery_Document', 'Raised after goods issue'),
      rel('triggers', 'AR_Payment', 'Payments are applied to invoices'),
    ],
  },
  {
    name: 'AR_Payment', systemKey: 'oracle', domain: 'Finance', scorProcess: 'Deliver', riskLevel: 'medium',
    semantic: 'Cash receipt applied to a customer invoice.',
    fdwMappingStatus: 'mapped', totalRows: 15733,
    cols: [
      c('payment_id', 'varchar2(20)', 'Receipt number', i => `PAY-${55310 + i}`),
      c('invoice_id', 'varchar2(20)', 'Invoice paid', i => `INV-${88120 + i * 2 + 1}`),
      c('customer_name', 'varchar2(240)', 'Paying customer', i => cust(i * 2 + 1)),
      c('payment_date', 'date', 'Receipt date', i => dayAgo(1 + i * 2)),
      c('amount', 'number(14,2)', 'Amount received in USD', i => between(`pay-${i}`, 8, 520) * 1000),
      c('method', 'varchar2(12)', 'Payment method', i => pick(['ACH', 'Wire', 'ACH', 'Check', 'Card'], i)),
      c('status', 'varchar2(12)', 'Application status', i => pick(['Applied', 'Applied', 'Applied', 'Unapplied', 'Applied', 'Reversed'], i)),
    ],
    relationships: [rel('depends_on', 'AR_Invoice', 'Applied against an invoice')],
  },
  {
    name: 'AP_Invoice', systemKey: 'oracle', domain: 'Procurement', scorProcess: 'Source', riskLevel: 'medium',
    semantic: 'Supplier invoice awaiting three-way match against purchase order and goods receipt.',
    fdwMappingStatus: 'mapped', totalRows: 9240,
    cols: [
      c('ap_invoice_id', 'varchar2(20)', 'Supplier invoice id', i => `API-${71200 + i}`),
      c('vendor_name', 'varchar2(240)', 'Supplier', i => vend(i)),
      c('po_number', 'varchar2(12)', 'Purchase order', i => `45000${pad(1210 + i)}`),
      c('invoice_date', 'date', 'Invoice date', i => dayAgo(3 + i * 2)),
      c('amount', 'number(14,2)', 'Invoice amount in USD', i => between(`po-amt-${i}`, 6, 380) * 1000),
      c('match_status', 'varchar2(20)', 'Three-way match result', i => pick(['Matched', 'Matched', 'Price variance', 'Matched', 'Awaiting receipt', 'Quantity variance'], i)),
      c('payment_status', 'varchar2(20)', 'Payment status', i => pick(['Scheduled', 'Paid', 'On hold', 'Paid', 'Scheduled'], i)),
    ],
    relationships: [
      rel('depends_on', 'Purchase_Order', 'Billed against a purchase order'),
      rel('depends_on', 'Goods_Receipt', 'Matched against received quantity'),
    ],
  },
  // ---- SAP S/4HANA --------------------------------------------------------
  {
    name: 'Purchase_Order', systemKey: 'sap', domain: 'Procurement', scorProcess: 'Source', riskLevel: 'medium',
    semantic: 'Order placed with a supplier for raw materials, packaging or services.',
    fdwMappingStatus: 'mapped', totalRows: 7615,
    cols: [
      c('PO_Number', 'char(10)', 'Purchase order number', i => `45000${pad(1210 + i)}`),
      c('Vendor_ID', 'char(10)', 'Supplier id', i => `V-${1001 + (i % VENDORS.length)}`),
      c('Vendor_Name', 'varchar(80)', 'Supplier name', i => vend(i)),
      c('Material_ID', 'char(18)', 'Material ordered', i => pick(RAW_MATERIALS, i).id),
      c('Quantity', 'decimal(13,3)', 'Ordered quantity', i => between(`po-q-${i}`, 2, 90) * 1000),
      c('Net_Value', 'decimal(15,2)', 'Order value in USD', i => between(`po-amt-${i}`, 6, 380) * 1000),
      c('Order_Date', 'date', 'Order date', i => dayAgo(9 + i * 2)),
      c('Delivery_Date', 'date', 'Requested delivery date', i => dayAgo(i * 2 - 12)),
      c('Plant', 'char(4)', 'Receiving plant', i => plant(i).id),
      c('Status', 'varchar(24)', 'Order status', i => pick(['Open', 'Received', 'Partially received', 'Received', 'Open', 'Blocked'], i)),
    ],
    relationships: [
      rel('depends_on', 'Vendor_Master', 'Placed with an approved supplier'),
      rel('depends_on', 'Material_Master', 'Orders a material'),
      rel('triggers', 'Goods_Receipt', 'Deliveries are posted as goods receipts'),
      rel('constrained_by', 'Contract_Document', 'Prices follow the supplier contract'),
    ],
  },
  {
    name: 'Vendor_Master', systemKey: 'sap', domain: 'Procurement', scorProcess: 'Source', riskLevel: 'medium',
    semantic: 'Approved supplier with delivery, quality and risk scores.',
    fdwMappingStatus: 'mapped', totalRows: 412,
    cols: [
      c('Vendor_ID', 'char(10)', 'Supplier id', i => `V-${1001 + i}`),
      c('Vendor_Name', 'varchar(80)', 'Supplier name', i => vend(i)),
      c('Country', 'char(2)', 'Country', i => pick(['DE', 'AU', 'US', 'NO', 'NL', 'GB', 'FR', 'MX', 'US', 'SG'], i)),
      c('Category', 'varchar(30)', 'Spend category', i => pick(['Packaging', 'Raw_Materials', 'Raw_Materials', 'Raw_Materials', 'Logistics', 'Packaging', 'Utilities', 'Packaging', 'Services', 'Logistics'], i)),
      c('Payment_Terms', 'varchar(10)', 'Payment terms', i => pick(['Net 45', 'Net 30', 'Net 60'], i)),
      c('On_Time_Delivery_Pct', 'decimal(5,2)', 'On-time delivery, last 90 days', i => between(`v-otd-${i}`, 78, 99, 1)),
      c('Quality_Score', 'decimal(5,2)', 'Incoming quality score', i => between(`v-q-${i}`, 82, 99, 1)),
      c('Risk_Score', 'integer', 'Composite risk score, 0-100', i => between(`v-r-${i}`, 12, 81)),
      c('Single_Source', 'boolean', 'Only approved source for a material', i => i % 4 === 2),
      c('Status', 'varchar(20)', 'Supplier status', i => pick(['Active', 'Active', 'Active', 'Under review', 'Active', 'Blocked'], i)),
    ],
    relationships: [
      rel('triggers', 'Purchase_Order', 'Suppliers receive purchase orders'),
      rel('constrained_by', 'Contract_Document', 'Terms come from the signed contract'),
      rel('depends_on', 'Market_Signal', 'External disruption signals adjust risk'),
    ],
  },
  {
    name: 'Material_Master', systemKey: 'sap', domain: 'Product', scorProcess: 'Make', riskLevel: 'low',
    semantic: 'Finished goods, raw materials and packaging with cost and shelf life.',
    fdwMappingStatus: 'mapped', totalRows: 2140,
    cols: [
      c('Material_ID', 'char(18)', 'Material number', i => (i < PRODUCTS.length ? PRODUCTS[i].id : pick(RAW_MATERIALS, i).id)),
      c('Description', 'varchar(80)', 'Material description', i => (i < PRODUCTS.length ? PRODUCTS[i].name : pick(RAW_MATERIALS, i).name)),
      c('Material_Type', 'varchar(20)', 'Material type', i => (i < PRODUCTS.length ? 'Finished good' : pick(RAW_MATERIALS, i).category === 'Packaging' ? 'Packaging' : 'Raw material')),
      c('Category', 'varchar(30)', 'Product or spend category', i => (i < PRODUCTS.length ? PRODUCTS[i].category : pick(RAW_MATERIALS, i).category)),
      c('Base_UoM', 'char(3)', 'Base unit of measure', i => (i < PRODUCTS.length ? 'CS' : pick(['EA', 'KG', 'KG', 'KG', 'ROL', 'KG'], i))),
      c('Standard_Cost', 'decimal(11,2)', 'Standard cost per unit, USD', i => between(`m-c-${i}`, 0.4, 14, 2)),
      c('Shelf_Life_Days', 'integer', 'Shelf life in days', i => pick([365, 365, 270, 180, 240, 365, 540, 210], i)),
      c('Recycled_Content_Pct', 'decimal(5,2)', 'Recycled content of packaging', i => between(`m-rc-${i}`, 18, 74, 1)),
    ],
    relationships: [
      rel('triggers', 'Inventory_Position', 'Stock is held per material and plant'),
      rel('triggers', 'Production_Order', 'Finished goods are made to order'),
    ],
  },
  {
    name: 'Inventory_Position', systemKey: 'sap', domain: 'Inventory', scorProcess: 'Deliver', riskLevel: 'medium',
    semantic: 'Stock on hand per material, plant and storage location.',
    fdwMappingStatus: 'mapped', totalRows: 6388,
    cols: [
      c('Material_ID', 'char(18)', 'Material', i => prod(i).id),
      c('Material_Description', 'varchar(80)', 'Material description', i => prod(i).name),
      c('Plant', 'char(4)', 'Plant', i => plant(i + Math.floor(i / PRODUCTS.length)).id),
      c('Storage_Location', 'char(4)', 'Storage location', i => pick(['FG01', 'FG02', 'QA01', 'FG01', 'RT01'], i)),
      c('Unrestricted_Qty', 'decimal(13,3)', 'Available stock in cases', i => between(`inv-u-${i}`, 800, 48000)),
      c('Blocked_Qty', 'decimal(13,3)', 'Blocked stock in cases', i => (i % 5 === 3 ? between(`inv-b-${i}`, 100, 2400) : 0)),
      c('In_Transit_Qty', 'decimal(13,3)', 'Stock in transit', i => between(`inv-t-${i}`, 0, 6000)),
      c('Days_Of_Supply', 'decimal(6,1)', 'Days of supply at current demand', i => between(`inv-d-${i}`, 4, 71, 1)),
      c('Reorder_Point', 'decimal(13,3)', 'Reorder point in cases', i => pick([15000, 15000, 8000, 5000, 5000, 8000, 10000, 2000], i)),
      c('Stock_Status', 'varchar(24)', 'Stock health', i => pick(['Healthy', 'Healthy', 'Below reorder point', 'Healthy', 'Overstock', 'Expiring soon'], i)),
    ],
    relationships: [
      rel('depends_on', 'Material_Master', 'Stock of a material'),
      rel('depends_on', 'Plant_Master', 'Held at a plant'),
      rel('constrained_by', 'POL-INV-001', 'Min, max and reorder rules', 'onto_policy'),
    ],
  },
  {
    name: 'Production_Order', systemKey: 'sap', domain: 'Manufacturing', scorProcess: 'Make', riskLevel: 'medium',
    semantic: 'Order to fill and pack a finished good on a production line.',
    fdwMappingStatus: 'mapped', totalRows: 3902,
    cols: [
      c('Order_ID', 'char(12)', 'Production order', i => `PRD-${60410 + i}`),
      c('Material_ID', 'char(18)', 'Finished good', i => prod(i).id),
      c('Plant', 'char(4)', 'Producing plant', i => plant(i).id),
      c('Line_ID', 'char(8)', 'Production line', i => `LINE-0${1 + (i % 6)}`),
      c('Planned_Qty', 'decimal(13,3)', 'Planned cases', i => between(`prd-p-${i}`, 4, 40) * 1000),
      c('Actual_Qty', 'decimal(13,3)', 'Confirmed cases', i => Math.round(between(`prd-p-${i}`, 4, 40) * 1000 * between(`prd-y-${i}`, 0.9, 1, 3))),
      c('Yield_Pct', 'decimal(5,2)', 'Yield %', i => round(between(`prd-y-${i}`, 0.9, 1, 3) * 100, 1)),
      c('Start_Date', 'date', 'Scheduled start', i => dayAgo(i * 2 - 3)),
      c('End_Date', 'date', 'Scheduled finish', i => dayAgo(i * 2 - 4)),
      c('Status', 'varchar(20)', 'Order status', i => pick(['Completed', 'In process', 'Released', 'Completed', 'Delayed', 'Completed'], i)),
    ],
    relationships: [
      rel('depends_on', 'Material_Master', 'Produces a finished good'),
      rel('depends_on', 'Plant_Master', 'Runs at a plant'),
      rel('triggers', 'Inventory_Position', 'Confirmed output raises stock'),
    ],
  },
  {
    name: 'Delivery_Document', systemKey: 'sap', domain: 'Logistics', scorProcess: 'Deliver', riskLevel: 'medium',
    semantic: 'Outbound delivery to a customer. Goods issue is the trigger for invoicing.',
    fdwMappingStatus: 'mapped', totalRows: 11876,
    cols: [
      c('Delivery_ID', 'char(10)', 'Delivery number', i => `80${pad(31450 + i, 6)}`),
      c('Sales_Order_Ref', 'varchar(18)', 'Salesforce order reference', i => `OPP-${10231 + i}`),
      c('Ship_To', 'varchar(80)', 'Ship-to customer', i => cust(i)),
      c('Plant', 'char(4)', 'Shipping plant', i => plant(i).id),
      c('Material_ID', 'char(18)', 'Material shipped', i => prod(i).id),
      c('Delivered_Qty', 'decimal(13,3)', 'Cases delivered', i => between(`dlv-q-${i}`, 200, 9000)),
      c('Planned_GI_Date', 'date', 'Planned goods issue', i => dayAgo(2 + i)),
      c('Actual_GI_Date', 'date', 'Actual goods issue', i => (i % 5 === 2 ? null : dayAgo(2 + i - (i % 4 === 3 ? -2 : 0)))),
      c('Carrier', 'varchar(40)', 'Carrier', i => pick(['TransGlobal Freight', 'Northline Haulage', 'BlueRoute Logistics'], i)),
      c('Status', 'varchar(24)', 'Delivery status', i => pick(['Delivered', 'Delivered', 'In transit', 'Delayed', 'Delivered', 'Partially delivered'], i)),
    ],
    relationships: [
      rel('depends_on', 'Opportunity', 'Fulfils a won order'),
      rel('depends_on', 'Inventory_Position', 'Ships from available stock'),
      rel('triggers', 'AR_Invoice', 'Goods issue triggers invoicing'),
    ],
  },
  {
    name: 'Plant_Master', systemKey: 'sap', domain: 'Manufacturing', scorProcess: 'Enable', riskLevel: 'low',
    semantic: 'Filling plant with capacity, energy and water intensity.',
    fdwMappingStatus: 'mapped', totalRows: 5,
    cols: [
      c('Plant', 'char(4)', 'Plant code', i => plant(i).id),
      c('Name', 'varchar(40)', 'Plant name', i => plant(i).name),
      c('Country', 'char(2)', 'Country', i => plant(i).country),
      c('Lines', 'integer', 'Production lines', i => pick([6, 4, 5, 3, 4], i)),
      c('Capacity_Cases_Per_Day', 'integer', 'Daily capacity in cases', i => pick([82000, 54000, 67000, 38000, 49000], i)),
      c('Energy_kWh_Per_Case', 'decimal(6,3)', 'Energy use per case', i => pick([0.412, 0.468, 0.395, 0.521, 0.447], i)),
      c('Water_L_Per_Case', 'decimal(6,2)', 'Water use per case', i => pick([1.84, 2.12, 1.76, 2.41, 1.98], i)),
    ],
    relationships: [rel('triggers', 'Production_Order', 'Plants run production orders')],
  },
  {
    name: 'Goods_Receipt', systemKey: 'sap', domain: 'Procurement', scorProcess: 'Source', riskLevel: 'low',
    semantic: 'Receipt of ordered material at a plant, with incoming quality result.',
    fdwMappingStatus: 'virtual', totalRows: 0,
    cols: [
      c('GR_ID', 'char(10)', 'Material document', i => `50${pad(20110 + i, 6)}`),
      c('PO_Number', 'char(10)', 'Purchase order', i => `45000${pad(1210 + i)}`),
      c('Material_ID', 'char(18)', 'Material received', i => pick(RAW_MATERIALS, i).id),
      c('Received_Qty', 'decimal(13,3)', 'Quantity received', i => between(`po-q-${i}`, 2, 90) * 1000),
      c('Posting_Date', 'date', 'Posting date', i => dayAgo(1 + i * 2)),
      c('Plant', 'char(4)', 'Receiving plant', i => plant(i).id),
      c('Quality_Status', 'varchar(20)', 'Incoming inspection result', i => pick(['Released', 'Released', 'In inspection', 'Released', 'Rejected'], i)),
    ],
    relationships: [rel('depends_on', 'Purchase_Order', 'Received against a purchase order')],
  },
  // ---- Google Drive -------------------------------------------------------
  {
    name: 'Contract_Document', systemKey: 'gdrive', domain: 'Procurement', scorProcess: 'Source', riskLevel: 'high',
    semantic: 'Supplier contract extracted from Google Drive: prices, volumes, SLAs and penalties.',
    fdwMappingStatus: 'mapped', totalRows: 38,
    cols: [
      c('Contract_ID', 'varchar(20)', 'Contract reference', i => `CTR-2026-${pad(41 + i, 3)}`),
      c('Document_Path', 'varchar(400)', 'Drive path', i => `/Procurement/Contracts/2026/${vend(i).replace(/[^A-Za-z]+/g, '_')}_supply_agreement.pdf`),
      c('Vendor_ID', 'varchar(10)', 'Supplier', i => `V-${1001 + (i % VENDORS.length)}`),
      c('Effective_Date', 'date', 'Contract start', i => dayAgo(200 + i * 21)),
      c('Expiry_Date', 'date', 'Contract end', i => dayAgo(i * 21 - 165)),
      c('Contracted_Price', 'numeric(10,2)', 'Unit price in USD', i => between(`ctr-p-${i}`, 0.08, 9.4, 2), 'medium'),
      c('Volume_Commitment', 'integer', 'Committed annual volume', i => between(`ctr-v-${i}`, 20, 900) * 1000),
      c('SLA_Terms', 'varchar(200)', 'Service levels', i => pick(['98% on-time, 5-day lead time', '95% on-time, 10-day lead time', '99.5% fill rate, 48h replenishment', '97% on-time, 7-day lead time'], i)),
      c('Penalty_Clauses', 'varchar(200)', 'Penalties', i => pick(['2% of order value per late day, capped at 10%', 'Service credit of 5% below SLA', 'None', '1.5% per late day, capped at 8%'], i)),
      c('Auto_Renewal', 'boolean', 'Renews automatically', i => i % 3 !== 1),
      c('Extraction_Confidence', 'numeric(5,1)', 'Extraction confidence %', i => between(`ctr-c-${i}`, 71, 99, 1)),
    ],
    relationships: [
      rel('constrained_by', 'Vendor_Master', 'Signed with a supplier'),
      rel('triggers', 'Purchase_Order', 'Sets the price purchase orders must follow'),
    ],
  },
  {
    name: 'Sustainability_Report', systemKey: 'gdrive', domain: 'ESG', scorProcess: 'Enable', riskLevel: 'low',
    semantic: 'Sustainability report extracted from Google Drive with targets and actuals.',
    fdwMappingStatus: 'mapped', totalRows: 14,
    cols: [
      c('Report_ID', 'varchar(20)', 'Report reference', i => `ESG-2026-${pad(7 + i, 3)}`),
      c('Framework', 'varchar(10)', 'Reporting framework', i => pick(['GRI', 'SASB', 'CDP', 'TCFD'], i)),
      c('Report_Type', 'varchar(40)', 'Report type', i => pick(['Carbon_Disclosure', 'Water_Stewardship', 'Packaging_Circularity', 'Climate_Risk', 'Energy_Audit'], i)),
      c('Period', 'varchar(10)', 'Reporting period', i => pick(['2026-Q3', '2026-Q2', '2026-H1', 'FY2025'], i)),
      c('KPIs_Extracted', 'integer', 'KPIs found', i => between(`esg-k-${i}`, 6, 24)),
      c('Targets', 'varchar(200)', 'Stated targets', i => pick(['Scope 1+2 down 30% by 2028', 'Water ratio 1.7 L per case', '50% recycled aluminium by 2027', 'Net zero logistics by 2035'], i)),
      c('Actuals', 'varchar(200)', 'Reported actuals', i => pick(['Down 17% against 2023 baseline', '1.98 L per case', '41% recycled aluminium', '12% of fleet electric'], i)),
      c('Document_Path', 'varchar(400)', 'Drive path', i => `/Sustainability/Reports/${pick(['2026-Q3', '2026-Q2', '2026-H1', 'FY2025'], i)}_${pick(['carbon_disclosure', 'water_stewardship', 'packaging_circularity', 'climate_risk', 'energy_audit'], i)}.pdf`),
    ],
    relationships: [rel('depends_on', 'Plant_Master', 'Reports plant-level footprint')],
  },
  // ---- Social listening ---------------------------------------------------
  {
    name: 'Market_Signal', systemKey: 'social', domain: 'Risk', scorProcess: 'Plan', riskLevel: 'medium',
    semantic: 'External event that may disrupt supply or shift demand.',
    fdwMappingStatus: 'mapped', totalRows: 264,
    cols: [
      c('Signal_ID', 'varchar(20)', 'Signal reference', i => `SIG-${7301 + i}`),
      c('Event_Type', 'varchar(40)', 'Event type', i => pick(['Port_Congestion', 'Price_Spike', 'Weather_Alert', 'Labour_Strike', 'Regulatory_Change', 'Supplier_Insolvency', 'Demand_Surge'], i)),
      c('Location', 'varchar(60)', 'Where it happens', i => pick(['Rotterdam, NL', 'Queensland, AU', 'Gulf of Mexico, US', 'Felixstowe, GB', 'Brussels, BE', 'Hamburg, DE', 'Texas, US'], i)),
      c('Affected_Commodity', 'varchar(40)', 'Commodity affected', i => pick(['Aluminium', 'Cane sugar', 'CO2', 'Freight', 'Caffeine', 'Shrink film', 'Finished goods'], i)),
      c('Severity', 'varchar(10)', 'Severity', i => pick(['High', 'Medium', 'Critical', 'Medium', 'Low', 'High', 'Low'], i)),
      c('Source', 'varchar(40)', 'Where the signal came from', i => pick(['News_Wire', 'Trade_Journal', 'Weather_Service', 'Social_Media', 'Regulator_Feed'], i)),
      c('Timestamp', 'timestamp', 'When it was detected', i => ago(35 + i * 190)),
    ],
    relationships: [rel('triggers', 'Vendor_Master', 'Signals feed supplier risk scores')],
  },
  {
    name: 'Brand_Sentiment', systemKey: 'social', domain: 'Marketing', scorProcess: 'Plan', riskLevel: 'low',
    semantic: 'Brand sentiment by platform and topic.',
    fdwMappingStatus: 'mapped', totalRows: 1920,
    cols: [
      c('Brand', 'varchar(40)', 'Brand', i => pick(['Kinetiq Original', 'Kinetiq Zero Sugar', 'Kinetiq Citrus Surge', 'Kinetiq Hydrate Sport', 'Kinetiq Focus Tea'], i)),
      c('Product_Category', 'varchar(30)', 'Category', i => pick(['Energy', 'Energy', 'Carbonated', 'Sports', 'Tea'], i)),
      c('Platform', 'varchar(30)', 'Platform', i => pick(['Instagram', 'TikTok', 'Reddit', 'X', 'YouTube', 'Retail_Reviews'], i)),
      c('Topic', 'varchar(60)', 'Topic', i => pick(['Taste', 'Price', 'Sugar content', 'Packaging', 'Availability', 'Sustainability', 'Caffeine level'], i)),
      c('Sentiment_Score', 'numeric(4,2)', 'Score from -1 to 1', i => between(`sent-${i}`, -0.62, 0.88, 2)),
      c('Mention_Count', 'integer', 'Mentions in the period', i => between(`ment-${i}`, 140, 18400)),
      c('Period', 'varchar(10)', 'Period', i => pick(['2026-W45', '2026-W44', '2026-W43'], Math.floor(i / 6))),
    ],
    relationships: [rel('depends_on', 'Campaign', 'Campaigns move sentiment')],
  },
  {
    name: 'Commodity_Price', systemKey: 'social', domain: 'Procurement', scorProcess: 'Source', riskLevel: 'low',
    semantic: 'Market price of a key input commodity.',
    fdwMappingStatus: 'mapped', totalRows: 730,
    cols: [
      c('Commodity', 'varchar(40)', 'Commodity', i => pick(['Aluminium', 'Raw_Sugar', 'CO2_Food_Grade', 'PET_Resin', 'Diesel', 'Natural_Gas', 'Caffeine', 'Citric_Acid'], i)),
      c('Price_Per_Unit', 'numeric(12,2)', 'Price', i => pick([2614.5, 428.3, 182.0, 1096.4, 1.12, 3.41, 14.8, 0.94], i)),
      c('Currency', 'char(3)', 'Currency', () => 'USD'),
      c('Unit', 'varchar(10)', 'Unit', i => pick(['tonne', 'tonne', 'tonne', 'tonne', 'litre', 'MMBtu', 'kg', 'kg'], i)),
      c('Change_Pct_30D', 'numeric(6,2)', 'Change over 30 days %', i => pick([6.8, -2.4, 11.2, -0.6, 3.1, -7.9, 1.4, 0.3], i)),
      c('Source', 'varchar(40)', 'Price source', i => pick(['LME', 'ICE', 'Spot survey', 'ICIS', 'EIA', 'EIA', 'Supplier index', 'Supplier index'], i)),
      c('Date', 'date', 'Price date', i => dayAgo(Math.floor(i / 8))),
    ],
    relationships: [rel('triggers', 'Purchase_Order', 'Price moves drive variance against contract')],
  },
  // ---- File uploads -------------------------------------------------------
  {
    name: 'Invoice_Upload', systemKey: 'files', domain: 'Procurement', scorProcess: 'Source', riskLevel: 'medium',
    semantic: 'Scanned supplier invoice with extracted header fields.',
    fdwMappingStatus: 'mapped', totalRows: 126,
    cols: [
      c('File_Path', 'varchar(400)', 'Uploaded file', i => `/uploads/invoices/2026-11/${vend(i).split(' ')[0].toLowerCase()}_invoice_${71200 + i}.pdf`),
      c('Invoice_Number', 'varchar(30)', 'Invoice number', i => `API-${71200 + i}`),
      c('Vendor_Name', 'varchar(120)', 'Supplier', i => vend(i)),
      c('Invoice_Amount', 'numeric(14,2)', 'Amount in USD', i => between(`po-amt-${i}`, 6, 380) * 1000),
      c('PO_Reference', 'varchar(12)', 'Purchase order', i => `45000${pad(1210 + i)}`),
      c('Extraction_Confidence', 'numeric(5,1)', 'Extraction confidence %', i => between(`iu-c-${i}`, 58, 99, 1)),
      c('Validation_Status', 'varchar(20)', 'Validation result', i => pick(['Validated', 'Validated', 'Needs_Review', 'Validated', 'Pending', 'Rejected'], i)),
      c('Upload_Date', 'timestamp', 'Uploaded at', i => ago(50 + i * 310)),
    ],
    relationships: [rel('syncs_to', 'AP_Invoice', 'Validated uploads become supplier invoices')],
  },
  {
    name: 'Lab_Report_Upload', systemKey: 'files', domain: 'Quality', scorProcess: 'Make', riskLevel: 'medium',
    semantic: 'Laboratory report for a production batch, checked against specification.',
    fdwMappingStatus: 'unmapped', totalRows: 0,
    cols: [
      c('File_Path', 'varchar(400)', 'Uploaded file', i => `/uploads/lab-reports/2026-11/batch_B${26110 + i}_${pick(['micro', 'brix', 'caffeine', 'carbonation'], i)}.pdf`),
      c('Batch_ID', 'varchar(12)', 'Production batch', i => `B${26110 + i}`),
      c('Material_ID', 'varchar(18)', 'Finished good', i => prod(i).id),
      c('Test_Type', 'varchar(40)', 'Test', i => pick(['Microbiology', 'Brix', 'Caffeine assay', 'Carbonation'], i)),
      c('Result_Value', 'varchar(40)', 'Result', i => pick(['< 10 cfu/ml', '11.2 °Bx', '31.8 mg/100ml', '3.6 vol'], i)),
      c('Lab_Name', 'varchar(60)', 'Laboratory', i => pick(['Eurolab Rotterdam', 'Northern Analytical', 'In-house QA Austin'], i)),
      c('Extraction_Confidence', 'numeric(5,1)', 'Extraction confidence %', i => between(`lr-c-${i}`, 66, 99, 1)),
      c('Spec_Compliance', 'boolean', 'Within specification', i => pick([true, true, true, false, true, null], i)),
      c('Upload_Date', 'timestamp', 'Uploaded at', i => ago(80 + i * 420)),
    ],
    relationships: [rel('depends_on', 'Production_Order', 'Tests a production batch')],
  },
];

export const entityByName = (name: string) => ENTITIES.find(e => e.name.toLowerCase() === String(name).toLowerCase());
export const systemOf = (e: EntityDef) => systemByKey(e.systemKey);
export const ENTITY_NAMES = ENTITIES.map(e => e.name);

/** Rows for a catalogue entity. Deterministic: row i is always the same. */
export function entityRows(e: EntityDef, count: number, offset = 0): Record<string, unknown>[] {
  const rows: Record<string, unknown>[] = [];
  for (let i = offset; i < offset + count; i++) {
    const row: Record<string, unknown> = {};
    for (const col of e.cols) row[col.name] = col.gen(i);
    rows.push(row);
  }
  return rows;
}

/** Entity as the Entity Explorer and knowledge graph read it. */
export const schemaEntity = (e: EntityDef) => ({
  name: e.name,
  system: systemOf(e).system,
  domain: e.domain,
  semantic: e.semantic,
  riskLevel: e.riskLevel,
  isVirtual: e.fdwMappingStatus === 'virtual',
  fdwMappingStatus: e.fdwMappingStatus,
  scorProcess: e.scorProcess,
  fields: e.cols.map((col, i) => ({
    name: col.name,
    dataType: col.dataType,
    semantic: col.semantic,
    riskLevel: col.riskLevel,
    constraints: i === 0 ? ['primary_key', 'not_null'] : col.riskLevel === 'high' ? ['approval_required'] : [],
  })),
  relationships: e.relationships,
});

// ---------------------------------------------------------------------------
// Mapping rules: one per mapped entity, plus a draft and an inactive rule.
// ---------------------------------------------------------------------------

const camel = (s: string) => s.replace(/__c$/, '').replace(/_([a-zA-Z])/g, (_, ch: string) => ch.toUpperCase()).replace(/^./, ch => ch.toLowerCase());

export const MAPPING_RULES = ENTITIES.filter(e => e.fdwMappingStatus !== 'unmapped').map((e, i) => {
  const sys = systemOf(e);
  const status = e.fdwMappingStatus === 'virtual' ? 'draft' : e.name === 'Campaign' ? 'inactive' : 'active';
  return {
    id: `mr-${pad(i + 1, 3)}`,
    name: `${e.name} from ${sys.label}`,
    virtualEntity: e.name,
    sourceType: (sys.fdwSource === 'external' ? 'ETL' : e.name === 'AR_Payment' ? 'CDC' : 'FDW') as 'FDW' | 'ETL' | 'CDC',
    sourceSystem: sys.system,
    sourceTable: e.name,
    sourceSchema: sys.schema,
    fieldMaps: e.cols.map((col, k) => ({
      sourceField: col.name,
      targetField: camel(col.name),
      ...(col.dataType.startsWith('date') && k % 2 === 0 ? { transform: 'to_date' } : {}),
      ...(col.name === 'currency' || col.name === 'Currency' ? { defaultValue: 'USD' } : {}),
    })),
    businessLogic: e.riskLevel === 'high' ? 'Values in USD. Rows flagged for approval are excluded until approved.' : '',
    filterExpression: e.name === 'Opportunity' ? "StageName <> 'Closed Lost'" : e.name === 'AR_Invoice' ? "status <> 'Void'" : '',
    status: status as 'draft' | 'active' | 'inactive',
    createdAt: ago(DAY * (60 - i)),
    updatedAt: ago(HOUR * (5 + i * 7)),
  };
});
export const ruleForEntity = (name: string) => MAPPING_RULES.find(r => r.virtualEntity === name);

// ---------------------------------------------------------------------------
// Journeys. Keys are given in both spellings: the home page reads snake_case,
// the journey service reads camelCase.
// ---------------------------------------------------------------------------

/** Step ids per stage, as the Journey Studio hard-codes them. */
export const STAGE_STEPS: Record<string, string[]> = {
  order_to_cash: ['entity_resolution', 'three_way_match', 'anomaly_scoring', 'risk_prioritization', 'workflow_actions', 'dunning_and_collections', 'action_summary', 'cash_flow_projection', 'store_results', 'verify_results'],
  demand_forecasting: ['feature_engineering', 'model_ensemble', 'promotion_overlay', 'cannibalization_adjustment', 'consensus_integration', 'publish_forecast'],
  inventory_optimization: ['load_positions', 'abc_classification', 'reorder_calculation', 'expiry_analysis', 'rebalance_recommendations', 'publish_results'],
  procurement_analytics: ['load_procurement_data', 'spend_classification', 'three_way_match', 'price_variance_analysis', 'vendor_scorecard', 'publish_results'],
  semantic_rag: ['extract_unified_schema', 'resolve_fdw_mapping', 'extract_mapping_rules', 'extract_policies', 'extract_workflows', 'extract_integrations', 'normalize', 'enrich', 'chunk_embed', 'load_vector', 'index_nlq_exemplars', 'load_graph', 'validate'],
  supply_chain_risk: ['load_supplier_data', 'delivery_scoring', 'quality_scoring', 'financial_risk', 'market_signal_integration', 'publish_results'],
  etl_pipeline: ['extract', 'validate_schema', 'transform', 'load', 'verify'],
};

interface JourneySeed {
  id: string; name: string; type: string; stageId: string; stageName: string; description: string;
  status: string; createdMin: number; updatedMin: number;
  total: number; completed: number; running: number; failed: number; avgSeconds: number;
  oda?: string; config?: Record<string, unknown>; currentStep?: string;
}

const journeySeeds: JourneySeed[] = [
  { id: 'jr-o2c-01', name: 'Order-to-Cash daily run', type: 'order_to_cash', stageId: 'order_to_cash', stageName: 'Order-to-Cash Monitor', description: 'Matches orders, deliveries and invoices and raises collection actions.', status: 'completed', createdMin: DAY * 21, updatedMin: 42, total: 64, completed: 61, running: 0, failed: 3, avgSeconds: 184 },
  { id: 'jr-dfc-01', name: 'Demand forecast refresh', type: 'demand_forecasting', stageId: 'demand_forecasting', stageName: 'Demand Forecasting Engine', description: 'Rebuilds the 13-week forecast by SKU and region.', status: 'running', createdMin: DAY * 14, updatedMin: 3, total: 28, completed: 26, running: 1, failed: 1, avgSeconds: 412 },
  { id: 'jr-inv-01', name: 'Inventory rebalancing', type: 'inventory_optimization', stageId: 'inventory_optimization', stageName: 'Inventory Optimization', description: 'Recalculates reorder points and proposes inter-plant transfers.', status: 'completed', createdMin: DAY * 9, updatedMin: 190, total: 19, completed: 19, running: 0, failed: 0, avgSeconds: 96 },
  { id: 'jr-prc-01', name: 'Procurement spend scan', type: 'procurement_analytics', stageId: 'procurement_analytics', stageName: 'Procurement & Spend Analytics', description: 'Classifies spend and checks prices against contracts.', status: 'failed', createdMin: DAY * 6, updatedMin: 75, total: 12, completed: 9, running: 0, failed: 3, avgSeconds: 233 },
  { id: 'jr-rag-01', name: 'Knowledge Processor', type: 'semantic-rag', stageId: 'semantic_rag', stageName: 'Knowledge Processor', description: 'Builds the enterprise knowledge index from schemas, policies, workflows and integrations.', status: 'completed', createdMin: DAY * 30, updatedMin: 380, total: 41, completed: 40, running: 0, failed: 1, avgSeconds: 521 },
  { id: 'jr-risk-01', name: 'Supplier risk radar', type: 'supply_chain_risk', stageId: 'supply_chain_risk', stageName: 'Supply Chain Risk Radar', description: 'Scores suppliers on delivery, quality, finance and market signals.', status: 'created', createdMin: HOUR * 20, updatedMin: HOUR * 20, total: 0, completed: 0, running: 0, failed: 0, avgSeconds: 0 },
];

const pipelineSeeds: JourneySeed[] = [
  { id: 'jr-pipe-social', name: 'Social listening ingest', type: 'data-pipeline', stageId: 'etl_pipeline', stageName: 'ETL Pipeline - Social Listening', description: 'Incremental load of market signals, sentiment and commodity prices.', status: 'running', createdMin: DAY * 18, updatedMin: 2, total: 96, completed: 93, running: 1, failed: 2, avgSeconds: 48, oda: 'data-pipeline', currentStep: 'transform', config: { mappingRuleId: ruleForEntity('Market_Signal')?.id, sourceType: 'social_listening', mode: 'incremental', batchSize: 1000, schedule: '0 */6 * * *' } },
  { id: 'jr-pipe-files', name: 'Invoice uploads load', type: 'data-pipeline', stageId: 'etl_pipeline', stageName: 'ETL Pipeline - File Uploads', description: 'Full load of extracted supplier invoices.', status: 'completed', createdMin: DAY * 12, updatedMin: 260, total: 31, completed: 31, running: 0, failed: 0, avgSeconds: 72, oda: 'data-pipeline', currentStep: 'verify', config: { mappingRuleId: ruleForEntity('Invoice_Upload')?.id, sourceType: 'file_uploads', mode: 'full', batchSize: 500, schedule: '0 */12 * * *' } },
  { id: 'jr-pipe-drive', name: 'Google Drive contracts sync', type: 'data-pipeline', stageId: 'etl_pipeline', stageName: 'ETL Pipeline - Google Drive', description: 'Full load of supplier contracts and sustainability reports.', status: 'failed', createdMin: DAY * 11, updatedMin: 95, total: 22, completed: 19, running: 0, failed: 3, avgSeconds: 131, oda: 'data-pipeline', currentStep: 'validate_schema', config: { mappingRuleId: ruleForEntity('Contract_Document')?.id, sourceType: 'google_drive', mode: 'full', batchSize: 200, schedule: '' } },
];

const toJourney = (s: JourneySeed) => {
  const stageStatus = s.status === 'created' ? 'pending' : s.status;
  const progress = s.status === 'completed' ? 100 : s.status === 'running' ? 64 : s.status === 'failed' ? 38 : 0;
  return {
    id: s.id, journeyId: s.id, journey_id: s.id,
    name: s.name, description: s.description,
    type: s.type, status: s.status,
    odaComponentType: s.oda || 'resource-management',
    solution_id: s.type,
    created_at: ago(s.createdMin), createdAt: ago(s.createdMin),
    updated_at: ago(s.updatedMin), updatedAt: ago(s.updatedMin),
    total_jobs: s.total, totalJobs: s.total, jobCount: s.total,
    completed_jobs: s.completed, completedJobs: s.completed,
    running_jobs: s.running, runningJobs: s.running,
    failed_jobs: s.failed, failedJobs: s.failed,
    success_rate: s.total ? round((s.completed * 100) / (s.completed + s.failed || 1), 1) : 0,
    avg_duration_seconds: s.avgSeconds,
    overallProgress: progress,
    stages: [{ stageId: s.stageId, name: s.stageName, description: s.description, order: 0, status: stageStatus, progress }],
    ...(s.config ? { config: s.config, currentStep: s.currentStep, lastRunAt: ago(s.updatedMin) } : {}),
  };
};

/** The six journeys shown on Home and in AI Automation. */
export const JOURNEYS = journeySeeds.map(toJourney);
/** Data pipelines (journeys with component type data-pipeline). */
export const PIPELINES = pipelineSeeds.map(toJourney);
export const ALL_JOURNEYS = [...JOURNEYS, ...PIPELINES];
export type Journey = (typeof JOURNEYS)[number];

/** Journeys saved from the Copilot (control-plane journey documents). */
export const COPILOT_JOURNEYS = [
  {
    journey_id: 'cj-overdue-followup', title: 'Overdue invoice follow-up', kind: 'copilot', solution_id: 'order-to-cash',
    tags: ['collections', 'finance'], createdBy: emailOf(PEOPLE[1]), createdMin: DAY * 8, updatedMin: HOUR * 7,
    description: 'Finds invoices more than 30 days overdue and sends tiered collection notices.',
    steps: [
      { step_id: 'find_overdue', name: 'Find overdue invoices', tool: 'query_ar_invoices', description: 'Invoices past due by more than 30 days' },
      { step_id: 'check_credit', name: 'Check credit exposure', tool: 'get_customer_credit_status', description: 'Compare open balance with credit limit' },
      { step_id: 'send_notice', name: 'Send dunning notice', tool: 'send_dunning_notice', description: 'Notice level by ageing bucket' },
      { step_id: 'log_actions', name: 'Log actions', tool: 'write_action_log', description: 'Record each notice for audit' },
    ],
  },
  {
    journey_id: 'cj-low-stock-transfer', title: 'Low stock transfer proposal', kind: 'copilot', solution_id: 'inventory-optimization',
    tags: ['inventory'], createdBy: emailOf(PEOPLE[2]), createdMin: DAY * 5, updatedMin: HOUR * 30,
    description: 'Proposes inter-plant transfers for SKUs below reorder point.',
    steps: [
      { step_id: 'find_low_stock', name: 'Find SKUs below reorder point', tool: 'query_inventory_positions', description: 'Stock status below reorder point' },
      { step_id: 'find_surplus', name: 'Find surplus plants', tool: 'find_surplus_stock', description: 'Plants with more than 45 days of supply' },
      { step_id: 'propose_transfer', name: 'Propose transfers', tool: 'create_transfer_proposal', description: 'One proposal per SKU and lane' },
    ],
  },
  {
    journey_id: 'cj-contract-price-check', title: 'Contract price check', kind: 'builder', solution_id: 'procurement-analytics',
    tags: ['procurement', 'contracts'], createdBy: emailOf(PEOPLE[4]), createdMin: DAY * 3, updatedMin: HOUR * 52,
    description: 'Compares purchase order prices with contracted prices and flags variances above 5%.',
    steps: [
      { step_id: 'load_contracts', name: 'Load active contracts', tool: 'query_contract_documents', description: 'Contracts in force today' },
      { step_id: 'load_orders', name: 'Load open purchase orders', tool: 'query_purchase_orders', description: 'Open and partially received orders' },
      { step_id: 'compare_prices', name: 'Compare prices', tool: 'compute_price_variance', description: 'Variance against contracted price' },
      { step_id: 'raise_alerts', name: 'Raise variance alerts', tool: 'create_procurement_alert', description: 'Alert buyers above threshold' },
      { step_id: 'notify_buyers', name: 'Notify buyers', tool: 'send_notification', description: 'Summary to the category buyer' },
    ],
  },
  {
    journey_id: 'cj-supplier-risk-brief', title: 'Weekly supplier risk brief', kind: 'copilot', solution_id: 'supply-chain-risk',
    tags: ['risk'], createdBy: ADMIN_EMAIL, createdMin: DAY * 2, updatedMin: HOUR * 20,
    description: 'Summarises supplier risk movements and new market signals for the weekly review.',
    steps: [
      { step_id: 'load_scores', name: 'Load supplier scores', tool: 'query_vendor_master', description: 'Current risk, delivery and quality scores' },
      { step_id: 'load_signals', name: 'Load market signals', tool: 'query_market_signals', description: 'High and critical signals from the last 7 days' },
      { step_id: 'write_brief', name: 'Write the brief', tool: 'summarise_findings', description: 'One page for the review meeting' },
    ],
  },
].map(j => ({ ...j, step_count: j.steps.length, createdAt: ago(j.createdMin), updatedAt: ago(j.updatedMin) }));

// ---------------------------------------------------------------------------
// Tools and connector APIs (Reasoning, registries, builder, diagnostics)
// ---------------------------------------------------------------------------

export interface ToolDef {
  name: string; description: string; group: string; risk: 'read_only' | 'low_risk_write' | 'high_risk_write';
  approval?: boolean; connectorApi?: string | null; tags: string[];
  params: Record<string, { type: string; description: string }>; required?: string[];
}

export const TOOLS: ToolDef[] = [
  { name: 'semantic_search', description: 'Search schemas, policies, workflows and integrations in the knowledge index.', group: 'rag', risk: 'read_only', tags: ['rag', 'knowledge'], params: { query: { type: 'string', description: 'What to look for' }, limit: { type: 'integer', description: 'Maximum results' } }, required: ['query'] },
  { name: 'virtual_query', description: 'Query a virtual entity through the virtual data layer.', group: 'virtual_query', risk: 'read_only', tags: ['vdl'], params: { entity: { type: 'string', description: 'Virtual entity name' }, filters: { type: 'object', description: 'Field filters' }, limit: { type: 'integer', description: 'Maximum rows' } }, required: ['entity'] },
  { name: 'query_ar_invoices', description: 'List customer invoices by status, customer or ageing bucket.', group: 'o2c', risk: 'read_only', connectorApi: 'oracle.ar_invoice.list', tags: ['finance', 'o2c'], params: { status: { type: 'string', description: 'Invoice status' }, days_past_due: { type: 'integer', description: 'Minimum days past due' } } },
  { name: 'get_customer_credit_status', description: 'Credit limit, open balance and risk tier for a customer.', group: 'credit', risk: 'read_only', connectorApi: 'sfdc.account.get', tags: ['finance', 'credit'], params: { account_id: { type: 'string', description: 'Salesforce account id' } }, required: ['account_id'] },
  { name: 'query_inventory_positions', description: 'Stock on hand by material, plant and stock status.', group: 'inventory', risk: 'read_only', connectorApi: 'sap.inventory.list', tags: ['inventory'], params: { plant: { type: 'string', description: 'Plant code' }, stock_status: { type: 'string', description: 'Stock status' } } },
  { name: 'query_purchase_orders', description: 'Purchase orders by supplier, plant or status.', group: 'procurement', risk: 'read_only', connectorApi: 'sap.purchase_order.list', tags: ['procurement'], params: { vendor_id: { type: 'string', description: 'Supplier id' }, status: { type: 'string', description: 'Order status' } } },
  { name: 'query_vendor_master', description: 'Supplier master data with delivery, quality and risk scores.', group: 'scr', risk: 'read_only', connectorApi: 'sap.vendor.list', tags: ['procurement', 'risk'], params: { category: { type: 'string', description: 'Spend category' } } },
  { name: 'query_market_signals', description: 'External disruption signals by severity and commodity.', group: 'scr', risk: 'read_only', tags: ['risk', 'external'], params: { severity: { type: 'string', description: 'Minimum severity' }, days: { type: 'integer', description: 'Look-back window in days' } } },
  { name: 'query_contract_documents', description: 'Supplier contracts with prices, volumes and SLA terms.', group: 'procurement', risk: 'read_only', tags: ['contracts'], params: { vendor_id: { type: 'string', description: 'Supplier id' } } },
  { name: 'compute_price_variance', description: 'Compare purchase order prices with contracted prices.', group: 'procurement', risk: 'read_only', tags: ['procurement', 'analytics'], params: { threshold_pct: { type: 'number', description: 'Variance threshold in percent' } } },
  { name: 'find_surplus_stock', description: 'Plants holding more than a given number of days of supply.', group: 'inventory', risk: 'read_only', tags: ['inventory'], params: { material_id: { type: 'string', description: 'Material' }, min_days_of_supply: { type: 'number', description: 'Threshold in days' } }, required: ['material_id'] },
  { name: 'forecast_demand', description: 'Forecast demand for a SKU and region over the next weeks.', group: 'demand_forecast', risk: 'read_only', tags: ['forecast'], params: { sku: { type: 'string', description: 'SKU' }, region: { type: 'string', description: 'Region' }, weeks: { type: 'integer', description: 'Horizon in weeks' } }, required: ['sku'] },
  { name: 'summarise_findings', description: 'Write a short summary of the results gathered so far.', group: 'misc', risk: 'read_only', tags: ['summary'], params: { audience: { type: 'string', description: 'Who the summary is for' } } },
  { name: 'send_notification', description: 'Send an email or chat notification to a user or group.', group: 'notify', risk: 'low_risk_write', tags: ['notify'], params: { recipient: { type: 'string', description: 'User or group' }, message: { type: 'string', description: 'Message text' } }, required: ['recipient', 'message'] },
  { name: 'write_action_log', description: 'Record an action in the audit log of a solution.', group: 'o2c', risk: 'low_risk_write', tags: ['audit'], params: { action_type: { type: 'string', description: 'Action type' }, entity_id: { type: 'string', description: 'Affected record' } }, required: ['action_type', 'entity_id'] },
  { name: 'send_dunning_notice', description: 'Send a collection notice for an overdue invoice.', group: 'o2c', risk: 'low_risk_write', connectorApi: 'oracle.ar_invoice.add_dunning', tags: ['finance', 'collections'], params: { invoice_id: { type: 'string', description: 'Invoice number' }, level: { type: 'integer', description: 'Notice level 1-3' } }, required: ['invoice_id'] },
  { name: 'create_procurement_alert', description: 'Raise an alert for the category buyer.', group: 'procurement', risk: 'low_risk_write', tags: ['procurement', 'alerts'], params: { po_number: { type: 'string', description: 'Purchase order' }, reason: { type: 'string', description: 'Why it was flagged' } }, required: ['po_number', 'reason'] },
  { name: 'create_transfer_proposal', description: 'Propose a stock transfer between two plants.', group: 'inventory', risk: 'low_risk_write', connectorApi: 'sap.stock_transfer.create', tags: ['inventory'], params: { material_id: { type: 'string', description: 'Material' }, from_plant: { type: 'string', description: 'Sending plant' }, to_plant: { type: 'string', description: 'Receiving plant' }, quantity: { type: 'number', description: 'Cases to move' } }, required: ['material_id', 'from_plant', 'to_plant', 'quantity'] },
  { name: 'update_credit_limit', description: 'Change the credit limit of a customer account. Needs approval.', group: 'credit', risk: 'high_risk_write', approval: true, connectorApi: 'sfdc.account.update_credit_limit', tags: ['finance', 'credit'], params: { account_id: { type: 'string', description: 'Salesforce account id' }, new_limit: { type: 'number', description: 'New limit in USD' }, justification: { type: 'string', description: 'Reason for the change' } }, required: ['account_id', 'new_limit', 'justification'] },
  { name: 'place_credit_hold', description: 'Put a customer on credit hold in receivables. Needs approval.', group: 'credit', risk: 'high_risk_write', approval: true, connectorApi: 'oracle.ar_customer.set_hold', tags: ['finance', 'credit'], params: { customer_id: { type: 'string', description: 'Oracle customer id' }, reason: { type: 'string', description: 'Reason for the hold' } }, required: ['customer_id', 'reason'] },
  { name: 'block_purchase_order', description: 'Block a purchase order pending review. Needs approval.', group: 'procurement', risk: 'high_risk_write', approval: true, connectorApi: 'sap.purchase_order.block', tags: ['procurement'], params: { po_number: { type: 'string', description: 'Purchase order' }, reason: { type: 'string', description: 'Reason for the block' } }, required: ['po_number', 'reason'] },
];
export const toolParamsSchema = (t: ToolDef) => ({ type: 'object', properties: t.params, required: t.required || [] });

export interface ConnectorApiDef {
  api_id: string; target_system: 'oracle' | 'sap' | 'sfdc' | 'external'; operation: string; description: string;
  risk_level: 'read_only' | 'low_risk_write' | 'high_risk_write'; simulator_writeback: boolean; tags: string[];
  request: Record<string, string>; response: Record<string, string>;
}

export const CONNECTOR_APIS: ConnectorApiDef[] = [
  { api_id: 'sfdc.account.get', target_system: 'sfdc', operation: 'GET /sobjects/Account/{id}', description: 'Read a customer account with credit fields.', risk_level: 'read_only', simulator_writeback: false, tags: ['customer', 'credit'], request: { account_id: 'string' }, response: { Id: 'string', Name: 'string', Credit_Limit__c: 'number', Risk_Tier__c: 'string' } },
  { api_id: 'sfdc.account.update_credit_limit', target_system: 'sfdc', operation: 'PATCH /sobjects/Account/{id}', description: 'Update the credit limit of an account.', risk_level: 'high_risk_write', simulator_writeback: true, tags: ['customer', 'credit'], request: { account_id: 'string', Credit_Limit__c: 'number' }, response: { success: 'boolean', Id: 'string' } },
  { api_id: 'sfdc.opportunity.list', target_system: 'sfdc', operation: 'GET /query?q=Opportunity', description: 'List opportunities by stage or account.', risk_level: 'read_only', simulator_writeback: false, tags: ['sales'], request: { stage: 'string', account_id: 'string' }, response: { records: 'Opportunity[]', totalSize: 'integer' } },
  { api_id: 'oracle.ar_invoice.list', target_system: 'oracle', operation: 'GET /receivablesInvoices', description: 'List customer invoices.', risk_level: 'read_only', simulator_writeback: false, tags: ['finance'], request: { status: 'string', customer_id: 'integer' }, response: { items: 'AR_Invoice[]', count: 'integer' } },
  { api_id: 'oracle.ar_invoice.add_dunning', target_system: 'oracle', operation: 'POST /receivablesInvoices/{id}/dunning', description: 'Record a dunning notice against an invoice.', risk_level: 'low_risk_write', simulator_writeback: true, tags: ['finance', 'collections'], request: { invoice_id: 'string', level: 'integer' }, response: { dunning_id: 'string', status: 'string' } },
  { api_id: 'oracle.ar_customer.set_hold', target_system: 'oracle', operation: 'PATCH /receivablesCustomers/{id}', description: 'Place or release a credit hold.', risk_level: 'high_risk_write', simulator_writeback: true, tags: ['finance', 'credit'], request: { customer_id: 'integer', credit_hold: 'boolean', reason: 'string' }, response: { customer_id: 'integer', status: 'string' } },
  { api_id: 'oracle.ap_invoice.list', target_system: 'oracle', operation: 'GET /payablesInvoices', description: 'List supplier invoices with match status.', risk_level: 'read_only', simulator_writeback: false, tags: ['procurement'], request: { match_status: 'string' }, response: { items: 'AP_Invoice[]', count: 'integer' } },
  { api_id: 'sap.inventory.list', target_system: 'sap', operation: 'GET /A_MatlStkInAcctMod', description: 'Read stock by material and plant.', risk_level: 'read_only', simulator_writeback: false, tags: ['inventory'], request: { plant: 'string', material_id: 'string' }, response: { results: 'Inventory_Position[]' } },
  { api_id: 'sap.purchase_order.list', target_system: 'sap', operation: 'GET /A_PurchaseOrder', description: 'List purchase orders.', risk_level: 'read_only', simulator_writeback: false, tags: ['procurement'], request: { vendor_id: 'string', status: 'string' }, response: { results: 'Purchase_Order[]' } },
  { api_id: 'sap.purchase_order.block', target_system: 'sap', operation: 'PATCH /A_PurchaseOrder/{id}', description: 'Block a purchase order.', risk_level: 'high_risk_write', simulator_writeback: true, tags: ['procurement'], request: { po_number: 'string', reason: 'string' }, response: { po_number: 'string', status: 'string' } },
  { api_id: 'sap.stock_transfer.create', target_system: 'sap', operation: 'POST /A_StockTransportOrder', description: 'Create a stock transport order between plants.', risk_level: 'low_risk_write', simulator_writeback: true, tags: ['inventory'], request: { material_id: 'string', from_plant: 'string', to_plant: 'string', quantity: 'number' }, response: { order_id: 'string', status: 'string' } },
  { api_id: 'sap.vendor.list', target_system: 'sap', operation: 'GET /A_Supplier', description: 'List suppliers.', risk_level: 'read_only', simulator_writeback: false, tags: ['procurement', 'risk'], request: { category: 'string' }, response: { results: 'Vendor_Master[]' } },
  { api_id: 'sap.production_order.list', target_system: 'sap', operation: 'GET /A_ProductionOrder', description: 'List production orders.', risk_level: 'read_only', simulator_writeback: false, tags: ['manufacturing'], request: { plant: 'string', status: 'string' }, response: { results: 'Production_Order[]' } },
  { api_id: 'external.gdrive.contract.get', target_system: 'external', operation: 'GET /drive/contracts/{id}', description: 'Read an extracted supplier contract.', risk_level: 'read_only', simulator_writeback: false, tags: ['contracts'], request: { contract_id: 'string' }, response: { Contract_ID: 'string', Contracted_Price: 'number' } },
];
export const schemaOf = (shape: Record<string, string>) => ({
  type: 'object',
  properties: Object.fromEntries(Object.entries(shape).map(([k, v]) => [k, { type: v }])),
});
/** Tools that call a connector API. */
export const callersOf = (apiId: string) => TOOLS.filter(t => t.connectorApi === apiId).map(t => t.name);
