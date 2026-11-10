import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import UserMenu from './UserMenu';
import { useTheme } from '@/hooks/use-theme';
import { RefreshProvider } from '@/context/RefreshContext';
import { getBreadcrumbs, getPageTitle } from '@/config/navigation';
import { CommandPalette } from '@/components/ds/CommandPalette';
import { MobileDrawer, MobileTabBar } from '@/components/ds/MobileNav';
import { LogoMark } from '@/components/ds/Logo';
import { Kbd } from '@/components/ds/primitives';
import { Icon } from '@/components/ds/Icon';
import { PageErrorBoundary } from '@/components/ds/PageErrorBoundary';
import { cn } from '@/lib/utils';

interface LayoutProps {
  children: React.ReactNode;
  /** Optional override for the last breadcrumb (kept for existing callers). */
  title?: string;
}

const iconBtn =
  'flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors duration-150 hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

/**
 * App shell: sidebar (desktop), top bar with breadcrumbs and search, content
 * area and drawer + bottom tabs (mobile). The assistant is docked in App.tsx.
 * Every routed page renders inside this.
 */
const Layout: React.FC<LayoutProps> = ({ children, title }) => {
  const loc = useLocation();
  const { theme, toggleTheme } = useTheme();
  const [searchOpen, setSearchOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const crumbs = getBreadcrumbs(loc.pathname);
  if (title && crumbs.length) crumbs[crumbs.length - 1] = { label: title };

  useEffect(() => {
    document.title = `${title || getPageTitle(loc.pathname)} · Nexus AI`;
  }, [loc.pathname, title]);

  return (
    <RefreshProvider>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground"
      >
        Skip to content
      </a>

      <div className="flex h-[100dvh] overflow-hidden bg-background text-foreground">
        <Sidebar />

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {/* Top bar */}
          <header className="flex h-[var(--topbar-h)] shrink-0 items-center gap-3 border-b border-border bg-header px-3 sm:px-5 lg:px-8">
            <div className="flex min-w-0 flex-1 items-center gap-2">
              <button type="button" onClick={() => setMenuOpen(true)} aria-label="Open menu" className={cn(iconBtn, 'lg:hidden')}>
                <Icon name="menu" className="h-[18px] w-[18px]" />
              </button>
              <Link to="/" aria-label="Nexus AI home" className="mr-1 lg:hidden">
                <LogoMark className="h-6 w-6 [--logo-bg:var(--header)]" />
              </Link>

              <nav aria-label="Breadcrumb" className="min-w-0">
                <ol className="flex min-w-0 items-center gap-1.5 text-sm">
                  {crumbs.map((c, i) => {
                    const last = i === crumbs.length - 1;
                    return (
                      <li key={`${c.label}-${i}`} className={cn('flex min-w-0 items-center gap-1.5', !last && 'hidden sm:flex')}>
                        {i > 0 && <span className="hidden text-subtle-foreground sm:block" aria-hidden="true">/</span>}
                        {c.path && !last ? (
                          <Link to={c.path} className="truncate text-muted-foreground transition-colors hover:text-foreground">{c.label}</Link>
                        ) : (
                          <span className={cn('truncate', last ? 'font-medium text-foreground' : 'text-muted-foreground')} aria-current={last ? 'page' : undefined}>
                            {c.label}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ol>
              </nav>
            </div>

            {/* Search */}
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="hidden h-8 w-full max-w-[340px] items-center gap-2 rounded-md border border-border bg-surface-2/60 px-2.5 text-sm text-subtle-foreground transition-colors duration-150 hover:border-border-strong hover:text-muted-foreground md:flex"
            >
              <Icon name="search" />
              <span className="flex-1 text-left">Search or jump to…</span>
              <span className="flex items-center gap-0.5"><Kbd>Ctrl</Kbd><Kbd>K</Kbd></span>
            </button>

            <div className="flex shrink-0 items-center gap-0.5 md:flex-1 md:justify-end">
              <button type="button" onClick={() => setSearchOpen(true)} aria-label="Search" className={cn(iconBtn, 'md:hidden')}>
                <Icon name="search" className="h-[18px] w-[18px]" />
              </button>
              <button type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} className={iconBtn}>
                <span key={theme} className="animate-scale-in">
                  <Icon name={theme === 'dark' ? 'sun' : 'moon'} className="h-[18px] w-[18px]" />
                </span>
              </button>
              <div className="ml-2"><UserMenu /></div>
            </div>
          </header>

          {/* Content */}
          <main id="main" tabIndex={-1} className="scroll-thin relative min-h-0 flex-1 overflow-auto focus:outline-none">
            <div className="min-h-full animate-fade-in">
              <PageErrorBoundary resetKey={loc.pathname + loc.search}>
                {children}
              </PageErrorBoundary>
            </div>
          </main>

          <MobileTabBar onOpenMenu={() => setMenuOpen(true)} />
        </div>
      </div>

      <MobileDrawer open={menuOpen} onOpenChange={setMenuOpen} onOpenSearch={() => setSearchOpen(true)} />
      <CommandPalette open={searchOpen} onOpenChange={setSearchOpen} />
    </RefreshProvider>
  );
};

export default Layout;
