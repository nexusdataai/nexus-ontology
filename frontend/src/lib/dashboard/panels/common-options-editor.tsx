/**
 * Display options for each panel type (the "Display options" section of the
 * panel editor). Every editor writes the same option keys, with the same value
 * types, as before the redesign; only the controls changed.
 *
 * When the panel's query has returned data, field options are picked from the
 * real fields instead of being typed. "Automatic" leaves the option empty, so
 * the panel chooses a field itself, exactly as an empty text box did.
 */
import { useId } from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Field } from '@/components/ds/kit';
import { Icon } from '@/components/ds/Icon';
import { CHART_COLORS } from '@/components/ds/charts';
import { cn } from '@/lib/utils';
import type { DataField, DataFrame } from '../types';
import type { PanelOptionsEditorProps } from './types';

/* ------------------------------------------------------------------ helpers */

type Opts = Record<string, unknown>;
type Kind = 'number' | 'time' | 'any';

const AUTO = '__auto';

/** Every field the panel's query returned, once each. */
function fieldsOf(data?: DataFrame[]): DataField[] {
  const seen = new Map<string, DataField>();
  for (const frame of data || []) for (const f of frame.fields || []) if (!seen.has(f.name)) seen.set(f.name, f);
  return [...seen.values()];
}

function fieldsOfKind(data: DataFrame[] | undefined, kind: Kind): string[] {
  const all = fieldsOf(data);
  const pick = kind === 'any' ? all : all.filter((f) => f.type === kind);
  // Fall back to every field when none has the expected type (types are inferred).
  return (pick.length ? pick : all).map((f) => f.name);
}

const pretty = (name: string) => name.replace(/_/g, ' ');

function Grid({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-x-4 gap-y-4 sm:grid-cols-2">{children}</div>;
}

interface FieldPickProps {
  label: string;
  hint?: string;
  value: unknown;
  /** Called with the field name, or with '' / undefined for "Automatic". */
  onChange: (value: string | undefined) => void;
  data?: DataFrame[];
  kind?: Kind;
  /** Text shown for the empty choice. */
  autoLabel?: string;
  /** Optional options store undefined when cleared; the others store ''. */
  optional?: boolean;
  placeholder?: string;
}

/** One field of the query result. A list when there is data, a text box when there is none. */
function FieldPick({ label, hint, value, onChange, data, kind = 'any', autoLabel = 'Automatic', optional, placeholder }: FieldPickProps) {
  const id = useId();
  const current = typeof value === 'string' ? value : '';
  const names = fieldsOfKind(data, kind);
  const clear = optional ? undefined : '';

  if (names.length === 0) {
    return (
      <Field label={label} hint={hint} htmlFor={id}>
        <Input id={id} value={current} onChange={(e) => onChange(e.target.value || clear)} placeholder={placeholder || autoLabel} />
      </Field>
    );
  }

  const options = current && !names.includes(current) ? [current, ...names] : names;
  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <Select value={current || AUTO} onValueChange={(v) => onChange(v === AUTO ? clear : v)}>
        <SelectTrigger id={id}><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value={AUTO}>{autoLabel}</SelectItem>
          {options.map((n) => <SelectItem key={n} value={n}>{pretty(n)}</SelectItem>)}
        </SelectContent>
      </Select>
    </Field>
  );
}

interface FieldsPickProps {
  label: string;
  hint?: string;
  value: unknown;
  onChange: (value: string[] | undefined) => void;
  data?: DataFrame[];
  kind?: Kind;
  emptyText: string;
}

/** Several fields. Toggle chips when there is data, a comma-separated box when there is none. */
function FieldsPick({ label, hint, value, onChange, data, kind = 'any', emptyText }: FieldsPickProps) {
  const id = useId();
  const current = Array.isArray(value) ? (value as string[]) : [];
  const names = fieldsOfKind(data, kind);

  if (names.length === 0) {
    return (
      <Field label={label} hint={hint || 'Separate names with commas.'} htmlFor={id} className="sm:col-span-2">
        <Input
          id={id}
          value={current.join(', ')}
          onChange={(e) => {
            const list = e.target.value.split(',').map((s) => s.trim()).filter(Boolean);
            onChange(list.length ? list : undefined);
          }}
          placeholder={emptyText}
        />
      </Field>
    );
  }

  const options = [...new Set([...current, ...names])];
  const toggle = (n: string) => {
    const next = current.includes(n) ? current.filter((c) => c !== n) : [...current, n];
    onChange(next.length ? next : undefined);
  };
  return (
    <Field label={label} hint={current.length === 0 ? emptyText : hint} className="sm:col-span-2">
      <div className="flex flex-wrap gap-1.5" role="group" aria-label={label}>
        {options.map((n) => {
          const on = current.includes(n);
          return (
            <button
              key={n}
              type="button"
              aria-pressed={on}
              onClick={() => toggle(n)}
              className={cn(
                'inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                on ? 'border-primary/50 bg-primary/10 text-foreground' : 'border-border text-muted-foreground hover:border-border-strong hover:text-foreground',
              )}
            >
              {on && <Icon name="check" className="h-3.5 w-3.5 text-primary dark:text-brand-hi" />}
              {pretty(n)}
            </button>
          );
        })}
      </div>
    </Field>
  );
}

