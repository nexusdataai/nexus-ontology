import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Tabs, TabsContent } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PageTabsBar, useUrlTab, type TabSection } from '@/components/ds/PageTabs';
import { Icon, type IconName } from '@/components/ds/Icon';
import { Button } from '@/components/ui/button';
import { dataPlaneService, DataPlane } from '@/services/dataPlaneService';
import { etlPipelineService } from '@/services/etlPipelineService';
import { dataSourceModeService, type Mode } from '@/services/dataSourceModeService';
import { fdwService } from '@/services/fdwService';
import DataPipelinesTab from '@/components/data-plane/DataPipelinesTab';
import { ConnectorsTab } from '@/components/ConnectorsTab';
import EntityExplorer from '@/components/control-plane/EntityExplorer';
import MappingRulesEditor from '@/components/control-plane/MappingRulesEditor';
import ConnectorApiWorkbenchPanel from '@/components/diagnostics/ConnectorApiWorkbenchPanel';
import ConnectorApisRegistryBrowser from '@/components/registry-browser/ConnectorApisRegistryBrowser';
import VdlApiRegistryBrowser from '@/components/registry-browser/VdlApiRegistryBrowser';

const SOURCE_ICONS: Record<string, IconName> = {
  FDW: 'database',
  CDC: 'refresh',
  ETL: 'shuffle',
  FILE_UPLOAD: 'upload',
  CLOUD_DRIVE: 'folder',
  SOCIAL_LISTENING: 'megaphone-or-rss',
};

/** Tabs grouped into sections. Item values are the original ?tab= values. */
const DP_SECTIONS: TabSection[] = [
  { label: 'Sources', icon: 'database', items: [{ value: 'sources', label: 'Data sources' }] },
  { label: 'Virtual data', icon: 'cube', items: [
    { value: 'virtualdata', label: 'Entities' },
    { value: 'vdl-apis', label: 'API registry' },
  ] },
  { label: 'Mapping rules', icon: 'shuffle', items: [{ value: 'mappingrules', label: 'Mapping rules' }] },
  { label: 'Pipelines', icon: 'route', items: [{ value: 'pipelines', label: 'Data pipelines' }] },
  { label: 'Connectors', icon: 'plug', items: [
    { value: 'connectors', label: 'Catalogue' },
    { value: 'connector-registry', label: 'API registry' },
    { value: 'connector-apis', label: 'Workbench' },
  ] },
];

type Vertical = 'all' | 'supply_chain' | 'crm';

const VERTICALS: { value: Vertical; label: string }[] = [
  { value: 'all', label: 'All Verticals' },
  { value: 'supply_chain', label: 'Supply Chain' },
  { value: 'crm', label: 'CRM' },
];

interface SourceDef {
  id: string;
  name: string;
  type: string;
  status: string;
  desc: string;
  verticals: string[];
  simulatorKey: string;
  entities: number;
}

const SAMPLE_SOURCES: SourceDef[] = [
  { id: 'sample-crm', name: 'Salesforce CRM', type: 'FDW', status: 'connected', desc: 'Customer accounts, pipeline, contracts', verticals: ['crm', 'supply_chain'], simulatorKey: 'simulator', entities: 6 },
  { id: 'sample-erp', name: 'Oracle ERP', type: 'FDW', status: 'connected', desc: 'Finance, AR/AP, general ledger', verticals: ['crm', 'supply_chain'], simulatorKey: 'oracle', entities: 12 },
  { id: 'sample-sap', name: 'SAP S/4HANA', type: 'FDW', status: 'connected', desc: 'Inventory, supply chain, production', verticals: ['supply_chain'], simulatorKey: 'sap', entities: 20 },
  { id: 'sample-drive', name: 'Google Drive', type: 'CLOUD_DRIVE', status: 'connected', desc: 'Contracts, reports, documents', verticals: ['supply_chain'], simulatorKey: 'external', entities: 2 },
  { id: 'sample-files', name: 'File Uploads', type: 'FILE_UPLOAD', status: 'connected', desc: 'Invoices, lab reports, CSV files', verticals: ['supply_chain'], simulatorKey: 'external', entities: 2 },
  { id: 'sample-social', name: 'Social Listening', type: 'SOCIAL_LISTENING', status: 'connected', desc: 'Market signals, sentiment', verticals: ['supply_chain'], simulatorKey: 'external', entities: 3 },
];

interface SimStatus { table_count: number; total_rows: number; tables_with_data: number }

const SOURCE_ID_TO_ETL_TYPE: Record<string, string> = {
  'sample-social': 'social_listening',
  'sample-files': 'file_uploads',
  'sample-drive': 'google_drive',
};

interface PipelineInfo { status: string; sourceType: string; id: string }

