import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SubHeading } from '@/components/ds/kit';
import type { CatalogNodeType, DataFlowNode } from '@/services/dataFlowService';
import type { MappingRule } from '@/services/mappingRuleService';
import type { DataPlane } from '@/services/dataPlaneService';
import { SOURCE_TYPE_LABELS, type ETLSourceType } from '@/services/etlPipelineService';
import NodeSchemaForm from './NodeSchemaForm';
import GoogleDriveSourcePanel from './GoogleDriveSourcePanel';
import { categoryForType } from './pipelineConnectionRules';

const SOURCE_TYPES: ETLSourceType[] = [
  'social_listening',
  'file_uploads',
  'google_drive',
  'external_full',
  'generic',
];

const LIVE_SOURCE = (t: string) => t.startsWith('source.') && t !== 'source.mapping_rule' && !['source.kafka', 'source.postgres_cdc', 'source.s3'].includes(t);

const FLOW_PROCESSOR_TYPE = (t: string) => t.startsWith('nexus.') || t.startsWith('nifi.');

export default function PipelineInspector({
  node,
  mappingRules,
  dataPlanes = [],
  catalog = [],
  onPatch,
}: {
  node: DataFlowNode | null;
  mappingRules: MappingRule[];
  dataPlanes?: DataPlane[];
  catalog?: CatalogNodeType[];
  onPatch: (nodeId: string, params: Record<string, unknown>, label?: string) => void;
}) {
  if (!node) {
    return (
      <div className="p-4 text-sm text-muted-foreground">Select a step to edit parameters.</div>
    );
  }

  const params = node.params ?? {};
  const catalogEntry = catalog.find(c => c.type === node.type);
  const catLabel = categoryForType(node.type, catalog);

  return (
    <div className="space-y-4 p-4">
      <SubHeading>{node.ui?.label ?? node.type}</SubHeading>
      <p className="text-xs text-muted-foreground">
        {catLabel} · <span className="font-mono">{node.type}</span>
      </p>

      {catalogEntry?.configFields?.length ? (
        <NodeSchemaForm
          fields={catalogEntry.configFields}
          params={params}
          onChange={next => onPatch(node.id, next)}
        />
      ) : null}

      {node.type === 'source.google_drive' && (
        <GoogleDriveSourcePanel />
      )}

      {(LIVE_SOURCE(node.type) || node.type === 'transform.map_fields' || node.type === 'source.mapping_rule') && (
        <div className="space-y-2">
          <label className="block text-xs text-muted-foreground">Mapping rule</label>
          <Select
            value={String(params.mappingRuleId ?? '') || '__none__'}
            onValueChange={v => onPatch(node.id, { ...params, mappingRuleId: v === '__none__' ? '' : v })}
          >
            <SelectTrigger><SelectValue placeholder="Select rule" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">Auto-detect</SelectItem>
              {mappingRules.map(r => (
                <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {LIVE_SOURCE(node.type) && !catalogEntry?.configFields?.length && (
        <div className="space-y-3">
          {node.type === 'source.external_feed' && (
            <>
              <label className="block text-xs text-muted-foreground">Source type</label>
              <Select
                value={String(params.sourceType ?? 'generic')}
                onValueChange={v => onPatch(node.id, { ...params, sourceType: v })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SOURCE_TYPES.map(st => (
                    <SelectItem key={st} value={st}>{SOURCE_TYPE_LABELS[st]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}
          {node.type === 'source.fdw' && dataPlanes.length > 0 && (
            <>
              <label className="block text-xs text-muted-foreground">Data source</label>
              <Select
                value={String(params.dataPlaneId ?? '') || '__none__'}
                onValueChange={v => onPatch(node.id, { ...params, dataPlaneId: v === '__none__' ? '' : v })}
              >
                <SelectTrigger><SelectValue placeholder="Select source" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Unset</SelectItem>
                  {dataPlanes.map(dp => (
                    <SelectItem key={dp.id} value={dp.id}>{dp.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}
          <label className="block text-xs text-muted-foreground">Mode</label>
          <Select
            value={String(params.mode ?? 'full')}
            onValueChange={v => onPatch(node.id, { ...params, mode: v })}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="full">Full</SelectItem>
              <SelectItem value="incremental">Incremental</SelectItem>
            </SelectContent>
          </Select>
          <label className="block text-xs text-muted-foreground">Batch size</label>
          <Input
            type="number"
            value={Number(params.batchSize ?? 1000)}
            onChange={e => onPatch(node.id, { ...params, batchSize: Number(e.target.value) })}
          />
          <label className="block text-xs text-muted-foreground">Schedule (cron)</label>
          <Input
            value={String(params.schedule ?? '')}
            placeholder="Manual"
            onChange={e => onPatch(node.id, { ...params, schedule: e.target.value })}
          />
        </div>
      )}

      {node.type === 'transform.filter' && (
        <div className="space-y-2">
          <label className="block text-xs text-muted-foreground">Predicate</label>
          <Input
            value={String(params.predicate ?? '')}
            placeholder="e.g. order_id NOT LIKE 'test-%'"
            onChange={e => onPatch(node.id, { ...params, predicate: e.target.value })}
          />
        </div>
      )}

      {FLOW_PROCESSOR_TYPE(node.type) && (
        <FlowProcessorPropertyEditor
          node={node}
          catalogEntry={catalog.find(c => c.type === node.type)}
          onPatch={onPatch}
        />
      )}
    </div>
  );
}

function FlowProcessorPropertyEditor({
  node,
  catalogEntry,
  onPatch,
}: {
  node: DataFlowNode;
  catalogEntry?: CatalogNodeType;
  onPatch: (nodeId: string, params: Record<string, unknown>, label?: string) => void;
}) {
  const params = node.params ?? {};
  const props = catalogEntry?.properties ?? [];
  if (props.length === 0) {
    return (
      <div className="space-y-2">
        <label className="block text-xs text-muted-foreground">Custom property</label>
        <Input
          placeholder="name=value (add via key below)"
          onKeyDown={e => {
            if (e.key !== 'Enter') return;
            const raw = (e.target as HTMLInputElement).value;
            const eq = raw.indexOf('=');
            if (eq < 1) return;
            const key = raw.slice(0, eq).trim();
            const val = raw.slice(eq + 1).trim();
            onPatch(node.id, { ...params, [key]: val });
            (e.target as HTMLInputElement).value = '';
          }}
        />
        <p className="text-[10px] text-muted-foreground">Press Enter to add. Values support ${'{'}attr{'}'} EL.</p>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {props.slice(0, 12).map(p => (
        <div key={p.name} className="space-y-1">
          <label className="block text-xs text-muted-foreground">{p.displayName || p.name}</label>
          <Input
            value={String(params[p.name] ?? '')}
            onChange={e => onPatch(node.id, { ...params, [p.name]: e.target.value })}
          />
        </div>
      ))}
      {(catalogEntry?.relationships?.length ?? 0) > 0 && (
        <p className="text-[10px] text-muted-foreground">
          Outbound edges use relationship labels: {(catalogEntry?.relationships || []).map(r => r.name).join(', ')}
        </p>
      )}
    </div>
  );
}