import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { PanelOptionsEditorProps } from './types';

export function ChartOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">X-Axis Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.xKey as string) || ''}
          onChange={(e) => onChange({ ...options, xKey: e.target.value })}
          placeholder="Auto-detect from first field"
        />
      </div>
      <div>
        <Label className="text-xs">Y-Axis Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.yKey as string) || ''}
          onChange={(e) => onChange({ ...options, yKey: e.target.value })}
          placeholder="Auto-detect from second field"
        />
      </div>
      <div>
        <Label className="text-xs">Color</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.color as string) || '#3b82f6'}
          onChange={(e) => onChange({ ...options, color: e.target.value })}
          type="color"
        />
      </div>
    </div>
  );
}

export function KPIOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Value Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.valueField as string) || ''}
          onChange={(e) => onChange({ ...options, valueField: e.target.value })}
          placeholder="Auto-detect from first field"
        />
      </div>
      <div>
        <Label className="text-xs">Unit</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.unit as string) || ''}
          onChange={(e) => onChange({ ...options, unit: e.target.value })}
          placeholder="%, $, ms, etc."
        />
      </div>
      <div>
        <Label className="text-xs">Target</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.target ?? '')}
          onChange={(e) => onChange({ ...options, target: e.target.value ? Number(e.target.value) : undefined })}
          type="number"
          placeholder="Target value"
        />
      </div>
      <div>
        <Label className="text-xs">Direction (higher or lower is better)</Label>
        <select
          className="w-full h-8 text-xs mt-1 rounded border bg-background px-2"
          value={(options.direction as string) || 'higher'}
          onChange={(e) => onChange({ ...options, direction: e.target.value })}
        >
          <option value="higher">Higher is better</option>
          <option value="lower">Lower is better</option>
        </select>
      </div>
    </div>
  );
}

export function PieChartOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Name Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.nameKey as string) || ''}
          onChange={(e) => onChange({ ...options, nameKey: e.target.value })}
          placeholder="Auto-detect from first field"
        />
      </div>
      <div>
        <Label className="text-xs">Value Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.valueKey as string) || ''}
          onChange={(e) => onChange({ ...options, valueKey: e.target.value })}
          placeholder="Auto-detect from second field"
        />
      </div>
    </div>
  );
}

export function TableOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Visible Columns (comma separated, empty = all)</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={((options.columns as string[]) || []).join(', ')}
          onChange={(e) => {
            const cols = e.target.value.split(',').map((s) => s.trim()).filter(Boolean);
            onChange({ ...options, columns: cols.length ? cols : undefined });
          }}
          placeholder="All columns"
        />
      </div>
    </div>
  );
}

export function GaugeOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Value Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.valueField as string) || ''}
          onChange={(e) => onChange({ ...options, valueField: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Min</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.min ?? 0)}
          onChange={(e) => onChange({ ...options, min: Number(e.target.value) })}
          type="number"
        />
      </div>
      <div>
        <Label className="text-xs">Max</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.max ?? 100)}
          onChange={(e) => onChange({ ...options, max: Number(e.target.value) })}
          type="number"
        />
      </div>
      <div>
        <Label className="text-xs">Unit</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.unit as string) || ''}
          onChange={(e) => onChange({ ...options, unit: e.target.value })}
        />
      </div>
    </div>
  );
}

export function TextOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Content</Label>
        <textarea
          className="w-full h-32 text-xs mt-1 rounded border bg-background px-2 py-1 resize-none"
          value={(options.content as string) || ''}
          onChange={(e) => onChange({ ...options, content: e.target.value })}
          placeholder="Enter text or markdown content..."
        />
      </div>
    </div>
  );
}

