export type WidgetType =
  | 'kpi_card'
  | 'line_chart'
  | 'bar_chart'
  | 'pie_chart'
  | 'table'
  | 'alert_list'
  | 'configuration_canvas'
  | 'price_waterfall'
  | 'approval_timeline'
  | 'document_preview'
  | 'bid_matrix'
  | 'scenario_comparison'
  | 'contract_diff'
  | 'should_cost';

export interface WidgetQuery {
  entity: string;
  columns?: string[];
  aggregation?: string;
  groupBy?: string;
  orderBy?: string;
  filters?: Record<string, unknown>;
  limit?: number;
}

export interface DashboardWidget {
  id: string;
  type: WidgetType;
  title: string;
  query: WidgetQuery;
  config: Record<string, unknown>;
  span?: number; // grid column span (1-4), defaults to 1
}

export interface AppDashboardConfig {
  appId: string;
  widgets: DashboardWidget[];
}

const O2C_WIDGETS: DashboardWidget[] = [
  {
    id: 'dso', type: 'kpi_card', title: 'Days Sales Outstanding',
    query: { entity: 'O2C_KPI_Snapshot', columns: ['dso'] },
    config: { unit: 'days', target: 35, direction: 'lower' },
  },
  {
    id: 'match_rate', type: 'kpi_card', title: 'Match Rate',
    query: { entity: 'O2C_KPI_Snapshot', columns: ['match_rate'] },
    config: { unit: '%', target: 95, direction: 'higher' },
  },
  {
    id: 'leakage_rate', type: 'kpi_card', title: 'Revenue Leakage',
    query: { entity: 'O2C_KPI_Snapshot', columns: ['leakage_rate'] },
    config: { unit: '%', target: 5, direction: 'lower' },
  },
  {
    id: 'total_open_ar', type: 'kpi_card', title: 'Open AR',
    query: { entity: 'O2C_KPI_Snapshot', columns: ['total_open_ar'] },
    config: { unit: '$', format: 'currency' },
  },
  {
    id: 'risk_distribution', type: 'pie_chart', title: 'Order Match Status',
    query: { entity: 'O2C_Order_Result', columns: ['match_status'], aggregation: 'count', groupBy: 'match_status', limit: 1000 },
    config: {
      colors: { matched: '#22c55e', quantity_mismatch: '#f59e0b', price_mismatch: '#ef4444', missing_delivery: '#8b5cf6', missing_invoice: '#64748b' },
    },
    span: 2,
  },
  {
    id: 'anomaly_top', type: 'bar_chart', title: 'Top Anomaly Scores',
    query: { entity: 'O2C_Order_Result', columns: ['opportunity_id', 'anomaly_score'], orderBy: 'anomaly_score DESC', limit: 15 },
    config: { xKey: 'opportunity_id', yKey: 'anomaly_score', color: '#ef4444' },
    span: 2,
  },
  {
    id: 'top_risk_orders', type: 'table', title: 'Top Risk Orders',
    query: {
      entity: 'O2C_Order_Result',
      columns: ['opportunity_id', 'account_name', 'order_amount', 'match_status', 'anomaly_score', 'risk_rank'],
      orderBy: 'risk_rank ASC', limit: 20,
    },
    config: {},
    span: 4,
  },
  {
    id: 'alert_list', type: 'alert_list', title: 'Active Alerts',
    query: { entity: 'O2C_Alert' },
    config: {},
    span: 4,
  },
  {
    id: 'action_breakdown', type: 'pie_chart', title: 'Actions by Type',
    query: { entity: 'O2C_Action_Log', columns: ['action_type'], aggregation: 'count', groupBy: 'action_type', limit: 1000 },
    config: {
      colors: { credit_hold: '#ef4444', dispute_case: '#f59e0b', sla_breach: '#8b5cf6', dunning_notice: '#3b82f6', expedited_fulfillment: '#22c55e', credit_note: '#06b6d4' },
    },
    span: 2,
  },
  {
    id: 'recent_actions', type: 'table', title: 'Recent Actions',
    query: {
      entity: 'O2C_Action_Log',
      columns: ['action_type', 'entity_type', 'entity_id', 'status', 'policy_reference'],
      limit: 15,
    },
    config: {},
    span: 2,
  },
];

