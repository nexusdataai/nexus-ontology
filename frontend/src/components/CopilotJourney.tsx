import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ScrollArea } from './ui/scroll-area';
import {
  Sparkles, Send, Loader2, CheckCircle2, XCircle, Play, Save, RefreshCw,
  ChevronRight, AlertTriangle, MessageSquare, Zap, Clock, ArrowRight, Pause, Shield,
} from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { useToast } from '@/hooks/use-toast';

interface PlanStep {
  id: string;
  name: string;
  tool: string;
  params?: Record<string, any>;
  foreach?: string;
  rationale?: string;
}

interface CompletedStep {
  step_id: string;
  tool: string;
  status: string;
  result_preview: string;
  duration_ms?: number;
}

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  data?: any;
}

interface PlaybookSummary {
  use_case_id?: string;
  title?: string;
  solution_id?: string;
  score?: number;
  source?: string;
  tags?: string[];
  consumes_entities?: string[];
  produces_entities?: string[];
  use_case?: { use_case_id?: string; title?: string; solution_id?: string };
}

interface ValidationIssue {
  step_id: string;
  code: string;
  message: string;
}

interface PlanValidation {
  ok: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export function CopilotJourney() {
  const [goal, setGoal] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [plan, setPlan] = useState<PlanStep[]>([]);
  const [ragContext, setRagContext] = useState<string[]>([]);
  const [playbookContext, setPlaybookContext] = useState<PlaybookSummary | null>(null);
  const [validation, setValidation] = useState<PlanValidation | null>(null);
  const [status, setStatus] = useState<'idle' | 'planning' | 'planned' | 'executing' | 'awaiting_approval' | 'completed' | 'error'>('idle');
  const [messages, setMessages] = useState<Message[]>([]);
  const [completedSteps, setCompletedSteps] = useState<CompletedStep[]>([]);
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [summary, setSummary] = useState('');
  const [savedYaml, setSavedYaml] = useState<string | null>(null);
  const [pendingStep, setPendingStep] = useState<{
    step_id: string;
    step_name?: string;
    tool?: string;
    params?: any;
    rationale?: string;
    connector_api?: string | null;
    risk_level?: string | null;
  } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const addMsg = (role: Message['role'], content: string, data?: any) => {
    setMessages(prev => [...prev, { role, content, timestamp: new Date().toISOString(), data }]);
  };

  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handlePlan = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setStatus('planning');
    addMsg('user', goal);
    addMsg('system', 'Planning your journey using RAG context...');

    try {
      const data = await apiClient.post('/api/v1/control-plane/copilot-journey', {
        goal, use_case: '', max_steps: 10, auto_execute: false,
      }) as any;

      setSessionId(data.session_id);
      setPlan(data.plan || []);
      setRagContext(data.rag_context || []);
      setPlaybookContext(data.playbook_context || null);
      setValidation(data.validation || null);
      setStatus('planned');
      const pb = data.playbook_context || null;
      const ragCount = data.rag_context?.length || 0;
      const pbName = pb?.title || pb?.use_case?.title || pb?.use_case_id || pb?.use_case?.use_case_id || '';
      const summary = pb && pbName
        ? `Generated a ${data.plan?.length || 0}-step plan from playbook "${pbName}" (+${ragCount} knowledge sources). Review and approve to execute.`
        : `Generated a ${data.plan?.length || 0}-step plan based on ${ragCount} knowledge sources. Review and approve to execute.`;
      addMsg('assistant', summary, data);
      const v: PlanValidation | undefined = data.validation;
      if (v && !v.ok && v.errors?.length) {
        addMsg('system', `Validation: ${v.errors.length} error(s), ${v.warnings?.length || 0} warning(s) - the planner attempted self-repair.`);
      }
    } catch (e: any) {
      addMsg('assistant', `Planning failed: ${e.message}`);
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!sessionId) return;
    setLoading(true);
    setStatus('executing');
    if (!pendingStep) {
      addMsg('system', 'Executing plan...');
    }

    try {
      const data = await apiClient.post(`/api/v1/control-plane/copilot-journey/${sessionId}/execute`, {}, { timeout: 300000 }) as any;

      if (data.error) {
        setStatus('error');
        addMsg('assistant', `Execution error: ${data.error}`);
        return;
      }

      // Always merge whatever steps the engine streamed back so the UI
      // shows partial progress on pause as well as full completion.
      if (Array.isArray(data.steps)) setCompletedSteps(data.steps);

      if (data.status === 'awaiting_step_approval' && data.pending_step) {
        setPendingStep(data.pending_step);
        setStatus('awaiting_approval');
        const ps = data.pending_step;
        addMsg('system', `Waiting for approval: ${ps.step_name || ps.step_id} (${ps.tool}${ps.connector_api ? ` -> ${ps.connector_api}` : ''})`);
        return;
      }

      if (data.status === 'rejected') {
        setStatus('error');
        addMsg('assistant', `Step rejected; journey halted.`);
        return;
      }

      setSummary(data.summary || '');
      setStatus('completed');
      setPendingStep(null);
      addMsg('assistant', data.summary || 'Execution completed.', data);
    } catch (e: any) {
      addMsg('assistant', `Execution failed: ${e.message}`);
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveStep = async (approved: boolean) => {
    if (!sessionId || !pendingStep) return;
    setLoading(true);
    addMsg('user', approved ? `Approved: ${pendingStep.step_name || pendingStep.step_id}` : `Rejected: ${pendingStep.step_name || pendingStep.step_id}`);

    try {
      const data = await apiClient.post(`/api/v1/control-plane/copilot-journey/${sessionId}/approve-step`, {
        step_id: pendingStep.step_id, approved,
      }, { timeout: 300000 }) as any;

      if (data.error) {
        setStatus('error');
        addMsg('assistant', `Approval error: ${data.error}`);
        return;
      }

      if (Array.isArray(data.steps)) setCompletedSteps(data.steps);

      if (data.status === 'awaiting_step_approval' && data.pending_step) {
        setPendingStep(data.pending_step);
        setStatus('awaiting_approval');
        const ps = data.pending_step;
        addMsg('system', `Next approval needed: ${ps.step_name || ps.step_id} (${ps.tool}${ps.connector_api ? ` -> ${ps.connector_api}` : ''})`);
        return;
      }

      if (data.status === 'rejected') {
        setStatus('error');
        setPendingStep(null);
        addMsg('assistant', 'Step rejected; journey halted.');
        return;
      }

      setSummary(data.summary || '');
      setStatus('completed');
      setPendingStep(null);
      addMsg('assistant', data.summary || 'Execution completed.', data);
    } catch (e: any) {
      addMsg('assistant', `Approval failed: ${e.message}`);
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async () => {
    if (!sessionId || !feedback.trim()) return;
    setLoading(true);
    addMsg('user', feedback);

    try {
      const data = await apiClient.post(`/api/v1/control-plane/copilot-journey/${sessionId}/feedback`, {
        action: 'feedback', feedback,
      }) as any;
      if (data.revised_plan) {
        setPlan(prev => [...prev.filter(s => completedSteps.some(c => c.step_id === s.id)), ...data.revised_plan]);
        addMsg('assistant', `Plan revised with ${data.revised_plan.length} steps based on your feedback.`);
      }
    } catch (e: any) {
      addMsg('assistant', `Feedback processing failed: ${e.message}`);
    } finally {
      setFeedback('');
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!sessionId) return;
    setSaving(true);
    try {
      const data = await apiClient.post(`/api/v1/control-plane/copilot-journey/${sessionId}/save`, {
        name: goal.substring(0, 60),
      }) as any;
      setSavedYaml(data.yaml);
      const jid = data.journey_id || data.journey_definition?.journey_id;
      const title = data.journey_definition?.title || data.journey_definition?.display_name || jid || 'untitled';
      const persisted = data.persisted === true;
      addMsg('system', persisted
        ? `Saved to Journeys: ${title} (id: ${jid})`
        : `Generated journey YAML for ${title} (not persisted - journey store unavailable)`);
      toast({
        title: persisted ? 'Journey saved' : 'Journey generated',
        description: persisted
          ? `${title} is now available in the Journeys tab.`
          : `${title} - YAML preview only; persistence unavailable.`,
      });
    } catch (e: any) {
      addMsg('assistant', `Save failed: ${e.message}`);
      toast({
        title: 'Save failed',
        description: e.message || 'Could not save journey.',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const stepStatus = (stepId: string) => completedSteps.find(s => s.step_id === stepId);

  return (
    <div className="h-full flex gap-4 p-4">
      {/* Left: Chat Panel */}
      <Card className="w-[420px] flex flex-col shrink-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" /> AI Copilot Journey
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 flex flex-col gap-2 p-3">
          <ScrollArea className="flex-1">
            <div className="space-y-3 pr-2">
              {messages.length === 0 && (
                <div className="text-center py-10 text-muted-foreground text-sm">
                  <Sparkles className="h-8 w-8 mx-auto mb-3 opacity-30" />
                  <p>Describe your automation goal and I'll plan a journey for you.</p>
                  <p className="text-xs mt-2 opacity-60">Example: "Analyze Order-to-Cash health and identify at-risk accounts"</p>
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user' ? 'bg-primary text-primary-foreground' :
                    msg.role === 'system' ? 'bg-muted/50 text-muted-foreground text-xs italic' :
                    'bg-muted'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              <div ref={scrollRef} />
            </div>
          </ScrollArea>

          {status === 'idle' ? (
            <div className="flex gap-2">
              <Input value={goal} onChange={e => setGoal(e.target.value)} placeholder="What do you want to automate?"
                onKeyDown={e => e.key === 'Enter' && handlePlan()} className="text-sm" />
              <Button size="sm" onClick={handlePlan} disabled={loading || !goal.trim()}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          ) : (
            <div className="flex gap-2">
              <Input value={feedback} onChange={e => setFeedback(e.target.value)} placeholder="Provide feedback or ask a question..."
                onKeyDown={e => e.key === 'Enter' && handleFeedback()} className="text-sm" />
              <Button size="sm" onClick={handleFeedback} disabled={loading || !feedback.trim()}>
                <MessageSquare className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Right: Plan + Execution */}
      <div className="flex-1 flex flex-col gap-4 min-w-0">
        {/* Knowledge Sources pane (Playbook + RAG + Validation) */}
        {(playbookContext || ragContext.length > 0 || validation) && (
          <div className="border rounded-md bg-muted/20 p-3 text-xs space-y-2">
            {playbookContext && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-muted-foreground font-medium">Playbook:</span>
                <Badge className="bg-primary/15 text-primary border-primary/30">
                  {playbookContext.title || playbookContext.use_case?.title || playbookContext.use_case_id || playbookContext.use_case?.use_case_id || 'matched'}
                </Badge>
                {(playbookContext.solution_id || playbookContext.use_case?.solution_id) && (
                  <Badge variant="outline" className="text-[9px]">{playbookContext.solution_id || playbookContext.use_case?.solution_id}</Badge>
                )}
                {typeof playbookContext.score === 'number' && (
                  <Badge variant="outline" className="text-[9px]">score {playbookContext.score.toFixed(2)}</Badge>
                )}
                {playbookContext.source && (
                  <Badge variant="outline" className="text-[9px]">{playbookContext.source}</Badge>
                )}
                {playbookContext.tags?.slice(0, 4).map((tg, i) => (
                  <Badge key={`tg-${i}`} variant="outline" className="text-[9px]">{tg}</Badge>
                ))}
              </div>
            )}
            {ragContext.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-muted-foreground font-medium">Knowledge:</span>
                {ragContext.slice(0, 8).map((ctx, i) => (
                  <Badge key={i} variant="outline" className="text-[9px]">{ctx}</Badge>
                ))}
                {ragContext.length > 8 && (
                  <span className="text-[9px] text-muted-foreground">+{ragContext.length - 8} more</span>
                )}
              </div>
            )}
            {validation && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-muted-foreground font-medium">Validation:</span>
                {validation.ok ? (
                  <Badge className="bg-green-500/15 text-green-500 border-green-500/30">all checks passed</Badge>
                ) : (
                  <>
                    <Badge className="bg-red-500/15 text-red-500 border-red-500/30">{validation.errors.length} error(s)</Badge>
                    {validation.errors.slice(0, 3).map((e, i) => (
                      <Badge key={`err-${i}`} variant="outline" className="text-[9px] text-red-400 border-red-500/30">
                        {e.step_id}: {e.code}
                      </Badge>
                    ))}
                  </>
                )}
                {validation.warnings && validation.warnings.length > 0 && (
                  <Badge variant="outline" className="text-[9px] text-amber-400 border-amber-500/30">
                    {validation.warnings.length} warning(s)
                  </Badge>
                )}
              </div>
            )}
          </div>
        )}

        {/* Action Bar */}
        {status !== 'idle' && (
          <div className="flex items-center gap-2">
            <Badge className={
              status === 'planning' ? 'bg-blue-500/20 text-blue-400' :
              status === 'planned' ? 'bg-amber-500/20 text-amber-400' :
              status === 'executing' ? 'bg-blue-500/20 text-blue-400' :
              status === 'awaiting_approval' ? 'bg-amber-500/20 text-amber-400' :
              status === 'completed' ? 'bg-green-500/20 text-green-400' :
              'bg-red-500/20 text-red-400'
            }>{status === 'awaiting_approval' ? 'awaiting approval' : status}</Badge>
            <span className="text-xs text-muted-foreground">{plan.length} steps planned</span>
            <div className="flex-1" />
            {status === 'planned' && (
              <Button size="sm" onClick={handleExecute} disabled={loading}>
                {loading ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-1" />}
                Approve & Run
              </Button>
            )}
            {(status === 'completed' || status === 'planned' || status === 'awaiting_approval') && (
              <Button size="sm" variant="outline" onClick={handleSave} disabled={saving}>
                {saving ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}
                Save as Journey
              </Button>
            )}
            {status === 'completed' && (
              <Button size="sm" variant="outline" onClick={() => { setStatus('idle'); setSessionId(null); setPlan([]); setMessages([]); setCompletedSteps([]); setSummary(''); setGoal(''); setPendingStep(null); }}>
                <RefreshCw className="h-3.5 w-3.5 mr-1" /> New
              </Button>
            )}
          </div>
        )}

        {/* Pending step approval card */}
        {status === 'awaiting_approval' && pendingStep && (
          <Card className="border-amber-500/40 bg-amber-500/5">
            <CardContent className="py-3 px-4">
              <div className="flex items-start gap-3">
                <Pause className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">Approval needed: {pendingStep.step_name || pendingStep.step_id}</span>
                    {pendingStep.risk_level && (
                      <Badge variant="outline" className="text-[10px]">{pendingStep.risk_level}</Badge>
                    )}
                    <Badge variant="secondary" className="text-[10px]">{pendingStep.tool}</Badge>
                    {pendingStep.connector_api && (
                      <Badge variant="outline" className="text-[10px] flex items-center gap-1">
                        <Shield className="h-3 w-3" /> {pendingStep.connector_api}
                      </Badge>
                    )}
                  </div>
                  {pendingStep.rationale && (
                    <p className="text-xs text-muted-foreground mt-1">{pendingStep.rationale}</p>
                  )}
                  {pendingStep.params && Object.keys(pendingStep.params).length > 0 && (
                    <pre className="text-[11px] bg-background/50 rounded p-2 mt-2 overflow-x-auto max-h-32">
                      {JSON.stringify(pendingStep.params, null, 2)}
                    </pre>
                  )}
                  <div className="flex gap-2 mt-3">
                    <Button size="sm" onClick={() => handleApproveStep(true)} disabled={loading}>
                      {loading ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1" />}
                      Approve
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleApproveStep(false)} disabled={loading}>
                      <XCircle className="h-3.5 w-3.5 mr-1" /> Reject
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step Cards */}
        <ScrollArea className="flex-1">
          <div className="space-y-3">
            {plan.map((step, i) => {
              const completed = stepStatus(step.id);
              const isRunning = status === 'executing' && !completed && completedSteps.length === i;
              return (
                <Card key={step.id} className={`transition-all ${
                  completed?.status === 'completed' ? 'border-green-500/30 bg-green-500/5' :
                  completed?.status === 'failed' ? 'border-red-500/30 bg-red-500/5' :
                  isRunning ? 'border-blue-500/30 bg-blue-500/5 ring-1 ring-blue-500/20' :
                  ''
                }`}>
                  <CardContent className="py-3 px-4">
                    <div className="flex items-start gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                        completed?.status === 'completed' ? 'bg-green-500 text-white' :
                        completed?.status === 'failed' ? 'bg-red-500 text-white' :
                        isRunning ? 'bg-blue-500 text-white' :
                        'bg-muted text-muted-foreground'
                      }`}>
                        {completed?.status === 'completed' ? <CheckCircle2 className="h-4 w-4" /> :
                         completed?.status === 'failed' ? <XCircle className="h-4 w-4" /> :
                         isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> :
                         i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">{step.name}</span>
                          <Badge variant="outline" className="text-[9px]">{step.tool}</Badge>
                          {step.foreach && <Badge variant="outline" className="text-[9px] bg-purple-500/10 text-purple-400">foreach</Badge>}
                        </div>
                        {step.rationale && <p className="text-xs text-muted-foreground mt-0.5">{step.rationale}</p>}
                        {completed && (
                          <div className="mt-1 flex items-center gap-2 text-xs">
                            <span className={completed.status === 'completed' ? 'text-green-400' : 'text-red-400'}>
                              {completed.result_preview}
                            </span>
                            {completed.duration_ms && (
                              <span className="text-muted-foreground flex items-center gap-0.5">
                                <Clock className="h-2.5 w-2.5" />{completed.duration_ms}ms
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Summary */}
          {summary && (
            <Card className="mt-4 border-green-500/30">
              <CardContent className="py-3 px-4">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-green-400" />
                  <span className="font-medium text-sm">Execution Summary</span>
                </div>
                <p className="text-sm text-muted-foreground">{summary}</p>
              </CardContent>
            </Card>
          )}

          {/* Saved YAML */}
          {savedYaml && (
            <Card className="mt-4">
              <CardContent className="py-3 px-4">
                <div className="flex items-center gap-2 mb-2">
                  <Save className="h-4 w-4 text-blue-400" />
                  <span className="font-medium text-sm">Saved Journey YAML</span>
                </div>
                <pre className="text-[10px] bg-muted/30 rounded p-2 overflow-x-auto font-mono whitespace-pre">{savedYaml}</pre>
              </CardContent>
            </Card>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}
