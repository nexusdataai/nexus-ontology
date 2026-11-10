import { useSearchParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Tabs, TabsContent } from '@/components/ui/tabs';
import { PageTabsBar, type TabSection } from '@/components/ds/PageTabs';
import { DashboardListContent } from './dashboard/DashboardListContent';
import { ViewListContent } from './views/ViewListContent';
import { SolutionsManagerContent } from './solutions/SolutionsManagerContent';

const VALID_TABS = ['dashboards', 'views', 'solutions'] as const;
type AnalyticsTab = (typeof VALID_TABS)[number];

function isValidTab(value: string | null): value is AnalyticsTab {
  return !!value && (VALID_TABS as readonly string[]).includes(value);
}

const SECTIONS: TabSection[] = [
  { label: 'Dashboards', icon: 'dashboard', items: [{ value: 'dashboards', label: 'Dashboards' }] },
  { label: 'Views', icon: 'layers', items: [{ value: 'views', label: 'Views' }] },
  { label: 'Solution mapping', icon: 'apps', items: [{ value: 'solutions', label: 'Solution mapping' }] },
];

export default function AIAnalyticsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const raw = searchParams.get('tab');
  const active: AnalyticsTab = isValidTab(raw) ? raw : 'dashboards';

  const handleChange = (value: string) => {
    if (!isValidTab(value)) return;
    const next = new URLSearchParams(searchParams);
    next.set('tab', value);
    setSearchParams(next, { replace: true });
  };

  return (
    <Layout>
      <Tabs value={active} onValueChange={handleChange}>
        <PageTabsBar
          title="AI Analytics"
          description="Build, browse and organise dashboards and views on the virtual data layer."
          sections={SECTIONS}
          value={active}
          onChange={handleChange}
        />
        <div className="page">
          <TabsContent value="dashboards" className="mt-0">
            <DashboardListContent hideHeading />
          </TabsContent>
          <TabsContent value="views" className="mt-0">
            <ViewListContent hideHeading />
          </TabsContent>
          <TabsContent value="solutions" className="mt-0">
            <SolutionsManagerContent hideHeading />
          </TabsContent>
        </div>
      </Tabs>
    </Layout>
  );
}