const DF_WIDGETS: DashboardWidget[] = [
  {
    id: 'mape', type: 'kpi_card', title: 'Forecast Accuracy (MAPE)',
    query: { entity: 'DF_KPI_Snapshot', columns: ['mape'] },
    config: { unit: '%', target: 15, direction: 'lower' },
  },
  {
    id: 'bias', type: 'kpi_card', title: 'Forecast Bias',
    query: { entity: 'DF_KPI_Snapshot', columns: ['bias'] },
    config: { unit: '%', target: 3, direction: 'lower' },
  },
  {
    id: 'stockout_rate', type: 'kpi_card', title: 'Stockout Rate',
    query: { entity: 'DF_KPI_Snapshot', columns: ['stockout_rate_pct'] },
    config: { unit: '%', target: 2, direction: 'lower' },
  },
  {
    id: 'total_forecast', type: 'kpi_card', title: 'Total Forecast Volume',
    query: { entity: 'DF_KPI_Snapshot', columns: ['total_forecast_qty'] },
    config: { unit: 'units', format: 'number' },
  },
  {
    id: 'forecast_by_region', type: 'bar_chart', title: 'Forecast Volume by Region',
    query: { entity: 'DF_Region_Summary', columns: ['region', 'total_qty'], orderBy: 'total_qty DESC', limit: 10 },
    config: { xKey: 'region', yKey: 'total_qty', color: '#8b5cf6' },
    span: 2,
  },
  {
    id: 'forecast_by_category', type: 'pie_chart', title: 'Forecast by Category',
    query: { entity: 'DF_Category_Summary', columns: ['category', 'total_qty'], limit: 10 },
    config: {
      colors: { Carbonated: '#ef4444', Juice: '#f59e0b', Water: '#3b82f6', Energy: '#22c55e', Sports: '#8b5cf6', Tea: '#06b6d4', Snacks: '#ec4899' },
    },
    span: 2,
  },
  {
    id: 'top_forecasts', type: 'table', title: 'Top Forecast SKUs',
    query: {
      entity: 'DF_Forecast_Result',
      columns: ['sku', 'region', 'category', 'period', 'forecast_qty', 'base_forecast', 'promo_lift', 'override_applied'],
      orderBy: 'forecast_qty DESC', limit: 20,
    },
    config: {},
    span: 4,
  },
  {
    id: 'df_alerts', type: 'alert_list', title: 'Forecast Alerts',
    query: { entity: 'DF_Alert' },
    config: {},
    span: 4,
  },
];

const IO_WIDGETS: DashboardWidget[] = [
  { id: 'io_turns', type: 'kpi_card', title: 'Inventory Turns',
    query: { entity: 'IO_KPI_Snapshot', columns: ['turns'] },
    config: { unit: 'x', target: 12, direction: 'higher' } },
  { id: 'io_fill_rate', type: 'kpi_card', title: 'Fill Rate',
    query: { entity: 'IO_KPI_Snapshot', columns: ['fill_rate_pct'] },
    config: { unit: '%', target: 97, direction: 'higher' } },
  { id: 'io_dos', type: 'kpi_card', title: 'Days of Supply',
    query: { entity: 'IO_KPI_Snapshot', columns: ['days_of_supply'] },
    config: { unit: 'days', target: 30, direction: 'lower' } },
  { id: 'io_expiry', type: 'kpi_card', title: 'Expiry Write-off',
    query: { entity: 'IO_KPI_Snapshot', columns: ['expired_write_off_pct'] },
    config: { unit: '%', target: 1, direction: 'lower' } },
  { id: 'io_by_plant', type: 'bar_chart', title: 'Inventory by Plant',
    query: { entity: 'IO_Plant_Summary', columns: ['plant', 'total_qty'], orderBy: 'total_qty DESC', limit: 10 },
    config: { xKey: 'plant', yKey: 'total_qty', color: '#22c55e' }, span: 2 },
  { id: 'io_by_category', type: 'pie_chart', title: 'Inventory by Category',
    query: { entity: 'IO_Category_Summary', columns: ['category', 'total_qty'], limit: 10 },
    config: { colors: { Carbonated: '#ef4444', Juice: '#f59e0b', Water: '#3b82f6', Energy: '#22c55e', Sports: '#8b5cf6', Tea: '#06b6d4', Snacks: '#ec4899' } }, span: 2 },
  { id: 'io_positions', type: 'table', title: 'Top Inventory Positions',
    query: { entity: 'IO_Position_Result', columns: ['sku', 'plant', 'category', 'current_qty', 'days_of_supply', 'abc_class', 'expiry_risk'], orderBy: 'current_qty DESC', limit: 20 },
    config: {}, span: 4 },
  { id: 'io_alerts', type: 'alert_list', title: 'Inventory Alerts',
    query: { entity: 'IO_Alert' }, config: {}, span: 4 },
];

