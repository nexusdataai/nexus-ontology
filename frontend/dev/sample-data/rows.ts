/**
 * A small query engine over sample rows.
 *
 * - Catalogue entities (Account, AR_Invoice, ...) come from fixtures.
 * - Result entities written by journeys (O2C_Order_Result, DF_Region_Summary,
 *   Quote_Header, ...) are generated from the requested column names, so any
 *   widget or dashboard panel gets rows shaped the way it asked for.
 *
 * Used by /api/v1/apps/{id}/query, /api/v1/dashboard/query, the virtual query
 * endpoints and the diagnostics.
 */
import {
  CUSTOMERS, VENDORS, PRODUCTS, RAW_MATERIALS, PLANTS, REGIONS, PRODUCT_CATEGORIES, SPEND_CATEGORIES, PEOPLE,
  ago, dayAgo, between, pick, pad, round, emailOf, entityByName, entityRows,
} from './fixtures';

type Row = Record<string, unknown>;

// ---------------------------------------------------------------------------
// KPI snapshots and alerts per solution
// ---------------------------------------------------------------------------

export const APP_PREFIX: Record<string, string> = {
  'order-to-cash': 'O2C', 'demand-forecasting': 'DF', 'inventory-optimization': 'IO',
  'procurement-analytics': 'PA', 'production-quality': 'PQ', 'supply-chain-risk': 'SCR',
  'customer-360': 'C360', 'esg-sustainability': 'ESG', 'trade-cpq': 'TCPQ', 'sourcing-cpq': 'SCPQ',
};

export const KPIS: Record<string, Record<string, number>> = {
  O2C: { dso: 38.4, match_rate: 93.6, leakage_rate: 3.2, total_open_ar: 4862000, on_time_payment_pct: 86.9 },
  DF: { mape: 12.8, bias: 2.1, stockout_rate_pct: 2.6, total_forecast_qty: 1284000 },
  IO: { turns: 10.4, fill_rate_pct: 96.2, days_of_supply: 27.5, expired_write_off_pct: 1.3 },
  PA: { total_spend: 18640000, maverick_spend_pct: 6.4, stp_rate_pct: 82.1, price_variance_pct: 3.7 },
  PQ: { oee_pct: 81.6, yield_pct: 97.4, first_pass_rate_pct: 95.8, schedule_adherence_pct: 88.2 },
  SCR: { avg_risk_score: 34.2, otd_pct: 93.1, single_source_count: 3, contract_compliance_pct: 96.4 },
  C360: { avg_clv: 412000, churn_risk_pct: 8.7, wallet_share_avg: 37.5, cross_sell_rate_pct: 26.3 },
  ESG: { carbon_intensity: 0.46, water_ratio: 1.98, recycled_content_pct: 41.2, energy_efficiency_pct: 87.9 },
  TCPQ: { open_quotes: 48, avg_margin_pct: 18.4, avg_discount_pct: 12.6, pipeline_value: 9420000 },
  SCPQ: { open_rfx: 14, bids_submitted: 61, avg_modeled_savings_pct: 6.2, avg_concentration_pct: 58.0 },
};

interface AlertSeed { type: string; severity: 'Critical' | 'High' | 'Medium' | 'Low'; entity_id: string; description: string; action: string }

