import { memo, useState } from 'react';
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { Icon } from '@/components/ds/Icon';
import { StatusPill } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import {
  encodeInputHandle, encodeOutputHandle, consumedParamsOf,
  type BuilderGraphEdge, type BuilderNodeData, type OutputHint, type ValidationIssue,
} from './builderState';

interface ToolNodePayload extends BuilderNodeData {
  /** All edges -- the node renders only its slice via consumedParamsOf. */
  __edges?: BuilderGraphEdge[];
  /** Validation issues keyed by this node id. */
  __issues?: ValidationIssue[];
  /** Output hint list for this tool, indexed by tool name. */
  __outputHints?: OutputHint[];
  /** Delete callback. */
  __onDelete?: (nodeId: string) => void;
  /** 1-based execution-order position; -1 means cycle. */
  __order?: number;
  /** Click-to-connect: pending source, if any (canvas-wide). */
  __pendingConnection?: { nodeId: string; key: string } | null;
  /** Click handler invoked when the user clicks an output port. */
  __beginConnection?: (key: string) => void;
  /** Click handler invoked when the user clicks an input port; returns true if a wire completed. */
  __completeConnection?: (param: string) => boolean;
  /** Sequential-mode flag: when true, suppress the input/output Handle
   * dots so the node renders as a list row without wireable ports.
   * Row labels + relationship descriptions stay visible. */
  __hideHandles?: boolean;
  // Allow extra fields React-Flow may inject (it widens to Record<string, unknown>).
  [k: string]: unknown;
}

type ToolNodeProps = NodeProps<Node<ToolNodePayload, 'tool'>>;

// Risk level is communicated via the header *background* tint plus the
// small icon in the header. The node *ring* expresses status only --
// red on error / unsatisfied, primary on selected, green when ready.
// Decoupling risk from status fixes the prior confusion where a
// healthy high-risk-write node read as "error" because both used red.
const RISK_LABEL: Record<string, string> = {
  read_only: 'Read-only',
  low_risk_write: 'Low-risk write',
  high_risk_write: 'High-risk write, needs approval',
};

/**
 * Shared Tailwind class block for both source and target handles.
 *
 * Handles are now 14px (was 8px) and rendered outside the node body so
 * they don't overlap the param text. Hover lights up a primary-coloured
 * ring so the drop target is obvious before the user starts dragging.
 */
const HANDLE_BASE =
  '!w-3 !h-3 !border-[1.5px] transition-shadow ' +
  'hover:!ring-2 hover:!ring-ring/60';

/**
 * Custom React-Flow node for one journey step.
 *
 * Layout:
 *   +----------------------------------------+
 *   |[1] tool_name                  risk  X  |
 *   |    description                          |
 *   |                                         |
 *   |   IN handles (border-left)              |
 *  --o   account_id                           |
 *  --o   subject                              |
 *   |                       OUT handles -- o-+--
 *   |                       results       o-+--
 *   +----------------------------------------+
 *
 * Handle ids use the encoded prefix so the canvas can decode source /
 * target keys back into ``from_key`` / ``to_param`` on the wire.
 *
 * Selection is driven by React-Flow's ``onNodeClick`` on the canvas,
 * not the wrapper onClick (it clashes with the drag/pan handler).
 */