const PA_WIDGETS: DashboardWidget[] = [
  { id: 'pa_spend', type: 'kpi_card', title: 'Total Spend',
    query: { entity: 'PA_KPI_Snapshot', columns: ['total_spend'] },
    config: { unit: '$', format: 'currency' } },
  { id: 'pa_maverick', type: 'kpi_card', title: 'Maverick Spend',
    query: { entity: 'PA_KPI_Snapshot', columns: ['maverick_spend_pct'] },
    config: { unit: '%', target: 5, direction: 'lower' } },
  { id: 'pa_stp', type: 'kpi_card', title: 'Straight-Through Rate',
    query: { entity: 'PA_KPI_Snapshot', columns: ['stp_rate_pct'] },
    config: { unit: '%', target: 80, direction: 'higher' } },
  { id: 'pa_variance', type: 'kpi_card', title: 'Price Variance',
    query: { entity: 'PA_KPI_Snapshot', columns: ['price_variance_pct'] },
    config: { unit: '%', target: 5, direction: 'lower' } },
  { id: 'pa_by_vendor', type: 'bar_chart', title: 'Spend by Vendor',
    query: { entity: 'PA_Vendor_Summary', columns: ['vendor_name', 'total_spend'], orderBy: 'total_spend DESC', limit: 10 },
    config: { xKey: 'vendor_name', yKey: 'total_spend', color: '#f59e0b' }, span: 2 },
  { id: 'pa_by_category', type: 'pie_chart', title: 'Spend by Category',
    query: { entity: 'PA_Category_Summary', columns: ['category', 'total_spend'], limit: 10 },
    config: { colors: { Raw_Materials: '#ef4444', Packaging: '#f59e0b', Logistics: '#3b82f6', Services: '#22c55e', Equipment: '#8b5cf6', Utilities: '#06b6d4' } }, span: 2 },
  { id: 'pa_orders', type: 'table', title: 'Top Purchase Orders',
    query: { entity: 'PA_Spend_Result', columns: ['po_id', 'vendor', 'category', 'amount', 'maverick_flag', 'match_status', 'price_variance'], orderBy: 'amount DESC', limit: 20 },
    config: {}, span: 4 },
  { id: 'pa_alerts', type: 'alert_list', title: 'Procurement Alerts',
    query: { entity: 'PA_Alert' }, config: {}, span: 4 },
];

const PQ_WIDGETS: DashboardWidget[] = [
  { id: 'pq_oee', type: 'kpi_card', title: 'Overall OEE',
    query: { entity: 'PQ_KPI_Snapshot', columns: ['oee_pct'] },
    config: { unit: '%', target: 85, direction: 'higher' } },
  { id: 'pq_yield', type: 'kpi_card', title: 'Yield Rate',
    query: { entity: 'PQ_KPI_Snapshot', columns: ['yield_pct'] },
    config: { unit: '%', target: 98, direction: 'higher' } },
  { id: 'pq_fpr', type: 'kpi_card', title: 'First Pass Rate',
    query: { entity: 'PQ_KPI_Snapshot', columns: ['first_pass_rate_pct'] },
    config: { unit: '%', target: 95, direction: 'higher' } },
  { id: 'pq_adherence', type: 'kpi_card', title: 'Schedule Adherence',
    query: { entity: 'PQ_KPI_Snapshot', columns: ['schedule_adherence_pct'] },
    config: { unit: '%', target: 90, direction: 'higher' } },
  { id: 'pq_by_line', type: 'bar_chart', title: 'OEE by Production Line',
    query: { entity: 'PQ_Line_Summary', columns: ['line_id', 'avg_oee'], orderBy: 'avg_oee DESC', limit: 10 },
    config: { xKey: 'line_id', yKey: 'avg_oee', color: '#3b82f6' }, span: 2 },
  { id: 'pq_by_material', type: 'pie_chart', title: 'Quality by Material',
    query: { entity: 'PQ_Quality_Summary', columns: ['category', 'pass_rate'], limit: 10 },
    config: { colors: { Carbonated: '#ef4444', Juice: '#f59e0b', Water: '#3b82f6', Energy: '#22c55e', Sports: '#8b5cf6', Tea: '#06b6d4', Snacks: '#ec4899' } }, span: 2 },
  { id: 'pq_orders', type: 'table', title: 'Production Orders',
    query: { entity: 'PQ_Production_Result', columns: ['order_id', 'material', 'line_id', 'planned_qty', 'actual_qty', 'yield_pct', 'oee', 'status'], orderBy: 'yield_pct ASC', limit: 20 },
    config: {}, span: 4 },
  { id: 'pq_alerts', type: 'alert_list', title: 'Production Alerts',
    query: { entity: 'PQ_Alert' }, config: {}, span: 4 },
];

