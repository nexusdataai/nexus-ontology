import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Clock } from 'lucide-react';
import type { TimeRange } from '../types';

interface Props {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

const QUICK_RANGES = [
  { label: 'Last 15 minutes', from: 'now-15m', to: 'now' },
  { label: 'Last 1 hour', from: 'now-1h', to: 'now' },
  { label: 'Last 6 hours', from: 'now-6h', to: 'now' },
  { label: 'Last 12 hours', from: 'now-12h', to: 'now' },
  { label: 'Last 24 hours', from: 'now-24h', to: 'now' },
  { label: 'Last 7 days', from: 'now-7d', to: 'now' },
  { label: 'Last 30 days', from: 'now-30d', to: 'now' },
  { label: 'Last 90 days', from: 'now-90d', to: 'now' },
];

export function TimeRangePicker({ value, onChange }: Props) {
  const currentLabel = QUICK_RANGES.find((r) => r.from === value.from && r.to === value.to)?.label || `${value.from} to ${value.to}`;

  return (
    <Select
      value={`${value.from}|${value.to}`}
      onValueChange={(v) => {
        const [from, to] = v.split('|');
        onChange({ from, to });
      }}
    >
      <SelectTrigger className="h-8 text-xs w-[180px]">
        <Clock className="h-3 w-3 mr-1 text-muted-foreground" />
        <SelectValue>{currentLabel}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {QUICK_RANGES.map((r) => (
          <SelectItem key={r.from} value={`${r.from}|${r.to}`} className="text-xs">
            {r.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
