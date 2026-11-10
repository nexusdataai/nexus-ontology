/**
 * Shared frame and helpers for solution dashboard widgets, so every widget
 * has the same header, loading state, empty state and number formatting.
 */
import * as React from 'react';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

interface WidgetFrameProps {
  title: React.ReactNode;
  /** One muted line under the title: what the chart shows. */
  description?: React.ReactNode;
  /** Right side of the header: a total, a count, a link. */
  aside?: React.ReactNode;
  loading?: boolean;
  empty?: boolean;
  emptyText?: string;
  /** Body without padding (tables, lists). */
  flush?: boolean;
  minHeight?: number;
  className?: string;
  children?: React.ReactNode;
}

export function WidgetFrame({ title, description, aside, loading, empty, emptyText = 'No data yet', flush, minHeight = 240, className, children }: WidgetFrameProps) {
  return (
    <section className={cn('flex h-full min-w-0 flex-col overflow-hidden rounded-xl border border-border bg-card shadow-xs', className)}>
      <header className="flex items-start justify-between gap-4 px-5 pt-4">
        <div className="min-w-0">
          <h3 className="truncate text-md font-medium text-foreground">{title}</h3>
          {description && <p className="mt-0.5 truncate text-xs text-muted-foreground">{description}</p>}
        </div>
        {aside && !loading && <div className="shrink-0 text-right">{aside}</div>}
      </header>
      <div className={cn('min-h-0 flex-1', flush ? 'pt-3' : 'px-5 pb-5 pt-4')} style={{ minHeight }}>
        {loading ? (
          <div className={cn('space-y-3', flush && 'px-5 pb-5')} aria-busy="true">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : empty ? (
          <div className="flex h-full min-h-[160px] items-center justify-center px-5 text-sm text-muted-foreground">{emptyText}</div>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

const LABELS: Record<string, string> = {
  opportunity_id: 'Opportunity', order_id: 'Order', sales_order_id: 'Sales order', customer_id: 'Customer',
  customer_name: 'Customer', vendor_name: 'Vendor', vendor_id: 'Vendor', material_id: 'Material', sku: 'SKU',
  match_status: 'Match status', anomaly_score: 'Anomaly score', risk_score: 'Risk score', total_qty: 'Quantity',
  total_spend: 'Spend', total_open_ar: 'Open receivables', avg_oee: 'OEE', avg_clv: 'Lifetime value',
  avg_risk: 'Risk score', line_id: 'Line', plant_id: 'Plant', po_number: 'PO number', dso: 'DSO',
  created_at: 'Created', updated_at: 'Updated', action_type: 'Action', amount: 'Amount', qty: 'Quantity',
};

/** "total_open_ar" → "Open receivables"; unknown keys are sentence-cased. */
export function labelOf(key: unknown): string {
  const k = String(key ?? '');
  if (LABELS[k]) return LABELS[k];
  const s = k.replace(/[_-]+/g, ' ').trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

/** Compact number: 1,240 · 12.4K · 3.1M. */
export function compact(n: number, digits = 1): string {
  if (!Number.isFinite(n)) return '—';
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(digits) + 'B';
  if (a >= 1e6) return (n / 1e6).toFixed(digits) + 'M';
  if (a >= 1e4) return (n / 1e3).toFixed(digits) + 'K';
  if (a >= 100 || Number.isInteger(n)) return Math.round(n).toLocaleString('en-US');
  return a < 10 ? n.toFixed(2) : n.toFixed(1);
}

/** True when a value looks like a number (the query API returns strings). */
export const isNumeric = (v: unknown) => v !== null && v !== '' && v !== undefined && !Number.isNaN(Number(v)) && typeof v !== 'boolean';