interface NumProps {
  label: string;
  hint?: string;
  value: unknown;
  fallback?: number;
  /** Receives the raw text; each caller keeps its own rule for an empty box. */
  onRaw: (raw: string) => void;
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
}

function Num({ label, hint, value, fallback, onRaw, min, max, step, placeholder }: NumProps) {
  const id = useId();
  const shown = value === undefined || value === null ? (fallback !== undefined ? String(fallback) : '') : String(value);
  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <Input id={id} type="number" inputMode="decimal" value={shown} min={min} max={max} step={step} placeholder={placeholder} onChange={(e) => onRaw(e.target.value)} className="num" />
    </Field>
  );
}

function Text({ label, hint, value, onChange, placeholder }: { label: string; hint?: string; value: unknown; onChange: (v: string) => void; placeholder?: string }) {
  const id = useId();
  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <Input id={id} value={(value as string) || ''} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </Field>
  );
}

function Choice({ label, hint, value, fallback, options, onChange }: { label: string; hint?: string; value: unknown; fallback: string; options: { value: string; label: string }[]; onChange: (v: string) => void }) {
  const id = useId();
  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <Select value={(value as string) || fallback} onValueChange={onChange}>
        <SelectTrigger id={id}><SelectValue /></SelectTrigger>
        <SelectContent>
          {options.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
        </SelectContent>
      </Select>
    </Field>
  );
}

const SWATCH_NAMES = ['Blue', 'Light blue', 'Slate', 'Teal', 'Amber', 'Violet'];

/**
 * Colour from the product palette. Values are the palette tokens, so a chart
 * follows the light and dark themes. A colour saved before (a hex code) is kept
 * and shown as its own swatch.
 */
function ColorPick({ label, value, onChange, palette = CHART_COLORS, names = SWATCH_NAMES, autoLabel = 'Automatic' }: { label: string; value: unknown; onChange: (v: string | undefined) => void; palette?: string[]; names?: string[]; autoLabel?: string }) {
  const current = typeof value === 'string' ? value : '';
  const extra = current && !palette.includes(current) ? [current] : [];
  const swatch = (color: string, name: string, key: string) => {
    const on = current === color;
    return (
      <button
        key={key}
        type="button"
        aria-pressed={on}
        aria-label={name}
        title={name}
        onClick={() => onChange(color)}
        className={cn('grid h-8 w-8 place-items-center rounded-md border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring', on ? 'border-foreground/60' : 'border-border hover:border-border-strong')}
      >
        <span className="h-4 w-4 rounded-sm" style={{ background: color }} />
      </button>
    );
  };
  return (
    <Field label={label} className="sm:col-span-2">
      <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label={label}>
        <button
          type="button"
          aria-pressed={!current}
          onClick={() => onChange(undefined)}
          className={cn('inline-flex h-8 items-center rounded-md border px-2.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring', !current ? 'border-foreground/60 text-foreground' : 'border-border text-muted-foreground hover:text-foreground')}
        >
          {autoLabel}
        </button>
        {palette.map((c, i) => swatch(c, names[i] || `Colour ${i + 1}`, c))}
        {extra.map((c) => swatch(c, `Saved colour ${c}`, `x-${c}`))}
      </div>
    </Field>
  );
}

function Toggle({ label, hint, checked, onChange }: { label: string; hint?: string; checked: boolean; onChange: (v: boolean) => void }) {
  const id = useId();
  return (
    <div className="flex items-start justify-between gap-4 rounded-lg border border-border px-3 py-2.5">
      <div className="min-w-0">
        <label htmlFor={id} className="block text-sm font-medium text-foreground">{label}</label>
        {hint && <p className="mt-0.5 text-xs text-subtle-foreground">{hint}</p>}
      </div>
      <Switch id={id} checked={checked} onCheckedChange={onChange} />
    </div>
  );
}

