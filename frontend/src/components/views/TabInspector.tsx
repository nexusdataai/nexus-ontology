import { useEffect, useMemo, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Icon } from '@/components/ds/Icon';
import { Field } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { dashboardService, type DashboardListItem } from '@/services/dashboardService';
import type { DraftTab } from './ViewBuilderTypes';
import type { SimulatorRef } from '@/lib/foundry/model';

interface TabInspectorProps {
  tab: DraftTab | null;
  onChange: (next: DraftTab) => void;
  onRemove: () => void;
  /** Move the tab one place left (-1) or right (1). Omit to hide the buttons. */
  onMove?: (direction: -1 | 1) => void;
  canMoveLeft?: boolean;
  canMoveRight?: boolean;
  className?: string;
}

const GENERIC_LABEL = /^tab\s*\d+$/i;

/** Settings for the selected tab: label, dashboard, time range, simulator data. */
export function TabInspector({ tab, onChange, onRemove, onMove, canMoveLeft, canMoveRight, className }: TabInspectorProps) {
  const [dashboards, setDashboards] = useState<DashboardListItem[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [showSim, setShowSim] = useState(false);

  useEffect(() => {
    dashboardService
      .list()
      .then(setDashboards)
      .catch(() => undefined)
      .finally(() => setListLoading(false));
  }, []);

  const dashboardOptions = useMemo(() => dashboards, [dashboards]);

  if (!tab) return null;

  const update = (patch: Partial<DraftTab>) => {
    onChange({ ...tab, ...patch, isDirty: true });
  };

  const updateSimRef = (idx: number, patch: Partial<SimulatorRef>) => {
    const next = tab.simulatorRefs.map((r, i) => (i === idx ? { ...r, ...patch } : r));
    update({ simulatorRefs: next });
  };

  const removeSimRef = (idx: number) => {
    const next = tab.simulatorRefs.filter((_, i) => i !== idx);
    update({ simulatorRefs: next });
  };

  const addSimRef = () => {
    update({ simulatorRefs: [...tab.simulatorRefs, { service: '' }] });
    setShowSim(true);
  };

  const selected = dashboardOptions.find((d) => d.uid === tab.dashboardId);
  const generic = !tab.label.trim() || GENERIC_LABEL.test(tab.label.trim());
  const simOpen = showSim || tab.simulatorRefs.length > 0;
  const halfRange = !!(tab.timeOverride?.from) !== !!(tab.timeOverride?.to);

  return (
    <section className={cn('shrink-0 border-b border-border px-3 py-4 sm:px-5', className)} aria-label="Tab settings">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-foreground">Tab settings</h2>
        <div className="flex items-center gap-1">
          {onMove && (
            <>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => onMove(-1)} disabled={!canMoveLeft} aria-label="Move tab left" title="Move tab left">
                <Icon name="chevron-left" className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => onMove(1)} disabled={!canMoveRight} aria-label="Move tab right" title="Move tab right">
                <Icon name="chevron-right" className="h-3.5 w-3.5" />
              </Button>
            </>
          )}
          <Button variant="ghost" size="sm" className="h-7 px-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive" onClick={onRemove}>
            <Icon name="trash" className="h-3 w-3" /> Remove tab
          </Button>
        </div>
      </div>

      <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_minmax(0,1.2fr)]">
        <Field
          label="Label"
          htmlFor="tab-label"
          hint={generic && tab.dashboardId ? 'People see the dashboard name until you give the tab its own label.' : undefined}
        >
          <Input
            id="tab-label"
            value={tab.label}
            onChange={(e) => update({ label: e.target.value })}
            placeholder="For example: Overview"
            className="h-9"
          />
        </Field>

        <Field
          label="Dashboard"
          hint={
            !tab.dashboardId
              ? 'Every tab needs a dashboard before the view can be saved.'
              : !listLoading && !selected && dashboardOptions.length > 0
                ? 'This dashboard is no longer in the library. Choose another one.'
                : undefined
          }
        >
          <DashboardPicker
            dashboards={dashboardOptions}
            loading={listLoading}
            value={tab.dashboardId}
            selected={selected}
            onChange={(uid) => update({ dashboardId: uid })}
          />
        </Field>

        <Field
          label="Time range for this tab"
          hint={halfRange ? 'Fill in both ends, or leave both empty.' : "Optional. Leave empty to use the dashboard's own range."}
          className="sm:col-span-2 xl:col-span-1"
        >
          <div className="flex items-center gap-2">
            <Input
              placeholder="now-24h"
              aria-label="Time range from"
              value={tab.timeOverride?.from || ''}
              onChange={(e) =>
                update({
                  timeOverride: { ...(tab.timeOverride || {}), from: e.target.value || undefined },
                })
              }
              className="h-9"
            />
            <span className="text-xs text-subtle-foreground">to</span>
            <Input
              placeholder="now"
              aria-label="Time range to"
              value={tab.timeOverride?.to || ''}
              onChange={(e) =>
                update({
                  timeOverride: { ...(tab.timeOverride || {}), to: e.target.value || undefined },
                })
              }
              className="h-9"
            />
          </div>
        </Field>
      </div>

      <div className="mt-3">
        <button
          type="button"
          onClick={() => setShowSim((s) => !s)}
          aria-expanded={simOpen}
          disabled={tab.simulatorRefs.length > 0}
          className="inline-flex items-center gap-1.5 rounded text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:hover:text-muted-foreground"
        >
          <Icon name={simOpen ? 'chevron-down' : 'chevron-right'} className="h-3 w-3" />
          Simulator data
          <span className="num text-subtle-foreground">
            {tab.simulatorRefs.length > 0 ? tab.simulatorRefs.length : 'optional'}
          </span>
        </button>

        {simOpen && (
          <div className="mt-2 max-w-3xl">
            <p className="text-xs text-muted-foreground">
              Point this tab at simulator data sets in storage to limit what its dashboard shows.
            </p>
            {tab.simulatorRefs.length > 0 && (
              <ul className="mt-2 space-y-2">
                {tab.simulatorRefs.map((ref, idx) => (
                  <li key={idx} className="flex flex-wrap items-center gap-1.5">
                    <Input
                      placeholder="System, e.g. sfdc, oracle, sap"
                      aria-label="Source system"
                      value={ref.service}
                      onChange={(e) => updateSimRef(idx, { service: e.target.value })}
                      className="h-8 min-w-[140px] flex-1 basis-40"
                    />
                    <Input
                      placeholder="Scenario (optional)"
                      aria-label="Scenario"
                      value={ref.scenario || ''}
                      onChange={(e) => updateSimRef(idx, { scenario: e.target.value })}
                      className="h-8 min-w-[140px] flex-1 basis-40"
                    />
                    <Input
                      placeholder="Storage path or manifest"
                      aria-label="Storage path or manifest"
                      value={ref.s3Key || ''}
                      onChange={(e) => updateSimRef(idx, { s3Key: e.target.value })}
                      className="mono-id h-8 min-w-[160px] flex-[2] basis-48"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 shrink-0 p-0 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      onClick={() => removeSimRef(idx)}
                      aria-label="Remove simulator data set"
                    >
                      <Icon name="trash" className="h-3.5 w-3.5" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            <Button variant="ghost" size="sm" className="-ml-2 mt-1 h-7 px-2" onClick={addSimRef}>
              <Icon name="plus" className="h-3 w-3" /> Add a data set
            </Button>
          </div>
        )}
      </div>
    </section>
  );
}

interface DashboardPickerProps {
  dashboards: DashboardListItem[];
  loading: boolean;
  value: string;
  selected?: DashboardListItem;
  onChange: (uid: string) => void;
}

/** Searchable list of dashboards (by name, description or tag). */
function DashboardPicker({ dashboards, loading, value, selected, onChange }: DashboardPickerProps) {
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label="Dashboard"
          className={cn('h-9 w-full justify-between gap-2 px-3 font-normal', !value && 'border-warning/50')}
        >
          <span className={cn('min-w-0 truncate', !selected && 'text-muted-foreground')}>
            {selected ? selected.title : value ? (loading ? 'Loading' : 'Dashboard not found') : 'Choose a dashboard'}
          </span>
          <Icon name="chevron-down" className="h-3.5 w-3.5 text-subtle-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[min(420px,calc(100vw-2rem))] p-0">
        <Command>
          <CommandInput placeholder="Search dashboards" />
          <CommandList>
            <CommandEmpty>{loading ? 'Loading dashboards' : 'No dashboard matches.'}</CommandEmpty>
            <CommandGroup>
              {dashboards.map((d) => (
                <CommandItem
                  key={d.uid}
                  value={`${d.title} ${d.description || ''} ${(d.tags || []).join(' ')} ${d.uid}`}
                  onSelect={() => {
                    onChange(d.uid);
                    setOpen(false);
                  }}
                  className="items-start gap-2 py-2"
                >
                  <Icon name="check" className={cn('mt-0.5 h-3.5 w-3.5 text-primary dark:text-brand-hi', d.uid === value ? 'opacity-100' : 'opacity-0')} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{d.title}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {d.description || 'No description'}
                    </span>
                  </span>
                  <span className="num shrink-0 text-xs text-subtle-foreground">
                    {d.panelCount} {d.panelCount === 1 ? 'panel' : 'panels'}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

export default TabInspector;
