/**
 * Automation Copilot: describe a goal, review the plan the agent proposes,
 * approve it, watch it run and save it as a journey.
 *
 * A chat workspace in the language of the reasoning Copilot: a centred
 * conversation column with the composer pinned at the bottom. The plan sits in
 * the conversation as a numbered step list (tool, system, approval gates) with
 * its Approve / Save actions; a right rail lists what the plan was built from
 * (a sheet below xl).
 */
import { Fragment, useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Icon } from '@/components/ds/Icon';
import { LogoMark } from '@/components/ds/Logo';
import { CodeBlock, DetailSheet, StatusPill } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import {
  ApprovalGate, PlanSteps, Prose, Reveal, SourcesPanel, TypingDots,
  type PlanStepView, type PlaybookView,
} from '@/components/journeys/copilot/PlanParts';
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

const EXAMPLE_GOALS = [
  'Analyze Order-to-Cash health and identify at-risk accounts',
  'Find overdue invoices and send dunning notices by aging tier',
  'Score suppliers for delivery risk and flag single-source exposure',
  'Forecast next month demand and list SKUs at risk of stockout',
];

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

  // ------------------------------------------------------------------
  // Presentation only below this line.
  // ------------------------------------------------------------------
  const [revealIdx, setRevealIdx] = useState<number | null>(null);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Type out the newest assistant message.
  useEffect(() => {
    const last = messages.length - 1;
    if (last >= 0 && messages[last].role === 'assistant') setRevealIdx(last);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length]);

  const planning = status === 'idle';
  const draft = planning ? goal : feedback;
  const setDraft = planning ? setGoal : setFeedback;
  const submit = () => (planning ? handlePlan() : handleFeedback());

  // Grow the composer with its text.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [draft]);

  const hasChat = messages.length > 0 || status !== 'idle';
  const hasPlan = plan.length > 0;
  const hasSources = !!playbookContext || ragContext.length > 0 || !!validation;
  const planAnchor = (() => {
    for (let i = messages.length - 1; i >= 0; i--) if (Array.isArray(messages[i].data?.plan)) return i;
    return -1;
  })();

  const gated = new Set((validation?.warnings || []).filter(w => /approval/i.test(w.code)).map(w => w.step_id));
  const planSteps: PlanStepView[] = plan.map((step, i) => {
    const done = stepStatus(step.id);
    const waiting = status === 'awaiting_approval' && pendingStep?.step_id === step.id;
    const isRunning = status === 'executing' && !done && completedSteps.length === i;
    return {
      id: step.id,
      name: step.name,
      tool: step.tool,
      rationale: step.rationale,
      repeats: !!step.foreach,
      state: done ? (done.status === 'completed' ? 'completed' : done.status === 'failed' ? 'failed' : done.status) : waiting ? 'awaiting_approval' : isRunning ? 'running' : 'pending',
      gate: gated.has(step.id) || waiting,
      resultPreview: done?.result_preview,
      durationMs: done?.duration_ms,
      systemHint: `${step.tool} ${step.name} ${waiting ? pendingStep?.connector_api || '' : ''} ${step.params ? JSON.stringify(step.params) : ''}`,
    };
  });
  const doneCount = planSteps.filter(s => s.state === 'completed').length;
  const pendingInPlan = !!pendingStep && plan.some(s => s.id === pendingStep.step_id);

  const playbook: PlaybookView | null = playbookContext ? {
    title: playbookContext.title || playbookContext.use_case?.title || playbookContext.use_case_id || playbookContext.use_case?.use_case_id || 'Matched playbook',
    solution: playbookContext.solution_id || playbookContext.use_case?.solution_id,
    score: playbookContext.score,
    source: playbookContext.source,
    tags: playbookContext.tags,
    consumes: playbookContext.consumes_entities,
    produces: playbookContext.produces_entities,
  } : null;

  const statusText: Record<typeof status, string> = {
    idle: 'Ready',
    planning: 'Planning',
    planned: 'Plan ready for review',
    executing: 'Running the plan',
    awaiting_approval: 'Waiting for your approval',
    completed: 'Run completed',
    error: 'Stopped with an error',
  };
  const workingText = status === 'planning' ? 'Planning with playbooks and knowledge sources'
    : status === 'executing' || status === 'awaiting_approval' ? 'Running the plan'
    : 'Working on it';

  const newPlan = () => {
    setStatus('idle'); setSessionId(null); setPlan([]); setMessages([]); setCompletedSteps([]); setSummary(''); setGoal(''); setPendingStep(null);
    setRevealIdx(null);
  };

  const gate = pendingStep ? (
    <ApprovalGate
      title={pendingStep.step_name || pendingStep.step_id}
      tool={pendingStep.tool}
      connector={pendingStep.connector_api}
      risk={pendingStep.risk_level}
      rationale={pendingStep.rationale}
      params={pendingStep.params}
      busy={loading}
      onApprove={() => handleApproveStep(true)}
      onReject={() => handleApproveStep(false)}
    />
  ) : null;

  const planBlock = hasPlan ? (
    <li className="animate-fade-up pl-[42px]">
      <section aria-label="Proposed plan" className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
        <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-border px-4 py-3">
          <div className="min-w-0">
            <h3 className="text-md font-medium text-foreground">Plan</h3>
            <p className="num text-xs text-muted-foreground">
              {plan.length} {plan.length === 1 ? 'step' : 'steps'}
              {doneCount > 0 ? `, ${doneCount} done` : ''}
              {gated.size > 0 ? `, ${gated.size} ${gated.size === 1 ? 'pauses' : 'pause'} for approval` : ''}
            </p>
          </div>
          <StatusPill status={status === 'planned' ? 'pending' : status}>{statusText[status]}</StatusPill>
        </header>
        <div className="px-4 py-4">
          <PlanSteps steps={planSteps} renderGate={() => gate} />
          {status === 'awaiting_approval' && pendingStep && !pendingInPlan && gate}
        </div>
        {(status === 'planned' || status === 'completed' || status === 'awaiting_approval') && (
          <footer className="flex flex-wrap items-center gap-2 border-t border-border bg-surface-2/40 px-4 py-3">
            {status === 'planned' && (
              <Button size="sm" onClick={handleExecute} disabled={loading}>
                <Icon name={loading ? 'spinner' : 'play'} className={loading ? 'animate-spin' : undefined} /> Approve and run
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={handleSave} disabled={saving}>
              <Icon name={saving ? 'spinner' : 'download'} className={saving ? 'animate-spin' : undefined} /> Save as journey
            </Button>
            {status === 'completed' && (
              <Button size="sm" variant="ghost" onClick={newPlan}>
                <Icon name="edit" /> New plan
              </Button>
            )}
            {status === 'planned' && <span className="text-xs text-muted-foreground">Nothing runs until you approve. Reply below to change the plan.</span>}
          </footer>
        )}
      </section>
    </li>
  ) : null;

  const sources = <SourcesPanel playbook={playbook} knowledge={ragContext} validation={validation} />;

  return (
    <div className={cn('grid h-full', hasChat && 'xl:grid-cols-[minmax(0,1fr)_320px]')}>
      <div className="flex min-h-0 min-w-0 flex-col">
        {hasChat && (
          <div className="flex h-11 shrink-0 items-center justify-between gap-3 border-b border-border px-4 sm:px-6">
            <p className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
              {loading
                ? <span className="dot-live shrink-0 text-primary dark:text-brand-hi" aria-hidden="true" />
                : <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', status === 'error' ? 'bg-destructive' : status === 'awaiting_approval' || status === 'planned' ? 'bg-warning' : 'bg-success')} aria-hidden="true" />}
              <span className="truncate">{loading ? workingText : statusText[status]}{hasPlan ? `, ${plan.length} ${plan.length === 1 ? 'step' : 'steps'} planned` : ''}</span>
            </p>
            <div className="flex shrink-0 items-center gap-1">
              {hasSources && (
                <Button variant="ghost" size="sm" className="xl:hidden" onClick={() => setSourcesOpen(true)}>
                  <Icon name="layers" /> Sources
                </Button>
              )}
              {(status === 'completed' || status === 'error') && (
                <Button variant="ghost" size="sm" onClick={newPlan}>
                  <Icon name="edit" /> New plan
                </Button>
              )}
            </div>
          </div>
        )}

        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-[760px] flex-col px-4 sm:px-6">
            {!hasChat ? (
              <div className="flex flex-1 flex-col justify-center py-10">
                <LogoMark className="h-9 w-9 [--logo-bg:var(--background)]" />
                <h2 className="mt-5 text-2xl font-medium tracking-tight text-foreground">What do you want to automate?</h2>
                <p className="mt-2 max-w-xl text-base text-muted-foreground">
                  Describe the outcome. The Copilot proposes a step-by-step plan from your playbooks and knowledge, and nothing runs until you approve it.
                </p>
                <div className="mt-9 grid gap-2.5 sm:grid-cols-2">
                  {EXAMPLE_GOALS.map((q, i) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => { setGoal(q); inputRef.current?.focus(); }}
                      style={{ ['--i' as any]: i }}
                      className="rise group flex w-full items-start justify-between gap-3 rounded-xl border border-border bg-card px-3.5 py-3 text-left text-sm text-muted-foreground transition-[transform,border-color,color,box-shadow] duration-200 ease-brand hover:-translate-y-px hover:border-brand/50 hover:text-foreground hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <span>{q}</span>
                      <Icon name="arrow-up-right" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-subtle-foreground transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <ul className="space-y-6 py-7">
                {messages.map((msg, i) => (
                  <Fragment key={i}>
                    <li className="animate-fade-up">
                      {msg.role === 'user' ? (
                        <div className="flex justify-end">
                          <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-base text-primary-foreground">{msg.content}</p>
                        </div>
                      ) : msg.role === 'system' ? (
                        <p className="flex items-center gap-2.5 pl-[42px] text-sm text-muted-foreground">
                          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-border-strong" aria-hidden="true" />
                          <span className="min-w-0">{msg.content}</span>
                        </p>
                      ) : (
                        <div className="flex gap-3.5">
                          <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-card">
                            <LogoMark className="h-4 w-4 [--logo-bg:var(--card)]" />
                          </span>
                          <div className="min-w-0 flex-1">
                            {revealIdx === i
                              ? <Reveal text={msg.content} onDone={() => setRevealIdx(null)} onTick={() => scrollRef.current?.scrollIntoView({ block: 'end' })} />
                              : <Prose>{msg.content}</Prose>}
                          </div>
                        </div>
                      )}
                    </li>
                    {i === planAnchor && planBlock}
                  </Fragment>
                ))}
                {planAnchor === -1 && planBlock}

                {savedYaml && (
                  <li className="animate-fade-up pl-[42px]">
                    <details className="group rounded-xl border border-border bg-card">
                      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
                        <span>Journey definition <span className="font-normal text-muted-foreground">(YAML)</span></span>
                        <Icon name="chevron-down" className="h-3.5 w-3.5 text-muted-foreground transition-transform duration-200 group-open:rotate-180" />
                      </summary>
                      <div className="border-t border-border p-3">
                        <CodeBlock maxHeight={360}>{savedYaml}</CodeBlock>
                      </div>
                    </details>
                  </li>
                )}

                {loading && (
                  <li className="flex gap-3.5" aria-live="polite">
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-card">
                      <LogoMark className="h-4 w-4 [--logo-bg:var(--card)]" />
                    </span>
                    <div className="flex min-h-7 items-center gap-2.5 text-sm text-muted-foreground">
                      <TypingDots />
                      <span key={workingText} className="animate-fade-in">{workingText}</span>
                    </div>
                  </li>
                )}
              </ul>
            )}
            <div ref={scrollRef} />
          </div>
        </div>

        {/* Composer. The bottom padding keeps it clear of the Ask Nexus launcher where the column reaches that corner. */}
        <div className={cn('shrink-0 px-4 pb-20 pt-2 sm:px-6', hasChat ? 'xl:pb-5' : '2xl:pb-5')}>
          <form onSubmit={e => { e.preventDefault(); submit(); }} className="mx-auto w-full max-w-[760px]">
            <div className="flex items-end gap-2 rounded-2xl border border-border-strong bg-card px-4 py-2.5 shadow-sm transition-[border-color,box-shadow] duration-200 focus-within:border-brand focus-within:ring-2 focus-within:ring-ring/30">
              <textarea
                ref={inputRef}
                rows={1}
                value={draft}
                onChange={e => setDraft(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } }}
                placeholder={planning ? 'Describe what you want to automate' : 'Ask for a change to the plan, or ask a question'}
                aria-label={planning ? 'Automation goal' : 'Feedback on the plan'}
                className="scroll-thin max-h-[200px] min-h-[28px] flex-1 resize-none bg-transparent py-1 text-base text-foreground placeholder:text-subtle-foreground focus:outline-none"
              />
              <button
                type="submit"
                disabled={loading || !draft.trim()}
                aria-label={planning ? 'Plan this' : 'Send'}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all duration-200 hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-95 disabled:scale-100 disabled:bg-surface-3 disabled:text-subtle-foreground"
              >
                <Icon name={loading ? 'spinner' : 'send'} className={loading ? 'animate-spin' : undefined} />
              </button>
            </div>
            <p className="mt-2 px-1 text-xs text-subtle-foreground max-xl:pr-40">
              {planning
                ? 'Enter to plan, Shift + Enter for a new line. You review the plan before anything runs.'
                : 'Enter to send, Shift + Enter for a new line. Plans are generated by AI: check each step before you approve.'}
            </p>
          </form>
        </div>
      </div>

      {hasChat && (
        <aside className="hidden min-h-0 flex-col border-l border-border bg-sidebar/40 xl:flex" aria-label="Used for this plan">
          <div className="flex h-11 shrink-0 items-center border-b border-border px-5">
            <h2 className="text-sm font-medium text-foreground">Used for this plan</h2>
          </div>
          <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-5">{sources}</div>
        </aside>
      )}

      <DetailSheet open={sourcesOpen} onOpenChange={setSourcesOpen} title="Used for this plan" description="The playbook, knowledge sources and checks behind the plan.">
        {sources}
      </DetailSheet>
    </div>
  );
}
