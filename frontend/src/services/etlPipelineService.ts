import apiClient from './apiClient';
import { dataFlowService } from './dataFlowService';
import { defaultGraphForSource } from '@/components/pipeline-studio/pipelineStudioState';

export type ETLSourceType =
  | 'social_listening'
  | 'file_uploads'
  | 'google_drive'
  | 'external_full'
  | 'generic';

export interface ETLStepDef {
  id: string;
  name: string;
  description: string;
}

export const ETL_BACKEND_STEPS: ETLStepDef[] = [
  { id: 'extract', name: 'Extract Source Data', description: 'Read data from source system (FDW, simulator, API)' },
  { id: 'validate_schema', name: 'Validate Schema', description: 'Validate source data against field definitions' },
  { id: 'transform', name: 'Transform Data', description: 'Apply field mappings and business logic transforms' },
  { id: 'load', name: 'Load Data', description: 'Write transformed data to virtual data layer' },
  { id: 'verify', name: 'Verify Results', description: 'Row count checks, null validation, data quality' },
];

const ETL_VDL_STEPS: ETLStepDef[] = [
  { id: 'register_vdl', name: 'Register VDL Mappings', description: 'Activate FDW mapping rules for virtual entities and warehouse tables' },
  { id: 'materialize_warehouse', name: 'Materialize Warehouse', description: 'Refresh warehouse KPI snapshots from external feeds' },
];

let _catalogSteps: Record<string, ETLStepDef[]> | null = null;

export async function loadEtlStepCatalog(): Promise<void> {
  try {
    const cat = await dataFlowService.getCatalog();
    const map: Record<string, ETLStepDef[]> = {};
    for (const [st, steps] of Object.entries(cat.runtimeStepsBySource ?? {})) {
      map[st] = steps.map(s => ({ id: s.id, name: s.name, description: s.description }));
    }
    _catalogSteps = map;
  } catch {
    _catalogSteps = null;
  }
}

export function getStepsForSourceType(sourceType: ETLSourceType): ETLStepDef[] {
  if (_catalogSteps?.[sourceType]) {
    return _catalogSteps[sourceType];
  }
  if (
    sourceType === 'social_listening'
    || sourceType === 'file_uploads'
    || sourceType === 'google_drive'
    || sourceType === 'external_full'
  ) {
    return [...ETL_BACKEND_STEPS, ...ETL_VDL_STEPS];
  }
  return ETL_BACKEND_STEPS;
}

export const SOURCE_TYPE_LABELS: Record<ETLSourceType, string> = {
  social_listening: 'Social Listening',
  file_uploads: 'File Uploads',
  google_drive: 'Google Drive',
  external_full: 'External Sources (full VDL)',
  generic: 'Generic',
};

export interface ETLPipelineConfig {
  mappingRuleId: string;
  sourceType?: ETLSourceType;
  sourceQuery?: string;
  batchSize?: number;
  mode: 'full' | 'incremental';
  schedule?: string;
}

export interface ETLPipeline {
  id: string;
  name: string;
  mappingRuleId: string;
  config: ETLPipelineConfig;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'scheduled';
  lastRunAt?: string;
  createdAt: string;
}

export interface ETLPipelineRun {
  jobId: string;
  status: string;
  progress: number;
  currentStep: string;
  startedAt: string;
  completedAt?: string;
  rowsProcessed?: number;
  error?: string;
}

export const etlPipelineService = {
  createPipeline: async (name: string, config: ETLPipelineConfig): Promise<any> => {
    const sourceType = config.sourceType || 'generic';
    const stageName = `ETL Pipeline — ${SOURCE_TYPE_LABELS[sourceType]}`;

    const journey: any = await apiClient.post('/api/v1/journeys/', {
      name,
      description: `ETL Pipeline: ${name}`,
      odaComponentType: 'data-pipeline',
      metadata: {
        config,
        sourceType,
        frontendType: 'etl-pipeline',
      },
      stages: [{
        stageId: 'etl_pipeline',
        name: stageName,
        order: 0,
        steps: [],
      }],
    });

    const journeyId = journey?.journey_id || journey?.journeyId || journey?.id;
    if (journeyId) {
      try {
        await fetch(`/api/v1/journeys/${journeyId}/stages?stage_id=etl_pipeline`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ name: stageName, order: 0 }),
        });
      } catch {
        // stage registration is non-fatal
      }
    }

    if (journeyId && config.schedule) {
      const cronParts = config.schedule.trim().split(/\s+/);
      let intervalMinutes = 360;
      if (cronParts.length >= 5 && cronParts[1].startsWith('*/')) {
        const hours = parseInt(cronParts[1].replace('*/', ''), 10);
        if (!isNaN(hours)) intervalMinutes = hours * 60;
      }
      try {
        await apiClient.post('/api/v1/schedules/', {
          journey_id: journeyId,
          stage_id: 'etl_pipeline',
          interval_minutes: intervalMinutes,
          enabled: true,
        });
      } catch {
        // schedule registration is non-fatal
      }
    }

    if (journeyId) {
      try {
        const cat = await dataFlowService.getCatalog();
        const graph = defaultGraphForSource(sourceType, config.mappingRuleId || '', cat.nodeTypes);
        await dataFlowService.saveJourneyGraph(journeyId, graph, false);
      } catch {
        // graph seed is non-fatal
      }
    }

    return {
      id: journeyId,
      journeyId,
      name,
      status: 'pending',
      config,
      createdAt: new Date().toISOString(),
    };
  },

  listPipelines: async (): Promise<any> => {
    const res: any = await apiClient.get('/api/v1/journeys/?component_type=data-pipeline');
    const items = res?.data ?? (Array.isArray(res) ? res : []);
    return items.map((j: any) => ({
      ...j,
      id: j.journeyId || j.id,
      config: j.config || j.metadata?.config || {
        sourceType: j.metadata?.sourceType,
        mode: j.description?.includes('incremental') ? 'incremental' : 'full',
      },
    }));
  },

  getPipelineStatus: (journeyId: string, jobId: string): Promise<any> =>
    apiClient.get(`/api/v1/journeys/${journeyId}/jobs/${jobId}`),

  getPipelineJobs: (journeyId: string): Promise<any> =>
    apiClient.get(`/api/v1/journeys/${journeyId}/jobs`),

  runPipeline: (journeyId: string, triggeredBy = 'ui', stageId: 'etl_pipeline' | 'nexus_flow' = 'etl_pipeline'): Promise<any> =>
    apiClient.post(
      `/api/v1/journeys/${journeyId}/jobs?stage_id=${encodeURIComponent(stageId)}&triggered_by=${encodeURIComponent(triggeredBy)}`,
    ),
};
