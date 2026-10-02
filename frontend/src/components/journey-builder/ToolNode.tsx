import { memo, useState } from 'react';
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { AlertTriangle, CheckCircle2, Trash2 } from 'lucide-react';
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
const RISK_BG: Record<string, string> = {
  read_only: 'bg-green-500/10',
  low_risk_write: 'bg-amber-500/10',
  high_risk_write: 'bg-red-500/10',
};

const RISK_LABEL: Record<string, string> = {
  read_only: 'Read-only',
  low_risk_write: 'Low-risk write',
  high_risk_write: 'High-risk write -- requires approval',
};

/**
 * Shared Tailwind class block for both source and target handles.
 *
 * Handles are now 14px (was 8px) and rendered outside the node body so
 * they don't overlap the param text. Hover lights up a primary-coloured
 * ring so the drop target is obvious before the user starts dragging.
 */
const HANDLE_BASE =
  '!w-3.5 !h-3.5 !border-2 !border-card transition-shadow ' +
  'hover:!ring-2 hover:!ring-primary/60';

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
  const ringColor = (issues.length || hasUnsatisfied)
    ? 'ring-red-500'
    : selected
      ? 'ring-primary'
      : 'ring-green-500/60';

  return (
    <div
      className={cn(
        'rounded-md border bg-card text-foreground shadow-sm w-[280px] ring-2 transition-colors',
        ringColor,
      )}
    >
      {/* Order badge top-left -- shows the topological position so the
          author can read run order at a glance. ``!`` means the node is
          on a cycle the backend will reject. */}
      {order != null && (
        <div
          className={cn(
            'absolute -top-2 -left-2 w-5 h-5 rounded-full text-[10px]',
            'font-semibold flex items-center justify-center border-2 border-card shadow',
            order === -1
              ? 'bg-red-500 text-white'
              : 'bg-primary text-primary-foreground',
          )}
          title={order === -1 ? 'On a cycle -- resolve before running' : `Step ${order} in execution order`}
        >
          {order === -1 ? '!' : order}
        </div>
      )}

      <div className={cn('px-3 py-2 border-b flex items-center justify-between gap-2', RISK_BG[data.toolDef?.risk_level || 'read_only'])}>
        <button
          className="flex-1 min-w-0 text-left"
          onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
          title={open ? 'collapse' : 'expand'}
        >
          <div className="text-[12px] font-mono truncate font-medium">{data.tool || '(no tool)'}</div>
          <div className="text-[10px] text-muted-foreground truncate">
            {data.name && data.name !== data.tool ? data.name : (tool?.description || '').slice(0, 60)}
          </div>
        </button>
        {/* Status icon: green check when ready, red triangle when
            something needs attention. The risk-level tint on the
            header background communicates risk independently. */}
        {issues.length > 0 || hasUnsatisfied ? (
          <span
            title={
              hasUnsatisfied
                ? `${missingCount} required input${missingCount === 1 ? '' : 's'} unset`
                : issues.map((i) => `${i.code}: ${i.message}`).join('\n')
            }
          >
            <AlertTriangle className="h-3.5 w-3.5 text-red-300" />
          </span>
        ) : (
          <span
            title={`Ready -- ${RISK_LABEL[data.toolDef?.risk_level || 'read_only'] || 'Read-only'}`}
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />
          </span>
        )}
        <button
          className="text-muted-foreground hover:text-red-300"
          title="Remove step"
          onClick={(e) => { e.stopPropagation(); data.__onDelete?.(id); }}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Inline issue banner: surfaces validation errors AND
          client-side detection of unfilled required inputs so the
          user does not have to hover the AlertTriangle to learn
          why the node is red. */}
      {(issues.length > 0 || hasUnsatisfied) && (
        <div className="px-3 py-1 border-b text-[10px] bg-red-500/10 text-red-200 flex items-start gap-1">
          <AlertTriangle className="h-3 w-3 mt-[1px] shrink-0" />
          <div className="min-w-0 leading-snug">
            {hasUnsatisfied && (
              <div className="truncate">
                {missingCount} required input{missingCount === 1 ? '' : 's'} unset -- open Step Editor to fill
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
        <div className="px-3 py-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] font-mono">
          {/* Inputs (left column, target handles on the OUTSIDE edge) */}
          <div className="space-y-1.5">
            {paramKeys.length === 0 && (
              <div className="text-muted-foreground italic">no inputs</div>
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
                    isConnectTargetMode && 'rounded -ml-2 pl-3 pr-1 py-0.5 cursor-pointer hover:ring-2 hover:ring-blue-400/60',
                    isConnectTargetMode && (isRequired ? 'bg-amber-500/15' : 'bg-muted/30'),
                    // Required-but-unsatisfied takes precedence visually so
                    // the user knows exactly which field still needs input.
                    isUnsatisfied && !isConnectTargetMode && 'rounded -ml-2 pl-3 pr-1 py-0.5 bg-red-500/10 ring-1 ring-red-500/40',
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
                          ? '!bg-blue-400'
                          : isConnectTargetMode
                            ? '!bg-blue-400 !ring-2 !ring-blue-400/40'
                            : isUnsatisfied
                              ? '!bg-red-500 !ring-2 !ring-red-500/40'
                              : isRequired ? '!bg-amber-400' : '!bg-muted-foreground',
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
                      isConsumed && 'text-blue-300',
                      isUnsatisfied && 'text-red-300',
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
              <div className="text-muted-foreground italic">no outputs</div>
            )}
            {outputs.map((h) => {
              const isPendingSource = isPendingSourceNode && pending?.key === h.key;
              return (
                <div
                  key={`out-${h.key}`}
                  className={cn(
                    'relative pr-2 truncate transition-colors',
                    // Output rows are always clickable to start a wire.
                    'rounded -mr-2 pr-3 pl-1 py-0.5 cursor-pointer hover:ring-2 hover:ring-primary/40',
                    isPendingSource && 'bg-primary/20 ring-2 ring-primary',
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
                  <span className={cn(isPendingSource ? 'text-primary font-medium' : 'text-muted-foreground')}>
                    {h.key}
                  </span>
                  {!hideHandles && (
                    <Handle
                      id={encodeOutputHandle(h.key)}
                      type="source"
                      position={Position.Right}
                      aria-label={`Output port ${h.key}`}
                      title={`Output: ${h.key} (${h.kind}) -- click to start a wire, or drag onto a target port`}
                      className={cn(HANDLE_BASE, isPendingSource ? '!bg-primary !ring-2 !ring-primary' : '!bg-primary')}
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
