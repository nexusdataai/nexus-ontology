import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Loader2, Play, CheckCircle2, XCircle, AlertTriangle, ChevronDown, ChevronRight,
  Database, Link2, Table2, Shield, BarChart3,
} from 'lucide-react';
import { apiClient } from '@/services/apiClient';

interface DiagSection {
  status: string;
  [key: string]: any;
}

interface DiagReport {
  timestamp: string;
  overall_status: string;
  sections: {
    data_adequacy: DiagSection;
    mapping_correctness: DiagSection;
    data_after_mapping: DiagSection;
    data_quality: DiagSection;
    results_analysis: DiagSection;
  };
}

const STATUS_BADGE: Record<string, { cls: string; icon: React.ElementType; label: string }> = {
  pass: { cls: 'bg-green-500/20 text-green-300 border-green-500/30', icon: CheckCircle2, label: 'Pass' },
  ok: { cls: 'bg-green-500/20 text-green-300 border-green-500/30', icon: CheckCircle2, label: 'OK' },
  warn: { cls: 'bg-amber-500/20 text-amber-300 border-amber-500/30', icon: AlertTriangle, label: 'Warning' },
  fail: { cls: 'bg-red-500/20 text-red-300 border-red-500/30', icon: XCircle, label: 'Fail' },
  no_data: { cls: 'bg-red-500/20 text-red-300 border-red-500/30', icon: XCircle, label: 'No Data' },
  missing: { cls: 'bg-red-500/20 text-red-300 border-red-500/30', icon: XCircle, label: 'Missing' },
  inactive: { cls: 'bg-amber-500/20 text-amber-300 border-amber-500/30', icon: AlertTriangle, label: 'Inactive' },
  error: { cls: 'bg-red-500/20 text-red-300 border-red-500/30', icon: XCircle, label: 'Error' },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_BADGE[status] || STATUS_BADGE.fail;
  const Icon = cfg.icon;
  return (
    <Badge variant="outline" className={`${cfg.cls} gap-1`}>
      <Icon className="h-3 w-3" /> {cfg.label}
    </Badge>
  );
}

function Section({ title, icon: Icon, status, defaultOpen, children }: {
  title: string; icon: React.ElementType; status: string; defaultOpen?: boolean; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen ?? true);
  return (
    <Card>
      <CardHeader className="pb-2 cursor-pointer" onClick={() => setOpen(!open)}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            <Icon className="h-4 w-4" /> {title}
          </CardTitle>
          <StatusBadge status={status} />
        </div>
      </CardHeader>
      {open && <CardContent>{children}</CardContent>}
    </Card>
  );
}