const ALERTS: Record<string, AlertSeed[]> = {
  O2C: [
    { type: 'credit_limit_breach', severity: 'Critical', entity_id: 'ACC-1004', description: 'Cascade Convenience Stores is at 112% of its credit limit with two orders pending release.', action: 'Place credit hold or request a limit review' },
    { type: 'overdue_invoice', severity: 'High', entity_id: 'INV-88127', description: 'Invoice of $184,000 is 47 days past due. Second notice sent 12 days ago.', action: 'Escalate to the account owner' },
    { type: 'quantity_mismatch', severity: 'High', entity_id: 'OPP-10236', description: 'Delivered 4,180 cases against 4,600 ordered. Invoice raised for the full order.', action: 'Issue a credit note for 420 cases' },
    { type: 'missing_invoice', severity: 'Medium', entity_id: 'OPP-10244', description: 'Delivery posted 6 days ago and no invoice has been raised.', action: 'Trigger billing in Oracle' },
    { type: 'price_mismatch', severity: 'Medium', entity_id: 'OPP-10251', description: 'Invoiced unit price is 3.1% below the contract price.', action: 'Review the promotion applied' },
    { type: 'sla_breach', severity: 'Low', entity_id: 'OPP-10239', description: 'Delivery was 2 days later than the promised date.', action: 'Log the SLA breach' },
  ],
  DF: [
    { type: 'forecast_bias', severity: 'High', entity_id: 'FG-1003', description: 'Citrus Surge 500ml has been over-forecast by 14% for four weeks in the South region.', action: 'Review the promotion uplift assumption' },
    { type: 'stockout_risk', severity: 'Critical', entity_id: 'FG-1002', description: 'Zero Sugar 250ml demand in the West is forecast to exceed supply in week 47.', action: 'Raise production by 18,000 cases' },
    { type: 'override_expiring', severity: 'Medium', entity_id: 'FG-1006', description: 'A manual override on Hydrate Sport expires in 3 days.', action: 'Confirm or remove the override' },
    { type: 'new_signal', severity: 'Low', entity_id: 'SIG-7307', description: 'Heatwave forecast in Texas may lift demand for water and sports drinks.', action: 'Check the weather-adjusted forecast' },
  ],
  IO: [
    { type: 'below_reorder_point', severity: 'Critical', entity_id: 'FG-1003 / PL02', description: 'Citrus Surge at Leeds is at 6.2 days of supply against a 10-day lead time.', action: 'Transfer 9,000 cases from Rotterdam' },
    { type: 'expiry_risk', severity: 'High', entity_id: 'FG-1004 / PL04', description: '3,400 cases of Tropical 355ml expire within 60 days at Monterrey.', action: 'Start the discount workflow' },
    { type: 'overstock', severity: 'Medium', entity_id: 'FG-1008 / PL01', description: 'Protein Bites holds 71 days of supply at Rotterdam.', action: 'Pause replenishment for two cycles' },
    { type: 'blocked_stock', severity: 'Medium', entity_id: 'FG-1001 / PL03', description: '1,850 cases blocked pending a quality decision for 9 days.', action: 'Chase the quality release' },
    { type: 'count_variance', severity: 'Low', entity_id: 'FG-1007 / PL05', description: 'Cycle count differs from book stock by 0.8%.', action: 'Post the inventory difference' },
  ],
  PA: [
    { type: 'price_variance', severity: 'High', entity_id: '4500001214', description: 'Aluminium can price is 7.4% above the contracted price with Alucan Packaging.', action: 'Open a price dispute' },
    { type: 'maverick_spend', severity: 'Medium', entity_id: '4500001221', description: '$62,000 of logistics spend was placed outside a framework contract.', action: 'Route to the category buyer' },
    { type: 'three_way_mismatch', severity: 'High', entity_id: 'API-71205', description: 'Invoice quantity exceeds goods received by 1,200 kg.', action: 'Hold payment until the receipt is posted' },
    { type: 'contract_expiring', severity: 'Medium', entity_id: 'CTR-2026-044', description: 'The Pacific Sweeteners contract expires in 24 days.', action: 'Start the renewal' },
    { type: 'duplicate_invoice', severity: 'Low', entity_id: 'API-71211', description: 'Possible duplicate of invoice API-71198.', action: 'Check before payment' },
  ],
  PQ: [
    { type: 'low_yield', severity: 'High', entity_id: 'PRD-60414', description: 'Yield of 91.2% on LINE-05 against a 98% target.', action: 'Inspect the filler valves' },
    { type: 'oee_drop', severity: 'Medium', entity_id: 'LINE-03', description: 'OEE fell from 84% to 76% over three shifts.', action: 'Review changeover times' },
    { type: 'quality_hold', severity: 'Critical', entity_id: 'B26113', description: 'Caffeine assay out of specification for batch B26113.', action: 'Quarantine the batch' },
    { type: 'schedule_slip', severity: 'Medium', entity_id: 'PRD-60416', description: 'Order is running 11 hours behind plan.', action: 'Re-sequence the line' },
  ],
  SCR: [
    { type: 'supplier_risk_up', severity: 'Critical', entity_id: 'V-1003', description: 'NutraChem Ingredients risk score rose from 48 to 77 after a reported plant fire.', action: 'Qualify the second source for taurine premix' },
    { type: 'single_source', severity: 'High', entity_id: 'RM-2004', description: 'Caffeine anhydrous has one approved supplier.', action: 'Start supplier qualification' },
    { type: 'late_deliveries', severity: 'High', entity_id: 'V-1005', description: 'TransGlobal Freight on-time delivery dropped to 81% in the last 30 days.', action: 'Raise at the supplier review' },
    { type: 'market_signal', severity: 'Medium', entity_id: 'SIG-7301', description: 'Port congestion at Rotterdam is adding 4 days to inbound lead times.', action: 'Pull forward packaging orders' },
    { type: 'contract_non_compliance', severity: 'Low', entity_id: 'CTR-2026-047', description: 'Two deliveries below the contracted fill rate.', action: 'Apply the service credit' },
  ],
  C360: [
    { type: 'churn_risk', severity: 'High', entity_id: 'ACC-1008', description: 'Redwood Vending Services order volume is down 28% quarter on quarter.', action: 'Schedule an account review' },
    { type: 'cross_sell', severity: 'Low', entity_id: 'ACC-1003', description: 'BrightMart Retail buys energy drinks only. Similar accounts also stock sports and tea.', action: 'Propose a range extension' },
    { type: 'payment_behaviour', severity: 'Medium', entity_id: 'ACC-1005', description: 'Average days to pay moved from 31 to 44.', action: 'Review payment terms' },
    { type: 'sentiment_drop', severity: 'Medium', entity_id: 'ACC-1010', description: 'Retail review sentiment for Evergreen Supermarkets listings fell to -0.21.', action: 'Check availability and pricing in store' },
  ],
  ESG: [
    { type: 'carbon_target_gap', severity: 'High', entity_id: 'PL04', description: 'Monterrey emissions per case are 13% above the 2026 target.', action: 'Review the boiler efficiency project' },
    { type: 'water_ratio', severity: 'Medium', entity_id: 'PL02', description: 'Leeds water ratio is 2.12 L per case against a target of 2.0.', action: 'Audit the rinse cycle' },
    { type: 'recycled_content', severity: 'Medium', entity_id: 'RM-2001', description: 'Recycled aluminium content is 41% against a 50% target.', action: 'Renegotiate the can specification' },
    { type: 'report_due', severity: 'Low', entity_id: 'ESG-2026-009', description: 'The CDP water submission is due in 18 days.', action: 'Assign an owner' },
  ],
  TCPQ: [
    { type: 'margin_floor_breach', severity: 'High', entity_id: 'Q-2026-0417', description: 'Quote margin of 11.8% is below the 15% floor.', action: 'Send for finance approval' },
    { type: 'quote_expiring', severity: 'Medium', entity_id: 'Q-2026-0409', description: 'Quote validity ends in 3 days with no customer response.', action: 'Follow up with the buyer' },
    { type: 'approval_overdue', severity: 'Medium', entity_id: 'Q-2026-0421', description: 'Regional approval has been pending for 52 hours.', action: 'Escalate to the sales director' },
  ],
  SCPQ: [
    { type: 'bid_deadline', severity: 'Medium', entity_id: 'RFX-2026-031', description: 'Bidding closes in 2 days with three of seven suppliers yet to respond.', action: 'Send a reminder' },
    { type: 'concentration_risk', severity: 'High', entity_id: 'SCN-112', description: 'The lowest-cost scenario awards 86% of volume to one supplier.', action: 'Compare with the split-award scenario' },
    { type: 'award_pending', severity: 'Low', entity_id: 'AWD-2026-018', description: 'An award has waited 4 days for approval.', action: 'Approve or return' },
  ],
};

