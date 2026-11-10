/**
 * Page bar with URL-synced tabs.
 * ----------------------------------------------------------------------------
 * Every tabbed page uses this instead of a hand-built tab strip:
 *
 *   const [tab, setTab] = useUrlTab('sources');
 *   <Tabs value={tab} onValueChange={setTab}>
 *     <PageTabsBar title="Data Plane" description="…" sections={SECTIONS} value={tab} onChange={setTab} />
 *     <TabsContent value="sources">…</TabsContent>
 *   </Tabs>
 *
 * - The active tab lives in the URL (?tab=), so views can be linked and the
 *   browser back button works.
 * - `sections` groups related tabs: the section shows as a line tab, its
 *   items as a compact segment row underneath. A section with one item is a
 *   plain tab. Existing ?tab= values keep working because items keep their
 *   original values.
 */
import * as React from 'react';
import { useSearchParams } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Icon, type IconName } from '@/components/ds/Icon';

export interface TabItem {
  value: string;
  label: string;
}

export interface TabSection {
  label: string;
  icon?: IconName;
  items: TabItem[];
}

/** Read and write the active tab in the URL. Other query params are kept. */
export function useUrlTab(defaultTab: string, param = 'tab'): [string, (v: string) => void] {
  const [searchParams, setSearchParams] = useSearchParams();
  const value = searchParams.get(param) || defaultTab;
  const setValue = React.useCallback((v: string) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      if (v === defaultTab) next.delete(param); else next.set(param, v);
      next.delete('focus');
      return next;
    }, { replace: true });
  }, [defaultTab, param, setSearchParams]);
  return [value, setValue];
}

interface PageTabsBarProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  sections: TabSection[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function PageTabsBar({ title, description, actions, sections, value, onChange, className }: PageTabsBarProps) {
  const activeSection = sections.find(s => s.items.some(i => i.value === value)) || sections[0];
  // Remember the last item visited in each section.
  const lastRef = React.useRef<Record<string, string>>({});
  if (activeSection) lastRef.current[activeSection.label] = value;

  return (
    <div className={cn('border-b border-border bg-background', className)}>
      <div className="px-4 pt-5 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
          <div className="min-w-0">
            <h1 className="text-xl font-medium tracking-tight text-foreground sm:text-2xl">{title}</h1>
            {description && <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
        </div>

        <div role="tablist" aria-label={`${title} sections`} className="scrollbar-hide -mb-px mt-4 flex items-stretch gap-6 overflow-x-auto">
          {sections.map(section => {
            const on = section === activeSection;
            return (
              <button
                key={section.label}
                type="button"
                role="tab"
                aria-selected={on}
                onClick={() => onChange(lastRef.current[section.label] || section.items[0].value)}
                className={cn(
                  'relative flex h-10 shrink-0 items-center gap-2 whitespace-nowrap text-sm font-medium transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  on ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {section.icon && <Icon name={section.icon} className={cn(on ? 'text-primary dark:text-brand-hi' : 'text-subtle-foreground')} />}
                {section.label}
                <span className={cn('absolute inset-x-0 bottom-0 h-0.5 origin-center rounded-full bg-primary transition-transform duration-300 ease-brand-out', on ? 'scale-x-100' : 'scale-x-0')} />
              </button>
            );
          })}
        </div>
      </div>

      {activeSection && activeSection.items.length > 1 && (
        <div className="border-t border-border bg-surface-2/40 px-4 py-2 sm:px-6 lg:px-8">
          <div role="tablist" aria-label={`${activeSection.label} views`} className="scrollbar-hide flex items-center gap-1 overflow-x-auto">
            {activeSection.items.map(item => {
              const on = item.value === value;
              return (
                <button
                  key={item.value}
                  type="button"
                  role="tab"
                  aria-selected={on}
                  onClick={() => onChange(item.value)}
                  className={cn(
                    'h-7 shrink-0 whitespace-nowrap rounded-md px-2.5 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    on ? 'bg-card font-medium text-foreground shadow-xs ring-1 ring-border' : 'text-muted-foreground hover:bg-accent/70 hover:text-foreground',
                  )}
                >
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Full-height working area under a page bar (explorers, editors, canvases).
 * Fills the viewport below the top bar and page bar; scrolls inside.
 */
export function Pane({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn('h-pane min-h-0', className)}>{children}</div>;
}