const SCR_WIDGETS: DashboardWidget[] = [
  { id: 'scr_risk', type: 'kpi_card', title: 'Avg Risk Score',
    query: { entity: 'SCR_KPI_Snapshot', columns: ['avg_risk_score'] },
    config: { unit: '/100', target: 30, direction: 'lower' } },
  { id: 'scr_otd', type: 'kpi_card', title: 'On-Time Delivery',
    query: { entity: 'SCR_KPI_Snapshot', columns: ['otd_pct'] },
    config: { unit: '%', target: 95, direction: 'higher' } },
  { id: 'scr_single', type: 'kpi_card', title: 'Single-Source Materials',
    query: { entity: 'SCR_KPI_Snapshot', columns: ['single_source_count'] },
    config: { unit: '', target: 0, direction: 'lower' } },
  { id: 'scr_compliance', type: 'kpi_card', title: 'Contract Compliance',
    query: { entity: 'SCR_KPI_Snapshot', columns: ['contract_compliance_pct'] },
    config: { unit: '%', target: 95, direction: 'higher' } },
  { id: 'scr_by_region', type: 'bar_chart', title: 'Risk by Region',
    query: { entity: 'SCR_Region_Summary', columns: ['region', 'avg_risk'], orderBy: 'avg_risk DESC', limit: 10 },
    config: { xKey: 'region', yKey: 'avg_risk', color: '#ef4444' }, span: 2 },
  { id: 'scr_by_category', type: 'pie_chart', title: 'Risk by Category',
    query: { entity: 'SCR_Category_Summary', columns: ['category', 'vendor_count'], limit: 10 },
    config: { colors: { Raw_Materials: '#ef4444', Packaging: '#f59e0b', Logistics: '#3b82f6', Services: '#22c55e', Equipment: '#8b5cf6' } }, span: 2 },
  { id: 'scr_vendors', type: 'table', title: 'Vendor Risk Scores',
    query: { entity: 'SCR_Vendor_Result', columns: ['vendor_name', 'region', 'risk_score', 'otd_pct', 'quality_score', 'financial_risk', 'single_source_materials'], orderBy: 'risk_score DESC', limit: 20 },
    config: {}, span: 4 },
  { id: 'scr_alerts', type: 'alert_list', title: 'Risk Alerts',
    query: { entity: 'SCR_Alert' }, config: {}, span: 4 },
];

const C360_WIDGETS: DashboardWidget[] = [
  { id: 'c360_clv', type: 'kpi_card', title: 'Avg CLV',
    query: { entity: 'C360_KPI_Snapshot', columns: ['avg_clv'] },
    config: { unit: '$', format: 'currency' } },
  { id: 'c360_churn', type: 'kpi_card', title: 'Churn Risk',
    query: { entity: 'C360_KPI_Snapshot', columns: ['churn_risk_pct'] },
    config: { unit: '%', target: 10, direction: 'lower' } },
  { id: 'c360_wallet', type: 'kpi_card', title: 'Wallet Share',
    query: { entity: 'C360_KPI_Snapshot', columns: ['wallet_share_avg'] },
    config: { unit: '%', target: 40, direction: 'higher' } },
  { id: 'c360_xsell', type: 'kpi_card', title: 'Cross-Sell Rate',
    query: { entity: 'C360_KPI_Snapshot', columns: ['cross_sell_rate_pct'] },
    config: { unit: '%', target: 25, direction: 'higher' } },
  { id: 'c360_by_segment', type: 'bar_chart', title: 'CLV by Segment',
    query: { entity: 'C360_Segment_Summary', columns: ['segment', 'avg_clv'], orderBy: 'avg_clv DESC', limit: 10 },
    config: { xKey: 'segment', yKey: 'avg_clv', color: '#8b5cf6' }, span: 2 },
  { id: 'c360_by_region', type: 'pie_chart', title: 'Revenue by Region',
    query: { entity: 'C360_Revenue_Summary', columns: ['region', 'total_revenue'], limit: 10 },
    config: { colors: { North: '#ef4444', South: '#f59e0b', East: '#3b82f6', West: '#22c55e', Central: '#8b5cf6' } }, span: 2 },
  { id: 'c360_customers', type: 'table', title: 'Customer Profiles',
    query: { entity: 'C360_Customer_Result', columns: ['name', 'tier', 'region', 'clv', 'churn_score', 'wallet_share', 'cross_sell_count', 'ltv_segment'], orderBy: 'clv DESC', limit: 20 },
    config: {}, span: 4 },
  { id: 'c360_alerts', type: 'alert_list', title: 'Customer Alerts',
    query: { entity: 'C360_Alert' }, config: {}, span: 4 },
];

