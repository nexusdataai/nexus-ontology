/**
 * Network view of the knowledge graph: the original Nexus graph (a live
 * force-directed network of circles with coloured, labelled relationship
 * lines, an edge-type legend and a hover card), drawn in the product theme.
 *
 * Used by KnowledgeGraphView when the "Network" layout is chosen. Owns its own
 * SVG, physics and zoom; selection and search come from the parent so the
 * inspector and toolbar work the same as in the other views.
 */
import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';

export interface NetworkNode {
  id: string;
  group: string;
  domain: string;
  degree: number;
  fieldCount?: number;
  riskLevel?: string;
}
export interface NetworkLink { id: string; s: string; t: string; type: string; description?: string }
export interface NetworkHandle { zoomBy: (factor: number) => void; fit: () => void }

interface Props {
  nodes: NetworkNode[];
  links: NetworkLink[];
  colourOf: (group: string) => string;
  groupLabel: (group: string) => string;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  /** Lower-case search text: matching entities stay bright, the rest fade. */
  query: string;
}

/** Relationship colours, as in the original, from the theme palette. */
const EDGE_TYPE_COLOUR: Record<string, string> = {
  triggers: 'hsl(var(--chart-6))',
  syncs_to: 'hsl(var(--chart-1))',
  depends_on: 'hsl(var(--success))',
  constrained_by: 'hsl(var(--chart-5))',
  owned_by: 'hsl(var(--chart-3))',
  validates: 'hsl(var(--chart-2))',
};
const edgeColour = (type: string) => EDGE_TYPE_COLOUR[type] || 'hsl(var(--muted-foreground))';
const words = (s: string) => String(s || '').replace(/_/g, ' ');
const radius = (degree: number) => Math.max(11, Math.min(26, 9 + degree * 2.5));
const shortName = (id: string) => (id.length > 24 ? `${id.slice(0, 22)}…` : id);

type SimNode = NetworkNode & d3.SimulationNodeDatum & { r: number };
type SimLink = d3.SimulationLinkDatum<SimNode> & NetworkLink;

