import { useState, useEffect, useRef } from 'react';
import DashboardCard from '@/components/DashboardCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import * as d3 from 'd3';
import { useTheme } from '@/components/ThemeProvider';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Database, FileText, GitBranch, Globe, Code, Filter, Table, Layers, Network, ChevronDown, ChevronUp, Brain } from 'lucide-react';
import { TmfTable, TmfRelationship, TmfField } from '@/services/tmfOdaService';
import { useTmfOda } from '@/hooks/useTmfOda';
import { SecondBrainPanel } from '@/components/SecondBrainPanel';
import { SecondBrainRule } from '@/types/secondBrain';
import { secondBrainService } from '@/services/secondBrainService';

// Color schemes for different categories
const TABLE_COLORS = {
  'Core Entities': '#2563eb',        // Blue
  'Support Entities': '#059669',    // Green
  'Events': '#dc2626',             // Red
  'Characteristics': '#7c3aed',    // Purple
  'Contact Information': '#ea580c' // Orange
};

const RELATIONSHIP_COLORS = {
  'has_many': '#374151',          // Dark Gray
  'specializes_to': '#6366f1',    // Indigo  
  'extends': '#059669',           // Green
  'references': '#ec4899',        // Pink
  'association': '#f59e0b'        // Amber
};

// Relationship styles
const RELATIONSHIP_STYLES = {
  'has_many': 'solid',
  'specializes_to': 'dashed',
  'extends': 'solid',
  'references': 'dotted',
  'association': 'solid'
};

const width = 1400;
const height = 900;

