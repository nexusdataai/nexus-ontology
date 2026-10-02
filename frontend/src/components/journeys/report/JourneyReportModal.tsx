/**
 * JourneyReportModal -- schema-driven journey report surface.
 *
 * Replaces the legacy ``StageReportModal`` (which hard-coded the call-
 * processing layout for every journey). Fetches the new envelope from
 * ``GET /api/v1/journeys/{id}/aggregate-report`` and renders the
 * sections the backend's report-schema YAML declared. The modal has
 * NO per-solution logic; section ``kind`` -> renderer component is the
 * only dispatch.
 *
 * The legacy ``StageReportModal`` is preserved as a thin re-export
 * wrapper for any callers that haven't been migrated.
 */

import { useEffect, useState } from 'react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, Download, FileText } from 'lucide-react';
import { callProcessingJourneyService } from '@/services/callProcessingJourneyService';
import type { JourneyReport, ReportSection } from '@/types/callProcessingJourney';
import { SummaryStrip } from './SummaryStrip';
import { KpiGridSection } from './sections/KpiGridSection';
import { TableSection } from './sections/TableSection';
import { DistributionSection } from './sections/DistributionSection';
import { AlertsListSection } from './sections/AlertsListSection';
import { TimelineSection } from './sections/TimelineSection';
import { StepBreakdownSection } from './sections/StepBreakdownSection';
import { getIcon } from './iconMap';

interface JourneyReportModalProps {
  journeyId: string;
  journeyName?: string;
  trigger?: React.ReactNode;
}

function renderSection(section: ReportSection): React.ReactNode {
  switch (section.kind) {
    case 'kpi_grid':
      return <KpiGridSection key={section.id} section={section as any} />;
    case 'table':
      return <TableSection key={section.id} section={section as any} />;
    case 'distribution':
      return <DistributionSection key={section.id} section={section as any} />;
    case 'alerts_list':
      return <AlertsListSection key={section.id} section={section as any} />;
    case 'timeline':
      return <TimelineSection key={section.id} section={section as any} />;
    case 'step_breakdown':
      return <StepBreakdownSection key={section.id} section={section as any} />;
    default:
      return null;
  }
}

export function JourneyReportModal({ journeyId, journeyName, trigger }: JourneyReportModalProps) {
  const [open, setOpen] = useState(false);
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

  const TitleIcon = getIcon(report?.icon);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            View Report
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-5xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TitleIcon className="h-5 w-5" />
            {report?.title || 'Journey Report'}
            {(journeyName || report?.journey_title) && (
              <span className="text-muted-foreground font-normal">
                {' - '}{journeyName || report?.journey_title}
              </span>
            )}
          </DialogTitle>
          {report?.generated_at && (
            <div className="text-[11px] text-muted-foreground">
              Generated: {new Date(report.generated_at).toLocaleString()}
              {' | '}
              Based on {report.total_jobs} job{report.total_jobs === 1 ? '' : 's'}
              {report.solution_id && (
                <Badge variant="outline" className="ml-2 text-[9px]">
                  {report.solution_id}
                </Badge>
              )}
            </div>
          )}
        </DialogHeader>

        {loading && (
          <div className="py-10 flex items-center justify-center text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading report...
          </div>
        )}

        {error && (
          <div className="py-6 text-center text-sm text-red-500">{error}</div>
        )}

        {!loading && !error && report && (
          <div className="space-y-4 p-1">
            <SummaryStrip kpis={report.summary_kpis || []} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {(report.sections || []).map(renderSection)}
            </div>
            {(!report.sections || report.sections.length === 0) && (
              <div className="text-xs text-muted-foreground italic text-center py-4">
                No sections defined for this journey type.
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t">
          <Button variant="outline" size="sm" onClick={handleExport} disabled={!report}>
            <Download className="h-4 w-4 mr-1" />
            Export JSON
          </Button>
          <Button variant="default" size="sm" onClick={() => setOpen(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default JourneyReportModal;
