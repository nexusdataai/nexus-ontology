import { useState, useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Search, Loader2, RotateCcw, ZoomIn, ZoomOut, Maximize2,
  Database, Shield, Link2, Table2, X, Layers, Eye, ChevronDown, ChevronUp,
  ArrowRight, FileText, GitBranch,
} from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { mappingRuleService, type MappingRule } from '@/services/mappingRuleService';
import { virtualQueryService, type VirtualQueryResponse } from '@/services/virtualQueryService';

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  system: string;
  domain: string;
  riskLevel: string;
  fieldCount: number;
  isVirtual: boolean;
  fdwMappingStatus: string;
  degree: number;
}

interface GraphEdge extends d3.SimulationLinkDatum<GraphNode> {
  id: string;
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  category: string;
  description: string;
  targetExists: boolean;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: { nodeCount: number; edgeCount: number; systems: string[]; relationshipTypes: string[] };
}

const SYSTEM_COLORS: Record<string, string> = {
  Salesforce: '#3b82f6',
  Oracle: '#f97316',
  SAP: '#22c55e',
  Google_Drive: '#ef4444',
  File_Uploads: '#a855f7',
  Social_Listening: '#ec4899',
};

const EDGE_COLORS: Record<string, string> = {
  triggers: '#a855f7',
  syncs_to: '#3b82f6',
  depends_on: '#22c55e',
  constrained_by: '#f59e0b',
  owned_by: '#6b7280',
};

const RISK_COLORS: Record<string, string> = { high: '#ef4444', medium: '#f59e0b', low: '#22c55e' };

type RightTab = 'relationships' | 'vdl';