export default function IODiagnosticsPanel() {
  const [report, setReport] = useState<DiagReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runDiagnostics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.post<DiagReport>('/api/v1/diagnostics/io', {});
      setReport(data);
    } catch (e: any) {
      setError(e.message || 'Diagnostics failed');
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="p-6 space-y-4 max-w-[1200px] mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold mb-1">Inventory Optimization Diagnostics</h2>
          <p className="text-sm text-muted-foreground">Live diagnostic checks for the Inventory Optimization pipeline</p>
        </div>
        <div className="flex items-center gap-3">
          {report && <StatusBadge status={report.overall_status} />}
          <Button onClick={runDiagnostics} disabled={loading}>
            {loading ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Running...</> : <><Play className="h-4 w-4 mr-2" /> Run Diagnostics</>}
          </Button>
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          Diagnostics failed: {error}
        </div>
      )}

      {report && (
        <div className="space-y-3">
          {report.timestamp && (
            <div className="text-xs text-muted-foreground">Last run: {new Date(report.timestamp).toLocaleString()}</div>
          )}

          <Section title="Data Adequacy" icon={Database} status={report.sections.data_adequacy.status}>
            <div className="text-xs text-muted-foreground mb-3">
              {report.sections.data_adequacy.summary.with_data} of {report.sections.data_adequacy.summary.total_entities} entities have data
            </div>
            <table className="w-full text-xs">
              <thead><tr className="text-left text-muted-foreground border-b">
                <th className="pb-2 pr-4">Entity</th><th className="pb-2 pr-4">System</th>
                <th className="pb-2 pr-4 text-right">Rows</th><th className="pb-2 pr-4 text-right">Fields</th>
                <th className="pb-2">Status</th>
              </tr></thead>
              <tbody>
                {report.sections.data_adequacy.entities.map((e: any) => (
                  <tr key={e.name} className="border-b border-border/50">
                    <td className="py-2 pr-4">
                      <div className="font-medium">{e.name}</div>
                      {e.error && <div className="text-[10px] text-amber-400 mt-0.5">{e.error}</div>}
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">{e.system}</td>
                    <td className="py-2 pr-4 text-right">{e.rows >= 0 ? e.rows : '—'}</td>
                    <td className="py-2 pr-4 text-right">{e.fields || '—'}</td>
                    <td className="py-2"><StatusBadge status={e.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section title="Mapping Correctness" icon={Link2} status={report.sections.mapping_correctness.status}>
            <div className="text-xs text-muted-foreground mb-3">
              {report.sections.mapping_correctness.summary.active} of {report.sections.mapping_correctness.summary.total_rules} rules active
              {report.sections.mapping_correctness.summary.issues > 0 &&
                <span className="text-amber-400 ml-2">({report.sections.mapping_correctness.summary.issues} issues)</span>}
            </div>
            <table className="w-full text-xs">
              <thead><tr className="text-left text-muted-foreground border-b">
                <th className="pb-2 pr-4">Entity</th><th className="pb-2 pr-4">Source Table</th>
                <th className="pb-2 pr-4">Schema</th><th className="pb-2 pr-4">Type</th>
                <th className="pb-2 pr-4 text-right">Mapped</th><th className="pb-2 pr-4 text-right">Unmapped</th>
                <th className="pb-2">Status</th>
              </tr></thead>
              <tbody>
                {report.sections.mapping_correctness.rules.map((r: any) => (
                  <tr key={r.entity} className={`border-b border-border/50 ${r.issue ? 'bg-amber-500/5' : ''}`}>
                    <td className="py-2 pr-4">
                      <div className="font-medium">{r.entity}</div>
                      {r.issue && <div className="text-[10px] text-amber-400 mt-0.5">{r.issue}</div>}
                      {r.rule_name && <div className="text-[10px] text-muted-foreground">{r.rule_name}</div>}
                    </td>
                    <td className="py-2 pr-4 font-mono text-[10px]">{r.source_table || '—'}</td>
                    <td className="py-2 pr-4 text-muted-foreground">{r.source_schema || '—'}</td>
                    <td className="py-2 pr-4 text-muted-foreground">{r.source_type || '—'}</td>
                    <td className="py-2 pr-4 text-right">{r.mapped_fields}</td>
                    <td className="py-2 pr-4 text-right">{r.unmapped_fields > 0 ? <span className="text-amber-400">{r.unmapped_fields}</span> : 0}</td>
                    <td className="py-2"><StatusBadge status={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section title="Data after Mapping" icon={Table2} status={report.sections.data_after_mapping.status}>
            <div className="space-y-2">
              {report.sections.data_after_mapping.queries.map((q: any) => (
                <div key={q.entity} className="rounded-lg border p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium">{q.entity}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground">{q.rows_returned} rows</span>
                      <StatusBadge status={q.status} />
                    </div>
                  </div>
                  {q.field_keys.length > 0 && (
                    <div className="text-[10px] text-muted-foreground">
                      Fields: {q.field_keys.join(', ')}
                    </div>
                  )}
                  {q.sample_row && Object.keys(q.sample_row).length > 0 && (
                    <pre className="text-[10px] mt-1 bg-muted/30 rounded px-2 py-1 font-mono overflow-x-auto">
                      {JSON.stringify(q.sample_row, null, 2)}
                    </pre>
                  )}
                  {q.error && <div className="text-[10px] text-red-400 mt-1">{q.error}</div>}
                </div>
              ))}
            </div>
          </Section>

          <Section title="Data Quality" icon={Shield} status={report.sections.data_quality.status}>
            <div className="text-xs text-muted-foreground mb-3">
              {report.sections.data_quality.summary.passed} passed, {' '}
              {report.sections.data_quality.summary.warnings > 0 && <span className="text-amber-400">{report.sections.data_quality.summary.warnings} warnings, </span>}
              {report.sections.data_quality.summary.failures > 0 && <span className="text-red-400">{report.sections.data_quality.summary.failures} failures</span>}
              {report.sections.data_quality.summary.warnings === 0 && report.sections.data_quality.summary.failures === 0 && 'no issues'}
              <span className="ml-1">out of {report.sections.data_quality.summary.total_checks} checks</span>
            </div>
            <table className="w-full text-xs">
              <thead><tr className="text-left text-muted-foreground border-b">
                <th className="pb-2 pr-4">Entity</th><th className="pb-2 pr-4">Field</th>
                <th className="pb-2 pr-4">Type</th><th className="pb-2 pr-4 text-right">Nulls</th>
                <th className="pb-2 pr-4 text-right">Null %</th><th className="pb-2 pr-4">Present</th>
                <th className="pb-2">Status</th>
              </tr></thead>
              <tbody>
                {report.sections.data_quality.checks.map((c: any, i: number) => (
                  <tr key={`${c.entity}-${c.field}-${i}`} className="border-b border-border/50">
                    <td className="py-1.5 pr-4 font-medium">{c.entity}</td>
                    <td className="py-1.5 pr-4 font-mono text-[10px]">{c.field}</td>
                    <td className="py-1.5 pr-4 text-muted-foreground">{c.type}</td>
                    <td className="py-1.5 pr-4 text-right">{c.null_count}</td>
                    <td className="py-1.5 pr-4 text-right">{c.null_pct}%</td>
                    <td className="py-1.5 pr-4">{c.field_present ? 'Yes' : <span className="text-red-400">No</span>}</td>
                    <td className="py-1.5"><StatusBadge status={c.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section title="Results Analysis" icon={BarChart3} status={report.sections.results_analysis.status}>
            <div className="space-y-3">
              {report.sections.results_analysis.entities.map((e: any) => (
                <div key={e.name} className="rounded-lg border p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium">{e.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground">{e.rows} rows</span>
                      <StatusBadge status={e.status} />
                    </div>
                  </div>
                  {e.kpis && (
                    <div className="grid grid-cols-5 gap-2">
                      {Object.entries(e.kpis).map(([k, v]) => (
                        <div key={k} className="rounded bg-muted/30 px-2 py-1.5 text-center">
                          <div className="text-sm font-bold">{typeof v === 'number' ? (k.includes('pct') || k === 'mape' || k === 'bias' ? `${v}%` : v.toLocaleString()) : String(v)}</div>
                          <div className="text-[9px] text-muted-foreground">{k.replace(/_/g, ' ')}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  {e.alert_count !== undefined && (
                    <div className="text-xs text-muted-foreground">{e.alert_count} active alerts</div>
                  )}
                  {e.summary && (
                    <div className="grid grid-cols-5 gap-2 mt-1">
                      {Object.entries(e.summary).map(([k, v]) => (
                        <div key={k} className="rounded bg-muted/30 px-2 py-1.5 text-center">
                          <div className="text-sm font-bold">{typeof v === 'number' ? v.toLocaleString() : String(v)}</div>
                          <div className="text-[9px] text-muted-foreground">{k.replace(/_/g, ' ')}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  {e.breakdown && (
                    <div className="mt-2 grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-7 gap-1.5">
                      {e.breakdown.map((b: any, i: number) => {
                        const _lbl = new Set(['region','category','plant','vendor_name','segment','material_id','line_id','job_id','processed_at']);
                        const numEntry = Object.entries(b).find(([k, v]) => !_lbl.has(k) && typeof v === 'number');
                        return (
                          <div key={i} className="rounded bg-muted/20 px-2 py-1 text-center">
                            <div className="text-xs font-bold">{numEntry ? Number(numEntry[1]).toLocaleString() : '—'}</div>
                            <div className="text-[9px] text-muted-foreground">{b.region || b.category || b.plant || b.vendor_name || b.segment || b.material_id || b.line_id}</div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {e.error && <div className="text-[10px] text-red-400 mt-1">{e.error}</div>}
                </div>
              ))}
            </div>
          </Section>
        </div>
      )}

      {!report && !loading && !error && (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
          <BarChart3 className="h-10 w-10 opacity-20" />
          <span className="text-sm">Click "Run Diagnostics" to check the Inventory Optimization pipeline</span>
        </div>
      )}
    </div>
  );
}
