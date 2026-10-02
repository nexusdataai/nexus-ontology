import { useState, useRef, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Send, Bot, User, Loader2, Sparkles, Database, Play, X, CheckCircle2, XCircle,
  ChevronDown, ChevronRight, Clock, Zap, Shield, AlertTriangle, Search, Eye,
  ListTree, FileCode, MessageSquareText,
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { apiClient } from '@/services/apiClient';
import { ontoApi, type HybridSearchResponse } from '@/services/ontoApi';
import QueryPanel from '@/components/rag/QueryPanel';
import RetrievalBundle from '@/components/rag/RetrievalBundle';
import GraphViewer from '@/components/rag/GraphViewer';
import ScoreCard from '@/components/rag/ScoreCard';
import TestRunner from '@/components/rag/TestRunner';
import ToolBuilder from '@/components/tool-builder/ToolBuilder';
import ToolsRegistryBrowser from '@/components/registry-browser/ToolsRegistryBrowser';

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

const INTENT_COLORS: Record<string, string> = {
  read_only: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  low_risk_write: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  high_risk_write: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  cross_system: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
};

const EXAMPLE_QUESTIONS = [
  'Which system is the source of truth for customer credit limit?',
  'What happens if I increase a customer credit limit by more than 15%?',
  'If I deactivate a customer in Salesforce, what is impacted in Oracle ERP?',
  'What workflows are triggered when a new enterprise customer is created?',
  'Who is authorized to override customer credit block?',
  'What steps are required to fully onboard a new B2B customer across systems?',
];

function LiveProgress({ events }: { events: StreamEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />Connecting...
      </div>
    );
  }

  const last = events[events.length - 1];
  const maxSteps = events.find(e => e.max_steps)?.max_steps || 10;
  const currentStep = events.filter(e => e.type === 'step_start').length;
  const pct = Math.min(Math.round((currentStep / maxSteps) * 100), 95);
  const completedTools = events.filter(e => e.type === 'tool_result');

  let statusText = 'Thinking...';
  if (last.type === 'status') statusText = last.message || 'Processing...';
  else if (last.type === 'intent') statusText = `Intent: ${last.intent?.replace(/_/g, ' ')}`;
  else if (last.type === 'step_start') statusText = `Reasoning step ${last.step}/${last.max_steps}...`;
  else if (last.type === 'tool_call') statusText = `Querying ${last.tool}...`;
  else if (last.type === 'tool_result') statusText = `Got results from ${last.tool}`;
  else if (last.type === 'tool_blocked') statusText = `Policy blocked ${last.tool}`;

  return (
    <div className="space-y-2 min-w-[220px]">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin shrink-0" />
        <span className="truncate">{statusText}</span>
      </div>
      {currentStep > 0 && (
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-[9px] text-muted-foreground whitespace-nowrap">Step {currentStep}/{maxSteps}</span>
        </div>
      )}
      {completedTools.length > 0 && (
        <div className="space-y-0.5">
          {completedTools.map((t, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <CheckCircle2 className="h-3 w-3 text-green-500 shrink-0" />
              <span className="truncate">{t.tool}</span>
              {t.duration_ms != null && <span className="text-[9px] opacity-60 shrink-0">{Math.round(t.duration_ms)}ms</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SimilarityBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-1.5 min-w-[80px]">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[9px] text-muted-foreground w-7 text-right">{pct}%</span>
    </div>
  );
}

function RetrievalSection({ title, items, color }: { title: string; items: RetrievalItem[]; color: string }) {
  if (!items.length) return null;
  const vecCount = items.filter(i => !i.via_graph).length;
  const graphCount = items.filter(i => i.via_graph).length;
  return (
    <div className="mt-1.5">
      <div className="flex items-center gap-1.5 mb-1">
        <span className={`w-2 h-2 rounded-full ${color}`} />
        <span className="font-medium">{title}</span>
        <span className="text-muted-foreground">({items.length})</span>
        {graphCount > 0 && <span className="text-[9px] px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-300">{graphCount} via graph</span>}
      </div>
      <div className="ml-3.5 space-y-0.5">
        {items.map((item, j) => (
          <div key={j} className="flex items-center gap-2">
            {item.via_graph && <span className="text-[9px] text-emerald-400 shrink-0">G</span>}
            <span className="text-[10px] font-mono truncate flex-1 min-w-0">{item.source_id.replace(/_V1_0$/, '').replace(/_/g, ' ').toLowerCase()}</span>
            {item.relation_type && (
              <span className="text-[9px] px-1 py-0.5 rounded bg-purple-500/20 text-purple-300 shrink-0">{item.relation_type}</span>
            )}
            <SimilarityBar value={item.similarity} />
          </div>
        ))}
      </div>
    </div>
  );
}

function PipelinePhasesView({ phases }: { phases: PipelinePhase[] }) {
  if (!phases.length) return null;
  return (
    <div className="mb-2 space-y-1.5">
      {phases.map((phase, i) => (
        <div key={i} className="rounded border bg-muted/30 p-1.5">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-mono font-bold text-blue-400">Step {i + 1}</span>
            <span className="font-medium">{phase.step}</span>
            <span className="text-muted-foreground ml-auto">{phase.duration_ms}ms</span>
          </div>
          <p className="text-muted-foreground mb-1">{phase.description}</p>
          {phase.top_hits && phase.top_hits.length > 0 && (
            <div className="ml-2 space-y-0.5">
              {phase.top_hits.map((h, j) => (
                <div key={j} className="flex items-center gap-2">
                  <span className="text-blue-400 shrink-0">V</span>
                  <span className="font-mono truncate flex-1">{h.source_id.replace(/_V1_0$/, '').replace(/_/g, ' ').toLowerCase()}</span>
                  <span className="text-muted-foreground shrink-0">{h.content_type.replace('onto_', '')}</span>
                  <SimilarityBar value={h.similarity} />
                </div>
              ))}
            </div>
          )}
          {phase.edges_traversed && phase.edges_traversed.length > 0 && (
            <div className="ml-2 space-y-0.5">
              {phase.edges_traversed.map((e, j) => (
                <div key={j} className="flex items-center gap-1.5">
                  <span className="text-emerald-400 shrink-0">G</span>
                  <span className="font-mono truncate">{e.from.replace(/_/g, ' ').toLowerCase()}</span>
                  <span className="px-1 py-0.5 rounded bg-purple-500/20 text-purple-300 shrink-0">{e.relation}</span>
                  <span className="text-muted-foreground shrink-0">→</span>
                  <span className="font-mono truncate">{e.to.replace(/_/g, ' ').toLowerCase()}</span>
                </div>
              ))}
              {phase.neighbors_found != null && (
                <p className="text-muted-foreground mt-0.5">{phase.neighbors_found} neighbors found, {phase.results_count} docs retrieved</p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function RetrievalPanel({ details }: { details: RetrievalDetails }) {
  const [showPhases, setShowPhases] = useState(false);
  const hasPhases = (details.pipeline_phases?.length ?? 0) > 0;
  return (
    <div className="mt-2 p-2 rounded border bg-card/50 text-[10px]">
      <div className="flex items-center gap-3 mb-2 pb-1.5 border-b flex-wrap">
        <span className="font-medium text-xs">{details.summary}</span>
        <Badge variant="outline" className="text-[9px]">{details.vector_hits} vector</Badge>
        <Badge variant="outline" className="text-[9px] border-emerald-500/50 text-emerald-300">{details.graph_hits} graph</Badge>
        {hasPhases && (
          <button onClick={() => setShowPhases(!showPhases)}
            className="text-[9px] text-blue-400 hover:text-blue-300 ml-auto">
            {showPhases ? 'Hide' : 'Show'} pipeline steps
          </button>
        )}
      </div>
      {showPhases && details.pipeline_phases && (
        <PipelinePhasesView phases={details.pipeline_phases} />
      )}
      {details.graph_traversal_summary && details.graph_hits > 0 && !showPhases && (
        <div className="mb-2 px-2 py-1 rounded bg-emerald-500/10 text-emerald-300 text-[9px]">
          Graph traversal: {details.graph_traversal_summary}
        </div>
      )}
      <RetrievalSection title="Schemas" items={details.schemas} color="bg-blue-500" />
      <RetrievalSection title="Policies" items={details.policies} color="bg-amber-500" />
      <RetrievalSection title="Workflows" items={details.workflows} color="bg-green-500" />
      <RetrievalSection title="Integrations" items={details.integrations} color="bg-purple-500" />
    </div>
  );
}

function StepCard({ s }: { s: AgentStep }) {
  const isToolCall = !!s.tool && !s.blocked;
  const isFinalAnswer = !s.tool && !s.blocked;
  const argsString = s.args && Object.keys(s.args).length > 0 ? JSON.stringify(s.args, null, 2) : '';
  return (
    <div className="rounded-lg border bg-card/40">
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-2 min-w-0">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/15 text-primary text-[11px] font-semibold shrink-0">
            {s.step}
          </span>
          {s.blocked ? (
            <span className="flex items-center gap-1 text-destructive font-medium text-sm">
              <Shield className="h-3.5 w-3.5" /> Blocked
            </span>
          ) : isFinalAnswer ? (
            <span className="flex items-center gap-1 text-green-500 font-medium text-sm">
              <CheckCircle2 className="h-3.5 w-3.5" /> Final answer
            </span>
          ) : (
            <span className="flex items-center gap-1.5 min-w-0">
              <Database className="h-3.5 w-3.5 text-blue-500 shrink-0" />
              <span className="font-mono text-sm font-medium truncate" title={s.tool}>{s.tool}</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {isToolCall && (
            <Badge variant="outline" className="text-[10px]">tool call</Badge>
          )}
          {isFinalAnswer && (
            <Badge variant="outline" className="text-[10px] border-green-500/40 text-green-400">answer</Badge>
          )}
          {s.duration_ms != null && (
            <span className="text-[11px] text-muted-foreground flex items-center gap-0.5">
              <Clock className="h-3 w-3" />{Math.round(s.duration_ms)} ms
            </span>
          )}
        </div>
      </div>
      <div className="p-3 space-y-3 text-xs">
        {s.blocked && s.reason && (
          <div className="px-2 py-1.5 rounded bg-destructive/10 text-destructive flex items-start gap-2">
            <Shield className="h-3 w-3 mt-0.5 shrink-0" />
            <span>{s.reason}</span>
          </div>
        )}
        {isToolCall && argsString && (
          <div>
            <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
              <FileCode className="h-3 w-3" /> Arguments
            </div>
            <pre className="text-[11px] bg-muted/40 rounded p-2 overflow-auto max-h-40 font-mono leading-relaxed">
              {argsString}
            </pre>
          </div>
        )}
        {s.retrieval_details && (
          <div>
            <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
              <Database className="h-3 w-3" /> Retrieval bundle
            </div>
            <RetrievalPanel details={s.retrieval_details} />
          </div>
        )}
        {!s.retrieval_details && s.result_preview && (
          <div>
            <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
              <MessageSquareText className="h-3 w-3" /> Result preview
            </div>
            <pre className="text-[11px] bg-muted/40 rounded p-2 overflow-auto max-h-48 whitespace-pre-wrap break-words font-mono leading-relaxed">
              {s.result_preview}
            </pre>
          </div>
        )}
        {isFinalAnswer && !s.result_preview && (
          <div className="text-[11px] text-muted-foreground italic">
            The agent produced the final answer and exited the ReAct loop.
          </div>
        )}
      </div>
    </div>
  );
}

const STREAM_EVENT_TINTS: Record<string, string> = {
  status:        'bg-muted text-muted-foreground',
  intent:        'bg-blue-500/15 text-blue-300',
  step_start:    'bg-violet-500/15 text-violet-300',
  tool_call:     'bg-amber-500/15 text-amber-300',
  tool_result:   'bg-green-500/15 text-green-300',
  tool_blocked:  'bg-red-500/15 text-red-300',
  answer:        'bg-emerald-500/15 text-emerald-300',
  cache_hit:     'bg-sky-500/15 text-sky-300',
  error:         'bg-red-500/15 text-red-300',
};

function StreamLog({ events }: { events: StreamEvent[] }) {
  if (!events.length) {
    return (
      <div className="px-5 py-10 text-center text-xs text-muted-foreground">
        No stream events captured for this response.
      </div>
    );
  }
  return (
    <div className="p-5 space-y-1.5">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
        Server-Sent Events ({events.length})
      </div>
      <ol className="relative border-l border-border ml-2 space-y-2">
        {events.map((e, i) => {
          const tint = STREAM_EVENT_TINTS[e.type] || 'bg-muted text-muted-foreground';
          let detail = '';
          if (e.type === 'status') detail = e.message || '';
          else if (e.type === 'intent') detail = `intent = ${e.intent}`;
          else if (e.type === 'step_start') detail = `step ${e.step} / ${e.max_steps}`;
          else if (e.type === 'tool_call') detail = `${e.tool}(${e.args ? JSON.stringify(e.args).slice(0, 80) : ''})`;
          else if (e.type === 'tool_result') detail = `${e.tool} -> ${e.duration_ms != null ? `${Math.round(e.duration_ms)} ms` : ''}`;
          else if (e.type === 'tool_blocked') detail = `${e.tool} blocked: ${e.reason}`;
          else if (e.type === 'answer') detail = 'final answer delivered';
          else if (e.type === 'cache_hit') detail = 'served from cache';
          else if (e.type === 'error') detail = e.message || 'unknown error';
          return (
            <li key={i} className="ml-3 relative">
              <span className="absolute -left-[6.5px] top-1.5 w-2.5 h-2.5 rounded-full border border-border bg-background" />
              <div className="flex items-center gap-2 flex-wrap text-xs">
                <span className="text-[9px] text-muted-foreground font-mono w-8 shrink-0">{String(i + 1).padStart(3, '0')}</span>
                <Badge className={`text-[9px] ${tint}`}>{e.type}</Badge>
                <span className="text-muted-foreground truncate min-w-0">{detail}</span>
                {e.type === 'tool_result' && e.preview && (
                  <span className="text-[10px] text-muted-foreground/70 font-mono truncate max-w-[260px]" title={e.preview}>
                    {e.preview.slice(0, 60)}
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function StepDetails({ steps, intent, totalTokens, sessionId, streamEvents }: {
  steps: AgentStep[];
  intent?: string;
  totalTokens?: number;
  sessionId?: string;
  streamEvents?: StreamEvent[];
}) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<'steps' | 'stream'>('steps');
  if (!steps.length) return null;
  const toolSteps = steps.filter(s => s.tool && !s.blocked).length;
  const blockedSteps = steps.filter(s => s.blocked).length;
  const streamCount = streamEvents?.length || 0;
  return (
    <>
      <Button
        type="button"
        variant="secondary"
        size="sm"
        onClick={() => setOpen(true)}
        className="h-7 px-2.5 text-xs gap-1.5"
      >
        <ListTree className="h-3.5 w-3.5" />
        View reasoning steps
        <Badge variant="outline" className="ml-1 h-4 px-1 text-[10px] font-normal">
          {steps.length}
        </Badge>
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl w-[92vw] max-h-[88vh] flex flex-col p-0 gap-0">
          <DialogHeader className="px-5 pt-5 pb-3 border-b">
            <DialogTitle className="flex items-center gap-2 text-base">
              <Zap className="h-4 w-4 text-primary" /> Agent Reasoning Trace
            </DialogTitle>
            <DialogDescription className="text-xs flex flex-wrap items-center gap-x-3 gap-y-1 mt-1">
              <span>{steps.length} step{steps.length > 1 ? 's' : ''} total</span>
              <span className="text-muted-foreground">·</span>
              <span>{toolSteps} tool call{toolSteps === 1 ? '' : 's'}</span>
              {blockedSteps > 0 && (
                <>
                  <span className="text-muted-foreground">·</span>
                  <span className="text-destructive">{blockedSteps} blocked</span>
                </>
              )}
              {intent && (
                <>
                  <span className="text-muted-foreground">·</span>
                  <span>intent: <span className="font-medium">{intent.replace(/_/g, ' ')}</span></span>
                </>
              )}
              {totalTokens != null && (
                <>
                  <span className="text-muted-foreground">·</span>
                  <span>{totalTokens.toLocaleString()} tokens</span>
                </>
              )}
              {sessionId && (
                <>
                  <span className="text-muted-foreground">·</span>
                  <span className="font-mono text-[10px] text-muted-foreground" title={sessionId}>
                    session {sessionId.slice(0, 8)}
                  </span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <Tabs value={tab} onValueChange={(v) => setTab(v as 'steps' | 'stream')} className="flex flex-col flex-1 min-h-0 overflow-hidden">
            <div className="px-5 pt-3 border-b shrink-0">
              <TabsList className="bg-transparent gap-1 h-auto p-0">
                <TabsTrigger
                  value="steps"
                  className="data-[state=active]:bg-blue-600/20 data-[state=active]:text-blue-300 gap-1.5 text-xs px-3 py-1.5 rounded-t-md rounded-b-none border-b-2 border-transparent data-[state=active]:border-blue-400"
                >
                  <ListTree className="h-3.5 w-3.5" /> Steps
                  <Badge variant="outline" className="ml-1 h-4 px-1 text-[10px] font-normal">{steps.length}</Badge>
                </TabsTrigger>
                <TabsTrigger
                  value="stream"
                  disabled={streamCount === 0}
                  className="data-[state=active]:bg-blue-600/20 data-[state=active]:text-blue-300 gap-1.5 text-xs px-3 py-1.5 rounded-t-md rounded-b-none border-b-2 border-transparent data-[state=active]:border-blue-400"
                >
                  <Zap className="h-3.5 w-3.5" /> Stream events
                  <Badge variant="outline" className="ml-1 h-4 px-1 text-[10px] font-normal">{streamCount}</Badge>
                </TabsTrigger>
              </TabsList>
            </div>
            <TabsContent
              value="steps"
              className="flex-1 min-h-0 m-0 mt-0 overflow-y-auto p-5 space-y-3 data-[state=inactive]:hidden"
            >
              {steps.map((s, i) => (
                <StepCard key={i} s={s} />
              ))}
            </TabsContent>
            <TabsContent
              value="stream"
              className="flex-1 min-h-0 m-0 mt-0 overflow-y-auto data-[state=inactive]:hidden"
            >
              <StreamLog events={streamEvents || []} />
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    </>
  );
}

function CopilotTab() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text?: string) => {
    const question = (text || input).trim();
    if (!question || loading) return;
    setInput('');
    const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);
    const userMsg: Message = { id: uid(), role: 'user', content: question, timestamp: new Date() };
    const botId = uid();
    const botMsg: Message = { id: botId, role: 'assistant', content: '', timestamp: new Date(), loading: true, streamEvents: [] };
    setMessages(prev => [...prev, userMsg, botMsg]);
    setLoading(true);

    const updateBot = (patch: Partial<Message>) =>
      setMessages(prev => prev.map(m => m.id === botId ? { ...m, ...patch } : m));

    try {
      const resp = await fetch('/api/v1/control-plane/agent/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        credentials: 'include',
        body: JSON.stringify({ question, max_steps: 10 }),
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
              updateBot({ content: evt.data.answer, agentData: evt.data, loading: false, streamEvents: [...events] });
            } else if (evt.type === 'cache_hit' && evt.data) {
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
      updateBot({ content: 'Failed to get response.', loading: false, error: err.message || 'Stream error' });
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] max-w-5xl mx-auto p-4 gap-4">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600">
          <Sparkles className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold">AI Copilot</h1>
          <p className="text-xs text-muted-foreground">Ask questions about your enterprise data, schemas, and CRM operations</p>
        </div>
      </div>
      <Card className="flex-1 flex flex-col min-h-0">
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-6 py-12">
              <div className="p-4 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900 dark:to-purple-900">
                <Bot className="h-10 w-10 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="text-center max-w-md">
                <h2 className="text-lg font-semibold mb-2">Enterprise AI Agent</h2>
                <p className="text-sm text-muted-foreground mb-6">
                  Ask about schemas, policies, workflows, cross-system dependencies, and approval rules.
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {EXAMPLE_QUESTIONS.map((q, i) => (
                  <button key={i} onClick={() => sendMessage(q)}
                    className="text-left p-3 rounded-lg border hover:bg-muted/50 transition-colors text-xs">{q}</button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map(msg => (
                <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0 mt-0.5">
                      <Bot className="h-4 w-4 text-white" />
                    </div>
                  )}
                  <div className={`max-w-[80%] rounded-lg p-3 ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
                    {msg.loading ? (
                      <LiveProgress events={msg.streamEvents || []} />
                    ) : (
                      <>
                        <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                        {msg.error && (
                          <p className="mt-2 text-xs text-destructive flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" /> {msg.error}
                          </p>
                        )}
                        {msg.agentData && (
                          <div className="mt-3 pt-2 border-t border-border/50 flex flex-wrap gap-2 items-center">
                            <Badge variant="outline" className={INTENT_COLORS[msg.agentData.intent] || ''}>
                              {msg.agentData.intent.replace(/_/g, ' ')}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground">
                              {msg.agentData.total_tokens.toLocaleString()} tokens
                            </span>
                            {msg.agentData.policy_violations.length > 0 && (
                              <Badge variant="destructive" className="text-[10px]">
                                {msg.agentData.policy_violations.length} violation(s)
                              </Badge>
                            )}
                            {msg.agentData.steps && msg.agentData.steps.length > 0 && (
                              <div className="ml-auto">
                                <StepDetails
                                  steps={msg.agentData.steps}
                                  intent={msg.agentData.intent}
                                  totalTokens={msg.agentData.total_tokens}
                                  sessionId={msg.agentData.session_id}
                                  streamEvents={msg.streamEvents}
                                />
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-7 h-7 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center shrink-0 mt-0.5">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
        <div className="border-t p-3">
          <form onSubmit={e => { e.preventDefault(); sendMessage(); }} className="flex gap-2">
            <Input ref={inputRef} value={input} onChange={e => setInput(e.target.value)}
              placeholder="Ask about your enterprise data..." disabled={loading} className="flex-1" autoFocus />
            <Button type="submit" disabled={loading || !input.trim()} size="icon">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}

// ============================================================================
// ReAct Tools — Dynamic catalog + atomic test panel
// ============================================================================

interface RegisteredTool {
  name: string;
  description: string;
  risk_level: string;
  requires_approval: boolean;
  parameters: { type: string; properties?: Record<string, { type: string; description?: string }>; required?: string[] };
}

interface ToolExecResult {
  tool: string;
  risk_level: string;
  success: boolean;
  result: any;
  elapsed_ms: number;
}

function ReActToolsTab() {
  const [tools, setTools] = useState<RegisteredTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testTool, setTestTool] = useState<RegisteredTool | null>(null);
  const [testArgs, setTestArgs] = useState<Record<string, string>>({});
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState<ToolExecResult | null>(null);
  const [ddbCount, setDdbCount] = useState<number | null>(null);

  useEffect(() => {
    apiClient.get<{ tools: RegisteredTool[]; total: number }>('/api/v1/control-plane/tools')
      .then(d => { setTools(d.tools || []); setError(null); })
      .catch(e => setError(e.message || 'Failed to load tools'))
      .finally(() => setLoading(false));
    // Phase 4.2 (data-organization spec): the durable projection of this
    // catalog lives in DDB (TOOLREG#). Surface the row count so operators
    // can see backup coverage without leaving the page.
    apiClient.get<{ total: number }>('/api/v1/tools-registry')
      .then(r => setDdbCount(r.total ?? null))
      .catch(() => setDdbCount(null));
  }, []);

  const readTools = tools.filter(t => t.risk_level === 'read_only');
  const writeTools = tools.filter(t => t.risk_level !== 'read_only');

  const openTest = (tool: RegisteredTool) => {
    setTestTool(tool);
    setTestArgs({});
    setExecResult(null);
  };

  const runTest = useCallback(async () => {
    if (!testTool) return;
    setExecuting(true);
    setExecResult(null);
    try {
      const parsedArgs: Record<string, any> = {};
      for (const [k, v] of Object.entries(testArgs)) {
        if (!v.trim()) continue;
        try { parsedArgs[k] = JSON.parse(v); } catch { parsedArgs[k] = v; }
      }
      const result = await apiClient.post<ToolExecResult>(
        `/api/v1/control-plane/tools/${testTool.name}/execute`,
        { arguments: parsedArgs },
      );
      setExecResult(result);
    } catch (e: any) {
      setExecResult({ tool: testTool.name, risk_level: testTool.risk_level, success: false, result: { error: e.message }, elapsed_ms: 0 });
    } finally {
      setExecuting(false);
    }
  }, [testTool, testArgs]);

  const paramEntries = testTool?.parameters?.properties
    ? Object.entries(testTool.parameters.properties)
    : [];
  const requiredParams = new Set(testTool?.parameters?.required || []);

  const renderToolGrid = (toolList: RegisteredTool[], label: string) => (
    <>
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">{label}</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {toolList.map(tool => (
          <Card key={tool.name} className="group">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-mono">{tool.name}</CardTitle>
                {tool.requires_approval && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">Approval</span>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground mb-3">{tool.description}</p>
              <div className="flex items-center justify-between">
                <Badge variant="outline" className={INTENT_COLORS[tool.risk_level] || ''}>{tool.risk_level.replace(/_/g, ' ')}</Badge>
                <Button variant="ghost" size="sm" className="h-7 px-2 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={() => openTest(tool)}>
                  <Play className="h-3 w-3 mr-1" /> Test
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );

  return (
    <div className="p-6 overflow-auto h-full">
      <h2 className="text-xl font-semibold mb-2">ReAct Tools</h2>
      <p className="text-sm text-muted-foreground mb-6">
        Tools available to the ReAct planning agent — click Test to execute with real inputs
        <span className="ml-2 text-[10px] bg-muted px-2 py-0.5 rounded">{tools.length} registered</span>
        {ddbCount !== null && (
          <span className="ml-2 text-[10px] bg-blue-500/15 text-blue-300 px-2 py-0.5 rounded">
            {ddbCount} in DDB (TOOLREG#)
          </span>
        )}
      </p>

      {loading && (
        <div className="flex items-center gap-2 text-muted-foreground text-sm py-12 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading tools from agent registry...
        </div>
      )}

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6">
          Failed to load tools: {error}
        </div>
      )}

      {!loading && !error && (
        <>
          {readTools.length > 0 && renderToolGrid(readTools, 'Read Tools')}
          {writeTools.length > 0 && renderToolGrid(writeTools, 'Write Tools')}
          {tools.length === 0 && (
            <div className="text-center text-muted-foreground py-12">No tools registered in the agent</div>
          )}
        </>
      )}

      {/* Test Panel Overlay */}
      {testTool && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setTestTool(null)}>
          <div className="bg-card border rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b shrink-0">
              <div>
                <h3 className="font-mono font-semibold text-sm">{testTool.name}</h3>
                <p className="text-xs text-muted-foreground mt-0.5">{testTool.description}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={INTENT_COLORS[testTool.risk_level] || ''}>{testTool.risk_level.replace(/_/g, ' ')}</Badge>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setTestTool(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Body */}
            <ScrollArea className="flex-1 min-h-0">
              <div className="p-5 space-y-4">
                {/* Parameters Form */}
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Parameters</h4>
                  {paramEntries.length === 0 ? (
                    <p className="text-xs text-muted-foreground">This tool takes no parameters</p>
                  ) : (
                    <div className="space-y-3">
                      {paramEntries.map(([key, schema]) => (
                        <div key={key}>
                          <label className="text-xs font-medium flex items-center gap-1.5 mb-1">
                            {key}
                            {requiredParams.has(key) && <span className="text-red-400">*</span>}
                            {schema.type && <span className="text-[10px] text-muted-foreground font-normal">({schema.type})</span>}
                          </label>
                          {schema.description && <p className="text-[10px] text-muted-foreground mb-1">{schema.description}</p>}
                          {schema.type === 'object' ? (
                            <textarea
                              className="w-full bg-muted/50 border rounded-lg px-3 py-2 text-xs font-mono min-h-[60px] resize-y"
                              placeholder="{}"
                              value={testArgs[key] || ''}
                              onChange={e => setTestArgs(prev => ({ ...prev, [key]: e.target.value }))}
                            />
                          ) : (
                            <Input
                              className="text-xs font-mono"
                              type={schema.type === 'integer' || schema.type === 'number' ? 'number' : 'text'}
                              placeholder={schema.type === 'integer' || schema.type === 'number' ? '0' : `Enter ${key}...`}
                              value={testArgs[key] || ''}
                              onChange={e => setTestArgs(prev => ({ ...prev, [key]: e.target.value }))}
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Run Button */}
                <Button onClick={runTest} disabled={executing} className="w-full">
                  {executing ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Executing...</> : <><Play className="h-4 w-4 mr-2" /> Run Tool</>}
                </Button>

                {/* Result */}
                {execResult && (
                  <div className={`rounded-lg border p-4 ${execResult.success ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {execResult.success ? <CheckCircle2 className="h-4 w-4 text-green-400" /> : <XCircle className="h-4 w-4 text-red-400" />}
                        <span className="text-xs font-medium">{execResult.success ? 'Success' : 'Error'}</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground">{execResult.elapsed_ms}ms</span>
                    </div>
                    <pre className="text-[11px] whitespace-pre-wrap bg-muted/50 p-3 rounded-lg font-mono max-h-[300px] overflow-auto">
                      {JSON.stringify(execResult.result, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        </div>
      )}
    </div>
  );
}

function PlanningPlaygroundTab() {
  const [results, setResults] = useState<HybridSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastQuery, setLastQuery] = useState('');

  const handleSearch = async (query: string, contentType?: string, graphHops?: number) => {
    setLoading(true);
    setLastQuery(query);
    try {
      const response = await ontoApi.hybridSearch({ query, content_type: contentType, limit: 15, graph_hops: graphHops ?? 2 });
      setResults(response);
    } catch (e) { console.error('Search failed:', e); }
    finally { setLoading(false); }
  };

  return (
    <div className="p-6 space-y-4 max-w-[1400px] mx-auto">
      <div>
        <h2 className="text-xl font-semibold mb-1">Planning Playground</h2>
        <p className="text-sm text-muted-foreground">Test hybrid RAG queries, inspect retrieval bundles, and validate knowledge quality for planning</p>
      </div>

      <QueryPanel onSearch={handleSearch} loading={loading} />

      {lastQuery && (
        <div className="text-sm text-muted-foreground">
          Query: <span className="font-medium text-foreground">{lastQuery}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Tabs defaultValue="bundle">
            <TabsList>
              <TabsTrigger value="bundle">Retrieval Bundle</TabsTrigger>
              <TabsTrigger value="graph">Graph View</TabsTrigger>
              <TabsTrigger value="tests">Test Suite</TabsTrigger>
            </TabsList>
            <TabsContent value="bundle" className="mt-3"><RetrievalBundle results={results} /></TabsContent>
            <TabsContent value="graph" className="mt-3"><GraphViewer results={results} /></TabsContent>
            <TabsContent value="tests" className="mt-3"><TestRunner /></TabsContent>
          </Tabs>
        </div>
        <div className="space-y-4">
          <ScoreCard results={results} />
        </div>
      </div>
    </div>
  );
}

export default function ReasoningPage() {
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState(searchParams.get('tab') || 'copilot');

  useEffect(() => {
    const t = searchParams.get('tab');
    if (t) setTab(t);
  }, [searchParams]);

  return (
    <Layout>
      <Tabs value={tab} onValueChange={setTab} className="flex flex-col h-full">
        <div className="border-b border-border px-6 pt-3">
          <TabsList className="bg-transparent gap-1 h-auto p-0">
            {[
              { value: 'copilot', label: 'AI Copilot' },
              { value: 'playground', label: 'Planning Playground' },
              { value: 'tools', label: 'ReAct Tools' },
              { value: 'tools-reg', label: 'Tools Registry' },
              { value: 'builder', label: 'Tool Builder' },
            ].map(t => (
              <TabsTrigger key={t.value} value={t.value}
                className="data-[state=active]:bg-blue-600/20 data-[state=active]:text-blue-300 gap-1.5 text-xs px-3 py-1.5 rounded-t-md rounded-b-none border-b-2 border-transparent data-[state=active]:border-blue-400">
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        <div className="flex-1 overflow-auto">
          <TabsContent value="copilot" className="mt-0 h-full">
            <CopilotTab />
          </TabsContent>
          <TabsContent value="playground" className="mt-0">
            <PlanningPlaygroundTab />
          </TabsContent>
          <TabsContent value="tools" className="mt-0 h-full">
            <ReActToolsTab />
          </TabsContent>
          <TabsContent value="tools-reg" className="mt-0 h-full">
            <ToolsRegistryBrowser />
          </TabsContent>
          <TabsContent value="builder" className="mt-0 h-full">
            <ToolBuilder />
          </TabsContent>
        </div>
      </Tabs>
    </Layout>
  );
}
