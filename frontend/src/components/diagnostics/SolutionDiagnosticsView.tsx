/**
 * The report shown by every per-solution diagnostics panel.
 *
 * Each panel (O2C, demand forecasting, inventory …) keeps its own state and
 * its own endpoint, and renders this view. The report has the same five
 * sections for every solution, read top to bottom like the data flows:
 * is there data → is it mapped → does it read back → is it clean → did the
 * solution produce results.
 */
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon, type IconName } from '@/components/ds/Icon';
import { CodeBlock, InlineError, MetricStrip, StatusPill, type Tone } from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';

interface DiagSection { status: string; [key: string]: any }
export interface SolutionDiagReport {
  timestamp?: string;
  overall_status: string;
  sections: Record<string, DiagSection>;
}

interface Props {
  /** e.g. "Order-to-Cash" */
  solution: string;
  report: SolutionDiagReport | null;
  loading: boolean;
  error: string | null;
  onRun: () => void;
}

const STEPS: { key: string; title: string; what: string; icon: IconName }[] = [
  { key: 'data_adequacy', title: 'Source data', what: 'Every entity the solution needs has rows in its source system.', icon: 'database' },
  { key: 'mapping_correctness', title: 'Mapping rules', what: 'Each entity has an active rule that maps it to a source table.', icon: 'shuffle' },
  { key: 'data_after_mapping', title: 'Read-back', what: 'Entities can be queried through the virtual data layer and return rows.', icon: 'table' },
  { key: 'data_quality', title: 'Data quality', what: 'Key fields are present and not empty.', icon: 'shield-check' },
  { key: 'results_analysis', title: 'Results', what: 'The latest automation run produced KPIs, alerts and result sets.', icon: 'chart-bar' },
];

const LABEL: Record<string, string> = {
  pass: 'Passed', ok: 'OK', healthy: 'Healthy', warn: 'Warning', degraded: 'Degraded', fail: 'Failed', unhealthy: 'Unhealthy',
  no_data: 'No data', missing: 'Missing', inactive: 'Inactive', error: 'Error',
};
const TONE: Record<string, Tone> = { no_data: 'danger', missing: 'danger', inactive: 'warning' };
const isBad = (s?: string) => !!s && !['pass', 'ok', 'healthy'].includes(s);

export function CheckStatus({ status, soft }: { status: string; soft?: boolean }) {
  return <StatusPill status={status} tone={TONE[status]} variant={soft ? 'soft' : 'dot'}>{LABEL[status] || status.replace(/_/g, ' ')}</StatusPill>;
}

