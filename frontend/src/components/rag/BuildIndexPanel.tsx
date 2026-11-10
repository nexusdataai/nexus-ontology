import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ds/Icon';
import { CodeBlock, Meter, Panel, StatusPill } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { ontoApi } from '@/services/ontoApi';

interface StepStatus {
  id: string;
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  elapsed?: number;
}

const PIPELINE_STEPS: StepStatus[] = [
  { id: 'extract_unified_schema', name: 'Read the unified schema', status: 'pending' },
  { id: 'resolve_fdw_mapping', name: 'Resolve source table mappings', status: 'pending' },
  { id: 'extract_fdw', name: 'Read source table metadata', status: 'pending' },
  { id: 'extract_mapping_rules', name: 'Read mapping rules', status: 'pending' },
  { id: 'extract_policies', name: 'Read policies', status: 'pending' },
  { id: 'extract_workflows', name: 'Read workflows', status: 'pending' },
  { id: 'extract_integrations', name: 'Read integration rules', status: 'pending' },
  { id: 'normalize', name: 'Merge into one knowledge bundle', status: 'pending' },
  { id: 'enrich', name: 'Enrich with descriptions', status: 'pending' },
  { id: 'chunk_embed', name: 'Split and embed', status: 'pending' },
  { id: 'load_vector', name: 'Load the vector index', status: 'pending' },
  { id: 'load_graph', name: 'Load the knowledge graph', status: 'pending' },
  { id: 'validate', name: 'Check quality', status: 'pending' },
];

interface BuildIndexPanelProps {
  onComplete?: () => void;
  /** The index already exists, so the action reads "Rebuild index". */
  built?: boolean;
  className?: string;
}

const formatElapsed = (s: number): string => (s >= 60 ? `${Math.floor(s / 60)} min ${Math.round(s % 60)} s` : `${Math.round(s * 10) / 10} s`);

