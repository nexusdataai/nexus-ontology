import { ScrollArea } from '@/components/ui/scroll-area';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';

export function TablePanel({ data, options, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Loading...' : 'No data'}
      </div>
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const visibleColumns = (options.columns as string[]) || frame.fields.map((f) => f.name);
  const tableHeight = Math.max(height - 40, 100);

  return (
    <ScrollArea style={{ height: tableHeight }}>
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-muted/30 sticky top-0 z-10">
            {visibleColumns.map((col) => (
              <th key={col} className="px-3 py-2 text-left font-medium text-muted-foreground">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-muted/20">
              {visibleColumns.map((col) => (
                <td key={col} className="px-3 py-1.5 font-mono max-w-[180px] truncate">
                  {String(row[col] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollArea>
  );
}
