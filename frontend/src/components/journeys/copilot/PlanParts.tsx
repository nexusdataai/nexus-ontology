/**
 * Presentational pieces of the automation Copilot (components/CopilotJourney):
 * chat atoms in the language of the reasoning Copilot, the proposed plan as a
 * numbered step list with approval gates, and the "what the plan used" panel.
 * No data fetching in here.
 */
import { useEffect, useState, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ds/Icon';
import { CodeBlock, Meter, StatusPill, SubHeading } from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
import { systemsIn } from '../studio/format';

/* ------------------------------------------------------------- chat atoms */

const MD =
  'text-base leading-7 text-foreground [&_p]:mb-3 [&_p:last-child]:mb-0 [&_ul]:mb-3 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:mb-3 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mb-1 ' +
  '[&_strong]:font-medium [&_code]:rounded [&_code]:bg-surface-2 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs ' +
  '[&_a]:text-primary [&_a]:underline [&_a]:underline-offset-4 dark:[&_a]:text-brand-hi ' +
  '[&_h1]:mb-2 [&_h1]:text-md [&_h1]:font-medium [&_h2]:mb-2 [&_h2]:text-md [&_h2]:font-medium [&_h3]:mb-1.5 [&_h3]:font-medium';

export function Prose({ children }: { children: string }) {
  return <div className={MD}><ReactMarkdown>{children}</ReactMarkdown></div>;
}

/** Types the answer out a few characters per frame. Skipped for reduced motion. */
export function Reveal({ text, onDone, onTick }: { text: string; onDone: () => void; onTick?: () => void }) {
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
  return <Prose>{text.slice(0, n)}</Prose>;
}

export function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden="true">
      {[0, 1, 2].map(i => (
        <span key={i} className="h-1.5 w-1.5 rounded-full bg-primary dark:bg-brand-hi" style={{ animation: 'typing-dot 1.1s ease-in-out infinite', animationDelay: `${i * 140}ms` }} />
      ))}
    </span>
  );
}

/* ------------------------------------------------------------------- plan */

export interface PlanStepView {
  id: string;
  name: string;
  tool: string;
  rationale?: string;
  /** Runs once per item of a list. */
  repeats?: boolean;
  /** 'pending' | 'running' | 'completed' | 'failed' | 'awaiting_approval' */
  state: string;
  /** The step pauses for a person before it runs. */
  gate?: boolean;
  resultPreview?: string;
  durationMs?: number;
  /** Text searched for a known source system (tool, connector, parameters). */
  systemHint?: string;
}

const ms = (v?: number) => (v == null ? '' : v < 1000 ? `${Math.round(v)} ms` : `${(v / 1000).toFixed(1)} s`);

function StepNode({ state, index }: { state: string; index: number }) {
  return (
    <span
      className={cn(
        'relative z-10 mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-medium transition-colors duration-200',
        state === 'completed' && 'border-primary bg-primary text-primary-foreground',
        state === 'running' && 'border-brand bg-card text-primary dark:text-brand-hi',
        state === 'failed' && 'border-destructive/60 bg-card text-destructive',
        state === 'awaiting_approval' && 'border-warning/60 bg-card text-warning',
        state === 'pending' && 'border-border-strong bg-card text-muted-foreground',
      )}
    >
      {state === 'completed' ? <Icon name="check" className="h-3 w-3" />
        : state === 'running' ? <span className="dot-live" />
        : state === 'failed' ? <Icon name="close" className="h-3 w-3" />
        : state === 'awaiting_approval' ? <Icon name="pause" className="h-3 w-3" />
        : <span className="num">{index + 1}</span>}
    </span>
  );
}

