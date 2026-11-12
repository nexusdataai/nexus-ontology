/**
 * Health > Connected platforms: the four Nexus platforms, whether each one
 * answers, and how it works with the ontology.
 */
import { Icon } from '@/components/ds/Icon';
import { StatusPill } from '@/components/ds/kit';
import { Button } from '@/components/ui/button';
import { usePlatforms, RELATION_LABEL, type Relation, type Reach } from '@/config/platforms';
import { cn } from '@/lib/utils';

const TONE: Record<Relation, 'success' | 'warning' | 'neutral' | 'info'> = { self: 'info', connected: 'success', 'not-connected': 'warning', separate: 'neutral' };
const REACH_WORD: Record<Reach, string> = { up: 'Online', down: 'Not answering', checking: 'Checking…' };

export function ConnectedPlatforms() {
  const { platforms, reach } = usePlatforms(true);
  return (
    <div className="page-end mx-auto w-full max-w-[1400px] space-y-6">
      <header>
        <h2 className="text-xl font-medium tracking-tight text-foreground">Connected platforms</h2>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          The four Nexus platforms run side by side on the same cluster. This is how each one works with the ontology, and whether it answers right now.
        </p>
      </header>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {platforms.map((p, i) => {
          const r = reach[p.id] || 'checking';
          return (
            <section key={p.id} className="rise flex flex-col rounded-xl border border-border bg-card p-5 shadow-xs" style={{ ['--i' as string]: i } as React.CSSProperties}>
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-foreground"><Icon name={p.icon} className="h-5 w-5" /></span>
                <div className="min-w-0 flex-1">
                  <h3 className="text-md font-medium text-foreground">{p.name}</h3>
                  <p className="text-sm text-muted-foreground">{p.role}</p>
                </div>
                <StatusPill tone={TONE[p.relation]}>{RELATION_LABEL[p.relation]}</StatusPill>
              </div>
              <p className="mt-4 flex-1 text-sm text-foreground">{p.link}</p>
              <div className="mt-4 flex items-center justify-between gap-3 border-t border-border pt-3">
                <span className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
                  <span className={cn('h-2 w-2 shrink-0 rounded-full', r === 'up' ? 'bg-success' : r === 'down' ? 'bg-destructive' : 'animate-pulse bg-subtle-foreground')} aria-hidden="true" />
                  {REACH_WORD[r]} · <span className="truncate font-mono">{p.url.replace(/^https?:\/\//, '')}</span>
                </span>
                {p.id !== 'ontology' && (
                  <Button variant="outline" size="sm" asChild>
                    <a href={p.url} target="_blank" rel="noopener noreferrer">Open <Icon name="external-link" className="h-3.5 w-3.5" /></a>
                  </Button>
                )}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