const ESG_WIDGETS: DashboardWidget[] = [
  { id: 'esg_carbon', type: 'kpi_card', title: 'Carbon Intensity',
    query: { entity: 'ESG_KPI_Snapshot', columns: ['carbon_intensity'] },
    config: { unit: 'tCO2/unit', target: 0.5, direction: 'lower' } },
  { id: 'esg_water', type: 'kpi_card', title: 'Water Ratio',
    query: { entity: 'ESG_KPI_Snapshot', columns: ['water_ratio'] },
    config: { unit: 'L/unit', target: 2.0, direction: 'lower' } },
  { id: 'esg_recycled', type: 'kpi_card', title: 'Recycled Content',
    query: { entity: 'ESG_KPI_Snapshot', columns: ['recycled_content_pct'] },
    config: { unit: '%', target: 50, direction: 'higher' } },
  { id: 'esg_energy', type: 'kpi_card', title: 'Energy Efficiency',
    query: { entity: 'ESG_KPI_Snapshot', columns: ['energy_efficiency_pct'] },
    config: { unit: '%', target: 90, direction: 'higher' } },
  { id: 'esg_by_plant', type: 'bar_chart', title: 'Emissions by Plant',
    query: { entity: 'ESG_Plant_Result', columns: ['plant_id', 'carbon_emissions'], orderBy: 'carbon_emissions DESC', limit: 10 },
    config: { xKey: 'plant_id', yKey: 'carbon_emissions', color: '#22c55e' }, span: 2 },
  { id: 'esg_by_category', type: 'pie_chart', title: 'Recycled Content by Category',
    query: { entity: 'ESG_Category_Summary', columns: ['category', 'avg_recycled_pct'], limit: 10 },
    config: { colors: { Carbonated: '#ef4444', Juice: '#f59e0b', Water: '#3b82f6', Energy: '#22c55e', Sports: '#8b5cf6', Tea: '#06b6d4', Snacks: '#ec4899' } }, span: 2 },
  { id: 'esg_materials', type: 'table', title: 'Material Sustainability',
    query: { entity: 'ESG_Material_Summary', columns: ['material_id', 'category', 'recycled_content_pct', 'recyclability_score', 'carbon_footprint'], orderBy: 'carbon_footprint DESC', limit: 20 },
    config: {}, span: 4 },
  { id: 'esg_alerts', type: 'alert_list', title: 'ESG Alerts',
    query: { entity: 'ESG_Alert' }, config: {}, span: 4 },
];

