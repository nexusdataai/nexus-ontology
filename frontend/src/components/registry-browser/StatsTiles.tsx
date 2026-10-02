import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import type { StatTile, StatTone } from './types';

interface StatsTilesProps {
  tiles: StatTile[];
}

const TONE_BG: Record<StatTone, string> = {
  ok: 'bg-green-500/10 text-green-300 border-green-500/30',
  warn: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  err: 'bg-red-500/10 text-red-300 border-red-500/30',
  muted: 'bg-muted/40 text-muted-foreground border-border/60',
};

const TONE_CHIP: Record<StatTone, string> = {
  ok: 'bg-green-500/15 text-green-300',
  warn: 'bg-amber-500/15 text-amber-300',
  err: 'bg-red-500/15 text-red-300',
  muted: 'bg-muted/40 text-muted-foreground',
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
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
      {tiles.map((t) => {
        const tone = t.tone || 'muted';
        return (
          <Card key={t.title} className={cn('border', TONE_BG[tone])}>
            <CardContent className="p-3 space-y-1">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{t.title}</div>
              <div className="text-xl font-semibold leading-none">{t.value}</div>
              {t.hint && (
                <div className="text-[10px] text-muted-foreground">{t.hint}</div>
              )}
              {t.breakdown && t.breakdown.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-1">
                  {t.breakdown.map((b) => (
                    <span
                      key={b.label}
                      className={cn(
                        'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px]',
                        TONE_CHIP[b.tone || 'muted'],
                      )}
                      title={`${b.label}: ${b.value}`}
                    >
                      <span className="font-mono font-medium">{b.value}</span>
                      <span className="opacity-80">{b.label}</span>
                    </span>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

export default StatsTiles;
