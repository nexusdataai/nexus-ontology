import { cn } from '@/lib/utils';
import type { StatTile, StatTone } from './types';

interface StatsTilesProps {
  tiles: StatTile[];
}

const TONE_DOT: Record<StatTone, string> = {
  ok: 'bg-success',
  warn: 'bg-warning',
  err: 'bg-destructive',
  muted: 'bg-border-strong',
};

const TONE_TEXT: Record<StatTone, string> = {
  ok: 'text-success',
  warn: 'text-warning',
  err: 'text-destructive',
  muted: 'text-muted-foreground',
};

/**
 * Top-of-panel summary tiles. The parent panel computes the tiles from
 * the live registry response; this component is purely presentational.
 *
 * Tile count is expected to be ~4-6; the grid wraps responsively at
 * common breakpoints so the panel still looks balanced on narrower
 * viewports.
 */
export function StatsTiles({ tiles }: StatsTilesProps) {
  if (!tiles.length) return null;
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border bg-border md:grid-cols-3 xl:grid-cols-6">
      {tiles.map((t) => {
        const tone = t.tone || 'muted';
        return (
          <div key={t.title} className="min-w-0 bg-card p-3.5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', TONE_DOT[tone])} aria-hidden="true" />
              <span className="truncate">{t.title}</span>
            </div>
            <div className="num mt-1 text-xl font-medium leading-7 text-foreground">{t.value}</div>
            {t.hint && <div className="text-xs text-muted-foreground">{t.hint}</div>}
            {t.breakdown && t.breakdown.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-x-2.5 gap-y-0.5 text-xs">
                {t.breakdown.map((b) => (
                  <span key={b.label} className="inline-flex items-baseline gap-1" title={`${b.label}: ${b.value}`}>
                    <span className={cn('num font-medium', TONE_TEXT[b.tone || 'muted'])}>{b.value}</span>
                    <span className="text-muted-foreground">{b.label}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default StatsTiles;
