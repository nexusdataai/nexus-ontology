import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Play, RefreshCw, ChevronRight, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
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

interface Props {
  app: AppConfig;
}

const SECTION_LABELS: Record<string, string> = {
  'agent-builder': 'Agent Builder',
  'tools-catalogue': 'Tools Catalogue',
};

export function AppShell({ app }: Props) {
  const nav = useNavigate();
  const [activeSection, setActiveSection] = useState('insights');
  const [solution, setSolution] = useState<Solution | null>(null);

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

  const handleSectionChange = (sectionId: string) => {
    setActiveSection(sectionId);
  };

  const handleManageViews = () => {
    if (solution) {
      nav(`/ai-analytics?tab=solutions&solutionId=${encodeURIComponent(solution.solutionId)}`);
    } else {
      nav('/ai-analytics?tab=solutions');
    }
  };

  const Icon = app.icon;
  const currentSection = app.sections.find(s => s.id === activeSection);
  const sectionName = activeSection.startsWith('view:')
    ? 'View'
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
    <div className="h-screen flex overflow-hidden bg-background text-foreground">
      <AppSidebar
        app={app}
        solution={solution}
        activeSection={activeSection}
        onSectionChange={handleSectionChange}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-5 h-12 shrink-0 border-b border-border bg-card">
          <div className="flex items-center gap-2">
            <div className={`p-1 rounded bg-gradient-to-br ${app.color}`}>
              <Icon className="h-3.5 w-3.5 text-white" />
            </div>
            <span className="text-sm font-semibold">{app.name}</span>
            <ChevronRight className="h-3 w-3 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">{sectionName}</span>
            <Badge className={app.status === 'available' ? 'bg-green-500/20 text-green-400 text-[9px]' : 'bg-amber-500/20 text-amber-400 text-[9px]'}>
              {app.status === 'available' ? 'Active' : 'Coming Soon'}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleManageViews}
              title={solution ? 'Manage Views for this Solution' : 'Open Solutions manager'}
            >
              <Settings className="h-3 w-3 mr-1" /> Manage Views
            </Button>
            {app.journeyStageId && (
              <Button size="sm" variant="outline" onClick={() => nav('/operations/journeys')}>
                <Play className="h-3 w-3 mr-1" /> Run Journey
              </Button>
            )}
            <Button size="sm" variant="ghost"><RefreshCw className="h-3.5 w-3.5" /></Button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

function AgentBuilderPlaceholder({ appName }: { appName: string }) {
  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h2 className="text-xl font-semibold mb-2">Agent Builder</h2>
      <p className="text-sm text-muted-foreground mb-6">
        Build and configure AI agents for the {appName} application. Define custom ReAct tools, compose journeys, and set up automation workflows.
      </p>
      <div className="grid grid-cols-2 gap-4">
        {[
          { title: 'Custom Tools', desc: 'Define application-specific ReAct tools with declarative YAML' },
          { title: 'Journey Templates', desc: 'Compose multi-step automation journeys from available tools' },
          { title: 'Agent Profiles', desc: 'Configure agent behavior, permissions, and system prompts' },
          { title: 'Test Harness', desc: 'Test agents with sample inputs and validate outputs' },
        ].map(item => (
          <div key={item.title} className="rounded-lg border p-4">
            <h3 className="text-sm font-medium mb-1">{item.title}</h3>
            <p className="text-xs text-muted-foreground">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
