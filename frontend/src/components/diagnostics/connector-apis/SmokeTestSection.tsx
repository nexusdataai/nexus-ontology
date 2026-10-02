import { Badge } from '@/components/ui/badge';
import { Loader2, CheckCircle2, XCircle, MinusCircle } from 'lucide-react';
import { formatLatency } from '../_shared';
import type { SmokeReport, Verdict } from '@/services/connectorApiWorkbenchService';

interface Props {
  report: SmokeReport | null;
  loading: boolean;
  skipHighRisk: boolean;
  onSkipHighRiskChange: (v: boolean) => void;
}

function verdictIcon(v?: Verdict) {
  if (v === 'verified') return <CheckCircle2 className="h-3.5 w-3.5 text-green-300" />;
  if (v === 'http_error') return <XCircle className="h-3.5 w-3.5 text-red-300" />;
  return <MinusCircle className="h-3.5 w-3.5 text-amber-300" />;
}

function verdictColor(v?: Verdict): string {
  if (v === 'verified') return 'text-green-300';
  if (v === 'http_error') return 'text-red-300';
  return 'text-amber-300';
}

export default function SmokeTestSection({
  report, loading, skipHighRisk, onSkipHighRiskChange,
}: Props) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center gap-3 flex-wrap text-xs">
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="checkbox"
            checked={skipHighRisk}
            onChange={(e) => onSkipHighRiskChange(e.target.checked)}
          />
          <span>skip high-risk writes</span>
        </label>
        <span className="text-muted-foreground italic">
          Smoke writes are tagged actor=diagnostic-runner.
        </span>
      </div>

      {loading && !report && (
        <div className="text-xs text-muted-foreground italic flex items-center gap-2">
          <Loader2 className="h-3 w-3 animate-spin" /> Driving every API through invoke...
        </div>
      )}

      {!loading && !report && (
        <div className="text-xs text-muted-foreground">
          Click <span className="font-mono">Run all</span> in the section header to drive every Connector API through the invoke route. Each call runs against the live simulator with a discovered canary payload.
        </div>
      )}

      {report && (
        <>
          <div className="flex items-center gap-3 flex-wrap text-xs">
            <span className="text-muted-foreground">total: <span className="font-mono">{report.totals.checked}</span></span>
            <span className="text-green-300">verified: <span className="font-mono">{report.totals.verified}</span></span>
            <span className="text-amber-300">no_change: <span className="font-mono">{report.totals.no_change}</span></span>
            <span className="text-amber-300">audit_missing: <span className="font-mono">{report.totals.audit_missing}</span></span>
            <span className="text-red-300">http_error: <span className="font-mono">{report.totals.http_error}</span></span>
            <span className="text-muted-foreground">| total time: {formatLatency(report.totals.duration_ms)}</span>
          </div>

          <div className="border rounded-md max-h-[28rem] overflow-auto">
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-muted/40">
                <tr className="text-left">
                  <th className="px-2 py-1"></th>
                  <th className="px-2 py-1">api_id</th>
                  <th className="px-2 py-1">verdict</th>
                  <th className="px-2 py-1">http</th>
                  <th className="px-2 py-1">latency</th>
                  <th className="px-2 py-1">diff / count</th>
                  <th className="px-2 py-1">audit</th>
                  <th className="px-2 py-1">error</th>
                </tr>
              </thead>
              <tbody>
                {report.results.map(r => {
                  const v = r.verification;
                  const isPatch = v?.mode === 'patch';
                  const diffStr = isPatch
                    ? (v?.row_diff?.length ? v.row_diff.join(', ') : '-')
                    : v
                      ? `+${(v.row_count_after ?? 0) - (v.row_count_before ?? 0)} row`
                      : '-';
                  const audit = v?.audit_event;
                  return (
                    <tr key={r.api_id} className="border-t border-border/40">
                      <td className="px-2 py-1">{verdictIcon(r.verdict)}</td>
                      <td className="px-2 py-1 font-mono">{r.api_id}</td>
                      <td className="px-2 py-1">
                        <Badge
                          variant="outline"
                          className={`text-[9px] ${verdictColor(r.verdict)} ${
                            r.verdict === 'verified' ? 'border-green-500/30 bg-green-500/10'
                            : r.verdict === 'http_error' ? 'border-red-500/30 bg-red-500/10'
                            : 'border-amber-500/30 bg-amber-500/10'
                          }`}
                        >{r.verdict}</Badge>
                      </td>
                      <td className="px-2 py-1 font-mono">{r.http_status ?? '-'}</td>
                      <td className="px-2 py-1 font-mono">{formatLatency(r.duration_ms)}</td>
                      <td className="px-2 py-1 text-[10px] text-muted-foreground">{diffStr}</td>
                      <td className="px-2 py-1">
                        {audit ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-green-300" />
                        ) : (
                          <MinusCircle className="h-3.5 w-3.5 text-amber-400" />
                        )}
                      </td>
                      <td className="px-2 py-1 text-[10px] text-red-300 max-w-xs truncate">
                        {r.http_error || ''}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
