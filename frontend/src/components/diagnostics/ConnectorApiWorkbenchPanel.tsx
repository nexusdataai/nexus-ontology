import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Activity, Database, Plug, ShieldCheck, Target, Wrench, Zap } from 'lucide-react';
import { Icon } from '@/components/ds/Icon';
import { InlineError, MetricStrip, SearchInput, StatusPill, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
import {
  connectorApiWorkbenchService,
  type ConnectorAPIListResponse,
  type ConnectorAPIRowEnriched,
  type DiagnosticReport,
  type SmokeReport,
} from '@/services/connectorApiWorkbenchService';
import ConnectorApiTestDrawer from './ConnectorApiTestDrawer';
import { Section } from './_shared';
import SummarySection from './connector-apis/SummarySection';
import CatalogueHealthSection from './connector-apis/CatalogueHealthSection';
import ToolMappingSection from './connector-apis/ToolMappingSection';
import VerificationHintsSection from './connector-apis/VerificationHintsSection';
import SmokeTestSection from './connector-apis/SmokeTestSection';
import AuditDisciplineSection from './connector-apis/AuditDisciplineSection';
import SimulatorCoverageSection from './connector-apis/SimulatorCoverageSection';

export default function ConnectorApiWorkbenchPanel() {
  const [data, setData] = useState<ConnectorAPIListResponse | null>(null);
  const [diag, setDiag] = useState<DiagnosticReport | null>(null);
  const [smoke, setSmoke] = useState<SmokeReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [smokeRunning, setSmokeRunning] = useState(false);
  const [skipHighRisk, setSkipHighRisk] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [systemFilter, setSystemFilter] = useState<string>('');
  const [search, setSearch] = useState('');
  const [orphansOnly, setOrphansOnly] = useState(false);
  const [neverInvokedOnly, setNeverInvokedOnly] = useState(false);
  const [activeApiId, setActiveApiId] = useState<string | null>(null);
  const [tab, setTab] = useState<'apis' | 'checks'>('apis');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [list, dx] = await Promise.all([
        connectorApiWorkbenchService.list(),
        connectorApiWorkbenchService.diagnostic(),
      ]);
      setData(list);
      setDiag(dx);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runSmoke = useCallback(async () => {
    setSmokeRunning(true);
    try {
      const r = await connectorApiWorkbenchService.smokeTest({
        skip_high_risk: skipHighRisk,
      });
      setSmoke(r);
      load();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setSmokeRunning(false);
    }
  }, [skipHighRisk, load]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    return data.items.filter(r => {
      if (systemFilter && r.target_system !== systemFilter) return false;
      if (orphansOnly && r.tool_caller_count > 0) return false;
      if (neverInvokedOnly && r.verified) return false;
      if (q && !(
        r.api_id.toLowerCase().includes(q)
        || r.operation.toLowerCase().includes(q)
        || (r.description || '').toLowerCase().includes(q)
        || r.tool_callers.some(t => t.toLowerCase().includes(q))
      )) return false;
      return true;
    });
  }, [data, systemFilter, search, orphansOnly, neverInvokedOnly]);

  const totals = data?.totals;
  const systems = totals ? Object.entries(totals.by_target_system) : [];
  const checks = diag ? [diag.catalogue_health, diag.tool_mapping, diag.verification_hints, diag.audit_discipline, diag.simulator_coverage] : [];
  const checksFailing = checks.filter(c => !['ok', 'pass', 'healthy'].includes(c.overall)).length;
  const riskLabel = (r: string) => (r === 'high_risk_write' ? 'High-risk write' : r === 'low_risk_write' ? 'Low-risk write' : r === 'read_only' ? 'Read only' : r.replace(/_/g, ' '));
  const lastCall = (iso?: string | null) => {
    if (!iso) return 'Never called';
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="page space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-xl font-medium tracking-tight text-foreground">API workbench</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Every connector API in one place. Test a call against its system, see which agent tools use it, and check that it has been verified.
          </p>
        </div>
        <Button variant="outline" onClick={() => load()} disabled={loading}>
          <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
        </Button>
      </header>

      {error && <InlineError onRetry={load}>{error}</InlineError>}

      {!data && loading ? (
        <div className="space-y-3" aria-busy="true"><Skeleton className="h-24 w-full rounded-xl" /><Skeleton className="h-80 w-full rounded-xl" /></div>
      ) : (
        <>
          {totals && (
            <MetricStrip
              columns={4}
              items={[
                { label: 'APIs', value: totals.checked, hint: `${systems.length} systems` },
                { label: 'Verified', value: totals.verified, tone: 'success', hint: totals.checked ? `${Math.round((totals.verified / totals.checked) * 100)}% of the catalogue` : undefined },
                { label: 'Never called', value: totals.never_invoked, tone: totals.never_invoked ? 'warning' : 'neutral', hint: 'No audit record yet', onClick: () => { setTab('apis'); setNeverInvokedOnly(v => !v); } },
                { label: 'Not used by any tool', value: totals.orphans, tone: totals.orphans ? 'warning' : 'neutral', hint: 'No agent tool calls them', onClick: () => { setTab('apis'); setOrphansOnly(v => !v); } },
              ]}
            />
          )}

          <Tabs value={tab} onValueChange={(v) => setTab(v as 'apis' | 'checks')}>
            <TabsList variant="line">
              <TabsTrigger value="apis">APIs{data ? <span className="num ml-1.5 text-xs text-muted-foreground">{data.items.length}</span> : null}</TabsTrigger>
              <TabsTrigger value="checks">Health checks{diag ? <span className={cn('num ml-1.5 text-xs', checksFailing ? 'text-warning' : 'text-muted-foreground')}>{checksFailing ? `${checksFailing} to review` : 'all passing'}</span> : null}</TabsTrigger>
            </TabsList>

            {/* ------------------------------------------------------ APIs */}
            <TabsContent value="apis" className="mt-5">
              <Toolbar>
                <SearchInput value={search} onChange={setSearch} placeholder="Search by API, operation or tool" className="w-full sm:w-72" />
                <Select value={systemFilter || '__all'} onValueChange={(v) => setSystemFilter(v === '__all' ? '' : v)}>
                  <SelectTrigger className="h-9 w-[190px]" aria-label="System"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all">All systems ({totals?.checked ?? 0})</SelectItem>
                    {systems.map(([s, c]) => (
                      <SelectItem key={s} value={s}><span className="inline-flex items-center gap-2"><SystemLogo system={s} size="xs" />{systemName(s)} ({c})</span></SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FilterToggle on={neverInvokedOnly} onChange={setNeverInvokedOnly}>Never called</FilterToggle>
                <FilterToggle on={orphansOnly} onChange={setOrphansOnly}>Not used by a tool</FilterToggle>
                <ToolbarSpacer />
                <span className="num text-xs text-muted-foreground">{filtered.length} of {data?.items.length ?? 0}</span>
              </Toolbar>

              <div className="scroll-thin mt-3 max-h-[640px] overflow-auto rounded-xl border border-border bg-card shadow-xs">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr>
                      {['API', 'System', 'Access', 'Used by', 'Last call', ''].map((h, i) => (
                        <th key={i} scope="col" className="sticky top-0 z-10 whitespace-nowrap border-b border-border bg-surface-2 px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map(r => (
                      <tr key={r.api_id} className="group border-b border-border transition-colors last:border-b-0 hover:bg-surface-2/60">
                        <td className="max-w-[340px] px-4 py-2.5">
                          <span className="flex items-center gap-2">
                            {r.verified
                              ? <Icon name="check-circle" className="h-3.5 w-3.5 shrink-0 text-success" />
                              : <span className="h-3.5 w-3.5 shrink-0 rounded-full border border-dashed border-border-strong" title="Not verified yet" />}
                            <span className="truncate font-mono text-xs text-foreground" title={r.api_id}>{r.api_id}</span>
                          </span>
                          <span className="mt-0.5 block truncate pl-[22px] text-xs text-muted-foreground" title={r.description || r.operation}>{r.description || r.operation}</span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-2.5"><span className="inline-flex items-center gap-2 text-muted-foreground"><SystemLogo system={r.target_system} size="xs" />{systemName(r.target_system)}</span></td>
                        <td className="whitespace-nowrap px-4 py-2.5"><StatusPill status={r.risk_level}>{riskLabel(r.risk_level)}</StatusPill></td>
                        <td className="max-w-[260px] px-4 py-2.5">
                          {r.tool_caller_count === 0 ? (
                            <span className="text-xs text-warning">No tool uses it</span>
                          ) : (
                            <span className="block truncate font-mono text-xs text-muted-foreground" title={r.tool_callers.join(', ')}>
                              {r.tool_callers.slice(0, 2).join(', ')}{r.tool_callers.length > 2 && <span className="font-sans"> +{r.tool_callers.length - 2}</span>}
                            </span>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-4 py-2.5 text-xs text-muted-foreground">
                          {lastCall(r.last_invocation_ts)}
                          {r.audit_count > 0 && <span className="num ml-1.5 text-foreground">· {r.audit_count} calls</span>}
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <Button size="sm" variant="outline" onClick={() => setActiveApiId(r.api_id)}>
                            <Icon name="play" className="h-3 w-3" /> Test
                          </Button>
                        </td>
                      </tr>
                    ))}
                    {filtered.length === 0 && !loading && (
                      <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-muted-foreground">No APIs match these filters.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </TabsContent>

            {/* ---------------------------------------------- Health checks */}
            <TabsContent value="checks" className="mt-5 space-y-3">
              {!diag ? (
                <div className="space-y-3" aria-busy="true">{[0, 1, 2].map(i => <Skeleton key={i} className="h-14 w-full rounded-xl" />)}</div>
              ) : (
                <>
                  <Section title={`Summary of ${diag.summary.checked} APIs`} icon={Plug} status={diag.summary.overall} defaultOpen>
                    <SummarySection summary={diag.summary} />
                  </Section>

                  <Section
                    title={`Test every API${smoke ? `: ${smoke.totals.verified} of ${smoke.totals.checked} verified` : ''}`}
                    icon={Zap}
                    status={smoke?.overall || 'ok'}
                    defaultOpen={!!smoke}
                    rightSlot={
                      <Button size="sm" onClick={runSmoke} disabled={smokeRunning}>
                        <Icon name={smokeRunning ? 'spinner' : 'play'} className={cn('h-3 w-3', smokeRunning && 'animate-spin')} />
                        {smokeRunning ? 'Running' : 'Run all'}
                      </Button>
                    }
                  >
                    <SmokeTestSection report={smoke} loading={smokeRunning} skipHighRisk={skipHighRisk} onSkipHighRiskChange={setSkipHighRisk} />
                  </Section>

                  <Section title={`Catalogue health: ${diag.catalogue_health.totals.errors} errors, ${diag.catalogue_health.totals.warnings} warnings`} icon={ShieldCheck} status={diag.catalogue_health.overall} defaultOpen={false}>
                    <CatalogueHealthSection report={diag.catalogue_health} />
                  </Section>

                  <Section title={`Tool mapping: ${diag.tool_mapping.totals.tools_with_binding} of ${diag.tool_mapping.totals.tools} tools bound`} icon={Wrench} status={diag.tool_mapping.overall} defaultOpen={false}>
                    <ToolMappingSection report={diag.tool_mapping} />
                  </Section>

                  <Section title={`Verification hints: ${diag.verification_hints.totals.with_hint} of ${diag.verification_hints.totals.checked}`} icon={Target} status={diag.verification_hints.overall} defaultOpen={false}>
                    <VerificationHintsSection report={diag.verification_hints} />
                  </Section>

                  <Section title={`Audit records: ${diag.audit_discipline.totals.audit_missing} missing, ${diag.audit_discipline.totals.never_called} never called`} icon={Activity} status={diag.audit_discipline.overall} defaultOpen={false}>
                    <AuditDisciplineSection report={diag.audit_discipline} />
                  </Section>

                  <Section title={`Simulator coverage: ${diag.simulator_coverage.totals.blocking} blocking of ${diag.simulator_coverage.totals.tables} tables`} icon={Database} status={diag.simulator_coverage.overall} defaultOpen={false}>
                    <SimulatorCoverageSection report={diag.simulator_coverage} />
                  </Section>
                </>
              )}
            </TabsContent>
          </Tabs>
        </>
      )}

      {activeApiId && (
        <ConnectorApiTestDrawer apiId={activeApiId} onClose={() => { setActiveApiId(null); load(); }} />
      )}
    </div>
  );
}

function FilterToggle({ on, onChange, children }: { on: boolean; onChange: (v: boolean) => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={() => onChange(!on)}
      className={cn(
        'flex h-9 items-center gap-1.5 rounded-md border px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        on ? 'border-brand/60 bg-accent text-foreground' : 'border-border text-muted-foreground hover:text-foreground',
      )}
    >
      {on && <Icon name="check" className="h-3 w-3 text-primary dark:text-brand-hi" />}
      {children}
    </button>
  );
}

export type { ConnectorAPIRowEnriched };