export default function TmfOdaViewer() {
  // Use the simplified TMF ODA hook
  const {
    // State
    isLoading,
    error,
    currentDataset,
    filteredEndpoints,
    filterOptions,
    statistics,
    
    // Actions
    updateFilter,
    resetFilters,
    toggleCategory,
    isCategoryIncluded
  } = useTmfOda();

  // UI-only state
  const [selectedNode, setSelectedNode] = useState<TmfTable | null>(null);
  const [tooltip, setTooltip] = useState<{x: number, y: number, node: any} | null>(null);
  const [activeTab, setActiveTab] = useState('graph');
  const [legendCollapsed, setLegendCollapsed] = useState(false);
  const [showFilterPopup, setShowFilterPopup] = useState(false);
  const [secondBrainCollapsed, setSecondBrainCollapsed] = useState(false);
  
  const svgRef = useRef<SVGSVGElement>(null);
  const { theme } = useTheme();

  // Handle escape key to close popup
  useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && showFilterPopup) {
        setShowFilterPopup(false);
      }
    };

    if (showFilterPopup) {
      document.addEventListener('keydown', handleEscapeKey);
      return () => document.removeEventListener('keydown', handleEscapeKey);
    }
  }, [showFilterPopup]);

  // D3 Graph Rendering Function - Simplified
  const renderGraph = () => {
    if (!currentDataset || !svgRef.current) return;
    
    const { tables, relationships } = currentDataset;
    console.log('🎨 Rendering graph:', tables.length, 'tables,', relationships.length, 'relationships');
    console.log('🔍 Debug - currentDataset:', currentDataset);
    console.log('📋 Table names:', tables.map(t => t.name).slice(0, 10));
    console.log('🔗 Relationships sample:', relationships.slice(0, 5).map(r => `${r.source} -> ${r.target} (${r.relationship})`));
    
    // Clear SVG completely
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Handle empty data
    if (!tables.length) {
      svg.append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('font-size', 18)
        .attr('fill', theme === 'dark' ? '#9ca3af' : '#6b7280')
        .text(`No tables found for current filters`);
      return;
    }
    
    // Create main group
    const g = svg.append('g');
    
    // Add zoom behavior
    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => g.attr('transform', event.transform)) as any
    );
    
    // Add arrow markers for different relationship types
    const defs = svg.append('defs');
    
    Object.keys(RELATIONSHIP_COLORS).forEach(relType => {
      const color = RELATIONSHIP_COLORS[relType as keyof typeof RELATIONSHIP_COLORS];
      defs.append('marker')
        .attr('id', `arrowhead-${relType.replace(/\s+/g, '-')}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 30)
        .attr('refY', 0)
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color);
    });
    
    // Create simulation with enhanced forces
    const simulation = d3.forceSimulation(tables as any)
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(60))
      .force('x', d3.forceX(width / 2).strength(0.1))
      .force('y', d3.forceY(height / 2).strength(0.1));
    
    // Filter relationships to only include those between visible tables
    const tableNames = new Set(tables.map(t => t.name));
    const validRelationships = relationships.filter(r => {
      // Handle both string and object references (in case D3.js has mutated them)
      const sourceString = typeof r.source === 'string' ? r.source : (r.source as any).name || String(r.source);
      const targetString = typeof r.target === 'string' ? r.target : (r.target as any).name || String(r.target);
      return tableNames.has(sourceString) && tableNames.has(targetString);
    });
    
    console.log(`🔗 Rendering ${validRelationships.length} of ${relationships.length} relationships`);
    
    // Create a deep copy of relationships to prevent D3.js from mutating the original data
    const relationshipsCopy = validRelationships.map(r => ({
      ...r,
      source: typeof r.source === 'string' ? r.source : (r.source as any).name || String(r.source),
      target: typeof r.target === 'string' ? r.target : (r.target as any).name || String(r.target)
    }));
    
    // Add link force - only valid relationships
    const linkForce = d3.forceLink(relationshipsCopy)
      .id((d: any) => d.name)
      .distance(150)
      .strength(0.5);
    
    simulation.force('link', linkForce);
    
    // Draw valid relationships
    const link = g.append('g')
      .selectAll('line')
      .data(relationshipsCopy)
      .join('line')
      .attr('stroke', d => RELATIONSHIP_COLORS[d.relationship as keyof typeof RELATIONSHIP_COLORS] || '#666666')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', d => {
        const style = RELATIONSHIP_STYLES[d.relationship as keyof typeof RELATIONSHIP_STYLES];
        return style === 'dashed' ? '5,5' : style === 'dotted' ? '2,2' : 'none';
      })
      .attr('marker-end', d => `url(#arrowhead-${d.relationship.replace(/\s+/g, '-')})`)
      .attr('opacity', 0.8);
    
    // Draw nodes
    const node = g.append('g')
      .selectAll('g')
      .data(tables)
      .join('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .call(d3.drag<SVGGElement, any>()
        .on('start', (event, d: any) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d: any) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d: any) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        }) as any
      );
    
    // Node circles with category-based colors
    node.append('circle')
      .attr('r', d => {
        const categorySize = {
          'Core Entities': 35,
          'Support Entities': 28,
          'Events': 25,
          'Characteristics': 22,
          'Contact Information': 25
        };
        return categorySize[d.category as keyof typeof categorySize] || 25;
      })
      .attr('fill', d => TABLE_COLORS[d.category as keyof typeof TABLE_COLORS] || '#6fa8dc')
      .attr('stroke', '#fff')
      .attr('stroke-width', 3)
      .attr('opacity', 0.9)
      .on('click', function(event, d) {
        event.stopPropagation();
        setTooltip({ 
          x: event.clientX, 
          y: event.clientY, 
          node: d 
        });
        setSelectedNode(selectedNode?.name === d.name ? null : d);
      });
    
    // Entity names below circles
    node.append('text')
      .text(d => d.name)
      .attr('x', 0)
      .attr('y', d => {
        const categorySize = {
          'Core Entities': 35,
          'Support Entities': 28,
          'Events': 25,
          'Characteristics': 22,
          'Contact Information': 25
        };
        const radius = categorySize[d.category as keyof typeof categorySize] || 25;
        return radius + 18;
      })
      .attr('text-anchor', 'middle')
      .attr('font-size', 11)
      .attr('font-weight', 'bold')
      .attr('fill', theme === 'dark' ? '#fff' : '#000')
      .style('pointer-events', 'none');
    
    // Update positions on tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);
      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });
    
    // Ensure simulation runs
    simulation.alpha(1).restart();
    
    // Background click handler to close tooltips
    svg.on('click', () => {
      setTooltip(null);
    });
    
    console.log('✅ Graph rendered successfully');
  };

  // Handle Second Brain rule application
  const handleRuleApplied = (rule: SecondBrainRule) => {
    console.log('🧠 Applied rule:', rule.title);
    // Here you can implement specific logic for how rules affect the visualization
    // For example, highlighting certain entities, applying filters, etc.
    
    // Example: If it's a field-mapping rule, you might want to highlight related tables
    if (rule.type === 'field-mapping' && rule.context.tables) {
      console.log('🎯 Highlighting tables:', rule.context.tables);
      // This could trigger visual feedback in the graph
    }
  };

  // Re-render graph when dependencies change
  useEffect(() => {
    if (activeTab === 'graph') {
      const timer = setTimeout(() => {
        renderGraph();
      }, 50);
      
      return () => clearTimeout(timer);
    }
  }, [currentDataset, theme, activeTab]);

  // Additional effect to ensure graph re-renders when tab becomes active
  useEffect(() => {
    if (activeTab === 'graph' && currentDataset && svgRef.current) {
      renderGraph();
    }
  }, [activeTab]);

  // Handle loading and error states
  if (isLoading) return <LoadingSpinner />;
  if (error) return <div className="text-destructive p-4">{error}</div>;
  if (!currentDataset || !statistics) return <div>No TMF629 data available</div>;

  // Check if all categories are selected
  const allCategories = ['Core Entities', 'Support Entities', 'Events', 'Characteristics', 'Contact Information'];
  const allCategoriesSelected = allCategories.every(cat => isCategoryIncluded(cat));

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="text-sm bg-primary/10 dark:bg-primary/20">
            <Database className="h-3 w-3 mr-1" />
            TMF629
          </Badge>
          <Badge variant="outline" className="text-sm">
            {currentDataset.tables.length} Tables
          </Badge>
          <Badge variant="outline" className="text-sm">
            {currentDataset.relationships.length} Relationships
          </Badge>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Filter Icon */}
          <button
            onClick={() => setShowFilterPopup(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm border border-input bg-background rounded-md hover:bg-muted/50 transition-colors"
          >
            <Filter className="h-4 w-4" />
            Entity Categories
            <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">
              {allCategoriesSelected ? 'All' : filterOptions.includedCategories.size} selected
            </span>
          </button>
          
          {/* Second Brain Link */}
          <button
            onClick={() => setSecondBrainCollapsed(!secondBrainCollapsed)}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <Brain className="h-4 w-4" />
            Second Brain
            <Badge variant="secondary" className="text-xs">
              AI
            </Badge>
          </button>
        </div>
      </div>

      {/* Filter Popup */}
      {showFilterPopup && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowFilterPopup(false)}
        >
          <div 
            className="bg-background border border-border rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-foreground">Select Entity Categories</h3>
              <button
                onClick={() => setShowFilterPopup(false)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Category Toggles */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {allCategories.map(category => (
                  <label key={category} className="flex items-center space-x-3 cursor-pointer p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors">
                    <input
                      type="checkbox"
                      checked={isCategoryIncluded(category)}
                      onChange={() => toggleCategory(category)}
                      className="rounded border-border text-primary focus:ring-primary focus:ring-offset-0 w-4 h-4"
                    />
                    <div className="flex-1">
                      <span className="text-sm font-medium text-foreground">{category}</span>
                      <div className="text-xs text-muted-foreground">
                        {statistics?.tablesByCategory[category] || 0} tables
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                      {statistics?.tablesByCategory[category] || 0}
                    </span>
                  </label>
                ))}
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-4 border-t border-border">
                <button
                  onClick={() => {
                    // Select all categories
                    updateFilter({ includedCategories: new Set(allCategories) });
                  }}
                  className="px-4 py-2 text-sm border border-input bg-background rounded-md hover:bg-muted/50 transition-colors"
                >
                  Select All
                </button>
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowFilterPopup(false)}
                    className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                  >
                    Apply Filters
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs for Graph and Endpoints */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="graph" className="flex items-center gap-2">
            <GitBranch className="h-4 w-4" />
            Entity Relationship Graph
          </TabsTrigger>
          <TabsTrigger value="endpoints" className="flex items-center gap-2">
            <Globe className="h-4 w-4" />
            API Endpoints
          </TabsTrigger>
        </TabsList>

        <TabsContent value="graph" className="mt-6">
          {/* Main Graph Area */}
          <div className="relative bg-card rounded-lg border border-border">
            {/* Collapsible Legend */}
            <div className="absolute top-4 right-4 bg-card/95 rounded-lg border border-border shadow-lg z-20">
              {/* Legend Header with Toggle */}
              <div 
                className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => setLegendCollapsed(!legendCollapsed)}
              >
                <h4 className="text-foreground font-semibold text-sm flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Legend
                </h4>
                {legendCollapsed ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                )}
              </div>

              {/* Collapsible Content */}
              {!legendCollapsed && (
                <div className="px-4 pb-3 w-80">
                  {/* Table Categories */}
                  <div className="mb-4">
                    <h5 className="text-xs font-medium text-muted-foreground mb-2">Table Categories:</h5>
                    <div className="space-y-2 text-xs">
                      {Object.entries(TABLE_COLORS).map(([category, color]) => (
                        <div key={category} className="flex items-center gap-2">
                          <div 
                            className="w-4 h-4 rounded-full border border-border" 
                            style={{ backgroundColor: color }}
                          ></div>
                          <span className="text-muted-foreground flex-1">{category}</span>
                          <span className="text-xs bg-muted px-2 py-0.5 rounded">
                            {currentDataset.tables.filter(t => t.category === category).length}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Relationship Types */}
                  <div className="border-t border-border pt-3">
                    <h5 className="text-xs font-medium text-muted-foreground mb-2">Relationship Types:</h5>
                    <div className="space-y-2 text-xs">
                      {Object.entries(RELATIONSHIP_COLORS).map(([relType, color]) => (
                        <div key={relType} className="flex items-center gap-2">
                          <div 
                            className="w-6 h-0 border-t-2"
                            style={{ 
                              borderColor: color,
                              borderStyle: RELATIONSHIP_STYLES[relType as keyof typeof RELATIONSHIP_STYLES] 
                            }}
                          ></div>
                          <span className="text-muted-foreground flex-1">{relType}</span>
                          <span className="text-xs bg-muted px-2 py-0.5 rounded">
                            {currentDataset.relationships.filter(r => r.relationship === relType).length}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Graph SVG */}
            <div className="p-4" style={{ height: `${height + 100}px` }}>
              <svg 
                ref={svgRef} 
                width="100%" 
                height="100%" 
                style={{ background: theme === 'dark' ? '#0f172a' : '#f8fafc' }}
                viewBox={`0 0 ${width} ${height}`}
              />
            </div>

            {/* Simplified Node Details Tooltip */}
            {tooltip && (
              <div
                className={`fixed z-30 rounded-lg shadow-lg border text-sm max-h-96 overflow-hidden ${
                  theme === 'dark' 
                    ? 'bg-card text-white border-border' 
                    : 'bg-white text-foreground border-border'
                }`}
                style={{ 
                  left: Math.min(tooltip.x + 16, window.innerWidth - 520), 
                  top: Math.min(tooltip.y + 16, window.innerHeight - 400), 
                  minWidth: 350,
                  maxWidth: 500
                }}
              >
                {/* Header with close button */}
                <div className={`flex items-center justify-between px-4 py-3 border-b ${
                  theme === 'dark' ? 'border-border' : 'border-border'
                }`}>
                  <div className={`font-semibold text-base ${
                    theme === 'dark' ? 'text-primary' : 'text-primary'
                  }`}>{tooltip.node.name}</div>
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
                  <div className={`text-xs mb-3 flex items-center gap-2 ${
                    theme === 'dark' ? 'text-muted-foreground' : 'text-muted-foreground'
                  }`}>
                    <div 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: TABLE_COLORS[tooltip.node.category as keyof typeof TABLE_COLORS] }}
                    ></div>
                    <span>{tooltip.node.category}</span>
                    <span className="text-xs bg-muted px-2 py-0.5 rounded">TMF629</span>
                  </div>
                  <div className={`mb-4 ${
                    theme === 'dark' ? 'text-muted-foreground' : 'text-foreground'
                  }`}>{tooltip.node.description}</div>
                  
                  {/* Fields with descriptions */}
                  <div className={`border-t pt-3 ${
                    theme === 'dark' ? 'border-border-strong' : 'border-border'
                  }`}>
                    <div className={`font-semibold mb-3 text-sm flex items-center gap-2 ${
                      theme === 'dark' ? 'text-success' : 'text-success'
                    }`}>
                      <FileText className="h-4 w-4" />
                      Fields ({tooltip.node.fields.length}):
                    </div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {tooltip.node.fields.map((field: TmfField, index: number) => (
                        <div key={index} className={`rounded p-3 border ${
                          theme === 'dark' 
                            ? 'bg-surface-3 border-border' 
                            : 'bg-surface-2 border-border'
                        }`}>
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`font-medium ${
                              theme === 'dark' ? 'text-white' : 'text-foreground'
                            }`}>{field.name}</span>
                            <span className={`text-xs px-2 py-1 rounded ${
                              theme === 'dark' 
                                ? 'bg-primary text-primary' 
                                : 'bg-primary/10 text-primary'
                            }`}>
                              {field.type}
                            </span>
                          </div>
                          <div className={`text-xs leading-relaxed ${
                            theme === 'dark' ? 'text-muted-foreground' : 'text-muted-foreground'
                          }`}>{field.description}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="endpoints" className="mt-6">
          {/* API Endpoints Table */}
          <DashboardCard 
            title="TMF629 API Endpoints"
            subtitle={`${filteredEndpoints.length} endpoints available for Customer Management API`}
          >
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left p-3 font-semibold">Method</th>
                    <th className="text-left p-3 font-semibold">Endpoint</th>
                    <th className="text-left p-3 font-semibold">Name</th>
                    <th className="text-left p-3 font-semibold">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEndpoints.map((endpoint, index) => (
                    <tr key={index} className="border-b border-border hover:bg-muted/50">
                      <td className="p-3">
                        <Badge 
                          variant={endpoint.method === 'GET' ? 'default' : 
                                   endpoint.method === 'POST' ? 'secondary' : 
                                   endpoint.method === 'PUT' ? 'outline' : 'destructive'}
                          className="text-xs"
                        >
                          {endpoint.method}
                        </Badge>
                      </td>
                      <td className="p-3">
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {endpoint.endpoint}
                        </code>
                      </td>
                      <td className="p-3 font-medium text-sm">{endpoint.name}</td>
                      <td className="p-3 text-sm text-muted-foreground max-w-md">
                        {endpoint.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </DashboardCard>
        </TabsContent>
      </Tabs>

      {/* Statistics Summary */}
      <DashboardCard title="TMF629 Data Overview" subtitle="Summary statistics and entity distribution">
        {/* Table Category Statistics */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {Object.entries(statistics.tablesByCategory).map(([category, count]) => (
            <div key={category} className="bg-card rounded-lg p-4 border border-border text-center">
              <div 
                className="text-2xl font-semibold mb-1"
                style={{ color: TABLE_COLORS[category as keyof typeof TABLE_COLORS] }}
              >
                {currentDataset.tables.filter(t => t.category === category).length}
              </div>
              <div className="text-muted-foreground text-sm">{category}</div>
            </div>
          ))}
        </div>

        {/* Relationship Statistics */}
        <div className="grid grid-cols-3 gap-4">
          {Object.entries(statistics.relationshipsByCategory).map(([category, count]) => (
            <div key={category} className="bg-card rounded-lg p-4 border border-border text-center">
              <div 
                className="text-2xl font-semibold mb-1"
                style={{ color: RELATIONSHIP_COLORS[category as keyof typeof RELATIONSHIP_COLORS] }}
              >
                {currentDataset.relationships.filter(r => r.relationship === category).length}
              </div>
              <div className="text-muted-foreground text-sm">{category} Relationships</div>
            </div>
          ))}
        </div>
      </DashboardCard>

      {/* Second Brain Panel */}
      <SecondBrainPanel
        currentStage="tmf-mapping"
        contextData={{
          // You can provide context based on current selection
          table: selectedNode?.name,
        }}
        onRuleApplied={handleRuleApplied}
        collapsed={secondBrainCollapsed}
        onToggleCollapsed={() => setSecondBrainCollapsed(!secondBrainCollapsed)}
      />
    </div>
  );
} 