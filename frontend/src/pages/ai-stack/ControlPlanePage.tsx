import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Loader2, Search, Database, FileText, GitBranch, Link2, Clock,
  ChevronRight, ChevronLeft, ChevronDown, RefreshCw, Network, Zap, Eye,
} from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { ontoApi, type OntoDocument, type OntoStats, type SearchResult } from '@/services/ontoApi';
import { SemanticRagStudioPanel } from '@/components/journeys/SemanticRagStudioPanel';
import KnowledgeGraphView from '@/components/control-plane/KnowledgeGraphView';
import BuildIndexPanel from '@/components/rag/BuildIndexPanel';
import OntoDataManager from '@/components/rag/OntoDataManager';
import {
  knowledgePipelinesService,
  KnowledgePipeline,
  KnowledgePipelineRun,
} from '@/services/knowledgePipelinesService';

export default function ControlPlanePage() {
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState(searchParams.get('tab') || 'semantic');

  useEffect(() => {
    const t = searchParams.get('tab');
    if (t) setTab(t);
  }, [searchParams]);

  return (
    <Layout>
      <Tabs value={tab} onValueChange={setTab} className="flex flex-col h-full">
        <div className="border-b border-border px-6 pt-3">
          <TabsList className="bg-transparent gap-1 h-auto p-0 flex-wrap">
            {[
              { value: 'semantic', label: 'Knowledge Pipeline' },
              { value: 'knowledge', label: 'Knowledge Index' },
              { value: 'explorer', label: 'Knowledge Graph' },
              { value: 'policies', label: 'Policy Builder' },
              { value: 'workflows', label: 'Workflows' },
              { value: 'integrations', label: 'Integration Rules' },
            ].map(t => (
              <TabsTrigger key={t.value} value={t.value}
                className="data-[state=active]:bg-blue-600/20 data-[state=active]:text-blue-300 gap-1.5 text-xs px-3 py-1.5 rounded-t-md rounded-b-none border-b-2 border-transparent data-[state=active]:border-blue-400">
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        <div className="flex-1 overflow-auto">
          <TabsContent value="semantic" className="mt-0"><SemanticLayerInner /></TabsContent>
          <TabsContent value="knowledge" className="mt-0 h-full"><KnowledgeFormationInner /></TabsContent>
          <TabsContent value="explorer" className="mt-0 h-full"><KnowledgeGraphView /></TabsContent>
          <TabsContent value="policies" className="mt-0"><PolicyBuilderInner /></TabsContent>
          <TabsContent value="workflows" className="mt-0"><WorkflowRulesInner /></TabsContent>
          <TabsContent value="integrations" className="mt-0"><IntegrationRulesInner /></TabsContent>
        </div>
      </Tabs>
    </Layout>
  );
}

// ============================================================================
// Shared
// ============================================================================

interface SimulatorStatus {
  loaded: boolean;
  tables: number;
  rows: number;
}

interface CpStats {
  total_embeddings: number;
  graph_nodes: number;
  graph_edges: number;
  onto_schema: number;
  onto_policy: number;
  onto_workflow: number;
  onto_integration: number;
  fdw_tables: number;
  embedding_available: boolean;
  virtual_entities?: number;
  mapped_entities?: number;
  virtual_only_entities?: number;
  unmapped_entities?: number;
  mapping_rules_total?: number;
  mapping_rules_active?: number;
  entities_by_system?: Record<string, number>;
  simulator_status?: Record<string, SimulatorStatus>;
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-4">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{label}</div>
    </div>
  );
}

const CATEGORY_COLORS: Record<string, string> = {
  onto_schema: 'bg-blue-500',
  onto_policy: 'bg-amber-500',
  onto_workflow: 'bg-green-500',
  onto_integration: 'bg-purple-500',
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  onto_schema: <Database className="h-4 w-4" />,
  onto_policy: <FileText className="h-4 w-4" />,
  onto_workflow: <GitBranch className="h-4 w-4" />,
  onto_integration: <Link2 className="h-4 w-4" />,
};

// ============================================================================
// Knowledge Pipelines table (Phase 3.4, data-organization spec)
// ============================================================================

function KnowledgePipelinesTable() {
  const [pipelines, setPipelines] = useState<KnowledgePipeline[]>([]);
  const [runsByPipeline, setRunsByPipeline] = useState<Record<string, KnowledgePipelineRun[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await knowledgePipelinesService.list();
      const items = r.items || [];
      setPipelines(items);
      const runsMap: Record<string, KnowledgePipelineRun[]> = {};
      for (const p of items) {
        try {
          const runs = await knowledgePipelinesService.listRuns(p.pipelineId, 5);
          runsMap[p.pipelineId] = runs.items || [];
        } catch {
          runsMap[p.pipelineId] = [];
        }
      }
      setRunsByPipeline(runsMap);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading && pipelines.length === 0) {
    return (
      <div className="px-6 py-3 text-xs text-muted-foreground flex items-center gap-2">
        <Loader2 className="h-3 w-3 animate-spin" /> Loading pipeline registry...
      </div>
    );
  }
  if (error || pipelines.length === 0) {
    return null;
  }

  return (
    <div className="px-6 py-3 border-b">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Pipelines Registry
          </h3>
        </div>
        <Button variant="ghost" size="sm" onClick={load} disabled={loading}>
          {loading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <RefreshCw className="h-3 w-3 mr-1" />}
          Refresh
        </Button>
      </div>
      <div className="rounded border overflow-hidden">
        <div className="grid grid-cols-12 gap-2 px-3 py-1.5 bg-muted/40 text-[10px] uppercase tracking-wider text-muted-foreground">
          <div className="col-span-3">Pipeline</div>
          <div className="col-span-5">Description</div>
          <div className="col-span-2">Outputs</div>
          <div className="col-span-1">Runs</div>
          <div className="col-span-1">Last run</div>
        </div>
        {pipelines.map((p) => {
          const runs = runsByPipeline[p.pipelineId] || [];
          const last = runs[0];
          const lastTs = last?.SK ? last.SK.replace('RUN#', '') : (last?.recordedAt || '');
          return (
            <div key={p.pipelineId} className="grid grid-cols-12 gap-2 px-3 py-2 items-center border-t text-xs">
              <div className="col-span-3">
                <div className="font-mono text-xs">{p.pipelineId}</div>
                <div className="text-[10px] text-muted-foreground truncate">{p.name}</div>
              </div>
              <div className="col-span-5 text-[11px] text-muted-foreground truncate">{p.description}</div>
              <div className="col-span-2 flex flex-wrap gap-1">
                {(p.outputs || []).map((o) => (
                  <Badge key={o} variant="outline" className="text-[9px] font-mono">{o}</Badge>
                ))}
              </div>
              <div className="col-span-1 text-[11px]">{runs.length}</div>
              <div className="col-span-1 text-[10px] text-muted-foreground truncate" title={lastTs}>
                {lastTs ? new Date(lastTs).toLocaleString() : '—'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// Semantic Layer (stats)
// ============================================================================

function SemanticLayerInner() {
  const [stats, setStats] = useState<CpStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [showKnowledgeData, setShowKnowledgeData] = useState(false);
  const [showIndexReport, setShowIndexReport] = useState(false);

  const refreshStats = useCallback(() => {
    setStatsLoading(true);
    apiClient.get<CpStats>('/api/v1/control-plane/stats')
      .then(setStats).catch(() => {}).finally(() => setStatsLoading(false));
  }, []);

  useEffect(() => { refreshStats(); }, []);

  // Auto-refresh stats every 30 seconds
  useEffect(() => {
    const interval = setInterval(refreshStats, 30000);
    return () => clearInterval(interval);
  }, [refreshStats]);

  const s = stats;
  return (
    <div className="flex flex-col h-full">
      {/* Semantic Stats bar */}
      <div className="px-6 pt-4 pb-3 border-b space-y-3">
        {statsLoading && !stats ? (
          <div className="flex items-center gap-2 text-muted-foreground text-sm"><Loader2 className="h-4 w-4 animate-spin" />Loading stats...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
              <StatCard label="Graph Nodes" value={s ? s.graph_nodes.toLocaleString() : '—'} />
              <StatCard label="Graph Edges" value={s ? s.graph_edges.toLocaleString() : '—'} />
              <StatCard label="Embeddings" value={s ? s.total_embeddings.toLocaleString() : '—'} />
              <StatCard label="Embedding Svc" value={s?.embedding_available ? 'Active' : '—'} />
              <StatCard label="Schemas" value={s ? s.onto_schema.toLocaleString() : '—'} />
              <StatCard label="Policies" value={s ? s.onto_policy.toLocaleString() : '—'} />
              <StatCard label="Workflows" value={s ? s.onto_workflow.toLocaleString() : '—'} />
              <StatCard label="Integrations" value={s ? s.onto_integration.toLocaleString() : '—'} />
            </div>
          </>
        )}
      </div>

      {/* Knowledge Pipeline registry (Phase 3.4). Compact table above the
          journey studio — pulls KP# rows + last run timestamps. */}
      <KnowledgePipelinesTable />

      {/* Journey Studio View (Knowledge Processor) */}
      <div className="flex-1 overflow-auto">
        <SemanticRagStudioPanel
          hideBackButton
          hideStatsCards
          hideHeader
          overrideReportButton={
            <Button variant="outline" className="flex items-center gap-2" onClick={() => setShowIndexReport(true)}>
              <FileText className="h-4 w-4" />View Index Report
            </Button>
          }
          extraHeaderButtons={
            <Button variant="outline" size="sm" onClick={() => setShowKnowledgeData(true)}>
              <Database className="h-4 w-4 mr-2" />Knowledge Data
            </Button>
          }
        />
      </div>

      {/* Knowledge Data Modal */}
      {showKnowledgeData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowKnowledgeData(false)}>
          <div className="bg-card border rounded-xl shadow-2xl w-[800px] max-h-[85vh] overflow-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="font-semibold">Knowledge Data Store</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowKnowledgeData(false)}>Close</Button>
            </div>
            <div className="p-4 space-y-4">
              {/* Connected Data Sources — dynamic from stats */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Connected Data Sources</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3">
                    {(() => {
                      const sources = [
                        { key: 'Salesforce', simKey: 'sfdc', label: 'Salesforce CRM', desc: 'Customers, Orders, Opportunities', color: 'bg-blue-500', letter: 'S' },
                        { key: 'Oracle', simKey: 'oracle', label: 'Oracle ERP', desc: 'Finance, AR/AP/GL, Operations', color: 'bg-orange-500', letter: 'O' },
                        { key: 'SAP', simKey: 'sap', label: 'SAP S/4HANA', desc: 'Inventory, Supply Chain, Production', color: 'bg-green-500', letter: 'S' },
                        { key: 'Google_Drive', simKey: '', label: 'Google Drive', desc: 'Contracts, Documents', color: 'bg-red-500', letter: 'G' },
                        { key: 'Social_Listening', simKey: '', label: 'Social Listening', desc: 'Market Signals, Sentiment', color: 'bg-purple-500', letter: 'M' },
                        { key: 'File_Uploads', simKey: '', label: 'File Uploads', desc: 'Invoices, Lab Reports', color: 'bg-cyan-500', letter: 'F' },
                      ];
                      const entityMap = s?.entities_by_system || {};
                      const simMap = s?.simulator_status || {};
                      const activeSources = sources.filter(src => (entityMap[src.key] || 0) > 0);
                      return activeSources.map(src => {
                        const entityCount = entityMap[src.key] || 0;
                        const sim = src.simKey ? simMap[src.simKey] : undefined;
                        return (
                          <div key={src.key} className="flex items-center gap-3 p-3 rounded-lg border">
                            <div className={`w-8 h-8 rounded-full ${src.color} flex items-center justify-center text-white text-xs font-bold shrink-0`}>{src.letter}</div>
                            <div className="min-w-0">
                              <div className="text-xs font-medium">{src.label}</div>
                              <div className="text-[10px] text-muted-foreground">{src.desc}</div>
                              <div className="text-[10px] text-muted-foreground">
                                {entityCount} entities
                                {sim ? (sim.loaded ? ` · Simulator: ${sim.tables} tables, ${sim.rows.toLocaleString()} rows` : ' · Simulator: not loaded') : ''}
                              </div>
                            </div>
                          </div>
                        );
                      });
                    })()}
                  </div>
                </CardContent>
              </Card>

              {/* Virtual Entity Summary */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Virtual Data Layer</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 mb-3">
                    <div className="text-2xl font-bold">{s?.virtual_entities || 0}</div>
                    <div className="text-xs text-muted-foreground">
                      entities across {Object.keys(s?.entities_by_system || {}).length} systems
                    </div>
                  </div>
                  {(() => {
                    const mapped = s?.mapped_entities || 0;
                    const virtual = s?.virtual_only_entities || 0;
                    const unmapped = s?.unmapped_entities || 0;
                    const total = mapped + virtual + unmapped || 1;
                    return (
                      <>
                        <div className="flex h-3 rounded-full overflow-hidden bg-muted/30 mb-2">
                          {mapped > 0 && <div className="bg-green-500" style={{ width: `${(mapped / total) * 100}%` }} />}
                          {virtual > 0 && <div className="bg-yellow-500" style={{ width: `${(virtual / total) * 100}%` }} />}
                          {unmapped > 0 && <div className="bg-gray-500" style={{ width: `${(unmapped / total) * 100}%` }} />}
                        </div>
                        <div className="flex gap-4 text-[10px]">
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" />{mapped} Mapped</span>
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" />{virtual} Virtual</span>
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-500" />{unmapped} Unmapped</span>
                          <span className="ml-auto text-muted-foreground">{s?.mapping_rules_active || 0} active mapping rules</span>
                        </div>
                      </>
                    );
                  })()}
                </CardContent>
              </Card>

              {/* Enhanced Stats Row */}
              <div className="grid grid-cols-6 gap-2 text-center">
                <div className="p-2 rounded bg-muted/50"><div className="text-sm font-bold">{s?.virtual_entities || '—'}</div><div className="text-[9px] text-muted-foreground">Schema Entities</div></div>
                <div className="p-2 rounded bg-muted/50"><div className="text-sm font-bold">{s?.mapped_entities || '—'}</div><div className="text-[9px] text-muted-foreground">Mapped</div></div>
                <div className="p-2 rounded bg-muted/50"><div className="text-sm font-bold">{s?.mapping_rules_active || '—'}</div><div className="text-[9px] text-muted-foreground">Mapping Rules</div></div>
                <div className="p-2 rounded bg-muted/50"><div className="text-sm font-bold">{s?.onto_policy || '—'}</div><div className="text-[9px] text-muted-foreground">Policies</div></div>
                <div className="p-2 rounded bg-muted/50"><div className="text-sm font-bold">{s?.onto_workflow || '—'}</div><div className="text-[9px] text-muted-foreground">Workflows</div></div>
                <div className="p-2 rounded bg-muted/50"><div className="text-sm font-bold">{s?.onto_integration || '—'}</div><div className="text-[9px] text-muted-foreground">Integrations</div></div>
              </div>

              {/* Onto Data Manager */}
              <OntoDataManager />
            </div>
          </div>
        </div>
      )}

      {/* Index Report Modal */}
      {showIndexReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowIndexReport(false)}>
          <div className="bg-card border rounded-xl shadow-2xl w-[600px] max-h-[80vh] overflow-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="font-semibold flex items-center gap-2"><Database className="h-4 w-4" />Knowledge Index Report</h3>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => {
                  const blob = new Blob([JSON.stringify(s, null, 2)], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a'); a.href = url; a.download = 'knowledge-index-report.json'; a.click();
                }}>Export JSON</Button>
                <Button variant="ghost" size="sm" onClick={() => setShowIndexReport(false)}>Close</Button>
              </div>
            </div>
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <Card><CardContent className="pt-4 text-center">
                  <div className="text-3xl font-bold">{s?.total_embeddings.toLocaleString() || '—'}</div>
                  <div className="text-xs text-muted-foreground mt-1">Total Embeddings</div>
                </CardContent></Card>
                <Card><CardContent className="pt-4 text-center">
                  <div className="text-3xl font-bold">{s?.graph_nodes.toLocaleString() || '—'}</div>
                  <div className="text-xs text-muted-foreground mt-1">Graph Nodes</div>
                </CardContent></Card>
              </div>
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Index Breakdown</CardTitle></CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {[
                      { label: 'Schema Documents', value: s?.onto_schema, color: 'bg-blue-500' },
                      { label: 'Policy Documents', value: s?.onto_policy, color: 'bg-amber-500' },
                      { label: 'Workflow Documents', value: s?.onto_workflow, color: 'bg-green-500' },
                      { label: 'Integration Documents', value: s?.onto_integration, color: 'bg-purple-500' },
                    ].map(item => (
                      <div key={item.label} className="flex items-center justify-between py-1.5">
                        <div className="flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
                          <span className="text-sm">{item.label}</span>
                        </div>
                        <span className="font-mono font-bold text-sm">{item.value?.toLocaleString() || '0'}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Graph Database</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div><div className="text-xl font-bold">{s?.graph_nodes.toLocaleString() || '—'}</div><div className="text-[10px] text-muted-foreground">Nodes</div></div>
                    <div><div className="text-xl font-bold">{s?.graph_edges.toLocaleString() || '—'}</div><div className="text-[10px] text-muted-foreground">Edges</div></div>
                    <div><div className="text-xl font-bold">{s?.embedding_available ? 'Active' : 'Inactive'}</div><div className="text-[10px] text-muted-foreground">Embedding Svc</div></div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Knowledge Formation — Vector DB Document Browser
// ============================================================================

const CATEGORY_LABELS: Record<string, string> = {
  onto_schema: 'Schema',
  onto_policy: 'Policy',
  onto_workflow: 'Workflow',
  onto_integration: 'Integration',
};

const SYSTEM_COLORS: Record<string, string> = {
  Salesforce: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  SAP: 'bg-green-500/20 text-green-300 border-green-500/30',
  Oracle: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  Google_Drive: 'bg-red-500/20 text-red-300 border-red-500/30',
  Social_Listening: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
  Internal: 'bg-gray-500/20 text-gray-300 border-gray-500/30',
};

function docDisplayName(doc: OntoDocument): string {
  const meta = doc.metadata || {};
  if (meta.object_name) return meta.object_name;
  return doc.source_id.replace(/_V1_0$/, '').replace(/^[^_]+_/, '').replace(/_/g, ' ');
}

function KnowledgeFormationInner() {
  const [category, setCategory] = useState('onto_schema');
  const [query, setQuery] = useState('');
  const [documents, setDocuments] = useState<OntoDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [pageSize] = useState(50);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<OntoDocument | null>(null);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [lastIndexedAt, setLastIndexedAt] = useState<string | null>(null);
  const [showMetadata, setShowMetadata] = useState(false);

  useEffect(() => {
    ontoApi.getStats().then((d: OntoStats) => {
      setStats(d.by_content_type || {});
      setLastIndexedAt(d.last_indexed_at || null);
    }).catch(() => {});
  }, []);

  const fetchDocuments = useCallback(async (cat: string, off: number, q: string) => {
    setLoading(true);
    try {
      const data = await ontoApi.listDocuments({
        content_type: cat,
        offset: off,
        limit: pageSize,
        q: q || undefined,
      });
      setDocuments(data.documents || []);
      setTotal(data.total || 0);
    } catch {
      setDocuments([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  useEffect(() => {
    setOffset(0);
    setSelected(null);
    fetchDocuments(category, 0, query);
  }, [category]);

  useEffect(() => {
    fetchDocuments(category, offset, query);
  }, [offset]);

  const handleSearch = () => {
    setOffset(0);
    setSelected(null);
    fetchDocuments(category, 0, query);
  };

  const categories = [
    { key: 'onto_schema', label: 'Schemas', icon: <Database className="h-3.5 w-3.5" /> },
    { key: 'onto_policy', label: 'Policies', icon: <FileText className="h-3.5 w-3.5" /> },
    { key: 'onto_workflow', label: 'Workflows', icon: <GitBranch className="h-3.5 w-3.5" /> },
    { key: 'onto_integration', label: 'Integrations', icon: <Link2 className="h-3.5 w-3.5" /> },
  ];

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.floor(offset / pageSize) + 1;

  return (
    <div className="p-6 flex flex-col h-full gap-3">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold mb-1">Knowledge Index</h2>
          <p className="text-sm text-muted-foreground">Browse indexed enterprise knowledge documents by category</p>
        </div>
        {lastIndexedAt && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 rounded-lg px-3 py-1.5 shrink-0">
            <Clock className="h-3.5 w-3.5" />
            Last indexed: {new Date(lastIndexedAt).toLocaleString()}
          </div>
        )}
      </div>

      {/* Category Tabs */}
      <div className="flex gap-2 flex-wrap">
        {categories.map(c => (
          <button key={c.key} onClick={() => setCategory(c.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              category === c.key ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30' : 'bg-muted/50 text-muted-foreground hover:bg-muted'}`}>
            {c.icon} {c.label}
            <Badge variant="outline" className="text-[9px] ml-1">{stats[c.key] || 0}</Badge>
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex gap-2">
        <Input placeholder="Filter documents by name or content..." value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()} className="flex-1" />
        <Button size="sm" onClick={handleSearch} disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
        </Button>
      </div>

      {/* Main Content: List + Detail */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-4 min-h-0 overflow-hidden">
        {/* Document List */}
        <Card className="flex flex-col min-h-0 overflow-hidden">
          <CardHeader className="pb-2 shrink-0">
            <CardTitle className="text-sm flex items-center justify-between">
              <span>Documents ({total})</span>
              {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0 p-0 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="divide-y">
                {documents.map(doc => {
                  const meta = doc.metadata || {};
                  const system = meta.source_system || meta.system || '';
                  const domain = meta.domain || '';
                  return (
                    <button key={doc.source_id} onClick={() => setSelected(doc)}
                      className={`w-full text-left px-3 py-2.5 hover:bg-muted/50 transition-colors ${selected?.source_id === doc.source_id ? 'bg-blue-600/10 border-l-2 border-l-blue-400' : 'border-l-2 border-l-transparent'}`}>
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className={`w-2 h-2 rounded-full shrink-0 ${CATEGORY_COLORS[doc.content_type] || 'bg-gray-500'}`} />
                        <span className="text-xs font-medium truncate flex-1">{docDisplayName(doc)}</span>
                      </div>
                      <div className="flex items-center gap-1.5 ml-4">
                        {system && (
                          <Badge variant="outline" className={`text-[9px] py-0 border ${SYSTEM_COLORS[system] || 'text-muted-foreground'}`}>{system}</Badge>
                        )}
                        {domain && (
                          <span className="text-[9px] text-muted-foreground truncate">{domain}</span>
                        )}
                      </div>
                    </button>
                  );
                })}
                {documents.length === 0 && !loading && (
                  <div className="p-8 text-center text-muted-foreground text-sm">
                    {query ? 'No documents match your filter' : 'No documents indexed yet'}
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Document Detail */}
        <Card className="flex flex-col min-h-0 overflow-hidden">
          <CardHeader className="pb-2 shrink-0">
            <CardTitle className="text-sm">
              {selected ? 'Document Detail' : 'Select a document'}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0 p-0 overflow-hidden">
            {selected ? (
              <ScrollArea className="h-full">
                <div className="p-4 space-y-4">
                  {/* Identity */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-[10px] text-muted-foreground mb-0.5">Name</div>
                      <div className="text-sm font-medium">{docDisplayName(selected)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-muted-foreground mb-0.5">Type</div>
                      <Badge variant="outline" className={`${CATEGORY_COLORS[selected.content_type] ? CATEGORY_COLORS[selected.content_type].replace('bg-', 'text-').replace('-500', '-300') : ''}`}>
                        {CATEGORY_LABELS[selected.content_type] || selected.content_type}
                      </Badge>
                    </div>
                    {(selected.metadata?.source_system || selected.metadata?.system) && (
                      <div>
                        <div className="text-[10px] text-muted-foreground mb-0.5">System</div>
                        <Badge variant="outline" className={`border ${SYSTEM_COLORS[selected.metadata.source_system || selected.metadata.system] || ''}`}>
                          {selected.metadata.source_system || selected.metadata.system}
                        </Badge>
                      </div>
                    )}
                    {selected.metadata?.domain && (
                      <div>
                        <div className="text-[10px] text-muted-foreground mb-0.5">Domain</div>
                        <div className="text-xs">{selected.metadata.domain}</div>
                      </div>
                    )}
                    {selected.metadata?.scor_process && (
                      <div>
                        <div className="text-[10px] text-muted-foreground mb-0.5">SCOR Process</div>
                        <div className="text-xs">{selected.metadata.scor_process}</div>
                      </div>
                    )}
                    {selected.updated_at && (
                      <div>
                        <div className="text-[10px] text-muted-foreground mb-0.5">Updated</div>
                        <div className="text-xs">{new Date(selected.updated_at).toLocaleString()}</div>
                      </div>
                    )}
                  </div>

                  <div className="border-t pt-3">
                    <div className="text-[10px] text-muted-foreground mb-0.5">Source ID</div>
                    <div className="font-mono text-[10px] text-muted-foreground break-all">{selected.source_id}</div>
                  </div>

                  {/* Key Fields */}
                  {selected.metadata?.key_field_details && selected.metadata.key_field_details.length > 0 && (
                    <div className="border-t pt-3">
                      <div className="text-[10px] text-muted-foreground mb-1.5">Key Fields</div>
                      <div className="space-y-1">
                        {selected.metadata.key_field_details.map((f: any, i: number) => (
                          <div key={i} className="flex items-center gap-2 text-xs bg-muted/30 rounded px-2 py-1">
                            <span className="font-medium">{f.name}</span>
                            {f.data_type && <Badge variant="outline" className="text-[8px] py-0">{f.data_type}</Badge>}
                            {f.semantic && <span className="text-muted-foreground truncate text-[10px]">{f.semantic}</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Content */}
                  <div className="border-t pt-3">
                    <div className="text-[10px] text-muted-foreground mb-1">Content</div>
                    <pre className="text-xs whitespace-pre-wrap bg-muted/50 p-3 rounded-lg leading-relaxed">{selected.content}</pre>
                  </div>

                  {/* Metadata (collapsible) */}
                  {selected.metadata && Object.keys(selected.metadata).length > 0 && (
                    <div className="border-t pt-3">
                      <button onClick={() => setShowMetadata(!showMetadata)}
                        className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors">
                        {showMetadata ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                        Raw Metadata
                      </button>
                      {showMetadata && (
                        <pre className="text-[10px] whitespace-pre-wrap bg-muted/50 p-3 rounded-lg font-mono mt-1.5 max-h-[300px] overflow-auto">
                          {JSON.stringify(selected.metadata, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              </ScrollArea>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
                <Database className="h-8 w-8 opacity-30" />
                <span className="text-sm">Click a document to inspect its content and metadata</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="flex items-center justify-between text-xs text-muted-foreground shrink-0 pt-1">
          <span>Showing {offset + 1}–{Math.min(offset + pageSize, total)} of {total} documents</span>
          <div className="flex items-center gap-1">
            <Button variant="outline" size="sm" disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - pageSize))} className="h-7 px-2">
              <ChevronLeft className="h-3.5 w-3.5" />
            </Button>
            <span className="px-2 text-xs">Page {currentPage} of {totalPages}</span>
            <Button variant="outline" size="sm" disabled={offset + pageSize >= total}
              onClick={() => setOffset(offset + pageSize)} className="h-7 px-2">
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Semantic Explorer — Graph Visualization
// ============================================================================

interface GraphNode { id: string }
interface GraphEdge { source: string; target: string; type: string; description?: string }

function SemanticExplorerInner() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(false);
  const [neighborCount, setNeighborCount] = useState(0);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const doSearch = async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const data = await apiClient.post<SearchResult[]>('/api/v1/control-plane/search', {
        query: searchQuery, limit: 10,
      });
      setSearchResults(data);
    } catch { setSearchResults([]); }
    finally { setLoading(false); }
  };

  const loadGraph = async (ontoId: string) => {
    setSelectedId(ontoId);
    setLoading(true);
    try {
      const data = await ontoApi.getGraphNeighborhood(ontoId, 2);
      setNodes(data.nodes || []);
      setEdges(data.edges || []);
      setNeighborCount(data.neighbor_count || 0);
      setSelectedNode(ontoId);
    } catch { setNodes([]); setEdges([]); }
    finally { setLoading(false); }
  };

  const nodeEdges = selectedNode ? edges.filter(e => e.source === selectedNode || e.target === selectedNode) : [];

  return (
    <div className="p-6 flex flex-col h-full gap-4">
      <div>
        <h2 className="text-xl font-semibold mb-1">Semantic Explorer</h2>
        <p className="text-sm text-muted-foreground">Explore the enterprise knowledge graph — nodes, edges, and relationships</p>
      </div>

      <div className="flex gap-2">
        <Input placeholder="Search for an entity (e.g. Account, credit-policy, Oracle)..."
          value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch()} className="flex-1" />
        <Button size="sm" onClick={doSearch} disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
        </Button>
      </div>

      {searchResults.length > 0 && !selectedId && (
        <Card>
          <CardContent className="p-3">
            <div className="text-xs text-muted-foreground mb-2">Select a node to explore its graph neighborhood:</div>
            <div className="flex flex-wrap gap-2">
              {searchResults.slice(0, 8).map((r, i) => (
                <button key={i} onClick={() => loadGraph(r.source_id)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border hover:bg-muted/50 text-xs transition-colors">
                  <span className={`w-2 h-2 rounded-full ${CATEGORY_COLORS[r.content_type] || 'bg-gray-500'}`} />
                  {r.source_id.replace(/_V1_0$/, '').replace(/_/g, ' ').toLowerCase().slice(0, 40)}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {selectedId && (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
          <div className="lg:col-span-2">
            <Card className="h-full">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Network className="h-4 w-4" />
                    Graph: {nodes.length} nodes, {edges.length} edges
                  </CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => { setSelectedId(''); setNodes([]); setEdges([]); setSearchResults([]); }}>
                    Clear
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="relative bg-muted/20 rounded-lg p-4 min-h-[350px]">
                  {nodes.length > 0 ? (
                    <div className="flex flex-wrap gap-2 justify-center">
                      {nodes.map((n, i) => {
                        const isCenter = n.id === selectedId;
                        const isSelected = n.id === selectedNode;
                        const hasEdge = edges.some(e => e.source === n.id || e.target === n.id);
                        return (
                          <button key={i} onClick={() => setSelectedNode(n.id)}
                            className={`px-3 py-2 rounded-lg text-[10px] font-mono transition-all border ${
                              isCenter ? 'bg-blue-600/30 border-blue-500 text-blue-200' :
                              isSelected ? 'bg-amber-600/30 border-amber-500 text-amber-200' :
                              hasEdge ? 'bg-emerald-600/20 border-emerald-500/50 text-emerald-200' :
                              'bg-card border-border text-muted-foreground hover:border-blue-500/50'
                            }`}>
                            {n.id.replace(/_V1_0$/, '').replace(/_/g, ' ').toLowerCase().slice(0, 35)}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                      {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'No graph data'}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="flex flex-col min-h-0">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">
                {selectedNode ? `Edges for ${selectedNode.replace(/_V1_0$/, '').replace(/_/g, ' ').toLowerCase().slice(0, 30)}` : 'Node Inspector'}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 p-0">
              <ScrollArea className="h-[350px]">
                {selectedNode ? (
                  <div className="p-3 space-y-2">
                    <div className="text-[10px] text-muted-foreground">onto_id</div>
                    <div className="font-mono text-xs mb-3 break-all">{selectedNode}</div>
                    <div className="text-[10px] text-muted-foreground">Edges ({nodeEdges.length})</div>
                    {nodeEdges.length > 0 ? (
                      <div className="space-y-1">
                        {nodeEdges.map((e, i) => {
                          const isOutgoing = e.source === selectedNode;
                          return (
                            <div key={i} className="p-2 rounded bg-muted/30 text-[10px]">
                              <div className="flex items-center gap-1.5">
                                <span className="text-muted-foreground">{isOutgoing ? '→' : '←'}</span>
                                <Badge variant="outline" className="text-[9px]">{e.type}</Badge>
                                <button onClick={() => { setSelectedNode(isOutgoing ? e.target : e.source); loadGraph(isOutgoing ? e.target : e.source); }}
                                  className="font-mono truncate text-blue-400 hover:underline">
                                  {(isOutgoing ? e.target : e.source).replace(/_V1_0$/, '').replace(/_/g, ' ').toLowerCase().slice(0, 30)}
                                </button>
                              </div>
                              {e.description && <p className="text-muted-foreground mt-0.5 ml-4">{e.description}</p>}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-muted-foreground text-xs">No edges found for this node</p>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground text-sm p-4">
                    Click a node to inspect its edges
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Policy Builder / Workflow Rules / Integration Rules (Part 2A)
// ============================================================================

import { KnowledgeEditor, PolicyPreview, WorkflowPreview, IntegrationPreview } from '@/components/control-plane/KnowledgeEditor';
import { POLICY_TEMPLATES, WORKFLOW_TEMPLATES, INTEGRATION_TEMPLATES } from '@/components/control-plane/templates';
import PolicyFormBuilder from '@/components/control-plane/PolicyFormBuilder';
import WorkflowFormBuilder from '@/components/control-plane/WorkflowFormBuilder';
import IntegrationFormBuilder from '@/components/control-plane/IntegrationFormBuilder';

function PolicyBuilderInner() {
  return (
    <KnowledgeEditor
      category="policies"
      fileExtension=".md"
      templates={POLICY_TEMPLATES}
      title="Policy Builder"
      description="Define and manage business policies for the energy drink supply chain"
      renderPreview={(content) => <PolicyPreview content={content} />}
      formBuilder={({ content, onChange }) => <PolicyFormBuilder content={content} onChange={onChange} />}
    />
  );
}

function WorkflowRulesInner() {
  return (
    <KnowledgeEditor
      category="workflows"
      fileExtension=".yaml"
      templates={WORKFLOW_TEMPLATES}
      title="Workflow Rules"
      description="Define process flows spanning Salesforce, Oracle ERP, SAP, and Google Drive"
      renderPreview={(content) => <WorkflowPreview content={content} />}
      formBuilder={({ content, onChange }) => <WorkflowFormBuilder content={content} onChange={onChange} />}
    />
  );
}

function IntegrationRulesInner() {
  return (
    <KnowledgeEditor
      category="integrations"
      fileExtension=".yaml"
      templates={INTEGRATION_TEMPLATES}
      title="Integration Rules"
      description="Configure field-level sync mappings between enterprise systems"
      renderPreview={(content) => <IntegrationPreview content={content} />}
      formBuilder={({ content, onChange }) => <IntegrationFormBuilder content={content} onChange={onChange} />}
    />
  );
}
