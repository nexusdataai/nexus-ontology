import { useSearchParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DashboardListContent } from './dashboard/DashboardListContent';
import { ViewListContent } from './views/ViewListContent';
import { SolutionsManagerContent } from './solutions/SolutionsManagerContent';

const VALID_TABS = ['dashboards', 'views', 'solutions'] as const;
type AnalyticsTab = (typeof VALID_TABS)[number];

function isValidTab(value: string | null): value is AnalyticsTab {
  return !!value && (VALID_TABS as readonly string[]).includes(value);
}

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
      <div className="p-6 max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-lg font-semibold">AI Analytics</h1>
          <p className="text-xs text-muted-foreground">
            Build, browse, and organise dashboards and views powered by the Virtual Data Layer.
          </p>
        </div>

        <Tabs value={active} onValueChange={handleChange} className="w-full">
          <TabsList className="bg-transparent p-0 h-auto gap-1 border-b rounded-none w-full justify-start mb-4">
            <TabsTrigger
              value="dashboards"
              className="data-[state=active]:bg-muted text-xs px-4 py-1.5 rounded-md"
            >
              Dashboards
            </TabsTrigger>
            <TabsTrigger
              value="views"
              className="data-[state=active]:bg-muted text-xs px-4 py-1.5 rounded-md"
            >
              Views
            </TabsTrigger>
            <TabsTrigger
              value="solutions"
              className="data-[state=active]:bg-muted text-xs px-4 py-1.5 rounded-md"
            >
              Solution Mapping
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboards" className="mt-0">
            <DashboardListContent hideHeading />
          </TabsContent>
          <TabsContent value="views" className="mt-0">
            <ViewListContent hideHeading />
          </TabsContent>
          <TabsContent value="solutions" className="mt-0">
            <SolutionsManagerContent hideHeading />
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