const set = (options: Opts, onChange: (o: Opts) => void) => (key: string, value: unknown) => onChange({ ...options, [key]: value });

/* ------------------------------------------------------------------ editors */

export function ChartOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Category field" hint="Shown along the horizontal axis." value={options.xKey} onChange={(v) => s('xKey', v)} data={data} autoLabel="Automatic (first field)" />
      <FieldPick label="Value field" hint="The number each bar or point shows." value={options.yKey} onChange={(v) => s('yKey', v)} data={data} kind="number" autoLabel="Automatic (second field)" />
    </Grid>
  );
}

export function KPIOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Value field" value={options.valueField} onChange={(v) => s('valueField', v)} data={data} kind="number" autoLabel="Automatic (first field)" />
      <Text label="Unit" hint="Shown after the number, for example %, days or ms." value={options.unit} onChange={(v) => s('unit', v)} placeholder="None" />
      <Num label="Target" value={options.target} onRaw={(r) => s('target', r ? Number(r) : undefined)} placeholder="No target" />
      <Choice
        label="Better when the number is"
        hint="Decides whether the card reads on or off target."
        value={options.direction}
        fallback={AUTO}
        options={[
          { value: AUTO, label: 'Worked out from the name' },
          { value: 'higher', label: 'Higher' },
          { value: 'lower', label: 'Lower' },
        ]}
        onChange={(v) => s('direction', v === AUTO ? undefined : v)}
      />
    </Grid>
  );
}

export function PieChartOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Label field" hint="One slice for each value." value={options.nameKey} onChange={(v) => s('nameKey', v)} data={data} autoLabel="Automatic (first field)" />
      <FieldPick label="Size field" hint="How big each slice is." value={options.valueKey} onChange={(v) => s('valueKey', v)} data={data} kind="number" autoLabel="Automatic (second field)" />
    </Grid>
  );
}

export function TableOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldsPick label="Columns shown" hint="Shown in the order you pick them." value={options.columns} onChange={(v) => s('columns', v)} data={data} emptyText="None picked: every column is shown." />
    </Grid>
  );
}

export function GaugeOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Value field" value={options.valueField} onChange={(v) => s('valueField', v)} data={data} kind="number" />
      <Text label="Unit" value={options.unit} onChange={(v) => s('unit', v)} placeholder="None" />
      <Num label="Minimum" value={options.min} fallback={0} onRaw={(r) => s('min', Number(r))} />
      <Num label="Maximum" value={options.max} fallback={100} onRaw={(r) => s('max', Number(r))} />
    </Grid>
  );
}

export function TextOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  const id = useId();
  return (
    <Field label="Content" hint="Markdown works: headings, lists, links and bold text." htmlFor={id}>
      <Textarea
        id={id}
        className="min-h-[160px] font-mono text-sm"
        value={(options.content as string) || ''}
        onChange={(e) => onChange({ ...options, content: e.target.value })}
        placeholder="Write a note for the people who read this dashboard."
      />
    </Field>
  );
}

export function BarGaugeOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Label field" value={options.nameKey} onChange={(v) => s('nameKey', v)} data={data} />
      <FieldPick label="Value field" value={options.valueKey} onChange={(v) => s('valueKey', v)} data={data} kind="number" />
      <Choice label="Direction" value={options.orientation} fallback="horizontal" options={[{ value: 'horizontal', label: 'Horizontal bars' }, { value: 'vertical', label: 'Vertical bars' }]} onChange={(v) => s('orientation', v)} />
      <Choice label="Bar style" value={options.displayMode} fallback="gradient" options={[{ value: 'gradient', label: 'Shaded' }, { value: 'basic', label: 'Solid' }, { value: 'lcd', label: 'Segmented' }]} onChange={(v) => s('displayMode', v)} />
      <Num label="Minimum" value={options.min} fallback={0} onRaw={(r) => s('min', Number(r))} />
      <Num label="Maximum" value={options.max} fallback={100} onRaw={(r) => s('max', Number(r))} />
    </Grid>
  );
}