export function BarGaugeOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Name Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.nameKey as string) || ''}
          onChange={(e) => onChange({ ...options, nameKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Value Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.valueKey as string) || ''}
          onChange={(e) => onChange({ ...options, valueKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Orientation</Label>
        <select
          className="w-full h-8 text-xs mt-1 rounded border bg-background px-2"
          value={(options.orientation as string) || 'horizontal'}
          onChange={(e) => onChange({ ...options, orientation: e.target.value })}
        >
          <option value="horizontal">Horizontal</option>
          <option value="vertical">Vertical</option>
        </select>
      </div>
      <div>
        <Label className="text-xs">Display Mode</Label>
        <select
          className="w-full h-8 text-xs mt-1 rounded border bg-background px-2"
          value={(options.displayMode as string) || 'gradient'}
          onChange={(e) => onChange({ ...options, displayMode: e.target.value })}
        >
          <option value="gradient">Gradient</option>
          <option value="basic">Basic</option>
          <option value="lcd">LCD</option>
        </select>
      </div>
      <div>
        <Label className="text-xs">Min</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.min ?? 0)}
          onChange={(e) => onChange({ ...options, min: Number(e.target.value) })}
          type="number"
        />
      </div>
      <div>
        <Label className="text-xs">Max</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.max ?? 100)}
          onChange={(e) => onChange({ ...options, max: Number(e.target.value) })}
          type="number"
        />
      </div>
    </div>
  );
}

export function TimeSeriesOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">X-Axis Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.xKey as string) || ''}
          onChange={(e) => onChange({ ...options, xKey: e.target.value })}
          placeholder="Auto-detect (time field)"
        />
      </div>
      <div>
        <Label className="text-xs">Y-Axis Fields (comma separated)</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={((options.yFields as string[]) || []).join(', ')}
          onChange={(e) => {
            const fields = e.target.value.split(',').map((s) => s.trim()).filter(Boolean);
            onChange({ ...options, yFields: fields.length ? fields : undefined });
          }}
          placeholder="Auto-detect numeric fields"
        />
      </div>
      <div>
        <Label className="text-xs">Draw Style</Label>
        <select
          className="w-full h-8 text-xs mt-1 rounded border bg-background px-2"
          value={(options.drawStyle as string) || 'line'}
          onChange={(e) => onChange({ ...options, drawStyle: e.target.value })}
        >
          <option value="line">Line</option>
          <option value="area">Area</option>
          <option value="bars">Bars</option>
        </select>
      </div>
      <div>
        <Label className="text-xs">Fill Opacity (0-1)</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.fillOpacity ?? '')}
          onChange={(e) => onChange({ ...options, fillOpacity: e.target.value ? Number(e.target.value) : undefined })}
          type="number"
          step="0.1"
          min="0"
          max="1"
          placeholder="0 for line, 0.3 for area"
        />
      </div>
      <div>
        <Label className="text-xs">Stacking</Label>
        <select
          className="w-full h-8 text-xs mt-1 rounded border bg-background px-2"
          value={(options.stacking as string) || 'none'}
          onChange={(e) => onChange({ ...options, stacking: e.target.value })}
        >
          <option value="none">None</option>
          <option value="normal">Normal</option>
          <option value="percent">Percent</option>
        </select>
      </div>
      <div>
        <Label className="text-xs">Legend Position</Label>
        <select
          className="w-full h-8 text-xs mt-1 rounded border bg-background px-2"
          value={(options.legendPosition as string) || 'bottom'}
          onChange={(e) => onChange({ ...options, legendPosition: e.target.value })}
        >
          <option value="bottom">Bottom</option>
          <option value="top">Top</option>
        </select>
      </div>
    </div>
  );
}

export function HistogramOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Value Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.valueField as string) || ''}
          onChange={(e) => onChange({ ...options, valueField: e.target.value })}
          placeholder="Auto-detect first numeric field"
        />
      </div>
      <div>
        <Label className="text-xs">Bucket Count (0 = auto)</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.bucketCount ?? 0)}
          onChange={(e) => onChange({ ...options, bucketCount: Number(e.target.value) })}
          type="number"
          min="0"
        />
      </div>
      <div>
        <Label className="text-xs">Color</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.color as string) || '#3b82f6'}
          onChange={(e) => onChange({ ...options, color: e.target.value })}
          type="color"
        />
      </div>
    </div>
  );
}

