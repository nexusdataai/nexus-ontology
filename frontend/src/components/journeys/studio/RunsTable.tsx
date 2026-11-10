/**
 * Recent runs of a journey as a compact table. Clicking a row shows that run
 * in the pipeline above. Columns that are zero for every run are left out.
 */
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { StatusPill, TableShell } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { dayAndTime, runNumber } from './format';

interface RunsTableProps {
  jobs: any[];
  steps: { id: string; name: string }[];
  selectedJobId: string | null;
  onSelect: (jobId: string) => void;
  onCancel: (jobId: string) => void;
  limit?: number;
}

/** The numbers the studio shows for one run, whatever spelling the backend used. */
export function runFigures(job: any) {
  const m = job?.metrics || {};
  return {
    read: m.availableCalls ?? m.itemsTotal ?? job?.itemsTotal ?? 0,
    skipped: m.skippedTasks ?? 0,
    processed: m.newTasks ?? 0,
    succeeded: m.successfulProcessing ?? m.itemsProcessed ?? job?.itemsProcessed ?? 0,
    failed: m.failedProcessing ?? 0,
    noData: m.noRecording ?? 0,
  };
}

/** Time per step of one run, in pipeline order. */
export function stepTimes(job: any, steps: { id: string; name: string }[]) {
  const results = job?.stepResults || job?.step_results || {};
  return steps
    .map(s => {
      const r = results[s.id];
      if (!r) return null;
      const seconds = typeof r.durationSeconds === 'number' ? r.durationSeconds : null;
      const label = r.durationFormatted || (seconds != null ? `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s` : null);
      if (!label) return null;
      return { id: s.id, name: s.name, label, seconds, status: String(r.status || '') };
    })
    .filter(Boolean) as { id: string; name: string; label: string; seconds: number | null; status: string }[];
}

const n = (v: number) => Number(v || 0).toLocaleString();

export function RunsTable({ jobs, steps, selectedJobId, onSelect, onCancel, limit = 10 }: RunsTableProps) {
  const rows = jobs.slice(0, limit).map(job => ({ job, f: runFigures(job) }));
  const showSkipped = rows.some(r => r.f.skipped > 0);
  const showNoData = rows.some(r => r.f.noData > 0);

  return (
    <TooltipProvider delayDuration={200}>
      <TableShell>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Run</TableHead>
              <TableHead className="text-right">Read</TableHead>
              {showSkipped && <TableHead className="text-right">Skipped</TableHead>}
              <TableHead className="text-right">Processed</TableHead>
              <TableHead className="text-right">Succeeded</TableHead>
              <TableHead className="text-right">Failed</TableHead>
              {showNoData && <TableHead className="text-right">No data</TableHead>}
              <TableHead>Duration</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-px" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map(({ job, f }, index) => {
              const jobId = job.id || job.jobId;
              const selected = selectedJobId === jobId;
              const running = job.status === 'running' || job.status === 'in_progress';
              const times = stepTimes(job, steps);
              const duration = job.duration;
              return (
                <TableRow
                  key={jobId}
                  onClick={() => onSelect(jobId)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(jobId); } }}
                  tabIndex={0}
                  aria-selected={selected}
                  className={cn('rise cursor-pointer focus-visible:bg-accent/60 focus-visible:outline-none', selected && 'bg-accent hover:bg-accent')}
                  style={{ ['--i' as any]: index }}
                >
                  <TableCell>
                    <div className="flex items-baseline gap-2">
                      <span className={cn('num text-sm text-foreground', selected && 'font-medium')}>#{runNumber(jobId, jobs.length - index)}</span>
                      {index === 0 && <span className="text-xs text-primary dark:text-brand-hi">Latest</span>}
                    </div>
                    <div className="num text-xs text-muted-foreground">{dayAndTime(job.startedAt ?? job.startTime) || 'Not started'}</div>
                  </TableCell>
                  <TableCell className="num text-right">{n(f.read)}</TableCell>
                  {showSkipped && <TableCell className="num text-right text-muted-foreground">{n(f.skipped)}</TableCell>}
                  <TableCell className="num text-right">{n(f.processed)}</TableCell>
                  <TableCell className="num text-right">{n(f.succeeded)}</TableCell>
                  <TableCell className={cn('num text-right', f.failed > 0 ? 'font-medium text-destructive' : 'text-muted-foreground')}>{n(f.failed)}</TableCell>
                  {showNoData && <TableCell className="num text-right text-muted-foreground">{n(f.noData)}</TableCell>}
                  <TableCell className="num whitespace-nowrap">
                    {duration ? (
                      times.length > 0 ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="cursor-default underline decoration-border-strong decoration-dotted underline-offset-4">{duration}</span>
                          </TooltipTrigger>
                          <TooltipContent side="left" className="min-w-[200px]">
                            <p className="mb-1 text-xs font-medium">Time by step</p>
                            {times.map(t => (
                              <div key={t.id} className="flex justify-between gap-4 py-0.5 text-xs">
                                <span className="opacity-80">{t.name}</span>
                                <span className="num">{t.label}</span>
                              </div>
                            ))}
                          </TooltipContent>
                        </Tooltip>
                      ) : duration
                    ) : <span className="text-muted-foreground">{running ? 'Running' : 'Not recorded'}</span>}
                  </TableCell>
                  <TableCell><StatusPill status={job.status} /></TableCell>
                  <TableCell className="text-right">
                    {running && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-destructive hover:bg-destructive/10 hover:text-destructive"
                        onClick={(e) => { e.stopPropagation(); onCancel(jobId); }}
                      >
                        Stop
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableShell>
    </TooltipProvider>
  );
}

export default RunsTable;
