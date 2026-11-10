import {
  ShoppingCart, TrendingUp, Package, Factory, FileText, Shield, Users, Leaf,
  LayoutDashboard, BarChart3, Bell, Workflow, MessageSquare, Activity,
  Receipt, ClipboardList,
  type LucideIcon,
} from 'lucide-react';

export interface AppTab {
  id: string;
  name: string;
}

export interface AppSection {
  id: string;
  name: string;
  icon: LucideIcon;
  tabs?: AppTab[];
}

export interface AppConfig {
  id: string;
  name: string;
  shortName: string;
  icon: LucideIcon;
  color: string;
  description: string;
  sections: AppSection[];
  journeyStageId?: string;
  useCase: string;
  entities: string[];
  kpis: { label: string; target: string }[];
  status: 'available' | 'coming_soon';
}

const COMMON_SECTIONS: AppSection[] = [
  { id: 'insights', name: 'Business Insights', icon: BarChart3 },
  { id: 'analytics', name: 'Process Analytics', icon: Activity },
  { id: 'reports', name: 'Reports', icon: FileText },
];

export const APP_REGISTRY: AppConfig[] = [
  {
    id: 'order-to-cash', name: 'Order-to-Cash Monitor', shortName: 'O2C',
    icon: ShoppingCart, color: 'from-primary to-primary',
    description: 'End-to-end visibility and anomaly detection across the order-to-cash lifecycle',
    sections: [
      { id: 'insights', name: 'Business Insights', icon: BarChart3 },
      { id: 'analytics', name: 'Process Analytics', icon: Activity },
      { id: 'workflows', name: 'Workflow Actions', icon: Workflow },
      { id: 'reports', name: 'Reports', icon: FileText },
    ],
    journeyStageId: 'order_to_cash', useCase: 'order-to-cash',
    entities: ['Opportunity', 'Opportunity_Line_Item', 'Account', 'Delivery_Document', 'AR_Invoice', 'AR_Payment', 'AR_Credit_Note'],
    kpis: [{ label: 'DSO', target: '< 35 days' }, { label: 'Match Rate', target: '> 95%' }, { label: 'Leakage', target: '< 0.5%' }, { label: 'On-Time Payment', target: '> 88%' }],
    status: 'available',
  },
  {
    id: 'demand-forecasting', name: 'Demand Forecasting Engine', shortName: 'Forecast',
    icon: TrendingUp, color: 'from-primary to-primary',
    description: 'AI-driven demand prediction across SKUs, regions, and channels',
    sections: [
      { id: 'insights', name: 'Forecast Insights', icon: BarChart3 },
      { id: 'analytics', name: 'Accuracy Analytics', icon: Activity },
      { id: 'workflows', name: 'Forecast Workflows', icon: Workflow },
      { id: 'reports', name: 'Reports', icon: FileText },
    ],
    journeyStageId: 'demand_forecasting', useCase: 'demand-forecasting',
    entities: ['Material_Master', 'Opportunity', 'Opportunity_Line_Item', 'Inventory_Position', 'Forecast_Override', 'Campaign', 'Market_Signal', 'Account', 'Material_Plant'],
    kpis: [{ label: 'MAPE', target: '< 15%' }, { label: 'Stockout Rate', target: '< 2%' }, { label: 'Bias', target: '± 3%' }, { label: 'Promo Lift Accuracy', target: '± 10%' }],
    status: 'available',
  },
  {
    id: 'inventory-optimization', name: 'Inventory Optimization', shortName: 'Inventory',
    icon: Package, color: 'from-success to-success',
    description: 'Multi-echelon inventory optimization and distribution intelligence',
    sections: COMMON_SECTIONS, journeyStageId: 'inventory_optimization', useCase: 'inventory-optimization',
    entities: ['Inventory_Position', 'Batch_Master', 'Plant_Master', 'Storage_Location', 'Material_Master', 'Warehouse_Transfer'],
    kpis: [{ label: 'Turns', target: '> 12x' }, { label: 'Fill Rate', target: '> 97%' }, { label: 'Expiry', target: '< 1%' }],
    status: 'available',
  },
  {
    id: 'procurement-analytics', name: 'Procurement & Spend Analytics', shortName: 'Procurement',
    icon: FileText, color: 'from-warning to-warning',
    description: 'Spend visibility, maverick detection, and intelligent invoice processing',
    sections: COMMON_SECTIONS, journeyStageId: 'procurement_analytics', useCase: 'procurement-analytics',
    entities: ['Purchase_Order', 'Goods_Receipt', 'AP_Invoice', 'AP_Payment', 'Vendor_Master', 'Contract_Document', 'Invoice_Upload'],
    kpis: [{ label: 'Maverick', target: '< 5%' }, { label: 'STP Rate', target: '> 80%' }, { label: 'Price Variance', target: '< 3%' }],
    status: 'available',
  },
  {
    id: 'production-quality', name: 'Production & Quality Copilot', shortName: 'Production',
    icon: Factory, color: 'from-destructive to-destructive',
    description: 'AI-assisted production scheduling, yield optimization, and quality detection',
    sections: COMMON_SECTIONS, journeyStageId: 'production_quality', useCase: 'production-quality',
    entities: ['Production_Order', 'Production_Line', 'Bill_of_Materials', 'Quality_Inspection_Lot', 'Quality_Test_Result', 'Batch_Master'],
    kpis: [{ label: 'OEE', target: '> 85%' }, { label: 'Yield', target: '> 98%' }, { label: 'First Pass', target: '> 95%' }],
    status: 'available',
  },
  {
    id: 'supply-chain-risk', name: 'Supply Chain Risk Radar', shortName: 'Risk',
    icon: Shield, color: 'from-primary to-primary',
    description: 'Real-time supplier risk scoring and early warning for disruptions',
    sections: COMMON_SECTIONS, journeyStageId: 'supply_chain_risk', useCase: 'supply-chain-risk',
    entities: ['Vendor_Master', 'Purchase_Order', 'Source_List', 'Market_Signal', 'Contract_Document', 'Goods_Receipt'],
    kpis: [{ label: 'Risk Score', target: '< 30' }, { label: 'OTD', target: '> 95%' }, { label: 'Early Warning', target: '> 7d' }],
    status: 'available',
  },
  {
    id: 'customer-360', name: 'Customer 360 & Revenue Growth', shortName: 'Customer',
    icon: Users, color: 'from-primary to-primary',
    description: 'Unified customer profiles with churn prediction and cross-sell recommendations',
    sections: COMMON_SECTIONS, journeyStageId: 'customer_360', useCase: 'customer-360',
    entities: ['Account', 'Contact', 'Opportunity', 'AR_Customer', 'AR_Invoice', 'Brand_Sentiment'],
    kpis: [{ label: 'Churn', target: '< 5%' }, { label: 'Wallet Share', target: '> 60%' }, { label: 'CLV', target: '+15%' }],
    status: 'available',
  },
  {
    id: 'esg-sustainability', name: 'ESG & Sustainability Tracker', shortName: 'ESG',
    icon: Leaf, color: 'from-primary to-success',
    description: 'Carbon footprint tracking, water monitoring, and ESG compliance reporting',
    sections: COMMON_SECTIONS, journeyStageId: 'esg_sustainability', useCase: 'esg-sustainability',
    entities: ['Sustainability_Report', 'Material_Master', 'Plant_Master', 'Brand_Sentiment'],
    kpis: [{ label: 'CO₂', target: '-30%' }, { label: 'Water Ratio', target: '< 2L' }, { label: 'Recycled', target: '> 80%' }],
    status: 'available',
  },
  {
    id: 'trade-cpq', name: 'Trade CPQ', shortName: 'Trade CPQ',
    icon: Receipt, color: 'from-primary to-primary',
    description: 'AI-first sell-side CPQ for trade quotes — configure offerings, price with channel/tier waterfalls, and convert to orders',
    sections: [
      { id: 'insights', name: 'Quote Pipeline', icon: BarChart3 },
      { id: 'analytics', name: 'Pricing & Margin', icon: Activity },
      { id: 'workflows', name: 'CPQ Workflows', icon: Workflow },
      { id: 'reports', name: 'Proposals & Alerts', icon: FileText },
    ],
    journeyStageId: 'trade_cpq', useCase: 'trade-cpq',
    entities: [
      'Quote_Header', 'Quote_Line', 'Quote_Promotion', 'Product_Offering',
      'Offering_Component', 'Price_Book', 'Price_Book_Entry',
      'Serviceability_Footprint', 'Configuration_Rule',
      'Account', 'Campaign', 'Material_Master',
    ],
    kpis: [
      { label: 'Quote Cycle Time', target: '< 1 day' },
      { label: 'Auto-Approval', target: '> 70%' },
      { label: 'Discount Leakage', target: '< 1%' },
      { label: 'Margin Floor Breach', target: '< 5%' },
    ],
    status: 'available',
  },
  {
    id: 'sourcing-cpq', name: 'Sourcing CPQ', shortName: 'Sourcing CPQ',
    icon: ClipboardList, color: 'from-primary to-primary',
    description: 'AI-first buy-side CPQ for sourcing — launch RFx, score bids vs should-cost, run award scenarios, and draft contracts',
    sections: [
      { id: 'insights', name: 'RFx Pipeline', icon: BarChart3 },
      { id: 'analytics', name: 'Bid Matrix & Scenarios', icon: Activity },
      { id: 'workflows', name: 'Sourcing Workflows', icon: Workflow },
      { id: 'reports', name: 'Awards & Contracts', icon: FileText },
    ],
    journeyStageId: 'sourcing_cpq', useCase: 'sourcing-cpq',
    entities: [
      'RFx_Event', 'RFx_Line', 'RFx_Invitation',
      'Vendor_Quote', 'Vendor_Quote_Line',
      'Should_Cost_Model', 'Sourcing_Scenario', 'Sourcing_Award',
      'Vendor_Master', 'Source_List', 'Material_Master',
      'Commodity_Price', 'Contract_Document',
    ],
    kpis: [
      { label: 'RFx Cycle Time', target: '< 10 days' },
      { label: 'Savings vs Should-Cost', target: '> 5%' },
      { label: 'Single-Source ABC-A', target: '< 2%' },
      { label: 'Time to Contract', target: '< 3 days' },
    ],
    status: 'available',
  },
];

export function getAppConfig(appId: string): AppConfig | undefined {
  return APP_REGISTRY.find(a => a.id === appId);
}
