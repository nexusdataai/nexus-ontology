import { useState, useMemo, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Icon } from '@/components/ds/Icon';
import type { PanelModel } from '../model';
import { getPanelPlugin } from '../panels/registry';
import { useQueryRunner } from '../runtime/useQueryRunner';
import type { DataFrame, TimeRange } from '../types';

interface Props {
  panel: PanelModel;
  width: number;
  height: number;
  timeRange?: TimeRange;
  isEditing?: boolean;
  onEdit?: () => void;
  onDuplicate?: () => void;
  onRemove?: () => void;
  /** Receives the query result, so the panel editor can offer its fields. */
  onData?: (frames: DataFrame[]) => void;
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
  onData,
}: Props) {
  const [hovered, setHovered] = useState(false);
  const plugin = getPanelPlugin(panel.type);

  const stableTargets = useMemo(() => panel.targets, [JSON.stringify(panel.targets)]);
  const { panelData } = useQueryRunner(stableTargets, timeRange);

  useEffect(() => {
    if (onData && panelData.state !== 'loading') onData(panelData.frames || []);
  }, [panelData.frames, panelData.state]);

  const loading = panelData.state === 'loading';
  const error = panelData.error;
  const headerHeight = 36;
  const contentHeight = height - headerHeight - 16;

  const PanelComponent = plugin?.component;

  return (
    <section
      className={`flex h-full flex-col overflow-hidden rounded-xl border border-border bg-card shadow-xs transition-shadow ${isEditing ? 'cursor-pointer hover:border-brand/50 hover:shadow-md' : ''}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onDoubleClick={isEditing ? onEdit : undefined}
    >
      <header className="flex h-9 shrink-0 items-center justify-between gap-2 px-4">
        <h3
          className={`flex min-w-0 items-center gap-2 truncate text-sm font-medium text-foreground ${isEditing ? 'cursor-pointer transition-colors hover:text-primary dark:hover:text-brand-hi' : ''}`}
          onClick={isEditing ? onEdit : undefined}
        >
          <span className="truncate">{panel.title}</span>
          {loading && <Icon name="spinner" className="h-3 w-3 shrink-0 animate-spin text-muted-foreground" />}
          {error && !loading && <Icon name="alert-triangle" className="h-3.5 w-3.5 shrink-0 text-destructive" />}
        </h3>
        {isEditing && (
          <div className={`flex items-center gap-0.5 transition-opacity ${hovered ? 'opacity-100' : 'opacity-0 focus-within:opacity-100'}`}>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={(e) => { e.stopPropagation(); onEdit?.(); }} aria-label="Edit panel" title="Edit panel">
              <Icon name="edit" className="h-3.5 w-3.5" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0" aria-label="More panel actions">
                  <Icon name="more" className="h-3.5 w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={onEdit}><Icon name="edit" className="mr-2 h-3.5 w-3.5" /> Edit</DropdownMenuItem>
                <DropdownMenuItem onClick={onDuplicate}><Icon name="copy" className="mr-2 h-3.5 w-3.5" /> Duplicate</DropdownMenuItem>
                <DropdownMenuItem onClick={onRemove} className="text-destructive focus:text-destructive"><Icon name="trash" className="mr-2 h-3.5 w-3.5" /> Remove</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </header>
      <div className="min-h-0 flex-1 overflow-hidden">
        {error && !loading ? (
          <div className="flex h-full items-center justify-center p-4 text-center">
            <p className="max-w-xs text-sm text-muted-foreground"><span className="font-medium text-destructive">This panel could not load.</span> {error}</p>
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
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Unknown panel type: {panel.type}
          </div>
        )}
      </div>
    </section>
  );
}
