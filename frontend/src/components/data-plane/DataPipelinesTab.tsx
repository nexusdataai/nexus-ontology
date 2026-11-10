import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import {
  Field, InlineError, KeyValues, MetricStrip, Panel, StatusPill, SubHeading, Timeline,
} from '@/components/ds/kit';
import { SystemLogo } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
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

const SOURCE_DESCRIPTIONS: Record<ETLSourceType, string> = {
  social_listening: 'Market signals, social mentions, competitor alerts',
  file_uploads: 'Invoices, lab reports, CSV files',
  google_drive: 'Contracts, sustainability reports',
  generic: 'Custom data pipeline',
};

const SOURCE_LABEL: Record<ETLSourceType, string> = {
  social_listening: 'Social listening',
  file_uploads: 'File uploads',
  google_drive: 'Google Drive',
  generic: 'Generic',
};

const SOURCE_TYPES: ETLSourceType[] = ['social_listening', 'file_uploads', 'google_drive', 'generic'];

/** Radix Select cannot hold an empty value; this stands for "auto-detect". */
const AUTO_RULE = '__auto__';

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

type StepState = 'done' | 'active' | 'pending' | 'failed';

function stepStates(steps: ETLStepDef[], currentStep: string | undefined, status: string): StepState[] {
  const currentIdx = currentStep ? steps.findIndex(s => s.id === currentStep) : -1;
  return steps.map((_, i) => {
    if (status === 'completed') return 'done';
    if (status === 'failed' && i === currentIdx) return 'failed';
    if (status === 'failed' && i < currentIdx) return 'done';
    if (i < currentIdx) return 'done';
    if (i === currentIdx && status === 'running') return 'active';
    return 'pending';
  });
}

const STEP_STATE_LABEL: Record<StepState, string> = { done: 'done', active: 'running', pending: 'waiting', failed: 'failed' };

/** Five small segments in one hue: where the pipeline is in its run. */
function StepSegments({ steps, states }: { steps: ETLStepDef[]; states: StepState[] }) {
  const doneCount = states.filter(s => s === 'done').length;
  return (
    <div
      role="img"
      aria-label={`${doneCount} of ${steps.length} steps done`}
      title={steps.map((s, i) => `${i + 1}. ${s.name}: ${STEP_STATE_LABEL[states[i]]}`).join('\n')}
      className="flex items-center gap-1"
    >
      {steps.map((step, i) => (
        <span
          key={step.id}
          className={cn(
            'h-1.5 w-5 rounded-full',
            states[i] === 'done' && 'bg-primary',
            states[i] === 'active' && 'animate-pulse bg-primary',
            states[i] === 'pending' && 'bg-surface-3',
            states[i] === 'failed' && 'bg-destructive',
          )}
        />
      ))}
    </div>
  );
}

