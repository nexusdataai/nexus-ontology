import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Icon } from '@/components/ds/Icon';
import type { DataFlowGraph, ProposedPatch } from '@/services/dataFlowService';
import { dataFlowService } from '@/services/dataFlowService';
import { SubHeading } from '@/components/ds/kit';

export default function PipelineCopilotPanel({
  graph,
  journeyId,
  onApply,
}: {
  graph: DataFlowGraph;
  journeyId?: string;
  onApply: (patches: ProposedPatch[], nextGraph: DataFlowGraph) => void;
}) {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState('');
  const [patches, setPatches] = useState<ProposedPatch[]>([]);
  const [impact, setImpact] = useState<Record<string, unknown>>({});

  const plan = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    try {
      const res: any = await dataFlowService.plan(graph, prompt, journeyId);
      setPatches(res.patches ?? []);
      setExplanation(res.explanation ?? '');
      setImpact(res.impact ?? {});
    } finally {
      setLoading(false);
    }
  };

  const apply = async () => {
    if (!patches.length) return;
    const next = await dataFlowService.applyPatches(graph, patches);
    onApply(patches, next);
    setPatches([]);
    setPrompt('');
    setExplanation('');
  };

  return (
    <aside className="flex h-full flex-col border-l border-border bg-surface-1/50">
      <div className="border-b border-border px-4 py-3">
        <SubHeading action={<Icon name="sparkles" className="h-4 w-4 text-primary" />}>Copilot</SubHeading>
        <p className="mt-1 text-xs text-muted-foreground">Plan graph changes from natural language</p>
      </div>
      <div className="scroll-thin flex-1 space-y-3 overflow-y-auto p-4">
        {explanation && (
          <p className="rounded-md border border-border bg-card p-3 text-xs text-muted-foreground">{explanation}</p>
        )}
        {patches.length > 0 && (
          <ul className="space-y-2">
            {patches.map((p, i) => (
              <li key={i} className="rounded-md border border-dashed border-primary/40 bg-primary/5 px-3 py-2 text-xs font-mono text-foreground">
                {p.summary ?? p.op}
              </li>
            ))}
          </ul>
        )}
        {Object.keys(impact).length > 0 && (
          <div className="text-xs text-muted-foreground">
            {impact.volumeDeltaPct != null && <p>Volume: {String(impact.volumeDeltaPct)}%</p>}
            {impact.latencyDeltaMs != null && <p>Latency: +{String(impact.latencyDeltaMs)} ms</p>}
          </div>
        )}
      </div>
      <div className="border-t border-border p-3 space-y-2">
        <Input
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Describe a change — drop test orders and dedupe order_id"
          onKeyDown={e => e.key === 'Enter' && plan()}
        />
        <div className="flex gap-2">
          <Button size="sm" className="flex-1" onClick={plan} disabled={loading || !prompt.trim()}>
            {loading ? 'Planning…' : 'Plan change'}
          </Button>
          <Button size="sm" variant="outline" disabled={!patches.length} onClick={apply}>
            Apply to draft
          </Button>
        </div>
      </div>
    </aside>
  );
}