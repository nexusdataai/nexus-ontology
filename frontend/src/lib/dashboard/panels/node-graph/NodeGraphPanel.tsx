import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';

interface NodeData {
  id: string;
  label: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  color: string;
  size: number;
}

interface EdgeData {
  source: string;
  target: string;
  label?: string;
}

const NODE_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#64748b'];

export function NodeGraphPanel({ data, options, width, height, loading }: PanelProps) {
  if (loading || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Loading...' : 'No data'}
      </div>
    );
  }

  const nodeFrame = data[0];
  const edgeFrame = data.length > 1 ? data[1] : undefined;
  const nodeIdField = (options.nodeIdField as string) || 'id';
  const nodeLabelField = (options.nodeLabelField as string) || 'label';
  const sourceField = (options.sourceField as string) || 'source';
  const targetField = (options.targetField as string) || 'target';
  const nodeSize = (options.nodeSize as number) ?? 16;

  const { initialNodes, edges } = useMemo(() => {
    const nodeRows = dataFrameToRows(nodeFrame);
    const nodes: NodeData[] = nodeRows.map((row, i) => ({
      id: String(row[nodeIdField] ?? row[nodeFrame.fields[0]?.name] ?? i),
      label: String(row[nodeLabelField] ?? row[nodeIdField] ?? row[nodeFrame.fields[0]?.name] ?? i),
      x: width / 2 + (Math.random() - 0.5) * width * 0.6,
      y: height / 2 + (Math.random() - 0.5) * height * 0.6,
      vx: 0,
      vy: 0,
      color: NODE_COLORS[i % NODE_COLORS.length],
      size: nodeSize,
    }));

    let edgeList: EdgeData[] = [];
    if (edgeFrame) {
      const edgeRows = dataFrameToRows(edgeFrame);
      edgeList = edgeRows.map((row) => ({
        source: String(row[sourceField] ?? ''),
        target: String(row[targetField] ?? ''),
        label: row.label ? String(row.label) : undefined,
      }));
    } else {
      const fields = nodeFrame.fields.map((f) => f.name);
      const srcIdx = fields.findIndex((f) => /source|from|parent/i.test(f));
      const tgtIdx = fields.findIndex((f) => /target|to|child/i.test(f));
      if (srcIdx >= 0 && tgtIdx >= 0) {
        const allRows = dataFrameToRows(nodeFrame);
        edgeList = allRows
          .filter((r) => r[fields[srcIdx]] && r[fields[tgtIdx]])
          .map((r) => ({
            source: String(r[fields[srcIdx]]),
            target: String(r[fields[tgtIdx]]),
          }));
      }
    }

    return { initialNodes: nodes, edges: edgeList };
  }, [nodeFrame, edgeFrame, nodeIdField, nodeLabelField, sourceField, targetField, nodeSize, width, height]);

  const [nodes, setNodes] = useState<NodeData[]>(initialNodes);
  const animRef = useRef<number>(0);

  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes]);

  useEffect(() => {
    let iteration = 0;
    const maxIterations = 120;

    const simulate = () => {
      if (iteration >= maxIterations) return;
      iteration++;

      setNodes((prev) => {
        const next = prev.map((n) => ({ ...n }));
        const alpha = 1 - iteration / maxIterations;
        const k = Math.sqrt((width * height) / Math.max(next.length, 1));

        for (let i = 0; i < next.length; i++) {
          for (let j = i + 1; j < next.length; j++) {
            const dx = next[j].x - next[i].x;
            const dy = next[j].y - next[i].y;
            const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
            const force = (k * k) / dist * alpha * 0.1;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            next[i].vx -= fx;
            next[i].vy -= fy;
            next[j].vx += fx;
            next[j].vy += fy;
          }
        }

        const nodeMap = new Map(next.map((n) => [n.id, n]));
        for (const edge of edges) {
          const src = nodeMap.get(edge.source);
          const tgt = nodeMap.get(edge.target);
          if (!src || !tgt) continue;
          const dx = tgt.x - src.x;
          const dy = tgt.y - src.y;
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const force = (dist / k) * alpha * 0.3;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          src.vx += fx;
          src.vy += fy;
          tgt.vx -= fx;
          tgt.vy -= fy;
        }

        const cx = width / 2;
        const cy = height / 2;
        for (const n of next) {
          n.vx += (cx - n.x) * 0.001 * alpha;
          n.vy += (cy - n.y) * 0.001 * alpha;
          n.vx *= 0.6;
          n.vy *= 0.6;
          n.x += n.vx;
          n.y += n.vy;
          n.x = Math.max(20, Math.min(width - 20, n.x));
          n.y = Math.max(20, Math.min(height - 40, n.y));
        }

        return next;
      });

      animRef.current = requestAnimationFrame(simulate);
    };

    animRef.current = requestAnimationFrame(simulate);
    return () => cancelAnimationFrame(animRef.current);
  }, [edges, width, height, initialNodes.length]);

  const nodeMap = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  return (
    <svg width={width} height={height - 16} className="overflow-hidden">
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <path d="M0,0 L8,3 L0,6" fill="currentColor" opacity="0.4" />
        </marker>
      </defs>
      {edges.map((edge, i) => {
        const src = nodeMap.get(edge.source);
        const tgt = nodeMap.get(edge.target);
        if (!src || !tgt) return null;
        return (
          <line
            key={i}
            x1={src.x}
            y1={src.y}
            x2={tgt.x}
            y2={tgt.y}
            stroke="currentColor"
            strokeOpacity={0.2}
            strokeWidth={1.5}
            markerEnd="url(#arrowhead)"
          />
        );
      })}
      {nodes.map((node) => (
        <g key={node.id}>
          <circle
            cx={node.x}
            cy={node.y}
            r={node.size / 2}
            fill={node.color}
            stroke={node.color}
            strokeWidth={2}
            fillOpacity={0.8}
          />
          <text
            x={node.x}
            y={node.y + node.size / 2 + 10}
            textAnchor="middle"
            className="fill-foreground"
            fontSize={9}
          >
            {node.label.length > 12 ? node.label.slice(0, 12) + '…' : node.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
