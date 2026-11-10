/**
 * JourneyReportModal -- schema-driven journey report surface.
 *
 * Fetches the envelope from ``GET /api/v1/journeys/{id}/aggregate-report``
 * and renders the sections the backend's report-schema YAML declared. The
 * modal has NO per-solution logic; section ``kind`` -> renderer is the only
 * dispatch (see ``ReportSections.tsx``).
 *
 * Opens from its own trigger, or is controlled by the parent through
 * ``open`` / ``onOpenChange`` (then no trigger is rendered).
 *
 * The legacy ``StageReportModal`` is preserved as a thin re-export
 * wrapper for any callers that haven't been migrated.
 */

import { useEffect, useState } from 'react';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { InlineError } from '@/components/ds/kit';
import { callProcessingJourneyService } from '@/services/callProcessingJourneyService';
import type { JourneyReport } from '@/types/callProcessingJourney';
import { KpiStrip, renderReportSection } from './ReportSections';

interface JourneyReportModalProps {
  journeyId: string;
  journeyName?: string;
  trigger?: React.ReactNode;
  /** Controlled mode: the parent owns the open state and no trigger is rendered. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function JourneyReportModal({ journeyId, journeyName, trigger, open: controlledOpen, onOpenChange }: JourneyReportModalProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const controlled = controlledOpen !== undefined;
  const open = controlled ? !!controlledOpen : internalOpen;
  const setOpen = (next: boolean) => {
    if (controlled) onOpenChange?.(next);
    else setInternalOpen(next);
  };
  const [report, setReport] = useState<JourneyReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await callProcessingJourneyService.getAggregateReport(journeyId);
      if (resp.success && resp.data) {
        setReport(resp.data as unknown as JourneyReport);
      } else {
        setError(resp.error?.message || 'Failed to load report');
      }
    } catch (e: any) {
      setError(e?.message || 'Unexpected error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open && !report && !loading) {
      loadReport();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleExport = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.solution_id || 'journey'}-report-${journeyId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const name = journeyName || report?.journey_title;
  const sections = report?.sections || [];
  const kpis = report?.summary_kpis || [];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {!controlled && (
        <DialogTrigger asChild>
          {trigger || (
            <Button variant="outline">
              <Icon name="document" /> View report
            </Button>
          )}
        </DialogTrigger>
      )}
      <DialogContent className="flex max-h-[88dvh] max-w-4xl flex-col gap-0 p-0">
        <DialogHeader className="border-b border-border px-5 pb-4 pt-5 pr-12 text-left sm:px-7">
          <DialogTitle className="text-xl font-medium tracking-tight">{report?.title || 'Journey report'}</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            {name ? `${name}. ` : ''}
            {report?.generated_at
              ? `Based on ${report.total_jobs} ${report.total_jobs === 1 ? 'run' : 'runs'}, generated ${new Date(report.generated_at).toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}.`
              : 'Results across the runs of this journey.'}
          </DialogDescription>
        </DialogHeader>

        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-6 sm:px-7">
          {loading && (
            <div className="space-y-6" aria-label="Loading report">
              <Skeleton className="h-24 w-full rounded-xl" />
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-32 w-full rounded-xl" />
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-24 w-full rounded-xl" />
            </div>
          )}

          {!loading && error && <InlineError onRetry={loadReport}>The report could not be loaded. {error}</InlineError>}

          {!loading && !error && report && (
            <div className="space-y-7">
              <KpiStrip kpis={kpis} />
              {sections.map(renderReportSection)}
              {sections.length === 0 && kpis.length === 0 && (
                <EmptyState icon="document" title="Nothing to report yet" description="This journey type has no report sections, or it has not completed a run." />
              )}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-5 py-3 sm:px-7">
          <Button variant="ghost" size="sm" onClick={loadReport} disabled={loading}>
            <Icon name={loading ? 'spinner' : 'refresh'} className={loading ? 'animate-spin' : undefined} /> Refresh
          </Button>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleExport} disabled={!report}>
              <Icon name="download" /> Export JSON
            </Button>
            <Button size="sm" onClick={() => setOpen(false)}>Close</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default JourneyReportModal;
