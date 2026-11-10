/**
 * AI Copilot: the full-page chat workspace of the Reasoning area.
 *
 * A centred conversation column with the composer pinned at the bottom. While
 * the agent works, its steps show as a compact live trace; when the answer
 * arrives the trace folds into one line ("Used 3 tools, 4.2 s, 5,120 tokens")
 * that opens into a step timeline. On wide screens a right rail lists what
 * the selected answer used.
 *
 * Talks to POST /api/v1/control-plane/agent/stream (server-sent events), the
 * same agent as the docked assistant.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Icon } from '@/components/ds/Icon';
import { LogoMark } from '@/components/ds/Logo';
import { SystemLogo } from '@/components/ds/SystemLogo';
import { CodeBlock, DetailSheet, KeyValues, Meter, StatusPill, SubHeading, Timeline, type TimelineItem } from '@/components/ds/kit';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ types */

interface RetrievalItem {
  source_id: string;
  similarity: number;
  relation_type?: string;
  via_graph?: boolean;
}

interface PipelinePhase {
  step: string;
  description: string;
  duration_ms: number;
  results_count: number;
  top_hits?: { source_id: string; content_type: string; similarity: number }[];
  edges_traversed?: { from: string; to: string; relation: string; hop: number }[];
  neighbors_found?: number;
}

interface RetrievalDetails {
  vector_hits: number;
  graph_hits: number;
  summary: string;
  graph_traversal_summary?: string;
  pipeline_phases?: PipelinePhase[];
  schemas: RetrievalItem[];
  policies: RetrievalItem[];
  workflows: RetrievalItem[];
  integrations: RetrievalItem[];
}

interface AgentStep {
  step: number;
  tool?: string;
  action?: string;
  args?: Record<string, any>;
  result_preview?: string;
  duration_ms?: number;
  blocked?: boolean;
  reason?: string;
  retrieval_details?: RetrievalDetails;
}

interface AgentResponse {
  answer: string;
  intent: string;
  session_id: string;
  steps: AgentStep[];
  total_steps: number;
  total_tokens: number;
  policy_violations: string[];
  note?: string;
}

interface StreamEvent {
  type: string;
  message?: string;
  intent?: string;
  step?: number;
  max_steps?: number;
  tool?: string;
  args?: Record<string, any>;
  duration_ms?: number;
  preview?: string;
  reason?: string;
  data?: AgentResponse;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  agentData?: AgentResponse;
  loading?: boolean;
  error?: string;
  streamEvents?: StreamEvent[];
}

/* ---------------------------------------------------------------- content */

const EXAMPLE_GROUPS: { title: string; questions: string[] }[] = [
  {
    title: 'Data and ownership',
    questions: [
      'Which system is the source of truth for customer credit limit?',
      'If I deactivate a customer in Salesforce, what is impacted in Oracle ERP?',
    ],
  },
  {
    title: 'Policies and approvals',
    questions: [
      'What happens if I increase a customer credit limit by more than 15%?',
      'Who is authorized to override customer credit block?',
    ],
  },
  {
    title: 'Workflows',
    questions: [
      'What workflows are triggered when a new enterprise customer is created?',
      'What steps are required to fully onboard a new B2B customer across systems?',
    ],
  },
];

/* ---------------------------------------------------------------- helpers */

