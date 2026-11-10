import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, FileText, Copy, Check } from 'lucide-react';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

// Renders a markdown proposal document produced by the
// generate_proposal_doc tool. Supports copy-to-clipboard and shows
// generation metadata.
export function DocumentPreviewWidget({ widget, data, loading }: Props) {
  const [copied, setCopied] = useState(false);
  const rows: any[] = data?.rows ?? [];
  const doc = rows[0]?.body || rows[0]?.document || rows[0]?.markdown || '';
  const generatedAt = rows[0]?.generated_at || rows[0]?.Generated_At;

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(doc);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary" />
          {widget.title}
        </CardTitle>
        <div className="flex items-center gap-2">
          {generatedAt && (
            <Badge variant="outline" className="text-xs">generated {String(generatedAt).slice(0, 19)}</Badge>
          )}
          <Button size="sm" variant="outline" onClick={onCopy} disabled={!doc}>
            {copied ? <Check className="h-3 w-3 mr-1" /> : <Copy className="h-3 w-3 mr-1" />}
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center h-[220px]">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : !doc ? (
          <div className="flex items-center justify-center h-[220px] text-sm text-muted-foreground">
            Run "Generate Proposal" from the chat to see the LLM-grounded document here
          </div>
        ) : (
          <pre className="text-xs whitespace-pre-wrap bg-muted/30 p-3 rounded-md max-h-[420px] overflow-auto font-mono leading-relaxed">
            {doc}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
