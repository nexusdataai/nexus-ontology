import type { DashboardWidget } from '@/config/dashboardWidgets';
import { StatusPill, type Tone } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { WidgetFrame, labelOf, isNumeric } from './WidgetFrame';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

const STATUS_COLUMN = /(^|_)(status|severity|risk_level|priority|state)$/;
const ID_COLUMN = /(^id$|_id$|_number$|^sku$)/;

/** Tones for words toneOf() does not know (order matching vocabulary). */
function statusTone(v: string): Tone | undefined {
  const s = v.toLowerCase();
  if (s === 'matched') return 'success';
  if (s.includes('mismatch')) return 'warning';
  if (s.startsWith('missing')) return 'danger';
  return undefined;
}

function formatNumber(col: string, v: unknown) {
  const n = Number(v);
  if (/(amount|spend|revenue|price|cost|clv|_ar$|(order|invoice|deal|contract|total|open|net|gross)_value)/.test(col)) return `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
  if (/(rate|pct|percent|share)$/.test(col)) return `${(Math.abs(n) <= 1 ? n * 100 : n).toFixed(1)}%`;
  return Number.isInteger(n) ? n.toLocaleString('en-US') : n.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

export function TableWidget({ widget, data, loading }: Props) {
  const rows: any[] = data?.rows ?? [];
  const columns = widget.query.columns ?? (rows.length > 0 ? Object.keys(rows[0]).slice(0, 8) : []);
  const numeric = (col: string) => !ID_COLUMN.test(col) && rows.slice(0, 5).every(r => r[col] === null || r[col] === undefined || isNumeric(r[col]));

  return (
    <WidgetFrame
      title={widget.title}
      aside={rows.length > 0 ? <span className="num text-xs text-muted-foreground">{rows.length} rows</span> : null}
      loading={loading}
      empty={rows.length === 0}
      flush
      minHeight={200}
    >
      <div className="scroll-thin max-h-[340px] overflow-auto border-t border-border">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              {columns.map(col => (
                <th
                  key={col}
                  scope="col"
                  className={cn('sticky top-0 z-10 whitespace-nowrap border-b border-border bg-surface-2 px-5 py-2.5 text-xs font-medium text-muted-foreground', numeric(col) ? 'text-right' : 'text-left')}
                >
                  {labelOf(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-border transition-colors last:border-b-0 hover:bg-surface-2/60">
                {columns.map((col, ci) => {
                  const v = row[col];
                  const isNum = numeric(col);
                  return (
                    <td
                      key={col}
                      className={cn(
                        'max-w-[220px] truncate whitespace-nowrap px-5 py-2.5',
                        isNum && 'num text-right',
                        ID_COLUMN.test(col) && 'font-mono text-xs text-muted-foreground',
                        ci === 0 && !ID_COLUMN.test(col) && 'font-medium text-foreground',
                      )}
                      title={typeof v === 'string' ? v : undefined}
                    >
                      {v === null || v === undefined || v === '' ? (
                        <span className="text-muted-foreground">—</span>
                      ) : STATUS_COLUMN.test(col) ? (
                        <StatusPill status={String(v)} tone={statusTone(String(v))} />
                      ) : isNum ? (
                        formatNumber(col, v)
                      ) : typeof v === 'string' && /^[a-z]+(_[a-z0-9]+)+$/.test(v) ? (
                        labelOf(v)
                      ) : (
                        String(v)
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </WidgetFrame>
  );
}