export function HeatmapOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">X-Axis Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.xKey as string) || ''}
          onChange={(e) => onChange({ ...options, xKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Y-Axis Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.yKey as string) || ''}
          onChange={(e) => onChange({ ...options, yKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Value Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.valueKey as string) || ''}
          onChange={(e) => onChange({ ...options, valueKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Color Scheme</Label>
        <select
          className="w-full h-8 text-xs mt-1 rounded border bg-background px-2"
          value={(options.colorScheme as string) || 'blues'}
          onChange={(e) => onChange({ ...options, colorScheme: e.target.value })}
        >
          <option value="blues">Blues</option>
          <option value="greens">Greens</option>
          <option value="reds">Reds</option>
          <option value="spectral">Spectral</option>
        </select>
      </div>
      <div>
        <Label className="text-xs">Cell Gap</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.cellGap ?? 1)}
          onChange={(e) => onChange({ ...options, cellGap: Number(e.target.value) })}
          type="number"
          min="0"
          max="4"
        />
      </div>
    </div>
  );
}

export function StateTimelineOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Entity Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.entityKey as string) || ''}
          onChange={(e) => onChange({ ...options, entityKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Time Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.timeKey as string) || ''}
          onChange={(e) => onChange({ ...options, timeKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">State Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.stateKey as string) || ''}
          onChange={(e) => onChange({ ...options, stateKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Show Value</Label>
        <select
          className="w-full h-8 text-xs mt-1 rounded border bg-background px-2"
          value={(options.showValue as string) || 'auto'}
          onChange={(e) => onChange({ ...options, showValue: e.target.value })}
        >
          <option value="auto">Auto</option>
          <option value="always">Always</option>
          <option value="never">Never</option>
        </select>
      </div>
      <div>
        <Label className="text-xs">Row Height</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.rowHeight ?? 28)}
          onChange={(e) => onChange({ ...options, rowHeight: Number(e.target.value) })}
          type="number"
          min="16"
          max="64"
        />
      </div>
    </div>
  );
}

export function XYChartOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">X-Axis Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.xField as string) || ''}
          onChange={(e) => onChange({ ...options, xField: e.target.value })}
          placeholder="Auto-detect first numeric field"
        />
      </div>
      <div>
        <Label className="text-xs">Y-Axis Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.yField as string) || ''}
          onChange={(e) => onChange({ ...options, yField: e.target.value })}
          placeholder="Auto-detect second numeric field"
        />
      </div>
      <div>
        <Label className="text-xs">Size Field (optional, for bubble)</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.sizeField as string) || ''}
          onChange={(e) => onChange({ ...options, sizeField: e.target.value || undefined })}
          placeholder="None"
        />
      </div>
      <div>
        <Label className="text-xs">Color Group Field (optional)</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.colorField as string) || ''}
          onChange={(e) => onChange({ ...options, colorField: e.target.value || undefined })}
          placeholder="None"
        />
      </div>
      <div>
        <Label className="text-xs">Point Size</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.pointSize ?? 8)}
          onChange={(e) => onChange({ ...options, pointSize: Number(e.target.value) })}
          type="number"
          min="2"
          max="24"
        />
      </div>
    </div>
  );
}

export function StatusHistoryOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Entity Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.entityKey as string) || ''}
          onChange={(e) => onChange({ ...options, entityKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Time Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.timeKey as string) || ''}
          onChange={(e) => onChange({ ...options, timeKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Status Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.statusKey as string) || ''}
          onChange={(e) => onChange({ ...options, statusKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
    </div>
  );
}

export function TrendOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">X-Axis Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.xKey as string) || ''}
          onChange={(e) => onChange({ ...options, xKey: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Y-Axis Fields (comma separated)</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={((options.yFields as string[]) || []).join(', ')}
          onChange={(e) => {
            const fields = e.target.value.split(',').map((s) => s.trim()).filter(Boolean);
            onChange({ ...options, yFields: fields.length ? fields : undefined });
          }}
          placeholder="Auto-detect numeric fields"
        />
      </div>
      <div>
        <Label className="text-xs">Draw Style</Label>
        <select
          className="w-full h-8 text-xs mt-1 rounded border bg-background px-2"
          value={(options.drawStyle as string) || 'line'}
          onChange={(e) => onChange({ ...options, drawStyle: e.target.value })}
        >
          <option value="line">Line</option>
          <option value="area">Area</option>
          <option value="bars">Bars</option>
        </select>
      </div>
    </div>
  );
}

export function NodeGraphOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Node ID Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.nodeIdField as string) || ''}
          onChange={(e) => onChange({ ...options, nodeIdField: e.target.value })}
          placeholder="id"
        />
      </div>
      <div>
        <Label className="text-xs">Node Label Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.nodeLabelField as string) || ''}
          onChange={(e) => onChange({ ...options, nodeLabelField: e.target.value })}
          placeholder="label"
        />
      </div>
      <div>
        <Label className="text-xs">Source Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.sourceField as string) || ''}
          onChange={(e) => onChange({ ...options, sourceField: e.target.value })}
          placeholder="source"
        />
      </div>
      <div>
        <Label className="text-xs">Target Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.targetField as string) || ''}
          onChange={(e) => onChange({ ...options, targetField: e.target.value })}
          placeholder="target"
        />
      </div>
      <div>
        <Label className="text-xs">Node Size</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.nodeSize ?? 16)}
          onChange={(e) => onChange({ ...options, nodeSize: Number(e.target.value) })}
          type="number"
          min="8"
          max="40"
        />
      </div>
    </div>
  );
}