/** The proposed plan: numbered steps with the tool, the system and approval gates. */
export function PlanSteps({ steps, renderGate }: { steps: PlanStepView[]; renderGate?: (step: PlanStepView) => ReactNode }) {
  return (
    <ol>
      {steps.map((s, i) => {
        const system = systemsIn(s.systemHint || `${s.tool} ${s.name}`)[0];
        const last = i === steps.length - 1;
        const reached = s.state === 'completed';
        return (
          <li key={s.id} className="rise relative flex gap-3.5 pb-5 last:pb-0" style={{ ['--i' as any]: i }}>
            {!last && <span className={cn('absolute left-[13px] top-8 h-[calc(100%-30px)] w-px', reached ? 'bg-primary/50' : 'bg-border-strong')} aria-hidden="true" />}
            <StepNode state={s.state} index={i} />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                <span className={cn('text-sm font-medium', s.state === 'failed' ? 'text-destructive' : 'text-foreground')}>{s.name}</span>
                <span className="num text-xs text-muted-foreground">
                  {s.state === 'running' ? 'Running' : s.state === 'awaiting_approval' ? 'Waiting for approval' : s.durationMs ? ms(s.durationMs) : ''}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <span className="mono-id text-foreground/80">{s.tool}</span>
                {system && <span className="inline-flex items-center gap-1.5"><SystemLogo system={system} size="xs" /> {systemName(system)}</span>}
                {s.repeats && <span>Repeats for each item</span>}
                {s.gate && s.state !== 'awaiting_approval' && (
                  <span className="inline-flex items-center gap-1 text-warning"><Icon name="shield-check" className="h-3 w-3" /> Pauses for approval</span>
                )}
              </div>
              {s.rationale && <p className="mt-1.5 text-sm text-muted-foreground">{s.rationale}</p>}
              {s.resultPreview && (
                <p className={cn('mt-1.5 text-sm', s.state === 'failed' ? 'text-destructive' : 'text-foreground')}>{s.resultPreview}</p>
              )}
              {s.state === 'awaiting_approval' && renderGate?.(s)}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/** The approval gate of the step the run is paused on. */
export function ApprovalGate({
  title, tool, connector, risk, rationale, params, busy, onApprove, onReject,
}: {
  title: string;
  tool?: string;
  connector?: string | null;
  risk?: string | null;
  rationale?: string;
  params?: any;
  busy?: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  const hasParams = params && typeof params === 'object' && Object.keys(params).length > 0;
  return (
    <div className="animate-fade-up mt-3 rounded-lg border border-warning/30 bg-warning/5 p-3.5" role="group" aria-label={`Approval needed: ${title}`}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-sm font-medium text-foreground">Approve this step to continue</span>
        {risk && <StatusPill status={risk} />}
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {tool ? <>Calls <span className="mono-id text-foreground/80">{tool}</span></> : 'Calls a tool'}
        {connector ? <> through <span className="mono-id text-foreground/80">{connector}</span></> : null}. Nothing is written until you approve.
      </p>
      {rationale && <p className="mt-2 text-sm text-muted-foreground">{rationale}</p>}
      {hasParams && <CodeBlock className="mt-2.5" maxHeight={140}>{JSON.stringify(params, null, 2)}</CodeBlock>}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" onClick={onApprove} disabled={busy}>
          <Icon name={busy ? 'spinner' : 'check'} className={busy ? 'animate-spin' : undefined} /> Approve
        </Button>
        <Button size="sm" variant="outline" onClick={onReject} disabled={busy}>
          Reject
        </Button>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- sources */

export interface PlaybookView {
  title: string;
  solution?: string;
  score?: number;
  source?: string;
  tags?: string[];
  consumes?: string[];
  produces?: string[];
}

export interface ValidationView {
  ok: boolean;
  errors: { step_id: string; code: string; message: string }[];
  warnings: { step_id: string; code: string; message: string }[];
}

const words = (s?: string) => String(s || '').replace(/[_-]+/g, ' ');

/** What the plan was built from: the matched playbook, knowledge sources and plan checks. */
export function SourcesPanel({ playbook, knowledge, validation }: { playbook: PlaybookView | null; knowledge: string[]; validation: ValidationView | null }) {
  const [allKnowledge, setAllKnowledge] = useState(false);
  const shownKnowledge = allKnowledge ? knowledge : knowledge.slice(0, 8);
  const issues = validation ? [...validation.errors.map(e => ({ ...e, kind: 'error' as const })), ...(validation.warnings || []).map(w => ({ ...w, kind: 'warning' as const }))] : [];

  if (!playbook && knowledge.length === 0 && !validation) {
    return <p className="text-sm text-muted-foreground">Once the Copilot proposes a plan, the playbook, knowledge sources and checks it used are listed here.</p>;
  }

  return (
    <div className="space-y-7">
      {playbook && (
        <section>
          <SubHeading>Playbook</SubHeading>
          <p className="text-sm text-foreground">{playbook.title}</p>
          <p className="mt-0.5 text-xs text-muted-foreground first-letter:uppercase">
            {[words(playbook.solution), playbook.source ? `from the ${words(playbook.source)}` : ''].filter(Boolean).join(', ')}
          </p>
          {typeof playbook.score === 'number' && (
            <div className="mt-3">
              <div className="mb-1 flex items-baseline justify-between text-xs text-muted-foreground">
                <span>Match with your goal</span>
                <span className="num text-foreground">{Math.round(playbook.score * 100)}%</span>
              </div>
              <Meter value={playbook.score * 100} label="Playbook match" />
            </div>
          )}
          {(playbook.consumes?.length || playbook.produces?.length) ? (
            <dl className="mt-3 space-y-1 text-xs">
              {playbook.consumes?.length ? <div className="flex gap-2"><dt className="shrink-0 text-muted-foreground">Reads</dt><dd className="min-w-0 text-foreground">{playbook.consumes.map(words).join(', ')}</dd></div> : null}
              {playbook.produces?.length ? <div className="flex gap-2"><dt className="shrink-0 text-muted-foreground">Writes</dt><dd className="min-w-0 text-foreground">{playbook.produces.map(words).join(', ')}</dd></div> : null}
            </dl>
          ) : null}
          {playbook.tags && playbook.tags.length > 0 && (
            <p className="mt-2 text-xs text-subtle-foreground">{playbook.tags.slice(0, 4).join(', ')}</p>
          )}
        </section>
      )}

      {knowledge.length > 0 && (
        <section>
          <SubHeading action={<span className="num text-xs text-muted-foreground">{knowledge.length}</span>}>Knowledge sources</SubHeading>
          <ul className="divide-y divide-border border-y border-border">
            {shownKnowledge.map((k, i) => {
              const system = systemsIn(k)[0];
              return (
                <li key={`${k}-${i}`} className="flex items-center gap-2.5 py-2 text-sm text-foreground">
                  {system ? <SystemLogo system={system} size="xs" /> : <Icon name="document" className="h-3.5 w-3.5 shrink-0 text-subtle-foreground" />}
                  <span className="min-w-0 truncate" title={k}>{k}</span>
                </li>
              );
            })}
          </ul>
          {knowledge.length > 8 && (
            <button type="button" onClick={() => setAllKnowledge(v => !v)} className="mt-2 text-xs font-medium text-primary underline-offset-4 hover:underline dark:text-brand-hi">
              {allKnowledge ? 'Show fewer' : `Show all ${knowledge.length}`}
            </button>
          )}
        </section>
      )}

      {validation && (
        <section>
          <SubHeading action={<StatusPill tone={validation.ok ? (issues.length ? 'warning' : 'success') : 'danger'}>{validation.ok ? (issues.length ? 'Passed with notes' : 'Passed') : `${validation.errors.length} ${validation.errors.length === 1 ? 'error' : 'errors'}`}</StatusPill>}>
            Plan checks
          </SubHeading>
          {issues.length === 0 ? (
            <p className="text-sm text-muted-foreground">Every step refers to a known tool and its inputs are available.</p>
          ) : (
            <ul className="space-y-2.5">
              {issues.map((it, i) => (
                <li key={`${it.step_id}-${it.code}-${i}`} className="text-sm">
                  <div className="flex items-center gap-2">
                    <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', it.kind === 'error' ? 'bg-destructive' : 'bg-warning')} aria-hidden="true" />
                    <span className="mono-id text-foreground/80">{it.step_id}</span>
                    <span className="text-xs text-muted-foreground first-letter:uppercase">{words(it.code)}</span>
                  </div>
                  {it.message && <p className="mt-0.5 pl-3.5 text-xs text-muted-foreground">{it.message}</p>}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
