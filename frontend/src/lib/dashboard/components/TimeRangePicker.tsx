import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icon } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';
import type { TimeRange } from '../types';

interface Props {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  className?: string;
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

export function TimeRangePicker({ value, onChange, className }: Props) {
  const currentLabel = QUICK_RANGES.find((r) => r.from === value.from && r.to === value.to)?.label || `${value.from} to ${value.to}`;

  return (
    <Select
      value={`${value.from}|${value.to}`}
      onValueChange={(v) => {
        const [from, to] = v.split('|');
        onChange({ from, to });
      }}
    >
      <SelectTrigger aria-label="Time range" className={cn('h-8 w-auto min-w-[168px] gap-2 text-sm', className)}>
        <div className="flex min-w-0 items-center gap-2 whitespace-nowrap">
          <Icon name="clock" className="h-3.5 w-3.5 text-subtle-foreground" />
          <SelectValue>{currentLabel}</SelectValue>
        </div>
      </SelectTrigger>
      <SelectContent>
        {QUICK_RANGES.map((r) => (
          <SelectItem key={r.from} value={`${r.from}|${r.to}`}>
            {r.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