/** Alerts for a solution. `lower` gives lowercase severities, as the widgets expect. */
export function alertsFor(prefix: string, lower = false): Row[] {
  return (ALERTS[prefix] || ALERTS.O2C).map((a, i) => ({
    ...a,
    severity: lower ? a.severity.toLowerCase() : a.severity,
    message: a.description,
    created_at: ago(40 + i * 170),
    jobId: `JOB-${pad(64 - i)}`,
  }));
}

// ---------------------------------------------------------------------------
// Generated columns for result entities
// ---------------------------------------------------------------------------

const prefixOf = (entity: string) => entity.split('_')[0].toUpperCase();
const isSpend = (entity: string) => /^(PA|SCR)_|^RFx|^Sourcing|^Vendor/.test(entity);

const OFFERINGS = ['Summer Surge display bundle', 'Zero Sugar launch listing', 'Multipack 4x250ml tier', 'Travel retail gift pack', 'Chiller placement programme', 'Convenience end-cap', 'Citrus Surge volume tier', 'Hydrate Sport season pass', 'Focus Tea trial listing', 'Mixed pallet promotion', 'Forecourt meal deal', 'Campus vending bundle'];
const SCENARIOS = ['Lowest landed cost', 'Split award 60/40', 'Incumbent retained', 'Regional dual source', 'Sustainability weighted'];
const SEGMENTS = ['Strategic', 'Enterprise', 'Mid-Market', 'SMB', 'Emerging'];

const approvalChain = () => JSON.stringify([
  { role: 'Account Manager', approver_id: emailOf(PEOPLE[3]), status: 'approved', at: ago(60 * 30).slice(0, 16).replace('T', ' ') },
  { role: 'Regional Sales Manager', approver_id: emailOf(PEOPLE[1]), status: 'approved', at: ago(60 * 9).slice(0, 16).replace('T', ' ') },
  { role: 'Finance Controller', approver_id: emailOf(PEOPLE[4]), status: 'pending', due_at: dayAgo(-1) },
  { role: 'Commercial Director', approver_id: emailOf(PEOPLE[0]), status: 'pending', due_at: dayAgo(-3) },
]);

type Gen = (i: number, entity: string) => unknown;