const TRADE_CPQ_WIDGETS: DashboardWidget[] = [
  { id: 'tcpq_open_quotes', type: 'kpi_card', title: 'Open Quotes',
    query: { entity: 'Quote_Header', columns: ['Quote_ID'], aggregation: 'count' },
    config: { unit: '', format: 'number' } },
  { id: 'tcpq_avg_margin', type: 'kpi_card', title: 'Avg Margin',
    query: { entity: 'Quote_Header', columns: ['Margin_Pct'], aggregation: 'avg' },
    config: { unit: '%', target: 15, direction: 'higher' } },
  { id: 'tcpq_avg_discount', type: 'kpi_card', title: 'Avg Discount',
    query: { entity: 'Quote_Header', columns: ['Discount_Pct'], aggregation: 'avg' },
    config: { unit: '%', target: 15, direction: 'lower' } },
  { id: 'tcpq_total_net', type: 'kpi_card', title: 'Quote Pipeline Value',
    query: { entity: 'Quote_Header', columns: ['Total_Net'], aggregation: 'sum' },
    config: { unit: '$', format: 'currency' } },
  { id: 'tcpq_status_pie', type: 'pie_chart', title: 'Quotes by Stage',
    query: { entity: 'Quote_Header', columns: ['Status'], aggregation: 'count', groupBy: 'Status', limit: 20 },
    config: { colors: { Draft: '#94a3b8', In_Review: '#f59e0b', Approved: '#3b82f6', Won_Converted: '#22c55e', Rejected: '#ef4444', Expired: '#64748b' } },
    span: 2 },
  { id: 'tcpq_offering_types', type: 'bar_chart', title: 'Offering Mix by Type',
    query: { entity: 'Product_Offering', columns: ['Type'], aggregation: 'count', groupBy: 'Type', orderBy: 'value DESC', limit: 10 },
    config: { xKey: 'Type', yKey: 'value', color: '#d946ef' },
    span: 2 },
  { id: 'tcpq_offering_canvas', type: 'configuration_canvas', title: 'Active Offerings Canvas',
    query: { entity: 'Product_Offering', columns: ['Offering_ID', 'Name', 'Type', 'Channel_Eligibility', 'Status'],
             filters: { Status: { operator: 'eq', value: 'Active' } }, orderBy: 'Name ASC', limit: 18 },
    config: {}, span: 2 },
  { id: 'tcpq_pricing_waterfall', type: 'price_waterfall', title: 'Pricing Waterfall (latest quote)',
    query: { entity: 'Quote_Line',
             columns: ['Line_ID', 'Offering_ID', 'Qty', 'Unit_Price', 'Discount_Pct', 'Listing_Fee', 'Slotting_Fee', 'Margin_Pct_Line'],
             orderBy: 'Line_ID ASC', limit: 8 },
    config: {}, span: 2 },
  { id: 'tcpq_approval_timeline', type: 'approval_timeline', title: 'Approval Timeline (latest quote)',
    query: { entity: 'Quote_Header', columns: ['Quote_ID', 'Status', 'Approval_Chain_JSON'],
             filters: { Status: { operator: 'eq', value: 'In_Review' } }, orderBy: 'Submitted_At DESC', limit: 1 },
    config: {}, span: 2 },
  { id: 'tcpq_top_quotes', type: 'table', title: 'Highest Value Quotes',
    query: { entity: 'Quote_Header', columns: ['Quote_ID', 'Account_ID', 'Status', 'Total_Net', 'Discount_Pct', 'Margin_Pct', 'Validity_Date'], orderBy: 'Total_Net DESC', limit: 20 },
    config: {}, span: 4 },
  { id: 'tcpq_margin_breaches', type: 'table', title: 'Margin Floor Breaches',
    query: { entity: 'Quote_Header', columns: ['Quote_ID', 'Account_ID', 'Margin_Pct', 'Discount_Pct', 'Total_Net'],
             filters: { Margin_Pct: { operator: 'lt', value: 15 } }, orderBy: 'Margin_Pct ASC', limit: 20 },
    config: {}, span: 4 },
];

