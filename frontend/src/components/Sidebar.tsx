import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { NAV_GROUPS, SETTINGS_ITEM, HELP_ITEM, isNavItemActive, type NavItem } from '@/config/navigation';
import { Logo } from '@/components/ds/Logo';
import { Icon, type IconName } from '@/components/ds/Icon';

const MINI_KEY = 'nexus-sidebar-mini';


interface SidebarNavProps {
  /** Icon-only rail. */
  mini?: boolean;
  /** Called after a navigation (used to close the mobile drawer). */
  onNavigate?: () => void;
}

const rowBase =
  'group flex h-8 w-full items-center rounded-md text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';
const rowIdle = 'text-sidebar-foreground hover:bg-accent/70 hover:text-foreground';
const rowActive = 'bg-accent font-medium text-foreground';

/** Wraps a row in a tooltip when the sidebar is collapsed to icons. */
function MiniTip({ label, mini, children }: { label: string; mini?: boolean; children: React.ReactElement }) {
  if (!mini) return children;
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side="right" sideOffset={10}>{label}</TooltipContent>
    </Tooltip>
  );
}

/**
 * Navigation content. Rendered inside the desktop rail and the mobile drawer.
 */
export function SidebarNav({ mini, onNavigate }: SidebarNavProps) {
  const nav = useNavigate();
  const loc = useLocation();
  const go = (path: string) => {
    nav(path);
    onNavigate?.();
  };

  const layout = mini ? 'justify-center' : 'gap-2.5 px-2';
  const iconCls = (on: boolean) => cn('h-[17px] w-[17px] transition-colors', on ? 'text-primary dark:text-brand-hi' : 'text-subtle-foreground group-hover:text-foreground');

  const renderItem = (item: NavItem) => {
    const on = isNavItemActive(item, loc.pathname);
    return (
      <MiniTip key={item.id} label={item.name} mini={mini}>
        <button
          type="button"
          onClick={() => go(item.path)}
          aria-current={on ? 'page' : undefined}
          aria-label={mini ? item.name : undefined}
          className={cn(rowBase, layout, on ? rowActive : rowIdle)}
        >
          <Icon name={item.icon} className={iconCls(on)} />
          {!mini && <span className="truncate">{item.name}</span>}
        </button>
      </MiniTip>
    );
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <nav aria-label="Main" className={cn('scrollbar-hide min-h-0 flex-1 overflow-y-auto pb-3', mini ? 'px-2' : 'px-3')}>
        {NAV_GROUPS.map((group, gi) => (
          <div key={group.label} className={cn(gi > 0 && 'mt-5')}>
            {mini
              ? gi > 0 && <div className="mx-1.5 mb-3 border-t border-sidebar-border" />
              : <div className="eyebrow px-2 pb-1.5">{group.label}</div>}
            <div className="space-y-px">
              {group.items.map(renderItem)}
            </div>
          </div>
        ))}
      </nav>

      <div className={cn('space-y-px border-t border-sidebar-border py-2.5', mini ? 'px-2' : 'px-3')}>
        {renderItem(SETTINGS_ITEM)}
        {renderItem(HELP_ITEM)}
      </div>
    </div>
  );
}

/** Desktop sidebar rail. Hidden below the lg breakpoint (see MobileNav). */
const Sidebar = () => {
  const nav = useNavigate();
  const [mini, setMini] = useState(() => localStorage.getItem(MINI_KEY) === '1');

  useEffect(() => {
    localStorage.setItem(MINI_KEY, mini ? '1' : '0');
  }, [mini]);

  return (
    <aside
      className={cn(
        'relative hidden h-full shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-300 ease-brand-out lg:flex',
        mini ? 'w-[var(--sidebar-w-mini)]' : 'w-[var(--sidebar-w)]',
      )}
    >
      <div className={cn('flex h-[var(--topbar-h)] shrink-0 items-center', mini ? 'justify-center px-2' : 'justify-between pl-5 pr-2.5')}>
        <button type="button" onClick={() => nav('/')} aria-label="Nexus AI home" className="rounded-md">
          <Logo markOnly={mini} />
        </button>
        {!mini && (
          <button
            type="button"
            onClick={() => setMini(true)}
            aria-label="Collapse sidebar"
            className="flex h-7 w-7 items-center justify-center rounded-md text-subtle-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <Icon name="chevron-left" />
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 pt-3">
        <SidebarNav mini={mini} />
      </div>

      {mini && (
        <button
          type="button"
          onClick={() => setMini(false)}
          aria-label="Expand sidebar"
          className="absolute -right-3 top-[14px] z-10 flex h-6 w-6 items-center justify-center rounded-full border border-border-strong bg-card text-muted-foreground shadow-xs transition-colors hover:text-foreground"
        >
          <Icon name="chevron-right" className="h-3.5 w-3.5" />
        </button>
      )}
    </aside>
  );
};

export default Sidebar;
