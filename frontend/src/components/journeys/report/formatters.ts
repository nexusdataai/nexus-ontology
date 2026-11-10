/**
 * Format codes -> display string. Mirrors the format vocabulary the
 * backend report-schema YAML files declare. ``null`` / ``undefined``
 * values render as "--" so the UI never shows literal "null".
 */

export function formatValue(value: number | string | null | undefined, format: string): string {
  if (value === null || value === undefined || value === '') return '--';
  const fmt = (format || 'integer').toLowerCase();
  switch (fmt) {
    case 'percent':
      return `${formatNumeric(value, 1)}%`;
    case 'integer':
      return formatNumeric(value, 0);
    case 'decimal':
      return formatNumeric(value, 2);
    case 'duration':
      return formatDuration(value);
    case 'currency':
      return formatCurrency(value);
    case 'text':
      return String(value);
    default:
      return String(value);
  }
}

function formatNumeric(value: number | string, decimals: number): string {
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  if (Math.abs(n) >= 10_000) {
    // Group large ints with thousands separators.
    return n.toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }
  return n.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatDuration(value: number | string): string {
  // Accept either seconds (number) or pre-formatted strings (e.g. "1m 5s").
  if (typeof value === 'string') {
    const asNum = Number(value);
    if (!Number.isFinite(asNum)) return value;
    return _secondsToHms(asNum);
  }
  return _secondsToHms(value);
}

function _secondsToHms(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0s';
  const s = Math.floor(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  if (m < 60) return `${m}m ${rem}s`;
  const h = Math.floor(m / 60);
  const mRem = m % 60;
  return `${h}h ${mRem}m`;
}

function formatCurrency(value: number | string): string {
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  // Compact notation for large amounts (1.2M, 3.4K) to keep cards readable.
  if (Math.abs(n) >= 1_000_000) {
    return `$${(n / 1_000_000).toFixed(2)}M`;
  }
  if (Math.abs(n) >= 1_000) {
    return `$${(n / 1_000).toFixed(1)}K`;
  }
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

// Status -> tailwind text colour class. Reused by KpiCard.
export function statusColorClass(status?: string | null): string {
  if (status === 'critical') return 'text-destructive';
  if (status === 'warn') return 'text-warning';
  if (status === 'ok') return 'text-success';
  return '';
}