export const NetworkCanvas = forwardRef<NetworkHandle, Props>(function NetworkCanvas(
  { nodes, links, colourOf, groupLabel, selectedId, onSelect, query },
  ref,
) {
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const simRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null);
  const simNodesRef = useRef<SimNode[]>([]);
  const [, setTick] = useState(0);
  const [hover, setHover] = useState<string | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  const nodeKey = nodes.map(n => n.id).join('|');
  const linkKey = links.map(l => l.id).join('|');

  const fitToContent = (animate = true) => {
    const svg = svgRef.current;
    const zoom = zoomRef.current;
    const pts = simNodesRef.current;
    if (!svg || !zoom || pts.length === 0) return;
    const W = svg.clientWidth, H = svg.clientHeight;
    if (!W || !H) return;
    const xs = pts.map(p => p.x || 0), ys = pts.map(p => p.y || 0);
    const x0 = Math.min(...xs) - 60, x1 = Math.max(...xs) + 60, y0 = Math.min(...ys) - 50, y1 = Math.max(...ys) + 50;
    // Leave room for the toolbar above and the domain bar below.
    const fitAll = Math.min(1.3, (W - 80) / (x1 - x0), (H - 190) / (y1 - y0));
    // Never shrink below a readable size; if it cannot all fit, start at the top.
    const minK = 0.55;
    const k = Math.max(minK, fitAll);
    const ty = fitAll < minK ? 120 - y0 * k : H / 2 + 10 - ((y0 + y1) / 2) * k;
    const t = d3.zoomIdentity.translate(W / 2 - ((x0 + x1) / 2) * k, ty).scale(k);
    const sel = d3.select(svg);
    if (animate) sel.transition().duration(600).call(zoom.transform, t);
    else sel.call(zoom.transform, t);
  };

  useImperativeHandle(ref, () => ({
    zoomBy: (f: number) => { if (svgRef.current && zoomRef.current) d3.select(svgRef.current).transition().duration(250).call(zoomRef.current.scaleBy, f); },
    fit: () => fitToContent(true),
  }));

  // Zoom and pan.
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .filter((event: MouseEvent) => (event.type === 'wheel' ? true : !event.button && !(event.target as Element).closest?.('[data-net-node]')))
      .on('zoom', (event) => { if (gRef.current) gRef.current.setAttribute('transform', event.transform.toString()); });
    zoomRef.current = zoom;
    d3.select(svg).call(zoom).on('dblclick.zoom', null);
    return () => { d3.select(svg).on('.zoom', null); };
  }, []);

  // Physics: a live force simulation, as in the original, with more room
  // between circles so names do not collide.
  useEffect(() => {
    const prev = new Map(simNodesRef.current.map(n => [n.id, n]));
    const count = Math.max(nodes.length, 1);
    const simNodes: SimNode[] = nodes.map((n, i) => {
      const old = prev.get(n.id);
      const a = (i / count) * Math.PI * 2;
      return { ...n, r: radius(n.degree), x: old?.x ?? Math.cos(a) * 360, y: old?.y ?? Math.sin(a) * 360 };
    });
    const byId = new Map(simNodes.map(n => [n.id, n]));
    const simLinks: SimLink[] = links
      .filter(l => byId.has(l.s) && byId.has(l.t))
      .map(l => ({ ...l, source: l.s, target: l.t }));
    simNodesRef.current = simNodes;

    const sim = d3.forceSimulation<SimNode>(simNodes)
      .force('link', d3.forceLink<SimNode, SimLink>(simLinks).id(d => d.id).distance(190))
      .force('charge', d3.forceManyBody().strength(-700).distanceMax(800))
      .force('center', d3.forceCenter(0, 0))
      .force('x', d3.forceX(0).strength(0.05))
      .force('y', d3.forceY(0).strength(0.06))
      .force('collide', d3.forceCollide<SimNode>(d => d.r + 52).iterations(3))
      .on('tick', () => setTick(t => t + 1));
    // Once the first settle finishes, frame the whole network.
    let framed = prev.size !== 0;
    sim.on('end', () => { if (!framed) { framed = true; fitToContent(true); } });
    simRef.current = sim;
    // Settle most of the way before the first paint, then let it finish live.
    if (prev.size === 0) {
      sim.stop();
      for (let i = 0; i < 300; i++) sim.tick();
      setTick(t => t + 1);
      setTimeout(() => fitToContent(false), 0);
      sim.alpha(0.08).restart();
    }
    return () => { sim.stop(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeKey, linkKey]);

  // Dragging a circle pulls its neighbours, as in the original.
  const drag = useRef<{ id: string; moved: boolean; x: number; y: number } | null>(null);
  const toWorld = (e: React.PointerEvent) => {
    const svg = svgRef.current!;
    const pt = d3.pointer(e.nativeEvent, svg);
    const t = d3.zoomTransform(svg);
    return t.invert(pt);
  };
  const onDown = (e: React.PointerEvent, id: string) => {
    if (e.button !== 0) return;
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
    drag.current = { id, moved: false, x: e.clientX, y: e.clientY };
  };
  const onMove = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    if (!d.moved && Math.hypot(e.clientX - d.x, e.clientY - d.y) < 4) return;
    const n = simNodesRef.current.find(x => x.id === d.id);
    if (!n) return;
    if (!d.moved) { d.moved = true; simRef.current?.alphaTarget(0.3).restart(); }
    const [wx, wy] = toWorld(e);
    n.fx = wx; n.fy = wy;
  };
  const onUp = (e: React.PointerEvent, id: string) => {
    const d = drag.current;
    drag.current = null;
    try { (e.currentTarget as Element).releasePointerCapture(e.pointerId); } catch { /* not captured */ }
    const n = simNodesRef.current.find(x => x.id === id);
    if (n) { n.fx = null; n.fy = null; }
    simRef.current?.alphaTarget(0);
    if (d && !d.moved) onSelectRef.current(id === selectedId ? null : id);
  };

  /* ------------------------------------------------------------ highlight */

  const [legendType, setLegendType] = useState<string | null>(null);
  const focusId = selectedId;
  const connected = useMemo(() => {
    const s = new Set<string>();
    if (!focusId) return s;
    s.add(focusId);
    for (const l of links) {
      if (l.s === focusId) s.add(l.t);
      if (l.t === focusId) s.add(l.s);
    }
    return s;
  }, [focusId, links]);
  const matches = (n: NetworkNode) => !query || n.id.toLowerCase().includes(query) || n.domain.toLowerCase().includes(query);
  const nodeOpacity = (n: NetworkNode) => (focusId ? (connected.has(n.id) ? 1 : 0.3) : query ? (matches(n) ? 1 : 0.15) : 1);
  const touches = (l: NetworkLink, id: string | null) => !!id && (l.s === id || l.t === id);

  const pos = new Map(simNodesRef.current.map(n => [n.id, n]));
  const hoverNode = hover ? nodes.find(n => n.id === hover) : null;
  const usedTypes = [...new Set(links.map(l => l.type))].sort();

  return (
    <div className="net-canvas absolute inset-0">
      <style>{NET_CSS}</style>
      <svg
        ref={svgRef}
        className="h-full w-full cursor-grab touch-none select-none active:cursor-grabbing"
        onClick={(e) => { if (e.target === e.currentTarget) onSelectRef.current(null); }}
        role="img"
        aria-label={`Network of ${nodes.length} entities and ${links.length} relationships`}
      >
        <defs>
          {Object.entries({ ...EDGE_TYPE_COLOUR, other: 'hsl(var(--muted-foreground))' }).map(([type, colour]) => (
            <marker key={type} id={`net-arrow-${type}`} viewBox="0 -5 10 10" refX="10" refY="0" markerWidth="5" markerHeight="5" orient="auto">
              <path d="M0,-5L10,0L0,5" fill={colour} />
            </marker>
          ))}
        </defs>
        <g ref={gRef}>
          {/* relationships */}
          <g className="net-lines">
            {links.map(l => {
              const a = pos.get(l.s), b = pos.get(l.t);
              if (!a || !b || a.x == null || b.x == null || a.y == null || b.y == null) return null;
              const dx = b.x - a.x, dy = b.y - a.y, dist = Math.hypot(dx, dy) || 1;
              const x1 = a.x + (dx / dist) * (a.r + 1), y1 = a.y + (dy / dist) * (a.r + 1);
              const x2 = b.x - (dx / dist) * (b.r + 4), y2 = b.y - (dy / dist) * (b.r + 4);
              const selectedLink = touches(l, focusId);
              const hovered = touches(l, hover);
              const legendOn = legendType === l.type;
              const on = selectedLink || hovered || legendOn;
              const opacity = legendType ? (legendOn ? 0.95 : 0.06)
                : focusId ? (selectedLink ? 0.9 : hovered ? 0.6 : 0.12)
                : hovered ? 0.95 : query ? 0.2 : 0.5;
              const labelOpacity = legendType ? (legendOn ? 1 : 0)
                : focusId ? (selectedLink ? 1 : hovered ? 0.7 : 0.08)
                : hovered ? 1 : query ? 0.15 : 0.75;
              const type = EDGE_TYPE_COLOUR[l.type] ? l.type : 'other';
              const colour = edgeColour(l.type);
              return (
                <g key={l.id}>
                  <line className="net-ease" x1={x1} y1={y1} x2={x2} y2={y2} stroke={colour} style={{ strokeOpacity: opacity }} strokeWidth={on ? 2.6 : 1.6} markerEnd={`url(#net-arrow-${type})`} />
                  {selectedLink && (
                    <line className="net-flow" x1={x1} y1={y1} x2={x2} y2={y2} stroke="hsl(var(--background))" strokeOpacity={0.7} strokeWidth={1.6} strokeDasharray="3 9" strokeLinecap="round" />
                  )}
                  <text
                    className="net-ease"
                    x={(x1 + x2) / 2}
                    y={(y1 + y2) / 2}
                    dy={-5}
                    textAnchor="middle"
                    fill={colour}
                    fontSize={on ? 12 : 11}
                    fontWeight={on ? 500 : 400}
                    style={{ opacity: labelOpacity }}
                    pointerEvents="none"
                  >
                    {words(l.type)}
                  </text>
                </g>
              );
            })}
          </g>

          {/* entities */}
          <g>
            {nodes.map((n, i) => {
              const p = pos.get(n.id);
              if (!p || p.x == null || p.y == null) return null;
              const selected = n.id === selectedId;
              const isHover = n.id === hover;
              const colour = colourOf(n.group);
              return (
                <g
                  key={n.id}
                  data-net-node
                  transform={`translate(${p.x},${p.y})`}
                  style={{ opacity: nodeOpacity(n) }}
                  className="net-ease net-node cursor-pointer outline-none"
                  tabIndex={0}
                  role="button"
                  aria-pressed={selected}
                  aria-label={`${words(n.id)}, ${groupLabel(n.group)}, ${n.degree} links`}
                  onPointerDown={(e) => onDown(e, n.id)}
                  onPointerMove={onMove}
                  onPointerUp={(e) => onUp(e, n.id)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectRef.current(n.id); } }}
                  onMouseEnter={() => setHover(n.id)}
                  onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(n.id)}
                  onBlur={() => setHover(null)}
                >
                  <g className="net-pop" style={{ animationDelay: `${Math.min(i * 14, 700)}ms` }}>
                    {selected && <circle className="net-pulse" r={p.r + 5} fill="none" stroke={colour} strokeWidth={2} />}
                    <circle className="net-halo" r={p.r + 7} fill={colour} style={{ opacity: isHover || selected ? 0.22 : 0 }} />
                    <circle
                      className="net-dot"
                      r={p.r}
                      fill={colour}
                      stroke={selected ? 'hsl(var(--foreground))' : 'hsl(var(--background))'}
                      strokeWidth={selected ? 3.5 : 2.5}
                    />
                    <text
                      y={p.r + 18}
                      textAnchor="middle"
                      fontSize={13}
                      fill={selected || isHover ? 'hsl(var(--foreground))' : 'hsl(var(--muted-foreground))'}
                      fontWeight={selected ? 600 : isHover ? 500 : 400}
                      paintOrder="stroke"
                      stroke="hsl(var(--background))"
                      strokeWidth={3}
                      strokeLinejoin="round"
                      pointerEvents="none"
                    >
                      {shortName(words(n.id))}
                    </text>
                  </g>
                </g>
              );
            })}
          </g>
        </g>
      </svg>

      {/* hover card, as in the original */}
      {hoverNode && (
        <div key={hoverNode.id} className="net-card pointer-events-none absolute left-3 top-28 z-10 w-64 rounded-xl border border-border bg-popover px-3.5 py-2.5 text-sm shadow-lg sm:left-4" role="status">
          <p className="flex items-center gap-2 font-medium text-foreground">
            <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: colourOf(hoverNode.group) }} />
            <span className="truncate">{words(hoverNode.id)}</span>
          </p>
          <p className="mt-1 text-muted-foreground">{hoverNode.domain}</p>
          <p className="mt-0.5 text-muted-foreground">
            {hoverNode.fieldCount != null && <><span className="num text-foreground">{hoverNode.fieldCount}</span> fields · </>}
            <span className="num text-foreground">{hoverNode.degree}</span> links
            {hoverNode.riskLevel && <> · {hoverNode.riskLevel} risk</>}
          </p>
        </div>
      )}

      {/* edge-type legend, as in the original; hover a type to see only those lines */}
      <div className="absolute bottom-24 left-3 z-10 rounded-xl border border-border bg-popover/90 px-3.5 py-2.5 text-sm shadow-sm backdrop-blur sm:left-4" aria-label="Relationship types">
        <p className="mb-1.5 font-medium text-foreground">Edge types</p>
        <ul className="space-y-0.5">
          {usedTypes.map(t => (
            <li key={t}>
              <button
                type="button"
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-md px-1.5 py-0.5 text-left transition-colors duration-150',
                  legendType === t ? 'bg-accent text-foreground' : 'text-muted-foreground hover:text-foreground',
                )}
                onMouseEnter={() => setLegendType(t)}
                onMouseLeave={() => setLegendType(null)}
                onFocus={() => setLegendType(t)}
                onBlur={() => setLegendType(null)}
                aria-label={`Highlight ${words(t)} relationships`}
              >
                <span className={cn('h-[3px] rounded-full transition-all duration-200', legendType === t ? 'w-6' : 'w-4')} style={{ background: edgeColour(t) }} />
                {words(t)}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
});

