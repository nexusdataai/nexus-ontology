import type { DataFlowEdge, DataFlowGraph, DataFlowNode, CatalogNodeType } from '@/services/dataFlowService';
import type { ETLSourceType } from '@/services/etlPipelineService';
import { ETL_PIPELINE_TEMPLATES } from '../../config/etlPipelineTemplates';

const SOURCE_NODE: Record<ETLSourceType, string> = {
  social_listening: 'source.social_listening',
  file_uploads: 'source.file_uploads',
  google_drive: 'source.google_drive',
  external_full: 'source.external_full',
  generic: 'source.external_feed',
};

const TYPE_ORDER_TAIL = [
  'transform.parse_schema',
  'transform.validate_schema',
  'transform.map_fields',
  'sink.load_fdw',
  'sink.verify',
  'sink.register_vdl',
  'sink.materialize_warehouse',
];

export function emptyGraph(): DataFlowGraph {
  return { version: 1, draftVersion: 1, nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } };
}

const EXTERNAL: ETLSourceType[] = ['social_listening', 'file_uploads', 'google_drive', 'external_full'];

export function nodeLabel(type: string, catalog: CatalogNodeType[]): string {
  return catalog.find(c => c.type === type)?.label ?? type.split('.').pop() ?? type;
}

export function defaultGraphForSource(
  sourceType: ETLSourceType,
  mappingRuleId = '',
  catalog: CatalogNodeType[] = [],
): DataFlowGraph {
  const tpl = ETL_PIPELINE_TEMPLATES.find(t => t.sourceType === sourceType);
  const sourceNode = SOURCE_NODE[sourceType] ?? 'source.external_feed';
  const types = [sourceNode, ...TYPE_ORDER_TAIL].filter(t => {
    if ((t === 'sink.register_vdl' || t === 'sink.materialize_warehouse') && !EXTERNAL.includes(sourceType)) {
      return false;
    }
    return catalog.length === 0 || catalog.some(c => c.type === t) || t === sourceNode;
  });

  const nodes: DataFlowNode[] = types.map((type, i) => {
    const params: Record<string, unknown> = {};
    if (type.startsWith('source.')) {
      Object.assign(params, {
        sourceType,
        mode: tpl?.defaultConfig.mode ?? 'full',
        batchSize: tpl?.defaultConfig.batchSize ?? 1000,
        schedule: tpl?.defaultConfig.schedule,
        mappingRuleId: mappingRuleId || tpl?.defaultConfig.mappingRuleId || '',
      });
    }
    if (type === 'transform.map_fields' && mappingRuleId) {
      params.mappingRuleId = mappingRuleId;
    }
    return {
      id: `n-${type}-${i}`,
      type,
      params,
      ui: { position: { x: 120, y: i * 110 }, label: nodeLabel(type, catalog) },
    };
  });

  const edges: DataFlowEdge[] = nodes.slice(0, -1).map((n, i) => ({
    id: `e-${i}`,
    source: n.id,
    target: nodes[i + 1].id,
  }));

  return { version: 1, draftVersion: 1, nodes, edges, viewport: { x: 0, y: 0, zoom: 1 } };
}

export function verticalLayout(nodes: DataFlowNode[]): DataFlowNode[] {
  return nodes.map((n, i) => ({
    ...n,
    ui: { ...n.ui, position: { x: 120, y: i * 110 } },
  }));
}