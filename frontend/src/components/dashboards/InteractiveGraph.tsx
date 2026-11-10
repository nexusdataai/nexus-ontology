import { useState, useEffect, useRef } from 'react';
import { fetchGraphData, GraphData, GraphNode, GraphEdge } from '@/services/dataService';
import DashboardCard from '@/components/DashboardCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import * as d3 from 'd3';
import { useTheme } from '@/components/ThemeProvider';

const nodeColors = {
  table: '#3b82f6',
  procedure: '#f59e0b',
  tmf_component: '#10b981',
  oda_endpoint: '#64748b',
  relationship: '#ef4444',
};

const nodeTypeLabels = {
  table: 'Table',
  procedure: 'Procedure',
  tmf_component: 'TMF Component',
  oda_endpoint: 'ODA Endpoint',
  relationship: 'Relationship',
};

const width = 900;
const height = 650;

export default function InteractiveGraph() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [simNodes, setSimNodes] = useState<any[]>([]);
  const [simLinks, setSimLinks] = useState<any[]>([]);
  const [tooltip, setTooltip] = useState<{x: number, y: number, node: any} | null>(null);
  const [filter, setFilter] = useState('');
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const simulationRef = useRef<d3.Simulation<any, undefined> | null>(null);
  const { theme } = useTheme();

  // Load data
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        const graphData = await fetchGraphData();
        setData(graphData);
      } catch (err) {
        setError('Failed to load graph data. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // D3 graph rendering
  useEffect(() => {
    if (!data) return;
    // Filtered nodes/links
    let nodes = data.nodes;
    let links = data.links;
    if (filter.trim()) {
      const filterLower = filter.trim().toLowerCase();
      nodes = data.nodes.filter(n => n.label.toLowerCase().includes(filterLower));
      const nodeIds = new Set(nodes.map(n => n.id));
      links = data.links.filter(l => nodeIds.has(l.source) && nodeIds.has(l.target));
    }
    // D3 code
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    const g = svg.append('g');
    svg.call(
      d3.zoom().scaleExtent([0.2, 3]).on('zoom', (event) => {
        g.attr('transform', event.transform);
      })
    );
    svg.append('defs').append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 22)
      .attr('refY', 0)
      .attr('markerWidth', 7)
      .attr('markerHeight', 7)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#bbb');
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(140))
      .force('charge', d3.forceManyBody().strength(-500))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(40));
    // Draw links
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', d => d.color || '#666')
      .attr('stroke-dasharray', d => d.type === 'tmf_mapping' ? '6,3' : d.type === 'procedure_mapping' ? '2,2' : null)
      .attr('marker-end', 'url(#arrowhead)');
    // Draw nodes
    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', 'node')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended)
      );
    node.append('circle')
      .attr('r', d => {
        switch (d.type) {
          case 'table': return 15;
          case 'procedure': return 12;
          case 'tmf_component': return 18;
          case 'oda_endpoint': return 10;
          default: return 8;
        }
      })
      .attr('fill', d => d.color || '#3b82f6')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      // Click handlers for interactive popup
      .on('click', function(event, d) {
        event.stopPropagation();
        // Toggle tooltip - close if same node, open if different node
        if (tooltip && tooltip.node.id === d.id) {
          setTooltip(null);
        } else {
          setTooltip({ x: event.clientX, y: event.clientY, node: d });
        }
      });
    // Force label color to white in dark mode, black in light mode
    node.append('text')
      .text(d => d.label)
      .attr('x', 0)
      .attr('y', d => {
        switch (d.type) {
          case 'table': return 25;
          case 'procedure': return 22;
          case 'tmf_component': return 28;
          case 'oda_endpoint': return 20;
          default: return 18;
        }
      })
      .attr('text-anchor', 'middle')
      .attr('font-size', 12)
      .attr('fill', theme === 'dark' ? '#fff' : '#000');
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }
    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
    // Add click handler to close popup when clicking on SVG background
    svg.on('click', function() {
      setTooltip(null);
    });

    // Clean up on unmount
    return () => simulation.stop();
  }, [data, filter, theme]);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="text-destructive p-4">{error}</div>;
  if (!data) return <div>Error: Invalid or missing graph data.</div>;

  // Filtered nodes/links for summary
  let shownNodes = data.nodes;
  let shownLinks = data.links;
  if (filter.trim()) {
    const filterLower = filter.trim().toLowerCase();
    shownNodes = data.nodes.filter(n => n.label.toLowerCase().includes(filterLower));
    const nodeIds = new Set(shownNodes.map(n => n.id));
    shownLinks = data.links.filter(l => nodeIds.has(l.source) && nodeIds.has(l.target));
  }

  return (
    <div className="w-full h-full">
      <div className="relative">
        {/* Legend - Absolute top right corner, no margin */}
        <div className="absolute top-0 right-0 w-64 bg-card/90 rounded-lg border border-border shadow px-5 py-4 z-20">
          <h4 className="text-foreground font-semibold mb-3 text-base">Legend</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-primary rounded-full border border-border"></div>
              <span className="text-muted-foreground">Table</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-warning rounded-full border border-border"></div>
              <span className="text-muted-foreground">Procedure</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-success rounded-full border border-border"></div>
              <span className="text-muted-foreground">TMF Component</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-border-strong rounded-full border border-border"></div>
              <span className="text-muted-foreground">ODA Endpoint</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-destructive rounded-full border border-border"></div>
              <span className="text-muted-foreground">Relationship</span>
            </div>
            <div className="border-t border-border pt-2 mt-2">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-6 h-0 border-t border-muted-foreground"></div>
                <span className="text-muted-foreground text-xs">TMF Mapping</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0 border-t border-muted-foreground border-dashed"></div>
                <span className="text-muted-foreground text-xs">ODA Mapping</span>
              </div>
            </div>
          </div>
        </div>
        {/* Removed horizontal legend bar */}
      </div>
      <div className="relative" style={{ height: `calc(100vh - 220px)` }}>
        <div className="absolute inset-0 bg-muted/30 w-full h-full ml-0">
          <svg ref={svgRef} width="100%" height="100%" style={{ display: 'block', width: '100%', height: '100%', background: 'none', marginLeft: 0 }} />
          {/* Interactive Node Details Popup */}
          {tooltip && (
            <div
              className={`fixed z-30 rounded-lg shadow-lg border text-sm max-h-96 overflow-hidden ${
                theme === 'dark' 
                  ? 'bg-card text-white border-border' 
                  : 'bg-white text-foreground border-border'
              }`}
              style={{ 
                left: Math.min(tooltip.x + 16, window.innerWidth - 420), 
                top: Math.min(tooltip.y + 16, window.innerHeight - 400), 
                minWidth: 280, 
                maxWidth: 400 
              }}
            >
              {/* Header with close button */}
              <div className={`flex items-center justify-between px-4 py-3 border-b ${
                theme === 'dark' ? 'border-border' : 'border-border'
              }`}>
                <div className={`font-semibold text-base ${
                  theme === 'dark' ? 'text-white' : 'text-foreground'
                }`}>{tooltip.node.label}</div>
                <button 
                  onClick={() => setTooltip(null)}
                  className={`transition-colors p-1 rounded ${
                    theme === 'dark' 
                      ? 'text-muted-foreground hover:text-white' 
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  ✕
                </button>
              </div>

              {/* Scrollable content */}
              <div className="px-4 py-3 max-h-80 overflow-y-auto">
                <div className={`mb-3 text-xs ${
                  theme === 'dark' ? 'text-muted-foreground' : 'text-muted-foreground'
                }`}>Type: {tooltip.node.type} | ID: {tooltip.node.id}</div>
                
                {/* Node Properties */}
                <div className="mb-4">
                  <div className={`font-semibold text-xs mb-2 ${
                    theme === 'dark' ? 'text-primary' : 'text-primary'
                  }`}>Properties:</div>
                  <div className="space-y-1">
                    {Object.entries(tooltip.node).map(([k, v]) => (
                      k !== 'label' && k !== 'id' && k !== 'type' && (
                        <div key={k} className="flex justify-between gap-2 text-xs">
                          <span className={`font-medium ${
                            theme === 'dark' ? 'text-muted-foreground' : 'text-muted-foreground'
                          }`}>{k}:</span> 
                          <span className={`break-words ${
                            theme === 'dark' ? 'text-foreground' : 'text-foreground'
                          }`}>{String(v)}</span>
                        </div>
                      )
                    ))}
                  </div>
                </div>

                {/* Mapped TMF Fields */}
                {data && (
                  <div className="mt-4">
                    <div className={`font-semibold text-xs mb-2 ${
                      theme === 'dark' ? 'text-success' : 'text-success'
                    }`}>Mapped TMF Fields:</div>
                    {data.links.filter(l => l.type === 'tmf_mapping' && l.source === tooltip.node.id).length === 0 ? (
                      <div className={`text-xs ${
                        theme === 'dark' ? 'text-muted-foreground' : 'text-muted-foreground'
                      }`}>No TMF mapping</div>
                    ) : (
                      <div className="space-y-2">
                        {data.links.filter(l => l.type === 'tmf_mapping' && l.source === tooltip.node.id).map((l, idx) => (
                          <div key={idx} className={`rounded p-2 ${
                            theme === 'dark' ? 'bg-surface-3' : 'bg-surface-2'
                          }`}>
                            <span className={`font-medium text-xs ${
                              theme === 'dark' ? 'text-success' : 'text-success'
                            }`}>{l.target}</span>
                            {l.title && <div className={`text-xs mt-1 ${
                              theme === 'dark' ? 'text-muted-foreground' : 'text-muted-foreground'
                            }`}>({l.title})</div>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

