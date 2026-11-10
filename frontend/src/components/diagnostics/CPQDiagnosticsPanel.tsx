import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, Play, Server, Database, Link2, Shield, Wrench, Workflow, FileText } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { Section, StatusBadge } from './_shared';

interface DiagSection { status: string; [k: string]: any }

interface CPQDiagReport {
  timestamp: string;
  overall_status: string;
  sections: {
    simulator_status: DiagSection;
    data_adequacy_sell: DiagSection;
    data_adequacy_buy: DiagSection;
    mapping_correctness: DiagSection;
    data_quality: DiagSection;
    tool_registry: DiagSection;
    workflows: DiagSection;
    policies: DiagSection;
  };
}




function EntityTable({ entities }: { entities: any[] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead><tr className="border-b border-border text-left text-xs text-muted-foreground">
        <th className="pb-2 pr-4 font-medium">Entity</th><th className="pb-2 pr-4 font-medium">System</th>
        <th className="pb-2 pr-4 font-medium text-right">Rows</th><th className="pb-2 pr-4 font-medium text-right">Fields</th>
        <th className="pb-2 font-medium">Status</th>
      </tr></thead>
      <tbody>
        {entities.map((e: any) => (
          <tr key={e.name} className="border-b border-border">
            <td className="py-2 pr-4">
              <div className="font-medium">{e.name}</div>
              {e.error && <div className="text-xs text-warning mt-0.5">{e.error}</div>}
            </td>
            <td className="py-2 pr-4 text-muted-foreground font-mono text-xs">{e.system}</td>
            <td className="py-2 pr-4 text-right">{e.rows >= 0 ? e.rows : '—'}</td>
            <td className="py-2 pr-4 text-right">{e.fields || '—'}</td>
            <td className="py-2"><StatusBadge status={e.status} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ToolTable({ tools, title }: { tools: any[]; title: string }) {
  return (
    <div className="mb-4">
      <h4 className="text-xs font-semibold text-muted-foreground mb-2">{title} ({tools.filter(t => t.status === 'ok').length} / {tools.length})</h4>
      <table className="w-full border-collapse text-sm">
        <thead><tr className="border-b border-border text-left text-xs text-muted-foreground">
          <th className="pb-2 pr-4 font-medium">Tool</th><th className="pb-2 pr-4 font-medium">Risk</th>
          <th className="pb-2 pr-4 font-medium">Bucket</th><th className="pb-2 pr-4 font-medium">Approval</th>
          <th className="pb-2 pr-4 font-medium">Connector API</th><th className="pb-2 font-medium">Status</th>
        </tr></thead>
        <tbody>
          {tools.map((t: any) => (
            <tr key={t.name} className="border-b border-border">
              <td className="py-1.5 pr-4 font-mono text-xs">{t.name}</td>
              <td className="py-1.5 pr-4 text-xs">{t.risk || '—'}</td>
              <td className="py-1.5 pr-4 text-xs">{t.bucket || '—'}</td>
              <td className="py-1.5 pr-4 text-xs">{t.requires_approval ? 'required' : '—'}</td>
              <td className="py-1.5 pr-4 font-mono text-xs text-muted-foreground">{t.connector_api || '—'}</td>
              <td className="py-1.5"><StatusBadge status={t.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function CPQDiagnosticsPanel() {
  const [report, setReport] = useState<CPQDiagReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runDiagnostics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.post<CPQDiagReport>('/api/v1/diagnostics/cpq', {});
      setReport(data);
    } catch (e: any) {
      setError(e.message || 'Diagnostics failed');
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="page space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-medium tracking-tight text-foreground">CPQ Solution Diagnostics</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            End-to-end health check for Trade CPQ (sell-side) and Sourcing CPQ (buy-side):
            simulators, virtual entities, mapping rules, quality, ReAct tools, workflows, and policies.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {report && <StatusBadge status={report.overall_status} />}
          <Button onClick={runDiagnostics} disabled={loading}>
            {loading ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Running checks</>
                     : <><Play className="h-4 w-4 mr-2" /> Run checks</>}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/25 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          The checks could not run: {error}
        </div>
      )}

      {report && (
        <div className="space-y-3">
          {report.timestamp && (
            <div className="text-xs text-muted-foreground">
              Last run: {new Date(report.timestamp).toLocaleString()}
            </div>
          )}

          {/* 1. Simulator status */}
          <Section title="Simulator Status (TPM + Sourcing)" icon={Server} status={report.sections.simulator_status.status}>
            <div className="space-y-2">
              {report.sections.simulator_status.checks.map((c: any) => (
                <div key={c.key} className="flex items-center justify-between rounded-lg border border-border p-4">
                  <div>
                    <div className="text-sm font-medium">{c.name}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{c.message}</div>
                    <div className="flex gap-3 text-xs text-muted-foreground mt-1">
                      <span>schema: <span className="font-mono">{c.details?.schema || '—'}</span></span>
                      <span>tables: {c.details?.tables_with_data ?? 0}/{c.details?.tables ?? 0}</span>
                      <span>rows: {(c.details?.total_rows ?? 0).toLocaleString()}</span>
                    </div>
                  </div>
                  <StatusBadge status={c.status} />
                </div>
              ))}
            </div>
          </Section>

          {/* 2. Data adequacy — Sell */}
          <Section title="Data Adequacy — Trade CPQ (Sell-Side)" icon={Database} status={report.sections.data_adequacy_sell.status}>
            <div className="text-xs text-muted-foreground mb-3">
              {report.sections.data_adequacy_sell.summary.with_data} of {report.sections.data_adequacy_sell.summary.total} entities have data
            </div>
            <EntityTable entities={report.sections.data_adequacy_sell.entities} />
          </Section>

          {/* 3. Data adequacy — Buy */}
          <Section title="Data Adequacy — Sourcing CPQ (Buy-Side)" icon={Database} status={report.sections.data_adequacy_buy.status}>
            <div className="text-xs text-muted-foreground mb-3">
              {report.sections.data_adequacy_buy.summary.with_data} of {report.sections.data_adequacy_buy.summary.total} entities have data
            </div>
            <EntityTable entities={report.sections.data_adequacy_buy.entities} />
          </Section>

          {/* 4. Mapping correctness */}
          <Section title="Mapping Correctness" icon={Link2} status={report.sections.mapping_correctness.status} defaultOpen={false}>
            <div className="text-xs text-muted-foreground mb-3">
              {report.sections.mapping_correctness.summary.active} of {report.sections.mapping_correctness.summary.total} mapping rules active
              {report.sections.mapping_correctness.summary.issues > 0 &&
                <span className="text-warning ml-2">({report.sections.mapping_correctness.summary.issues} issues — click Auto-Map in Mapping Rules)</span>}
            </div>
            <table className="w-full border-collapse text-sm">
              <thead><tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="pb-2 pr-4 font-medium">Entity</th><th className="pb-2 pr-4 font-medium">Source Schema</th>
                <th className="pb-2 pr-4 font-medium">Source Table</th>
                <th className="pb-2 pr-4 font-medium text-right">Mapped Fields</th>
                <th className="pb-2 font-medium">Status</th>
              </tr></thead>
              <tbody>
                {report.sections.mapping_correctness.rules.map((r: any) => (
                  <tr key={r.entity} className="border-b border-border">
                    <td className="py-1.5 pr-4 font-medium">{r.entity}</td>
                    <td className="py-1.5 pr-4 font-mono text-xs text-muted-foreground">{r.source_schema || '—'}</td>
                    <td className="py-1.5 pr-4 font-mono text-xs">{r.source_table || '—'}</td>
                    <td className="py-1.5 pr-4 text-right">{r.mapped_fields}</td>
                    <td className="py-1.5"><StatusBadge status={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          {/* 5. Data quality */}
          <Section title="Data Quality (Null %)" icon={Shield} status={report.sections.data_quality.status} defaultOpen={false}>
            <div className="text-xs text-muted-foreground mb-3">
              {report.sections.data_quality.summary.passed} passed,
              {report.sections.data_quality.summary.warnings > 0 && <span className="text-warning ml-1">{report.sections.data_quality.summary.warnings} warnings,</span>}
              {report.sections.data_quality.summary.failures > 0 && <span className="text-destructive ml-1">{report.sections.data_quality.summary.failures} failures</span>}
              <span className="ml-1">out of {report.sections.data_quality.summary.total_checks} checks</span>
            </div>
            <table className="w-full border-collapse text-sm">
              <thead><tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="pb-2 pr-4 font-medium">Entity</th><th className="pb-2 pr-4 font-medium">Field</th>
                <th className="pb-2 pr-4 font-medium text-right">Nulls</th>
                <th className="pb-2 pr-4 font-medium text-right">Null %</th>
                <th className="pb-2 font-medium">Status</th>
              </tr></thead>
              <tbody>
                {report.sections.data_quality.checks.map((c: any, i: number) => (
                  <tr key={`${c.entity}-${c.field}-${i}`} className="border-b border-border">
                    <td className="py-1.5 pr-4 font-medium">{c.entity}</td>
                    <td className="py-1.5 pr-4 font-mono text-xs">{c.field}</td>
                    <td className="py-1.5 pr-4 text-right">{c.null_count} / {c.total_rows}</td>
                    <td className="py-1.5 pr-4 text-right">{c.null_pct}%</td>
                    <td className="py-1.5"><StatusBadge status={c.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          {/* 6. Tool registry */}
          <Section title="ReAct Tool Registry" icon={Wrench} status={report.sections.tool_registry.status}>
            <div className="text-xs text-muted-foreground mb-3">
              {report.sections.tool_registry.summary.registered} of {report.sections.tool_registry.summary.expected} CPQ tools registered
            </div>
            <ToolTable tools={report.sections.tool_registry.sell_tools} title="Sell-side (Trade CPQ)" />
            <ToolTable tools={report.sections.tool_registry.buy_tools} title="Buy-side (Sourcing CPQ)" />
          </Section>

          {/* 7. Workflows */}
          <Section title="Workflows" icon={Workflow} status={report.sections.workflows.status}>
            <div className="text-xs text-muted-foreground mb-3">
              {report.sections.workflows.summary.present} of {report.sections.workflows.summary.expected} workflow YAMLs present
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground mb-2">Sell-Side</h4>
                <ul className="space-y-1">
                  {report.sections.workflows.sell_workflows.map((w: any) => (
                    <li key={w.id} className="flex items-center justify-between rounded border p-2">
                      <div>
                        <div className="text-xs font-medium">{w.name || w.id}</div>
                        <div className="text-xs text-muted-foreground font-mono">{w.file || w.id}</div>
                      </div>
                      <StatusBadge status={w.status} />
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground mb-2">Buy-Side</h4>
                <ul className="space-y-1">
                  {report.sections.workflows.buy_workflows.map((w: any) => (
                    <li key={w.id} className="flex items-center justify-between rounded border p-2">
                      <div>
                        <div className="text-xs font-medium">{w.name || w.id}</div>
                        <div className="text-xs text-muted-foreground font-mono">{w.file || w.id}</div>
                      </div>
                      <StatusBadge status={w.status} />
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Section>

          {/* 8. Policies */}
          <Section title="Policies" icon={FileText} status={report.sections.policies.status}>
            <ul className="space-y-1">
              {report.sections.policies.policies.map((p: any) => (
                <li key={p.id} className="flex items-center justify-between rounded border p-2">
                  <div>
                    <div className="text-xs font-medium">{p.id}</div>
                    <div className="text-xs text-muted-foreground font-mono">{p.file} · {p.size_bytes} bytes</div>
                  </div>
                  <StatusBadge status={p.status} />
                </li>
              ))}
            </ul>
          </Section>
        </div>
      )}
    </div>
  );
}
