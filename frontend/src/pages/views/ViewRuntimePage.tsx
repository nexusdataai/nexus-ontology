import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Loader2, Pencil } from 'lucide-react';
import { toast } from 'sonner';
import type { View } from '@/lib/foundry/model';
import { viewService } from '@/services/viewService';
import { ViewRuntime } from '@/components/views/ViewRuntime';

export default function ViewRuntimePage() {
  const { viewId } = useParams<{ viewId: string }>();
  const navigate = useNavigate();
  const [view, setView] = useState<View | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!viewId) return;
    setLoading(true);
    viewService
      .get(viewId)
      .then(setView)
      .catch(() => toast.error('Failed to load view'))
      .finally(() => setLoading(false));
  }, [viewId]);

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      </Layout>
    );
  }

  if (!view) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center h-64">
          <p className="text-sm text-muted-foreground mb-3">View not found</p>
          <Button variant="outline" size="sm" onClick={() => navigate('/views')}>
            <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Back to views
          </Button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between gap-3 p-3 border-b bg-background/95 backdrop-blur-sm sticky top-0 z-20">
          <div className="flex items-center gap-2 min-w-0">
            <Button variant="ghost" size="sm" className="h-8" onClick={() => navigate('/views')}>
              <ArrowLeft className="h-3.5 w-3.5" />
            </Button>
            <h1 className="text-sm font-medium truncate">{view.name}</h1>
            {view.version > 0 && (
              <Badge variant="outline" className="text-[9px]">v{view.version}</Badge>
            )}
            <span className="text-[10px] text-muted-foreground">{view.tabs.length} tabs</span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => navigate(`/views/builder/${view.viewId}`)}
            >
              <Pencil className="h-3.5 w-3.5 mr-1" /> Edit
            </Button>
          </div>
        </div>

        <div className="flex-1 min-h-0">
          <ViewRuntime view={view} />
        </div>
      </div>
    </Layout>
  );
}
