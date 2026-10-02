import { Badge } from '@/components/ui/badge';
import type { SimulatorCoverageReport } from '@/services/connectorApiWorkbenchService';

interface Props {
  report: SimulatorCoverageReport;
}

export default function SimulatorCoverageSection({ report }: Props) {
  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <Stat label="Tables" value={report.totals.tables} />
        <Stat
          label="Blocking (empty)"
          value={report.totals.blocking}
          tone={report.totals.blocking ? 'red' : 'green'}
        />
        <Stat
          label="Health"
          value={report.overall}
          tone={report.overall === 'healthy' ? 'green' : 'red'}
        />
      </div>

      {report.totals.blocking > 0 && (
        <div className="border-l-2 border-red-500/40 pl-3 py-1 text-xs">
          <div className="text-red-300">
            Empty tables block PATCH canary discovery. Re-seed the simulator
            (or pick alternate hint paths) to unblock these APIs.
          </div>
        </div>
      )}

      <div className="border rounded-md max-h-96 overflow-auto">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 bg-muted/40">
            <tr className="text-left">
              <th className="px-2 py-1">schema.table</th>
              <th className="px-2 py-1">sim</th>
              <th className="px-2 py-1">rows</th>
              <th className="px-2 py-1">used by</th>
              <th className="px-2 py-1">blocking</th>
            </tr>
          </thead>
          <tbody>
            {report.rows.map(r => (
              <tr key={`${r.sim_key}/${r.schema}/${r.table}`} className="border-t border-border/40">
                <td className="px-2 py-1 font-mono text-[10px]">{r.schema}.{r.table}</td>
                <td className="px-2 py-1 text-muted-foreground">{r.sim_key}</td>
                <td className={`px-2 py-1 font-mono ${r.row_count === 0 ? 'text-red-300' : ''}`}>
                  {r.row_count}
                </td>
                <td className="px-2 py-1">
                  <div className="flex flex-wrap gap-1">
                    {r.used_by_apis.map(a => (
                      <span key={a} className="px-1.5 py-0.5 rounded bg-muted/40 font-mono text-[10px]">{a}</span>
                    ))}
                  </div>
                </td>
                <td className="px-2 py-1">
                  {r.blocking
                    ? <Badge variant="outline" className="text-[9px] text-red-300 border-red-500/30 bg-red-500/10">blocking</Badge>
                    : <Badge variant="outline" className="text-[9px] text-green-300 border-green-500/30 bg-green-500/10">ok</Badge>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number | string; tone?: 'green' | 'amber' | 'red' }) {
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
