import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ReportSectionTable } from '@/types/callProcessingJourney';
import { formatValue } from '../formatters';

interface Props {
  section: ReportSectionTable;
}

export function TableSection({ section }: Props) {
  const cols = section.columns || [];
  const rows = section.rows || [];
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{section.title}</CardTitle>
        {section.description && (
          <p className="text-xs text-muted-foreground">{section.description}</p>
        )}
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="px-2 py-1 font-medium">Job</th>
                {cols.map((c) => (
                  <th key={c.key} className="px-2 py-1 font-medium whitespace-nowrap">
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.jobId || i} className="border-b last:border-b-0 hover:bg-muted/30">
                  <td className="px-2 py-1 font-mono text-[11px]">{r.jobId || '--'}</td>
                  {cols.map((c) => (
                    <td key={c.key} className="px-2 py-1">
                      {formatValue(r[c.key], c.format)}
                    </td>
                  ))}
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={cols.length + 1} className="px-2 py-4 text-center text-muted-foreground italic">
                    No data yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

export default TableSection;
