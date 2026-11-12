/**
 * Top-bar menu to open the other Nexus platforms (AI Engine, SRE, Simulator),
 * each with a dot showing whether it answers right now.
 */
import { Link } from 'react-router-dom';
import { Icon } from '@/components/ds/Icon';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { usePlatforms, type Reach } from '@/config/platforms';
import { cn } from '@/lib/utils';

const DOT: Record<Reach, string> = { up: 'bg-success', down: 'bg-destructive', checking: 'bg-subtle-foreground animate-pulse' };
const DOT_WORD: Record<Reach, string> = { up: 'online', down: 'not answering', checking: 'checking' };

export function PlatformSwitcher({ className }: { className?: string }) {
  const { platforms, reach } = usePlatforms(true);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Open another Nexus platform"
        title="Nexus platforms"
        className={cn('flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors duration-150 hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring', className)}
      >
        <Icon name="apps" className="h-[18px] w-[18px]" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="text-xs font-medium text-muted-foreground">Nexus platforms</DropdownMenuLabel>
        {platforms.map(p => {
          const r = reach[p.id] || 'checking';
          const self = p.id === 'ontology';
          const body = (
            <span className="flex w-full items-start gap-3">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-surface-2 text-foreground"><Icon name={p.icon} className="h-4 w-4" /></span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2 text-sm font-medium text-foreground">
                  {p.name}
                  <span className={cn('h-1.5 w-1.5 rounded-full', DOT[r])} aria-label={DOT_WORD[r]} title={DOT_WORD[r]} />
                </span>
                <span className="block truncate text-xs text-muted-foreground">{self ? 'You are here' : p.role}</span>
              </span>
              {!self && <Icon name="external-link" className="mt-1 h-3.5 w-3.5 shrink-0 text-subtle-foreground" />}
            </span>
          );
          return self ? (
            <DropdownMenuItem key={p.id} disabled className="opacity-100 data-[disabled]:opacity-100">{body}</DropdownMenuItem>
          ) : (
            <DropdownMenuItem key={p.id} asChild>
              <a href={p.url} target="_blank" rel="noopener noreferrer" className="cursor-pointer">{body}</a>
            </DropdownMenuItem>
          );
        })}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/operations/health?tab=platforms" className="cursor-pointer text-sm">
            <Icon name="network" className="mr-2 h-4 w-4" /> How they connect
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
