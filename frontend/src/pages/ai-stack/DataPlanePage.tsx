import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Plus, Database, RefreshCw, ArrowDownUp, Settings2 } from 'lucide-react';
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

const SOURCE_COLORS: Record<string, string> = {
  FDW: 'from-blue-500 to-blue-600',
  CDC: 'from-green-500 to-green-600',
  ETL: 'from-orange-500 to-orange-600',
  FILE_UPLOAD: 'from-purple-500 to-purple-600',
  CLOUD_DRIVE: 'from-cyan-500 to-cyan-600',
  SOCIAL_LISTENING: 'from-pink-500 to-pink-600',
};

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
      return `${stats.table_count} tables · ${stats.total_rows.toLocaleString()} rows`;
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
  const angleStep = (2 * Math.PI) / Math.max(totalCount, 1);
  const hubRadius = 200;
  const [searchParams] = useSearchParams();
  const [dpTab, setDpTab] = useState(searchParams.get('tab') || 'sources');

  useEffect(() => {
    const t = searchParams.get('tab');
    if (t) setDpTab(t);
  }, [searchParams]);

  return (
    <Layout>
      <Tabs value={dpTab} onValueChange={setDpTab}>
        <div className="sticky top-0 z-20 border-b border-border px-6 pt-3 bg-background">
          <TabsList className="bg-transparent gap-1 h-auto p-0">
            {[
              { value: 'sources', label: 'Data Sources' },
              { value: 'virtualdata', label: 'Virtual Data' },
              { value: 'vdl-apis', label: 'Virtual Data API Registry' },
              { value: 'mappingrules', label: 'Mapping Rules' },
              { value: 'pipelines', label: 'Data Pipelines' },
              { value: 'connectors', label: 'Connectors' },
              { value: 'connector-apis', label: 'Connector Workbench' },
              { value: 'connector-registry', label: 'Connector Registry' },
            ].map(t => (
              <TabsTrigger key={t.value} value={t.value}
                className="data-[state=active]:bg-blue-600/20 data-[state=active]:text-blue-300 gap-1.5 text-xs px-3 py-1.5 rounded-t-md rounded-b-none border-b-2 border-transparent data-[state=active]:border-blue-400">
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

          <TabsContent value="virtualdata" className="mt-0 h-[calc(100vh-6rem)]">
            <EntityExplorer />
          </TabsContent>
          <TabsContent value="vdl-apis" className="mt-0 h-[calc(100vh-6rem)]">
            <VdlApiRegistryBrowser />
          </TabsContent>
          <TabsContent value="mappingrules" className="mt-0 h-[calc(100vh-6rem)]">
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
          <TabsContent value="connector-registry" className="mt-0 h-[calc(100vh-6rem)]">
            <ConnectorApisRegistryBrowser />
          </TabsContent>
          <TabsContent value="sources" className="mt-0">
      <div className="p-6">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">Data Sources</h1>
            <p className="text-sm text-muted-foreground mt-1">Connect and manage your enterprise data ecosystem</p>
          </div>
          <div className="flex items-center gap-3">
            <select value={vertical} onChange={e => setVertical(e.target.value as Vertical)} className="text-xs px-2 py-1 rounded-md border bg-background">
              {VERTICALS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
            </select>
            <button
              onClick={openSettingsForMode}
              className="flex items-center gap-2 rounded-lg border px-3 py-1 text-xs hover:bg-muted/40 transition-colors"
              title="Open Settings to change per-source mode"
            >
              <Badge variant="outline" className="bg-amber-500/10 text-amber-300 border-amber-500/30 text-[10px]">
                {modeSummary.simulator} sim
              </Badge>
              <Badge variant="outline" className="bg-green-500/10 text-green-300 border-green-500/30 text-[10px]">
                {modeSummary.real} real
              </Badge>
              <Settings2 className="h-3 w-3 text-muted-foreground" />
            </button>
            <Badge variant="outline" className="text-xs px-3 py-1">{connectedCount} / {totalCount} connected</Badge>
            <Button variant="outline" size="sm" onClick={loadPlanes} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </Button>
            <Button size="sm" onClick={() => nav('/ai-stack/data-plane/create')}>
              <Plus className="h-4 w-4 mr-1.5" /> Add Data Source
            </Button>
          </div>
        </div>

        {/* Hub-Spoke */}
        <div className="relative mx-auto mb-10" style={{ width: hubRadius * 2 + 280, height: hubRadius * 2 + 280 }}>
          <div className="absolute rounded-full border-2 border-primary/30 flex flex-col items-center justify-center bg-card shadow-lg shadow-primary/5"
            style={{ width: 120, height: 120, left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}>
            <Database className="h-6 w-6 text-primary mb-1" />
            <span className="text-[11px] font-semibold">Data Plane</span>
            <span className="text-[9px] text-muted-foreground">{connectedCount} active</span>
          </div>

          {allSources.map((src, i) => {
            const angle = angleStep * i - Math.PI / 2;
            const x = Math.cos(angle) * hubRadius;
            const y = Math.sin(angle) * hubRadius;
            const cx = hubRadius + 140;
            const cy = hubRadius + 140;
            const colors = SOURCE_COLORS[src.type] || 'from-slate-500 to-slate-600';
            const srcMode = getSourceMode(src.id);
            const simSource = getSimulatorSource(src as SourceDef, srcMode);

            return (
              <div key={src.id}>
                <svg className="absolute inset-0 pointer-events-none" style={{ width: '100%', height: '100%' }}>
                  <line x1={cx} y1={cy} x2={cx + x} y2={cy + y}
                    stroke={src.status === 'connected' ? 'hsl(var(--primary))' : 'hsl(var(--muted))'}
                    strokeWidth={src.status === 'connected' ? 2 : 1}
                    strokeDasharray={src.status === 'connected' ? '' : '4 4'} opacity={0.4} />
                </svg>
                <div className="absolute flex flex-col items-center gap-0.5"
                  style={{ left: cx + x - 55, top: cy + y - 40, width: 110 }}>
                  <button
                    onClick={() => nav(`/ai-stack/data-plane/${src.id}?mode=${srcMode}&source=${simSource}`)}
                    className="transition-transform hover:scale-110 cursor-pointer"
                    title={`Open ${src.name} explorer`}>
                    <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${colors} flex items-center justify-center text-white text-sm font-bold shadow-md mx-auto`}>
                      {src.name.charAt(0)}
                    </div>
                  </button>
                  <span className="text-[10px] font-medium text-center leading-tight truncate max-w-[100px]">{src.name}</span>
                  <span className="text-[9px] text-muted-foreground text-center">{getRecordLabel(src as SourceDef)}</span>
                  <button onClick={openSettingsForMode}
                    className={`text-[8px] px-1.5 py-0.5 rounded-full border transition-colors ${
                      srcMode === 'simulator' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-green-500/20 text-green-300 border-green-500/30'
                    }`} title="Open Settings to change mode">
                    {srcMode === 'simulator' ? 'Simulator' : 'Real FDW'}
                  </button>
                  {pipelinesBySource[src.id] && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setDpTab('pipelines'); }}
                      className={`text-[8px] px-1.5 py-0.5 rounded-full border flex items-center gap-0.5 transition-colors ${
                        pipelinesBySource[src.id].status === 'completed' ? 'bg-green-500/20 text-green-300 border-green-500/30' :
                        pipelinesBySource[src.id].status === 'running' ? 'bg-blue-500/20 text-blue-300 border-blue-500/30' :
                        pipelinesBySource[src.id].status === 'failed' ? 'bg-red-500/20 text-red-300 border-red-500/30' :
                        'bg-muted text-muted-foreground border-border'
                      }`}
                      title="View ETL pipeline"
                    >
                      <ArrowDownUp className="h-2 w-2" /> ETL
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Cards Grid */}
        <h2 className="text-lg font-semibold mb-4">All Data Sources</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {allSources.map(src => {
            const colors = SOURCE_COLORS[src.type] || 'from-slate-500 to-slate-600';
            const srcMode = getSourceMode(src.id);
            const simSource = getSimulatorSource(src as SourceDef, srcMode);
            return (
              <Card key={src.id} className="p-4 flex items-start gap-4 cursor-pointer hover:border-primary/30 transition-colors"
                onClick={() => nav(`/ai-stack/data-plane/${src.id}?mode=${srcMode}&source=${simSource}`)}>
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${colors} flex items-center justify-center text-white text-sm font-bold shrink-0`}>
                  {src.name.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm truncate">{src.name}</span>
                    <button onClick={openSettingsForMode}
                      title="Open Settings to change mode"
                      className={`text-[9px] px-1.5 py-0.5 rounded-full border ml-auto shrink-0 ${
                        srcMode === 'simulator' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-green-500/20 text-green-300 border-green-500/30'
                      }`}>{srcMode === 'simulator' ? 'Simulator' : 'Real FDW'}</button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{src.desc}</p>
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    <Badge variant="secondary" className="text-[10px]">{src.type}</Badge>
                    <span className="text-[10px] text-muted-foreground">{getRecordLabel(src as SourceDef)}</span>
                    {pipelinesBySource[src.id] && (
                      <Badge
                        className={`text-[9px] cursor-pointer ${
                          pipelinesBySource[src.id].status === 'completed' ? 'bg-green-500/20 text-green-300' :
                          pipelinesBySource[src.id].status === 'running' ? 'bg-blue-500/20 text-blue-300' :
                          pipelinesBySource[src.id].status === 'failed' ? 'bg-red-500/20 text-red-300' :
                          'bg-muted text-muted-foreground'
                        }`}
                        onClick={(e) => { e.stopPropagation(); setDpTab('pipelines'); }}
                      >
                        <ArrowDownUp className="h-2.5 w-2.5 mr-0.5" /> ETL {pipelinesBySource[src.id].status}
                      </Badge>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
          <Card className="p-4 flex items-center justify-center border-dashed cursor-pointer hover:border-primary/30 transition-colors min-h-[100px]"
            onClick={() => nav('/ai-stack/data-plane/create')}>
            <div className="flex flex-col items-center gap-2 text-muted-foreground">
              <Plus className="h-6 w-6" />
              <span className="text-xs font-medium">Add Data Source</span>
            </div>
          </Card>
        </div>
      </div>
          </TabsContent>
      </Tabs>
    </Layout>
  );
}