const SYN: Record<string, Gen> = {
  // dimensions
  region: i => pick(REGIONS, i),
  category: (i, e) => (isSpend(e) ? pick(SPEND_CATEGORIES, i) : pick(PRODUCT_CATEGORIES, i)),
  Category: i => pick(SPEND_CATEGORIES, i),
  plant: i => `${pick(PLANTS, i).id} ${pick(PLANTS, i).name}`,
  plant_id: i => pick(PLANTS, i).id,
  vendor_name: i => pick(VENDORS, i),
  vendor: i => pick(VENDORS, i),
  segment: i => pick(SEGMENTS, i),
  line_id: i => `LINE-0${1 + (i % 6)}`,
  sku: i => pick(PRODUCTS, i).id,
  material: i => pick(PRODUCTS, i).name,
  material_id: i => pick(RAW_MATERIALS, i).id,
  Material_ID: i => pick(RAW_MATERIALS, i).id,
  period: i => `2026-W${46 + (i % 6)}`,
  date: i => dayAgo(29 - i),
  week: i => `W${String(35 + i).padStart(2, '0')}`,
  month: i => pick(['Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov'], i),
  // order-to-cash
  opportunity_id: i => `OPP-${10231 + i}`,
  account_name: i => pick(CUSTOMERS, i),
  order_amount: i => between(`opp-amt-${i}`, 18, 640) * 1000,
  match_status: i => pick(['matched', 'matched', 'quantity_mismatch', 'matched', 'matched', 'price_mismatch', 'matched', 'missing_delivery', 'matched', 'matched', 'missing_invoice', 'matched'], i),
  anomaly_score: i => between(`anom-${i}`, 0.06, 0.97, 2),
  risk_rank: i => i + 1,
  action_id: i => `ACT-${pad(9120 - i)}`,
  action_type: i => pick(['dunning_notice', 'credit_hold', 'dunning_notice', 'dispute_case', 'sla_breach', 'dunning_notice', 'expedited_fulfillment', 'credit_note'], i),
  entity_type: i => pick(['AR_Invoice', 'Account', 'AR_Invoice', 'Opportunity', 'Delivery_Document', 'AR_Invoice', 'Opportunity', 'AR_Invoice'], i),
  entity_id: i => pick([`INV-${88120 + i}`, `ACC-${1001 + (i % 12)}`, `INV-${88120 + i}`, `OPP-${10231 + i}`, `80${pad(31450 + i, 6)}`, `INV-${88120 + i}`, `OPP-${10231 + i}`, `INV-${88120 + i}`], i),
  policy_reference: i => pick(['POL-O2C-004', 'POL-CREDIT-001', 'POL-O2C-004', 'POL-O2C-002', 'POL-FULFIL-001', 'POL-O2C-004', 'POL-FULFIL-001', 'POL-O2C-002'], i),
  details: i => ({ amount: between(`act-a-${i}`, 4, 240) * 1000, note: pick(['Second notice, 31-60 day bucket', 'Open balance above credit limit', 'First notice, 1-30 day bucket', 'Short delivery of 420 cases', 'Delivered 2 days late', 'Final notice, 61-90 day bucket', 'Order expedited for a key account', 'Credit for a price difference'], i) }),
  job_id: i => `JOB-${pad(64 - (i % 9))}`,
  processed_at: i => ago(42 + i * 95),
  dso: i => round(41.5 - i * 0.11 + between(`dso-${i}`, -1.2, 1.2, 1), 1),
  open_ar: i => 5200000 - i * 11500 + between(`oar-${i}`, -60, 60) * 1000,
  cash_collected: i => between(`cash-${i}`, 280, 720) * 1000,
  // demand forecasting
  forecast_qty: i => between(`fq-${i}`, 6, 92) * 1000,
  base_forecast: i => Math.round(between(`fq-${i}`, 6, 92) * 1000 * 0.91),
  actual_qty: i => Math.round(between(`fq-${i}`, 6, 92) * 1000 * between(`fa-${i}`, 0.86, 1.09, 3)),
  promo_lift: i => between(`pl-${i}`, 0, 18, 1),
  override_applied: i => i % 5 === 1,
  total_qty: i => between(`tq-${i}`, 90, 480) * 1000,
  mape: i => round(15.5 - i * 0.09 + between(`mape-${i}`, -0.9, 0.9, 1), 1),
  // inventory
  fill_rate_pct: i => between(`frp-${i}`, 89, 99.4, 1),
  avg_days_of_supply: i => between(`ados-${i}`, 14, 46, 1),
  current_qty: i => between(`cq-${i}`, 1200, 46000),
  days_of_supply: i => between(`dos-${i}`, 4, 71, 1),
  abc_class: i => pick(['A', 'A', 'B', 'A', 'B', 'C', 'B', 'C'], i),
  expiry_risk: i => pick(['Low', 'Low', 'Medium', 'Low', 'High', 'Low', 'Medium'], i),
  // procurement
  total_spend: i => between(`ts-${i}`, 480, 4200) * 1000,
  po_id: i => `45000${pad(1210 + i)}`,
  amount: i => between(`po-amt-${i}`, 6, 380) * 1000,
  maverick_flag: i => i % 6 === 3,
  price_variance: i => between(`pv-${i}`, -2.5, 8.5, 1),
  // production
  avg_oee: i => between(`oee-${i}`, 68, 91, 1),
  pass_rate: i => between(`pr-${i}`, 91, 99.6, 1),
  order_id: i => `PRD-${60410 + i}`,
  planned_qty: i => between(`prd-p-${i}`, 4, 40) * 1000,
  yield_pct: i => between(`yl-${i}`, 90.5, 99.4, 1),
  oee: i => between(`oee2-${i}`, 66, 92, 1),
  // supplier risk
  avg_risk: i => between(`ar-${i}`, 21, 58, 1),
  vendor_count: i => between(`vc-${i}`, 6, 48),
  risk_score: i => between(`v-r-${i}`, 12, 81),
  otd_pct: i => between(`v-otd-${i}`, 78, 99, 1),
  quality_score: i => between(`v-q-${i}`, 82, 99, 1),
  financial_risk: i => pick(['Low', 'Medium', 'Low', 'High', 'Low', 'Medium'], i),
  single_source_materials: i => pick([0, 1, 0, 2, 0, 0, 1], i),
  // customer 360
  avg_clv: i => between(`clv-s-${i}`, 90, 880) * 1000,
  total_revenue: i => between(`trv-${i}`, 1800, 9600) * 1000,
  name: i => pick(CUSTOMERS, i),
  tier: i => pick(['Platinum', 'Gold', 'Gold', 'Silver', 'Silver', 'Bronze'], i),
  clv: i => between(`clv-${i}`, 60, 1400) * 1000,
  churn_score: i => between(`churn-${i}`, 3, 68),
  wallet_share: i => between(`ws-${i}`, 12, 64, 1),
  cross_sell_count: i => pick([3, 1, 0, 2, 4, 1], i),
  ltv_segment: i => pick(['High value', 'Growth', 'High value', 'Maintain', 'At risk', 'Growth'], i),
  // ESG
  carbon_emissions: i => between(`ce-${i}`, 820, 3900),
  avg_recycled_pct: i => between(`arp-${i}`, 22, 68, 1),
  recycled_content_pct: i => between(`rcp-${i}`, 18, 74, 1),
  recyclability_score: i => between(`rs-${i}`, 52, 97),
  carbon_footprint: i => between(`cf-${i}`, 0.12, 2.8, 2),
  // trade CPQ
  Quote_ID: i => `Q-2026-${pad(421 - i)}`,
  Account_ID: i => `ACC-${1001 + (i % 12)}`,
  Total_Net: i => between(`tn-${i}`, 40, 940) * 1000,
  Discount_Pct: i => between(`dp-${i}`, 4, 24, 1),
  Margin_Pct: i => between(`mp-${i}`, 9, 31, 1),
  Validity_Date: i => dayAgo(i * 2 - 21),
  Submitted_At: i => ago(60 * (9 + i * 14)),
  Approval_Chain_JSON: () => approvalChain(),
  Offering_ID: i => `OFF-${pad(201 + i, 3)}`,
  Type: i => pick(['Bundle', 'Listing', 'Volume_Tier', 'Promotion', 'Display'], i),
  Channel_Eligibility: i => pick(['Grocery,Convenience', 'Grocery', 'Convenience,Forecourt', 'Travel_Retail', 'Grocery,Wholesale', 'Vending,Campus'], i),
  Line_ID: i => `QL-${pad(421, 4)}-${pad(i + 1, 2)}`,
  Qty: i => between(`qty-${i}`, 2, 48) * 100,
  Unit_Price: i => between(`up-${i}`, 0.42, 21.5, 2),
  List_Price: i => round(between(`up-${i}`, 0.42, 21.5, 2) * 1.18, 2),
  Unit_Net: i => between(`up-${i}`, 0.42, 21.5, 2),
  Listing_Fee: i => pick([0, 2500, 0, 4000, 1500], i),
  Slotting_Fee: i => pick([1200, 0, 800, 0, 0], i),
  Margin_Pct_Line: i => between(`mpl-${i}`, 8, 29, 1),
  Tier_Max_Discount_Pct: i => pick([15, 18, 12, 20, 15], i),
  Applied_Discount_Pct: i => between(`adp-${i}`, 6, 21, 1),
  Below_Floor: i => between(`mpl-${i}`, 8, 29, 1) < 15,
  // sourcing CPQ
  Event_ID: i => `RFX-2026-${pad(31 - (i % 14), 3)}`,
  Vendor_Quote_ID: i => `VQ-${pad(5120 + i)}`,
  Scenario_ID: i => `SCN-${110 + i}`,
  Modeled_Savings: i => between(`ms-${i}`, 2.1, 11.4, 1),
  Modeled_Risk_Score: i => between(`mrs-${i}`, 18, 62),
  Concentration_Pct: i => between(`conc-${i}`, 38, 96),
  Model_ID: i => `SCM-${pad(301 + i, 3)}`,
  Modeled_Cost: i => between(`mc-${i}`, 0.06, 8.9, 2),
  Confidence: i => between(`conf-${i}`, 0.48, 0.94, 2),
  Generated_At: i => ago(60 * (20 + i * 31)).slice(0, 10),
  RFx_Line_ID: i => `RL-${pad(31, 3)}-${1 + (i % 6)}`,
  Lead_Time_Days: i => between(`lt-${i}`, 5, 42),
  MOQ: i => between(`moq-${i}`, 1, 40) * 500,
  Payment_Terms: i => pick(['Net 45', 'Net 30', 'Net 60', 'Net 90'], i),
  Compliance_Flags: i => pick(['ISO9001,FSSC22000', 'ISO9001', 'ISO9001,FSSC22000,ISO14001', '', 'FSSC22000'], i),
  Award_ID: i => `AWD-2026-${pad(18 + i, 3)}`,
  Approved_At: () => null,
};

