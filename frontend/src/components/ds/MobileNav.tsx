import { useLocation, useNavigate } from 'react-router-dom';
import { Icon } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { ALL_NAV_ITEMS, MOBILE_TAB_IDS, isNavItemActive } from '@/config/navigation';
import { SidebarNav } from '@/components/Sidebar';
import { Logo } from '@/components/ds/Logo';

interface MobileDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenSearch: () => void;
}

/** Full navigation in a left drawer (phones and tablets). */
export function MobileDrawer({ open, onOpenChange, onOpenSearch }: MobileDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="flex w-[280px] flex-col gap-0 border-sidebar-border bg-sidebar p-0 sm:max-w-[280px]">
        <SheetTitle className="sr-only">Navigation</SheetTitle>
        <SheetDescription className="sr-only">Main navigation</SheetDescription>
        <div className="flex h-[var(--topbar-h)] shrink-0 items-center px-4">
          <Logo />
        </div>
        <div className="min-h-0 flex-1 pt-2">
          <SidebarNav
            onNavigate={() => onOpenChange(false)}
          />
        </div>
      </SheetContent>
    </Sheet>
  );
}

/** Bottom tab bar on phones: four main destinations plus "More". */
export function MobileTabBar({ onOpenMenu }: { onOpenMenu: () => void }) {
  const nav = useNavigate();
  const loc = useLocation();
  const tabs = MOBILE_TAB_IDS.map(id => ALL_NAV_ITEMS.find(i => i.id === id)!).filter(Boolean);
  const anyActive = tabs.some(t => isNavItemActive(t, loc.pathname));

  const tabClass = (on: boolean) => cn(
    'relative flex h-full flex-1 flex-col items-center justify-center gap-1 text-xs font-medium transition-colors duration-200',
    on ? 'text-foreground' : 'text-subtle-foreground',
  );

  return (
    <nav
      aria-label="Primary"
      className="flex h-[60px] shrink-0 items-stretch border-t border-border bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
    >
      {tabs.map(item => {
        const on = isNavItemActive(item, loc.pathname);
        return (
          <button key={item.id} type="button" onClick={() => nav(item.path)} aria-current={on ? 'page' : undefined} className={tabClass(on)}>
            <span className={cn('absolute top-0 h-0.5 w-8 rounded-b-full bg-primary transition-transform duration-300 ease-brand-out', on ? 'scale-x-100' : 'scale-x-0')} />
            <Icon name={item.icon} className={cn('h-5 w-5', on && 'text-primary dark:text-brand-hi')} />
            <span className="max-w-full truncate px-1">{item.name.replace('AI ', '')}</span>
          </button>
        );
      })}
      <button type="button" onClick={onOpenMenu} className={tabClass(!anyActive)} aria-label="Open menu">
        <span className={cn('absolute top-0 h-0.5 w-8 rounded-b-full bg-primary transition-transform duration-300 ease-brand-out', !anyActive ? 'scale-x-100' : 'scale-x-0')} />
        <Icon name="menu" className={cn('h-5 w-5', !anyActive && 'text-primary dark:text-brand-hi')} />
        <span>More</span>
      </button>
    </nav>
  );
}
