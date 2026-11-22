import apiClient from './apiClient';

export interface NiFiPropertyDescriptor {
  name: string;
  displayName?: string;
  required?: boolean;
  default?: string;
}

export interface NiFiProcessorSpec {
  processorId: string;
  label: string;
  description?: string;
  category?: string;
  tags?: string[];
  bundle?: string;
  nifiClass?: string;
  runtime?: 'live' | 'stub';
  codeRef?: string;
  properties?: NiFiPropertyDescriptor[];
  relationships?: { name: string }[];
}

export interface ProcessorSource {
  processorId: string;
  available: boolean;
  path: string;
  language: string;
  source: string;
  reason?: string;
}

export interface ProcessorProbeRequest {
  params?: Record<string, unknown>;
  content?: string;
  attributes?: Record<string, unknown>;
}

export interface ProcessorProbeResult {
  processorId: string;
  status: 'pass' | 'fail' | 'skip' | string;
  duration_ms?: number;
  reason?: string;
  error?: string;
  result_preview?: string;
  terminalCount?: number;
  terminalAttributes?: Record<string, unknown>[];
  nodeStats?: unknown[];
  params?: Record<string, unknown>;
}

export interface NiFiAsset {
  assetId: string;
  title?: string;
  kind: string;
  processorIds?: string[];
  contentText?: string;
}

export function formatNexusBundle(bundle?: string): string {
  if (!bundle) return '—';
  return bundle.startsWith('nifi-') ? `nexus-${bundle.slice(5)}` : bundle;
}

export interface ProcessorRegistryCapabilities {
  runtimeExecution: boolean;
  envKey?: string;
  message?: string;
}

export const nifiProcessorService = {
  listProcessors: (category?: string) =>
    apiClient.get('/api/v1/nifi-processors', { params: category ? { category } : {} }) as Promise<{
      total: number;
      items: NiFiProcessorSpec[];
      capabilities?: ProcessorRegistryCapabilities;
    }>,

  getProcessor: (id: string) =>
    apiClient.get(`/api/v1/nifi-processors/${encodeURIComponent(id)}`) as Promise<NiFiProcessorSpec>,

  resync: () => apiClient.post('/api/v1/nifi-processors/resync') as Promise<{ synced: { processors: number; assets: number } }>,

  listAssets: (kind?: string) =>
    apiClient.get('/api/v1/nifi-assets', { params: kind ? { kind } : {} }) as Promise<{
      total: number;
      items: NiFiAsset[];
    }>,

  previewRun: (graph: unknown) =>
    apiClient.post('/api/v1/data-flow/nifi/preview-run', graph) as Promise<Record<string, unknown>>,

  getSource: (id: string) =>
    apiClient.get(`/api/v1/nifi-processors/${encodeURIComponent(id)}/source`) as Promise<ProcessorSource>,

  probeDefaults: (id: string) =>
    apiClient.get(`/api/v1/nifi-processors/${encodeURIComponent(id)}/probe-defaults`) as Promise<
      ProcessorProbeRequest & { processorId: string }
    >,

  probeProcessor: (id: string, body: ProcessorProbeRequest) =>
    apiClient.post(`/api/v1/nifi-processors/${encodeURIComponent(id)}/probe`, body) as Promise<ProcessorProbeResult>,

  probeBatch: (processorIds: string[]) =>
    apiClient.post('/api/v1/nifi-processors/probe-batch', { processor_ids: processorIds }) as Promise<{
      total: number;
      results: ProcessorProbeResult[];
    }>,
};