function ToolNodeImpl({ id, data, selected }: ToolNodeProps) {
  const [open, setOpen] = useState(true);
  const tool = data.toolDef;
  const schemaProperties = tool?.parameters?.properties || {};
  const requiredSet = new Set<string>(tool?.parameters?.required || []);
  const paramKeys = Object.keys(schemaProperties);
  const userParams = data.params || {};

  const issues = data.__issues || [];
  const consumed = consumedParamsOf(id, data.__edges || []);
  const outputs = data.__outputHints || [];
  const order = data.__order;
  const pending = data.__pendingConnection || null;
  const isPendingSourceNode = pending?.nodeId === id;
  const isConnectTargetMode = !!pending && pending.nodeId !== id;
  const hideHandles = !!data.__hideHandles;

  /**
   * Client-side check for "required input that has no source": neither
   * a literal value nor an incoming wire. Surfaced as a red row so the
   * user does not have to click Validate to discover missing fields.
   */
  const isParamUnsatisfied = (p: string): boolean => {
    if (!requiredSet.has(p)) return false;
    if (consumed.has(p)) return false;
    const v = (userParams as Record<string, unknown>)[p];
    return v === undefined || v === null || v === '';
  };
  const missingCount = paramKeys.filter(isParamUnsatisfied).length;
  const hasUnsatisfied = missingCount > 0;

  // Traffic-light status ring: red = needs attention, primary =
  // currently selected, green = ready. Risk level is encoded by the
  // header background + icon below, NOT by the ring.
  const needsAttention = issues.length > 0 || hasUnsatisfied;
  const risk = data.toolDef?.risk_level || 'read_only';
  const ringColor = selected
    ? 'border-brand ring-2 ring-ring/40'
    : needsAttention
      ? 'border-destructive/60'
      : 'border-border-strong hover:border-brand/50';

  return (
    <div
      className={cn(
        'w-[280px] rounded-xl border bg-card text-foreground shadow-xs transition-[border-color,box-shadow] duration-200',
        ringColor,
      )}
    >
      {/* Order badge top-left -- shows the topological position so the
          author can read run order at a glance. ``!`` means the node is
          on a cycle the backend will reject. */}
      {order != null && (
        <div
          className={cn(
            'num absolute -left-2.5 -top-2.5 flex h-5 min-w-5 items-center justify-center rounded-full border px-1 text-xs font-medium',
            order === -1
              ? 'border-destructive/60 bg-card text-destructive'
              : 'border-border-strong bg-card text-muted-foreground',
          )}
          title={order === -1 ? 'Part of a loop: remove one connection before running' : `Step ${order} in run order`}
        >
          {order === -1 ? '!' : order}
        </div>
      )}

      <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2.5">
        <button
          className="flex-1 min-w-0 text-left"
          onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
          title={open ? 'Collapse' : 'Expand'}
        >
          <div className="truncate font-mono text-xs font-medium text-foreground">{data.tool || 'No tool chosen'}</div>
          <div className="text-xs text-muted-foreground truncate">
            {data.name && data.name !== data.tool ? data.name : (tool?.description || '').slice(0, 60)}
          </div>
        </button>
        {/* Status icon: green check when ready, red triangle when
            something needs attention. The risk-level tint on the
            header background communicates risk independently. */}
        {needsAttention ? (
          <span
            title={
              hasUnsatisfied
                ? `${missingCount} required input${missingCount === 1 ? '' : 's'} not set`
                : issues.map((i) => `${i.code}: ${i.message}`).join('\n')
            }
          >
            <Icon name="alert-triangle" className="h-3.5 w-3.5 text-destructive" />
          </span>
        ) : risk !== 'read_only' ? (
          <StatusPill status={risk} className="font-normal">{risk === 'high_risk_write' ? 'High-risk write' : 'Write'}</StatusPill>
        ) : null}
        <button
          className="rounded-sm text-subtle-foreground transition-colors hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          title="Remove step"
          aria-label="Remove step"
          onClick={(e) => { e.stopPropagation(); data.__onDelete?.(id); }}
        >
          <Icon name="trash" className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Inline issue banner: surfaces validation errors AND
          client-side detection of unfilled required inputs so the
          user does not have to hover the AlertTriangle to learn
          why the node is red. */}
      {(issues.length > 0 || hasUnsatisfied) && (
        <div className="flex items-start gap-1.5 border-b border-border bg-destructive/5 px-3 py-1.5 text-xs text-destructive">
          <div className="min-w-0 leading-snug">
            {hasUnsatisfied && (
              <div className="truncate">
                {missingCount} required input{missingCount === 1 ? '' : 's'} not set. Fill {missingCount === 1 ? 'it' : 'them'} in the step properties.
              </div>
            )}
            {issues.length > 0 && (
              <div className="truncate" title={issues.map((i) => `${i.code}: ${i.message}`).join('\n')}>
                {issues[0].code}: {issues[0].message}
                {issues.length > 1 && ` (+${issues.length - 1} more)`}
              </div>
            )}
          </div>
        </div>
      )}

      {open && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 px-3 py-2.5 font-mono text-xs">
          {/* Inputs (left column, target handles on the OUTSIDE edge) */}
          <div className="space-y-1.5">
            {paramKeys.length === 0 && (
              <div className="font-sans text-subtle-foreground">No inputs</div>
            )}
            {paramKeys.map((p) => {
              const isRequired = requiredSet.has(p);
              const isConsumed = consumed.has(p);
              const isUnsatisfied = isParamUnsatisfied(p);
              return (
                <div
                  key={`in-${p}`}
                  className={cn(
                    'relative pl-2 truncate transition-colors',
                    // In connect-target mode every input port lights up as a
                    // landing zone, with required ports nudged a shade brighter.
                    isConnectTargetMode && 'rounded -ml-2 pl-3 pr-1 py-0.5 cursor-pointer hover:ring-2 hover:ring-ring/60',
                    isConnectTargetMode && (isRequired ? 'bg-brand/10' : 'bg-surface-2'),
                    // Required-but-unsatisfied takes precedence visually so
                    // the user knows exactly which field still needs input.
                    isUnsatisfied && !isConnectTargetMode && 'rounded -ml-2 pl-3 pr-1 py-0.5 bg-destructive/10',
                  )}
                  title={
                    isConnectTargetMode
                      ? `Click to wire ${pending!.nodeId}.${pending!.key} into ${p}`
                      : isUnsatisfied
                        ? `Required input '${p}' has no value -- type a literal in the Step Editor or wire it from a prior step`
                        : undefined
                  }
                  onClick={(e) => {
                    if (!isConnectTargetMode) return;
                    e.stopPropagation();
                    data.__completeConnection?.(p);
                  }}
                >
                  {!hideHandles && (
                    <Handle
                      id={encodeInputHandle(p)}
                      type="target"
                      position={Position.Left}
                      aria-label={`Input port ${p}${isRequired ? ' (required)' : ''}`}
                      title={`Input: ${p}${isRequired ? ' (required)' : ''}`}
                      className={cn(
                        HANDLE_BASE,
                        isConsumed
                          ? '!border-brand !bg-brand'
                          : isConnectTargetMode
                            ? '!border-brand !bg-card !ring-2 !ring-ring/40'
                            : isUnsatisfied
                              ? '!border-destructive !bg-card'
                              : '!border-border-strong !bg-card',
                      )}
                      style={{ top: '50%', left: -7 }}
                      onClick={(e) => {
                        // Mirror the row click so users can land on either
                        // the dot or the row to complete a wire.
                        if (!isConnectTargetMode) return;
                        e.stopPropagation();
                        data.__completeConnection?.(p);
                      }}
                    />
                  )}
                  <span
                    className={cn(
                      isRequired ? 'text-foreground' : 'text-muted-foreground',
                      isConsumed && 'text-primary dark:text-brand-hi',
                      isUnsatisfied && 'text-destructive',
                    )}
                  >
                    {p}{isRequired ? '*' : ''}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Outputs (right column, source handles on the OUTSIDE edge) */}
          <div className="space-y-1.5 text-right">
            {outputs.length === 0 && (
              <div className="font-sans text-subtle-foreground">No outputs</div>
            )}
            {outputs.map((h) => {
              const isPendingSource = isPendingSourceNode && pending?.key === h.key;
              return (
                <div
                  key={`out-${h.key}`}
                  className={cn(
                    'relative pr-2 truncate transition-colors',
                    // Output rows are always clickable to start a wire.
                    'rounded -mr-2 pr-3 pl-1 py-0.5 cursor-pointer hover:bg-surface-2',
                    isPendingSource && 'bg-brand/10 ring-1 ring-brand/50',
                  )}
                  title={
                    isPendingSource
                      ? `Source selected: ${h.key} -- click an input port to wire, or Esc to cancel`
                      : `Output: ${h.key} (${h.kind}) -- click to start a wire, or drag onto a target port`
                  }
                  onClick={(e) => {
                    e.stopPropagation();
                    // If this output is already the pending source, toggle off.
                    if (isPendingSource) {
                      // Cancel by calling beginConnection with a noop?
                      // Simpler: let parent's Esc/pane-click handle cancel.
                      // Re-clicking the same source no-ops to avoid
                      // accidental cancellation; user can press Esc.
                      return;
                    }
                    data.__beginConnection?.(h.key);
                  }}
                >
                  <span className={cn(isPendingSource ? 'font-medium text-primary dark:text-brand-hi' : 'text-muted-foreground')}>
                    {h.key}
                  </span>
                  {!hideHandles && (
                    <Handle
                      id={encodeOutputHandle(h.key)}
                      type="source"
                      position={Position.Right}
                      aria-label={`Output port ${h.key}`}
                      title={`Output: ${h.key} (${h.kind}) -- click to start a wire, or drag onto a target port`}
                      className={cn(HANDLE_BASE, isPendingSource ? '!border-brand !bg-brand !ring-2 !ring-ring/50' : '!border-brand !bg-card')}
                      style={{ top: '50%', right: -7 }}
                      onClick={(e) => {
                        // Mirror the row click so the small dot also starts a wire.
                        e.stopPropagation();
                        if (isPendingSource) return;
                        data.__beginConnection?.(h.key);
                      }}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default memo(ToolNodeImpl);