const STATUS_BY_ENTITY: Record<string, readonly string[]> = {
  Quote_Header: ['In_Review', 'Approved', 'Draft', 'Won_Converted', 'Approved', 'In_Review', 'Rejected', 'Won_Converted', 'Expired', 'Draft'],
  RFx_Event: ['Bidding', 'Evaluation', 'Published', 'Awarded', 'Bidding', 'Draft', 'Awarded', 'Cancelled'],
  Product_Offering: ['Active', 'Active', 'Active', 'Draft', 'Active', 'Retired'],
  Sourcing_Award: ['Pending_Approval', 'Pending_Approval', 'Approved', 'Pending_Approval'],
  O2C_Action_Log: ['completed', 'completed', 'pending_approval', 'completed', 'completed', 'failed'],
  PQ_Production_Result: ['Completed', 'In process', 'Completed', 'Delayed', 'Completed', 'Released'],
};

/** Result entities that are naturally small. Others get 48 generated rows. */
const ENTITY_ROWS: Record<string, number> = { Product_Offering: 12, Sourcing_Scenario: 5, RFx_Event: 14, Should_Cost_Model: 10, Sourcing_Award: 8, Quote_Line: 8 };

/** Columns returned when a query names none. */
const DEFAULT_COLS: Record<string, string[]> = {
  O2C_Action_Log: ['action_id', 'action_type', 'entity_type', 'entity_id', 'status', 'policy_reference', 'details', 'job_id', 'processed_at'],
  O2C_Order_Result: ['opportunity_id', 'account_name', 'order_amount', 'match_status', 'anomaly_score', 'risk_rank'],
  Quote_Header: ['Quote_ID', 'Account_ID', 'Status', 'Total_Net', 'Discount_Pct', 'Margin_Pct', 'Validity_Date'],
  Quote_Line: ['Line_ID', 'Offering_ID', 'Qty', 'Unit_Price', 'Discount_Pct', 'Margin_Pct_Line'],
  Product_Offering: ['Offering_ID', 'Name', 'Type', 'Channel_Eligibility', 'Status'],
  RFx_Event: ['Event_ID', 'Name', 'Category', 'Status'],
  Vendor_Quote: ['Vendor_Quote_ID', 'Event_ID', 'vendor_name', 'Total_Net'],
  Sourcing_Scenario: ['Scenario_ID', 'Event_ID', 'Name', 'Modeled_Savings', 'Modeled_Risk_Score', 'Concentration_Pct'],
};
/** Columns a widget reads without asking for them. */
const EXTRA_COLS: Record<string, string[]> = {
  Quote_Line: ['List_Price', 'Unit_Net', 'Tier_Max_Discount_Pct', 'Applied_Discount_Pct', 'Below_Floor'],
};

