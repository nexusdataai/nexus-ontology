import { useState } from 'react';
import {
  BaseEdge, EdgeLabelRenderer, getSmoothStepPath, useReactFlow,
  type EdgeProps,
} from '@xyflow/react';
import { X } from 'lucide-react';

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

  // Pin the stroke to a clear primary blue regardless of theme /
  // React-Flow's selected colour palette so the animated dashes are
  // never mistaken for an error indicator.
  const mergedStyle: React.CSSProperties = {
    stroke: 'hsl(217 91% 60%)',
    strokeWidth: selected ? 2.5 : 1.75,
    ...style,
  };

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={mergedStyle} />
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
            aria-label="Delete edge"
            title="Delete this chain (Backspace also works)"
            onClick={(e) => {
              e.stopPropagation();
              setEdges((curr) => curr.filter((edge) => edge.id !== id));
            }}
            className={[
              'rounded-full w-5 h-5 flex items-center justify-center',
              'border border-card bg-red-500 text-white shadow',
              'hover:bg-red-400 transition-opacity',
              visible ? 'opacity-100' : 'opacity-0',
            ].join(' ')}
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export default DeletableEdge;
