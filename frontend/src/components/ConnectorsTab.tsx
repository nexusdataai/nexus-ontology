import { useState } from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ArrowLeft, Globe, Building, Code2, Brain, Timer, Plug, HardDrive } from 'lucide-react';
import GoogleDriveConnectorSettings from './settings/GoogleDriveConnectorSettings';
import { ConnectorDetailView } from './connectors/ConnectorDetailView';
import type { TargetSystem } from '@/services/connectorApiService';
import SalesforceConnector from './SalesforceConnector';
import Office365Connector from './Office365Connector';
import KnowledgeBase from './KnowledgeBase';
import BSSStudioConnector from './BSSStudioConnector';

// Connectors that ship a full configuration UI (carried over from the legacy
// ToolsCatalogue). Selecting these tiles renders the rich component instead
// of the generic ConnectorDetailView. Components are no-prop and the Back
// button is rendered by ConnectorsTab around them.
const RICH_COMPONENTS: Record<string, React.ComponentType> = {
  'salesforce': SalesforceConnector,
  'office365': Office365Connector,
  'knowledge-base': KnowledgeBase,
  'bss-studio': BSSStudioConnector,
};

interface Connector {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  status: 'Available' | 'Coming Soon';
  inputs: string[];
  outputs: string[];
  color: string;
  targetSystem?: TargetSystem;
}

const CONNECTORS: Connector[] = [
  {
    id: 'salesforce', name: 'Salesforce Connector',
    description: 'Connect with Salesforce CRM to sync customer data and call records.',
    icon: <Building className="h-6 w-6 text-white" />, status: 'Available', color: 'from-blue-600 to-cyan-600',
    inputs: ['OAuth Configuration'], outputs: ['CRM Data', 'Customer Records', 'Activity Analytics'],
    targetSystem: 'sfdc',
  },
  {
    id: 'office365', name: 'Office 365 Connector',
    description: 'Integrate with Microsoft Office 365 and Teams for communication analytics.',
    icon: <Code2 className="h-6 w-6 text-white" />, status: 'Available', color: 'from-orange-500 to-red-500',
    inputs: ['Azure AD Registration'], outputs: ['Teams Data', 'Email Analytics', 'Calendar Insights'],
  },
  {
    id: 'knowledge-base', name: 'KnowledgeBase',
    description: 'Upload documents and content for vectordb indexing with AI-powered query testing and knowledge-based suggestions.',
    icon: <Brain className="h-6 w-6 text-white" />, status: 'Available', color: 'from-emerald-500 to-teal-500',
    inputs: ['Documents', 'Content Files', 'Indexing Config'], outputs: ['Vector Index', 'Query Results', 'AI Suggestions'],
  },
  {
    id: 'bss-studio', name: 'Langflow Connector',
    description: 'Set schedules for BSS Flow jobs like cron jobs, test invocations, and monitor executions with diagnostic messages.',
    icon: <Timer className="h-6 w-6 text-white" />, status: 'Available', color: 'from-pink-500 to-rose-500',
    inputs: ['Lambda Configuration', 'Schedule Settings', 'API Endpoints'], outputs: ['Job Schedules', 'Execution Logs', 'Diagnostic Reports'],
  },
  {
    id: 'oracle-erp', name: 'Oracle ERP Connector',
    description: 'Connect to Oracle ERP for financial data, AP/AR, general ledger, and purchase orders.',
    icon: <Plug className="h-6 w-6 text-white" />, status: 'Available', color: 'from-amber-500 to-orange-500',
    inputs: ['Connection Config', 'Schema Mapping'], outputs: ['Financial Data', 'AP/AR Records', 'GL Entries'],
    targetSystem: 'oracle',
  },
  {
    id: 'sap', name: 'SAP S/4HANA Connector',
    description: 'Connect to SAP for supply chain data, materials, inventory, production, and logistics.',
    icon: <Plug className="h-6 w-6 text-white" />, status: 'Available', color: 'from-green-500 to-emerald-500',
    inputs: ['RFC/OData Config', 'Schema Mapping'], outputs: ['Material Data', 'Inventory', 'Production Orders'],
    targetSystem: 'sap',
  },
  {
    id: 'google-drive', name: 'Google Drive Connector',
    description: 'Connect to Google Drive for contract documents, sustainability reports, and file extraction with OCR.',
    icon: <HardDrive className="h-6 w-6 text-white" />, status: 'Available', color: 'from-red-500 to-yellow-500',
    inputs: ['OAuth2 Credentials', 'Folder IDs', 'File Filters'],
    outputs: ['Contract Documents', 'Sustainability Reports', 'Extracted Data'],
  },
  {
    id: 'external', name: 'External Systems',
    description: 'Cross-system actions: alerts, audit events, dunning notices, and outcome writebacks dispatched to internal systems.',
    icon: <Globe className="h-6 w-6 text-white" />, status: 'Available', color: 'from-slate-500 to-zinc-600',
    inputs: ['Webhook Endpoints', 'Notification Channels'],
    outputs: ['Alerts', 'Audit Events', 'Dunning Notices', 'Outcomes'],
    targetSystem: 'external',
  },
];

export function ConnectorsTab() {
  const [activeConnector, setActiveConnector] = useState<string | null>(null);

  if (activeConnector === 'google-drive') {
    return <GoogleDriveConnectorSettings onBack={() => setActiveConnector(null)} />;
  }

  if (activeConnector && RICH_COMPONENTS[activeConnector]) {
    const RichComponent = RICH_COMPONENTS[activeConnector];
    return (
      <div className="space-y-4">
        <div className="px-6 pt-6">
          <Button variant="outline" size="sm" onClick={() => setActiveConnector(null)} className="text-xs">
            <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Back to Connectors
          </Button>
        </div>
        <RichComponent />
      </div>
    );
  }

  if (activeConnector) {
    const c = CONNECTORS.find((x) => x.id === activeConnector);
    if (c) {
      return (
        <ConnectorDetailView
          connectorId={c.id}
          connectorName={c.name}
          description={c.description}
          color={c.color}
          icon={c.icon}
          targetSystem={c.targetSystem}
          onBack={() => setActiveConnector(null)}
        />
      );
    }
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Plug className="h-6 w-6 text-purple-400" />
          Connectors
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Integration connectors for enterprise data sources and services
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {CONNECTORS.map(c => (
          <Card key={c.id} className="overflow-hidden hover:border-primary/50 transition-all">
            <div className={`h-1.5 bg-gradient-to-r ${c.color}`} />
            <CardContent className="pt-4 pb-4">
              <div className="flex items-start justify-between mb-3">
                <div className={`p-2.5 rounded-xl bg-gradient-to-br ${c.color}`}>
                  {c.icon}
                </div>
                <div className="flex gap-1">
                  <Badge className={c.status === 'Available' ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'}>
                    {c.status}
                  </Badge>
                </div>
              </div>

              <h3 className="font-semibold text-sm">{c.name}</h3>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{c.description}</p>

              <div className="mt-3 space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-foreground w-12">Inputs</span>
                  <div className="flex flex-wrap gap-1">
                    {c.inputs.map(inp => <Badge key={inp} variant="outline" className="text-[9px]">{inp}</Badge>)}
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-foreground w-12">Outputs</span>
                  <div className="flex flex-wrap gap-1">
                    {c.outputs.map(out => <Badge key={out} variant="outline" className="text-[9px]">{out}</Badge>)}
                  </div>
                </div>
              </div>

              <Button size="sm" className="w-full mt-3" onClick={() => setActiveConnector(c.id)}>
                <Plug className="h-3.5 w-3.5 mr-1" /> Configure
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