// Map a UI source id to a backend mode-resolver key (1:1 with the
// 6 cards on this page).
const SOURCE_ID_TO_MODE_KEY: Record<string, string> = {
  'sample-crm':    'sfdc',
  'sample-erp':    'oracle',
  'sample-sap':    'sap',
  'sample-drive':  'google_drive',
  'sample-files':  'file_uploads',
  'sample-social': 'social_listening',
};

export default function DataPlanePage() {
  const nav = useNavigate();
  const [planes, setPlanes] = useState<DataPlane[]>([]);
  const [loading, setLoading] = useState(true);
  const [vertical, setVertical] = useState<Vertical>('all');
  // Phase 2: modes are now read-only on this page; the canonical write
  // surface is Settings > System > Data Source Mode. The local map is
  // populated from /api/v1/data-source-mode and refreshed on demand.
  const [modeMap, setModeMap] = useState<Record<string, Mode>>({
    sfdc: 'simulator',
    oracle: 'simulator',
    sap: 'simulator',
    file_uploads: 'simulator',
    google_drive: 'simulator',
    social_listening: 'simulator',
  });
  const [modeSummary, setModeSummary] = useState<{ simulator: number; real: number }>({
    simulator: 6, real: 0,
  });
  const [simStats, setSimStats] = useState<Record<string, SimStatus>>({});
  const [pipelinesBySource, setPipelinesBySource] = useState<Record<string, PipelineInfo>>({});

  const loadPlanes = async () => {
    setLoading(true);
    try { setPlanes(await dataPlaneService.list()); } catch { setPlanes([]); }
    finally { setLoading(false); }
  };

  const loadModes = async () => {
    try {
      const r = await dataSourceModeService.list();
      const fallback: Mode = (r.default as Mode) || 'simulator';
      const next: Record<string, Mode> = {};
      for (const src of (r.available_sources || [])) {
        next[src] = (r.modes[src] as Mode) || fallback;
      }
      // Keep keys for the 6 known sources even if the backend trims any.
      for (const k of ['sfdc', 'oracle', 'sap', 'file_uploads', 'google_drive', 'social_listening']) {
        if (!(k in next)) next[k] = fallback;
      }
      setModeMap(next);
      setModeSummary(r.summary || { simulator: 0, real: 0 });
    } catch {
      // leave defaults
    }
  };

  useEffect(() => {
    loadPlanes();
    loadModes();
    const sources: [string, string][] = [
      ['simulator', 'simulator'],
      ['oracle', 'oracle'],
      ['sap', 'sap'],
      ['external', 'external'],
    ];
    for (const [key, source] of sources) {
      fdwService.listTables(undefined, source)
        .then((tables) => setSimStats(prev => ({
          ...prev,
          [key]: { table_count: tables.length, total_rows: 0, tables_with_data: tables.length },
        })))
        .catch(() => {});
    }
    etlPipelineService.listPipelines()
      .then((res: any) => {
        const list = Array.isArray(res) ? res : res?.data ?? [];
        const bySource: Record<string, PipelineInfo> = {};
        for (const p of list) {
          const st = p.config?.sourceType;
          if (st) {
            const srcId = Object.entries(SOURCE_ID_TO_ETL_TYPE).find(([, v]) => v === st)?.[0];
            if (srcId) bySource[srcId] = { status: p.status || 'pending', sourceType: st, id: p.id };
          }
        }
        setPipelinesBySource(bySource);
      })
      .catch(() => {});
  }, []);

  const getSourceMode = (srcId: string): Mode => {
    const key = SOURCE_ID_TO_MODE_KEY[srcId];
    if (!key) return 'simulator';
    return modeMap[key] || 'simulator';
  };

  const openSettingsForMode = (e: React.MouseEvent) => {
    e.stopPropagation();
    nav('/settings?tab=system&category=data_source_mode');
  };

  const getRecordLabel = (src: SourceDef) => {
    const stats = simStats[src.simulatorKey];
    if (stats) {
      return stats.total_rows > 0
        ? `${stats.table_count} tables · ${stats.total_rows.toLocaleString()} rows`
        : `${stats.table_count} tables`;
    }
    return `${src.entities} entities`;
  };

  const getSimulatorSource = (src: SourceDef, mode: string) => {
    if (mode === 'real') return 'real';
    return src.simulatorKey || 'simulator';
  };

  const allSourcesRaw = [
    ...planes.map(p => ({ id: p.id, name: p.name, type: p.type, status: p.status, desc: `${p.type} data source`, real: true, verticals: ['crm'] as string[], simulatorKey: 'simulator', entities: 0 })),
    ...SAMPLE_SOURCES.filter(s => !planes.some(p => p.name === s.name)).map(s => ({ ...s, real: false })),
  ];
  const allSources = vertical === 'all' ? allSourcesRaw : allSourcesRaw.filter(s => s.verticals?.includes(vertical));
  const connectedCount = allSources.filter(s => s.status === 'connected').length;
  const totalCount = allSources.length;
  const [dpTab, setDpTab] = useUrlTab('sources');

  const openSource = (src: { id: string }) => {
    const srcMode = getSourceMode(src.id);
    nav(`/ai-stack/data-plane/${src.id}?mode=${srcMode}&source=${getSimulatorSource(src as SourceDef, srcMode)}`);
  };

  // Geometry of the source map: one row per source, all lines meet at the hub.
  const ROW = 72;
  const mapH = Math.max(totalCount, 1) * ROW;

  return (
    <Layout>
      <Tabs value={dpTab} onValueChange={setDpTab}>
        <PageTabsBar
          title="Data Plane"
          description="Connect enterprise systems, model them as virtual entities, and expose them through governed APIs."
          sections={DP_SECTIONS}
          value={dpTab}
          onChange={setDpTab}
          actions={dpTab === 'sources' ? (
            <>
              <Button variant="outline" size="sm" onClick={loadPlanes} disabled={loading}>
                <Icon name="refresh" className={loading ? 'animate-spin' : undefined} /> Refresh
              </Button>
              <Button size="sm" onClick={() => nav('/ai-stack/data-plane/create')}>
                <Icon name="plus" /> Add data source
              </Button>
            </>
          ) : undefined}
        />

        <TabsContent value="virtualdata" className="mt-0 h-pane-sub">
          <EntityExplorer />
        </TabsContent>
        <TabsContent value="vdl-apis" className="pane-wide mt-0 h-pane-sub">
          <VdlApiRegistryBrowser />
        </TabsContent>
        <TabsContent value="mappingrules" className="mt-0 h-pane">
          <MappingRulesEditor />
        </TabsContent>
        <TabsContent value="pipelines" className="mt-0">
          <DataPipelinesTab />
        </TabsContent>
        <TabsContent value="connectors" className="mt-0">
          <ConnectorsTab />
        </TabsContent>
        <TabsContent value="connector-apis" className="mt-0">
          <ConnectorApiWorkbenchPanel />
        </TabsContent>
        <TabsContent value="connector-registry" className="pane-wide mt-0 h-pane-sub">
          <ConnectorApisRegistryBrowser />
        </TabsContent>

        <TabsContent value="sources" className="mt-0">
          <div className="page">
            {/* Filters and summary */}
            <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
              <Select value={vertical} onValueChange={v => setVertical(v as Vertical)}>
                <SelectTrigger className="h-8 w-[170px]" aria-label="Filter by vertical"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {VERTICALS.map(v => <SelectItem key={v.value} value={v.value}>{v.label}</SelectItem>)}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground">
                <span className="num font-medium text-foreground">{connectedCount}</span> of <span className="num">{totalCount}</span> connected
              </span>
              <button
                type="button"
                onClick={openSettingsForMode}
                title="Source modes are changed in Settings"
                className="group inline-flex items-center gap-2 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              >
                <span><span className="num font-medium text-foreground">{modeSummary.simulator}</span> simulator</span>
                <span aria-hidden="true">·</span>
                <span><span className="num font-medium text-foreground">{modeSummary.real}</span> real</span>
                <Icon name="sliders" className="h-3.5 w-3.5 text-subtle-foreground group-hover:text-foreground" />
              </button>
            </div>

            {/* Source map */}
            <section className="mt-5 overflow-hidden rounded-xl border border-border bg-card shadow-xs">
              <div className="canvas-dots grid gap-0 lg:grid-cols-[minmax(0,400px)_minmax(80px,1fr)_250px]">
                {/* sources */}
                <ul className="min-w-0 py-3 pl-3 pr-3 lg:pr-0">
                  {allSources.map((src, i) => {
                    const srcMode = getSourceMode(src.id);
                    const pipe = pipelinesBySource[src.id];
                    const connected = src.status === 'connected';
                    return (
                      <li key={src.id} style={{ height: ROW, '--i': i } as React.CSSProperties} className="rise flex items-center">
                        <div
                          role="button"
                          tabIndex={0}
                          onClick={() => openSource(src)}
                          onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openSource(src); } }}
                          title={`Open ${src.name} explorer`}
                          className="group flex h-[60px] w-full cursor-pointer items-center gap-3 rounded-lg border border-border bg-card px-3 shadow-xs transition-[border-color,transform,box-shadow] duration-200 ease-brand hover:-translate-y-px hover:border-brand/50 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-surface-2 text-muted-foreground transition-colors group-hover:border-brand/40 group-hover:text-primary dark:group-hover:text-brand-hi">
                            <Icon name={SOURCE_ICONS[src.type] || 'database'} className="h-[18px] w-[18px]" />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="flex items-center gap-2">
                              <span className="truncate text-sm font-medium text-foreground">{src.name}</span>
                              <span className={connected ? 'dot-live text-success' : 'inline-block h-2 w-2 rounded-full bg-subtle-foreground'} title={src.status} />
                            </span>
                            <span className="block truncate text-xs text-muted-foreground">{getRecordLabel(src as SourceDef)} · {src.desc}</span>
                          </span>
                          <span className="flex shrink-0 flex-col items-end gap-1">
                            <button
                              type="button"
                              onClick={openSettingsForMode}
                              title="Open Settings to change mode"
                              className="rounded-sm text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                            >
                              {srcMode === 'simulator' ? 'Simulator' : 'Real FDW'}
                            </button>
                            {pipe && (
                              <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); setDpTab('pipelines'); }}
                                title="View ETL pipeline"
                                className={`rounded-sm text-xs underline-offset-2 hover:underline ${
                                  pipe.status === 'completed' ? 'text-success' : pipe.status === 'running' ? 'text-primary dark:text-brand-hi' : pipe.status === 'failed' ? 'text-destructive' : 'text-muted-foreground'
                                }`}
                              >
                                ETL {pipe.status}
                              </button>
                            )}
                          </span>
                        </div>
                      </li>
                    );
                  })}
                </ul>

                {/* links */}
                <div className="relative hidden lg:block" style={{ height: mapH + 24 }} aria-hidden="true">
                  <svg className="absolute inset-0 h-full w-full" viewBox={`0 0 100 ${mapH + 24}`} preserveAspectRatio="none">
                    {allSources.map((src, i) => {
                      const y = 12 + i * ROW + ROW / 2;
                      const yc = 12 + mapH / 2;
                      const d = `M0,${y} C55,${y} 45,${yc} 100,${yc}`;
                      const connected = src.status === 'connected';
                      return (
                        <g key={src.id} fill="none">
                          <path d={d} stroke="hsl(var(--border-strong))" strokeWidth="1" vectorEffect="non-scaling-stroke" strokeDasharray={connected ? undefined : '3 4'} />
                          {connected && <path d={d} stroke="hsl(var(--brand))" strokeWidth="1.5" strokeLinecap="round" vectorEffect="non-scaling-stroke" className="flow-line" />}
                        </g>
                      );
                    })}
                  </svg>
                </div>

                {/* hub */}
                <div className="flex items-center border-t border-border p-4 lg:border-t-0 lg:py-3 lg:pl-0 lg:pr-5">
                  <div className="glow-brand w-full rounded-lg border border-brand/40 bg-card p-4">
                    <div className="flex items-center gap-2.5">
                      <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
                        <Icon name="layers" className="h-[18px] w-[18px]" />
                      </span>
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-foreground">Virtual data layer</div>
                        <div className="text-xs text-muted-foreground"><span className="num">{connectedCount}</span> active sources</div>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-col gap-1.5 border-t border-border pt-3">
                      <button type="button" onClick={() => setDpTab('virtualdata')} className="group flex items-center justify-between text-sm text-muted-foreground hover:text-foreground">
                        Virtual entities <Icon name="arrow-right" className="h-3.5 w-3.5 transition-transform duration-300 ease-brand-out group-hover:translate-x-0.5" />
                      </button>
                      <button type="button" onClick={() => setDpTab('mappingrules')} className="group flex items-center justify-between text-sm text-muted-foreground hover:text-foreground">
                        Mapping rules <Icon name="arrow-right" className="h-3.5 w-3.5 transition-transform duration-300 ease-brand-out group-hover:translate-x-0.5" />
                      </button>
                      <button type="button" onClick={() => setDpTab('pipelines')} className="group flex items-center justify-between text-sm text-muted-foreground hover:text-foreground">
                        Pipelines <Icon name="arrow-right" className="h-3.5 w-3.5 transition-transform duration-300 ease-brand-out group-hover:translate-x-0.5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between gap-3 border-t border-border px-4 py-2.5">
                <p className="text-xs text-muted-foreground">Select a source to browse its tables and run queries.</p>
                <button type="button" onClick={() => nav('/ai-stack/data-plane/create')} className="inline-flex items-center gap-1.5 text-sm font-medium text-foreground underline-offset-4 hover:underline">
                  <Icon name="plus" className="h-3.5 w-3.5" /> Add data source
                </button>
              </div>
            </section>
          </div>
        </TabsContent>
      </Tabs>
    </Layout>
  );
}
