/**
 * "Results" of one run, written as a short report: a sentence that says what
 * happened, the four figures that matter, and where the time went.
 * Built only from the job row the studio already has.
 */
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { StatusPill } from '@/components/ds/kit';
import { dayAndTime, runNumber, secondsInWords, timeOfDay } from './format';
import { runFigures, stepTimes } from './RunsTable';

interface RunResultsProps {
  job: any;
  steps: { id: string; name: string }[];
  /** Position used when the job id carries no number. */
  fallbackNumber: number;
  /** What the run counts ("orders", "calls", "items"). */
  noun: string;
  actions?: ReactNode;
}

const n = (v: number) => Number(v || 0).toLocaleString();

export function RunResults({ job, steps, fallbackNumber, noun, actions }: RunResultsProps) {
  const jobId = job.id || job.jobId;
  const num = runNumber(jobId, fallbackNumber);
  const f = runFigures(job);
  const status = String(job.status || '').toLowerCase();
  const started = job.startedAt ?? job.startTime;
  const durationSeconds = job.metrics?.durationSeconds ?? job.durationSeconds;
  const duration = job.duration || secondsInWords(durationSeconds);
  const times = stepTimes(job, steps).filter(t => t.seconds != null) as { id: string; name: string; label: string; seconds: number; status: string }[];
  const longest = Math.max(1, ...times.map(t => t.seconds));
  const slowest = times.length > 1 ? [...times].sort((a, b) => b.seconds - a.seconds)[0] : null;
  const failedStep = steps.find(s => String((job.stepResults || job.step_results || {})[s.id]?.status).toLowerCase() === 'failed');

  const when = dayAndTime(started);
  const headline =
    status === 'completed' ? `Run #${num} finished${when ? ` on ${when}` : ''}${duration ? ` in ${duration}` : ''}.`
    : status === 'failed' ? `Run #${num} failed${when ? ` on ${when}` : ''}${failedStep ? ` at the step "${failedStep.name}"` : ''}.`
    : status === 'running' || status === 'in_progress' ? `Run #${num} started${started ? ` at ${timeOfDay(started)}` : ''} and is still going.`
    : status === 'cancelled' ? `Run #${num} was stopped${when ? ` on ${when}` : ''}.`
    : `Run #${num} has not started yet.`;

  const body = f.read > 0
    ? `It read ${n(f.read)} ${noun}${f.skipped > 0 ? `, skipped ${n(f.skipped)} that were already handled` : ''} and completed ${n(f.succeeded)}. ${f.failed > 0 ? `${n(f.failed)} could not be processed.` : 'Nothing failed.'}`
    : 'No records were read in this run.';

  const facts = [
    { label: 'Read', value: n(f.read) },
    { label: 'Completed', value: n(f.succeeded) },
    { label: 'Failed', value: n(f.failed), danger: f.failed > 0 },
    { label: 'Duration', value: duration || 'Not recorded' },
  ];

  return (
    <div className="grid gap-x-12 gap-y-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,380px)]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-3">
          <StatusPill status={job.status} variant="soft" />
          {job.triggeredBy && <span className="text-xs text-muted-foreground">Started by {job.triggeredBy === 'ui' ? 'a person' : job.triggeredBy === 'api' ? 'the API' : `the ${job.triggeredBy}`}</span>}
        </div>
        <p className="mt-3 max-w-2xl text-base text-foreground">
          {headline} <span className="text-muted-foreground">{body}</span>
        </p>
        {job.error && <p className="mt-2 max-w-2xl text-sm text-destructive">{String(job.error)}</p>}
        {slowest && status === 'completed' && (
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">Most of the time went into "{slowest.name}" ({slowest.label}).</p>
        )}

        <dl className="mt-5 grid grid-cols-2 gap-y-4 border-t border-border pt-4 sm:grid-cols-4">
          {facts.map(fact => (
            <div key={fact.label} className="min-w-0 pr-4">
              <dt className="text-xs text-muted-foreground">{fact.label}</dt>
              <dd className={cn('num mt-0.5 truncate text-md font-medium', fact.danger ? 'text-destructive' : 'text-foreground')}>{fact.value}</dd>
            </div>
          ))}
        </dl>

        {actions && <div className="mt-5 flex flex-wrap items-center gap-2">{actions}</div>}
      </div>

      <div className="min-w-0">
        <h3 className="text-sm font-medium text-foreground">Time by step</h3>
        {times.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">Step timings appear here once a run has finished.</p>
        ) : (
          <ol className="mt-3 space-y-2.5">
            {times.map((t, i) => (
              <li key={t.id} className="min-w-0">
                <div className="flex items-baseline justify-between gap-3 text-xs">
                  <span className={cn('truncate', t.status === 'failed' ? 'text-destructive' : 'text-muted-foreground')}>{t.name}</span>
                  <span className="num shrink-0 text-foreground">{t.label}</span>
                </div>
                <div className="mt-1 h-1 overflow-hidden rounded-full bg-surface-3">
                  <div
                    className={cn('grow-x h-full rounded-full', t.status === 'failed' ? 'bg-destructive' : 'bg-primary')}
                    style={{ width: `${Math.max(2, (t.seconds / longest) * 100)}%`, ['--i' as any]: i }}
                  />
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

export default RunResults;
