import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
import PipelineStepPalette from './PipelineStepPalette';
import PipelineGraphCanvas, { addPaletteNode, type PipelineCanvasHandle } from './PipelineGraphCanvas';
import PipelineInspector from './PipelineInspector';
import PipelineCopilotPanel from './PipelineCopilotPanel';
import PipelineCompileReviewModal, { type CompilePreview } from './PipelineCompileReviewModal';
import PipelineRunConsole from './PipelineRunConsole';
import {
  dataFlowService,
  type CatalogNodeType,
  type DataFlowGraph,
  type DataFlowValidateIssue,
} from '@/services/dataFlowService';
import { defaultGraphForSource, emptyGraph, pipelineStageId } from './pipelineStudioState';
import { etlPipelineService, type ETLSourceType } from '@/services/etlPipelineService';
import { mappingRuleService, type MappingRule } from '@/services/mappingRuleService';
import { dataPlaneService, type DataPlane } from '@/services/dataPlaneService';
import { flowProcessorService } from '@/services/flowProcessorService';

export default function PipelineStudioView({
  journeyId,
  templateSourceType,
  onCreated,
}: {
  journeyId?: string;
  templateSourceType?: ETLSourceType;
  onCreated?: (id: string) => void;
}) {
  const canvasRef = useRef<PipelineCanvasHandle>(null);
  const [catalog, setCatalog] = useState<CatalogNodeType[]>([]);
  const [graph, setGraph] = useState<DataFlowGraph>(emptyGraph());
  const [name, setName] = useState('Untitled pipeline');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validationValid, setValidationValid] = useState(true);
  const [validationIssues, setValidationIssues] = useState<DataFlowValidateIssue[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<DataFlowValidateIssue[]>([]);
  const [mappingRules, setMappingRules] = useState<MappingRule[]>([]);
  const [planes, setPlanes] = useState<DataPlane[]>([]);
  const [savedId, setSavedId] = useState<string | undefined>(journeyId);
  const [flowExecutionEnabled, setFlowExecutionEnabled] = useState(false);
  const [compileOpen, setCompileOpen] = useState(false);
  const [compilePreview, setCompilePreview] = useState<CompilePreview | null>(null);
  const [runJobId, setRunJobId] = useState<string | null>(null);

  const sourceType = useMemo((): ETLSourceType => {
    const src = graph.nodes.find(n => n.type.startsWith('source.') && n.type !== 'source.mapping_rule');
    return (src?.params?.sourceType as ETLSourceType) || 'generic';
  }, [graph]);

  const selectedNode = graph.nodes.find(n => n.id === selectedId) ?? null;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [cat, rules, dps, procMeta] = await Promise.all([
          dataFlowService.getCatalog(),
          mappingRuleService.list(),
          dataPlaneService.list().catch(() => [] as DataPlane[]),
          flowProcessorService.listProcessors().catch(() => null),
        ]);
        if (cancelled) return;
        setCatalog(cat.nodeTypes ?? []);
        setMappingRules(Array.isArray(rules) ? rules : (rules as any)?.data ?? []);
        setPlanes(Array.isArray(dps) ? dps : []);
        setFlowExecutionEnabled(procMeta?.capabilities?.runtimeExecution === true);
        if (journeyId) {
          const journey = await dataFlowService.getJourneyGraph(journeyId);
          if (cancelled) return;
          setSavedId(journeyId);
          let g = journey.graph;
          if (!g?.nodes?.length) {
            const st = (journey.config?.sourceType as ETLSourceType) || 'generic';
            const rule = String(journey.config?.mappingRuleId ?? '');
            g = defaultGraphForSource(st, rule, cat.nodeTypes ?? []);
          }
          setGraph(g);
          setDirty(false);
        } else if (templateSourceType) {
          setGraph(defaultGraphForSource(templateSourceType, '', cat.nodeTypes ?? []));
          setName(`${templateSourceType.replace(/_/g, ' ')} pipeline`);
          setDirty(true);
        } else {
          setGraph(emptyGraph());
          setName('Untitled pipeline');
          setDirty(false);
        }
      } catch (e: any) {
        toast.error('Studio could not load', { description: e?.message });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [journeyId, templateSourceType]);

  const onGraphChange = useCallback((g: DataFlowGraph) => {
    setGraph(g);
    setDirty(true);
    dataFlowService.validate(g).then(v => {
      setValidationValid(v.valid);
      setValidationIssues(v.issues ?? []);
      setValidationWarnings(v.warnings ?? []);
    }).catch(() => {});
  }, []);

  const patchNode = useCallback((nodeId: string, params: Record<string, unknown>) => {
    const nodes = graph.nodes.map(n => (n.id === nodeId ? { ...n, params: { ...n.params, ...params } } : n));
    onGraphChange({ ...graph, nodes });
  }, [graph, onGraphChange]);

  const addNode = useCallback((type: string, extra?: Record<string, unknown>, label?: string) => {
    onGraphChange(addPaletteNode(graph, type, catalog, extra, label, selectedId));
  }, [catalog, graph, onGraphChange, selectedId]);

  const persist = async (deploy: boolean) => {
    if (!graph.nodes.length) {
      toast.error('Add a source before saving');
      return null;
    }
    if (deploy && !validationValid) {
      toast.error('Fix validation errors before deploy');
      return null;
    }
    setSaving(true);
    try {
      if (!savedId) {
        const created: any = await dataFlowService.createPipeline(name.trim() || 'Untitled pipeline', graph, deploy);
        const id = created.journeyId || created.journey_id;
        setSavedId(id);
        setDirty(false);
        onCreated?.(id);
        toast.success(deploy ? 'Pipeline created and deployed' : 'Pipeline created');
        return id;
      }
      await dataFlowService.saveJourneyGraph(
        savedId,
        { ...graph, draftVersion: (graph.draftVersion ?? 1) + 1 },
        deploy,
        name,
      );
      setDirty(false);
      toast.success(deploy ? 'Deployed to production snapshot' : 'Draft saved');
      return savedId;
    } catch (e: any) {
      const issues = e?.data?.issues as { message?: string }[] | undefined;
      toast.error('Save failed', {
        description: issues?.map(i => i.message).join(' · ') || e?.message || e?.data?.error,
      });
      return null;
    } finally {
      setSaving(false);
    }
  };

  const openDeployReview = async () => {
    try {
      const compiled: any = await dataFlowService.compile(graph);
      setCompilePreview({
        valid: compiled.valid,
        enabledSteps: compiled.enabledSteps ?? compiled.enabled_steps,
        compileMode: compiled.compileMode ?? compiled.metadataPatch?.compileMode,
        issues: compiled.issues,
        warnings: compiled.warnings,
      });
      setCompileOpen(true);
    } catch (e: unknown) {
      toast.error('Compile failed', { description: e instanceof Error ? e.message : String(e) });
    }
  };

  const confirmDeploy = async () => {
    setCompileOpen(false);
    await persist(true);
  };

  const hasFlowProcessors = useMemo(
    () => graph.nodes.some(n => n.type.startsWith('nexus.') || n.type.startsWith('nifi.')),
    [graph.nodes],
  );

  const previewFlow = async () => {
    try {
      const r = await dataFlowService.previewFlowRun(graph);
      toast.success('Flow preview', {
        description: `Terminal records: ${(r as { terminalCount?: number }).terminalCount ?? 0}`,
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error('Preview failed', { description: msg });
    }
  };

  const runSample = async () => {
  if (!validationValid) {
      toast.error('Fix validation errors before running a sample');
      return;
    }
    const id = savedId || await persist(false);
    if (!id) return;
    const stageId = pipelineStageId(graph);
    try {
      const job = await etlPipelineService.runPipeline(id, 'studio_sample', stageId);
      const jobId = (job as { jobId?: string }).jobId || (job as { job_id?: string }).job_id;
      if (jobId) setRunJobId(String(jobId));
      toast.success('Sample run started', { description: `Stage ${stageId}` });
    } catch (e: any) {
      toast.error('Run failed', { description: e?.message });
    }
  };

  const inspector = (
    <PipelineInspector
      node={selectedNode}
      mappingRules={mappingRules}
      dataPlanes={planes}
      catalog={catalog}
      onPatch={patchNode}
    />
  );

  if (loading) {
    return <div className="flex h-pane items-center justify-center text-sm text-muted-foreground">Loading studio…</div>;
  }

  return (
    <div className="flex h-pane min-h-0 flex-col overflow-hidden bg-background">
      <header className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-2.5">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Pipelines / Flow Studio</p>
          <Input
            value={name}
            onChange={e => { setName(e.target.value); setDirty(true); }}
            className="mt-1 h-8 max-w-md border-0 bg-transparent px-0 text-sm font-medium shadow-none focus-visible:ring-0"
          />
          <p className="text-xs text-muted-foreground">
            Draft v{graph.draftVersion ?? 1}{dirty ? ' · unsaved changes' : savedId ? '' : ' · not created yet'}
            {!validationValid && ' · has validation errors'}
          </p>
        </div>
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm" className="lg:hidden">
              <Icon name="settings" /> Inspector
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-[min(100vw,360px)] overflow-y-auto p-0">
            <SheetHeader className="px-4 pt-4">
              <SheetTitle>Step parameters</SheetTitle>
            </SheetHeader>
            {inspector}
          </SheetContent>
        </Sheet>
        {hasFlowProcessors && (
          <Button
            variant="outline"
            size="sm"
            onClick={previewFlow}
            disabled={!flowExecutionEnabled}
            title={flowExecutionEnabled ? undefined : 'Preview dry-run disabled on this host.'}
          >
            Preview flow run
          </Button>
        )}
        <Button variant="outline" size="sm" onClick={runSample} disabled={!graph.nodes.length}>
          Test on sample
        </Button>
        <Button variant="outline" size="sm" onClick={() => persist(false)} disabled={saving || !graph.nodes.length}>
          Save draft
        </Button>
        <Button size="sm" onClick={openDeployReview} disabled={saving || !graph.nodes.length || !validationValid}>
          Review & deploy
        </Button>
      </header>

      {validationIssues.length > 0 && (
        <InlineError className="mx-4 mt-2 text-xs">
          {validationIssues.map(i => i.message).join(' · ')}
        </InlineError>
      )}
      {validationWarnings.length > 0 && (
        <div
          role="status"
          className="mx-4 mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200"
        >
          {validationWarnings.map(w => w.message).join(' · ')}
        </div>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[240px_1fr_260px_240px]">
        <PipelineStepPalette
          catalog={catalog}
          sourceType={sourceType}
          dataPlanes={planes}
          onAdd={addNode}
        />
        <div
          className="relative min-h-[320px] border-x border-border"
          onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }}
          onDrop={e => {
            e.preventDefault();
            const type = e.dataTransfer.getData('application/pipeline-node');
            if (type) addNode(type);
          }}
        >
          {graph.nodes.length === 0 && (
            <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
              <p className="max-w-sm text-center text-sm text-muted-foreground">
                Drag sources, transforms and sinks from the left, then Review &amp; deploy to create the job.
              </p>
            </div>
          )}
          <PipelineGraphCanvas
            canvasRef={canvasRef}
            graph={graph}
            catalog={catalog}
            onGraphChange={onGraphChange}
            selectedNodeId={selectedId}
            onSelectNode={setSelectedId}
          />
        </div>
        <div className="hidden overflow-y-auto border-r border-border lg:block">{inspector}</div>
        <div className="hidden lg:block">
          <PipelineCopilotPanel
            graph={graph}
            journeyId={savedId}
            onApply={(_, next) => onGraphChange(next)}
          />
        </div>
      </div>

      <PipelineRunConsole journeyId={savedId} jobId={runJobId} />

      <PipelineCompileReviewModal
        open={compileOpen}
        preview={compilePreview}
        deploying={saving}
        onClose={() => setCompileOpen(false)}
        onConfirmDeploy={confirmDeploy}
      />
    </div>
  );
}