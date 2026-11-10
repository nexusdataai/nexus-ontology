/**
 * Detail of the selected pipeline step: what it does, the systems it touches,
 * live progress and its console. Presentational: the studio owns the state.
 */
import type { ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ds/Icon';
import { Meter, StatusPill } from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { systemsIn } from './format';
import type { StepStatus } from './StepPipeline';

interface StepDetailProps {
  index: number;
  total: number;
  name: string;
  description?: string;
  status: StepStatus;
  progress?: number;
  duration?: string;
  /** Item counter of the step that is running right now. */
  taskProgress?: { current: number; total: number } | null;
  logsCount: number;
  logsOpen: boolean;
  onToggleLogs: () => void;
  onOpenLogs: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  /** Hide the title row (the narrow layout already shows the name in the timeline). */
  compact?: boolean;
  /** The console, rendered by the studio. */
  children?: ReactNode;
}

export function StepDetail({
  index, total, name, description, status, progress = 0, duration, taskProgress,
  logsCount, logsOpen, onToggleLogs, onOpenLogs, onPrev, onNext, compact, children,
}: StepDetailProps) {
  const systems = systemsIn(`${name} ${description || ''}`);
  const running = status === 'running';
  const pct = Math.max(0, Math.min(100, Math.round(progress || 0)));

  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0 flex-1">
          {!compact && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="num text-xs text-muted-foreground">Step {index + 1} of {total}</span>
              <h3 className="text-md font-medium text-foreground">{name}</h3>
              <StatusPill status={status === 'pending' ? 'not started' : status} tone={status === 'pending' ? 'neutral' : undefined} />
            </div>
          )}
          {description && <p className={compact ? 'text-sm text-muted-foreground' : 'mt-1.5 max-w-3xl text-sm text-muted-foreground'}>{description}</p>}
          {systems.length > 0 && (
            <ul className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-foreground">
              <li className="text-xs text-muted-foreground">Systems</li>
              {systems.map(s => (
                <li key={s} className="inline-flex items-center gap-1.5">
                  <SystemLogo system={s} size="sm" /> {systemName(s)}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={onToggleLogs} aria-expanded={logsOpen}>
            <Icon name="terminal" /> {logsOpen ? 'Hide output' : 'Show output'}
            <span className="num text-xs text-muted-foreground">{logsCount}</span>
          </Button>
          <Button variant="ghost" size="sm" onClick={onOpenLogs}>
            <Icon name="expand" /> Full log
          </Button>
          {!compact && (onPrev || onNext) && (
            <span className="ml-1 hidden items-center sm:inline-flex">
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onPrev} disabled={!onPrev} aria-label="Previous step"><Icon name="chevron-left" /></Button>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onNext} disabled={!onNext} aria-label="Next step"><Icon name="chevron-right" /></Button>
            </span>
          )}
        </div>
      </div>

      {running && (
        <div className="mt-4 max-w-xl">
          <Meter value={pct} label={`${name} progress`} />
          <p className="num mt-1.5 text-xs text-muted-foreground">
            {pct}% done{taskProgress ? `, item ${taskProgress.current.toLocaleString()} of ${taskProgress.total.toLocaleString()}` : ''}
          </p>
        </div>
      )}
      {status === 'completed' && duration && <p className="num mt-3 text-xs text-muted-foreground">Completed in {duration}</p>}
      {status === 'failed' && <p className="mt-3 text-sm text-destructive">This step failed. Open the output to see the error.</p>}

      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}

export default StepDetail;
