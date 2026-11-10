/**
 * Shared pieces for dashboard panels: one loading state, one empty state,
 * one way to label raw field names and format numbers.
 */
import { Skeleton } from '@/components/ui/skeleton';

export function PanelState({ loading, text = 'No data for this panel yet' }: { loading?: boolean; text?: string }) {
  if (loading) {
    return (
      <div className="flex h-full flex-col justify-end gap-2 p-4" aria-busy="true">
        <Skeleton className="h-3 w-1/3" />
        <Skeleton className="h-3 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-5/6" />
      </div>
    );
  }
  return <div className="flex h-full items-center justify-center px-4 text-center text-sm text-muted-foreground">{text}</div>;
}

/** "total_open_ar" → "Total open ar"; keeps short acronyms readable. */
export function fieldLabel(key: unknown): string {
  const s = String(key ?? '').replace(/[_-]+/g, ' ').trim();
  if (!s) return '';
  return (s.charAt(0).toUpperCase() + s.slice(1)).replace(/\b(ar|dso|oee|clv|sku|po|id|kpi|sla|otd|mape)\b/gi, m => m.toUpperCase());
}

export function compactNumber(n: number, digits = 1): string {
  if (!Number.isFinite(n)) return '—';
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(digits) + 'B';
  if (a >= 1e6) return (n / 1e6).toFixed(digits) + 'M';
  if (a >= 1e4) return (n / 1e3).toFixed(digits) + 'K';
  if (a >= 100 || Number.isInteger(n)) return Math.round(n).toLocaleString('en-US');
  return a < 10 ? n.toFixed(2) : n.toFixed(1);
}

export const isNumberLike = (v: unknown) => v !== null && v !== undefined && v !== '' && typeof v !== 'boolean' && !Number.isNaN(Number(v));
