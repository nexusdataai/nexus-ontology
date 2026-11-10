import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import type { AppConfig } from '@/config/appRegistry';
import { AppSidebar } from './AppSidebar';
import { AppOverview } from './sections/AppOverview';
import { AppDashboard } from './sections/AppDashboard';
import { AppAlerts } from './sections/AppAlerts';
import { AppWorkflowActions } from './sections/AppWorkflowActions';
import { AppToolsCatalogue } from './sections/AppToolsCatalogue';
import { ViewRuntime } from '@/components/views/ViewRuntime';
import { solutionService } from '@/services/solutionService';
import type { Solution } from '@/lib/foundry/model';
import { Icon } from '@/components/ds/Icon';
import { PageErrorBoundary } from '@/components/ds/PageErrorBoundary';
import UserMenu from '@/components/UserMenu';
import { useTheme } from '@/hooks/use-theme';

interface Props {
  app: AppConfig;
}

const SECTION_LABELS: Record<string, string> = {
  'agent-builder': 'Agent Builder',
  'tools-catalogue': 'Tools Catalogue',
};

const iconBtn =
  'flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors duration-150 hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

/**
 * Shell of a solution app: its own sidebar (sections, attached views,
 * workspace) and top bar. The active section lives in the URL (?section=).
 */
export function AppShell({ app }: Props) {
  const nav = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeSection = searchParams.get('section') || 'insights';
  const [solution, setSolution] = useState<Solution | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    solutionService
      .getByAppId(app.id)
      .then((s) => {
        if (!cancelled) setSolution(s);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [app.id]);

  useEffect(() => {
    document.title = `${app.name} · Nexus AI`;
  }, [app.name]);

  const handleSectionChange = (sectionId: string) => {
    const next = new URLSearchParams(searchParams);
    if (sectionId === 'insights') next.delete('section'); else next.set('section', sectionId);
    setSearchParams(next, { replace: true });
    setMenuOpen(false);
  };

  const handleManageViews = () => {
    if (solution) {
      nav(`/ai-analytics?tab=solutions&solutionId=${encodeURIComponent(solution.solutionId)}`);
    } else {
      nav('/ai-analytics?tab=solutions');
    }
  };

  const currentSection = app.sections.find(s => s.id === activeSection);
  const sectionName = activeSection.startsWith('view:')
    ? (solution?.views.find(v => `view:${v.viewId}` === activeSection)?.displayName || 'View')
    : currentSection?.name || SECTION_LABELS[activeSection] || 'Business Insights';

  const renderContent = () => {
    if (activeSection.startsWith('view:')) {
      const viewId = activeSection.slice('view:'.length);
      return <ViewRuntime viewId={viewId} className="flex flex-col h-full" />;
    }
    switch (activeSection) {
      case 'insights': return <AppOverview app={app} onNavigate={handleSectionChange} />;
      case 'analytics': return <AppDashboard app={app} />;
      case 'workflows': return <AppWorkflowActions app={app} />;
      case 'reports': return <AppAlerts app={app} />;
      case 'tools-catalogue': return <AppToolsCatalogue app={app} />;
      case 'agent-builder': return <AgentBuilderPlaceholder appName={app.shortName} />;
      default: return <AppOverview app={app} onNavigate={handleSectionChange} />;
    }
  };

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-background text-foreground">
      <div className="hidden lg:block">
        <AppSidebar app={app} solution={solution} activeSection={activeSection} onSectionChange={handleSectionChange} />
      </div>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-[var(--topbar-h)] shrink-0 items-center gap-3 border-b border-border bg-header px-3 sm:px-5 lg:px-8">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <button type="button" onClick={() => setMenuOpen(true)} aria-label="Open sections" className={`${iconBtn} lg:hidden`}>
              <Icon name="menu" className="h-[18px] w-[18px]" />
            </button>
            <nav aria-label="Breadcrumb" className="min-w-0">
              <ol className="flex min-w-0 items-center gap-1.5 text-sm">
                <li className="hidden sm:block"><Link to="/workspace/apps" className="text-muted-foreground transition-colors hover:text-foreground">Solutions</Link></li>
                <li className="hidden text-subtle-foreground sm:block" aria-hidden="true">/</li>
                <li className="hidden min-w-0 truncate text-muted-foreground md:block">{app.name}</li>
                <li className="hidden text-subtle-foreground md:block" aria-hidden="true">/</li>
                <li className="min-w-0 truncate font-medium text-foreground" aria-current="page">{sectionName}</li>
              </ol>
            </nav>
            {app.status !== 'available' && <Badge variant="neutral" className="ml-1 hidden sm:inline-flex">Coming soon</Badge>}
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            <Button
              size="sm"
              variant="outline"
              onClick={handleManageViews}
              title={solution ? 'Manage the views attached to this solution' : 'Open solution mapping'}
              className="hidden sm:inline-flex"
            >
              <Icon name="dashboard" /> Manage views
            </Button>
            {app.journeyStageId && (
              <Button size="sm" onClick={() => nav('/operations/journeys')}>
                <Icon name="play" /> Run journey
              </Button>
            )}
            <button type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} className={`${iconBtn} ml-1 hidden sm:flex`}>
              <Icon name={theme === 'dark' ? 'sun' : 'moon'} className="h-[18px] w-[18px]" />
            </button>
            <div className="ml-1"><UserMenu /></div>
          </div>
        </header>

        <main className="scroll-thin min-h-0 flex-1 overflow-auto">
          <div key={activeSection} className="min-h-full animate-fade-in">
            <PageErrorBoundary resetKey={activeSection}>
              {renderContent()}
            </PageErrorBoundary>
          </div>
        </main>
      </div>

      {/* Sections drawer on phones and tablets */}
      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent side="left" className="w-[280px] border-sidebar-border bg-sidebar p-0 sm:max-w-[280px]">
          <SheetTitle className="sr-only">{app.name} sections</SheetTitle>
          <SheetDescription className="sr-only">Sections of this solution</SheetDescription>
          <AppSidebar app={app} solution={solution} activeSection={activeSection} onSectionChange={handleSectionChange} inDrawer />
        </SheetContent>
      </Sheet>
    </div>
  );
}

function AgentBuilderPlaceholder({ appName }: { appName: string }) {
  const items = [
    { title: 'Custom tools', desc: 'Define application-specific ReAct tools with declarative YAML.' },
    { title: 'Journey templates', desc: 'Compose multi-step automation journeys from available tools.' },
    { title: 'Agent profiles', desc: 'Configure agent behaviour, permissions and system prompts.' },
    { title: 'Test harness', desc: 'Test agents with sample inputs and validate outputs.' },
  ];
  return (
    <div className="page max-w-3xl">
      <h1 className="text-2xl font-medium tracking-tight text-foreground">Agent Builder</h1>
      <p className="mt-1.5 text-sm text-muted-foreground">
        Build and configure AI agents for {appName}. This area is not available yet; it will cover:
      </p>
      <div className="mt-6 divide-y divide-border border-y border-border">
        {items.map(item => (
          <div key={item.title} className="flex flex-col gap-0.5 py-3 sm:flex-row sm:gap-6">
            <h3 className="w-44 shrink-0 text-sm font-medium text-foreground">{item.title}</h3>
            <p className="text-sm text-muted-foreground">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