function synValue(col: string, i: number, entity: string): unknown {
  if (col === 'Status' || col === 'status') {
    const list = STATUS_BY_ENTITY[entity];
    return list ? pick(list, i) : pick(['Active', 'Active', 'Pending', 'Active', 'Closed'], i);
  }
  if (col === 'Name') {
    if (entity === 'Sourcing_Scenario') return pick(SCENARIOS, i);
    if (entity === 'RFx_Event') return `${pick(RAW_MATERIALS, i).name} 2027 supply`;
    return pick(OFFERINGS, i);
  }
  const gen = SYN[col];
  if (gen) return gen(i, entity);
  // Fallbacks by naming convention, so an unknown column still looks sensible.
  const lc = col.toLowerCase();
  if (/(_pct|_rate|percent)$/.test(lc)) return between(`${col}-${i}`, 3, 97, 1);
  if (/(_score)$/.test(lc)) return between(`${col}-${i}`, 20, 95);
  if (/(_qty|quantity|_count|count)$/.test(lc)) return between(`${col}-${i}`, 40, 9000);
  if (/(amount|value|spend|revenue|cost|price|total)/.test(lc)) return between(`${col}-${i}`, 5, 900) * 1000;
  if (/(_at|_date|date|time|timestamp)$/.test(lc)) return ago(60 * (3 + i * 11));
  if (/_id$|^id$/.test(lc)) return `${col.replace(/_?id$/i, '').toUpperCase().slice(0, 4) || 'REC'}-${1001 + i}`;
  if (/^is_|^has_|_flag$/.test(lc)) return i % 3 === 0;
  if (/owner|user|approver|created_by/.test(lc)) return pick(PEOPLE, i);
  return pick(CUSTOMERS, i);
}

