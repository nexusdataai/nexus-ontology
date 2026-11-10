/**
 * Card for a saved dashboard or view in AI Analytics.
 * The thumbnail is a small wireframe drawn from the item's id, so every card
 * looks different and the same item always looks the same. It is a hint of
 * "a dashboard" or "a view with tabs", not a real screenshot.
 */
import * as React from 'react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Icon, type IconName } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';

function hash(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

type Tile = 'bars' | 'line' | 'donut' | 'stat' | 'table';
const ORDER: Tile[] = ['line', 'bars', 'donut', 'table', 'stat'];

function TileArt({ kind, seed }: { kind: Tile; seed: number }) {
  const r = (n: number) => ((seed >> (n * 3)) & 7) / 7;
  if (kind === 'bars') {
    return (
      <div className="flex h-full items-end gap-[3px]">
        {[0, 1, 2, 3, 4].map(i => <span key={i} className="flex-1 rounded-[2px] bg-primary" style={{ height: `${30 + r(i) * 65}%`, opacity: i === 3 ? 1 : 0.45 }} />)}
      </div>
    );
  }
  if (kind === 'line') {
    const pts = [0, 1, 2, 3, 4, 5].map(i => `${i * 20},${34 - (8 + r(i) * 22)}`).join(' ');
    return (
      <svg viewBox="0 0 100 36" preserveAspectRatio="none" className="h-full w-full text-primary dark:text-brand-hi">
        <polyline points={pts} fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      </svg>
    );
  }
  if (kind === 'donut') {
    return (
      <svg viewBox="0 0 36 36" className="mx-auto h-full text-primary dark:text-brand-hi">
        <circle cx="18" cy="18" r="12" fill="none" stroke="currentColor" strokeWidth="6" opacity="0.2" />
        <circle cx="18" cy="18" r="12" fill="none" stroke="currentColor" strokeWidth="6" pathLength={100} strokeDasharray={`${35 + r(1) * 40} 100`} transform="rotate(-90 18 18)" />
      </svg>
    );
  }
  if (kind === 'table') {
    return <div className="flex h-full flex-col justify-between py-0.5">{[0, 1, 2, 3].map(i => <span key={i} className="h-[3px] rounded-full bg-border-strong" style={{ width: `${55 + r(i) * 45}%` }} />)}</div>;
  }
  return (
    <div className="flex h-full flex-col justify-end gap-1">
      <span className="h-2 w-1/2 rounded-full bg-foreground/50" />
      <span className="h-[3px] w-full rounded-full bg-surface-3"><span className="block h-full rounded-full bg-primary" style={{ width: `${40 + r(2) * 50}%` }} /></span>
    </div>
  );
}

export function LibraryThumb({ id, kind, count }: { id: string; kind: 'dashboard' | 'view'; count: number }) {
  const seed = hash(id);
  const tiles = Math.max(2, Math.min(5, count || 3));
  const start = seed % ORDER.length;
  return (
    <div
      className="relative h-32 overflow-hidden border-b border-border bg-surface-2 p-3"
      style={{ backgroundImage: 'radial-gradient(hsl(var(--border-strong) / 0.45) 1px, transparent 1px)', backgroundSize: '14px 14px' }}
      aria-hidden="true"
    >
      {kind === 'view' && (
        <div className="mb-2 flex gap-1.5">
          {Array.from({ length: Math.max(2, Math.min(5, count || 2)) }).map((_, i) => (
            <span key={i} className={cn('h-1.5 rounded-full', i === 0 ? 'w-8 bg-primary' : 'w-6 bg-border-strong')} />
          ))}
        </div>
      )}
      <div className={cn('grid gap-1.5 transition-transform duration-500 ease-brand-out group-hover:scale-[1.03]', kind === 'view' ? 'h-[calc(100%-14px)] grid-cols-3' : 'h-full grid-cols-3 grid-rows-2')}>
        {Array.from({ length: kind === 'view' ? 3 : tiles }).map((_, i) => {
          const t = ORDER[(start + i) % ORDER.length];
          const wide = kind === 'dashboard' && i === 0;
          return (
            <div key={i} className={cn('min-h-0 rounded-md border border-border bg-card p-1.5 shadow-xs', wide && 'col-span-2', kind === 'dashboard' && tiles <= 3 && i === 0 && 'row-span-2')}>
              <TileArt kind={t} seed={seed >> i} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export interface LibraryAction { label: string; icon: IconName; onSelect: () => void; destructive?: boolean }

interface LibraryCardProps {
  id: string;
  kind: 'dashboard' | 'view';
  title: string;
  description?: string;
  /** Panels in a dashboard, tabs in a view. */
  count: number;
  updatedAt?: string | null;
  tags?: string[];
  onOpen: () => void;
  actions: LibraryAction[];
  index?: number;
}

const when = (iso?: string | null) => {
  if (!iso) return 'Not saved yet';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'Not saved yet';
  const days = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (days <= 0) return 'Updated today';
  if (days === 1) return 'Updated yesterday';
  if (days < 7) return `Updated ${days} days ago`;
  return `Updated ${d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}`;
};

export function LibraryCard({ id, kind, title, description, count, updatedAt, tags = [], onOpen, actions, index = 0 }: LibraryCardProps) {
  const unit = kind === 'dashboard' ? (count === 1 ? 'panel' : 'panels') : (count === 1 ? 'tab' : 'tabs');
  return (
    <article
      onClick={onOpen}
      style={{ ['--i' as any]: Math.min(index, 9) }}
      className="rise group flex cursor-pointer flex-col overflow-hidden rounded-xl border border-border bg-card shadow-xs transition-[border-color,box-shadow,transform] duration-300 ease-brand-out hover:-translate-y-0.5 hover:border-brand/50 hover:shadow-md"
    >
      <LibraryThumb id={id} kind={kind} count={count} />
      <div className="flex flex-1 flex-col p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="min-w-0 text-md font-medium text-foreground">
            <button type="button" onClick={(e) => { e.stopPropagation(); onOpen(); }} className="block max-w-full truncate rounded text-left underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{title}</button>
          </h3>
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <button type="button" aria-label={`Actions for ${title}`} className="-mr-1.5 -mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground opacity-60 transition-opacity hover:bg-accent hover:text-foreground focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring group-hover:opacity-100">
                <Icon name="more" className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
              {actions.map((a, i) => (
                <React.Fragment key={a.label}>
                  {a.destructive && i > 0 && <DropdownMenuSeparator />}
                  <DropdownMenuItem onClick={a.onSelect} className={a.destructive ? 'text-destructive focus:text-destructive' : undefined}>
                    <Icon name={a.icon} className="mr-2 h-3.5 w-3.5" /> {a.label}
                  </DropdownMenuItem>
                </React.Fragment>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <p className="mt-1 line-clamp-2 min-h-[2.5rem] text-sm text-muted-foreground">{description || (kind === 'dashboard' ? 'No description yet.' : 'A set of dashboards shown as tabs.')}</p>
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span><span className="num text-foreground">{count}</span> {unit}</span>
          <span aria-hidden="true">·</span>
          <span>{when(updatedAt)}</span>
          {tags.length > 0 && <span className="ml-auto truncate">{tags.slice(0, 3).join(', ')}</span>}
        </div>
      </div>
    </article>
  );
}

export default LibraryCard;
