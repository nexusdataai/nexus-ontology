/**
 * Renderers for the sections of a journey report, written to read as one
 * document: a heading, a line of context, then figures, rows or bars divided
 * by hairlines. No cards inside the report.
 *
 * Section `kind` -> renderer is the only dispatch; nothing here is specific
 * to a solution.
 */
import type { ReactNode } from 'react';
import type {
  ReportKpiValue, ReportSection, ReportSectionAlertsList, ReportSectionDistribution,
  ReportSectionKpiGrid, ReportSectionStepBreakdown, ReportSectionTable, ReportSectionTimeline,
} from '@/types/callProcessingJourney';
import { StatusPill, type Tone } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { formatValue } from './formatters';

const KPI_TONE: Record<string, string> = { ok: 'text-success', warn: 'text-warning', critical: 'text-destructive' };
const KPI_WORD: Record<string, string> = { ok: 'On target', warn: 'Watch', critical: 'Off target' };

/** Figures as one strip divided by hairlines. */
export function KpiStrip({ kpis, dense }: { kpis: ReportKpiValue[]; dense?: boolean }) {
  if (!kpis || kpis.length === 0) return null;
  return (
    <dl className={cn('grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border bg-border', dense ? 'sm:grid-cols-3 lg:grid-cols-4' : 'sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6')}>
      {kpis.map((k, i) => (
        <div key={k.key} className="rise min-w-0 bg-card p-4" style={{ ['--i' as any]: i }}>
          <dt className="truncate text-xs text-muted-foreground" title={k.label}>{k.label}</dt>
          <dd className={cn('num mt-1 truncate font-medium tracking-tight text-foreground', dense ? 'text-md' : 'text-xl')}>{formatValue(k.value, k.format)}</dd>
          {k.status && KPI_WORD[k.status] && <div className={cn('mt-0.5 text-xs', KPI_TONE[k.status])}>{KPI_WORD[k.status]}</div>}
        </div>
      ))}
    </dl>
  );
}

