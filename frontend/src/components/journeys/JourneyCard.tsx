/**
 * JourneyCard Component
 *
 * One journey as a row of the journeys list: name and what it does, a one-hue
 * stage progress strip, how its runs went, its status and when it last moved,
 * and Open. The whole row opens the Journey Studio.
 *
 * Requirements: 2.5, 2.6
 */

import { CallProcessingJourney } from '../../types/callProcessingJourney';
import { formatRelativeTime } from '../../utils/journeyUtils';
import { Icon } from '@/components/ds/Icon';
import { StatusPill } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { humanize } from './studio/format';

export interface JourneyCardProps {
  journey: CallProcessingJourney;
  onViewStudio: (journeyId: string) => void;
  onDelete: (journeyId: string) => void;
  isActionLoading?: boolean;
  /** Position in the list, for the staggered entrance. */
  index?: number;
}

function typeLabel(journey: CallProcessingJourney): string {
  const name = journey.name?.toLowerCase() || '';
  if (name.includes('semantic') || name.includes('rag')) return 'semantic-rag';
  if ((journey as any).odaComponentType === 'data-pipeline' || name.includes('etl')) return 'etl-pipeline';
  return String(journey.type || 'journey');
}

const TYPE_NAME: Record<string, string> = {
  'semantic-rag': 'Knowledge pipeline',
  'etl-pipeline': 'Data pipeline',
  'call-processing': 'Journey',
  'operation-management': 'Operations',
};

/** Shared column template so the header of the list lines up with the rows. */
export const JOURNEY_ROW_GRID = 'lg:grid lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_minmax(0,0.9fr)_150px_88px] lg:items-center lg:gap-6';

