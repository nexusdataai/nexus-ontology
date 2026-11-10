/**
 * Small formatting helpers shared by the Journey Studio pieces.
 * Presentational only.
 */

/** "Orders Processed" -> "Orders processed". Words with inner capitals (SKUs, POs, ESG) are kept. */
export function sentenceCase(label?: string | null): string {
  const words = String(label || '').trim().split(/\s+/).filter(Boolean);
  return words
    .map((w, i) => {
      if (/[A-Z]/.test(w.slice(1))) return w;
      return i === 0 ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : w.toLowerCase();
    })
    .join(' ');
}

/** "semantic-rag" -> "Semantic rag", "order_to_cash" -> "Order to cash". */
export function humanize(key?: string | null): string {
  const s = String(key || '').replace(/[_-]+/g, ' ').trim().replace(ACRONYMS, (w) => ACRONYM_CASE[w.toLowerCase()] || w.toUpperCase());
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}
/** Business abbreviations that must keep their capitals: "cpq buy" -> "CPQ buy". */
const ACRONYMS = /\b(cpq|esg|o2c|kpi|ar|ap|gl|sla|rfx|rag|erp|crm|sap|sku|dso|clv|api|vdl|fdw|etl|cdc|tpm|ai)\b/gi;
const ACRONYM_CASE: Record<string, string> = { rfx: 'RFx', o2c: 'O2C' };

/** Minutes -> "5 min", "6 h", "24 h". */
export function intervalInWords(minutes?: number | string | null): string {
  const m = Number(minutes);
  if (!Number.isFinite(m) || m <= 0) return '';
  if (m < 60) return `${m} min`;
  const h = m / 60;
  return Number.isInteger(h) ? `${h} h` : `${Math.floor(h)} h ${Math.round(m % 60)} min`;
}

export function timeOfDay(value?: string | number | Date | null): string {
  if (!value) return '';
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function dayAndTime(value?: string | number | Date | null): string {
  if (!value) return '';
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

/** A schedule row in words: "Every 24 h, next run 04:04". */
export function scheduleInWords(schedule?: any): string {
  if (!schedule) return 'No schedule';
  const every = intervalInWords(schedule.intervalMinutes ?? schedule.interval_minutes);
  if (schedule.enabled === false) return every ? `Schedule paused (every ${every})` : 'Schedule paused';
  const next = timeOfDay(schedule.nextRunAt ?? schedule.next_run_at);
  if (!every) return next ? `Scheduled, next run ${next}` : 'Scheduled';
  return next ? `Every ${every}, next run ${next}` : `Every ${every}`;
}

const KNOWN_SYSTEMS: { key: string; test: RegExp }[] = [
  { key: 'salesforce', test: /salesforce|\bsfdc\b|\bcrm\b/i },
  { key: 'sap', test: /\bsap\b/i },
  { key: 'oracle', test: /oracle/i },
  { key: 'google_drive', test: /google drive|\bgdrive\b/i },
  { key: 'slack', test: /\bslack\b/i },
  { key: 'mysql', test: /mysql/i },
];

/** Source systems named in a step's text, as SystemLogo keys. */
export function systemsIn(text?: string | null): string[] {
  const t = String(text || '');
  return KNOWN_SYSTEMS.filter(s => s.test.test(t)).map(s => s.key);
}

/** Seconds -> "45s", "1m 12s", "2h 5m". */
export function secondsInWords(seconds?: number | null): string {
  const n = Number(seconds);
  if (!Number.isFinite(n) || n < 0) return '';
  const s = Math.round(n);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

/** Run number from a job id like "JOB-0012"; falls back to the given number. */
export function runNumber(jobId: string | undefined, fallback: number): number {
  const m = String(jobId || '').match(/JOB-(\d+)/);
  return m ? parseInt(m[1], 10) : fallback;
}