function Section({ title, description, aside, children }: { title: string; description?: string | null; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="border-t border-border pt-6">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div className="min-w-0">
          <h3 className="text-md font-medium text-foreground">{title}</h3>
          {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
        </div>
        {aside && <span className="num text-xs text-muted-foreground">{aside}</span>}
      </div>
      {children}
    </section>
  );
}

const Nothing = ({ children }: { children: ReactNode }) => <p className="text-sm text-muted-foreground">{children}</p>;

function KpiGrid({ section }: { section: ReportSectionKpiGrid }) {
  const kpis = section.kpis || [];
  return (
    <Section title={section.title} description={section.description}>
      {kpis.length === 0 ? <Nothing>No figures yet.</Nothing> : <KpiStrip kpis={kpis} dense />}
    </Section>
  );
}

function TableBlock({ section }: { section: ReportSectionTable }) {
  const cols = section.columns || [];
  const rows = section.rows || [];
  const numeric = (f: string) => /percent|integer|decimal|currency|duration/.test(String(f || '').toLowerCase());
  return (
    <Section title={section.title} description={section.description} aside={rows.length ? `${rows.length} ${rows.length === 1 ? 'row' : 'rows'}` : undefined}>
      {rows.length === 0 ? <Nothing>No data yet.</Nothing> : (
        <div className="scroll-thin overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-2 text-left text-xs text-muted-foreground">
                <th className="px-3 py-2 font-medium">Run</th>
                {cols.map(c => <th key={c.key} className={cn('whitespace-nowrap px-3 py-2 font-medium', numeric(c.format) && 'text-right')}>{c.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.jobId || i} className="border-b border-border last:border-b-0">
                  <td className="mono-id px-3 py-2">{r.jobId || 'Unknown'}</td>
                  {cols.map(c => <td key={c.key} className={cn('px-3 py-2', numeric(c.format) && 'num text-right')}>{formatValue(r[c.key], c.format)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}

function Distribution({ section }: { section: ReportSectionDistribution }) {
  const buckets = section.buckets || [];
  const max = buckets.reduce((m, b) => Math.max(m, b.count), 0) || 1;
  return (
    <Section title={section.title} aside={`${Number(section.total || 0).toLocaleString()} items`}>
      {buckets.length === 0 ? <Nothing>No data yet.</Nothing> : (
        <ul className="space-y-2.5">
          {buckets.map((b, i) => (
            <li key={b.label} className="grid grid-cols-[minmax(0,160px)_minmax(0,1fr)_auto] items-center gap-3 text-sm">
              <span className="truncate text-muted-foreground" title={b.label}>{b.label}</span>
              <span className="h-1.5 overflow-hidden rounded-full bg-surface-3">
                <span className="grow-x block h-full rounded-full bg-primary" style={{ width: `${(b.count * 100) / max}%`, ['--i' as any]: i }} />
              </span>
              <span className="num w-24 text-right text-foreground">{b.count.toLocaleString()} <span className="text-xs text-muted-foreground">{Number(b.percentage || 0).toFixed(1)}%</span></span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

const severityTone = (s?: string | null): Tone => {
  const v = String(s || '').toLowerCase();
  if (/critical|high|error/.test(v)) return 'danger';
  if (/warn|medium/.test(v)) return 'warning';
  if (/info|low/.test(v)) return 'info';
  return 'neutral';
};
const words = (s?: string | null) => String(s || '').replace(/[_-]+/g, ' ');

function Alerts({ section }: { section: ReportSectionAlertsList }) {
  const groups = section.groups || [];
  const alerts = section.alerts || [];
  return (
    <Section title={section.title} aside={`${alerts.length} ${alerts.length === 1 ? 'alert' : 'alerts'}`}>
      {groups.length > 0 && (
        <p className="mb-3 text-sm text-muted-foreground">
          {groups.map((g, i) => (
            <span key={g.key}>{i > 0 && ', '}<span className="num font-medium text-foreground">{g.count}</span> {g.label}</span>
          ))}
        </p>
      )}
      {alerts.length === 0 ? <Nothing>No alerts were raised.</Nothing> : (
        <ul className="scroll-thin max-h-80 divide-y divide-border overflow-y-auto rounded-xl border border-border">
          {alerts.slice(0, 50).map((a, i) => (
            <li key={i} className="flex flex-wrap items-start gap-x-4 gap-y-1 px-3 py-2.5 text-sm">
              <StatusPill tone={severityTone(a.severity)} className="w-24">{words(a.severity) || 'Alert'}</StatusPill>
              <div className="min-w-0 flex-1">
                <p className="text-foreground">{a.message || words(a.type) || 'Alert'}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {a.message && a.type ? <span className="first-letter:uppercase">{words(a.type)}</span> : null}
                  {a.entity_id ? <span className="mono-id">{a.message && a.type ? ' · ' : ''}{a.entity_id}</span> : null}
                </p>
              </div>
              {a.jobId && <span className="mono-id shrink-0">{a.jobId}</span>}
            </li>
          ))}
        </ul>
      )}
      {alerts.length > 50 && <p className="mt-2 text-xs text-muted-foreground">Showing 50 of {alerts.length}.</p>}
    </Section>
  );
}

function Transitions({ section }: { section: ReportSectionTimeline }) {
  const events = section.events || [];
  return (
    <Section title={section.title} aside={events.length ? `${events.length} ${events.length === 1 ? 'change' : 'changes'}` : undefined}>
      {events.length === 0 ? <Nothing>No status changes recorded yet.</Nothing> : (
        <ul className="scroll-thin max-h-80 divide-y divide-border overflow-y-auto rounded-xl border border-border">
          {events.map((e, i) => (
            <li key={i} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-2 text-sm">
              <span className="num w-36 shrink-0 text-xs text-muted-foreground">{(e.timestamp || '').slice(0, 19).replace('T', ' ')}</span>
              <span className="inline-flex items-center gap-2">
                <StatusPill status={e.fromState || 'unknown'} />
                <span className="text-xs text-muted-foreground">to</span>
                <StatusPill status={e.toState || 'unknown'} />
              </span>
              {e.stepId && <span className="mono-id">{e.stepId}</span>}
              {e.reason && <span className="min-w-0 flex-1 truncate text-muted-foreground" title={e.reason}>{e.reason}</span>}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function StepBreakdown({ section }: { section: ReportSectionStepBreakdown }) {
  const steps = section.steps || [];
  return (
    <Section title={section.title} aside={steps.length ? `${steps.length} steps` : undefined}>
      {steps.length === 0 ? <Nothing>No step data yet.</Nothing> : (
        <div className="scroll-thin overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-2 text-left text-xs text-muted-foreground">
                <th className="px-3 py-2 font-medium">Step</th>
                <th className="px-3 py-2 font-medium">Tool</th>
                <th className="px-3 py-2 text-right font-medium">Completed</th>
                <th className="px-3 py-2 text-right font-medium">Failed</th>
                <th className="px-3 py-2 text-right font-medium">Other</th>
                <th className="px-3 py-2 text-right font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {steps.map(s => (
                <tr key={s.step_id} className="border-b border-border last:border-b-0">
                  <td className="px-3 py-2">
                    <div className="font-medium text-foreground">{s.name}</div>
                    <div className="mono-id">{s.step_id}</div>
                  </td>
                  <td className="px-3 py-2">{s.tool ? <span className="mono-id text-foreground">{s.tool}</span> : <span className="text-muted-foreground">None</span>}</td>
                  <td className="num px-3 py-2 text-right">{s.completed}</td>
                  <td className={cn('num px-3 py-2 text-right', s.failed > 0 ? 'font-medium text-destructive' : 'text-muted-foreground')}>{s.failed}</td>
                  <td className="num px-3 py-2 text-right text-muted-foreground">{s.other + s.pending}</td>
                  <td className="num px-3 py-2 text-right font-medium">{s.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}

export function renderReportSection(section: ReportSection): ReactNode {
  switch (section.kind) {
    case 'kpi_grid': return <KpiGrid key={section.id} section={section as any} />;
    case 'table': return <TableBlock key={section.id} section={section as any} />;
    case 'distribution': return <Distribution key={section.id} section={section as any} />;
    case 'alerts_list': return <Alerts key={section.id} section={section as any} />;
    case 'timeline': return <Transitions key={section.id} section={section as any} />;
    case 'step_breakdown': return <StepBreakdown key={section.id} section={section as any} />;
    default: return null;
  }
}
