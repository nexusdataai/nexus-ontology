import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
import { EditorHeader } from '@/components/analytics/EditorHeader';
import type { View } from '@/lib/foundry/model';
import { viewService } from '@/services/viewService';
import { DashboardSkeleton, ViewRuntime } from '@/components/views/ViewRuntime';

const LIBRARY = '/ai-analytics?tab=views';

export default function ViewRuntimePage() {
  const { viewId } = useParams<{ viewId: string }>();
  const navigate = useNavigate();
  const [view, setView] = useState<View | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!viewId) return;
    setLoading(true);
    viewService
      .get(viewId)
      .then(setView)
      .catch(() => toast.error('Failed to load view'))
      .finally(() => setLoading(false));
  }, [viewId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading || !view) {
    return (
      <Layout>
        <div className="flex flex-col">
          <EditorHeader
            backLabel="AI Analytics"
            onBack={() => navigate(LIBRARY)}
            title={loading ? <Skeleton className="h-7 w-56" /> : <h1 className="text-lg font-medium tracking-tight text-foreground">View</h1>}
          />
          <div className="p-4 sm:p-6">
            {loading ? (
              <DashboardSkeleton />
            ) : (
              <InlineError onRetry={load}>
                This view could not be loaded. It may have been deleted, or the server did not answer.
              </InlineError>
            )}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex flex-col">
        <EditorHeader
          backLabel="AI Analytics"
          onBack={() => navigate(LIBRARY)}
          title={<h1 className="min-w-0 truncate text-lg font-medium tracking-tight text-foreground">{view.name}</h1>}
          meta={
            <span className="num shrink-0 whitespace-nowrap text-xs text-muted-foreground">
              {view.tabs.length} {view.tabs.length === 1 ? 'tab' : 'tabs'}
              {view.version > 0 && ` · version ${view.version}`}
            </span>
          }
          actions={
            <Button size="sm" onClick={() => navigate(`/views/builder/${view.viewId}`)}>
              <Icon name="edit" className="h-3.5 w-3.5" /> Edit view
            </Button>
          }
        >
          {view.description && <p className="mt-1.5 max-w-3xl text-sm text-muted-foreground">{view.description}</p>}
        </EditorHeader>

        <div className="min-h-0 flex-1">
          <ViewRuntime view={view} />
        </div>
      </div>
    </Layout>
  );
}