/** Micro-animations for the network; all switched off for reduced motion. */
const NET_CSS = `
.net-canvas .net-ease { transition: opacity 260ms ease, stroke-opacity 260ms ease, stroke-width 200ms ease; }
.net-canvas .net-pop { transform-box: fill-box; transform-origin: center; animation: net-pop 520ms cubic-bezier(.2,.9,.3,1.25) both; }
.net-canvas .net-lines { animation: net-fade 700ms ease 350ms both; }
.net-canvas .net-dot { transform-box: fill-box; transform-origin: center; transition: transform 200ms cubic-bezier(.2,.9,.3,1.3), stroke-width 200ms ease; }
.net-canvas .net-node:hover .net-dot, .net-canvas .net-node:focus-visible .net-dot { transform: scale(1.14); }
.net-canvas .net-halo { transition: opacity 220ms ease; }
.net-canvas .net-pulse { transform-box: fill-box; transform-origin: center; animation: net-pulse 1.8s ease-out infinite; }
.net-canvas .net-flow { animation: net-flow 900ms linear infinite; }
.net-canvas .net-card { animation: net-card 180ms ease-out both; }
@keyframes net-pop { from { opacity: 0; transform: scale(.3); } to { opacity: 1; transform: scale(1); } }
@keyframes net-fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes net-pulse { 0% { opacity: .7; transform: scale(1); } 100% { opacity: 0; transform: scale(1.7); } }
@keyframes net-flow { from { stroke-dashoffset: 12; } to { stroke-dashoffset: 0; } }
@keyframes net-card { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) {
  .net-canvas .net-pop, .net-canvas .net-lines, .net-canvas .net-pulse, .net-canvas .net-flow, .net-canvas .net-card { animation: none; }
  .net-canvas .net-ease, .net-canvas .net-dot, .net-canvas .net-halo { transition: none; }
}
`;
