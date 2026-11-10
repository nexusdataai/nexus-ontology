import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { StatusPill, type Tone } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { PanelState, fieldLabel, isNumberLike } from '../_shared';

const STATUS_COLUMN = /(^|_)(status|severity|risk_level|priority|state)$/;
const ID_COLUMN = /(^id$|_id$|_number$|^sku$)/;

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
  return Number.isInteger(n) ? n.toLocaleString('en-US') : n.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

export function TablePanel({ data, options, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length === 0) return <PanelState loading={loading} />;

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const columns = (options.columns as string[]) || frame.fields.map((f) => f.name);
  const numeric = (col: string) => !ID_COLUMN.test(col) && rows.slice(0, 5).every(r => r[col] === null || r[col] === undefined || isNumberLike(r[col]));

  return (
    <div className="scroll-thin overflow-auto" style={{ height: Math.max(height, 100) }}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col} scope="col" className={cn('sticky top-0 z-10 whitespace-nowrap border-b border-border bg-surface-2 px-4 py-2 text-xs font-medium text-muted-foreground', numeric(col) ? 'text-right' : 'text-left')}>
                {fieldLabel(col)}
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
                      'max-w-[220px] truncate whitespace-nowrap px-4 py-2',
                      isNum && 'num text-right',
                      ID_COLUMN.test(col) && 'font-mono text-xs text-muted-foreground',
                      ci === 0 && !ID_COLUMN.test(col) && 'font-medium text-foreground',
                    )}
                  >
                    {v === null || v === undefined || v === '' ? (
                      <span className="text-muted-foreground">—</span>
                    ) : STATUS_COLUMN.test(col) ? (
                      <StatusPill status={String(v)} tone={statusTone(String(v))} />
                    ) : isNum ? (
                      formatNumber(col, v)
                    ) : typeof v === 'string' && /^[a-z]+(_[a-z0-9]+)+$/.test(v) ? (
                      fieldLabel(v)
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
  );
}
