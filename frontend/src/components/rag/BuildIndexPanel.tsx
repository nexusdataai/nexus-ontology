import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Hammer, Loader2, CheckCircle2, XCircle, Clock, Play } from 'lucide-react';
import { ontoApi } from '@/services/ontoApi';

interface StepStatus {
  id: string;
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  elapsed?: number;
}

const PIPELINE_STEPS: StepStatus[] = [
  { id: 'extract_unified_schema', name: 'Extract Unified Schema', status: 'pending' },
  { id: 'resolve_fdw_mapping', name: 'Resolve FDW Mapping', status: 'pending' },
  { id: 'extract_fdw', name: 'Extract FDW Metadata', status: 'pending' },
  { id: 'extract_mapping_rules', name: 'Extract Mapping Rules', status: 'pending' },
  { id: 'extract_policies', name: 'Extract Policies', status: 'pending' },
  { id: 'extract_workflows', name: 'Extract Workflows', status: 'pending' },
  { id: 'extract_integrations', name: 'Extract Integrations', status: 'pending' },
  { id: 'normalize', name: 'Normalize (.onto)', status: 'pending' },
  { id: 'enrich', name: 'LLM Enrichment', status: 'pending' },
  { id: 'chunk_embed', name: 'Chunk & Embed', status: 'pending' },
  { id: 'load_vector', name: 'Load Vector DB', status: 'pending' },
  { id: 'load_graph', name: 'Load Graph DB', status: 'pending' },
  { id: 'validate', name: 'Validate Quality', status: 'pending' },
];

interface BuildIndexPanelProps {
  onComplete?: () => void;
}

const BuildIndexPanel: React.FC<BuildIndexPanelProps> = ({ onComplete }) => {
  const [running, setRunning] = useState(false);
  const [journeyId, setJourneyId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [steps, setSteps] = useState<StepStatus[]>(PIPELINE_STEPS.map(s => ({ ...s })));
  const [overallStatus, setOverallStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [logs, setLogs] = useState<string[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
          onComplete?.();
        } else if (jobStatus === 'failed' || jobStatus === 'error') {
          setOverallStatus('failed');
          setRunning(false);
          setLogs(prev => [...prev, `Pipeline failed: ${status?.error || 'unknown error'}`]);
          if (pollRef.current) clearInterval(pollRef.current);
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

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Hammer className="h-5 w-5" />
            Build Knowledge Index
          </CardTitle>
          <Button
            onClick={startPipeline}
            disabled={running}
            size="sm"
            variant={overallStatus === 'completed' ? 'outline' : 'default'}
          >
            {running ? (
              <><Loader2 className="h-3 w-3 animate-spin mr-1" /> {completedCount}/{PIPELINE_STEPS.length}</>
            ) : overallStatus === 'completed' ? (
              <><CheckCircle2 className="h-3 w-3 mr-1" /> Rebuild</>
            ) : (
              <><Play className="h-3 w-3 mr-1" /> Build Index</>
            )}
          </Button>
        </div>
        {overallStatus !== 'idle' && (
          <div className="flex gap-2 mt-2">
            <Badge variant={overallStatus === 'completed' ? 'default' : overallStatus === 'failed' ? 'destructive' : 'secondary'}>
              {overallStatus}
            </Badge>
            <Badge variant="outline">{completedCount}/{PIPELINE_STEPS.length} steps</Badge>
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1">
          {steps.map((step) => (
            <div key={step.id} className="flex items-center gap-2 text-sm py-1">
              {step.status === 'completed' ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />
              ) : step.status === 'in_progress' ? (
                <Loader2 className="h-3.5 w-3.5 text-blue-400 animate-spin shrink-0" />
              ) : step.status === 'failed' ? (
                <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />
              ) : (
                <Clock className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />
              )}
              <span className={step.status === 'pending' ? 'text-muted-foreground/50' : ''}>
                {step.name}
              </span>
              {step.elapsed != null && (
                <span className="text-xs text-muted-foreground ml-auto">{step.elapsed}s</span>
              )}
            </div>
          ))}
        </div>

        {logs.length > 0 && (
          <ScrollArea className="h-[120px] mt-2">
            <div className="bg-muted/30 rounded p-2 text-xs font-mono space-y-0.5">
              {logs.map((log, i) => (
                <div key={i} className="text-muted-foreground">{log}</div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
};

export default BuildIndexPanel;
