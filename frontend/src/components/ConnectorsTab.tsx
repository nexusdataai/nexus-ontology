import { useState } from 'react';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { Chips, SearchInput, StatusPill, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { SystemLogo } from '@/components/ds/SystemLogo';
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
// link is rendered by ConnectorsTab around them.
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
  status: 'Available' | 'Coming Soon';
  inputs: string[];
  outputs: string[];
  /** Legacy gradient name. Not drawn any more; the brand logo identifies the system. */
  color?: string;
  targetSystem?: TargetSystem;
}

const CONNECTORS: Connector[] = [
  {
    id: 'salesforce', name: 'Salesforce Connector',
    description: 'Connect with Salesforce CRM to sync customer data and call records.',
    status: 'Available',
    inputs: ['OAuth Configuration'], outputs: ['CRM Data', 'Customer Records', 'Activity Analytics'],
    targetSystem: 'sfdc',
  },
  {
    id: 'office365', name: 'Office 365 Connector',
    description: 'Integrate with Microsoft Office 365 and Teams for communication analytics.',
    status: 'Available',
    inputs: ['Azure AD Registration'], outputs: ['Teams Data', 'Email Analytics', 'Calendar Insights'],
  },
  {
    id: 'knowledge-base', name: 'KnowledgeBase',
    description: 'Upload documents and content for vectordb indexing with AI-powered query testing and knowledge-based suggestions.',
    status: 'Available',
    inputs: ['Documents', 'Content Files', 'Indexing Config'], outputs: ['Vector Index', 'Query Results', 'AI Suggestions'],
  },
  {
    id: 'bss-studio', name: 'Langflow Connector',
    description: 'Set schedules for BSS Flow jobs like cron jobs, test invocations, and monitor executions with diagnostic messages.',
    status: 'Available',
    inputs: ['Lambda Configuration', 'Schedule Settings', 'API Endpoints'], outputs: ['Job Schedules', 'Execution Logs', 'Diagnostic Reports'],
  },
  {
    id: 'oracle-erp', name: 'Oracle ERP Connector',
    description: 'Connect to Oracle ERP for financial data, AP/AR, general ledger, and purchase orders.',
    status: 'Available',
    inputs: ['Connection Config', 'Schema Mapping'], outputs: ['Financial Data', 'AP/AR Records', 'GL Entries'],
    targetSystem: 'oracle',
  },
  {
    id: 'sap', name: 'SAP S/4HANA Connector',
    description: 'Connect to SAP for supply chain data, materials, inventory, production, and logistics.',
    status: 'Available',
    inputs: ['RFC/OData Config', 'Schema Mapping'], outputs: ['Material Data', 'Inventory', 'Production Orders'],
    targetSystem: 'sap',
  },
  {
    id: 'google-drive', name: 'Google Drive Connector',
    description: 'Connect to Google Drive for contract documents, sustainability reports, and file extraction with OCR.',
    status: 'Available',
    inputs: ['OAuth2 Credentials', 'Folder IDs', 'File Filters'],
    outputs: ['Contract Documents', 'Sustainability Reports', 'Extracted Data'],
  },
  {
    id: 'external', name: 'External Systems',
    description: 'Cross-system actions: alerts, audit events, dunning notices, and outcome writebacks dispatched to internal systems.',
    status: 'Available',
    inputs: ['Webhook Endpoints', 'Notification Channels'],
    outputs: ['Alerts', 'Audit Events', 'Dunning Notices', 'Outcomes'],
    targetSystem: 'external',
  },
];

type Category = 'business' | 'productivity' | 'knowledge';
type CategoryFilter = 'all' | Category;

const CATEGORY_LABEL: Record<Category, string> = {
  business: 'Business system',
  productivity: 'Productivity',
  knowledge: 'Knowledge and automation',
};

/** Presentation only: category and vendor are derived from the connector id. */
const CATEGORY_OF: Record<string, Category> = {
  'salesforce': 'business', 'oracle-erp': 'business', 'sap': 'business',
  'office365': 'productivity', 'google-drive': 'productivity',
  'knowledge-base': 'knowledge', 'bss-studio': 'knowledge', 'external': 'knowledge',
};
const VENDOR_OF: Record<string, string> = {
  'salesforce': 'Salesforce', 'oracle-erp': 'Oracle', 'sap': 'SAP',
  'office365': 'Microsoft', 'google-drive': 'Google',
  'knowledge-base': 'Nexus AI', 'bss-studio': 'Langflow', 'external': 'Webhooks',
};
const categoryOf = (id: string): Category => CATEGORY_OF[id] || 'knowledge';

