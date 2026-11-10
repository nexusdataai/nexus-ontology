import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ds/Icon';
import { Field } from '@/components/ds/kit';
import type { PanelModel } from '../model';
import type { DataFrame, TimeRange } from '../types';
import { QueryTab } from './QueryTab';
import { PanelDisplayOptions, PanelTypePicker } from './VisualizationTab';
import { PanelChrome } from '../components/PanelChrome';
import { TimeRangePicker } from '../components/TimeRangePicker';

interface Props {
  panel: PanelModel | null;
  open: boolean;
  timeRange?: TimeRange;
  /** Shows the dashboard's time range control above the preview. */
  onTimeRangeChange?: (range: TimeRange) => void;
  onSave: (panel: PanelModel) => void;
  onCancel: () => void;
}

/**
 * Panel editor: a large dialog with the live preview on the left and the
 * settings on the right (Panel, Visualisation, Data, Display options).
 * Nothing reaches the dashboard until "Apply changes".
 */
export function PanelEditor({ panel, open, timeRange, onTimeRangeChange, onSave, onCancel }: Props) {
  const [draft, setDraft] = useState<PanelModel | null>(null);
  const [frames, setFrames] = useState<DataFrame[]>([]);

  useEffect(() => {
    if (open && panel) {
      setDraft(JSON.parse(JSON.stringify(panel)));
    } else if (!open) {
      setDraft(null);
    }
  }, [open, panel?.id]);

  const current = draft ?? panel;

  const handleSave = () => {
    if (current) {
      onSave(current);
      setDraft(null);
    }
  };

  const handleClose = () => {
    onCancel();
    setDraft(null);
  };

  const update = (patch: Partial<PanelModel>) => {
    setDraft((prev) => ({ ...(prev ?? current!), ...patch }));
  };

  if (!open || !current) return null;

  const changed = !!panel && !!draft && JSON.stringify(draft) !== JSON.stringify(panel);

  return (
    <Dialog open onOpenChange={(next) => { if (!next) handleClose(); }}>
      <DialogContent
        className="flex h-[calc(100dvh-2rem)] max-h-[880px] max-w-[1280px] flex-col gap-0 overflow-hidden p-0"
        onInteractOutside={(e) => e.preventDefault()}
      >
        <div className="shrink-0 border-b border-border px-5 py-3.5 pr-12">
          <DialogTitle className="text-lg font-medium leading-6">Edit panel</DialogTitle>
          <DialogDescription className="mt-0.5 text-sm text-muted-foreground">
            The preview updates as you change the settings. Apply to put the panel on the dashboard.
          </DialogDescription>
        </div>

        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto lg:grid lg:grid-cols-[minmax(0,1fr)_460px] lg:overflow-hidden">
          {/* Live preview */}
          <div className="flex flex-col border-b border-border bg-surface-2/50 p-4 lg:min-h-0 lg:border-b-0 lg:border-r">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-medium text-muted-foreground">Preview</span>
              {timeRange && onTimeRangeChange && <TimeRangePicker value={timeRange} onChange={onTimeRangeChange} />}
            </div>
            <PanelPreview onData={setFrames} panel={current} timeRange={timeRange} />
          </div>

          {/* Settings */}
          <div className="scroll-thin lg:min-h-0 lg:overflow-y-auto">
            <EditorSection title="Panel" hint="The name shown at the top of the panel.">
              <Field label="Title" htmlFor="panel-title">
                <Input
                  id="panel-title"
                  className="h-9"
                  value={current.title}
                  onChange={(e) => update({ title: e.target.value })}
                  placeholder="For example: Open orders by region"
                />
              </Field>
            </EditorSection>

            <EditorSection title="Visualisation" hint="How the data is drawn.">
              <PanelTypePicker panelType={current.type} onTypeChange={(type) => update({ type, options: {} })} />
            </EditorSection>

            <EditorSection title="Data" hint="Which entity the panel reads, and which fields, filters and rows it uses.">
              <QueryTab
                targets={current.targets}
                onChange={(targets) => update({ targets })}
                onRunQuery={() => {}}
                onPanelTypeChange={(type) => update({ type, options: {} })}
                onTitleChange={(title) => update({ title })}
              />
            </EditorSection>

            <EditorSection title="Display options" hint="Settings for this panel type.">
              <PanelDisplayOptions
                panelType={current.type}
                options={current.options}
                onOptionsChange={(options) => update({ options })}
                data={frames}
              />
            </EditorSection>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-border px-5 py-3">
          <span className="text-xs text-muted-foreground" aria-live="polite">
            {changed ? 'Changes not applied yet' : 'No changes'}
          </span>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleClose}>
              Discard
            </Button>
            <Button size="sm" onClick={handleSave}>
              <Icon name="check" className="h-3.5 w-3.5" /> Apply changes
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function EditorSection({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="border-b border-border px-5 py-5 last:border-b-0">
      <h3 className="text-sm font-medium text-foreground">{title}</h3>
      {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
      <div className="mt-3.5">{children}</div>
    </section>
  );
}

/** The panel at the size of its box, with the same chrome it has on the dashboard. */
function PanelPreview({ panel, timeRange, onData }: { panel: PanelModel; timeRange?: TimeRange; onData?: (frames: DataFrame[]) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setSize({ width: Math.round(el.clientWidth), height: Math.round(el.clientHeight) });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div ref={ref} className="h-64 min-h-0 w-full lg:h-auto lg:max-h-[560px] lg:flex-1">
      {size.height > 0 && (
        <PanelChrome
          panel={panel}
          width={size.width}
          height={size.height}
          timeRange={timeRange}
          isEditing={false}
          onData={onData}
        />
      )}
    </div>
  );
}