export function JourneyCard({
  journey,
  onViewStudio,
  onDelete,
  isActionLoading = false,
  index = 0,
}: JourneyCardProps) {
  const m = journey.metrics || ({} as CallProcessingJourney['metrics']);
  const total = m.totalJobs || 0;
  const done = m.completedJobs || 0;
  const running = m.runningJobs || 0;
  const failed = m.failedJobs || 0;
  const isRunning = journey.status === 'running';
  // Can delete if journey is not running
  const canDelete = journey.status !== 'running';
  const successRate = total > 0 ? Math.round((done * 100) / Math.max(done + failed, 1)) : 0;
  const avgSeconds = m.averageJobDuration > 0 ? Math.round(m.averageJobDuration / 1000) : 0;
  const id = String(journey.id || '');

  const stages = journey.stages || [];
  const currentStage = stages[Math.min(journey.currentStageIndex || 0, Math.max(stages.length - 1, 0))];
  const any = journey as any;
  const solution = journey.solutionId ? humanize(journey.solutionId) : '';
  const kind = typeLabel(journey);
  // The backend stores every journey with the default call-processing text
  // and stage list, even when it is a solution journey. Do not show those as
  // if they described this journey.
  const LEGACY_TEXT = /^(call processing journey|fetch tasks from webex)/i;
  const clean = (t?: string) => (t && !LEGACY_TEXT.test(t.trim()) ? t : '');
  const legacyStages = LEGACY_TEXT.test(String(stages[0]?.description || '')) && !/call|webex/i.test(String(journey.name || ''));
  const about = clean(any.description) || (legacyStages ? '' : clean(currentStage?.description)) || (solution ? `Automation for ${solution}` : '') || (/journey/i.test(TYPE_NAME[kind] || kind) ? 'Automation journey' : `${TYPE_NAME[kind] || humanize(kind)} journey`);
  // A journey that has finished runs is not "not run yet", whatever its stored status says.
  const idle = journey.status === 'created' || (journey.status as string) === 'pending';
  const shownStatus: string = idle && total > 0 ? (running > 0 ? 'running' : done > 0 ? 'completed' : failed > 0 ? 'failed' : journey.status) : journey.status;
  const statusPill = <StatusPill status={shownStatus === 'created' || shownStatus === 'pending' ? 'not run yet' : shownStatus} tone={shownStatus === 'created' || shownStatus === 'pending' ? 'neutral' : undefined} />;
  const useRuns = legacyStages || stages.length <= 1;
  const runsPct = total > 0 ? Math.round(((done + failed) * 100) / total) : 0;
  const lastMoved = journey.completedAt || journey.startedAt || any.updatedAt || journey.createdAt;
  const overall = useRuns && total > 0 ? runsPct : Math.max(0, Math.min(100, Math.round(journey.overallProgress || 0)));
  const nextRun = any.nextRunAt || any.next_run_at;

  return (
    <article
      onClick={() => onViewStudio(journey.id)}
      style={{ ['--i' as any]: index }}
      className={cn(
        'rise group relative cursor-pointer px-4 py-4 transition-colors duration-150 hover:bg-surface-2/60 sm:px-5',
        JOURNEY_ROW_GRID,
      )}
      data-testid="journey-card"
    >
      {/* Name and what it does */}
      <div className="min-w-0">
        <div className="flex items-start justify-between gap-3 lg:block">
          <h3 className="truncate text-md font-medium text-foreground" data-testid="journey-name">{journey.name}</h3>
          <span className="shrink-0 lg:hidden">{statusPill}</span>
        </div>
        <p className="mt-0.5 line-clamp-1 text-sm text-muted-foreground">{about}</p>
        <p className="mt-1 flex items-center gap-2 text-xs text-subtle-foreground">
          <span data-testid="journey-type" data-type={kind}>{TYPE_NAME[kind] || humanize(kind)}</span>
          <span className="mono-id truncate" data-testid="journey-id" title={id}>{id.length > 12 ? `${id.slice(0, 8)}…` : id}</span>
        </p>
      </div>

      {/* Stage progress: one segment per stage, one hue */}
      <div className="mt-3 min-w-0 lg:mt-0">
        <div className="flex h-1.5 gap-0.5" role="img" aria-label={`${overall}% done`}>
          {!useRuns ? stages.map((s, i) => (
            <span key={s.id || i} className="h-full flex-1 overflow-hidden rounded-full bg-surface-3">
              <span
                className={cn(
                  'grow-x block h-full rounded-full',
                  s.status === 'completed' && 'bg-primary',
                  s.status === 'running' && 'bg-primary/60',
                  s.status === 'failed' && 'bg-destructive',
                  s.status === 'pending' && 'bg-transparent',
                )}
                style={{ width: s.status === 'running' ? `${Math.max(12, Math.min(100, s.progress || 0))}%` : '100%', ['--i' as any]: i }}
              />
            </span>
          )) : (
            <span className="h-full flex-1 overflow-hidden rounded-full bg-surface-3">
              <span className={cn('grow-x block h-full rounded-full', shownStatus === 'failed' ? 'bg-destructive' : 'bg-primary')} style={{ width: `${overall}%` }} />
            </span>
          )}
        </div>
        <p className="mt-1.5 flex items-center gap-1.5 truncate text-xs text-muted-foreground">
          {isRunning && <span className="dot-live shrink-0 text-primary dark:text-brand-hi" aria-hidden="true" />}
          <span className="truncate">
            {!useRuns
              ? `Stage ${Math.min((journey.currentStageIndex || 0) + 1, stages.length)} of ${stages.length}${currentStage?.name ? `: ${currentStage.name}` : ''}`
              : total > 0 ? `${(done + failed).toLocaleString()} of ${total.toLocaleString()} ${total === 1 ? 'run' : 'runs'} finished` : 'Ready to run'}
          </span>
          <span className="num shrink-0">{overall}%</span>
        </p>
      </div>

      {/* Runs */}
      <div className="mt-3 min-w-0 text-sm lg:mt-0">
        {total === 0 ? (
          <span className="text-muted-foreground">No runs yet</span>
        ) : (
          <>
            <p className="text-foreground">
              <span className="num font-medium">{successRate}%</span> <span className="text-muted-foreground">of <span className="num">{total.toLocaleString()}</span> {total === 1 ? 'run' : 'runs'} succeeded</span>
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {running > 0 && <span className="num text-primary dark:text-brand-hi">{running} running</span>}
              {running > 0 && (failed > 0 || avgSeconds > 0) ? ', ' : ''}
              {failed > 0 && <span className="num text-destructive">{failed} failed</span>}
              {failed > 0 && avgSeconds > 0 ? ', ' : ''}
              {avgSeconds > 0 && <span className="num">about {avgSeconds >= 60 ? `${Math.floor(avgSeconds / 60)}m ${avgSeconds % 60}s` : `${avgSeconds}s`} each</span>}
            </p>
          </>
        )}
      </div>

      {/* Status and time */}
      <div className="mt-3 min-w-0 lg:mt-0">
        <span className="hidden lg:block" data-testid="journey-status">
          {statusPill}
        </span>
        <p className="text-xs text-muted-foreground lg:mt-0.5">
          <span data-testid="journey-created-at">{formatRelativeTime(lastMoved)}</span>
          {nextRun ? `, next ${new Date(nextRun).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}
        </p>
      </div>

      {/* Actions */}
      <div className="mt-3 flex items-center justify-end gap-1 lg:mt-0">
        {canDelete && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onDelete(journey.id); }}
            disabled={isActionLoading}
            aria-label={`Delete ${journey.name}`}
            className="flex h-8 w-8 items-center justify-center rounded-md text-subtle-foreground transition-[opacity,color,background-color] hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 lg:opacity-0 lg:group-hover:opacity-100"
            data-testid="action-delete-button"
          >
            <Icon name={isActionLoading ? 'spinner' : 'trash'} className={cn('h-3.5 w-3.5', isActionLoading && 'animate-spin')} />
          </button>
        )}
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onViewStudio(journey.id); }}
          className="inline-flex h-8 items-center gap-1 rounded-md px-2 text-sm font-medium text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          data-testid="view-studio-button"
        >
          Open <Icon name="arrow-right" className="h-3.5 w-3.5 transition-transform duration-300 ease-brand-out group-hover:translate-x-0.5" />
        </button>
      </div>
    </article>
  );
}

export default JourneyCard;