export function TimeSeriesOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Time field" value={options.xKey} onChange={(v) => s('xKey', v)} data={data} kind="time" autoLabel="Automatic (the time field)" />
      <Choice label="Draw as" value={options.drawStyle} fallback="line" options={[{ value: 'line', label: 'Line' }, { value: 'area', label: 'Area' }, { value: 'bars', label: 'Bars' }]} onChange={(v) => s('drawStyle', v)} />
      <FieldsPick label="Series" value={options.yFields} onChange={(v) => s('yFields', v)} data={data} kind="number" emptyText="None picked: every number field is drawn." />
      <Num label="Fill strength" hint="From 0 (no fill) to 1. About 0.3 reads well for an area." value={options.fillOpacity} onRaw={(r) => s('fillOpacity', r ? Number(r) : undefined)} min={0} max={1} step={0.1} placeholder="Automatic" />
      <Choice label="Stacking" value={options.stacking} fallback="none" options={[{ value: 'none', label: 'Side by side' }, { value: 'normal', label: 'Stacked' }, { value: 'percent', label: 'Stacked to 100%' }]} onChange={(v) => s('stacking', v)} />
      <Choice label="Legend" value={options.legendPosition} fallback="bottom" options={[{ value: 'bottom', label: 'Below the chart' }, { value: 'top', label: 'Above the chart' }]} onChange={(v) => s('legendPosition', v)} />
    </Grid>
  );
}

export function HistogramOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Value field" value={options.valueField} onChange={(v) => s('valueField', v)} data={data} kind="number" autoLabel="Automatic (first number field)" />
      <Num label="Number of buckets" hint="0 chooses a good number for the data." value={options.bucketCount} fallback={0} onRaw={(r) => s('bucketCount', Number(r))} min={0} />
      <ColorPick label="Colour" value={options.color} onChange={(v) => s('color', v)} />
    </Grid>
  );
}

export function HeatmapOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Columns from" value={options.xKey} onChange={(v) => s('xKey', v)} data={data} />
      <FieldPick label="Rows from" value={options.yKey} onChange={(v) => s('yKey', v)} data={data} />
      <FieldPick label="Cell value" value={options.valueKey} onChange={(v) => s('valueKey', v)} data={data} kind="number" />
      <Choice label="Colour scale" value={options.colorScheme} fallback="blues" options={[{ value: 'blues', label: 'Blues' }, { value: 'greens', label: 'Greens' }, { value: 'reds', label: 'Reds' }, { value: 'spectral', label: 'Spectral' }]} onChange={(v) => s('colorScheme', v)} />
      <Num label="Gap between cells" hint="In pixels, 0 to 4." value={options.cellGap} fallback={1} onRaw={(r) => s('cellGap', Number(r))} min={0} max={4} />
    </Grid>
  );
}

export function StateTimelineOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="One row for each" value={options.entityKey} onChange={(v) => s('entityKey', v)} data={data} />
      <FieldPick label="Time field" value={options.timeKey} onChange={(v) => s('timeKey', v)} data={data} kind="time" />
      <FieldPick label="State field" value={options.stateKey} onChange={(v) => s('stateKey', v)} data={data} />
      <Choice label="Show the state name" value={options.showValue} fallback="auto" options={[{ value: 'auto', label: 'When it fits' }, { value: 'always', label: 'Always' }, { value: 'never', label: 'Never' }]} onChange={(v) => s('showValue', v)} />
      <Num label="Row height" hint="In pixels, 16 to 64." value={options.rowHeight} fallback={28} onRaw={(r) => s('rowHeight', Number(r))} min={16} max={64} />
    </Grid>
  );
}

export function XYChartOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Horizontal axis" value={options.xField} onChange={(v) => s('xField', v)} data={data} kind="number" autoLabel="Automatic (first number field)" />
      <FieldPick label="Vertical axis" value={options.yField} onChange={(v) => s('yField', v)} data={data} kind="number" autoLabel="Automatic (second number field)" />
      <FieldPick label="Point size from" hint="Turns the chart into bubbles." value={options.sizeField} onChange={(v) => s('sizeField', v)} data={data} kind="number" autoLabel="None" optional />
      <FieldPick label="Colour points by" value={options.colorField} onChange={(v) => s('colorField', v)} data={data} autoLabel="None" optional />
      <Num label="Point size" hint="In pixels, 2 to 24." value={options.pointSize} fallback={8} onRaw={(r) => s('pointSize', Number(r))} min={2} max={24} />
      <ColorPick label="Colour" value={options.color} onChange={(v) => s('color', v)} />
    </Grid>
  );
}

export function StatusHistoryOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="One row for each" value={options.entityKey} onChange={(v) => s('entityKey', v)} data={data} />
      <FieldPick label="Time field" value={options.timeKey} onChange={(v) => s('timeKey', v)} data={data} kind="time" />
      <FieldPick label="Status field" value={options.statusKey} onChange={(v) => s('statusKey', v)} data={data} />
    </Grid>
  );
}