/** "CRM Data" → "CRM data": sentence case that keeps acronyms. */
const quiet = (items: string[]): string =>
  items
    .map(s => s.split(' ').map((w, wi) => (wi === 0 || /[A-Z].*[A-Z]|\d|\//.test(w) ? w : w.toLowerCase())).join(' '))
    .join(', ');

export function ConnectorsTab() {
  const [activeConnector, setActiveConnector] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<CategoryFilter>('all');

  if (activeConnector === 'google-drive') {
    return <GoogleDriveConnectorSettings onBack={() => setActiveConnector(null)} />;
  }

  if (activeConnector && RICH_COMPONENTS[activeConnector]) {
    const RichComponent = RICH_COMPONENTS[activeConnector];
    return (
      <div>
        <div className="mx-auto w-full max-w-[1440px] px-4 pt-5 sm:px-6 sm:pt-6 lg:px-8">
          <button
            type="button"
            onClick={() => setActiveConnector(null)}
            className="-ml-1 inline-flex items-center gap-1 rounded-sm px-1 text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Icon name="chevron-left" className="h-3.5 w-3.5" /> All connectors
          </button>
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
          status={c.status}
          targetSystem={c.targetSystem}
          onBack={() => setActiveConnector(null)}
        />
      );
    }
  }

  const q = query.trim().toLowerCase();
  const matchesQuery = (c: Connector) =>
    !q || [c.name, c.description, VENDOR_OF[c.id] || '', ...c.inputs, ...c.outputs].some(s => s.toLowerCase().includes(q));
  const searched = CONNECTORS.filter(matchesQuery);
  const visible = searched.filter(c => category === 'all' || categoryOf(c.id) === category);
  const countOf = (cat: Category) => searched.filter(c => categoryOf(c.id) === cat).length;

  return (
    <div className="page">
      <div className="min-w-0">
        <h2 className="text-xl font-medium tracking-tight text-foreground sm:text-2xl">Connector catalogue</h2>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          The systems Nexus AI can read from and act on. Open a connector to set it up or to see the APIs it exposes.
        </p>
      </div>

      <Toolbar className="mt-5">
        <Chips<CategoryFilter>
          label="Connector category"
          value={category}
          onChange={setCategory}
          options={[
            { value: 'all', label: 'All', count: searched.length },
            { value: 'business', label: 'Business systems', count: countOf('business') },
            { value: 'productivity', label: 'Productivity', count: countOf('productivity') },
            { value: 'knowledge', label: 'Knowledge and automation', count: countOf('knowledge') },
          ]}
        />
        <ToolbarSpacer />
        <SearchInput value={query} onChange={setQuery} placeholder="Search connectors" />
      </Toolbar>

      {visible.length === 0 ? (
        <EmptyState
          className="mt-5"
          icon="plug"
          title="No connectors match"
          description="Try a different search or category."
          action={
            <button type="button" onClick={() => { setQuery(''); setCategory('all'); }} className="text-sm font-medium text-foreground underline underline-offset-4">
              Clear filters
            </button>
          }
        />
      ) : (
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((c, i) => (
            <button
              key={c.id}
              type="button"
              style={{ '--i': Math.min(i, 8) } as React.CSSProperties}
              onClick={() => setActiveConnector(c.id)}
              className="rise group flex flex-col rounded-xl border border-border bg-card p-5 text-left shadow-xs transition-[border-color,box-shadow,transform] duration-300 ease-brand-out hover:-translate-y-0.5 hover:border-brand/50 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span className="flex items-center gap-3.5">
                <SystemLogo system={c.id} tile size="lg" />
                <span className="min-w-0">
                  <span className="block truncate text-md font-medium text-foreground">{c.name}</span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {VENDOR_OF[c.id] ? `${VENDOR_OF[c.id]} · ` : ''}{CATEGORY_LABEL[categoryOf(c.id)]}
                  </span>
                </span>
              </span>

              <span className="mt-4 line-clamp-2 text-sm text-muted-foreground">{c.description}</span>

              <span className="mt-3 line-clamp-2 text-xs text-muted-foreground">
                <span className="text-subtle-foreground">Reads:</span> {quiet(c.inputs)}
                <span className="mx-1.5" aria-hidden="true">·</span>
                <span className="text-subtle-foreground">Writes:</span> {quiet(c.outputs)}
              </span>

              <span className="min-h-4 flex-1" />
              <span className="flex w-full items-center justify-between gap-3 border-t border-border pt-3">
                {c.status === 'Available'
                  ? <StatusPill status="available" className="font-normal text-muted-foreground" />
                  : <StatusPill tone="neutral" className="font-normal text-muted-foreground">Coming soon</StatusPill>}
                <span className="inline-flex items-center gap-1 text-sm font-medium text-foreground">
                  Configure <Icon name="arrow-right" className="h-3.5 w-3.5 transition-transform duration-300 ease-brand-out group-hover:translate-x-0.5" />
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
