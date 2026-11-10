import { useState } from 'react';
import { cn } from '@/lib/utils';
import { useNavigate } from 'react-router-dom';
import type { AppConfig } from '@/config/appRegistry';
import type { Solution } from '@/lib/foundry/model';
import { Icon, type IconName } from '@/components/ds/Icon';
import { LogoMark } from '@/components/ds/Logo';

interface Props {
  app: AppConfig;
  solution: Solution | null;
  activeSection: string;
  onSectionChange: (sectionId: string) => void;
  /** Rendered inside the mobile drawer: always expanded, no collapse control. */
  inDrawer?: boolean;
}

const WORKSPACE_ITEMS: { id: string; name: string; icon: IconName }[] = [
  { id: 'agent-builder', name: 'Agent Builder', icon: 'bot' },
  { id: 'tools-catalogue', name: 'Tools Catalogue', icon: 'wrench' },
];

const row = 'group flex h-8 w-full items-center rounded-md text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';
const rowIdle = 'text-sidebar-foreground hover:bg-accent/70 hover:text-foreground';
const rowOn = 'bg-accent font-medium text-foreground';

/** Sidebar of a solution app. Same visual language as the main sidebar. */
export function AppSidebar({ app, solution, activeSection, onSectionChange, inDrawer }: Props) {
  const nav = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const mini = collapsed && !inDrawer;
  const AppIcon = app.icon;
  const layout = mini ? 'justify-center' : 'gap-2.5 px-2';
  const iconCls = (on: boolean) => cn('h-[17px] w-[17px] shrink-0', on ? 'text-primary dark:text-brand-hi' : 'text-subtle-foreground group-hover:text-foreground');

  const label = (text: string, first?: boolean) => mini
    ? (!first && <div className="mx-1.5 my-3 border-t border-sidebar-border" />)
    : <div className={cn('eyebrow px-2 pb-1.5', !first && 'pt-5')}>{text}</div>;

  return (
    <aside className={cn(
      'flex h-full shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-300 ease-brand-out',
      inDrawer ? 'w-full border-r-0' : mini ? 'w-[var(--sidebar-w-mini)]' : 'w-[var(--sidebar-w)]',
    )}>
      {/* Back to the platform */}
      <div className={cn('flex h-[var(--topbar-h)] shrink-0 items-center', mini ? 'justify-center px-2' : 'px-3')}>
        <button
          type="button"
          onClick={() => nav('/workspace/apps')}
          aria-label="Back to Solutions"
          className={cn(row, rowIdle, mini ? 'justify-center' : 'gap-2 px-2')}
        >
          <Icon name="chevron-left" className="shrink-0 text-subtle-foreground group-hover:text-foreground" />
          {!mini && <><LogoMark className="h-5 w-5" /><span className="truncate">Solutions</span></>}
        </button>
      </div>

      {/* App identity */}
      {!mini && (
        <div className="flex items-center gap-2.5 border-b border-sidebar-border px-5 pb-4 pt-1">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-card text-primary dark:text-brand-hi">
            <AppIcon className="h-[18px] w-[18px]" strokeWidth={1.6} />
          </span>
          <div className="min-w-0">
            <div className="truncate text-sm font-medium text-foreground">{app.shortName}</div>
            <div className="truncate text-xs text-muted-foreground">{app.status === 'available' ? 'Active' : 'Coming soon'}</div>
          </div>
        </div>
      )}

      <nav aria-label={`${app.name} sections`} className={cn('scrollbar-hide min-h-0 flex-1 overflow-y-auto py-4', mini ? 'px-2' : 'px-3')}>
        {label('Analytics', true)}
        <div className="space-y-px">
          {app.sections.map(section => {
            const SIcon = section.icon;
            const on = activeSection === section.id;
            return (
              <button
                key={section.id}
                type="button"
                onClick={() => onSectionChange(section.id)}
                aria-current={on ? 'page' : undefined}
                title={mini ? section.name : undefined}
                className={cn(row, layout, on ? rowOn : rowIdle)}
              >
                <SIcon className={iconCls(on)} strokeWidth={1.6} />
                {!mini && <span className="truncate">{section.name}</span>}
              </button>
            );
          })}
        </div>

        {/* Views attached to this solution in AI Analytics */}
        {solution && solution.views.length > 0 && (
          <>
            {label('Views')}
            <div className="space-y-px">
              {solution.views.map((link) => {
                const sectionId = `view:${link.viewId}`;
                const on = activeSection === sectionId;
                const text = link.displayName || link.name || link.viewId;
                return (
                  <button
                    key={link.viewId}
                    type="button"
                    onClick={() => onSectionChange(sectionId)}
                    aria-current={on ? 'page' : undefined}
                    title={mini ? text : undefined}
                    className={cn(row, layout, on ? rowOn : rowIdle)}
                  >
                    <Icon name="dashboard" className={iconCls(on)} />
                    {!mini && <span className="truncate">{text}</span>}
                  </button>
                );
              })}
            </div>
          </>
        )}

        {label('Workspace')}
        <div className="space-y-px">
          {WORKSPACE_ITEMS.map(item => {
            const on = activeSection === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSectionChange(item.id)}
                aria-current={on ? 'page' : undefined}
                title={mini ? item.name : undefined}
                className={cn(row, layout, on ? rowOn : rowIdle)}
              >
                <Icon name={item.icon} className={iconCls(on)} />
                {!mini && <span className="truncate">{item.name}</span>}
              </button>
            );
          })}
        </div>
      </nav>

      {!inDrawer && (
        <div className={cn('border-t border-sidebar-border py-2.5', mini ? 'px-2' : 'px-3')}>
          <button
            type="button"
            onClick={() => setCollapsed(m => !m)}
            aria-label={mini ? 'Expand sidebar' : 'Collapse sidebar'}
            className={cn(row, rowIdle, layout)}
          >
            <Icon name={mini ? 'chevrons-right' : 'chevrons-left'} className="shrink-0 text-subtle-foreground group-hover:text-foreground" />
            {!mini && <span>Collapse</span>}
          </button>
        </div>
      )}
    </aside>
  );
}