const BuildIndexPanel: React.FC<BuildIndexPanelProps> = ({ onComplete, built, className }) => {
  const [running, setRunning] = useState(false);
  const [journeyId, setJourneyId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [steps, setSteps] = useState<StepStatus[]>(PIPELINE_STEPS.map(s => ({ ...s })));
  const [overallStatus, setOverallStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [logs, setLogs] = useState<string[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Presentation only: the step list and the log are folded away until needed.
  const [showSteps, setShowSteps] = useState(false);
  const [showLog, setShowLog] = useState(false);

  const startPipeline = async () => {
    setRunning(true);
    setOverallStatus('running');
    setSteps(PIPELINE_STEPS.map(s => ({ ...s, status: 'pending' })));
    setLogs(['Starting Semantic RAG pipeline...']);

    try {
      const result = await ontoApi.createAndRunPipeline();
      setJourneyId(result.journey_id);
      setJobId(result.job_id);
      setLogs(prev => [...prev, `Journey: ${result.journey_id}`, `Job: ${result.job_id}`, 'Pipeline started. Polling for progress...']);
    } catch (e: any) {
      setLogs(prev => [...prev, `Failed to start pipeline: ${e.message}`]);
      setOverallStatus('failed');
      setRunning(false);
      toast.error('The index build could not start', { description: e.message });
    }
  };

  useEffect(() => {
    if (!journeyId || !jobId || !running) return;

    pollRef.current = setInterval(async () => {
      try {
        const status = await ontoApi.getJobStatus(journeyId, jobId);
        const jobStatus = status?.status || status?.job_status || 'unknown';
        const stepResults = status?.steps || status?.step_results || [];

        const updatedSteps = PIPELINE_STEPS.map(s => {
          const result = stepResults.find((r: any) =>
            r.step_id === s.id || r.id === s.id
          );
          if (result) {
            return {
              ...s,
              status: result.status === 'completed' ? 'completed' as const
                : result.status === 'failed' ? 'failed' as const
                : result.status === 'in_progress' ? 'in_progress' as const
                : 'pending' as const,
              elapsed: result.elapsed_seconds,
            };
          }
          return { ...s };
        });
        setSteps(updatedSteps);

        const completedCount = updatedSteps.filter(s => s.status === 'completed').length;
        const currentStep = updatedSteps.find(s => s.status === 'in_progress');

        if (currentStep) {
          setLogs(prev => {
            const last = prev[prev.length - 1];
            const msg = `[${completedCount}/${PIPELINE_STEPS.length}] Running: ${currentStep.name}`;
            return last === msg ? prev : [...prev, msg];
          });
        }

        if (jobStatus === 'completed' || jobStatus === 'done' ||
            completedCount === PIPELINE_STEPS.length) {
          setOverallStatus('completed');
          setRunning(false);
          setLogs(prev => [...prev, 'Pipeline completed successfully!']);
          if (pollRef.current) clearInterval(pollRef.current);
          toast.success('Knowledge index built', { description: `${completedCount} of ${PIPELINE_STEPS.length} steps completed.` });
          onComplete?.();
        } else if (jobStatus === 'failed' || jobStatus === 'error') {
          setOverallStatus('failed');
          setRunning(false);
          setLogs(prev => [...prev, `Pipeline failed: ${status?.error || 'unknown error'}`]);
          if (pollRef.current) clearInterval(pollRef.current);
          toast.error('The index build failed', { description: status?.error || 'Open the run log for details.' });
        }
      } catch (e: any) {
        setLogs(prev => [...prev, `Poll error: ${e.message}`]);
      }
    }, 5000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [journeyId, jobId, running]);

  const completedCount = steps.filter(s => s.status === 'completed').length;
  const currentStep = steps.find(s => s.status === 'in_progress');
  const failedStep = steps.find(s => s.status === 'failed');
  const total = PIPELINE_STEPS.length;
  const stepsOpen = showSteps || overallStatus === 'running' || overallStatus === 'failed';

  const verdict =
    overallStatus === 'running' ? (currentStep ? `Running: ${currentStep.name}` : 'Starting the build')
    : overallStatus === 'completed' ? 'The index is up to date with the knowledge store.'
    : overallStatus === 'failed' ? (failedStep ? `Stopped at: ${failedStep.name}` : 'The build did not finish. See the run log.')
    : built ? 'Rebuild after you change policies, workflows, integration rules or mappings.'
    : 'Reads the knowledge store and source schemas, then loads the vector index and the graph.';

  return (
    <Panel
      className={className}
      title="Build"
      description={`${total} steps, from schema to quality check`}
      actions={overallStatus !== 'idle' && (
        <StatusPill status={overallStatus === 'running' ? 'running' : overallStatus} variant="soft">
          {overallStatus === 'running' ? 'Building' : overallStatus === 'completed' ? 'Built' : 'Failed'}
        </StatusPill>
      )}
    >
      <p className="text-sm text-muted-foreground" aria-live="polite">{verdict}</p>

      {overallStatus !== 'idle' && (
        <div className="mt-4">
          <Meter
            value={completedCount}
            max={total}
            tone={overallStatus === 'failed' ? 'danger' : overallStatus === 'completed' ? 'success' : 'info'}
            label="Build progress"
          />
          <p className="mt-1.5 text-xs text-muted-foreground"><span className="num">{completedCount}</span> of <span className="num">{total}</span> steps done</p>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button onClick={startPipeline} disabled={running} variant={overallStatus === 'completed' ? 'outline' : 'default'}>
          {running ? (
            <><Icon name="spinner" className="animate-spin" /> Building, {completedCount} of {total}</>
          ) : overallStatus === 'completed' || built ? (
            <><Icon name="refresh" /> Rebuild index</>
          ) : (
            <><Icon name="play" /> Build index</>
          )}
        </Button>
        {overallStatus !== 'running' && overallStatus !== 'failed' && (
          <Button variant="ghost" size="sm" onClick={() => setShowSteps(v => !v)} aria-expanded={stepsOpen}>
            {stepsOpen ? 'Hide steps' : 'What it does'}
            <Icon name={stepsOpen ? 'chevron-up' : 'chevron-down'} className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {stepsOpen && (
        <ol className="mt-4 border-t border-border">
          {steps.map((step, i) => (
            <li key={step.id} className="flex items-center gap-2.5 border-b border-border py-2 text-sm last:border-b-0">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center">
                {step.status === 'completed' ? (
                  <Icon name="check" className="h-3.5 w-3.5 text-success" label="Done" />
                ) : step.status === 'in_progress' ? (
                  <span className="dot-live text-primary dark:text-brand-hi" role="img" aria-label="Running" />
                ) : step.status === 'failed' ? (
                  <Icon name="cross-circle" className="h-3.5 w-3.5 text-destructive" label="Failed" />
                ) : (
                  <span className="num text-xs text-subtle-foreground">{i + 1}</span>
                )}
              </span>
              <span className={cn('min-w-0 flex-1 truncate', step.status === 'pending' ? 'text-muted-foreground' : 'text-foreground', step.status === 'in_progress' && 'font-medium')}>
                {step.name}
              </span>
              {step.elapsed != null && <span className="num shrink-0 text-xs text-muted-foreground">{formatElapsed(step.elapsed)}</span>}
            </li>
          ))}
        </ol>
      )}

      {logs.length > 0 && (
        <div className="mt-4">
          <button
            type="button"
            onClick={() => setShowLog(v => !v)}
            aria-expanded={showLog}
            className="inline-flex items-center gap-1.5 rounded-sm text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Icon name={showLog ? 'chevron-down' : 'chevron-right'} className="h-3 w-3" />
            Run log <span className="num text-subtle-foreground">{logs.length}</span>
          </button>
          {showLog && <CodeBlock className="mt-2" maxHeight={180} wrap>{logs.join('\n')}</CodeBlock>}
        </div>
      )}
    </Panel>
  );
};

export default BuildIndexPanel;
