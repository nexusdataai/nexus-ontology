import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Send, Bot, User, Loader2, Sparkles, Database,
  ChevronDown, ChevronRight, Clock, Zap, Shield, AlertTriangle,
  ListTree, FileCode, MessageSquareText, CheckCircle2,
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { apiClient } from '@/services/apiClient';
import Layout from '@/components/Layout';

interface AgentStep {
  step: number;
  tool?: string;
  action?: string;
  args?: Record<string, any>;
  result_preview?: string;
  duration_ms?: number;
  blocked?: boolean;
  reason?: string;
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

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  agentData?: AgentResponse;
  loading?: boolean;
  error?: string;
}

const INTENT_COLORS: Record<string, string> = {
  read_only: 'bg-success/10 text-success dark:bg-success/15 dark:text-success',
  low_risk_write: 'bg-warning/10 text-warning dark:bg-warning/15 dark:text-warning',
  high_risk_write: 'bg-destructive/10 text-destructive dark:bg-destructive/15 dark:text-destructive',
  cross_system: 'bg-primary/10 text-primary dark:bg-primary/15 dark:text-primary',
};

const EXAMPLE_QUESTIONS = [
  'How many Leads are in Salesforce? Show the first 5.',
  'What tables store product pricing information?',
  'Show me the Account table schema',
  'Find all Opportunities with their stage and amount',
  'What custom objects exist for commercial products?',
];

function StepCard({ s }: { s: AgentStep }) {
  const isToolCall = !!s.tool && !s.blocked;
  const isFinalAnswer = !s.tool && !s.blocked;
  const argsString = s.args && Object.keys(s.args).length > 0 ? JSON.stringify(s.args, null, 2) : '';
  return (
    <div className="rounded-lg border bg-card/40">
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-2 min-w-0">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/15 text-primary text-xs font-semibold shrink-0">
            {s.step}
          </span>
          {s.blocked ? (
            <span className="flex items-center gap-1 text-destructive font-medium text-sm">
              <Shield className="h-3.5 w-3.5" /> Blocked
            </span>
          ) : isFinalAnswer ? (
            <span className="flex items-center gap-1 text-success font-medium text-sm">
              <CheckCircle2 className="h-3.5 w-3.5" /> Final answer
            </span>
          ) : (
            <span className="flex items-center gap-1.5 min-w-0">
              <Database className="h-3.5 w-3.5 text-primary shrink-0" />
              <span className="font-mono text-sm font-medium truncate" title={s.tool}>{s.tool}</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {isToolCall && <Badge variant="outline" className="text-xs">tool call</Badge>}
          {isFinalAnswer && (
            <Badge variant="outline" className="text-xs border-success/40 text-success">answer</Badge>
          )}
          {s.duration_ms != null && (
            <span className="text-xs text-muted-foreground flex items-center gap-0.5">
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
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <FileCode className="h-3 w-3" /> Arguments
            </div>
            <pre className="text-xs bg-muted/40 rounded p-2 overflow-auto max-h-40 font-mono leading-relaxed">
              {argsString}
            </pre>
          </div>
        )}
        {s.result_preview && (
          <div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <MessageSquareText className="h-3 w-3" /> Result preview
            </div>
            <pre className="text-xs bg-muted/40 rounded p-2 overflow-auto max-h-48 whitespace-pre-wrap break-words font-mono leading-relaxed">
              {s.result_preview}
            </pre>
          </div>
        )}
        {isFinalAnswer && !s.result_preview && (
          <div className="text-xs text-muted-foreground italic">
            The agent produced the final answer and exited the ReAct loop.
          </div>
        )}
      </div>
    </div>
  );
}

function StepDetails({ steps, intent, totalTokens, sessionId }: {
  steps: AgentStep[];
  intent?: string;
  totalTokens?: number;
  sessionId?: string;
}) {
  const [open, setOpen] = useState(false);
  if (!steps.length) return null;
  const toolSteps = steps.filter(s => s.tool && !s.blocked).length;
  const blockedSteps = steps.filter(s => s.blocked).length;
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
        <Badge variant="outline" className="ml-1 h-4 px-1 text-xs font-normal">
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
                  <span className="font-mono text-xs text-muted-foreground" title={sessionId}>
                    session {sessionId.slice(0, 8)}
                  </span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-3">
            {steps.map((s, i) => (
              <StepCard key={i} s={s} />
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function CopilotPage() {
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
    const userMsg: Message = {
      id: uid(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };
    const botId = uid();
    const botMsg: Message = {
      id: botId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      loading: true,
    };

    setMessages(prev => [...prev, userMsg, botMsg]);
    setLoading(true);

    try {
      const data = await apiClient.post<AgentResponse>(
        '/api/v1/control-plane/agent',
        { question, max_steps: 10 },
        { timeout: 120000 },
      );
      setMessages(prev =>
        prev.map(m =>
          m.id === botId
            ? { ...m, content: data.answer, agentData: data, loading: false }
            : m,
        ),
      );
    } catch (err: any) {
      setMessages(prev =>
        prev.map(m =>
          m.id === botId
            ? { ...m, content: 'Failed to get response.', loading: false, error: err.message || 'Unknown error' }
            : m,
        ),
      );
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <Layout>
    <div className="flex flex-col h-[calc(100vh-64px)] max-w-5xl mx-auto p-4 gap-4">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-gradient-to-br from-primary to-primary">
          <Sparkles className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold">AI Control Plane Copilot</h1>
          <p className="text-xs text-muted-foreground">
            Ask questions about your Salesforce data, schemas, and CRM operations
          </p>
        </div>
      </div>

      <Card className="flex-1 flex flex-col min-h-0">
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-6 py-12">
              <div className="p-4 rounded-full bg-gradient-to-br from-primary/10 to-primary/10 dark:from-primary/15 dark:to-primary/15">
                <Bot className="h-10 w-10 text-primary dark:text-primary" />
              </div>
              <div className="text-center max-w-md">
                <h2 className="text-lg font-semibold mb-2">Enterprise AI Agent</h2>
                <p className="text-sm text-muted-foreground mb-6">
                  I can search 1,600+ Salesforce objects, inspect schemas, query live data,
                  and explain relationships — all grounded in your real FDW data plane.
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {EXAMPLE_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(q)}
                    className="text-left p-3 rounded-lg border hover:bg-muted/50 transition-colors text-xs"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map(msg => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-primary flex items-center justify-center shrink-0 mt-0.5">
                      <Bot className="h-4 w-4 text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-lg p-3 ${
                      msg.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    }`}
                  >
                    {msg.loading ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Thinking...
                      </div>
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
                            <span className="text-xs text-muted-foreground">
                              {msg.agentData.total_tokens.toLocaleString()} tokens
                            </span>
                            {msg.agentData.policy_violations.length > 0 && (
                              <Badge variant="destructive" className="text-xs">
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
                                />
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-7 h-7 rounded-full bg-surface-3 dark:bg-surface-3 flex items-center justify-center shrink-0 mt-0.5">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
        <div className="border-t p-3">
          <form
            onSubmit={e => { e.preventDefault(); sendMessage(); }}
            className="flex gap-2"
          >
            <Input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about your Salesforce data..."
              disabled={loading}
              className="flex-1"
              autoFocus
            />
            <Button type="submit" disabled={loading || !input.trim()} size="icon">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </form>
        </div>
      </Card>
    </div>
    </Layout>
  );
}
