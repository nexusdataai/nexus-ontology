import { useEffect, useState, type ReactNode } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import type { DetailDrawerTab, DetailBadge } from './types';

interface DetailDrawerProps<T> {
  open: boolean;
  row: T | null;
  /** Title shown at the top of the drawer. */
  title: (row: T) => string;
  /** Optional one-line subtitle (e.g. tool description). */
  subtitle?: (row: T) => string | undefined;
  /** Tinted chips rendered next to the title. */
  badges?: (row: T) => DetailBadge[];
  /** Tab definitions; each tab renders any ReactNode from the row. */
  tabs: DetailDrawerTab<T>[];
  /** Optional footer node (typically a Run button). */
  footer?: (row: T) => ReactNode;
  /** Default-selected tab key (defaults to tabs[0].key). */
  defaultTab?: string;
  onClose: () => void;
  /** Side; defaults to right. */
  side?: 'right' | 'left';
  /** Width class for the SheetContent (default w-[640px] / xl 720). */
  widthClass?: string;
}

const BADGE_TONE: Record<string, string> = {
  ok: 'bg-green-500/15 text-green-300 border-green-500/30',
  warn: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  err: 'bg-red-500/15 text-red-300 border-red-500/30',
  info: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  muted: 'bg-muted/40 text-muted-foreground border-border/60',
};

/**
 * Right-side slide-in detail drawer with tabbed content.
 *
 * Generic over the row type; the panel parent decides how to render
 * each tab. Drawer state (selected tab) resets when ``row`` changes
 * identity so opening a different row never leaks the previous tab.
 */
export function DetailDrawer<T>(props: DetailDrawerProps<T>) {
  const {
    open, row, title, subtitle, badges, tabs, footer, defaultTab,
    onClose, side = 'right', widthClass = 'w-full sm:max-w-2xl',
  } = props;

  const [tabKey, setTabKey] = useState<string | null>(defaultTab || tabs[0]?.key || null);

  useEffect(() => {
    // Reset to the default tab whenever we open a different row.
    setTabKey(defaultTab || tabs[0]?.key || null);
  }, [row, defaultTab, tabs]);

  if (!row) return null;

  return (
    <Sheet open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <SheetContent side={side} className={cn('p-0 flex flex-col', widthClass)}>
        <SheetHeader className="p-4 pb-3 border-b">
          <SheetTitle className="text-base flex items-start gap-2 flex-wrap">
            <span className="font-mono">{title(row)}</span>
            {badges?.(row).map((b) => (
              <Badge
                key={b.label}
                variant="outline"
                className={cn('text-[10px]', BADGE_TONE[b.tone || 'muted'])}
                title={b.title}
              >
                {b.label}
              </Badge>
            ))}
          </SheetTitle>
          {subtitle && (
            <SheetDescription className="text-xs text-muted-foreground">
              {subtitle(row)}
            </SheetDescription>
          )}
        </SheetHeader>

        <div className="flex-1 overflow-hidden">
          {tabs.length > 0 && tabKey != null && (
            <Tabs value={tabKey} onValueChange={setTabKey} className="h-full flex flex-col">
              <TabsList className="rounded-none border-b bg-transparent justify-start h-9 px-2 overflow-x-auto">
                {tabs.map((t) => (
                  <TabsTrigger key={t.key} value={t.key} className="text-xs h-7 px-2">
                    {t.label}
                  </TabsTrigger>
                ))}
              </TabsList>
              {tabs.map((t) => (
                <TabsContent key={t.key} value={t.key} className="flex-1 overflow-auto p-3 mt-0">
                  {t.render(row)}
                </TabsContent>
              ))}
            </Tabs>
          )}
        </div>

        {footer && (
          <div className="border-t p-3 bg-card/40">
            {footer(row)}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

export default DetailDrawer;
