import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import type { ToolMappingReport } from '@/services/connectorApiWorkbenchService';

interface Props {
  report: ToolMappingReport;
}

export default function ToolMappingSection({ report }: Props) {
  const [search, setSearch] = useState('');
  const q = search.trim().toLowerCase();

  const apiEntries = Object.entries(report.by_api).sort((a, b) => a[0].localeCompare(b[0]))
    .filter(([k, v]) => !q || k.toLowerCase().includes(q) || v.some(x => x.toLowerCase().includes(q)));
  const toolRows = report.by_tool
    .filter(r => !q || r.tool_id.toLowerCase().includes(q) || (r.connector_api || '').toLowerCase().includes(q));

  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Stat label="Tools" value={report.totals.tools} />
        <Stat label="Bound" value={report.totals.tools_with_binding} tone="green" />
        <Stat label="Orphan tools" value={report.totals.orphan_tools} tone={report.totals.orphan_tools ? 'red' : 'green'} />
        <Stat label="Dangling tools" value={report.totals.dangling_tools} tone={report.totals.dangling_tools ? 'red' : 'green'} />
        <Stat label="Orphan APIs" value={report.totals.orphan_apis} tone={report.totals.orphan_apis ? 'amber' : 'green'} />
      </div>

      <Input
        placeholder="Filter by api_id or tool_id..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="h-7 max-w-xs text-xs"
      />

      {report.orphan_tools.length > 0 && (
        <div className="border-l-2 border-destructive/40 pl-3 py-1 text-xs">
          <div className="text-destructive mb-1">Write tools without connector_api binding ({report.orphan_tools.length}):</div>
          <div className="flex items-center gap-1 flex-wrap">
            {report.orphan_tools.map(t => (
              <span key={t.tool_id} className="px-1.5 py-0.5 rounded bg-destructive/10 text-destructive border border-destructive/30 font-mono text-xs">
                {t.tool_id} ({t.risk_level})
              </span>
            ))}
          </div>
        </div>
      )}

      {report.dangling_tools.length > 0 && (
        <div className="border-l-2 border-destructive/40 pl-3 py-1 text-xs">
          <div className="text-destructive mb-1">Tools binding to unregistered connector_api ({report.dangling_tools.length}):</div>
          <div className="flex items-center gap-1 flex-wrap">
            {report.dangling_tools.map(t => (
              <span key={t} className="px-1.5 py-0.5 rounded bg-destructive/10 text-destructive border border-destructive/30 font-mono text-xs">{t}</span>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div>
          <div className="text-xs font-semibold text-muted-foreground mb-1.5">By API ({apiEntries.length})</div>
          <div className="border rounded-md max-h-72 overflow-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-muted/40">
                <tr className="text-left">
                  <th className="px-2 py-1">api_id</th>
                  <th className="px-2 py-1">tool callers</th>
                </tr>
              </thead>
              <tbody>
                {apiEntries.map(([apiId, callers]) => (
                  <tr key={apiId} className="border-t border-border/40">
                    <td className="px-2 py-1 font-mono">{apiId}</td>
                    <td className="px-2 py-1">
                      {callers.length === 0 ? (
                        <Badge variant="outline" className="text-xs text-warning border-warning/30">orphan</Badge>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {callers.map(c => (
                            <span key={c} className="px-1.5 py-0.5 rounded bg-muted/40 font-mono text-xs">{c}</span>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold text-muted-foreground mb-1.5">By Tool ({toolRows.length})</div>
          <div className="border rounded-md max-h-72 overflow-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-muted/40">
                <tr className="text-left">
                  <th className="px-2 py-1">tool_id</th>
                  <th className="px-2 py-1">risk</th>
                  <th className="px-2 py-1">connector_api</th>
                </tr>
              </thead>
              <tbody>
                {toolRows.map(r => (
                  <tr key={r.tool_id} className="border-t border-border/40">
                    <td className="px-2 py-1 font-mono">{r.tool_id}</td>
                    <td className="px-2 py-1 text-muted-foreground">{r.risk_level}</td>
                    <td className="px-2 py-1 font-mono text-xs">
                      {r.binding_status === 'orphan' ? (
                        <Badge variant="outline" className="text-xs text-destructive border-destructive/30">no binding</Badge>
                      ) : r.binding_status === 'dangling' ? (
                        <Badge variant="outline" className="text-xs text-destructive border-destructive/30">{r.connector_api} (unknown)</Badge>
                      ) : r.connector_api ? (
                        <span>{r.connector_api}</span>
                      ) : (
                        <span className="text-muted-foreground italic">read-only</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: 'green' | 'amber' | 'red' }) {
  const cls = tone === 'green' ? 'text-success'
    : tone === 'amber' ? 'text-warning'
    : tone === 'red' ? 'text-destructive'
    : '';
  return (
    <div>
      <div className="text-muted-foreground text-xs">{label}</div>
      <div className={`font-mono ${cls}`}>{value}</div>
    </div>
  );
}