const words = (s?: string) => String(s || '').replace(/_/g, ' ');
const prettyId = (id: string) => id.replace(/_V1_0$/, '').replace(/_/g, ' ').toLowerCase();
const seconds = (ms?: number) => (ms == null ? '' : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`);
const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

function traceTotals(data: AgentResponse) {
  const steps = data.steps || [];
  return {
    tools: steps.filter(s => s.tool && !s.blocked).length,
    blocked: steps.filter(s => s.blocked).length,
    ms: steps.reduce((sum, s) => sum + (s.duration_ms || 0), 0),
  };
}

/** One row per tool the agent has called so far, built from the live events. */
function liveCalls(events: StreamEvent[]) {
  const calls: { tool: string; state: 'running' | 'done' | 'blocked'; ms?: number; reason?: string }[] = [];
  for (const e of events) {
    if (!e.tool) continue;
    if (e.type === 'tool_call') calls.push({ tool: e.tool, state: 'running' });
    else if (e.type === 'tool_result' || e.type === 'tool_blocked') {
      const open = [...calls].reverse().find(c => c.tool === e.tool && c.state === 'running');
      const patch = e.type === 'tool_result' ? { state: 'done' as const, ms: e.duration_ms } : { state: 'blocked' as const, reason: e.reason };
      if (open) Object.assign(open, patch);
      else calls.push({ tool: e.tool, ...patch });
    }
  }
  return calls;
}

function liveStatus(events: StreamEvent[]): string {
  const last = events[events.length - 1];
  if (!last) return 'Connecting';
  if (last.type === 'status') return last.message || 'Working';
  if (last.type === 'intent') return `Intent: ${words(last.intent)}`;
  if (last.type === 'step_start') return `Reasoning, step ${last.step} of ${last.max_steps}`;
  if (last.type === 'tool_call') return `Running ${last.tool}`;
  if (last.type === 'tool_result') return `Reading the result of ${last.tool}`;
  if (last.type === 'tool_blocked') return `A policy blocked ${last.tool}`;
  return 'Thinking';
}

/** What the answer drew on, from the steps the stream returned. */
function usedBy(data: AgentResponse) {
  const collect = (key: 'schemas' | 'policies' | 'workflows' | 'integrations') => {
    const best = new Map<string, RetrievalItem>();
    for (const s of data.steps || []) {
      for (const item of s.retrieval_details?.[key] || []) {
        const prev = best.get(item.source_id);
        if (!prev || item.similarity > prev.similarity) best.set(item.source_id, item);
      }
    }
    return [...best.values()].sort((a, b) => b.similarity - a.similarity);
  };
  return {
    tools: (data.steps || []).filter(s => s.tool),
    entities: collect('schemas'),
    policies: collect('policies'),
    workflows: collect('workflows'),
    integrations: collect('integrations'),
  };
}

/* --------------------------------------------------------------- markdown */

const MD =
  'text-base leading-7 text-foreground [&_p]:mb-3 [&_p:last-child]:mb-0 [&_strong]:font-medium ' +
  '[&_ul]:mb-3 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5 [&_ol]:mb-3 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5 [&_li]:marker:text-subtle-foreground ' +
  '[&_code]:rounded [&_code]:bg-surface-2 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs ' +
  '[&_pre]:mb-3 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:border [&_pre]:border-border [&_pre]:bg-surface-2/70 [&_pre]:p-3 [&_pre_code]:bg-transparent [&_pre_code]:p-0 ' +
  '[&_a]:text-primary [&_a]:underline [&_a]:underline-offset-4 dark:[&_a]:text-brand-hi ' +
  '[&_h1]:mb-2 [&_h1]:text-md [&_h1]:font-medium [&_h2]:mb-2 [&_h2]:text-md [&_h2]:font-medium [&_h3]:mb-1.5 [&_h3]:font-medium ' +
  '[&_blockquote]:mb-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border-strong [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground ' +
  '[&_table]:mb-3 [&_table]:w-full [&_table]:text-sm [&_th]:border-b [&_th]:border-border [&_th]:py-1.5 [&_th]:pr-3 [&_th]:text-left [&_th]:font-medium [&_td]:border-b [&_td]:border-border [&_td]:py-1.5 [&_td]:pr-3';

function Markdown({ children }: { children: string }) {
  return <div className={MD}><ReactMarkdown>{children}</ReactMarkdown></div>;
}

/** Types the answer out a few characters per frame. Skipped for reduced motion. */
function Reveal({ text, onDone, onTick }: { text: string; onDone: () => void; onTick?: () => void }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) { setN(text.length); onDone(); return; }
    let i = 0;
    const stepSize = Math.max(2, Math.ceil(text.length / 110));
    const t = window.setInterval(() => {
      i = Math.min(text.length, i + stepSize);
      setN(i);
      onTick?.();
      if (i >= text.length) { window.clearInterval(t); onDone(); }
    }, 16);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);
  return <Markdown>{text.slice(0, n)}</Markdown>;
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden="true">
      {[0, 1, 2].map(i => (
        <span key={i} className="h-1.5 w-1.5 rounded-full bg-primary dark:bg-brand-hi" style={{ animation: 'typing-dot 1.1s ease-in-out infinite', animationDelay: `${i * 140}ms` }} />
      ))}
    </span>
  );
}

/* -------------------------------------------------------------- live trace */

function LiveTrace({ events }: { events: StreamEvent[] }) {
  const calls = liveCalls(events);
  const maxSteps = events.find(e => e.max_steps)?.max_steps || 10;
  const currentStep = events.filter(e => e.type === 'step_start').length;
  const status = liveStatus(events);
  return (
    <div aria-live="polite">
      <div className="flex min-h-7 items-center gap-2.5 text-sm text-muted-foreground">
        <TypingDots />
        <span key={status} className="min-w-0 animate-fade-in truncate">{status}</span>
        {currentStep > 0 && <span className="num ml-auto shrink-0 text-xs text-subtle-foreground">Step {currentStep} of {maxSteps}</span>}
      </div>
      {calls.length > 0 && (
        <ol className="mt-2 border-l border-border pl-3.5">
          {calls.map((c, i) => (
            <li key={i} className="animate-fade-up py-1 text-sm">
              <div className="flex items-center gap-2.5">
                {c.state === 'running'
                  ? <span className="dot-live shrink-0 text-primary dark:text-brand-hi" aria-hidden="true" />
                  : <span className={cn('h-2 w-2 shrink-0 rounded-full', c.state === 'blocked' ? 'bg-warning' : 'bg-success')} aria-hidden="true" />}
                <span className="min-w-0 truncate font-mono text-xs text-foreground">{c.tool}</span>
                <span className="num ml-auto shrink-0 text-xs text-muted-foreground">
                  {c.state === 'running' ? 'Running' : c.state === 'blocked' ? 'Blocked by policy' : seconds(c.ms) || 'Done'}
                </span>
              </div>
              {c.state === 'blocked' && c.reason && <p className="mt-0.5 pl-[18px] text-xs text-muted-foreground">{c.reason}</p>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

/* ------------------------------------------------------------- full trace */

function SimilarityMeter({ value, i = 0 }: { value: number; i?: number }) {
  const pct = Math.round(value * 100);
  return (
    <span className="flex w-24 shrink-0 items-center gap-2">
      <span className="grow-x block flex-1" style={{ ['--i' as any]: i }}><Meter value={pct} label="Similarity" /></span>
      <span className="num w-8 text-right text-xs text-muted-foreground">{pct}%</span>
    </span>
  );
}

function RetrievalGroup({ title, items }: { title: string; items: RetrievalItem[] }) {
  if (!items.length) return null;
  const viaGraph = items.filter(i => i.via_graph).length;
  return (
    <div className="mt-3">
      <p className="text-xs text-muted-foreground">
        <span className="font-medium text-foreground">{title}</span> <span className="num">{items.length}</span>
        {viaGraph > 0 && <span>, {viaGraph} through the graph</span>}
      </p>
      <ul className="mt-1 divide-y divide-border">
        {items.map((item, j) => (
          <li key={j} className="flex items-center gap-3 py-1.5">
            <span className="min-w-0 flex-1 truncate text-sm text-foreground" title={item.source_id}>{prettyId(item.source_id)}</span>
            {(item.relation_type || item.via_graph) && <span className="shrink-0 text-xs text-muted-foreground">{item.relation_type ? words(item.relation_type) : 'via graph'}</span>}
            <SimilarityMeter value={item.similarity} i={j} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function RetrievalBlock({ details }: { details: RetrievalDetails }) {
  const [showPhases, setShowPhases] = useState(false);
  const phases = details.pipeline_phases || [];
  return (
    <div>
      <p className="text-sm text-foreground">{details.summary}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">
        <span className="num">{details.vector_hits}</span> by vector search, <span className="num">{details.graph_hits}</span> through the graph
        {details.graph_traversal_summary && details.graph_hits > 0 && <span>. {details.graph_traversal_summary}</span>}
      </p>
      <RetrievalGroup title="Entities" items={details.schemas} />
      <RetrievalGroup title="Policies" items={details.policies} />
      <RetrievalGroup title="Workflows" items={details.workflows} />
      <RetrievalGroup title="Integrations" items={details.integrations} />
      {phases.length > 0 && (
        <div className="mt-3">
          <button type="button" onClick={() => setShowPhases(v => !v)} aria-expanded={showPhases} className="inline-flex items-center gap-1 rounded text-xs font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-brand-hi">
            {showPhases ? 'Hide' : 'Show'} retrieval pipeline
            <Icon name="chevron-down" className={cn('h-3 w-3 transition-transform duration-200', showPhases && 'rotate-180')} />
          </button>
          {showPhases && (
            <ol className="mt-2 space-y-3 border-l border-border pl-3.5">
              {phases.map((phase, i) => (
                <li key={i} className="rise" style={{ ['--i' as any]: i }}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-sm font-medium text-foreground">{i + 1}. {phase.step}</span>
                    <span className="num shrink-0 text-xs text-muted-foreground">{seconds(phase.duration_ms)}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{phase.description}</p>
                  {(phase.top_hits || []).map((h, j) => (
                    <div key={j} className="mt-1 flex items-center gap-3">
                      <span className="min-w-0 flex-1 truncate text-xs text-foreground">{prettyId(h.source_id)}</span>
                      <span className="shrink-0 text-xs text-muted-foreground">{h.content_type.replace('onto_', '')}</span>
                      <SimilarityMeter value={h.similarity} i={j} />
                    </div>
                  ))}
                  {(phase.edges_traversed || []).map((e, j) => (
                    <div key={j} className="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs">
                      <span className="text-foreground">{prettyId(e.from)}</span>
                      <span className="text-muted-foreground">{words(e.relation)}</span>
                      <Icon name="arrow-right" className="h-3 w-3 text-subtle-foreground" />
                      <span className="text-foreground">{prettyId(e.to)}</span>
                    </div>
                  ))}
                  {phase.neighbors_found != null && (
                    <p className="mt-1 text-xs text-muted-foreground">{phase.neighbors_found} neighbours found, {phase.results_count} documents retrieved</p>
                  )}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

function TraceStep({ s }: { s: AgentStep }) {
  const isFinal = !s.tool && !s.blocked;
  const args = s.args && Object.keys(s.args).length > 0 ? JSON.stringify(s.args, null, 2) : '';
  return (
    <li className="relative flex gap-3.5 pb-6 last:pb-0">
      <span className="absolute left-[13px] top-7 h-[calc(100%-28px)] w-px bg-border-strong [li:last-child>&]:hidden" aria-hidden="true" />
      <span className={cn(
        'num relative mt-0.5 flex h-[27px] w-[27px] shrink-0 items-center justify-center rounded-full border text-xs font-medium',
        s.blocked ? 'border-warning/40 bg-warning/10 text-warning' : isFinal ? 'border-success/40 bg-success/10 text-success' : 'border-border-strong bg-card text-muted-foreground',
      )}>
        {isFinal ? <Icon name="check" className="h-3 w-3" /> : s.step}
      </span>
      <div className="min-w-0 flex-1 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          {isFinal
            ? <span className="text-sm font-medium text-foreground">Final answer</span>
            : <span className="min-w-0 truncate font-mono text-sm text-foreground" title={s.tool}>{s.tool}</span>}
          <span className="flex items-center gap-3 text-xs text-muted-foreground">
            {s.blocked && <StatusPill tone="warning">Blocked by policy</StatusPill>}
            {s.duration_ms != null && <span className="num">{seconds(s.duration_ms)}</span>}
          </span>
        </div>
        {s.blocked && s.reason && <p className="text-sm text-muted-foreground">{s.reason}</p>}
        {!isFinal && !s.blocked && args && (
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Arguments</p>
            <CodeBlock maxHeight={160}>{args}</CodeBlock>
          </div>
        )}
        {s.retrieval_details && (
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Retrieved knowledge</p>
            <RetrievalBlock details={s.retrieval_details} />
          </div>
        )}
        {!s.retrieval_details && s.result_preview && (
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Result preview</p>
            <CodeBlock maxHeight={200} wrap>{s.result_preview}</CodeBlock>
          </div>
        )}
        {isFinal && !s.result_preview && <p className="text-sm text-muted-foreground">The agent wrote the answer and finished.</p>}
      </div>
    </li>
  );
}

function streamDetail(e: StreamEvent): string {
  if (e.type === 'status') return e.message || '';
  if (e.type === 'intent') return `Intent is ${words(e.intent)}`;
  if (e.type === 'step_start') return `Step ${e.step} of ${e.max_steps}`;
  if (e.type === 'tool_call') return `${e.tool}(${e.args ? JSON.stringify(e.args).slice(0, 80) : ''})`;
  if (e.type === 'tool_result') return `${e.tool}${e.duration_ms != null ? `, ${seconds(e.duration_ms)}` : ''}`;
  if (e.type === 'tool_blocked') return `${e.tool} blocked: ${e.reason}`;
  if (e.type === 'answer') return 'Final answer delivered';
  if (e.type === 'cache_hit') return 'Served from cache';
  if (e.type === 'error') return e.message || 'Unknown error';
  return '';
}

function StreamLog({ events }: { events: StreamEvent[] }) {
  if (!events.length) return <p className="py-8 text-center text-sm text-muted-foreground">No stream events were captured for this answer.</p>;
  return (
    <ol className="divide-y divide-border">
      {events.map((e, i) => (
        <li key={i} className="grid grid-cols-[28px_104px_minmax(0,1fr)] items-baseline gap-x-3 py-2 text-sm">
          <span className="num text-xs text-subtle-foreground">{i + 1}</span>
          <span className={cn('font-mono text-xs', e.type === 'error' ? 'text-destructive' : e.type === 'tool_blocked' ? 'text-warning' : 'text-foreground')}>{e.type}</span>
          <span className="min-w-0 break-words text-muted-foreground">
            {streamDetail(e)}
            {e.type === 'tool_result' && e.preview && <span className="mt-0.5 block truncate font-mono text-xs text-subtle-foreground" title={e.preview}>{e.preview.slice(0, 90)}</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}

function TraceSheet({ message, onClose }: { message: Message | null; onClose: () => void }) {
  const [tab, setTab] = useState<'steps' | 'stream'>('steps');
  const data = message?.agentData;
  useEffect(() => { setTab('steps'); }, [message?.id]);
  const totals = data ? traceTotals(data) : null;
  const streamCount = message?.streamEvents?.length || 0;
  return (
    <DetailSheet
      open={!!data}
      onOpenChange={(o) => { if (!o) onClose(); }}
      wide
      title="Reasoning trace"
      description={data && totals ? `${plural(data.steps.length, 'step')}, ${plural(totals.tools, 'tool call')}${totals.blocked ? `, ${totals.blocked} blocked by policy` : ''}, ${data.total_tokens.toLocaleString()} tokens` : undefined}
    >
      {data && (
        <Tabs value={tab} onValueChange={(v) => setTab(v as 'steps' | 'stream')}>
          <TabsList variant="line" className="-mt-2 mb-5">
            <TabsTrigger value="steps">Steps <span className="num text-xs font-normal text-muted-foreground">{data.steps.length}</span></TabsTrigger>
            <TabsTrigger value="stream" disabled={streamCount === 0}>Stream events <span className="num text-xs font-normal text-muted-foreground">{streamCount}</span></TabsTrigger>
          </TabsList>
          <TabsContent value="steps" className="mt-0">
            <ol>{data.steps.map((s, i) => <TraceStep key={i} s={s} />)}</ol>
            <div className="mt-6 border-t border-border pt-4">
              <KeyValues items={[
                { label: 'Intent', value: <span className="first-letter:uppercase">{words(data.intent)}</span> },
                { label: 'Session', value: data.session_id, mono: true },
              ]} />
            </div>
          </TabsContent>
          <TabsContent value="stream" className="mt-0">
            <StreamLog events={message?.streamEvents || []} />
          </TabsContent>
        </Tabs>
      )}
    </DetailSheet>
  );
}

/* ----------------------------------------------------------- answer footer */

function AnswerFooter({ msg, selected, onSelect, onOpenTrace }: { msg: Message; selected: boolean; onSelect: () => void; onOpenTrace: () => void }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const data = msg.agentData;
  const totals = data ? traceTotals(data) : null;

  const copy = () => {
    navigator.clipboard?.writeText(msg.content).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    }).catch(() => {});
  };

  const items: TimelineItem[] = (data?.steps || []).map((s, i) => ({
    id: i,
    title: s.tool ? <span className="font-mono text-xs">{s.tool}</span> : 'Final answer',
    status: s.blocked ? 'warning' : 'completed',
    meta: s.blocked ? 'Blocked by policy' : seconds(s.duration_ms),
    description: s.blocked ? s.reason : s.result_preview ? s.result_preview.split('\n')[0] : undefined,
  }));

  const quiet = 'inline-flex h-7 items-center gap-1.5 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

  return (
    <div className="mt-3 animate-fade-in">
      {data && data.policy_violations.length > 0 && (
        <div role="note" className="mb-3 flex items-start gap-2.5 rounded-lg border border-warning/25 bg-warning/10 px-3 py-2.5 text-sm">
          <Icon name="shield-check" className="mt-0.5 shrink-0 text-warning" />
          <div className="min-w-0">
            <p className="font-medium text-foreground">{data.policy_violations.length === 1 ? 'A policy stopped one action' : `Policies stopped ${data.policy_violations.length} actions`}</p>
            <ul className="mt-0.5 space-y-0.5 text-muted-foreground">
              {data.policy_violations.map((v, i) => <li key={i}>{v}</li>)}
            </ul>
          </div>
        </div>
      )}
      {data?.note && <p className="mb-2 text-xs text-muted-foreground">{data.note}</p>}

      <div className="-ml-2 flex flex-wrap items-center gap-x-1 gap-y-1">
        {data && totals && data.steps.length > 0 && (
          <button
            type="button"
            onClick={() => { setOpen(o => !o); onSelect(); }}
            aria-expanded={open}
            className={cn(quiet, selected && 'xl:text-foreground')}
          >
            <Icon name="route" className="h-3.5 w-3.5" />
            <span>
              Used {plural(totals.tools, 'tool')}
              {totals.blocked > 0 && <span className="text-warning">, {totals.blocked} blocked</span>}
              <span className="num"> · {seconds(totals.ms)} · {data.total_tokens.toLocaleString()} tokens</span>
            </span>
            <Icon name="chevron-down" className={cn('h-3 w-3 transition-transform duration-200', open && 'rotate-180')} />
          </button>
        )}
        {data && data.steps.length === 0 && (
          <span className="num px-2 text-xs text-muted-foreground">{data.total_tokens.toLocaleString()} tokens</span>
        )}
        {!msg.error && (
          <button type="button" onClick={copy} className={quiet} aria-label="Copy the answer">
            <Icon name={copied ? 'check' : 'copy'} className="h-3.5 w-3.5" /> {copied ? 'Copied' : 'Copy'}
          </button>
        )}
      </div>

      {open && data && (
        <div className="mt-3 rounded-xl border border-border bg-card p-4">
          <Timeline items={items} />
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3 text-xs text-muted-foreground">
            <span>Intent: {words(data.intent)}</span>
            <button type="button" onClick={onOpenTrace} className="inline-flex items-center gap-1 rounded font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-brand-hi">
              Open full trace <Icon name="arrow-right" className="h-3 w-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------- right rail */

function RailList({ title, items, withLogo }: { title: string; items: RetrievalItem[]; withLogo?: boolean }) {
  if (!items.length) return null;
  return (
    <section className="mt-6">
      <SubHeading action={<span className="num text-xs text-muted-foreground">{items.length}</span>}>{title}</SubHeading>
      <ul className="divide-y divide-border">
        {items.slice(0, 8).map((item, i) => (
          <li key={item.source_id} className="rise flex items-center gap-2.5 py-2" style={{ ['--i' as any]: i }}>
            {withLogo && <SystemLogo system={item.source_id} size="xs" />}
            <span className="min-w-0 flex-1 truncate text-sm text-foreground" title={item.source_id}>{prettyId(item.source_id)}</span>
            <span className="num shrink-0 text-xs text-muted-foreground">{Math.round(item.similarity * 100)}%</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AnswerRail({ message, onOpenTrace }: { message: Message | null; onOpenTrace: () => void }) {
  const data = message?.agentData;
  const used = useMemo(() => (data ? usedBy(data) : null), [data]);
  const totals = data ? traceTotals(data) : null;
  return (
    <aside className="scroll-thin hidden min-h-0 overflow-y-auto border-l border-border bg-sidebar/40 px-5 pb-24 pt-5 xl:block" aria-label="What this answer used">
      <h2 className="text-md font-medium text-foreground">This answer used</h2>
      {!data || !used || !totals ? (
        <p className="mt-2 text-sm text-muted-foreground">
          {message?.loading ? 'The agent is still working. Tools, entities and policies appear here when the answer arrives.' : 'The tools, entities and policies behind an answer appear here.'}
        </p>
      ) : (
        <div key={message!.id}>
          <p className="mt-1 text-sm text-muted-foreground">
            {plural(totals.tools, 'tool call')} in <span className="num">{seconds(totals.ms)}</span>
            {totals.blocked > 0 && <span>, {totals.blocked} blocked by policy</span>}.
          </p>

          {used.tools.length > 0 && (
            <section className="mt-5">
              <SubHeading>Tools</SubHeading>
              <ul className="divide-y divide-border">
                {used.tools.map((s, i) => (
                  <li key={i} className="rise flex items-center gap-2.5 py-2" style={{ ['--i' as any]: i }}>
                    <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', s.blocked ? 'bg-warning' : 'bg-success')} aria-hidden="true" />
                    <span className="min-w-0 flex-1 truncate font-mono text-xs text-foreground" title={s.tool}>{s.tool}</span>
                    <span className="num shrink-0 text-xs text-muted-foreground">{s.blocked ? 'Blocked' : seconds(s.duration_ms)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <RailList title="Entities" items={used.entities} withLogo />
          <RailList title="Policies" items={used.policies} />
          <RailList title="Workflows" items={used.workflows} />
          <RailList title="Integrations" items={used.integrations} />

          {data.policy_violations.length > 0 && (
            <section className="mt-6">
              <SubHeading>Policy checks</SubHeading>
              <ul className="space-y-2">
                {data.policy_violations.map((v, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <Icon name="shield-check" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
                    <span>{v}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="mt-6">
            <SubHeading>Run</SubHeading>
            <KeyValues items={[
              { label: 'Intent', value: <span className="first-letter:uppercase">{words(data.intent)}</span> },
              { label: 'Steps', value: <span className="num">{data.steps.length}</span> },
              { label: 'Tokens', value: <span className="num">{data.total_tokens.toLocaleString()}</span> },
              { label: 'Session', value: data.session_id, mono: true },
            ]} />
          </section>

          <Button variant="outline" size="sm" className="mt-5 w-full" onClick={onOpenTrace}>
            Open full trace
          </Button>
        </div>
      )}
    </aside>
  );
}

/* ---------------------------------------------------------------- workspace */

export default function CopilotWorkspace() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  // Local view state: which answer is typing out, which one the rail shows,
  // and which one has its full trace open.
  const [revealId, setRevealId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [traceId, setTraceId] = useState<string | null>(null);

  const toBottom = (smooth = true) => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  };

  useEffect(() => { toBottom(); }, [messages]);

  // Grow the composer with its content.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = '0px';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [input]);

  const sendMessage = async (text?: string) => {
    const question = (text || input).trim();
    if (!question || loading) return;
    setInput('');
    const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);
    const userMsg: Message = { id: uid(), role: 'user', content: question, timestamp: new Date() };
    const botId = uid();
    const botMsg: Message = { id: botId, role: 'assistant', content: '', timestamp: new Date(), loading: true, streamEvents: [] };
    setMessages(prev => [...prev, userMsg, botMsg]);
    setSelectedId(botId);
    setLoading(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const updateBot = (patch: Partial<Message>) =>
      setMessages(prev => prev.map(m => m.id === botId ? { ...m, ...patch } : m));

    try {
      const resp = await fetch('/api/v1/control-plane/agent/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        credentials: 'include',
        body: JSON.stringify({ question, max_steps: 10 }),
        signal: ctrl.signal,
      });

      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const events: StreamEvent[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const evt: StreamEvent = JSON.parse(line.slice(6));
            events.push(evt);
            if (evt.type === 'answer' && evt.data) {
              setRevealId(botId);
              updateBot({ content: evt.data.answer, agentData: evt.data, loading: false, streamEvents: [...events] });
            } else if (evt.type === 'cache_hit' && evt.data) {
              setRevealId(botId);
              updateBot({ content: evt.data.answer, agentData: evt.data, loading: false, streamEvents: [...events] });
            } else if (evt.type === 'error') {
              updateBot({ content: 'Failed to get response.', loading: false, error: evt.message, streamEvents: [...events] });
            } else {
              updateBot({ streamEvents: [...events] });
            }
          } catch { /* skip malformed */ }
        }
      }
      setMessages(prev => {
        const m = prev.find(x => x.id === botId);
        if (m?.loading) return prev.map(x => x.id === botId ? { ...x, content: 'No response received.', loading: false } : x);
        return prev;
      });
    } catch (err: any) {
      if (err?.name === 'AbortError') updateBot({ content: 'Stopped.', loading: false });
      else updateBot({ content: 'Failed to get response.', loading: false, error: err.message || 'Stream error' });
    } finally {
      setLoading(false);
      abortRef.current = null;
      inputRef.current?.focus();
    }
  };

  const stop = () => abortRef.current?.abort();
  const newChat = () => {
    stop();
    setMessages([]);
    setInput('');
    setRevealId(null);
    setSelectedId(null);
    setTraceId(null);
    inputRef.current?.focus();
  };

  const hasChat = messages.length > 0;
  const selected = messages.find(m => m.id === selectedId && m.role === 'assistant')
    || [...messages].reverse().find(m => m.role === 'assistant')
    || null;
  const traceMessage = messages.find(m => m.id === traceId) || null;

  return (
    <div className={cn('grid h-pane', hasChat && 'xl:grid-cols-[minmax(0,1fr)_320px]')}>
      <div className="flex min-h-0 min-w-0 flex-col">
        {hasChat && (
          <div className="flex h-11 shrink-0 items-center justify-between gap-3 border-b border-border px-4 sm:px-6">
            <p className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
              {loading ? <span className="dot-live shrink-0 text-primary dark:text-brand-hi" aria-hidden="true" /> : <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-success" aria-hidden="true" />}
              <span className="truncate">{loading ? 'The agent is working' : `${plural(messages.filter(m => m.role === 'user').length, 'question')} in this chat`}</span>
            </p>
            <Button variant="ghost" size="sm" onClick={newChat}>
              <Icon name="edit" /> New chat
            </Button>
          </div>
        )}

        <div ref={scrollRef} className="scroll-thin min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-[760px] flex-col px-4 sm:px-6">
            {!hasChat ? (
              <div className="flex flex-1 flex-col justify-center py-10">
                <LogoMark className="h-9 w-9 [--logo-bg:var(--background)]" />
                <h2 className="mt-5 text-2xl font-medium tracking-tight text-foreground">Ask about your enterprise</h2>
                <p className="mt-2 max-w-xl text-base text-muted-foreground">
                  Schemas, policies, workflows and how systems depend on each other. Every answer shows the tools the agent called and the policies it checked.
                </p>
                <div className="mt-9 grid gap-x-6 gap-y-7 md:grid-cols-3">
                  {EXAMPLE_GROUPS.map((group, g) => (
                    <section key={group.title}>
                      <h3 className="text-sm font-medium text-foreground">{group.title}</h3>
                      <div className="mt-2.5 space-y-2">
                        {group.questions.map((q, i) => (
                          <button
                            key={q}
                            type="button"
                            onClick={() => sendMessage(q)}
                            style={{ ['--i' as any]: g * 2 + i }}
                            className="rise group flex w-full items-start justify-between gap-3 rounded-xl border border-border bg-card px-3.5 py-3 text-left text-sm text-muted-foreground transition-[transform,border-color,color,box-shadow] duration-200 ease-brand hover:-translate-y-px hover:border-brand/50 hover:text-foreground hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            <span>{q}</span>
                            <Icon name="arrow-up-right" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-subtle-foreground transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground" />
                          </button>
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              </div>
            ) : (
              <ul className="space-y-8 py-7">
                {messages.map(msg => (
                  <li key={msg.id} className="animate-fade-up">
                    {msg.role === 'user' ? (
                      <div className="flex justify-end">
                        <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-base text-primary-foreground">{msg.content}</p>
                      </div>
                    ) : (
                      <div className="flex gap-3.5">
                        <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-card">
                          <LogoMark className="h-4 w-4 [--logo-bg:var(--card)]" />
                        </span>
                        <div className="min-w-0 flex-1">
                          {msg.loading ? (
                            <LiveTrace events={msg.streamEvents || []} />
                          ) : msg.error ? (
                            <>
                              <p className="flex items-start gap-2 text-base text-foreground">
                                <Icon name="alert-triangle" className="mt-1 shrink-0 text-warning" />
                                <span>The agent could not answer that. <span className="text-muted-foreground">{msg.error}</span></span>
                              </p>
                              <AnswerFooter msg={msg} selected={selected?.id === msg.id} onSelect={() => setSelectedId(msg.id)} onOpenTrace={() => setTraceId(msg.id)} />
                            </>
                          ) : (
                            <>
                              {revealId === msg.id
                                ? <Reveal text={msg.content} onDone={() => setRevealId(null)} onTick={() => toBottom(false)} />
                                : <Markdown>{msg.content}</Markdown>}
                              {revealId !== msg.id && (
                                <AnswerFooter msg={msg} selected={selected?.id === msg.id} onSelect={() => setSelectedId(msg.id)} onOpenTrace={() => setTraceId(msg.id)} />
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Composer. The bottom padding keeps it clear of the Ask Nexus launcher where the column reaches that corner. */}
        <div className={cn('shrink-0 px-4 pb-20 pt-2 sm:px-6', hasChat ? 'xl:pb-5' : '2xl:pb-5')}>
          <form
            onSubmit={e => { e.preventDefault(); sendMessage(); }}
            className="mx-auto w-full max-w-[760px]"
          >
            <div className="flex items-end gap-2 rounded-2xl border border-border-strong bg-card px-4 py-2.5 shadow-sm transition-[border-color,box-shadow] duration-200 focus-within:border-brand focus-within:ring-2 focus-within:ring-ring/30">
              <textarea
                ref={inputRef}
                rows={1}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                placeholder="Ask about your enterprise data"
                autoFocus
                aria-label="Message"
                className="scroll-thin max-h-[200px] min-h-[28px] flex-1 resize-none bg-transparent py-1 text-base text-foreground placeholder:text-subtle-foreground focus:outline-none"
              />
              {loading ? (
                <button type="button" onClick={stop} aria-label="Stop" title="Stop" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-3 text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <span className="h-2.5 w-2.5 rounded-[2px] bg-current" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  aria-label="Send"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all duration-200 hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-95 disabled:scale-100 disabled:bg-surface-3 disabled:text-subtle-foreground"
                >
                  <Icon name="send" />
                </button>
              )}
            </div>
            <p className="mt-2 px-1 text-xs text-subtle-foreground max-xl:pr-40">
              Enter to send, Shift + Enter for a new line. Answers are generated by AI: check the trace before acting on them.
            </p>
          </form>
        </div>
      </div>

      {hasChat && <AnswerRail message={selected} onOpenTrace={() => selected && setTraceId(selected.id)} />}

      <TraceSheet message={traceMessage} onClose={() => setTraceId(null)} />
    </div>
  );
}
