import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { ETLSourceType } from '@/services/etlPipelineService';
import PipelineStudioView from './PipelineStudioView';

export default function PipelineStudioPage() {
  const [params, setParams] = useSearchParams();
  const pipelineId = params.get('pipelineId') || undefined;
  const template = (params.get('template') || undefined) as ETLSourceType | undefined;

  const setPipelineId = (id: string) => {
    setParams(prev => {
      const next = new URLSearchParams(prev);
      next.set('tab', 'pipeline-studio');
      next.set('pipelineId', id);
      next.delete('template');
      return next;
    }, { replace: true });
  };

  const initialTemplate = useMemo(() => template, [template]);

  return (
    <PipelineStudioView
      journeyId={pipelineId}
      templateSourceType={initialTemplate}
      onCreated={setPipelineId}
    />
  );
}
