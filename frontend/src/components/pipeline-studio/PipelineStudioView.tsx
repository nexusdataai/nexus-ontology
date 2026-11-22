import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
import PipelineStepPalette from './PipelineStepPalette';
import PipelineGraphCanvas, { addPaletteNode, type PipelineCanvasHandle } from './PipelineGraphCanvas';
import PipelineInspector from './PipelineInspector';
import PipelineCopilotPanel from './PipelineCopilotPanel';
import { dataFlowService, type CatalogNodeType, type DataFlowGraph } from '@/services/dataFlowService';
import { defaultGraphForSource, emptyGraph } from './pipelineStudioState';
import { etlPipelineService, type ETLSourceType } from '@/services/etlPipelineService';
import { mappingRuleService, type MappingRule } from '@/services/mappingRuleService';
import { dataPlaneService, type DataPlane } from '@/services/dataPlaneService';
import { nifiProcessorService } from '@/services/nifiProcessorService';

export default function PipelineStudioView({
  journeyId,
  templateSourceType,
  onCreated,
}: {
  journeyId?: string;
  templateSourceType?: ETLSourceType;
  onCreated?: (id: string) => void;
}) {
  const nav = useNavigate();
  const canvasRef = useRef<PipelineCanvasHandle>(null);
  const [catalog, setCatalog] = useState<CatalogNodeType[]>([]);
  const [graph, setGraph] = useState<DataFlowGraph>(emptyGraph());
  const [name, setName] = useState('Untitled pipeline');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [issues, setIssues] = useState<string[]>([]);
  const [mappingRules, setMappingRules] = useState<MappingRule[]>([]);
  const [planes, setPlanes] = useState<DataPlane[]>([]);
  const [savedId, setSavedId] = useState<string | undefined>(journeyId);
  const [nifiExecutionEnabled, setNifiExecutionEnabled] = useState(false);

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
          nifiProcessorService.listProcessors().catch(() => null),
        ]);
        if (cancelled) return;
        setCatalog(cat.nodeTypes ?? []);
        setMappingRules(Array.isArray(rules) ? rules : (rules as any)?.data ?? []);
        setPlanes(Array.isArray(dps) ? dps : []);
        setNifiExecutionEnabled(procMeta?.capabilities?.runtimeExecution === true);
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
    dataFlowService.validate(g).then((v: any) => {
      setIssues((v?.issues ?? []).map((i: any) => i.message));
    }).catch(() => {});
  }, []);

  const patchNode = useCallback((nodeId: string, params: Record<string, unknown>) => {
    const nodes = graph.nodes.map(n => (n.id === nodeId ? { ...n, params: { ...n.params, ...params } } : n));
    onGraphChange({ ...graph, nodes });
  }, [graph, onGraphChange]);

  const persist = async (deploy: boolean) => {
    if (!graph.nodes.length) {
      toast.error('Add a source before saving');
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
      toast.error('Save failed', { description: e?.message || e?.data?.error });
      return null;
    } finally {
      setSaving(false);
    }
  };

  const hasNifi = useMemo(() => graph.nodes.some(n => n.type.startsWith('nifi.')), [graph.nodes]);

  const previewNifi = async () => {
    try {
      const r = await dataFlowService.previewNifiRun(graph);
      toast.success('Flow preview', {
        description: `Terminal flowfiles: ${(r as { terminalCount?: number }).terminalCount ?? 0}`,
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error('Preview failed', { description: msg });
    }
  };

  const runSample = async () => {
    const id = savedId || await persist(false);
    if (!id) return;
    try {
      await etlPipelineService.runPipeline(id, 'studio_sample');
      nav(`/workspace/automation?journeyId=${id}`);
    } catch (e: any) {
      toast.error('Run failed', { description: e?.message });
    }
  };

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
          </p>
        </div>
        {hasNifi && (
          <Button
            variant="outline"
            size="sm"
            onClick={previewNifi}
            disabled={!nifiExecutionEnabled}
            title={nifiExecutionEnabled ? undefined : 'Preview dry-run disabled. Save the pipeline and run the nexus_flow journey stage instead (NEXUS_NIFI_RUNTIME_EXECUTION).'}
          >
            Preview flow run
          </Button>
        )}
        <Button variant="outline" size="sm" onClick={runSample}>
          Test on sample
        </Button>
        <Button variant="outline" size="sm" onClick={() => persist(false)} disabled={saving}>
          Save draft
        </Button>
        <Button size="sm" onClick={() => persist(true)} disabled={saving}>
          Review & deploy
        </Button>
      </header>

      {issues.length > 0 && (
        <InlineError className="mx-4 mt-2 text-xs">{issues.join(' · ')}</InlineError>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[240px_1fr_260px_240px]">
        <PipelineStepPalette
          catalog={catalog}
          sourceType={sourceType}
          dataPlanes={planes}
          onAdd={(type, extra, label) => onGraphChange(addPaletteNode(graph, type, catalog, extra, label))}
        />
        <div
          className="relative min-h-[320px] border-x border-border"
          onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }}
          onDrop={e => {
            e.preventDefault();
            const type = e.dataTransfer.getData('application/pipeline-node');
            if (type) onGraphChange(addPaletteNode(graph, type, catalog));
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
        <div className="hidden overflow-y-auto border-r border-border lg:block">
          <PipelineInspector
            node={selectedNode}
            mappingRules={mappingRules}
            dataPlanes={planes}
            catalog={catalog}
            onPatch={patchNode}
          />
        </div>
        <div className="hidden lg:block">
          <PipelineCopilotPanel
            graph={graph}
            journeyId={savedId}
            onApply={(_, next) => onGraphChange(next)}
          />
        </div>
      </div>
    </div>
  );
}
