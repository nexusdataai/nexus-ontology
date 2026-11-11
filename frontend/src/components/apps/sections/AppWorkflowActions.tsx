import { useState, useEffect, useMemo } from 'react';
import { apiClient } from '@/services/apiClient';
import type { AppConfig } from '@/config/appRegistry';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon, type IconName } from '@/components/ds/Icon';
import { Chips, CodeBlock, DetailSheet, InlineError, KeyValues, SearchInput, StatusPill, SubHeading, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { cn } from '@/lib/utils';

interface ActionEntry {
  action_id: string;
  action_type: string;
  entity_type: string;
  entity_id: string;
  status: string;
  policy_reference: string;
  details: any;
  job_id: string;
  processed_at: string;
}

const ACTIONS: Record<string, { label: string; icon: IconName; what: string }> = {
  credit_hold: { label: 'Credit hold', icon: 'lock', what: 'Orders paused for customers over their credit limit' },
  dispute_case: { label: 'Dispute case', icon: 'alert-triangle', what: 'Cases opened for invoices that do not match' },
  sla_breach: { label: 'SLA escalation', icon: 'clock', what: 'Late deliveries escalated to the account owner' },
  dunning_notice: { label: 'Dunning notice', icon: 'mail', what: 'Payment reminders sent for overdue invoices' },
  expedited_fulfillment: { label: 'Expedited delivery', icon: 'truck', what: 'Shipments moved up to protect an SLA' },
  credit_note: { label: 'Credit note', icon: 'receipt', what: 'Credit notes issued for confirmed overbilling' },
};

const metaOf = (type: string) => ACTIONS[type] || { label: type.replace(/[_:]+/g, ' ').replace(/^\w/, c => c.toUpperCase()), icon: 'bolt' as IconName, what: '' };

/** Each solution writes its actions to its own log entity. */
const ACTION_LOG: Record<string, string> = {
  'order-to-cash': 'O2C_Action_Log',
  'customer-360': 'C360_Action_Log',
  'demand-forecasting': 'DF_Action_Log',
  'esg-sustainability': 'ESG_Action_Log',
  'inventory-optimization': 'IO_Action_Log',
  'procurement-analytics': 'PA_Action_Log',
  'production-quality': 'PQ_Action_Log',
  'supply-chain-risk': 'SCR_Action_Log',
};

/** The logs do not share one shape; read either spelling of each field. */
const normalise = (r: any): ActionEntry => ({
  ...r,
  action_id: r.action_id || r.id || '',
  action_type: r.action_type || 'unknown',
  entity_type: r.entity_type || r.target_entity || '',
  entity_id: r.entity_id || r.target_id || '',
  status: r.status || '',
  policy_reference: r.policy_reference || '',
  details: r.details ?? r.notes ?? null,
  job_id: r.job_id || '',
  processed_at: r.processed_at || r.taken_at || r.created_at || '',
});
const when = (iso?: string) => {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

interface Props { app: AppConfig; }

/** Workflow Actions: what the automation did, grouped by kind, with the policy behind each action. */
export function AppWorkflowActions({ app }: Props) {
  const [actions, setActions] = useState<ActionEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState<string>('all');
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState<ActionEntry | null>(null);

  const fetchActions = (retries = 3) => {
    setLoading(true);
    setError(false);
    const entity = ACTION_LOG[app.id];
    if (!entity) { setActions([]); setLoading(false); return; }
    apiClient.post(`/api/v1/apps/${app.id}/query`, {
      entity, limit: 500,
    }).then(d => {
      setActions((d?.rows || []).map(normalise));
      setLoading(false);
    }).catch(() => {
      if (retries > 1) {
        setTimeout(() => fetchActions(retries - 1), 800);
      } else {
        setError(true);
        setLoading(false);
      }
    });
  };

  useEffect(() => { fetchActions(); }, [app.id]);

  const byType = useMemo(() => {
    const m: Record<string, number> = {};
    for (const a of actions) m[a.action_type || 'unknown'] = (m[a.action_type || 'unknown'] || 0) + 1;
    return m;
  }, [actions]);
  const types = useMemo(() => Object.keys(byType).sort((a, b) => byType[b] - byType[a]), [byType]);
  const maxCount = Math.max(...Object.values(byType), 1);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return actions.filter(a =>
      (filter === 'all' || a.action_type === filter) &&
      (!q || `${a.entity_id} ${a.entity_type} ${a.policy_reference} ${a.action_type}`.toLowerCase().includes(q)));
  }, [actions, filter, query]);

  const details = open?.details;
  const detailText = details == null ? '' : typeof details === 'string' ? details : JSON.stringify(details, null, 2);

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-8 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-lg font-medium tracking-tight text-foreground">Workflow actions</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Every action the automation took on your behalf: credit holds, disputes, escalations and collections, each with the policy that allowed it.
          </p>
        </div>
        <Button variant="outline" onClick={() => fetchActions()} disabled={loading}>
          <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
        </Button>
      </header>

      {error ? (
        <InlineError onRetry={() => fetchActions()}>Workflow actions could not be loaded. The server may be busy.</InlineError>
      ) : loading ? (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-40 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      ) : actions.length === 0 ? (
        <EmptyState icon="workflow" title="No actions yet" description="Run the solution's automation journey and the actions it takes will be listed here." />
      ) : (
        <>
          {/* Breakdown: one row per kind of action, on one scale */}
          <section className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
            <div className="flex items-baseline justify-between gap-4 px-5 pt-4">
              <h2 className="text-md font-medium text-foreground">By kind of action</h2>
              <p className="text-sm text-muted-foreground"><span className="num font-medium text-foreground">{actions.length}</span> actions in total</p>
            </div>
            <ul className="grid gap-x-10 px-5 pb-4 pt-3 lg:grid-cols-2">
              {types.map((type, i) => {
                const m = metaOf(type);
                const selected = filter === type;
                return (
                  <li key={type}>
                    <button
                      type="button"
                      onClick={() => setFilter(selected ? 'all' : type)}
                      aria-pressed={selected}
                      className={cn('group -mx-2 flex w-[calc(100%+1rem)] items-center gap-3 rounded-lg px-2 py-2.5 text-left transition-colors hover:bg-surface-2', selected && 'bg-accent')}
                    >
                      <Icon name={m.icon} className={cn('h-[18px] w-[18px] shrink-0 text-muted-foreground', selected && 'text-primary dark:text-brand-hi')} />
                      <span className="min-w-0 flex-1">
                        <span className="flex items-baseline justify-between gap-3">
                          <span className="truncate text-sm font-medium text-foreground">{m.label}</span>
                          <span className="num text-sm font-medium text-foreground">{byType[type]}</span>
                        </span>
                        <span className="mt-1.5 block h-1 overflow-hidden rounded-full bg-surface-3">
                          <span className="grow-x block h-full rounded-full bg-primary" style={{ width: `${(byType[type] / maxCount) * 100}%`, ['--i' as any]: i }} />
                        </span>
                        {m.what && <span className="mt-1.5 block truncate text-xs text-muted-foreground">{m.what}</span>}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>

          {/* Log */}
          <section>
            <Toolbar>
              <Chips
                label="Filter by action"
                value={filter}
                onChange={setFilter}
                options={[{ value: 'all', label: 'All', count: actions.length }, ...types.map(t => ({ value: t, label: metaOf(t).label, count: byType[t] }))]}
              />
              <ToolbarSpacer />
              <SearchInput value={query} onChange={setQuery} placeholder="Search order, customer or policy" className="w-full sm:w-72" />
            </Toolbar>

            <div className="mt-3 overflow-hidden rounded-xl border border-border bg-card shadow-xs">
              {visible.length === 0 ? (
                <p className="px-5 py-10 text-center text-sm text-muted-foreground">No actions match this filter.</p>
              ) : (
                <ul className="scroll-thin max-h-[560px] divide-y divide-border overflow-y-auto">
                  {visible.map((a, i) => {
                    const m = metaOf(a.action_type);
                    return (
                      <li key={a.action_id || i}>
                        <button
                          type="button"
                          onClick={() => setOpen(a)}
                          className="group flex w-full items-center gap-4 px-5 py-3 text-left transition-colors hover:bg-surface-2/70 focus-visible:bg-surface-2 focus-visible:outline-none"
                        >
                          <Icon name={m.icon} className="h-[18px] w-[18px] shrink-0 text-muted-foreground" />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium text-foreground">{m.label}</span>
                            <span className="block truncate text-xs text-muted-foreground">
                              {String(a.entity_type || '').replace(/_/g, ' ')} <span className="font-mono">{a.entity_id}</span>
                              {a.policy_reference && <> · under {a.policy_reference}</>}
                            </span>
                          </span>
                          <span className="hidden shrink-0 text-xs text-muted-foreground md:block">{when(a.processed_at)}</span>
                          <StatusPill status={a.status} className="hidden w-24 sm:inline-flex" />
                          <Icon name="chevron-right" className="h-3.5 w-3.5 shrink-0 text-subtle-foreground transition-transform group-hover:translate-x-0.5" />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">Showing {visible.length} of {actions.length}</p>
          </section>
        </>
      )}

      <DetailSheet
        open={!!open}
        onOpenChange={(o) => !o && setOpen(null)}
        title={open ? metaOf(open.action_type).label : ''}
        description={open ? metaOf(open.action_type).what : undefined}
        meta={open ? <StatusPill status={open.status} variant="soft" /> : undefined}
      >
        {open && (
          <div className="space-y-6">
            <KeyValues
              items={[
                { label: 'Applied to', value: `${String(open.entity_type || '').replace(/_/g, ' ')} ${open.entity_id}` },
                { label: 'Policy', value: open.policy_reference || '—' },
                { label: 'When', value: when(open.processed_at) || '—' },
                { label: 'Run', value: open.job_id || '—', mono: true },
                { label: 'Action ID', value: open.action_id || '—', mono: true },
              ]}
            />
            {detailText && (
              <div>
                <SubHeading>Details recorded by the agent</SubHeading>
                <CodeBlock wrap>{detailText}</CodeBlock>
              </div>
            )}
          </div>
        )}
      </DetailSheet>
    </div>
  );
}