export function TrendOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Along the horizontal axis" value={options.xKey} onChange={(v) => s('xKey', v)} data={data} />
      <Choice label="Draw as" value={options.drawStyle} fallback="line" options={[{ value: 'line', label: 'Line' }, { value: 'area', label: 'Area' }, { value: 'bars', label: 'Bars' }]} onChange={(v) => s('drawStyle', v)} />
      <FieldsPick label="Series" value={options.yFields} onChange={(v) => s('yFields', v)} data={data} kind="number" emptyText="None picked: every number field is drawn." />
    </Grid>
  );
}

export function NodeGraphOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Node ID field" value={options.nodeIdField} onChange={(v) => s('nodeIdField', v)} data={data} placeholder="id" />
      <FieldPick label="Node name field" value={options.nodeLabelField} onChange={(v) => s('nodeLabelField', v)} data={data} placeholder="label" />
      <FieldPick label="Link starts at" value={options.sourceField} onChange={(v) => s('sourceField', v)} data={data} placeholder="source" />
      <FieldPick label="Link ends at" value={options.targetField} onChange={(v) => s('targetField', v)} data={data} placeholder="target" />
      <Num label="Node size" hint="In pixels, 8 to 40." value={options.nodeSize} fallback={16} onRaw={(r) => s('nodeSize', Number(r))} min={8} max={40} />
    </Grid>
  );
}

const UP_DOWN = ['hsl(var(--success))', 'hsl(var(--destructive))', ...CHART_COLORS];
const UP_DOWN_NAMES = ['Green', 'Red', ...SWATCH_NAMES];

export function CandlestickOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Time or label field" value={options.labelField} onChange={(v) => s('labelField', v)} data={data} />
      <FieldPick label="Open" value={options.openField} onChange={(v) => s('openField', v)} data={data} kind="number" />
      <FieldPick label="High" value={options.highField} onChange={(v) => s('highField', v)} data={data} kind="number" />
      <FieldPick label="Low" value={options.lowField} onChange={(v) => s('lowField', v)} data={data} kind="number" />
      <FieldPick label="Close" value={options.closeField} onChange={(v) => s('closeField', v)} data={data} kind="number" />
      <ColorPick label="Rising colour" value={options.colorUp} onChange={(v) => s('colorUp', v)} palette={UP_DOWN} names={UP_DOWN_NAMES} autoLabel="Automatic (green)" />
      <ColorPick label="Falling colour" value={options.colorDown} onChange={(v) => s('colorDown', v)} palette={UP_DOWN} names={UP_DOWN_NAMES} autoLabel="Automatic (red)" />
    </Grid>
  );
}

export function AnnotationsListOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <div className="space-y-3">
      <Toggle label="Show tags" checked={(options.showTags as boolean) ?? true} onChange={(v) => s('showTags', v)} />
      <Toggle label="Show who added it" checked={(options.showUser as boolean) ?? true} onChange={(v) => s('showUser', v)} />
      <Grid>
        <Num label="Most items shown" hint="1 to 200." value={options.limit} fallback={50} onRaw={(r) => s('limit', Number(r))} min={1} max={200} />
      </Grid>
    </div>
  );
}

export function GeomapOptionsEditor({ options, onChange, data }: PanelOptionsEditorProps) {
  const s = set(options, onChange);
  return (
    <Grid>
      <FieldPick label="Latitude" value={options.latField} onChange={(v) => s('latField', v)} data={data} kind="number" autoLabel="Automatic (lat or latitude)" />
      <FieldPick label="Longitude" value={options.lngField} onChange={(v) => s('lngField', v)} data={data} kind="number" autoLabel="Automatic (lng, lon or longitude)" />
      <FieldPick label="Label field" value={options.labelField} onChange={(v) => s('labelField', v)} data={data} />
      <FieldPick label="Point size from" value={options.valueField} onChange={(v) => s('valueField', v)} data={data} kind="number" autoLabel="None" optional />
      <FieldPick label="Colour points by" value={options.colorField} onChange={(v) => s('colorField', v)} data={data} autoLabel="None" optional />
      <Num label="Point size" hint="In pixels, 2 to 20." value={options.pointSize} fallback={6} onRaw={(r) => s('pointSize', Number(r))} min={2} max={20} />
    </Grid>
  );
}

export function EmptyOptionsEditor() {
  return <p className="text-sm text-muted-foreground">This panel type has no display options.</p>;
}