/** How many distinct values a dimension column has, for summary entities. */
function domainSize(col: string, entity: string): number {
  switch (col) {
    case 'region': return REGIONS.length;
    case 'category': return isSpend(entity) ? (entity.startsWith('SCR') ? 5 : SPEND_CATEGORIES.length) : PRODUCT_CATEGORIES.length;
    case 'plant': case 'plant_id': return PLANTS.length;
    case 'vendor_name': return VENDORS.length;
    case 'segment': return SEGMENTS.length;
    case 'line_id': return 6;
    case 'material_id': return RAW_MATERIALS.length;
    default: return 8;
  }
}

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

export interface SampleQuery {
  entity: string;
  fields?: string[];
  filters?: unknown;
  aggregation?: { function?: string; field?: string } | string | null;
  groupBy?: string[] | string | null;
  orderBy?: string | null;
  limit?: number | null;
}

interface Filter { field: string; operator: string; value: unknown }

function normaliseFilters(filters: unknown): Filter[] {
  if (!filters) return [];
  if (Array.isArray(filters)) {
    return filters.filter(f => f && typeof f === 'object' && 'field' in f).map(f => ({
      field: String((f as any).field), operator: String((f as any).operator || 'eq'), value: (f as any).value,
    }));
  }
  if (typeof filters === 'object') {
    return Object.entries(filters as Record<string, any>).map(([field, v]) =>
      v && typeof v === 'object' && 'operator' in v
        ? { field, operator: String(v.operator), value: v.value }
        : { field, operator: 'eq', value: v });
  }
  return [];
}

function passes(row: Row, f: Filter): boolean {
  const v = row[f.field];
  if (v === undefined) return true; // unknown column: do not empty the result
  const a = Number(v), b = Number(f.value);
  const numeric = !isNaN(a) && !isNaN(b) && v !== null && v !== '';
  switch (f.operator) {
    case 'eq': return String(v) === String(f.value);
    case 'neq': case 'ne': return String(v) !== String(f.value);
    case 'gt': return numeric ? a > b : String(v) > String(f.value);
    case 'gte': return numeric ? a >= b : String(v) >= String(f.value);
    case 'lt': return numeric ? a < b : String(v) < String(f.value);
    case 'lte': return numeric ? a <= b : String(v) <= String(f.value);
    case 'contains': case 'like': return String(v).toLowerCase().includes(String(f.value).replace(/%/g, '').toLowerCase());
    case 'in': return Array.isArray(f.value) ? f.value.map(String).includes(String(v)) : true;
    default: return true;
  }
}

function sortRows(rows: Row[], orderBy: string): Row[] {
  const desc = /\s+desc$/i.test(orderBy);
  const field = orderBy.replace(/\s+(asc|desc)$/i, '').trim();
  if (!rows.length || !(field in rows[0])) return rows;
  return [...rows].sort((x, y) => {
    const a = Number(x[field]), b = Number(y[field]);
    if (!isNaN(a) && !isNaN(b) && x[field] !== null && y[field] !== null) return desc ? b - a : a - b;
    const cmp = String(x[field] ?? '').localeCompare(String(y[field] ?? ''));
    return desc ? -cmp : cmp;
  });
}

/** True for entities the sample knows how to answer with meaningful rows. */
export const isKnownResultEntity = (entity: string) =>
  /^(O2C|DF|IO|PA|PQ|SCR|C360|ESG)_/.test(entity) || entity in DEFAULT_COLS || entity in STATUS_BY_ENTITY
  || ['Vendor_Quote_Line', 'Should_Cost_Model', 'Sourcing_Award'].includes(entity);

