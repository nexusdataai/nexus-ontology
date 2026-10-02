import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Activity, BookOpen, CheckCircle2, Database, Loader2, MinusCircle,
  Play, Plug, RefreshCw, ShieldCheck, Target, Wrench, Zap,
} from 'lucide-react';
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

function riskColor(risk: string): string {
  if (risk === 'high_risk_write') return 'text-red-300';
  if (risk === 'low_risk_write') return 'text-amber-300';
  return 'text-green-300';
}

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

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Plug className="h-5 w-5 text-purple-300" />
            Connector API Workbench
          </h2>
          <p className="text-sm text-muted-foreground">
            Cross-system catalogue of every Connector API spec with diagnostic health checks, tool callers, audit history, and a Test surface that hits the REST endpoint and verifies the simulator actually moved.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => load()} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          {error}
        </div>
      )}

      {/* ---- Diagnostic sections ---- */}

      {diag && (
        <>
          <Section
            title={`Summary (${diag.summary.checked} APIs)`}
            icon={Plug}
            status={diag.summary.overall}
            defaultOpen
          >
            <SummarySection summary={diag.summary} />
          </Section>

          <Section
            title={`Catalogue Health (${diag.catalogue_health.totals.errors} errors / ${diag.catalogue_health.totals.warnings} warnings)`}
            icon={ShieldCheck}
            status={diag.catalogue_health.overall}
            defaultOpen={false}
          >
            <CatalogueHealthSection report={diag.catalogue_health} />
          </Section>

          <Section
            title={`Tool Mapping (${diag.tool_mapping.totals.tools_with_binding}/${diag.tool_mapping.totals.tools} tools bound)`}
            icon={Wrench}
            status={diag.tool_mapping.overall}
            defaultOpen={false}
          >
            <ToolMappingSection report={diag.tool_mapping} />
          </Section>

          <Section
            title={`Verification Hints (${diag.verification_hints.totals.with_hint}/${diag.verification_hints.totals.checked} hinted)`}
            icon={Target}
            status={diag.verification_hints.overall}
            defaultOpen={false}
          >
            <VerificationHintsSection report={diag.verification_hints} />
          </Section>

          <Section
            title={`Run-all Smoke${smoke ? ` (${smoke.totals.verified}/${smoke.totals.checked} verified)` : ''}`}
            icon={Zap}
            status={smoke?.overall || 'ok'}
            defaultOpen={!!smoke}
            rightSlot={
              <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                <Button size="sm" onClick={runSmoke} disabled={smokeRunning}>
                  {smokeRunning
                    ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                    : <Play className="h-3.5 w-3.5 mr-1" />}
                  Run all
                </Button>
              </div>
            }
          >
            <SmokeTestSection
              report={smoke}
              loading={smokeRunning}
              skipHighRisk={skipHighRisk}
              onSkipHighRiskChange={setSkipHighRisk}
            />
          </Section>

          <Section
            title={`Audit Discipline (${diag.audit_discipline.totals.audit_missing} missing / ${diag.audit_discipline.totals.never_called} never called)`}
            icon={Activity}
            status={diag.audit_discipline.overall}
            defaultOpen={false}
          >
            <AuditDisciplineSection report={diag.audit_discipline} />
          </Section>

          <Section
            title={`Simulator Coverage (${diag.simulator_coverage.totals.blocking} blocking / ${diag.simulator_coverage.totals.tables} tables)`}
            icon={Database}
            status={diag.simulator_coverage.overall}
            defaultOpen={false}
          >
            <SimulatorCoverageSection report={diag.simulator_coverage} />
          </Section>
        </>
      )}

      {!diag && loading && (
        <div className="text-xs text-muted-foreground italic flex items-center gap-2">
          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading diagnostic...
        </div>
      )}

      {/* ---- Catalogue table (existing surface) ---- */}

      <Section
        title={`Catalogue (${data?.items.length ?? 0} APIs)`}
        icon={BookOpen}
        status="ok"
        defaultOpen
      >
        {totals && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm mb-3">
            <KpiCard label="APIs" value={totals.checked} />
            <KpiCard label="Verified" value={totals.verified} tone="green" />
            <KpiCard label="Never invoked" value={totals.never_invoked} tone="amber" />
            <KpiCard label="Orphans" value={totals.orphans} tone={totals.orphans ? 'amber' : 'green'} />
            <KpiCard label="Risk mix" value={Object.entries(totals.by_risk_level).map(([k, v]) => `${v} ${k.replace('_write','')}`).join(' \u00b7 ') || '-'} />
          </div>
        )}

        <div className="flex items-center gap-2 flex-wrap text-xs mb-3">
          <span className="text-muted-foreground">Target system:</span>
          <Button
            size="sm"
            variant={!systemFilter ? 'default' : 'outline'}
            className="h-6 text-[10px] px-2"
            onClick={() => setSystemFilter('')}
          >
            all ({totals?.checked ?? 0})
          </Button>
          {totals && Object.entries(totals.by_target_system).map(([s, c]) => (
            <Button
              key={s}
              size="sm"
              variant={systemFilter === s ? 'default' : 'outline'}
              className="h-6 text-[10px] px-2"
              onClick={() => setSystemFilter(systemFilter === s ? '' : s)}
            >
              {s} ({c})
            </Button>
          ))}
          <span className="mx-2 text-border">|</span>
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={orphansOnly} onChange={e => setOrphansOnly(e.target.checked)} />
            <span>orphans only</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={neverInvokedOnly} onChange={e => setNeverInvokedOnly(e.target.checked)} />
            <span>never invoked</span>
          </label>
          <Input
            placeholder="Search api_id / op / caller..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="h-7 text-xs max-w-xs ml-auto"
          />
          <span className="text-muted-foreground">
            {filtered.length} / {data?.items.length ?? 0}
          </span>
        </div>

        <div className="border rounded-md max-h-[36rem] overflow-auto">
          <table className="w-full text-[11px]">
            <thead className="sticky top-0 bg-muted/40 z-10">
              <tr className="text-left">
                <th className="px-2 py-1.5">api_id</th>
                <th className="px-2 py-1.5">System</th>
                <th className="px-2 py-1.5">Operation</th>
                <th className="px-2 py-1.5">Risk</th>
                <th className="px-2 py-1.5">Tool callers</th>
                <th className="px-2 py-1.5">Audit</th>
                <th className="px-2 py-1.5">Verified</th>
                <th className="px-2 py-1.5"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.api_id} className="border-t border-border/40 hover:bg-muted/20">
                  <td className="px-2 py-1 font-mono">{r.api_id}</td>
                  <td className="px-2 py-1 text-muted-foreground">{r.target_system}</td>
                  <td className="px-2 py-1 font-mono text-[10px] text-muted-foreground">{r.operation}</td>
                  <td className="px-2 py-1">
                    <span className={riskColor(r.risk_level)}>{r.risk_level}</span>
                  </td>
                  <td className="px-2 py-1">
                    {r.tool_caller_count === 0 ? (
                      <Badge variant="outline" className="text-[9px] text-amber-300 border-amber-500/30">orphan</Badge>
                    ) : (
                      <CallerChips callers={r.tool_callers} />
                    )}
                  </td>
                  <td className="px-2 py-1 font-mono">
                    {r.audit_count}
                    {r.last_invocation_ts && (
                      <div className="text-[9px] text-muted-foreground truncate max-w-[140px]">{r.last_invocation_ts}</div>
                    )}
                  </td>
                  <td className="px-2 py-1">
                    {r.verified
                      ? <CheckCircle2 className="h-3.5 w-3.5 text-green-300" />
                      : <MinusCircle className="h-3.5 w-3.5 text-muted-foreground" />}
                  </td>
                  <td className="px-2 py-1">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-6 text-[10px] px-2"
                      onClick={() => setActiveApiId(r.api_id)}
                    >
                      <Play className="h-3 w-3 mr-1" /> Test
                    </Button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && !loading && (
                <tr>
                  <td colSpan={8} className="px-3 py-6 text-center text-muted-foreground text-xs">
                    No APIs match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Section>

      {activeApiId && (
        <ConnectorApiTestDrawer apiId={activeApiId} onClose={() => { setActiveApiId(null); load(); }} />
      )}
    </div>
  );
}

function KpiCard({ label, value, tone }: { label: string; value: number | string; tone?: 'green' | 'amber' | 'red' }) {
  const cls = tone === 'green' ? 'text-green-300'
    : tone === 'amber' ? 'text-amber-300'
    : tone === 'red' ? 'text-red-300'
    : '';
  return (
    <div>
      <div className="text-muted-foreground text-xs">{label}</div>
      <div className={`font-mono ${cls}`}>{value}</div>
    </div>
  );
}

function CallerChips({ callers }: { callers: string[] }) {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {callers.map(c => (
        <span key={c} className="px-1.5 py-0.5 rounded bg-muted/40 font-mono text-[10px]">{c}</span>
      ))}
    </div>
  );
}

export type { ConnectorAPIRowEnriched };
