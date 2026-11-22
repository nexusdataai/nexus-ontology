import { memo } from 'react';
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { Icon, type IconName } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';

export interface PipelineNodeData {
  label: string;
  nodeType: string;
  icon?: string;
  proposed?: boolean;
  autoInserted?: boolean;
  [key: string]: unknown;
}

const ICON_MAP: Record<string, IconName> = {
  database: 'database',
  shuffle: 'shuffle',
  'file-json': 'file',
  'check-circle': 'check-circle',
  filter: 'filter',
  cube: 'cube',
  layers: 'layers',
  'alert-triangle': 'alert-triangle',
};

type Props = NodeProps<Node<PipelineNodeData, 'pipeline'>>;

function PipelineNodeComponent({ data, selected }: Props) {
  const icon = (ICON_MAP[data.icon ?? 'database'] ?? 'database') as IconName;
  return (
    <div
      className={cn(
        'min-w-[200px] rounded-lg border bg-card px-3 py-2.5 shadow-sm',
        data.proposed && 'border-dashed border-primary/60 bg-primary/5',
        selected && 'ring-2 ring-ring',
      )}
    >
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !border-border !bg-muted" />
      <div className="flex items-start gap-2">
        <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-surface-2 text-primary">
          <Icon name={icon} className="h-3.5 w-3.5" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-foreground">{data.label}</span>
          <span className="block truncate text-[11px] text-muted-foreground">{data.nodeType}</span>
          {data.autoInserted && (
            <span className="mt-0.5 block text-[10px] uppercase tracking-wide text-muted-foreground">Auto</span>
          )}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !border-border !bg-muted" />
    </div>
  );
}

export default memo(PipelineNodeComponent);