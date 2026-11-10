/**
 * Small shared helpers for the tool screens of the Reasoning area
 * (catalogue, registry, builder): plain labels for risk levels and the
 * source system a connector API belongs to.
 */
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { StatusPill } from '@/components/ds/kit';
import { cn } from '@/lib/utils';

const RISK_LABEL: Record<string, string> = {
  read_only: 'Read only',
  low_risk_write: 'Low-risk write',
  high_risk_write: 'High-risk write',
};

export const riskLabel = (risk?: string | null) => RISK_LABEL[String(risk || '')] || String(risk || 'Unknown').replace(/_/g, ' ');

/** Risk of a tool as a status: green reads, amber and red writes. */
export function RiskPill({ risk, variant, className }: { risk?: string | null; variant?: 'dot' | 'soft'; className?: string }) {
  return <StatusPill status={risk} variant={variant} className={className}>{riskLabel(risk)}</StatusPill>;
}

/** "sfdc.account.get" → "sfdc"; "external.gdrive.contract.get" → "gdrive". */
export function systemOfApi(api?: string | null): string | null {
  if (!api) return null;
  const parts = api.split('.');
  return parts[0] === 'external' && parts[1] ? parts[1] : parts[0];
}

/** Logo and name of the system a tool reaches, or a quiet "Nexus only". */
export function ToolSystem({ api, className }: { api?: string | null; className?: string }) {
  const system = systemOfApi(api);
  if (!system) return <span className={cn('text-sm text-muted-foreground', className)}>Nexus only</span>;
  return (
    <span className={cn('inline-flex min-w-0 items-center gap-2 text-sm text-foreground', className)}>
      <SystemLogo system={system} size="xs" />
      <span className="truncate">{systemName(system)}</span>
    </span>
  );
}

/** ISO timestamp → "12 Nov 2026, 14:05". Falls back to the raw value. */
export function formatWhen(iso?: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