export function CandlestickOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Label / Time Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.labelField as string) || ''}
          onChange={(e) => onChange({ ...options, labelField: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Open Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.openField as string) || ''}
          onChange={(e) => onChange({ ...options, openField: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">High Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.highField as string) || ''}
          onChange={(e) => onChange({ ...options, highField: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Low Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.lowField as string) || ''}
          onChange={(e) => onChange({ ...options, lowField: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Close Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.closeField as string) || ''}
          onChange={(e) => onChange({ ...options, closeField: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Up Color</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.colorUp as string) || '#22c55e'}
          onChange={(e) => onChange({ ...options, colorUp: e.target.value })}
          type="color"
        />
      </div>
      <div>
        <Label className="text-xs">Down Color</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.colorDown as string) || '#ef4444'}
          onChange={(e) => onChange({ ...options, colorDown: e.target.value })}
          type="color"
        />
      </div>
    </div>
  );
}

export function AnnotationsListOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={(options.showTags as boolean) ?? true}
          onChange={(e) => onChange({ ...options, showTags: e.target.checked })}
          className="rounded"
        />
        <Label className="text-xs">Show Tags</Label>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={(options.showUser as boolean) ?? true}
          onChange={(e) => onChange({ ...options, showUser: e.target.checked })}
          className="rounded"
        />
        <Label className="text-xs">Show User</Label>
      </div>
      <div>
        <Label className="text-xs">Max Items</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.limit ?? 50)}
          onChange={(e) => onChange({ ...options, limit: Number(e.target.value) })}
          type="number"
          min="1"
          max="200"
        />
      </div>
    </div>
  );
}

export function GeomapOptionsEditor({ options, onChange }: PanelOptionsEditorProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Latitude Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.latField as string) || ''}
          onChange={(e) => onChange({ ...options, latField: e.target.value })}
          placeholder="Auto-detect (lat/latitude)"
        />
      </div>
      <div>
        <Label className="text-xs">Longitude Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.lngField as string) || ''}
          onChange={(e) => onChange({ ...options, lngField: e.target.value })}
          placeholder="Auto-detect (lng/lon/longitude)"
        />
      </div>
      <div>
        <Label className="text-xs">Label Field</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.labelField as string) || ''}
          onChange={(e) => onChange({ ...options, labelField: e.target.value })}
          placeholder="Auto-detect"
        />
      </div>
      <div>
        <Label className="text-xs">Value Field (optional, for sizing)</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.valueField as string) || ''}
          onChange={(e) => onChange({ ...options, valueField: e.target.value || undefined })}
          placeholder="None"
        />
      </div>
      <div>
        <Label className="text-xs">Color Group Field (optional)</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={(options.colorField as string) || ''}
          onChange={(e) => onChange({ ...options, colorField: e.target.value || undefined })}
          placeholder="None"
        />
      </div>
      <div>
        <Label className="text-xs">Point Size</Label>
        <Input
          className="h-8 text-xs mt-1"
          value={String(options.pointSize ?? 6)}
          onChange={(e) => onChange({ ...options, pointSize: Number(e.target.value) })}
          type="number"
          min="2"
          max="20"
        />
      </div>
    </div>
  );
}

export function EmptyOptionsEditor() {
  return <div className="text-xs text-muted-foreground">No additional options for this panel.</div>;
}
