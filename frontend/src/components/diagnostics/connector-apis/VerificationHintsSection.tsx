import { Badge } from '@/components/ui/badge';
import { CheckCircle2, MinusCircle } from 'lucide-react';
import type { VerificationHintsReport } from '@/services/connectorApiWorkbenchService';

interface Props {
  report: VerificationHintsReport;
}

export default function VerificationHintsSection({ report }: Props) {
  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <Stat label="Specs checked" value={report.totals.checked} />
        <Stat label="With hint" value={report.totals.with_hint} tone="green" />
        <Stat label="Without hint" value={report.totals.without_hint} tone={report.totals.without_hint ? 'amber' : 'green'} />
      </div>

      {report.non_verifiable_api_ids.length > 0 && (
        <div className="border-l-2 border-amber-500/40 pl-3 py-1 text-xs">
          <div className="text-amber-300 mb-1">Non-verifiable APIs ({report.non_verifiable_api_ids.length}):</div>
          <div className="flex items-center gap-1 flex-wrap">
            {report.non_verifiable_api_ids.map(a => (
              <span key={a} className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 font-mono text-[10px]">{a}</span>
            ))}
          </div>
        </div>
      )}

      <div className="border rounded-md max-h-96 overflow-auto">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 bg-muted/40">
            <tr className="text-left">
              <th className="px-2 py-1">api_id</th>
              <th className="px-2 py-1">hint</th>
              <th className="px-2 py-1">mode</th>
              <th className="px-2 py-1">schema.table</th>
              <th className="px-2 py-1">pk_col</th>
              <th className="px-2 py-1">pk_arg</th>
              <th className="px-2 py-1">companion</th>
            </tr>
          </thead>
          <tbody>
            {report.rows.map(r => (
              <tr key={r.api_id} className="border-t border-border/40">
                <td className="px-2 py-1 font-mono">{r.api_id}</td>
                <td className="px-2 py-1">
                  {r.has_hint
                    ? <CheckCircle2 className="h-3.5 w-3.5 text-green-300" />
                    : <MinusCircle className="h-3.5 w-3.5 text-amber-400" />}
                </td>
                <td className="px-2 py-1 text-muted-foreground">
                  {r.mode || <span className="italic">-</span>}
                </td>
                <td className="px-2 py-1 font-mono text-[10px]">
                  {r.schema && r.table ? `${r.schema}.${r.table}` : '-'}
                </td>
                <td className="px-2 py-1 font-mono text-[10px]">{r.pk_col || '-'}</td>
                <td className="px-2 py-1 font-mono text-[10px]">{r.pk_arg || '-'}</td>
                <td className="px-2 py-1">
                  {r.has_companion
                    ? <Badge variant="outline" className="text-[9px]">yes</Badge>
                    : <span className="text-muted-foreground text-[10px]">-</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: 'green' | 'amber' | 'red' }) {
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
