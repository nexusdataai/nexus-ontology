import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Plus, Play, Clock, CheckCircle, XCircle, Loader2, RefreshCw,
  Database, ArrowRight, Radio, FileText, Globe, Zap, Settings,
  BarChart3, AlertTriangle, Eye, X, Activity, Layers, Timer,
} from 'lucide-react';
import {
  etlPipelineService,
  getStepsForSourceType,
  SOURCE_TYPE_LABELS,
  type ETLPipelineConfig,
  type ETLSourceType,
  type ETLStepDef,
} from '@/services/etlPipelineService';
import { mappingRuleService, type MappingRule } from '@/services/mappingRuleService';
import { ETL_PIPELINE_TEMPLATES, type ETLPipelineTemplate } from '@/config/etlPipelineTemplates';

const STATUS_STYLES: Record<string, { class: string; icon: React.ElementType }> = {
  running:   { class: 'bg-blue-500/20 text-blue-300',   icon: Loader2 },
  completed: { class: 'bg-green-500/20 text-green-300', icon: CheckCircle },
  failed:    { class: 'bg-red-500/20 text-red-300',     icon: XCircle },
  scheduled: { class: 'bg-amber-500/20 text-amber-300', icon: Clock },
  pending:   { class: 'bg-muted text-muted-foreground', icon: Clock },
};

const SOURCE_ICONS: Record<ETLSourceType, React.ElementType> = {
  social_listening: Radio,
  file_uploads: FileText,
  google_drive: Globe,
  generic: Database,
};

const SOURCE_COLORS: Record<ETLSourceType, string> = {
  social_listening: 'from-pink-500 to-pink-600',
  file_uploads: 'from-purple-500 to-purple-600',
  google_drive: 'from-cyan-500 to-cyan-600',
  generic: 'from-slate-500 to-slate-600',
};

const SOURCE_TEXT_COLORS: Record<ETLSourceType, string> = {
  social_listening: 'text-pink-400',
  file_uploads: 'text-purple-400',
  google_drive: 'text-cyan-400',
  generic: 'text-muted-foreground',
};

const SOURCE_DESCRIPTIONS: Record<ETLSourceType, string> = {
  social_listening: 'Market signals, social mentions, competitor alerts',
  file_uploads: 'Invoices, lab reports, CSV files',
  google_drive: 'Contracts, sustainability reports',
  generic: 'Custom data pipeline',
};

interface CreateForm {
  name: string;
  sourceType: ETLSourceType;
  mappingRuleId: string;
  mode: 'full' | 'incremental';
  batchSize: number;
  schedule: string;
}

const DEFAULT_FORM: CreateForm = {
  name: '',
  sourceType: 'generic',
  mappingRuleId: '',
  mode: 'full',
  batchSize: 1000,
  schedule: '',
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  const Icon = cfg.icon;
  return (
    <Badge className={cfg.class}>
      <Icon className={`h-3 w-3 mr-1 ${status === 'running' ? 'animate-spin' : ''}`} />
      {status}
    </Badge>
  );
}

function StepProgress({ steps, currentStep, status }: {
  steps: ETLStepDef[];
  currentStep?: string;
  status: string;
}) {
  const currentIdx = currentStep ? steps.findIndex(s => s.id === currentStep) : -1;
  return (
    <div className="flex items-center gap-0.5">
      {steps.map((step, i) => {
        let stepStatus: 'done' | 'active' | 'pending' | 'failed' = 'pending';
        if (status === 'completed') stepStatus = 'done';
        else if (status === 'failed' && i === currentIdx) stepStatus = 'failed';
        else if (status === 'failed' && i < currentIdx) stepStatus = 'done';
        else if (i < currentIdx) stepStatus = 'done';
        else if (i === currentIdx && status === 'running') stepStatus = 'active';
        const colors = { done: 'bg-green-500', active: 'bg-blue-500 animate-pulse', pending: 'bg-muted-foreground/30', failed: 'bg-red-500' };
        return (
          <div key={step.id} className="flex-1 min-w-0" title={step.name}>
            <div className={`h-1 rounded-full ${colors[stepStatus]}`} />
          </div>
        );
      })}
    </div>
  );
}

