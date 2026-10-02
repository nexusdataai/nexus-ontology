import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RefreshCw } from 'lucide-react';

interface Props {
  value: string;
  onChange: (interval: string) => void;
}

const OFF = '__off__';

const INTERVALS = [
  { value: OFF, label: 'Off' },
  { value: '10s', label: '10s' },
  { value: '30s', label: '30s' },
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '30m', label: '30m' },
  { value: '1h', label: '1h' },
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

export function RefreshPicker({ value, onChange }: Props) {
  return (
    <Select
      value={value || OFF}
      onValueChange={(v) => onChange(v === OFF ? '' : v)}
    >
      <SelectTrigger className="h-8 text-xs w-[90px]">
        <RefreshCw className="h-3 w-3 mr-1 text-muted-foreground" />
        <SelectValue>{value || 'Off'}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {INTERVALS.map((i) => (
          <SelectItem key={i.value} value={i.value} className="text-xs">
            {i.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
