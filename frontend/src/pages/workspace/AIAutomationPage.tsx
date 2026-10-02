import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { CopilotJourney } from '@/components/CopilotJourney';
import { JourneyBuilder } from '@/components/JourneyBuilder';
import { JourneysPanel } from '@/components/journeys/JourneysPanel';
import { CopilotSavedJourneysSection } from '@/components/journeys/CopilotSavedJourneysSection';
import { AutomationRegistryPanel } from '@/components/workspace/AutomationRegistryPanel';
import { Sparkles, Workflow, ListChecks, BookmarkCheck, Library } from 'lucide-react';
import { cn } from '@/lib/utils';

type Tab = 'copilot' | 'builder' | 'journeys' | 'copilot-saved' | 'registry';

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'journeys', label: 'Journeys', icon: ListChecks },
  { id: 'copilot-saved', label: 'Copilot Saved', icon: BookmarkCheck },
  { id: 'copilot', label: 'AI Copilot', icon: Sparkles },
  { id: 'builder', label: 'Journey Builder', icon: Workflow },
  { id: 'registry', label: 'Automation Registry', icon: Library },
];

export default function AIAutomationPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<Tab>((searchParams.get('tab') as Tab) || 'journeys');

  useEffect(() => {
    const t = searchParams.get('tab') as Tab;
    if (t && TABS.some(tab => tab.id === t)) setActiveTab(t);
  }, [searchParams]);

  // Deep-link selection for the Copilot Saved studio.
  // ``?tab=copilot-saved&journeyId=<id>`` -> studio view for that
  // journey. Clearing journeyId returns to the card grid.
  const handleSelectCopilotSavedJourney = useCallback((id: string | null) => {
    const next = new URLSearchParams(searchParams);
    next.set('tab', 'copilot-saved');
    if (id) next.set('journeyId', id);
    else next.delete('journeyId');
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  return (
    <Layout>
      <div className="h-full flex flex-col">
        <div className="border-b px-1 shrink-0">
          <nav className="flex gap-1" aria-label="AI Automation tabs">
            {TABS.map(tab => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                    active ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border',
                  )}>
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>
        <div className="flex-1 overflow-auto">
          {activeTab === 'journeys' && <JourneysPanel initialJourneyId={searchParams.get('journeyId') || undefined} />}
          {activeTab === 'copilot-saved' && (
            <div className="px-4 pt-4">
              <CopilotSavedJourneysSection
                selectedJourneyId={searchParams.get('journeyId') || undefined}
                onSelectJourney={handleSelectCopilotSavedJourney}
              />
            </div>
          )}
          {activeTab === 'copilot' && <CopilotJourney />}
          {activeTab === 'builder' && <JourneyBuilder />}
          {activeTab === 'registry' && <AutomationRegistryPanel />}
        </div>
      </div>
    </Layout>
  );
}
