import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, FileDiff } from 'lucide-react';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

// Show the LLM-drafted contract markdown side-by-side with a baseline
// template (when present). In v1 we render the drafted body and
// highlight non-template lines.
export function ContractDiffWidget({ widget, data, loading }: Props) {
  const rows: any[] = data?.rows ?? [];
  const draft: string = rows[0]?.body || rows[0]?.contract_markdown || '';
  const baseline: string = rows[0]?.baseline || rows[1]?.body || '';

  const draftLines = draft.split('\n');
  const baselineSet = new Set(baseline.split('\n').map((l) => l.trim()).filter(Boolean));

  return (
    <Card className="h-full">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2">
          <FileDiff className="h-4 w-4 text-primary" />
          {widget.title}
        </CardTitle>
        <Badge variant="outline" className="text-xs">
          {baseline ? 'Diff vs template' : 'Draft only'}
        </Badge>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center h-[260px]">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : !draft ? (
          <div className="flex items-center justify-center h-[260px] text-sm text-muted-foreground">
            Run "Draft Contract" from the chat to see the LLM-drafted contract here
          </div>
        ) : (
          <pre className="text-xs whitespace-pre-wrap bg-muted/30 p-3 rounded-md max-h-[420px] overflow-auto font-mono leading-relaxed">
            {draftLines.map((line, i) => {
              const trimmed = line.trim();
              const isNew = baseline && trimmed && !baselineSet.has(trimmed);
              return (
                <span
                  key={i}
                  className={isNew ? 'bg-success/15 block' : 'block'}
                >
                  {line || '\u00A0'}
                </span>
              );
            })}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
