import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { CopilotJourney } from '@/components/CopilotJourney';
import { JourneyBuilder } from '@/components/JourneyBuilder';
import { JourneysPanel } from '@/components/journeys/JourneysPanel';
import { CopilotSavedJourneysSection } from '@/components/journeys/CopilotSavedJourneysSection';
import { AutomationRegistryPanel } from '@/components/workspace/AutomationRegistryPanel';
import { PageTabsBar, type TabSection } from '@/components/ds/PageTabs';

type Tab = 'copilot' | 'builder' | 'journeys' | 'copilot-saved' | 'registry';

/** Tabs grouped into sections. Item values are the original ?tab= values. */
const SECTIONS: TabSection[] = [
  { label: 'Journeys', icon: 'route', items: [
    { value: 'journeys', label: 'All journeys' },
    { value: 'copilot-saved', label: 'Saved from Copilot' },
  ] },
  { label: 'Copilot', icon: 'chat-bot', items: [{ value: 'copilot', label: 'AI Copilot' }] },
  { label: 'Builder', icon: 'workflow', items: [{ value: 'builder', label: 'Journey builder' }] },
  { label: 'Registry', icon: 'list', items: [{ value: 'registry', label: 'Automation registry' }] },
];
const VALID: Tab[] = ['journeys', 'copilot-saved', 'copilot', 'builder', 'registry'];

export default function AIAutomationPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const raw = searchParams.get('tab') as Tab | null;
  const activeTab: Tab = raw && VALID.includes(raw) ? raw : 'journeys';

  // The tab lives in the URL. Leaving a tab also clears its journey selection.
  const setActiveTab = useCallback((tab: string) => {
    const next = new URLSearchParams(searchParams);
    if (tab === 'journeys') next.delete('tab'); else next.set('tab', tab);
    next.delete('journeyId');
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

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
      <PageTabsBar
        title="AI Automation"
        description="Create, run, schedule and monitor journeys. Plan one with the Copilot or draw it in the builder."
        sections={SECTIONS}
        value={activeTab}
        onChange={setActiveTab}
      />
      <div className="animate-fade-in" key={activeTab}>
        {activeTab === 'journeys' && <JourneysPanel initialJourneyId={searchParams.get('journeyId') || undefined} />}
        {activeTab === 'copilot-saved' && (
          <div className="page">
            <CopilotSavedJourneysSection
              selectedJourneyId={searchParams.get('journeyId') || undefined}
              onSelectJourney={handleSelectCopilotSavedJourney}
            />
          </div>
        )}
        {activeTab === 'copilot' && <div className="h-pane"><CopilotJourney /></div>}
        {activeTab === 'builder' && <div className="h-pane"><JourneyBuilder /></div>}
        {activeTab === 'registry' && <AutomationRegistryPanel />}
      </div>
    </Layout>
  );
}