const words = (k: string) => {
  const s = k.replace(/_/g, ' ').replace(/\bpct\b/g, '%');
  return (s.charAt(0).toUpperCase() + s.slice(1)).replace(/\b(dso|oee|clv|mape|otd|ar|kpi)\b/gi, m => m.toUpperCase());
};
function value(k: string, v: unknown): string {
  if (typeof v !== 'number') return String(v ?? '—');
  if (/pct|rate|mape|bias/.test(k)) return `${v > 0 && v < 1 ? (v * 100).toFixed(1) : v}%`;
  if (/value|amount|spend|revenue|_ar$/.test(k)) return `$${v.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
  if (v > 0 && v < 1) return `${(v * 100).toFixed(1)}%`;
  return v.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

const th = 'whitespace-nowrap border-b border-border bg-surface-2 px-5 py-2 text-left text-xs font-medium text-muted-foreground';
const td = 'px-5 py-2.5 align-top';

function Facts({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, v]) => v !== null && typeof v !== 'object');
  if (entries.length === 0) return null;
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 lg:grid-cols-5">
      {entries.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <dt className="truncate text-xs text-muted-foreground" title={words(k)}>{words(k)}</dt>
          <dd className="num mt-0.5 truncate text-md font-medium text-foreground">{value(k, v)}</dd>
        </div>
      ))}
    </dl>
  );
}

function Step({ index, step, section, children }: { index: number; step: (typeof STEPS)[number]; section?: DiagSection; children: React.ReactNode }) {
  const status = section?.status || 'missing';
  const [open, setOpen] = useState(isBad(status));
  return (
    <li className="rise overflow-hidden rounded-xl border border-border bg-card shadow-xs" style={{ ['--i' as any]: index }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-surface-2/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
      >
        <span className="num flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border text-xs text-muted-foreground">{index + 1}</span>
        <span className="min-w-0 flex-1">
          <span className="block text-md font-medium text-foreground">{step.title}</span>
          <span className="block truncate text-sm text-muted-foreground">{step.what}</span>
        </span>
        <CheckStatus status={status} soft />
        <Icon name="chevron-down" className={cn('h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200', open && 'rotate-180')} />
      </button>
      {open && <div className="animate-fade-in border-t border-border">{section ? children : <p className="px-5 py-4 text-sm text-muted-foreground">This check did not return a result.</p>}</div>}
    </li>
  );
}

export function SolutionDiagnosticsView({ solution, report, loading, error, onRun }: Props) {
  const s = report?.sections || {};
  const adequacy = s.data_adequacy, mapping = s.mapping_correctness, readback = s.data_after_mapping, quality = s.data_quality, results = s.results_analysis;
  const failing = STEPS.filter(st => isBad(s[st.key]?.status));
  const ranAt = report?.timestamp ? new Date(report.timestamp).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : null;

  return (
    <div className="page space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-x-8 gap-y-4">
        <div className="min-w-0">
          <h2 className="text-xl font-medium tracking-tight text-foreground">{solution} checks</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            {report
              ? failing.length === 0
                ? <>Everything {solution} needs is in place.{ranAt && <> Checked {ranAt}.</>}</>
                : <><span className="font-medium text-foreground">{failing.length} of {STEPS.length} checks need attention</span>: {failing.map(f => f.title.toLowerCase()).join(', ')}.{ranAt && <> Checked {ranAt}.</>}</>
              : `Five live checks that follow the data from the source systems to the results of ${solution}.`}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {report && <CheckStatus status={report.overall_status} soft />}
          <Button onClick={onRun} disabled={loading}>
            <Icon name={loading ? 'spinner' : 'play'} className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
            {loading ? 'Running checks' : report ? 'Run again' : 'Run checks'}
          </Button>
        </div>
      </header>

      {error && <InlineError onRetry={onRun}>The checks could not run: {error}</InlineError>}

      {/* Before the first run: say what will happen */}
      {!report && !error && (
        <ol className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
          {STEPS.map((st, i) => (
            <li key={st.key} className="flex items-center gap-4 border-b border-border px-5 py-4 last:border-b-0">
              <span className="num flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border text-xs text-muted-foreground">{i + 1}</span>
              <Icon name={st.icon} className="h-[18px] w-[18px] shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium text-foreground">{st.title}</span>
                <span className="block text-sm text-muted-foreground">{st.what}</span>
              </span>
              {loading ? <Skeleton className="h-5 w-20" style={{ animationDelay: `${i * 120}ms` }} /> : <span className="hidden text-xs text-subtle-foreground sm:block">Not run yet</span>}
            </li>
          ))}
        </ol>
      )}

      {report && (
        <>
          <MetricStrip
            columns={4}
            items={[
              { label: 'Entities with data', value: adequacy?.summary ? `${adequacy.summary.with_data} / ${adequacy.summary.total_entities}` : '—', tone: isBad(adequacy?.status) ? 'warning' : 'success', hint: adequacy ? LABEL[adequacy.status] : undefined },
              { label: 'Mapping rules active', value: mapping?.summary ? `${mapping.summary.active} / ${mapping.summary.total_rules}` : '—', tone: isBad(mapping?.status) ? 'warning' : 'success', hint: mapping?.summary?.issues > 0 ? `${mapping.summary.issues} with issues` : mapping ? LABEL[mapping.status] : undefined },
              { label: 'Quality checks passed', value: quality?.summary ? `${quality.summary.passed} / ${quality.summary.total_checks}` : '—', tone: isBad(quality?.status) ? 'warning' : 'success', hint: quality?.summary ? `${quality.summary.warnings || 0} warnings, ${quality.summary.failures || 0} failures` : undefined },
              { label: 'Result sets', value: results?.entities ? results.entities.length : '—', tone: isBad(results?.status) ? 'warning' : 'success', hint: results ? LABEL[results.status] : undefined },
            ]}
          />

          <ol className="space-y-3">
            {/* 1. Source data */}
            <Step index={0} step={STEPS[0]} section={adequacy}>
              <div className="scroll-thin overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead><tr><th className={th}>Entity</th><th className={th}>System</th><th className={cn(th, 'text-right')}>Rows</th><th className={cn(th, 'text-right')}>Fields</th><th className={th}>Status</th></tr></thead>
                  <tbody>
                    {(adequacy?.entities || []).map((e: any) => (
                      <tr key={e.name} className="border-b border-border last:border-b-0">
                        <td className={td}>
                          <span className="font-medium text-foreground">{String(e.name).replace(/_/g, ' ')}</span>
                          {e.error && <span className="mt-0.5 block text-xs text-warning">{e.error}</span>}
                        </td>
                        <td className={td}><span className="inline-flex items-center gap-2 text-muted-foreground"><SystemLogo system={e.system} size="xs" />{systemName(e.system)}</span></td>
                        <td className={cn(td, 'num text-right')}>{e.rows >= 0 ? Number(e.rows).toLocaleString('en-US') : '—'}</td>
                        <td className={cn(td, 'num text-right')}>{e.fields || '—'}</td>
                        <td className={td}><CheckStatus status={e.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Step>

            {/* 2. Mapping rules */}
            <Step index={1} step={STEPS[1]} section={mapping}>
              <div className="scroll-thin overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead><tr><th className={th}>Entity</th><th className={th}>Source table</th><th className={th}>Access</th><th className={cn(th, 'text-right')}>Mapped</th><th className={cn(th, 'text-right')}>Unmapped</th><th className={th}>Status</th></tr></thead>
                  <tbody>
                    {(mapping?.rules || []).map((r: any) => (
                      <tr key={r.entity} className="border-b border-border last:border-b-0">
                        <td className={td}>
                          <span className="font-medium text-foreground">{String(r.entity).replace(/_/g, ' ')}</span>
                          {r.rule_name && <span className="block text-xs text-muted-foreground">{r.rule_name}</span>}
                          {r.issue && <span className="mt-0.5 block text-xs text-warning">{r.issue}</span>}
                        </td>
                        <td className={cn(td, 'font-mono text-xs text-muted-foreground')}>{r.source_table ? `${r.source_schema ? r.source_schema + '.' : ''}${r.source_table}` : '—'}</td>
                        <td className={cn(td, 'text-muted-foreground')}>{r.source_type || '—'}</td>
                        <td className={cn(td, 'num text-right')}>{r.mapped_fields}</td>
                        <td className={cn(td, 'num text-right', r.unmapped_fields > 0 && 'text-warning')}>{r.unmapped_fields || 0}</td>
                        <td className={td}><CheckStatus status={r.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Step>

            {/* 3. Read-back */}
            <Step index={2} step={STEPS[2]} section={readback}>
              <ul className="divide-y divide-border">
                {(readback?.queries || []).map((q: any) => <ReadBackRow key={q.entity} q={q} />)}
              </ul>
            </Step>

            {/* 4. Data quality */}
            <Step index={3} step={STEPS[3]} section={quality}>
              <div className="scroll-thin max-h-[420px] overflow-auto">
                <table className="w-full border-collapse text-sm">
                  <thead><tr><th className={cn(th, 'sticky top-0')}>Entity</th><th className={cn(th, 'sticky top-0')}>Field</th><th className={cn(th, 'sticky top-0')}>Type</th><th className={cn(th, 'sticky top-0 text-right')}>Empty</th><th className={cn(th, 'sticky top-0')}>Present</th><th className={cn(th, 'sticky top-0')}>Status</th></tr></thead>
                  <tbody>
                    {(quality?.checks || []).map((c: any, i: number) => (
                      <tr key={`${c.entity}-${c.field}-${i}`} className="border-b border-border last:border-b-0">
                        <td className={cn(td, 'font-medium text-foreground')}>{String(c.entity).replace(/_/g, ' ')}</td>
                        <td className={cn(td, 'font-mono text-xs')}>{c.field}</td>
                        <td className={cn(td, 'text-muted-foreground')}>{c.type}</td>
                        <td className={cn(td, 'num text-right', c.null_pct > 0 && 'text-warning')}>{c.null_count} <span className="text-muted-foreground">({c.null_pct}%)</span></td>
                        <td className={td}>{c.field_present ? 'Yes' : <span className="text-destructive">No</span>}</td>
                        <td className={td}><CheckStatus status={c.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Step>

            {/* 5. Results */}
            <Step index={4} step={STEPS[4]} section={results}>
              <ul className="divide-y divide-border">
                {(results?.entities || []).map((e: any) => (
                  <li key={e.name} className="px-5 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <span className="text-sm font-medium text-foreground">{String(e.name).replace(/_/g, ' ')}</span>
                      <span className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span><span className="num text-foreground">{Number(e.rows || 0).toLocaleString('en-US')}</span> rows</span>
                        {e.alert_count !== undefined && <span><span className="num text-foreground">{e.alert_count}</span> open alerts</span>}
                        <CheckStatus status={e.status} />
                      </span>
                    </div>
                    {e.kpis && <div className="mt-3"><Facts data={e.kpis} /></div>}
                    {e.summary && <div className="mt-3"><Facts data={e.summary} /></div>}
                    {Array.isArray(e.breakdown) && e.breakdown.length > 0 && <Breakdown rows={e.breakdown} />}
                    {e.error && <p className="mt-2 text-sm text-destructive">{e.error}</p>}
                  </li>
                ))}
              </ul>
            </Step>
          </ol>
        </>
      )}
    </div>
  );
}

function ReadBackRow({ q }: { q: any }) {
  const [open, setOpen] = useState(false);
  const hasSample = q.sample_row && Object.keys(q.sample_row).length > 0;
  return (
    <li className="px-5 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-sm font-medium text-foreground">{String(q.entity).replace(/_/g, ' ')}</span>
        <span className="flex items-center gap-4 text-xs text-muted-foreground">
          <span><span className="num text-foreground">{q.rows_returned}</span> rows read</span>
          {(q.field_keys || []).length > 0 && <span><span className="num text-foreground">{q.field_keys.length}</span> fields</span>}
          <CheckStatus status={q.status} />
          {hasSample && (
            <button type="button" onClick={() => setOpen(o => !o)} aria-expanded={open} className="rounded text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-brand-hi">
              {open ? 'Hide sample' : 'Show sample'}
            </button>
          )}
        </span>
      </div>
      {q.error && <p className="mt-1 text-sm text-destructive">{q.error}</p>}
      {open && hasSample && <div className="mt-3 animate-fade-in"><CodeBlock maxHeight={220}>{JSON.stringify(q.sample_row, null, 2)}</CodeBlock></div>}
    </li>
  );
}

const LABEL_KEYS = ['region', 'category', 'plant', 'vendor_name', 'segment', 'material_id', 'line_id', 'job_id', 'processed_at'];

/** A grouped result (by region, category …) as ranked bars on one scale. */
function Breakdown({ rows }: { rows: any[] }) {
  const items = rows.map(b => {
    const label = LABEL_KEYS.map(k => b[k]).find(v => v !== undefined && v !== null) ?? '—';
    const num = Object.entries(b).find(([k, v]) => !LABEL_KEYS.includes(k) && typeof v === 'number');
    return { label: String(label), value: num ? Number(num[1]) : 0 };
  }).sort((a, b) => b.value - a.value).slice(0, 8);
  const max = Math.max(...items.map(i => i.value), 1);
  return (
    <ol className="mt-4 grid max-w-2xl gap-2">
      {items.map((it, i) => (
        <li key={`${it.label}-${i}`} className="grid grid-cols-[minmax(0,30%)_minmax(0,1fr)_auto] items-center gap-3 text-sm">
          <span className="truncate text-muted-foreground" title={it.label}>{it.label}</span>
          <span className="h-1.5 overflow-hidden rounded-full bg-surface-3"><span className="grow-x block h-full rounded-full bg-primary" style={{ width: `${Math.max(2, (it.value / max) * 100)}%`, ['--i' as any]: i }} /></span>
          <span className="num w-16 text-right font-medium text-foreground">{it.value.toLocaleString('en-US', { maximumFractionDigits: 1 })}</span>
        </li>
      ))}
    </ol>
  );
}

export default SolutionDiagnosticsView;
