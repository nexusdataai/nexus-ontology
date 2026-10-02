import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Network } from 'lucide-react';
import type { HybridSearchResponse } from '@/services/ontoApi';

interface GraphViewerProps {
  results: HybridSearchResponse | null;
}

const GraphViewer: React.FC<GraphViewerProps> = ({ results }) => {
  if (!results || results.total === 0) {
    return (
      <div className="text-center text-muted-foreground py-12">
        Run a query to visualize the knowledge graph
      </div>
    );
  }

  const nodes = results.results.map((r) => ({
    id: r.source_id,
    category: r.metadata?.category || r.content_type,
    system: r.metadata?.system || 'unknown',
    similarity: r.similarity,
    graphExpanded: r.graph_expanded,
  }));

  const edges: { from: string; to: string; type: string }[] = [];
  const graphDocs = results.results.filter((r) => r.graph_expanded);
  const vectorDocs = results.results.filter((r) => !r.graph_expanded);

  for (const gd of graphDocs) {
    const closestVector = vectorDocs[0];
    if (closestVector) {
      edges.push({
        from: closestVector.source_id,
        to: gd.source_id,
        type: 'depends_on',
      });
    }
  }

  const CATEGORY_COLORS: Record<string, string> = {
    schema: '#3b82f6',
    onto_schema: '#3b82f6',
    policy: '#f59e0b',
    onto_policy: '#f59e0b',
    workflow: '#22c55e',
    onto_workflow: '#22c55e',
    integration: '#a855f7',
    onto_integration: '#a855f7',
  };

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Network className="h-5 w-5" />
          Knowledge Graph
          <Badge variant="secondary" className="text-xs">
            {nodes.length} nodes, {edges.length} edges
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative bg-background/50 rounded-lg border border-border/30 p-4 min-h-[400px]">
          <svg viewBox="0 0 800 500" className="w-full h-full">
            {edges.map((edge, i) => {
              const fromNode = nodes.find((n) => n.id === edge.from);
              const toNode = nodes.find((n) => n.id === edge.to);
              if (!fromNode || !toNode) return null;
              const fi = nodes.indexOf(fromNode);
              const ti = nodes.indexOf(toNode);
              const fx = 100 + (fi % 4) * 180;
              const fy = 80 + Math.floor(fi / 4) * 120;
              const tx = 100 + (ti % 4) * 180;
              const ty = 80 + Math.floor(ti / 4) * 120;
              return (
                <line
                  key={i}
                  x1={fx} y1={fy} x2={tx} y2={ty}
                  stroke="#666" strokeWidth="1" strokeDasharray="4,4" opacity="0.5"
                />
              );
            })}

            {nodes.map((node, i) => {
              const x = 100 + (i % 4) * 180;
              const y = 80 + Math.floor(i / 4) * 120;
              const color = CATEGORY_COLORS[node.category] || '#888';
              const label = node.id.length > 20 ? node.id.slice(0, 20) + '...' : node.id;

              return (
                <g key={node.id}>
                  <circle
                    cx={x} cy={y}
                    r={node.graphExpanded ? 18 : 22}
                    fill={color}
                    opacity={0.2 + node.similarity * 0.6}
                    stroke={color}
                    strokeWidth={node.graphExpanded ? 1 : 2}
                    strokeDasharray={node.graphExpanded ? '3,3' : 'none'}
                  />
                  <text
                    x={x} y={y + 35}
                    textAnchor="middle"
                    fill="currentColor"
                    fontSize="9"
                    opacity="0.7"
                  >
                    {label}
                  </text>
                  <text
                    x={x} y={y + 4}
                    textAnchor="middle"
                    fill="currentColor"
                    fontSize="8"
                    fontWeight="bold"
                  >
                    {node.category.replace('onto_', '').slice(0, 3).toUpperCase()}
                  </text>
                </g>
              );
            })}
          </svg>

          <div className="absolute bottom-2 left-2 flex gap-2 text-xs">
            {Object.entries(CATEGORY_COLORS).filter(([k]) => !k.startsWith('onto_')).map(([cat, color]) => (
              <div key={cat} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color, opacity: 0.6 }} />
                <span className="capitalize">{cat}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default GraphViewer;
