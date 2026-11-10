import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icon } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';

interface Props {
  value: string;
  onChange: (interval: string) => void;
  className?: string;
}

const OFF = '__off__';

const INTERVALS = [
  { value: OFF, label: 'Off', menu: 'Do not refresh' },
  { value: '10s', label: '10s', menu: 'Every 10 seconds' },
  { value: '30s', label: '30s', menu: 'Every 30 seconds' },
  { value: '1m', label: '1m', menu: 'Every minute' },
  { value: '5m', label: '5m', menu: 'Every 5 minutes' },
  { value: '15m', label: '15m', menu: 'Every 15 minutes' },
  { value: '30m', label: '30m', menu: 'Every 30 minutes' },
  { value: '1h', label: '1h', menu: 'Every hour' },
];

export function parseRefreshInterval(interval: string): number {
  if (!interval) return 0;
  const match = interval.match(/^(\d+)(s|m|h)$/);
  if (!match) return 0;
  const num = parseInt(match[1], 10);
  switch (match[2]) {
    case 's': return num * 1000;
    case 'm': return num * 60 * 1000;
    case 'h': return num * 60 * 60 * 1000;
    default: return 0;
  }
}

export function RefreshPicker({ value, onChange, className }: Props) {
  return (
    <Select
      value={value || OFF}
      onValueChange={(v) => onChange(v === OFF ? '' : v)}
    >
      <SelectTrigger aria-label="Refresh" className={cn('h-8 w-auto min-w-[92px] gap-2 text-sm', className)}>
        <div className="flex items-center gap-2 whitespace-nowrap">
          <Icon name="refresh" className="h-3.5 w-3.5 text-subtle-foreground" />
          <SelectValue>{value || 'Off'}</SelectValue>
        </div>
      </SelectTrigger>
      <SelectContent>
        {INTERVALS.map((i) => (
          <SelectItem key={i.value} value={i.value}>
            {i.menu}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