const formatWhen = (value?: string | number | null): string => {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return `${d.toLocaleDateString([], { day: 'numeric', month: 'short' })}, ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
};

function PipelineRow({ pipeline, mappingRules, index, onRun, onStudio }: {
  pipeline: any;
  mappingRules: MappingRule[];
  index: number;
  onRun: (id: string) => void;
  onStudio: (id: string) => void;
}) {
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setJobsLoading(true);
    setJobsError(null);
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
      .catch((e: any) => {
        setJobs([]);
        setJobsError(e?.message || 'Runs could not be loaded.');
      })
      .finally(() => setJobsLoading(false));
  }, [pipeline.id, pipeline.status]);

  const sourceType: ETLSourceType = pipeline.config?.sourceType || 'generic';
  const status: string = pipeline.status ?? 'pending';
  const steps = getStepsForSourceType(sourceType);
  const states = stepStates(steps, pipeline.currentStep, status);
  const rule = mappingRules.find(r => r.id === (pipeline.config?.mappingRuleId ?? pipeline.mappingRuleId));
  const tpl = ETL_PIPELINE_TEMPLATES.find(t => t.sourceType === sourceType);

  const completedJobs = jobs.filter(j => j.status === 'completed');
  const failedJobs = jobs.filter(j => j.status === 'failed');
  const lastRun = jobs[0];
  const totalRows = jobs.reduce((sum, j) => sum + (j.rowsProcessed || 0), 0);

  const activeIdx = states.findIndex(s => s === 'active' || s === 'failed');
  const stepCaption = status === 'completed'
    ? 'All steps done'
    : activeIdx >= 0
      ? `${steps[activeIdx].name} · ${activeIdx + 1} of ${steps.length}`
      : 'Not started';
  const lastRunLabel = formatWhen(lastRun?.startedAt || pipeline.lastRunAt);
  const panelId = `pipeline-${pipeline.id}-details`;

  return (
    <li className="rise border-b border-border last:border-b-0" style={{ '--i': Math.min(index, 8) } as React.CSSProperties}>
      <div className={cn('flex flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3.5 transition-colors sm:px-5', open ? 'bg-surface-2/50' : 'hover:bg-surface-2/40')}>
        <button
          type="button"
          onClick={() => setOpen(o => !o)}
          aria-expanded={open}
          aria-controls={panelId}
          className="flex min-w-0 flex-1 basis-64 items-center gap-3 rounded-md text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Icon name="chevron-right" className={cn('h-3.5 w-3.5 shrink-0 text-subtle-foreground transition-transform duration-200 ease-brand', open && 'rotate-90')} />
          <SystemLogo system={sourceType} tile size="sm" />
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium text-foreground">{pipeline.name}</span>
            <span className="block truncate text-xs text-muted-foreground">{SOURCE_DESCRIPTIONS[sourceType]}</span>
          </span>
        </button>

        <div className="w-[172px] shrink-0">
          <StepSegments steps={steps} states={states} />
          <p className="mt-1.5 truncate text-xs text-muted-foreground">{stepCaption}</p>
        </div>

        <div className="w-[150px] shrink-0 text-xs text-muted-foreground">
          {jobsLoading ? (
            <Skeleton className="h-8 w-28" />
          ) : (
            <>
              <p className="truncate">
                <span className="num text-foreground">{jobs.length}</span> {jobs.length === 1 ? 'run' : 'runs'}
                {jobs.length > 0 && <> · <span className="num">{completedJobs.length}</span> succeeded</>}
              </p>
              <p className="mt-0.5 truncate">{lastRunLabel ? `Last run ${lastRunLabel}` : 'Never run'}</p>
            </>
          )}
        </div>

        <StatusPill status={status} className="w-[88px]" />

        <div className="flex shrink-0 items-center gap-1.5">
          <Button variant="outline" size="sm" onClick={() => onRun(pipeline.id)}>
            <Icon name="play" className="h-3.5 w-3.5" /> Run
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onStudio(pipeline.id)} title="Open in AI Automation">
            Studio <Icon name="arrow-up-right" className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {open && (
        <div id={panelId} className="grid gap-x-10 gap-y-7 border-t border-border bg-surface-2/30 px-4 py-5 sm:px-5 lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)]">
          <div className="min-w-0">
            <SubHeading>Steps</SubHeading>
            <Timeline
              className="mt-3"
              items={steps.map((s, i) => ({
                id: s.id,
                title: s.name,
                description: s.description,
                status: states[i] === 'done' ? 'completed' : states[i] === 'active' ? 'running' : states[i] === 'failed' ? 'failed' : undefined,
              }))}
            />
          </div>

          <div className="min-w-0 space-y-6">
            <div>
              <SubHeading
                action={jobs.length > 5 ? <span className="text-xs text-muted-foreground">Latest 5 of <span className="num">{jobs.length}</span></span> : undefined}
              >
                Recent runs
              </SubHeading>
              {jobsLoading ? (
                <div className="space-y-2" aria-busy="true">
                  {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
                </div>
              ) : jobsError ? (
                <InlineError>{jobsError}</InlineError>
              ) : jobs.length === 0 ? (
                <p className="text-sm text-muted-foreground">No runs recorded yet. Use Run to start the first one.</p>
              ) : (
                <div className="scroll-thin overflow-x-auto rounded-lg border border-border bg-card">
                  <Table className="min-w-[520px]">
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead className="h-9">Status</TableHead>
                        <TableHead className="h-9">Run</TableHead>
                        <TableHead className="h-9">Started</TableHead>
                        <TableHead className="h-9 text-right">Rows</TableHead>
                        <TableHead className="h-9 text-right">Duration</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {jobs.slice(0, 5).map((job: any, i: number) => (
                        <TableRow key={job.id || i}>
                          <TableCell className="py-2">
                            <StatusPill status={job.status || 'pending'} />
                            {job.error && <span className="mt-0.5 block max-w-[220px] truncate text-xs text-destructive" title={job.error}>{job.error}</span>}
                          </TableCell>
                          <TableCell className="py-2 font-mono text-xs text-muted-foreground">{job.id || `Run ${i + 1}`}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-xs text-muted-foreground">{formatWhen(job.startedAt) || '—'}</TableCell>
                          <TableCell className="num py-2 text-right text-xs text-foreground">{job.rowsProcessed > 0 ? job.rowsProcessed.toLocaleString() : '—'}</TableCell>
                          <TableCell className="num py-2 text-right text-xs text-muted-foreground">{job.durationMs > 0 ? `${(job.durationMs / 1000).toFixed(1)} s` : '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>

            <div>
              <SubHeading>Configuration</SubHeading>
              <KeyValues
                columns={2}
                items={[
                  { label: 'Mapping rule', value: rule?.name || 'Auto-detect' },
                  { label: 'Load mode', value: (pipeline.config?.mode || 'full') === 'incremental' ? 'Incremental' : 'Full' },
                  { label: 'Schedule', value: pipeline.config?.schedule || 'Manual', mono: !!pipeline.config?.schedule },
                  { label: 'Loads into', value: tpl ? tpl.targetEntities.join(', ') : 'Entity of the mapping rule' },
                  { label: 'Failed runs', value: <span className="num">{failedJobs.length}</span> },
                  { label: 'Rows processed', value: <span className="num">{totalRows > 0 ? totalRows.toLocaleString() : '—'}</span> },
                ]}
              />
            </div>
          </div>
        </div>
      )}
    </li>
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
  // Presentation only: surfaces a failed list request and the first paint.
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadedOnce, setLoadedOnce] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const [pipelinesRes, rulesRes] = await Promise.allSettled([
      etlPipelineService.listPipelines(),
      mappingRuleService.list(),
    ]);
    if (pipelinesRes.status === 'fulfilled') {
      const d = pipelinesRes.value;
      setPipelines(Array.isArray(d) ? d : d?.data ?? []);
      setLoadError(null);
    } else {
      setPipelines([]);
      setLoadError(pipelinesRes.reason?.message || 'Pipelines could not be loaded.');
    }
    if (rulesRes.status === 'fulfilled') {
      const d = rulesRes.value;
      setMappingRules(Array.isArray(d) ? d : (d as any)?.data ?? []);
    }
    setLoading(false);
    setLoadedOnce(true);
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
      toast.success('Pipeline created');
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
    } catch (e: any) {
      toast.error('The pipeline did not start', { description: e?.message || 'The run request failed.' });
    }
  };

  const handleViewStudio = (pipelineId: string) => {
    nav(`/workspace/automation?journeyId=${pipelineId}`);
  };

  const closeCreate = () => {
    setShowCreate(false);
    setCreateForm({ ...DEFAULT_FORM });
    setCreateError(null);
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
  const otherRules = mappingRules.filter(r => !matchedRules.includes(r));
  const stepsPreview = getStepsForSourceType(createForm.sourceType);

  const existingSourceTypes = new Set(pipelines.map((p: any) => p.config?.sourceType).filter(Boolean));
  const suggestedTemplates = ETL_PIPELINE_TEMPLATES.filter(tpl => !existingSourceTypes.has(tpl.sourceType));

  const totalJobs = pipelines.reduce((n, p) => n + (p.jobCount || 0), 0);
  const runningCount = pipelines.filter(p => p.status === 'running').length;
  const completedCount = pipelines.filter(p => p.status === 'completed').length;
  const firstLoad = !loadedOnce || (loading && pipelines.length === 0 && !loadError);

  return (
    <div className="page">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h2 className="text-xl font-medium tracking-tight text-foreground sm:text-2xl">Data pipelines</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Batch jobs that extract, check and load source data into the virtual data layer.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <Icon name="refresh" className={loading ? 'animate-spin' : undefined} /> Refresh
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Icon name="plus" /> New pipeline
          </Button>
        </div>
      </div>

      <MetricStrip
        className="mt-6"
        items={[
          { label: 'Active pipelines', value: firstLoad ? '—' : pipelines.length },
          { label: 'Completed', value: firstLoad ? '—' : completedCount, hint: 'Last run finished' },
          { label: 'Running now', value: firstLoad ? '—' : runningCount, hint: runningCount > 0 ? 'Updating every 3 s' : 'Idle', tone: runningCount > 0 ? 'info' : 'neutral' },
          { label: 'Runs recorded', value: firstLoad ? '—' : totalJobs.toLocaleString(), hint: 'Across all pipelines' },
        ]}
      />

      {loadError && <InlineError className="mt-6" onRetry={fetchData}>{loadError}</InlineError>}

      <Panel
        className="mt-6"
        flush
        title="Pipelines"
        actions={!firstLoad && pipelines.length > 0 ? <span className="num text-sm text-muted-foreground">{pipelines.length}</span> : undefined}
      >
        {firstLoad ? (
          <div className="divide-y divide-border" aria-busy="true">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-4">
                <Skeleton className="h-8 w-8 rounded-md" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-4 w-48 max-w-full" />
                  <Skeleton className="h-3 w-72 max-w-full" />
                </div>
                <Skeleton className="hidden h-4 w-28 sm:block" />
              </div>
            ))}
          </div>
        ) : pipelines.length === 0 ? (
          <div className="p-4 sm:p-5">
            <EmptyState
              icon="route"
              className="border-0 py-8"
              title="No pipelines yet"
              description={suggestedTemplates.length > 0
                ? 'Create one from scratch, or start from a suggested pipeline below.'
                : 'Create a pipeline to start loading source data into the virtual data layer.'}
              action={<Button size="sm" onClick={() => setShowCreate(true)}><Icon name="plus" /> New pipeline</Button>}
            />
          </div>
        ) : (
          <ul>
            {pipelines.map((p: any, i: number) => (
              <PipelineRow
                key={p.id}
                pipeline={p}
                index={i}
                mappingRules={mappingRules}
                onRun={handleRun}
                onStudio={handleViewStudio}
              />
            ))}
          </ul>
        )}
      </Panel>

      {!firstLoad && suggestedTemplates.length > 0 && (
        <section className="mt-10">
          <h3 className="text-md font-medium text-foreground">Suggested pipelines</h3>
          <p className="mt-0.5 text-sm text-muted-foreground">Sources that have no pipeline yet. Each one opens the form with sensible defaults.</p>
          <ul className="mt-3 border-t border-border">
            {suggestedTemplates.map(tpl => (
              <li key={tpl.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border py-3">
                <SystemLogo system={tpl.sourceType} size="md" />
                <div className="min-w-0 flex-1 basis-64">
                  <p className="text-sm font-medium text-foreground">{tpl.name}</p>
                  <p className="text-sm text-muted-foreground">{tpl.description}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">Loads {tpl.targetEntities.map(e => e.replace(/_/g, ' ')).join(', ')}</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleCreateFromTemplate(tpl)}
                  className="group inline-flex shrink-0 items-center gap-1 rounded-sm text-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-brand-hi"
                >
                  Create <Icon name="arrow-right" className="h-3.5 w-3.5 transition-transform duration-300 ease-brand-out group-hover:translate-x-0.5" />
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Create form */}
      <Dialog open={showCreate} onOpenChange={(o) => { if (!o) closeCreate(); }}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="text-xl font-medium">New pipeline</DialogTitle>
            <DialogDescription>Choose a source and how often it should load into the virtual data layer.</DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Source type">
              <Select
                value={createForm.sourceType}
                onValueChange={(v) => { const st = v as ETLSourceType; setCreateForm(f => ({ ...f, sourceType: st, name: f.name || SOURCE_TYPE_LABELS[st] + ' ETL' })); }}
              >
                <SelectTrigger aria-label="Source type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SOURCE_TYPES.map(st => (
                    <SelectItem key={st} value={st}>{SOURCE_LABEL[st]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Name" htmlFor="pipeline-name">
              <Input id="pipeline-name" placeholder="Pipeline name" value={createForm.name} onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))} />
            </Field>
            <Field
              label="Mapping rule (optional)"
              className="sm:col-span-2"
              hint={targetEntities.length > 0 ? `Loads into ${targetEntities.map(e => e.replace(/_/g, ' ')).join(', ')}.` : undefined}
            >
              <Select
                value={createForm.mappingRuleId || AUTO_RULE}
                onValueChange={(v) => setCreateForm(f => ({ ...f, mappingRuleId: v === AUTO_RULE ? '' : v }))}
              >
                <SelectTrigger aria-label="Mapping rule"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={AUTO_RULE}>Auto-detect from source</SelectItem>
                  {matchedRules.length > 0 && (
                    <SelectGroup>
                      <SelectLabel className="text-xs font-medium text-muted-foreground">Matched for {SOURCE_LABEL[createForm.sourceType]}</SelectLabel>
                      {matchedRules.map(r => <SelectItem key={r.id} value={r.id}>{r.name} ({r.virtualEntity})</SelectItem>)}
                    </SelectGroup>
                  )}
                  {otherRules.length > 0 && (
                    <SelectGroup>
                      <SelectLabel className="text-xs font-medium text-muted-foreground">All rules</SelectLabel>
                      {otherRules.map(r => <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>)}
                    </SelectGroup>
                  )}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Load mode">
              <Select value={createForm.mode} onValueChange={(v) => setCreateForm(f => ({ ...f, mode: v as 'full' | 'incremental' }))}>
                <SelectTrigger aria-label="Load mode"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="full">Full</SelectItem>
                  <SelectItem value="incremental">Incremental</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="Batch size" htmlFor="pipeline-batch">
              <Input id="pipeline-batch" type="number" value={createForm.batchSize} onChange={e => setCreateForm(f => ({ ...f, batchSize: Number(e.target.value) }))} />
            </Field>
            <Field label="Schedule (optional)" htmlFor="pipeline-schedule" className="sm:col-span-2" hint="A cron expression. Leave empty to run the pipeline by hand.">
              <Input id="pipeline-schedule" className="font-mono" placeholder="0 */6 * * *" value={createForm.schedule} onChange={e => setCreateForm(f => ({ ...f, schedule: e.target.value }))} />
            </Field>
          </div>

          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Steps this pipeline runs</p>
            <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-foreground">
              {stepsPreview.map((step, i) => (
                <React.Fragment key={step.id}>
                  {i > 0 && <li aria-hidden="true"><Icon name="arrow-right" className="h-3 w-3 text-subtle-foreground" /></li>}
                  <li title={step.description}>{step.name}</li>
                </React.Fragment>
              ))}
            </ol>
          </div>

          {createError && <InlineError>{createError}</InlineError>}

          <DialogFooter className="gap-2 sm:space-x-0">
            <Button variant="ghost" onClick={closeCreate}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!createForm.name || creating}>
              <Icon name={creating ? 'spinner' : 'plus'} className={creating ? 'animate-spin' : undefined} />
              {creating ? 'Creating…' : 'Create pipeline'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
