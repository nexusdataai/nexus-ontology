import { useState } from 'react';
import {
  BaseEdge, EdgeLabelRenderer, getSmoothStepPath, useReactFlow,
  type EdgeProps,
} from '@xyflow/react';
import { Icon } from '@/components/ds/Icon';

/**
 * Custom edge that exposes a tiny "x" delete button at its midpoint.
 *
 * Discoverability fix for the canvas: with the default React-Flow edge
 * there is no way to remove a mis-wired chain without opening the Step
 * Editor and picking "(literal)" from the Reads-from dropdown. The "x"
 * here is visible on hover OR when the edge is selected, plus
 * keyboard Delete / Backspace works because `deleteKeyCode` is enabled
 * on the parent ReactFlow.
 *
 * Deletion goes through React-Flow's normal ``setEdges`` so the
 * canvas's ``onEdgesDelete`` handler still fires and clears the
 * ``${steps.X.y}`` placeholder from the consumer node's params.
 */
export function DeletableEdge(props: EdgeProps) {
  const {
    id, sourceX, sourceY, targetX, targetY,
    sourcePosition, targetPosition, style, markerEnd, selected,
  } = props;

  const { setEdges } = useReactFlow();
  const [hover, setHover] = useState(false);

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  });

  const visible = hover || selected;

  // Links are neutral hairlines. A link lights up in the brand blue,
  // with a flow line on top, only while it is hovered or selected.
  const mergedStyle: React.CSSProperties = {
    ...style,
    stroke: visible ? 'hsl(var(--brand-hi))' : 'hsl(var(--border-strong))',
    strokeOpacity: visible ? 0.45 : 1,
    strokeWidth: 1.5,
  };

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={mergedStyle} />
      {visible && <path d={edgePath} fill="none" stroke="hsl(var(--brand-hi))" strokeWidth={1.5} className="flow-line pointer-events-none" />}
      {/* Invisible-but-fat hit area so the user can mouse over the edge
          without having to land exactly on the 1.75 px stroke. */}
      <path
        d={edgePath}
        stroke="transparent"
        strokeWidth={18}
        fill="none"
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        className="cursor-pointer"
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
          onMouseEnter={() => setHover(true)}
          onMouseLeave={() => setHover(false)}
        >
          <button
            type="button"
            aria-label="Remove connection"
            title="Remove this connection (Backspace also works)"
            onClick={(e) => {
              e.stopPropagation();
              setEdges((curr) => curr.filter((edge) => edge.id !== id));
            }}
            className={[
              'flex h-5 w-5 items-center justify-center rounded-full',
              'border border-border-strong bg-popover text-muted-foreground shadow-sm',
              'transition-[opacity,color,border-color] hover:border-destructive/50 hover:text-destructive',
              visible ? 'opacity-100' : 'opacity-0',
            ].join(' ')}
          >
            <Icon name="close" className="h-2.5 w-2.5" />
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export default DeletableEdge;