function PipelineCard({ pipeline, mappingRules, onRun, onStudio }: {
  pipeline: any;
  mappingRules: MappingRule[];
  onRun: (id: string) => void;
  onStudio: (id: string) => void;
}) {
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);

  useEffect(() => {
    setJobsLoading(true);
    etlPipelineService.getPipelineJobs(pipeline.id)
      .then((res: any) => {
        const list = Array.isArray(res) ? res : res?.jobs ?? res?.data ?? [];
        setJobs(list.map((j: any) => ({
          ...j,
          id: j.id || j.jobId,
          status: j.status || 'pending',
          startedAt: j.startedAt || j.startTime,
          rowsProcessed: j.rowsProcessed || j.itemsProcessed || 0,
          durationMs: j.durationMs || j.duration,
        })));
      })
      .catch(() => setJobs([]))
      .finally(() => setJobsLoading(false));
  }, [pipeline.id, pipeline.status]);

  const sourceType: ETLSourceType = pipeline.config?.sourceType || 'generic';
  const SrcIcon = SOURCE_ICONS[sourceType];
  const steps = getStepsForSourceType(sourceType);
  const rule = mappingRules.find(r => r.id === (pipeline.config?.mappingRuleId ?? pipeline.mappingRuleId));
  const tpl = ETL_PIPELINE_TEMPLATES.find(t => t.sourceType === sourceType);

  const completedJobs = jobs.filter(j => j.status === 'completed');
  const failedJobs = jobs.filter(j => j.status === 'failed');
  const lastRun = jobs[0];
  const totalRows = jobs.reduce((sum, j) => sum + (j.rowsProcessed || 0), 0);

  return (
    <Card className="overflow-hidden">
      <div className={`h-1 bg-gradient-to-r ${SOURCE_COLORS[sourceType]}`} />
      <CardContent className="pt-4 pb-3 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${SOURCE_COLORS[sourceType]} flex items-center justify-center text-white shrink-0`}>
              <SrcIcon className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium truncate">{pipeline.name}</p>
                <StatusBadge status={pipeline.status ?? 'pending'} />
              </div>
              <p className="text-[10px] text-muted-foreground mt-0.5">
                {SOURCE_DESCRIPTIONS[sourceType]}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => onRun(pipeline.id)}>
              <Play className="h-3 w-3 mr-1" />Run
            </Button>
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => onStudio(pipeline.id)}>
              <Eye className="h-3 w-3 mr-1" />Studio
            </Button>
          </div>
        </div>

        {/* Step progress */}
        <StepProgress steps={steps} currentStep={pipeline.currentStep} status={pipeline.status ?? 'pending'} />
        <div className="flex items-center gap-2 text-[9px] text-muted-foreground">
          {steps.map((s, i) => (
            <React.Fragment key={s.id}>
              {i > 0 && <ArrowRight className="h-2 w-2 shrink-0 opacity-40" />}
              <span className="truncate">{s.name}</span>
            </React.Fragment>
          ))}
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-4 gap-2">
          <div className="bg-muted/30 rounded-md px-2.5 py-2 text-center">
            <p className="text-lg font-semibold">{jobs.length}</p>
            <p className="text-[9px] text-muted-foreground">Total Runs</p>
          </div>
          <div className="bg-muted/30 rounded-md px-2.5 py-2 text-center">
            <p className="text-lg font-semibold text-green-400">{completedJobs.length}</p>
            <p className="text-[9px] text-muted-foreground">Completed</p>
          </div>
          <div className="bg-muted/30 rounded-md px-2.5 py-2 text-center">
            <p className="text-lg font-semibold text-red-400">{failedJobs.length}</p>
            <p className="text-[9px] text-muted-foreground">Failed</p>
          </div>
          <div className="bg-muted/30 rounded-md px-2.5 py-2 text-center">
            <p className="text-lg font-semibold">{totalRows > 0 ? totalRows.toLocaleString() : '—'}</p>
            <p className="text-[9px] text-muted-foreground">Rows Processed</p>
          </div>
        </div>

        {/* Pipeline info */}
        <div className="flex items-center gap-3 text-[10px] text-muted-foreground flex-wrap">
          <span className="flex items-center gap-1"><Layers className="h-3 w-3" />{rule?.name || 'Auto-detect'}</span>
          <span className="flex items-center gap-1"><Settings className="h-3 w-3" />{pipeline.config?.mode || 'full'}</span>
          {pipeline.config?.schedule && <span className="flex items-center gap-1 font-mono"><Clock className="h-3 w-3" />{pipeline.config.schedule}</span>}
          {tpl && (
            <span className="flex items-center gap-1">
              <Database className="h-3 w-3" />
              {tpl.targetEntities.join(', ')}
            </span>
          )}
        </div>

        {/* Recent jobs */}
        <div>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Recent Runs</p>
          {jobsLoading ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
              <Loader2 className="h-3 w-3 animate-spin" /> Loading...
            </div>
          ) : jobs.length === 0 ? (
            <p className="text-[10px] text-muted-foreground py-1">No runs recorded yet</p>
          ) : (
            <div className="space-y-1">
              {jobs.slice(0, 3).map((job: any, i: number) => (
                <div key={job.id || i} className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-muted/20 border border-border/50 text-[10px]">
                  <StatusBadge status={job.status || 'pending'} />
                  <span className="font-mono text-muted-foreground">{job.id || `Run ${i + 1}`}</span>
                  {job.startedAt && (
                    <span className="text-muted-foreground ml-auto">
                      {new Date(job.startedAt).toLocaleDateString()} {new Date(job.startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  )}
                  {job.rowsProcessed != null && job.rowsProcessed > 0 && (
                    <span className="text-muted-foreground">{job.rowsProcessed.toLocaleString()} rows</span>
                  )}
                  {job.durationMs != null && job.durationMs > 0 && (
                    <span className="text-muted-foreground">{(job.durationMs / 1000).toFixed(1)}s</span>
                  )}
                  {job.error && (
                    <span className="text-red-400 truncate max-w-[160px]" title={job.error}>
                      <AlertTriangle className="h-2.5 w-2.5 inline mr-0.5" />{job.error}
                    </span>
                  )}
                </div>
              ))}
              {jobs.length > 3 && (
                <p className="text-[9px] text-muted-foreground text-center pt-0.5">+ {jobs.length - 3} more runs</p>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function DataPipelinesTab() {
  const nav = useNavigate();
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [mappingRules, setMappingRules] = useState<MappingRule[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<CreateForm>({ ...DEFAULT_FORM });
  const [loading, setLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const [pipelinesRes, rulesRes] = await Promise.allSettled([
      etlPipelineService.listPipelines(),
      mappingRuleService.list(),
    ]);
    if (pipelinesRes.status === 'fulfilled') {
      const d = pipelinesRes.value;
      setPipelines(Array.isArray(d) ? d : d?.data ?? []);
    } else {
      setPipelines([]);
    }
    if (rulesRes.status === 'fulfilled') {
      const d = rulesRes.value;
      setMappingRules(Array.isArray(d) ? d : (d as any)?.data ?? []);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    const hasRunning = pipelines.some(p => p.status === 'running');
    if (hasRunning && !pollRef.current) {
      pollRef.current = setInterval(() => {
        etlPipelineService.listPipelines()
          .then((res: any) => setPipelines(Array.isArray(res) ? res : res?.data ?? []))
          .catch(() => {});
      }, 3000);
    } else if (!hasRunning && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [pipelines]);

  const handleCreate = async () => {
    if (!createForm.name) return;
    setCreating(true);
    setCreateError(null);
    const config: ETLPipelineConfig = {
      mappingRuleId: createForm.mappingRuleId,
      sourceType: createForm.sourceType,
      mode: createForm.mode,
      batchSize: createForm.batchSize,
      schedule: createForm.schedule || undefined,
    };
    try {
      const created = await etlPipelineService.createPipeline(createForm.name, config);
      setPipelines(prev => [created, ...prev]);
      setShowCreate(false);
      setCreateForm({ ...DEFAULT_FORM });
      setCreateError(null);
      fetchData();
    } catch (err: any) {
      setCreateError(err?.message || err?.data?.message || 'Failed to create pipeline.');
    } finally {
      setCreating(false);
    }
  };

  const handleCreateFromTemplate = (tpl: ETLPipelineTemplate) => {
    setCreateForm({
      name: tpl.name,
      sourceType: tpl.sourceType,
      mappingRuleId: tpl.defaultConfig.mappingRuleId,
      mode: tpl.defaultConfig.mode,
      batchSize: tpl.defaultConfig.batchSize || 1000,
      schedule: tpl.defaultConfig.schedule || '',
    });
    setShowCreate(true);
  };

  const handleRun = async (pipelineId: string) => {
    try {
      await etlPipelineService.runPipeline(pipelineId);
      nav(`/workspace/automation?journeyId=${pipelineId}`);
    } catch { /* noop */ }
  };

  const handleViewStudio = (pipelineId: string) => {
    nav(`/workspace/automation?journeyId=${pipelineId}`);
  };

  const currentTemplate = ETL_PIPELINE_TEMPLATES.find(t => t.sourceType === createForm.sourceType);
  const targetEntities = currentTemplate?.targetEntities ?? [];
  const matchedRules = mappingRules.filter(r =>
    targetEntities.some(e =>
      r.virtualEntity?.toLowerCase() === e.toLowerCase() ||
      r.name?.toLowerCase().includes(e.toLowerCase().replace(/_/g, ' ')) ||
      r.sourceTable?.toLowerCase().includes(e.toLowerCase())
    )
  );
  const stepsPreview = getStepsForSourceType(createForm.sourceType);

  const existingSourceTypes = new Set(pipelines.map((p: any) => p.config?.sourceType).filter(Boolean));
  const suggestedTemplates = ETL_PIPELINE_TEMPLATES.filter(tpl => !existingSourceTypes.has(tpl.sourceType));

  const totalJobs = pipelines.reduce((n, p) => n + (p.jobCount || 0), 0);
  const runningCount = pipelines.filter(p => p.status === 'running').length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Data Pipelines</h2>
          <p className="text-sm text-muted-foreground">ETL batch pipelines for hydrating the virtual data layer</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />Refresh
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4 mr-1" /> Create Pipeline
          </Button>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center"><Activity className="h-5 w-5 text-blue-400" /></div>
            <div>
              <p className="text-2xl font-bold">{pipelines.length}</p>
              <p className="text-xs text-muted-foreground">Active Pipelines</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center"><CheckCircle className="h-5 w-5 text-green-400" /></div>
            <div>
              <p className="text-2xl font-bold">{pipelines.filter(p => p.status === 'completed').length}</p>
              <p className="text-xs text-muted-foreground">Completed</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center"><Timer className="h-5 w-5 text-amber-400" /></div>
            <div>
              <p className="text-2xl font-bold">{runningCount}</p>
              <p className="text-xs text-muted-foreground">Running Now</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Create form */}
      {showCreate && (
        <Card className="border-dashed border-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">New ETL Pipeline</CardTitle>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => { setShowCreate(false); setCreateForm({ ...DEFAULT_FORM }); setCreateError(null); }}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Source Type</label>
                <select className="w-full h-9 rounded-md border bg-background px-3 text-sm" value={createForm.sourceType}
                  onChange={e => { const st = e.target.value as ETLSourceType; setCreateForm(f => ({ ...f, sourceType: st, name: f.name || SOURCE_TYPE_LABELS[st] + ' ETL' })); }}>
                  <option value="social_listening">Social Listening</option>
                  <option value="file_uploads">File Uploads</option>
                  <option value="google_drive">Google Drive</option>
                  <option value="generic">Generic</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Name</label>
                <Input placeholder="Pipeline name" value={createForm.name} onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Mapping Rule <span className="text-muted-foreground/60">(optional)</span></label>
                <select className="w-full h-9 rounded-md border bg-background px-3 text-sm" value={createForm.mappingRuleId}
                  onChange={e => setCreateForm(f => ({ ...f, mappingRuleId: e.target.value }))}>
                  <option value="">Auto-detect from source</option>
                  {matchedRules.length > 0 && (
                    <optgroup label={`Matched for ${SOURCE_TYPE_LABELS[createForm.sourceType]}`}>
                      {matchedRules.map(r => <option key={r.id} value={r.id}>{r.name} ({r.virtualEntity})</option>)}
                    </optgroup>
                  )}
                  {mappingRules.filter(r => !matchedRules.includes(r)).length > 0 && (
                    <optgroup label="All rules">
                      {mappingRules.filter(r => !matchedRules.includes(r)).map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </optgroup>
                  )}
                </select>
                {targetEntities.length > 0 && (
                  <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                    <span className="text-[9px] text-muted-foreground">Target entities:</span>
                    {targetEntities.map(e => <Badge key={e} variant="outline" className="text-[8px]">{e}</Badge>)}
                  </div>
                )}
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Mode</label>
                <select className="w-full h-9 rounded-md border bg-background px-3 text-sm" value={createForm.mode}
                  onChange={e => setCreateForm(f => ({ ...f, mode: e.target.value as 'full' | 'incremental' }))}>
                  <option value="full">Full</option>
                  <option value="incremental">Incremental</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Batch Size</label>
                <Input type="number" value={createForm.batchSize} onChange={e => setCreateForm(f => ({ ...f, batchSize: Number(e.target.value) }))} />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Schedule (cron, optional)</label>
                <Input placeholder="e.g. 0 */6 * * *" value={createForm.schedule} onChange={e => setCreateForm(f => ({ ...f, schedule: e.target.value }))} />
              </div>
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5 block">Pipeline Steps</label>
              <div className="flex items-center gap-1">
                {stepsPreview.map((step, i) => (
                  <React.Fragment key={step.id}>
                    {i > 0 && <ArrowRight className="h-3 w-3 text-muted-foreground/50 shrink-0" />}
                    <Badge variant="outline" className="text-[9px] shrink-0">{step.name}</Badge>
                  </React.Fragment>
                ))}
              </div>
            </div>
            {createError && (
              <div className="flex items-center gap-2 px-3 py-2 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />{createError}
              </div>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" onClick={() => { setShowCreate(false); setCreateForm({ ...DEFAULT_FORM }); setCreateError(null); }}>Cancel</Button>
              <Button size="sm" onClick={handleCreate} disabled={!createForm.name || creating}>
                {creating ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Plus className="h-4 w-4 mr-1" />}
                {creating ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center py-12 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading pipelines...
        </div>
      ) : (
        <>
          {/* Pipeline cards */}
          {pipelines.length > 0 && (
            <div className="grid gap-4 lg:grid-cols-2">
              {pipelines.map((p: any) => (
                <PipelineCard
                  key={p.id}
                  pipeline={p}
                  mappingRules={mappingRules}
                  onRun={handleRun}
                  onStudio={handleViewStudio}
                />
              ))}
            </div>
          )}

          {pipelines.length === 0 && suggestedTemplates.length === 0 && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <Database className="h-10 w-10 text-muted-foreground mb-3" />
                  <p className="text-sm font-medium">No ETL pipelines configured</p>
                  <p className="text-xs text-muted-foreground mt-1">Create one to start hydrating virtual data.</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Suggested templates */}
          {suggestedTemplates.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-3 flex items-center gap-1.5">
                <Zap className="h-4 w-4 text-amber-400" />Suggested Pipelines
              </h3>
              <div className="grid gap-3 md:grid-cols-3">
                {suggestedTemplates.map(tpl => {
                  const SrcIcon = SOURCE_ICONS[tpl.sourceType];
                  return (
                    <Card key={tpl.id} className="border-dashed hover:border-primary/30 transition-colors">
                      <CardContent className="pt-5 pb-4">
                        <div className="flex items-start gap-3">
                          <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${SOURCE_COLORS[tpl.sourceType]} flex items-center justify-center text-white shrink-0`}>
                            <SrcIcon className="h-4 w-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium">{tpl.name}</p>
                            <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">{tpl.description}</p>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {tpl.targetEntities.map(e => <Badge key={e} variant="outline" className="text-[8px]">{e}</Badge>)}
                            </div>
                          </div>
                        </div>
                        <Button variant="outline" size="sm" className="w-full mt-3" onClick={() => handleCreateFromTemplate(tpl)}>
                          <Plus className="h-3.5 w-3.5 mr-1" /> Set Up
                        </Button>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
