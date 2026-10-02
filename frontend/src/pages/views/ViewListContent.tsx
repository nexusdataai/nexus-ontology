import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Plus, Search, AppWindow, MoreVertical, Pencil, Trash2, Eye, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { viewService } from '@/services/viewService';
import type { ViewSummary } from '@/lib/foundry/model';

interface ViewListContentProps {
  hideHeading?: boolean;
}

export function ViewListContent({ hideHeading = false }: ViewListContentProps) {
  const navigate = useNavigate();
  const [views, setViews] = useState<ViewSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const load = () => {
    setLoading(true);
    viewService
      .list(search)
      .then(setViews)
      .catch(() => toast.error('Failed to load views'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [search]);

  const handleDelete = async (viewId: string) => {
    try {
      await viewService.delete(viewId);
      setViews((prev) => prev.filter((v) => v.viewId !== viewId));
      toast.success('View deleted');
    } catch {
      toast.error('Delete failed');
    }
  };

  return (
    <div className={hideHeading ? '' : 'p-6 max-w-6xl mx-auto'}>
      <div className="flex items-center justify-between mb-6">
        {!hideHeading ? (
          <div>
            <h1 className="text-lg font-semibold">Views</h1>
            <p className="text-xs text-muted-foreground">
              Tabbed collections of dashboards. Build with the visual View Builder and surface
              them inside Solutions.
            </p>
          </div>
        ) : (
          <div />
        )}
        <Button size="sm" className="h-8" onClick={() => navigate('/views/builder')}>
          <Plus className="h-3.5 w-3.5 mr-1" /> New View
        </Button>
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          className="h-8 pl-9 text-xs"
          placeholder="Search views..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : views.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 border-2 border-dashed border-border rounded-lg">
          <AppWindow className="h-8 w-8 text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground mb-3">No views yet</p>
          <Button size="sm" variant="outline" onClick={() => navigate('/views/builder')}>
            <Plus className="h-3.5 w-3.5 mr-1" /> Create your first view
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {views.map((v) => (
            <Card
              key={v.viewId}
              className="hover:shadow-md transition-shadow cursor-pointer group"
              onClick={() => navigate(`/views/${v.viewId}`)}
            >
              <CardHeader className="pb-2 flex flex-row items-start justify-between space-y-0">
                <div className="min-w-0 flex-1">
                  <CardTitle className="text-sm truncate">{v.name}</CardTitle>
                  {v.description && (
                    <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
                      {v.description}
                    </p>
                  )}
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <MoreVertical className="h-3.5 w-3.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="end"
                    className="text-xs"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <DropdownMenuItem
                      onClick={() => navigate(`/views/${v.viewId}`)}
                      className="text-xs"
                    >
                      <Eye className="h-3 w-3 mr-2" /> Open
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => navigate(`/views/builder/${v.viewId}`)}
                      className="text-xs"
                    >
                      <Pencil className="h-3 w-3 mr-2" /> Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleDelete(v.viewId)}
                      className="text-xs text-destructive"
                    >
                      <Trash2 className="h-3 w-3 mr-2" /> Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span>{v.tabCount} tabs</span>
                  <span>|</span>
                  <span>
                    {v.updatedAt ? new Date(v.updatedAt).toLocaleDateString() : 'Never saved'}
                  </span>
                </div>
                {v.tags.length > 0 && (
                  <div className="flex gap-1 mt-2">
                    {v.tags.map((t) => (
                      <Badge key={t} variant="outline" className="text-[9px]">
                        {t}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default ViewListContent;
