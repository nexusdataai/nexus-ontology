import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle2, XCircle, AlertTriangle, ChevronDown, ChevronRight,
} from 'lucide-react';

/**
 * Status pill config used across every diagnostics panel.
 *
 * The existing per-solution panels (O2CDiagnosticsPanel etc.) still inline
 * their own copy of this map; we keep this module additive so the new
 * Dashboard Diagnostics panel can consume it without touching the 9
 * existing panels. A future refactor can switch the others to import here.
 */
export const STATUS_BADGE: Record<string, { cls: string; icon: React.ElementType; label: string }> = {
  pass: { cls: 'bg-green-500/20 text-green-300 border-green-500/30', icon: CheckCircle2, label: 'Pass' },
  ok: { cls: 'bg-green-500/20 text-green-300 border-green-500/30', icon: CheckCircle2, label: 'OK' },
  healthy: { cls: 'bg-green-500/20 text-green-300 border-green-500/30', icon: CheckCircle2, label: 'Healthy' },
  warn: { cls: 'bg-amber-500/20 text-amber-300 border-amber-500/30', icon: AlertTriangle, label: 'Warning' },
  degraded: { cls: 'bg-amber-500/20 text-amber-300 border-amber-500/30', icon: AlertTriangle, label: 'Degraded' },
  fail: { cls: 'bg-red-500/20 text-red-300 border-red-500/30', icon: XCircle, label: 'Fail' },
  unhealthy: { cls: 'bg-red-500/20 text-red-300 border-red-500/30', icon: XCircle, label: 'Unhealthy' },
  no_data: { cls: 'bg-red-500/20 text-red-300 border-red-500/30', icon: XCircle, label: 'No Data' },
  missing: { cls: 'bg-red-500/20 text-red-300 border-red-500/30', icon: XCircle, label: 'Missing' },
  inactive: { cls: 'bg-amber-500/20 text-amber-300 border-amber-500/30', icon: AlertTriangle, label: 'Inactive' },
  error: { cls: 'bg-red-500/20 text-red-300 border-red-500/30', icon: XCircle, label: 'Error' },
};

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const cfg = STATUS_BADGE[status] || STATUS_BADGE.fail;
  const Icon = cfg.icon;
  return (
    <Badge variant="outline" className={`${cfg.cls} gap-1`}>
      <Icon className="h-3 w-3" /> {label ?? cfg.label}
    </Badge>
  );
}

export function Section({
  title,
  icon: Icon,
  status,
  defaultOpen,
  children,
  rightSlot,
}: {
  title: string;
  icon: React.ElementType;
  status: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  rightSlot?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen ?? true);
  return (
    <Card>
      <CardHeader className="pb-2 cursor-pointer" onClick={() => setOpen(!open)}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            <Icon className="h-4 w-4" /> {title}
          </CardTitle>
          <div className="flex items-center gap-2">
            {rightSlot}
            <StatusBadge status={status} />
          </div>
        </div>
      </CardHeader>
      {open && <CardContent>{children}</CardContent>}
    </Card>
  );
}

export function formatLatency(ms?: number | null): string {
  if (ms == null) return '-';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}
