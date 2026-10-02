import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Loader2, MoreVertical, Pencil, Copy, Trash2, AlertCircle } from 'lucide-react';
import type { PanelModel } from '../model';
import { getPanelPlugin } from '../panels/registry';
import { useQueryRunner } from '../runtime/useQueryRunner';
import type { TimeRange } from '../types';

interface Props {
  panel: PanelModel;
  width: number;
  height: number;
  timeRange?: TimeRange;
  isEditing?: boolean;
  onEdit?: () => void;
  onDuplicate?: () => void;
  onRemove?: () => void;
}

export function PanelChrome({
  panel,
  width,
  height,
  timeRange,
  isEditing,
  onEdit,
  onDuplicate,
  onRemove,
}: Props) {
  const [hovered, setHovered] = useState(false);
  const plugin = getPanelPlugin(panel.type);

  const stableTargets = useMemo(() => panel.targets, [JSON.stringify(panel.targets)]);
  const { panelData } = useQueryRunner(stableTargets, timeRange);

  const loading = panelData.state === 'loading';
  const error = panelData.error;
  const headerHeight = 36;
  const contentHeight = height - headerHeight - 16;

  const PanelComponent = plugin?.component;

  return (
    <Card
      className={`h-full overflow-hidden flex flex-col ${isEditing ? 'cursor-pointer ring-transparent hover:ring-1 hover:ring-primary/40 transition-shadow' : ''}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onDoubleClick={isEditing ? onEdit : undefined}
    >
      <CardHeader className="py-1.5 px-3 flex flex-row items-center justify-between space-y-0 border-b flex-shrink-0">
        <CardTitle
          className={`text-xs font-medium truncate flex items-center gap-1.5 ${isEditing ? 'cursor-pointer hover:text-primary transition-colors' : ''}`}
          onClick={isEditing ? onEdit : undefined}
        >
          {loading && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
          {error && !loading && <AlertCircle className="h-3 w-3 text-destructive" />}
          {panel.title}
        </CardTitle>
        {isEditing && (
          <div className={`flex items-center gap-0.5 transition-opacity ${hovered ? 'opacity-100' : 'opacity-0'}`}>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={(e) => { e.stopPropagation(); onEdit?.(); }}
              title="Edit panel"
            >
              <Pencil className="h-3 w-3" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <MoreVertical className="h-3.5 w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="text-xs">
                <DropdownMenuItem onClick={onEdit} className="text-xs">
                  <Pencil className="h-3 w-3 mr-2" /> Edit
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onDuplicate} className="text-xs">
                  <Copy className="h-3 w-3 mr-2" /> Duplicate
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onRemove} className="text-xs text-destructive">
                  <Trash2 className="h-3 w-3 mr-2" /> Remove
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </CardHeader>
      <CardContent className="p-0 flex-1 overflow-hidden">
        {error && !loading ? (
          <div className="flex items-center justify-center h-full p-4">
            <div className="text-center">
              <AlertCircle className="h-5 w-5 text-destructive mx-auto mb-1" />
              <p className="text-xs text-destructive">{error}</p>
            </div>
          </div>
        ) : PanelComponent ? (
          <PanelComponent
            data={panelData.frames}
            options={panel.options ?? {}}
            width={width}
            height={contentHeight}
            title={panel.title}
            loading={loading}
            error={error}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-xs text-muted-foreground">
            Unknown panel type: {panel.type}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
