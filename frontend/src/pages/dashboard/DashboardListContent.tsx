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
import {
  Plus,
  Search,
  LayoutDashboard,
  MoreVertical,
  Pencil,
  Copy,
  Trash2,
  Eye,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import { dashboardService, type DashboardListItem } from '@/services/dashboardService';

interface DashboardListContentProps {
  /** Hide the page-level title block (used when embedded in tabs). */
  hideHeading?: boolean;
}

export function DashboardListContent({ hideHeading = false }: DashboardListContentProps) {
  const navigate = useNavigate();
  const [dashboards, setDashboards] = useState<DashboardListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const load = () => {
    setLoading(true);
    dashboardService
      .list(search)
      .then(setDashboards)
      .catch(() => toast.error('Failed to load dashboards'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [search]);

  const handleDelete = async (uid: string) => {
    try {
      await dashboardService.delete(uid);
      setDashboards((prev) => prev.filter((d) => d.uid !== uid));
      toast.success('Dashboard deleted');
    } catch {
      toast.error('Delete failed');
    }
  };

  const handleClone = async (uid: string) => {
    try {
      const cloned = await dashboardService.clone(uid);
      toast.success('Dashboard cloned');
      navigate(`/dashboard/builder/${cloned.uid}`);
    } catch {
      toast.error('Clone failed');
    }
  };

  return (
    <div className={hideHeading ? '' : 'p-6 max-w-6xl mx-auto'}>
      <div className="flex items-center justify-between mb-6">
        {!hideHeading ? (
          <div>
            <h1 className="text-lg font-semibold">Dashboards</h1>
            <p className="text-xs text-muted-foreground">
              Create and manage dashboards powered by the Virtual Data Layer
            </p>
          </div>
        ) : (
          <div />
        )}
        <Button size="sm" className="h-8" onClick={() => navigate('/dashboard/builder')}>
          <Plus className="h-3.5 w-3.5 mr-1" /> New Dashboard
        </Button>
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          className="h-8 pl-9 text-xs"
          placeholder="Search dashboards..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : dashboards.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 border-2 border-dashed border-border rounded-lg">
          <LayoutDashboard className="h-8 w-8 text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground mb-3">No dashboards yet</p>
          <Button size="sm" variant="outline" onClick={() => navigate('/dashboard/builder')}>
            <Plus className="h-3.5 w-3.5 mr-1" /> Create your first dashboard
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {dashboards.map((d) => (
            <Card
              key={d.uid}
              className="hover:shadow-md transition-shadow cursor-pointer group"
              onClick={() => navigate(`/dashboard/view/${d.uid}`)}
            >
              <CardHeader className="pb-2 flex flex-row items-start justify-between space-y-0">
                <div className="min-w-0 flex-1">
                  <CardTitle className="text-sm truncate">{d.title}</CardTitle>
                  {d.description && (
                    <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
                      {d.description}
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
                      onClick={() => navigate(`/dashboard/view/${d.uid}`)}
                      className="text-xs"
                    >
                      <Eye className="h-3 w-3 mr-2" /> View
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => navigate(`/dashboard/builder/${d.uid}`)}
                      className="text-xs"
                    >
                      <Pencil className="h-3 w-3 mr-2" /> Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleClone(d.uid)} className="text-xs">
                      <Copy className="h-3 w-3 mr-2" /> Clone
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleDelete(d.uid)}
                      className="text-xs text-destructive"
                    >
                      <Trash2 className="h-3 w-3 mr-2" /> Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span>{d.panelCount} panels</span>
                  <span>|</span>
                  <span>
                    {d.updatedAt ? new Date(d.updatedAt).toLocaleDateString() : 'Never saved'}
                  </span>
                </div>
                {d.tags.length > 0 && (
                  <div className="flex gap-1 mt-2">
                    {d.tags.map((t) => (
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

export default DashboardListContent;