/** Unfiltered, unaggregated rows for an entity. */
function baseRows(q: SampleQuery, needed: string[]): Row[] {
  const entity = q.entity;
  const catalogue = entityByName(entity);
  if (catalogue) return entityRows(catalogue, 60);

  if (/_KPI_Snapshot$/.test(entity)) {
    return [{ ...(KPIS[prefixOf(entity)] || {}), snapshot_at: ago(42), job_id: 'JOB-0064' }];
  }
  if (/_Alert$/.test(entity)) return alertsFor(prefixOf(entity), true);

  const cols = [...new Set([...(needed.length ? needed : DEFAULT_COLS[entity] || ['id', 'name', 'status', 'updated_at']), ...(EXTRA_COLS[entity] || [])])];
  const summary = /_Summary$/.test(entity) || entity === 'ESG_Plant_Result';
  const trend = /_(Trend|Daily|Weekly|History)$/.test(entity);
  const count = summary ? domainSize(cols[0], entity) : trend ? (cols[0] === 'date' ? 30 : 12) : ENTITY_ROWS[entity] ?? 48;
  const rows: Row[] = [];
  for (let i = 0; i < count; i++) {
    const row: Row = {};
    for (const col of cols) row[col] = synValue(col, i, entity);
    rows.push(row);
  }
  return rows;
}

/** Run a query. Returns the rows and the row count before the limit was applied. */
export function runQuery(q: SampleQuery): { rows: Row[]; total: number } {
  const fields = (q.fields || []).filter(Boolean);
  const groupBy = (Array.isArray(q.groupBy) ? q.groupBy : q.groupBy ? [q.groupBy] : []).filter(Boolean);
  const agg = typeof q.aggregation === 'string'
    ? { function: q.aggregation, field: undefined as string | undefined }
    : q.aggregation && q.aggregation.function ? { function: q.aggregation.function, field: q.aggregation.field } : null;
  const filters = normaliseFilters(q.filters);
  const orderField = q.orderBy ? q.orderBy.replace(/\s+(asc|desc)$/i, '').trim() : '';

  const needed = [...new Set([
    ...fields, ...groupBy, ...(agg?.field ? [agg.field] : []), ...filters.map(f => f.field),
    ...(orderField && orderField !== 'value' ? [orderField] : []),
  ])];

  let rows = baseRows(q, needed).filter(r => filters.every(f => passes(r, f)));
  // Sort before projecting, so ordering by a column that is not returned works.
  if (!agg && q.orderBy) rows = sortRows(rows, q.orderBy);

  if (agg) {
    const fn = agg.function.toLowerCase();
    const field = agg.field || fields.find(f => !groupBy.includes(f)) || fields[0];
    const reduce = (group: Row[]): number => {
      if (fn === 'count' || !field) return group.length;
      const nums = group.map(r => Number(r[field])).filter(n => !isNaN(n));
      if (!nums.length) return 0;
      if (fn === 'sum') return round(nums.reduce((a, b) => a + b, 0), 2);
      if (fn === 'avg') return round(nums.reduce((a, b) => a + b, 0) / nums.length, 2);
      if (fn === 'min') return Math.min(...nums);
      if (fn === 'max') return Math.max(...nums);
      return group.length;
    };
    if (groupBy.length) {
      const groups = new Map<string, Row[]>();
      for (const r of rows) {
        const key = groupBy.map(g => String(r[g] ?? 'unknown')).join('|');
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key)!.push(r);
      }
      rows = [...groups.values()].map(group => {
        const out: Row = {};
        for (const g of groupBy) out[g] = group[0][g];
        out.value = reduce(group);
        return out;
      });
    } else {
      rows = [{ [field || 'value']: reduce(rows) }];
    }
  } else if (fields.length && rows.length) {
    // Project to the requested columns, in the requested order. Columns the
    // widget reads implicitly (EXTRA_COLS) are kept.
    const extra = EXTRA_COLS[q.entity] || [];
    const present = fields.filter(f => f in rows[0]);
    if (present.length) {
      rows = rows.map(r => {
        const out: Row = {};
        for (const f of [...present, ...extra]) if (f in r) out[f] = r[f];
        return out;
      });
    }
  }

  if (agg && q.orderBy) rows = sortRows(rows, q.orderBy);
  const total = rows.length;
  const limit = typeof q.limit === 'number' && q.limit > 0 ? q.limit : 100;
  return { rows: rows.slice(0, limit), total };
}

/** Preview rows for an entity as the virtual data layer returns them. */
export function previewEntity(entity: string, limit = 10) {
  const e = entityByName(entity);
  if (e && e.fdwMappingStatus !== 'mapped') return { rows: [] as Row[], total: 0 };
  return runQuery({ entity, limit });
}