const SOURCING_CPQ_WIDGETS: DashboardWidget[] = [
  { id: 'scpq_open_rfx', type: 'kpi_card', title: 'Open RFx Events',
    query: { entity: 'RFx_Event', columns: ['Event_ID'], aggregation: 'count' },
    config: { unit: '', format: 'number' } },
  { id: 'scpq_bids_in', type: 'kpi_card', title: 'Vendor Bids Submitted',
    query: { entity: 'Vendor_Quote', columns: ['Vendor_Quote_ID'], aggregation: 'count' },
    config: { unit: '', format: 'number' } },
  { id: 'scpq_avg_savings', type: 'kpi_card', title: 'Avg Modeled Savings',
    query: { entity: 'Sourcing_Scenario', columns: ['Modeled_Savings'], aggregation: 'avg' },
    config: { unit: '%', target: 5, direction: 'higher' } },
  { id: 'scpq_avg_concentration', type: 'kpi_card', title: 'Avg Concentration',
    query: { entity: 'Sourcing_Scenario', columns: ['Concentration_Pct'], aggregation: 'avg' },
    config: { unit: '%', target: 60, direction: 'lower' } },
  { id: 'scpq_rfx_status', type: 'pie_chart', title: 'RFx by Status',
    query: { entity: 'RFx_Event', columns: ['Status'], aggregation: 'count', groupBy: 'Status', limit: 20 },
    config: { colors: { Draft: '#94a3b8', Published: '#3b82f6', Bidding: '#f59e0b', Evaluation: '#a855f7', Awarded: '#22c55e', Cancelled: '#ef4444' } },
    span: 2 },
  { id: 'scpq_category_mix', type: 'bar_chart', title: 'RFx Volume by Category',
    query: { entity: 'RFx_Event', columns: ['Category'], aggregation: 'count', groupBy: 'Category', orderBy: 'value DESC', limit: 10 },
    config: { xKey: 'Category', yKey: 'value', color: '#6366f1' },
    span: 2 },
  { id: 'scpq_should_cost', type: 'should_cost', title: 'Should-Cost Models',
    query: { entity: 'Should_Cost_Model', columns: ['Model_ID', 'Material_ID', 'Modeled_Cost', 'Confidence', 'Generated_At'], orderBy: 'Generated_At DESC', limit: 10 },
    config: {}, span: 2 },
  { id: 'scpq_scenario_compare', type: 'scenario_comparison', title: 'Scenario Comparison',
    query: { entity: 'Sourcing_Scenario', columns: ['Scenario_ID', 'Event_ID', 'Name', 'Modeled_Savings', 'Modeled_Risk_Score', 'Concentration_Pct'], orderBy: 'Modeled_Savings DESC', limit: 3 },
    config: {}, span: 2 },
  { id: 'scpq_bid_matrix', type: 'bid_matrix', title: 'Bid Matrix',
    query: { entity: 'Vendor_Quote_Line', columns: ['Vendor_Quote_ID', 'RFx_Line_ID', 'Unit_Price', 'Lead_Time_Days', 'MOQ', 'Payment_Terms', 'Compliance_Flags'], orderBy: 'Unit_Price ASC', limit: 30 },
    config: {}, span: 4 },
  { id: 'scpq_scenarios', type: 'table', title: 'Sourcing Scenarios',
    query: { entity: 'Sourcing_Scenario', columns: ['Scenario_ID', 'Event_ID', 'Name', 'Modeled_Savings', 'Modeled_Risk_Score', 'Concentration_Pct'], orderBy: 'Modeled_Savings DESC', limit: 20 },
    config: {}, span: 4 },
  { id: 'scpq_pending_awards', type: 'table', title: 'Pending Awards',
    query: { entity: 'Sourcing_Award', columns: ['Award_ID', 'Event_ID', 'Scenario_ID', 'Status', 'Approved_At'],
             filters: { Status: { operator: 'eq', value: 'Pending_Approval' } }, orderBy: 'Award_ID ASC', limit: 20 },
    config: {}, span: 4 },
];

const PLACEHOLDER_WIDGETS: DashboardWidget[] = [
  {
    id: 'placeholder_kpi_1', type: 'kpi_card', title: 'Primary KPI',
    query: { entity: '', columns: [] },
    config: { placeholder: true },
  },
  {
    id: 'placeholder_kpi_2', type: 'kpi_card', title: 'Secondary KPI',
    query: { entity: '', columns: [] },
    config: { placeholder: true },
  },
  {
    id: 'placeholder_kpi_3', type: 'kpi_card', title: 'Target KPI',
    query: { entity: '', columns: [] },
    config: { placeholder: true },
  },
];

export const DASHBOARD_CONFIGS: AppDashboardConfig[] = [
  { appId: 'order-to-cash', widgets: O2C_WIDGETS },
  { appId: 'demand-forecasting', widgets: DF_WIDGETS },
  { appId: 'inventory-optimization', widgets: IO_WIDGETS },
  { appId: 'procurement-analytics', widgets: PA_WIDGETS },
  { appId: 'production-quality', widgets: PQ_WIDGETS },
  { appId: 'supply-chain-risk', widgets: SCR_WIDGETS },
  { appId: 'customer-360', widgets: C360_WIDGETS },
  { appId: 'esg-sustainability', widgets: ESG_WIDGETS },
  { appId: 'trade-cpq', widgets: TRADE_CPQ_WIDGETS },
  { appId: 'sourcing-cpq', widgets: SOURCING_CPQ_WIDGETS },
];

export function getWidgetsForApp(appId: string): DashboardWidget[] {
  const cfg = DASHBOARD_CONFIGS.find(c => c.appId === appId);
  return cfg?.widgets ?? PLACEHOLDER_WIDGETS;
}
