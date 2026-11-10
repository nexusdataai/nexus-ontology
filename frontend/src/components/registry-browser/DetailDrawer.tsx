import { useEffect, useState, type ReactNode } from 'react';
import { Sheet, SheetContent, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { StatusPill, type Tone } from '@/components/ds/kit';
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

const BADGE_TONE: Record<string, Tone> = {
  ok: 'success',
  warn: 'warning',
  err: 'danger',
  info: 'neutral',
  muted: 'neutral',
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

  const chips = badges?.(row) || [];
  const sub = subtitle?.(row);

  return (
    <Sheet open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <SheetContent side={side} className={cn('flex flex-col gap-0 p-0', widthClass)}>
        <div className="shrink-0 px-5 pb-4 pr-12 pt-5">
          <SheetTitle className="break-all font-mono text-md font-medium leading-6">{title(row)}</SheetTitle>
          <SheetDescription className={cn('mt-1 text-sm text-muted-foreground', !sub && 'sr-only')}>{sub || 'Details'}</SheetDescription>
          {chips.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5">
              {chips.map((b) => (
                <span key={b.label} title={b.title}>
                  <StatusPill tone={BADGE_TONE[b.tone || 'muted']}>{b.label}</StatusPill>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="min-h-0 flex-1">
          {tabs.length > 0 && tabKey != null && (
            <Tabs value={tabKey} onValueChange={setTabKey} className="flex h-full flex-col">
              <TabsList variant="line" className="shrink-0 px-5">
                {tabs.map((t) => (
                  <TabsTrigger key={t.key} value={t.key}>{t.label}</TabsTrigger>
                ))}
              </TabsList>
              {tabs.map((t) => (
                <TabsContent key={t.key} value={t.key} className="scroll-thin mt-0 min-h-0 flex-1 overflow-auto px-5 py-5">
                  {t.render(row)}
                </TabsContent>
              ))}
            </Tabs>
          )}
        </div>

        {footer && (
          <div className="shrink-0 border-t border-border px-5 py-3">
            {footer(row)}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

export default DetailDrawer;