export default function KnowledgeGraphView() {
  const svgRef = useRef<SVGSVGElement>(null);
  const simRef = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [systemFilters, setSystemFilters] = useState<Set<string>>(new Set());
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  const [rightTab, setRightTab] = useState<RightTab>('relationships');
  const [entityDetail, setEntityDetail] = useState<any | null>(null);
  const [entityMappingRules, setEntityMappingRules] = useState<MappingRule[]>([]);
  const [vdlLoading, setVdlLoading] = useState(false);

  const [showDataPreview, setShowDataPreview] = useState(false);
  const [previewData, setPreviewData] = useState<VirtualQueryResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await apiClient.get<GraphData>('/api/v1/control-plane/entities/graph');
        setGraphData(data);
        setSystemFilters(new Set(data.stats.systems));
      } catch { setGraphData(null); }
      finally { setLoading(false); }
    })();
  }, []);

  useEffect(() => {
    if (!selectedNode) {
      setEntityDetail(null);
      setEntityMappingRules([]);
      setPreviewData(null);
      setShowDataPreview(false);
      setRightTab('relationships');
      return;
    }
    apiClient.get(`/api/v1/control-plane/entities/${encodeURIComponent(selectedNode.id)}`)
      .then(setEntityDetail).catch(() => setEntityDetail(null));

    setPreviewData(null);
    setPreviewLoading(true);
    setShowDataPreview(true);
    virtualQueryService.previewEntity(selectedNode.id, 10)
      .then(setPreviewData)
      .catch(() => setPreviewData(null))
      .finally(() => setPreviewLoading(false));
  }, [selectedNode?.id]);

  useEffect(() => {
    if (!selectedNode || rightTab !== 'vdl') return;
    setVdlLoading(true);
    mappingRuleService.list(selectedNode.id)
      .then(setEntityMappingRules)
      .catch(() => setEntityMappingRules([]))
      .finally(() => setVdlLoading(false));
  }, [selectedNode?.id, rightTab]);

  const handlePreviewData = async () => {
    if (!selectedNode) return;
    setPreviewLoading(true);
    setShowDataPreview(true);
    try {
      const data = await virtualQueryService.previewEntity(selectedNode.id, 10);
      setPreviewData(data);
    } catch { setPreviewData(null); }
    finally { setPreviewLoading(false); }
  };

  const getFilteredData = useCallback(() => {
    if (!graphData) return { nodes: [], edges: [] };
    const nodes = graphData.nodes.filter(n => systemFilters.has(n.system));
    const nodeIds = new Set(nodes.map(n => n.id));
    const edges = graphData.edges.filter(e => {
      const src = typeof e.source === 'string' ? e.source : e.source.id;
      const tgt = typeof e.target === 'string' ? e.target : e.target.id;
      return nodeIds.has(src) && nodeIds.has(tgt);
    });
    return { nodes, edges };
  }, [graphData, systemFilters]);

  const nodeEdges = selectedNode
    ? (graphData?.edges || []).filter(e => {
        const src = typeof e.source === 'string' ? e.source : e.source.id;
        const tgt = typeof e.target === 'string' ? e.target : e.target.id;
        return src === selectedNode.id || tgt === selectedNode.id;
      })
    : [];

  const selectedEntity = selectedNode
    ? graphData?.nodes.find(n => n.id === selectedNode.id) || null
    : null;

  useEffect(() => {
    if (!graphData || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth || 900;
    const height = svgRef.current.clientHeight || 600;

    svg.selectAll('*').remove();

    const { nodes: filteredNodes, edges: filteredEdges } = getFilteredData();
    if (filteredNodes.length === 0) return;

    const nodes: GraphNode[] = filteredNodes.map(n => ({ ...n }));
    const edges: GraphEdge[] = filteredEdges.map(e => ({
      ...e,
      source: typeof e.source === 'string' ? e.source : e.source.id,
      target: typeof e.target === 'string' ? e.target : e.target.id,
    }));

    const defs = svg.append('defs');
    Object.entries(EDGE_COLORS).forEach(([type, color]) => {
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color);
    });

    const g = svg.append('g');

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoom);
    zoomRef.current = zoom;

    const link = g.append('g')
      .selectAll('line')
      .data(edges)
      .join('line')
      .attr('stroke', d => EDGE_COLORS[d.type] || '#4b5563')
      .attr('stroke-opacity', 0.5)
      .attr('stroke-width', 1.5)
      .attr('marker-end', d => `url(#arrow-${d.type})`);

    const edgeLabel = g.append('g')
      .selectAll('text')
      .data(edges)
      .join('text')
      .text(d => d.type)
      .attr('text-anchor', 'middle')
      .attr('fill', d => EDGE_COLORS[d.type] || '#4b5563')
      .attr('font-size', '7px')
      .attr('dy', -4)
      .attr('pointer-events', 'none')
      .attr('opacity', 0.7);

    const nodeGroup = g.append('g')
      .selectAll<SVGGElement, GraphNode>('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(d3.drag<SVGGElement, GraphNode>()
        .on('start', (event, d) => {
          if (!event.active) sim.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d) => {
          if (!event.active) sim.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      );

    nodeGroup.append('circle')
      .attr('r', d => Math.max(8, Math.min(20, 6 + d.degree * 2)))
      .attr('fill', d => SYSTEM_COLORS[d.system] || '#6b7280')
      .attr('stroke', '#1e293b')
      .attr('stroke-width', 2);

    nodeGroup.append('text')
      .text(d => d.id.length > 18 ? d.id.slice(0, 16) + '..' : d.id)
      .attr('dy', d => Math.max(8, Math.min(20, 6 + d.degree * 2)) + 12)
      .attr('text-anchor', 'middle')
      .attr('fill', '#94a3b8')
      .attr('font-size', '9px')
      .attr('pointer-events', 'none');

    nodeGroup.on('click', (_event, d) => {
      setSelectedNode(d);
      nodeGroup.selectAll('circle')
        .attr('stroke', (n: any) => n.id === d.id ? '#ffffff' : '#1e293b')
        .attr('stroke-width', (n: any) => n.id === d.id ? 3 : 2);
      link
        .attr('stroke-opacity', (l: any) => {
          const src = typeof l.source === 'string' ? l.source : l.source.id;
          const tgt = typeof l.target === 'string' ? l.target : l.target.id;
          return src === d.id || tgt === d.id ? 0.9 : 0.15;
        })
        .attr('stroke-width', (l: any) => {
          const src = typeof l.source === 'string' ? l.source : l.source.id;
          const tgt = typeof l.target === 'string' ? l.target : l.target.id;
          return src === d.id || tgt === d.id ? 2.5 : 1;
        });
      edgeLabel
        .attr('opacity', (l: any) => {
          const src = typeof l.source === 'string' ? l.source : l.source.id;
          const tgt = typeof l.target === 'string' ? l.target : l.target.id;
          return src === d.id || tgt === d.id ? 1 : 0.1;
        })
        .attr('font-size', (l: any) => {
          const src = typeof l.source === 'string' ? l.source : l.source.id;
          const tgt = typeof l.target === 'string' ? l.target : l.target.id;
          return src === d.id || tgt === d.id ? '9px' : '7px';
        });
      nodeGroup.selectAll('circle')
        .attr('opacity', (n: any) => {
          if (n.id === d.id) return 1;
          const connected = edges.some(e => {
            const src = typeof e.source === 'string' ? e.source : e.source.id;
            const tgt = typeof e.target === 'string' ? e.target : e.target.id;
            return (src === d.id && tgt === n.id) || (tgt === d.id && src === n.id);
          });
          return connected ? 1 : 0.3;
        });
      nodeGroup.selectAll('text')
        .attr('opacity', (n: any) => {
          if (n.id === d.id) return 1;
          const connected = edges.some(e => {
            const src = typeof e.source === 'string' ? e.source : e.source.id;
            const tgt = typeof e.target === 'string' ? e.target : e.target.id;
            return (src === d.id && tgt === n.id) || (tgt === d.id && src === n.id);
          });
          return connected ? 1 : 0.3;
        });
    });

    nodeGroup
      .on('mouseenter', (_event, d) => setHoveredNode(d.id))
      .on('mouseleave', () => setHoveredNode(null));

    svg.on('click', (event) => {
      if (event.target === svgRef.current) {
        setSelectedNode(null);
        nodeGroup.selectAll('circle').attr('stroke', '#1e293b').attr('stroke-width', 2).attr('opacity', 1);
        nodeGroup.selectAll('text').attr('opacity', 1);
        link.attr('stroke-opacity', 0.5).attr('stroke-width', 1.5);
        edgeLabel.attr('opacity', 0.7).attr('font-size', '7px');
      }
    });

    const sim = d3.forceSimulation<GraphNode>(nodes)
      .force('link', d3.forceLink<GraphNode, GraphEdge>(edges).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(30))
      .on('tick', () => {
        link
          .attr('x1', d => (d.source as GraphNode).x!)
          .attr('y1', d => (d.source as GraphNode).y!)
          .attr('x2', d => (d.target as GraphNode).x!)
          .attr('y2', d => (d.target as GraphNode).y!);
        edgeLabel
          .attr('x', d => ((d.source as GraphNode).x! + (d.target as GraphNode).x!) / 2)
          .attr('y', d => ((d.source as GraphNode).y! + (d.target as GraphNode).y!) / 2);
        nodeGroup.attr('transform', d => `translate(${d.x},${d.y})`);
      });

    simRef.current = sim;

    return () => { sim.stop(); };
  }, [graphData, systemFilters, getFilteredData]);

  useEffect(() => {
    if (!svgRef.current || !graphData) return;
    const svg = d3.select(svgRef.current);
    const q = searchQuery.toLowerCase();
    svg.selectAll<SVGGElement, GraphNode>('g g g').each(function(d) {
      const match = !q || d.id.toLowerCase().includes(q);
      d3.select(this).selectAll('circle').attr('opacity', match ? 1 : 0.15);
      d3.select(this).selectAll('text').attr('opacity', match ? 1 : 0.15);
    });
  }, [searchQuery, graphData]);

  const handleZoom = (direction: 'in' | 'out' | 'reset') => {
    if (!svgRef.current || !zoomRef.current) return;
    const svg = d3.select(svgRef.current);
    if (direction === 'reset') {
      svg.transition().duration(500).call(zoomRef.current.transform, d3.zoomIdentity);
    } else {
      svg.transition().duration(300).call(
        zoomRef.current.scaleBy, direction === 'in' ? 1.4 : 0.7
      );
    }
  };

  const toggleSystem = (sys: string) => {
    setSystemFilters(prev => {
      const next = new Set(prev);
      if (next.has(sys)) next.delete(sys); else next.add(sys);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading knowledge graph...
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <Database className="h-6 w-6 mr-2 opacity-40" /> No graph data available. Run the Knowledge Pipeline first.
      </div>
    );
  }

  const { stats } = graphData;

  const policyEdges = nodeEdges.filter(e => e.type === 'constrained_by');
  const workflowEdges = nodeEdges.filter(e => e.type === 'triggers');
  const activeRule = entityMappingRules.find(r => r.status === 'active');
  const detail = entityDetail;

  return (
    <div className="flex flex-col h-full">
      {/* Top Row: Graph + Right Panel */}
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 flex flex-col min-w-0">
          {/* Toolbar */}
          <div className="flex items-center gap-2 px-4 py-2 border-b bg-card/50">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search nodes..."
                className="pl-7 h-7 text-xs"
              />
            </div>

            <div className="flex items-center gap-1 ml-2">
              {stats.systems.map(sys => (
                <button
                  key={sys}
                  onClick={() => toggleSystem(sys)}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] border transition-colors ${
                    systemFilters.has(sys) ? 'border-border text-foreground' : 'border-transparent text-muted-foreground/40'
                  }`}
                >
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: SYSTEM_COLORS[sys] || '#6b7280' }} />
                  {sys}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1 ml-auto">
              <Badge className="bg-muted text-muted-foreground text-[9px]">{stats.nodeCount} nodes</Badge>
              <Badge className="bg-muted text-muted-foreground text-[9px]">{stats.edgeCount} edges</Badge>
            </div>

            <div className="flex items-center gap-0.5 ml-2">
              <Button variant="ghost" size="sm" onClick={() => handleZoom('in')} className="h-7 w-7 p-0"><ZoomIn className="h-3.5 w-3.5" /></Button>
              <Button variant="ghost" size="sm" onClick={() => handleZoom('out')} className="h-7 w-7 p-0"><ZoomOut className="h-3.5 w-3.5" /></Button>
              <Button variant="ghost" size="sm" onClick={() => handleZoom('reset')} className="h-7 w-7 p-0"><RotateCcw className="h-3.5 w-3.5" /></Button>
            </div>
          </div>

          {/* Graph Canvas */}
          <div className="flex-1 relative bg-slate-100 dark:bg-[#0f172a]">
            <svg ref={svgRef} className="w-full h-full" />

            {hoveredNode && !selectedNode && (
              <div className="absolute top-3 left-3 bg-card border rounded-lg px-3 py-2 text-xs shadow-xl pointer-events-none">
                <span className="font-medium">{hoveredNode}</span>
                {graphData.nodes.find(n => n.id === hoveredNode) && (
                  <span className="text-muted-foreground ml-2">
                    {graphData.nodes.find(n => n.id === hoveredNode)!.system} / {graphData.nodes.find(n => n.id === hoveredNode)!.fieldCount} fields
                  </span>
                )}
              </div>
            )}

            <div className="absolute bottom-3 left-3 bg-card/80 backdrop-blur border rounded-lg p-2 text-[9px] space-y-1">
              <div className="text-muted-foreground font-medium mb-1">Edge Types</div>
              {Object.entries(EDGE_COLORS).map(([type, color]) => (
                <div key={type} className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 rounded" style={{ backgroundColor: color }} />
                  <span className="text-muted-foreground">{type}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel — Tabbed */}
        {selectedNode && selectedEntity && (
          <Card className="w-80 shrink-0 border-l rounded-none flex flex-col">
            <div className="flex items-center gap-2 px-3 py-2 border-b">
              <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: SYSTEM_COLORS[selectedEntity.system] || '#6b7280' }} />
              <span className="text-xs font-medium truncate flex-1">{selectedEntity.id}</span>
              <Button variant="ghost" size="sm" onClick={() => setSelectedNode(null)} className="h-6 w-6 p-0">
                <X className="h-3 w-3" />
              </Button>
            </div>

            {/* Tabs */}
            <div className="flex border-b text-[10px]">
              <button
                onClick={() => setRightTab('relationships')}
                className={`flex-1 py-1.5 text-center transition-colors ${rightTab === 'relationships' ? 'border-b-2 border-blue-500 text-blue-400' : 'text-muted-foreground hover:text-foreground'}`}
              >
                <Link2 className="h-3 w-3 inline mr-1" />Relationships
              </button>
              <button
                onClick={() => setRightTab('vdl')}
                className={`flex-1 py-1.5 text-center transition-colors ${rightTab === 'vdl' ? 'border-b-2 border-blue-500 text-blue-400' : 'text-muted-foreground hover:text-foreground'}`}
              >
                <Layers className="h-3 w-3 inline mr-1" />Data Layer
              </button>
            </div>

            <CardContent className="flex-1 min-h-0 p-0">
              <ScrollArea className="h-full">
                <div className="px-3 py-2 space-y-3">
                  {/* Common badges */}
                  <div className="flex flex-wrap gap-1">
                    <Badge className="text-[9px]" style={{ backgroundColor: SYSTEM_COLORS[selectedEntity.system] + '33', color: SYSTEM_COLORS[selectedEntity.system] }}>
                      {selectedEntity.system}
                    </Badge>
                    <Badge className={`text-[9px] ${selectedEntity.isVirtual ? 'bg-yellow-500/20 text-yellow-300' : 'bg-green-500/20 text-green-300'}`}>
                      {selectedEntity.isVirtual ? 'virtual' : 'mapped'}
                    </Badge>
                    <Badge className="text-[9px]" style={{ color: RISK_COLORS[selectedEntity.riskLevel] }}>
                      <Shield className="h-2.5 w-2.5 mr-0.5" />{selectedEntity.riskLevel}
                    </Badge>
                  </div>

                  {selectedEntity.domain && (
                    <p className="text-[10px] text-muted-foreground">{selectedEntity.domain}</p>
                  )}

                  {/* Tab 1: Relationships */}
                  {rightTab === 'relationships' && (
                    <>
                      <div className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground">
                        <Table2 className="h-3 w-3" /> {selectedEntity.fieldCount} fields
                      </div>

                      {nodeEdges.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground mb-1.5">
                            <Link2 className="h-3 w-3" /> {nodeEdges.length} relationships
                          </div>
                          <div className="space-y-1">
                            {nodeEdges.map((e, i) => {
                              const src = typeof e.source === 'string' ? e.source : e.source.id;
                              const tgt = typeof e.target === 'string' ? e.target : e.target.id;
                              const isOutgoing = src === selectedNode.id;
                              const other = isOutgoing ? tgt : src;
                              return (
                                <div key={i} className="flex items-start gap-1.5 text-[10px] p-1.5 rounded bg-muted/30">
                                  <Badge className="text-[8px] shrink-0 mt-0.5" style={{
                                    backgroundColor: (EDGE_COLORS[e.type] || '#6b7280') + '33',
                                    color: EDGE_COLORS[e.type] || '#6b7280',
                                  }}>
                                    {isOutgoing ? '→' : '←'} {e.type}
                                  </Badge>
                                  <div className="min-w-0">
                                    <div className="font-medium truncate">{other}</div>
                                    {e.description && <div className="text-muted-foreground truncate">{e.description}</div>}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  {/* Tab 2: Virtual Data Layer */}
                  {rightTab === 'vdl' && (
                    <>
                      {vdlLoading ? (
                        <div className="flex justify-center py-4"><Loader2 className="h-4 w-4 animate-spin" /></div>
                      ) : (
                        <>
                          {/* Mapping Rule */}
                          <div>
                            <div className="text-[10px] font-medium text-muted-foreground mb-1">
                              <Database className="h-3 w-3 inline mr-1" />Mapping Rule
                            </div>
                            {activeRule ? (
                              <div className="p-2 rounded bg-muted/30 space-y-1 text-[10px]">
                                <div className="flex items-center gap-1">
                                  <Badge className="text-[8px] bg-green-500/20 text-green-300">active</Badge>
                                  <span className="truncate font-medium">{activeRule.name}</span>
                                </div>
                                <div className="text-muted-foreground">
                                  {activeRule.sourceSchema}.{activeRule.sourceTable}
                                </div>
                                <div className="text-muted-foreground">
                                  {activeRule.fieldMaps.length} field mappings · {activeRule.sourceType}
                                </div>
                                {activeRule.fieldMaps.slice(0, 5).map((fm, i) => (
                                  <div key={i} className="flex items-center gap-1 text-[9px] pl-1">
                                    <span className="font-mono text-muted-foreground">{fm.sourceField || '—'}</span>
                                    <ArrowRight className="h-2 w-2 text-muted-foreground/50" />
                                    <span className="font-mono">{fm.targetField}</span>
                                  </div>
                                ))}
                                {activeRule.fieldMaps.length > 5 && (
                                  <div className="text-[9px] text-muted-foreground pl-1">+{activeRule.fieldMaps.length - 5} more</div>
                                )}
                              </div>
                            ) : (
                              <div className="p-2 rounded bg-muted/20 text-[10px] text-muted-foreground">
                                No active mapping rule
                              </div>
                            )}
                          </div>

                          {/* SCOR Process */}
                          {detail?.scorProcess && (
                            <div>
                              <div className="text-[10px] font-medium text-muted-foreground mb-1">SCOR Process</div>
                              <Badge className="text-[9px] bg-blue-500/20 text-blue-300">{detail.scorProcess}</Badge>
                            </div>
                          )}

                          {/* Semantic description */}
                          {detail?.semantic && (
                            <div>
                              <div className="text-[10px] font-medium text-muted-foreground mb-1">Description</div>
                              <p className="text-[10px] text-muted-foreground">{detail.semantic}</p>
                            </div>
                          )}

                          {/* Fields */}
                          {detail?.fields?.length > 0 && (
                            <div>
                              <div className="text-[10px] font-medium text-muted-foreground mb-1">
                                <Table2 className="h-3 w-3 inline mr-1" />{detail.fields.length} Fields
                              </div>
                              <div className="space-y-0.5">
                                {detail.fields.slice(0, 10).map((f: any, i: number) => (
                                  <div key={i} className="flex items-center gap-1 text-[9px] font-mono p-1 rounded bg-muted/20">
                                    <span>{f.name}</span>
                                    <span className="text-muted-foreground">({f.dataType})</span>
                                  </div>
                                ))}
                                {detail.fields.length > 10 && (
                                  <div className="text-[9px] text-muted-foreground">+{detail.fields.length - 10} more</div>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Related Policies */}
                          {policyEdges.length > 0 && (
                            <div>
                              <div className="text-[10px] font-medium text-muted-foreground mb-1">
                                <FileText className="h-3 w-3 inline mr-1" />Policies ({policyEdges.length})
                              </div>
                              {policyEdges.map((e, i) => {
                                const tgt = typeof e.target === 'string' ? e.target : e.target.id;
                                return (
                                  <div key={i} className="text-[9px] p-1 rounded bg-yellow-500/10 text-yellow-300 mb-0.5 truncate">{tgt}</div>
                                );
                              })}
                            </div>
                          )}

                          {/* Related Workflows */}
                          {workflowEdges.length > 0 && (
                            <div>
                              <div className="text-[10px] font-medium text-muted-foreground mb-1">
                                <GitBranch className="h-3 w-3 inline mr-1" />Workflows ({workflowEdges.length})
                              </div>
                              {workflowEdges.map((e, i) => {
                                const tgt = typeof e.target === 'string' ? e.target : e.target.id;
                                return (
                                  <div key={i} className="text-[9px] p-1 rounded bg-purple-500/10 text-purple-300 mb-0.5 truncate">{tgt}</div>
                                );
                              })}
                            </div>
                          )}

                          {/* Preview Data controls */}
                          <div className="flex gap-1 mt-1">
                            <Button variant="outline" size="sm" onClick={handlePreviewData} className="flex-1">
                              <RotateCcw className="h-3 w-3 mr-1" />
                              Refresh Preview
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => setShowDataPreview(p => !p)} className="w-8 p-0">
                              {showDataPreview ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />}
                            </Button>
                          </div>
                        </>
                      )}
                    </>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Bottom Panel — Data Preview (always visible when a node is selected) */}
      {selectedNode && (
        <div className={`border-t bg-card flex flex-col shrink-0 transition-all ${showDataPreview ? 'h-[200px]' : 'h-8'}`}>
          <div className="flex items-center gap-2 px-3 py-1.5 border-b bg-muted/30 cursor-pointer" onClick={() => setShowDataPreview(p => !p)}>
            <Eye className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] font-medium">Data Preview: {selectedNode.id}</span>
            {previewLoading && <Loader2 className="h-3 w-3 animate-spin text-blue-400" />}
            {!previewLoading && previewData?.metadata && (
              <span className="text-[10px] text-muted-foreground ml-2">
                {previewData.metadata.sourceTable && `Source: ${previewData.metadata.sourceTable}`}
                {previewData.metadata.rowCount != null && ` · ${previewData.metadata.rowCount} rows`}
                {previewData.metadata.source_type && ` · ${previewData.metadata.source_type}`}
              </span>
            )}
            <div className="flex-1" />
            <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handlePreviewData(); }} className="h-5 px-1">
              <RotateCcw className="h-3 w-3" />
            </Button>
            {showDataPreview ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronUp className="h-3 w-3 text-muted-foreground" />}
          </div>
          {showDataPreview && (
            <div className="flex-1 overflow-auto">
              {previewLoading ? (
                <div className="flex items-center justify-center h-full"><Loader2 className="h-4 w-4 animate-spin" /></div>
              ) : previewData && previewData.rows.length > 0 ? (
                <table className="w-full text-[10px]">
                  <thead>
                    <tr className="bg-muted/30 sticky top-0">
                      {Object.keys(previewData.rows[0]).map(col => (
                        <th key={col} className="px-2 py-1 text-left text-muted-foreground font-medium whitespace-nowrap">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {previewData.rows.map((row, i) => (
                      <tr key={i} className="hover:bg-muted/20">
                        {Object.values(row).map((val, j) => (
                          <td key={j} className="px-2 py-1 font-mono whitespace-nowrap max-w-[200px] truncate">{String(val ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex items-center justify-center h-full text-[10px] text-muted-foreground">
                  {previewData ? 'No data available' : 'No active mapping rule found for this entity'}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
