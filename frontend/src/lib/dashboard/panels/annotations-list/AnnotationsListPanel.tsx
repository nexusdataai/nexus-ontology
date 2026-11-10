import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { CalendarDays, Tag } from 'lucide-react';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { PanelState } from '../_shared';

export function AnnotationsListPanel({ data, options, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length === 0) {
    return (
      <PanelState loading={loading} text="No annotations" />
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const showTags = (options.showTags as boolean) ?? true;
  const showUser = (options.showUser as boolean) ?? true;
  const limit = (options.limit as number) ?? 50;

  const fieldNames = frame.fields.map((f) => f.name);
  const timeField = fieldNames.find((n) => /time|date|created|timestamp/i.test(n)) || fieldNames[0];
  const textField = fieldNames.find((n) => /text|description|message|content|title/i.test(n)) || (fieldNames.length > 1 ? fieldNames[1] : fieldNames[0]);
  const tagsField = fieldNames.find((n) => /tags?|labels?|categories?/i.test(n));
  const userField = fieldNames.find((n) => /user|author|created_by|owner/i.test(n));

  const items = rows.slice(0, limit).map((row, i) => {
    const rawTags = tagsField ? row[tagsField] : undefined;
    let tags: string[] = [];
    if (rawTags) {
      if (Array.isArray(rawTags)) tags = rawTags.map(String);
      else if (typeof rawTags === 'string') {
        try { tags = JSON.parse(rawTags); } catch { tags = rawTags.split(',').map((s) => s.trim()).filter(Boolean); }
      }
    }

    return {
      id: i,
      time: String(row[timeField] ?? ''),
      text: String(row[textField] ?? ''),
      tags,
      user: userField ? String(row[userField] ?? '') : '',
    };
  });

  const listHeight = Math.max(height - 40, 100);

  return (
    <ScrollArea style={{ height: listHeight }} className="px-4 pb-4">
      <div className="space-y-2">
        {items.length === 0 ? (
          <div className="flex items-center justify-center h-20 text-sm text-muted-foreground">
            No annotations
          </div>
        ) : (
          items.map((item) => (
            <div key={item.id} className="rounded-md border p-3 bg-muted/10">
              <div className="flex items-start gap-2">
                <CalendarDays className="h-3.5 w-3.5 mt-0.5 text-muted-foreground flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs text-muted-foreground font-mono">{item.time}</span>
                    {showUser && item.user && (
                      <span className="text-xs text-muted-foreground">by {item.user}</span>
                    )}
                  </div>
                  <p className="text-xs">{item.text}</p>
                  {showTags && item.tags.length > 0 && (
                    <div className="flex items-center gap-1 mt-1 flex-wrap">
                      <Tag className="h-2.5 w-2.5 text-muted-foreground" />
                      {item.tags.map((tag, ti) => (
                        <Badge key={ti} variant="outline" className="text-xs px-1 py-0">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </ScrollArea>
  );
}
