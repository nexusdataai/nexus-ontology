/**
 * Knowledge graph explorer.
 *
 * One canvas, three ways to read the same graph:
 *   - Constellation: entities gather inside the territory of the system that
 *     owns them, so cross-system links are visible at a glance.
 *   - Lanes: one column per system, read left to right like data lineage.
 *   - Lineage: one entity in the middle, what feeds it on the left and what
 *     it feeds on the right.
 *
 * Hover or select an entity to light up its links (the dashes flow in the
 * direction of the relationship). "Trace a path" answers "how is A connected
 * to B?". The inspector on the right shows relationships, governance, the
 * data layer and live sample rows for the selected entity.
 *
 * Data: GET /api/v1/control-plane/entities/graph, /entities/{id},
 * mappingRuleService.list and virtualQueryService.previewEntity (unchanged).
 * Layout is computed once per view with d3-force and tweened; rendering is
 * plain React (SVG for links and territories, HTML for nodes).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import { mappingRuleService, type MappingRule } from '@/services/mappingRuleService';
import { virtualQueryService, type VirtualQueryResponse } from '@/services/virtualQueryService';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icon } from '@/components/ds/Icon';
import { SystemLogo, systemName, resolveSystem } from '@/components/ds/SystemLogo';
import { DetailSheet, InlineError, KeyValues, SearchInput, StatusPill } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { cn } from '@/lib/utils';
import { CHART_COLORS } from '@/components/ds/charts';
import { NetworkCanvas, type NetworkHandle } from './NetworkCanvas';

/* ------------------------------------------------------------------ types */

interface GraphNode {
  id: string;
  system: string;
  domain: string;
  riskLevel: string;
  fieldCount: number;
  isVirtual: boolean;
  fdwMappingStatus: string;
  degree: number;
  /** What the node is grouped by on the canvas: its business domain, or its system when the backend sets one. */
  group: string;
  /** Source system behind the entity (its own, or the one its mapping rules read from). Empty when none. */
  src: string;
}

interface GraphEdge {
  id: string;
  source: string | { id: string };
  target: string | { id: string };
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

interface Link { id: string; s: string; t: string; type: string; description: string }
type P = { x: number; y: number };
type Pos = Record<string, P>;
type LayoutMode = 'map' | 'network' | 'constellation' | 'lanes' | 'focus';
type InspectorTab = 'relationships' | 'fields' | 'vdl' | 'data';

/* ---------------------------------------------------------------- helpers */

const NODE_H = 36;
const pretty = (s: string) => String(s || '').replace(/_/g, ' ');
const nodeW = (id: string) => Math.max(132, Math.min(248, 86 + pretty(id).length * 7.4)); // room for icon, risk dot and link count
const endId = (e: string | { id: string }) => (typeof e === 'string' ? e : e.id);

const REL_LABEL: Record<string, string> = {
  triggers: 'triggers',
  syncs_to: 'syncs to',
  depends_on: 'depends on',
  constrained_by: 'governed by',
  owned_by: 'owned by',
};
const relLabel = (t: string) => REL_LABEL[t] || pretty(t);

const CATEGORY_LABEL: Record<string, string> = { onto_policy: 'Policy', onto_workflow: 'Workflow', onto_integration: 'Integration' };

/** Small deterministic random, so the layout is the same on every visit. */
function seeded(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/** Where a line from the centre of a pill towards (tx, ty) leaves the pill. */
function edgePoint(c: P, w: number, h: number, tx: number, ty: number, pad = 5): P {
  const dx = tx - c.x, dy = ty - c.y;
  if (dx === 0 && dy === 0) return c;
  const hw = w / 2 + pad, hh = h / 2 + pad;
  const scale = Math.min(hw / Math.abs(dx || 1e-6), hh / Math.abs(dy || 1e-6));
  return { x: c.x + dx * scale, y: c.y + dy * scale };
}

function bboxOf(pos: Pos, ids: string[]) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const id of ids) {
    const p = pos[id];
    if (!p) continue;
    const w = nodeW(id) / 2;
    x0 = Math.min(x0, p.x - w); x1 = Math.max(x1, p.x + w);
    y0 = Math.min(y0, p.y - NODE_H / 2); y1 = Math.max(y1, p.y + NODE_H / 2);
  }
  if (!Number.isFinite(x0)) return { x: 0, y: 0, w: 1, h: 1 };
  return { x: x0, y: y0, w: Math.max(1, x1 - x0), h: Math.max(1, y1 - y0) };
}

/* ---------------------------------------------------------------- layouts */

function layoutConstellation(nodes: GraphNode[], links: Link[], systems: string[], aspect = 1.6): Pos {
  const rnd = seeded(7);
  const n = Math.max(systems.length, 1);
  const R = 120 + n * 34 + nodes.length * 2.2;
  const rx = R * Math.sqrt(aspect) * 1.08, ry = (R / Math.sqrt(aspect)) * 1.02;
  const centre: Record<string, P> = {};
  systems.forEach((sys, i) => {
    const a = (i / n) * Math.PI * 2 - Math.PI / 2;
    centre[sys] = n === 1 ? { x: 0, y: 0 } : { x: Math.cos(a) * rx, y: Math.sin(a) * ry };
  });
  const sim = nodes.map(nd => {
    const c = centre[nd.group] || { x: 0, y: 0 };
    return { id: nd.id, system: nd.group, x: c.x + (rnd() - 0.5) * 120, y: c.y + (rnd() - 0.5) * 120 };
  });
  const byId = new Map(sim.map(s => [s.id, s]));
  const simLinks = links.filter(l => byId.has(l.s) && byId.has(l.t)).map(l => ({ source: l.s, target: l.t, same: byId.get(l.s)!.system === byId.get(l.t)!.system }));
  d3.forceSimulation(sim as any)
    .force('x', d3.forceX<any>(d => (centre[d.system] || { x: 0 }).x).strength(0.4))
    .force('y', d3.forceY<any>(d => (centre[d.system] || { y: 0 }).y).strength(0.5))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('link', d3.forceLink<any, any>(simLinks).id((d: any) => d.id).distance(l => (l.same ? 100 : 300)).strength(l => (l.same ? 0.2 : 0.008)))
    .force('collide', d3.forceCollide<any>(d => nodeW(d.id) * 0.42 + 10).strength(1).iterations(3))
    .stop()
    .tick(320);
  const pos: Pos = {};
  for (const s of sim) pos[s.id] = { x: s.x, y: s.y };
  return pos;
}

/**
 * Map: each group (domain or system) is a tidy box listing its entities, most
 * connected first. Boxes are laid out as masonry columns that fill the canvas
 * width, so names stay readable at normal size instead of a scattered ring
 * that has to be zoomed far out.
 */
const MAP_COL = 252, MAP_ROW = 46, MAP_PAD_X = 22, MAP_PAD_TOP = 56, MAP_PAD_BOTTOM = 20, MAP_GAP = 32;
function layoutMap(nodes: GraphNode[], groups: string[], availW: number): Pos {
  const pos: Pos = {};
  const boxW = MAP_COL + MAP_PAD_X * 2;
  const columns = Math.max(1, Math.floor((availW + MAP_GAP) / (boxW + MAP_GAP)));
  const heights = new Array(columns).fill(0);
  const boxes = groups
    .map(g => ({ g, members: nodes.filter(nd => nd.group === g).sort((a, b) => b.degree - a.degree || a.id.localeCompare(b.id)) }))
    .filter(b => b.members.length > 0)
    .sort((a, b) => b.members.length - a.members.length);
  for (const b of boxes) {
    // Next box goes in the shortest column.
    const c = heights.indexOf(Math.min(...heights));
    const x = c * (boxW + MAP_GAP), y = heights[c];
    b.members.forEach((nd, i) => {
      pos[nd.id] = { x: x + MAP_PAD_X + MAP_COL / 2, y: y + MAP_PAD_TOP + i * MAP_ROW + NODE_H / 2 };
    });
    heights[c] = y + MAP_PAD_TOP + b.members.length * MAP_ROW + MAP_PAD_BOTTOM + MAP_GAP;
  }
  return pos;
}

function layoutLanes(nodes: GraphNode[], systems: string[]): Pos {
  const pos: Pos = {};
  const laneW = 244, rowH = 50;
  const groups = systems.map(sys => nodes.filter(nd => nd.group === sys).sort((a, b) => a.domain.localeCompare(b.domain) || b.degree - a.degree));
  groups.forEach((g, i) => {
    const x = (i - (systems.length - 1) / 2) * laneW;
    g.forEach((nd, j) => { pos[nd.id] = { x, y: j * rowH }; });
  });
  return pos;
}

/** Signed distance from the centre: negative = upstream (feeds it), positive = downstream. */
function lineageLevels(links: Link[], centreId: string): Map<string, number> {
  const lv = new Map<string, number>([[centreId, 0]]);
  for (const dir of [1, -1]) {
    let frontier = [centreId];
    let d = 0;
    while (frontier.length && Math.abs(d) < 3) {
      d += dir;
      const next: string[] = [];
      for (const id of frontier) {
        for (const l of links) {
          const other = dir === 1 ? (l.s === id ? l.t : null) : (l.t === id ? l.s : null);
          if (other && !lv.has(other)) { lv.set(other, d); next.push(other); }
        }
      }
      frontier = next;
    }
  }
  return lv;
}

const LINEAGE_COL = 270, LINEAGE_ROW = 50;

function layoutFocus(nodes: GraphNode[], levels: Map<string, number>): Pos {
  const pos: Pos = {};
  const cols = new Map<number, GraphNode[]>();
  const rest: GraphNode[] = [];
  for (const nd of nodes) {
    const lv = levels.get(nd.id);
    if (lv === undefined) { rest.push(nd); continue; }
    if (!cols.has(lv)) cols.set(lv, []);
    cols.get(lv)!.push(nd);
  }
  let tallest = 1;
  for (const [lv, col] of cols) {
    col.sort((a, b) => b.degree - a.degree || a.id.localeCompare(b.id));
    tallest = Math.max(tallest, col.length);
    col.forEach((nd, j) => { pos[nd.id] = { x: lv * LINEAGE_COL, y: (j - (col.length - 1) / 2) * LINEAGE_ROW }; });
  }
  const lvs = [...cols.keys()];
  const midX = ((Math.min(...lvs) + Math.max(...lvs)) / 2) * LINEAGE_COL;
  const perRow = Math.max(3, Math.min(6, Math.ceil(Math.sqrt(rest.length * 2.4))));
  rest.sort((a, b) => a.group.localeCompare(b.group) || a.id.localeCompare(b.id));
  rest.forEach((nd, i) => {
    const r = Math.floor(i / perRow), c = i % perRow;
    const inRow = Math.min(perRow, rest.length - r * perRow);
    pos[nd.id] = { x: midX + (c - (inRow - 1) / 2) * 232, y: (tallest * LINEAGE_ROW) / 2 + 96 + r * LINEAGE_ROW };
  });
  return pos;
}

function shortestPath(links: Link[], from: string, to: string): string[] | null {
  if (from === to) return [from];
  const adj = new Map<string, string[]>();
  for (const l of links) {
    if (!adj.has(l.s)) adj.set(l.s, []);
    if (!adj.has(l.t)) adj.set(l.t, []);
    adj.get(l.s)!.push(l.t); adj.get(l.t)!.push(l.s);
  }
  const prev = new Map<string, string>();
  const seen = new Set([from]);
  const queue = [from];
  while (queue.length) {
    const cur = queue.shift()!;
    for (const nb of adj.get(cur) || []) {
      if (seen.has(nb)) continue;
      seen.add(nb); prev.set(nb, cur);
      if (nb === to) {
        const path = [to];
        let p = to;
        while (prev.has(p)) { p = prev.get(p)!; path.unshift(p); }
        return path;
      }
      queue.push(nb);
    }
  }
  return null;
}

function useIsDesktop() {
  const [is, setIs] = useState(() => (typeof window === 'undefined' ? true : window.matchMedia('(min-width: 1024px)').matches));
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)');
    const on = () => setIs(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return is;
}

/* ============================================================== component */

export default function KnowledgeGraphView() {
  const nav = useNavigate();
  const isDesktop = useIsDesktop();
  const wrapRef = useRef<HTMLDivElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<HTMLDivElement, unknown> | null>(null);
  const netRef = useRef<NetworkHandle>(null);

  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [systemFilters, setSystemFilters] = useState<Set<string>>(new Set());
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [groupBy, setGroupBy] = useState<'domain' | 'system'>('domain');

  const [rightTab, setRightTab] = useState<InspectorTab>('relationships');
  const [entityDetail, setEntityDetail] = useState<any | null>(null);
  const [entityMappingRules, setEntityMappingRules] = useState<MappingRule[]>([]);
  const [vdlLoading, setVdlLoading] = useState(false);
  const [previewData, setPreviewData] = useState<VirtualQueryResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const [mode, setMode] = useState<LayoutMode>('network');
  const modeRef = useRef<LayoutMode>('network');
  modeRef.current = mode;
  const [focusId, setFocusId] = useState<string | null>(null);
  const [crossOnly, setCrossOnly] = useState(false);
  const [traceTo, setTraceTo] = useState<string | null>(null);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const [pos, setPos] = useState<Pos>({});
  const posRef = useRef<Pos>({});
  const [size, setSize] = useState({ w: 0, h: 0 });

  /* ------------------------------------------------------------ loading */

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const [raw, rules] = await Promise.all([
        apiClient.get<GraphData>('/api/v1/control-plane/entities/graph'),
        mappingRuleService.list().catch(() => [] as MappingRule[]),
      ]);
      // Canonical entities are source-agnostic: the backend leaves `system`
      // empty and binds sources through mapping rules. Group those by business
      // domain and take the source system from the entity's active rules.
      const votes = new Map<string, Map<string, number>>();
      for (const r of rules) {
        if (!r.virtualEntity || !r.sourceSystem || r.status === 'inactive') continue;
        const key = resolveSystem(r.sourceSystem).key;
        const m = votes.get(r.virtualEntity) || new Map<string, number>();
        m.set(key, (m.get(key) || 0) + 1);
        votes.set(r.virtualEntity, m);
      }
      const ruleSource = (id: string) => [...(votes.get(id) || new Map<string, number>()).entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || '';
      const rawNodes = raw.nodes || [];
      const withSystem = rawNodes.filter(nd => nd.system).length;
      const by: 'domain' | 'system' = rawNodes.length > 0 && withSystem / rawNodes.length >= 0.6 ? 'system' : 'domain';
      const nodes = rawNodes.map(nd => ({
        ...nd,
        domain: nd.domain || 'Other',
        src: nd.system || ruleSource(nd.id),
        group: by === 'system' ? (nd.system || 'unassigned') : (nd.domain || 'Other'),
      }));
      setGroupBy(by);
      setGraphData({ ...raw, nodes, edges: raw.edges || [] });
      setSystemFilters(new Set(nodes.map(nd => nd.group)));
    } catch { setGraphData(null); setLoadError(true); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  useEffect(() => {
    if (!selectedNode) {
      setEntityDetail(null);
      setEntityMappingRules([]);
      setPreviewData(null);
      setTraceTo(null);
      return;
    }
    setEntityDetail(null);
    apiClient.get(`/api/v1/control-plane/entities/${encodeURIComponent(selectedNode.id)}`)
      .then(setEntityDetail).catch(() => setEntityDetail(null));

    setPreviewData(null);
    setPreviewLoading(true);
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
    try {
      const data = await virtualQueryService.previewEntity(selectedNode.id, 10);
      setPreviewData(data);
    } catch { setPreviewData(null); }
    finally { setPreviewLoading(false); }
  };

  /* -------------------------------------------------------- derived data */

  const allLinks: Link[] = useMemo(
    () => (graphData?.edges || []).map(e => ({ id: e.id, s: endId(e.source), t: endId(e.target), type: e.type, description: e.description })),
    [graphData],
  );
  const systems = useMemo(() => {
    const count = new Map<string, number>();
    for (const nd of graphData?.nodes || []) count.set(nd.group, (count.get(nd.group) || 0) + 1);
    return [...count.entries()].sort((a, b) => b[1] - a[1]).map(([sys, n]) => ({ sys, n }));
  }, [graphData]);
  const systemOfNode = useMemo(() => new Map((graphData?.nodes || []).map(nd => [nd.id, nd.group])), [graphData]);
  const groupLabel = useCallback((g: string) => (groupBy === 'domain' ? g : systemName(g)), [groupBy]);
  const groupColour = useCallback((g: string) => {
    const i = systems.findIndex(x => x.sys === g);
    return CHART_COLORS[(i < 0 ? 0 : i) % CHART_COLORS.length];
  }, [systems]);

  const nodes = useMemo(() => (graphData?.nodes || []).filter(nd => systemFilters.has(nd.group)), [graphData, systemFilters]);
  const nodeIds = useMemo(() => new Set(nodes.map(nd => nd.id)), [nodes]);
  const links = useMemo(
    () => allLinks.filter(l => nodeIds.has(l.s) && nodeIds.has(l.t) && (!crossOnly || systemOfNode.get(l.s) !== systemOfNode.get(l.t))),
    [allLinks, nodeIds, crossOnly, systemOfNode],
  );
  const visibleSystems = useMemo(() => systems.map(s => s.sys).filter(s => systemFilters.has(s)), [systems, systemFilters]);
  const crossCount = useMemo(() => allLinks.filter(l => systemOfNode.get(l.s) !== systemOfNode.get(l.t)).length, [allLinks, systemOfNode]);

  const centreId = useMemo(() => {
    if (focusId && nodeIds.has(focusId)) return focusId;
    return [...nodes].sort((a, b) => b.degree - a.degree)[0]?.id || null;
  }, [focusId, nodes, nodeIds]);

  const lineage = useMemo(
    () => (centreId ? lineageLevels(allLinks.filter(l => nodeIds.has(l.s) && nodeIds.has(l.t)), centreId) : new Map<string, number>()),
    [allLinks, nodeIds, centreId],
  );

  const aspect = size.w && size.h ? Math.max(1, Math.min(2.6, Math.round((size.w / Math.max(size.h - 120, 200)) * 4) / 4)) : 1.75;

  const target: Pos = useMemo(() => {
    if (nodes.length === 0) return {};
    if (mode === 'lanes') return layoutLanes(nodes, visibleSystems);
    if (mode === 'network') return {};
    if (mode === 'map') return layoutMap(nodes, visibleSystems, size.w ? Math.max(560, size.w - 96) : 1200);
    if (mode === 'focus' && centreId) return layoutFocus(nodes, lineage);
    return layoutConstellation(nodes, allLinks.filter(l => nodeIds.has(l.s) && nodeIds.has(l.t)), visibleSystems, aspect);
  }, [nodes, nodeIds, allLinks, visibleSystems, mode, centreId, aspect, lineage, mode === 'map' ? Math.round(size.w / 120) : 0]);

  /* -------------------------------------------------- tween to the layout */

  useEffect(() => {
    const from = posRef.current;
    const ids = Object.keys(target);
    if (ids.length === 0) { posRef.current = {}; setPos({}); return; }
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const start = performance.now();
    const dur = reduce ? 0 : 650;
    let raf = 0;
    const step = (now: number) => {
      const t = dur === 0 ? 1 : Math.min(1, (now - start) / dur);
      const e = d3.easeCubicOut(t);
      const next: Pos = {};
      for (const id of ids) {
        const a = from[id] || { x: target[id].x * 0.2, y: target[id].y * 0.2 };
        next[id] = { x: a.x + (target[id].x - a.x) * e, y: a.y + (target[id].y - a.y) * e };
      }
      posRef.current = next;
      setPos(next);
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target]);

  /* --------------------------------------------------------- pan and zoom */

  const ready = !loading && !!graphData && graphData.nodes.length > 0;

  useEffect(() => {
    const el = wrapRef.current;
    if (!ready || !el) return;
    const zoom = d3.zoom<HTMLDivElement, unknown>()
      .scaleExtent([0.25, 2.4])
      .filter((event: any) => {
        if (event.type === 'wheel') return true;
        if (event.button) return false;
        return !(event.target as Element).closest?.('[data-graph-ui]');
      })
      .on('zoom', (event) => setView({ x: event.transform.x, y: event.transform.y, k: event.transform.k }));
    zoomRef.current = zoom;
    d3.select(el).call(zoom).on('dblclick.zoom', null);
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => { ro.disconnect(); d3.select(el).on('.zoom', null); };
  }, [ready]);

  const fit = useCallback((to: Pos, animate = true) => {
    const el = wrapRef.current;
    if (!el || !zoomRef.current) return;
    const ids = Object.keys(to);
    if (ids.length === 0) return;
    const b = bboxOf(to, ids);
    const W = el.clientWidth, H = el.clientHeight;
    if (!W || !H) return;
    const fitAll = Math.min(1.15, (W - 72) / b.w, (H - 200) / b.h);
    const fitWidth = Math.min(1, (W - 72) / b.w);
    // The network is meant to be seen whole; the boxed layouts stay readable and scroll.
    const minK = modeRef.current === 'network' ? 0.5 : 0.62;
    const k = fitAll >= minK ? fitAll : Math.max(minK, fitWidth);
    const tx = W / 2 - 16 - (b.x + b.w / 2) * k;
    const tallerThanView = b.h * k > H - 200;
    const ty = tallerThanView ? 96 - b.y * k : H / 2 + 12 - (b.y + b.h / 2) * k;
    const t = d3.zoomIdentity.translate(tx, ty).scale(k);
    const sel = d3.select(el);
    if (animate) sel.transition().duration(650).ease(d3.easeCubicOut).call(zoomRef.current.transform as any, t);
    else sel.call(zoomRef.current.transform as any, t);
  }, []);

  const fitted = useRef(false);
  useEffect(() => {
    if (!ready || size.w === 0) return;
    fit(target, fitted.current);
    fitted.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, ready, size.w > 0, isDesktop && !!selectedNode]);

  const zoomBy = (factor: number) => {
    const el = wrapRef.current;
    if (el && zoomRef.current) d3.select(el).transition().duration(250).call(zoomRef.current.scaleBy as any, factor);
  };

  /* ------------------------------------------------------- node dragging */

  const drag = useRef<{ id: string; x: number; y: number; moved: boolean } | null>(null);
  const onNodePointerDown = (e: React.PointerEvent, id: string) => {
    if (e.button !== 0) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    drag.current = { id, x: e.clientX, y: e.clientY, moved: false };
  };
  const onNodePointerMove = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (!d.moved && Math.hypot(dx, dy) < 4) return;
    d.moved = true; d.x = e.clientX; d.y = e.clientY;
    const cur = posRef.current[d.id];
    if (!cur) return;
    const next = { ...posRef.current, [d.id]: { x: cur.x + dx / view.k, y: cur.y + dy / view.k } };
    posRef.current = next;
    setPos(next);
  };
  const onNodePointerUp = (e: React.PointerEvent, nd: GraphNode) => {
    const d = drag.current;
    drag.current = null;
    try { (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId); } catch { /* not captured */ }
    if (d && !d.moved) selectNode(nd);
  };

  /* ----------------------------------------------------------- selection */

  const selectNode = (nd: GraphNode | null) => {
    setSelectedNode(nd);
    setTraceTo(null);
    if (nd && mode === 'focus') setFocusId(nd.id);
  };
  const selectById = (id: string) => {
    const nd = graphData?.nodes.find(x => x.id === id);
    if (!nd) return;
    if (!systemFilters.has(nd.group)) setSystemFilters(prev => new Set(prev).add(nd.group));
    selectNode(nd);
  };
  const focusOn = (id: string) => { setFocusId(id); setMode('focus'); };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && selectedNode && isDesktop) selectNode(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedNode, isDesktop]);

  const toggleSystem = (sys: string) => {
    setSystemFilters(prev => {
      const next = new Set(prev);
      if (next.has(sys)) { if (next.size > 1) next.delete(sys); } else next.add(sys);
      return next;
    });
  };

  /* ------------------------------------------------------- highlight sets */

  const activeId = hoveredNode || selectedNode?.id || null;
  const path = useMemo(
    () => (selectedNode && traceTo ? shortestPath(allLinks.filter(l => nodeIds.has(l.s) && nodeIds.has(l.t)), selectedNode.id, traceTo) : null),
    [selectedNode, traceTo, allLinks, nodeIds],
  );
  const pathSet = useMemo(() => new Set(path || []), [path]);
  const pathPairs = useMemo(() => {
    const s = new Set<string>();
    if (path) for (let i = 0; i < path.length - 1; i++) { s.add(`${path[i]}|${path[i + 1]}`); s.add(`${path[i + 1]}|${path[i]}`); }
    return s;
  }, [path]);
  const neighbours = useMemo(() => {
    const s = new Set<string>();
    if (activeId) { s.add(activeId); for (const l of links) { if (l.s === activeId) s.add(l.t); if (l.t === activeId) s.add(l.s); } }
    return s;
  }, [activeId, links]);

  const q = searchQuery.trim().toLowerCase();
  const matches = (nd: GraphNode) => !q || pretty(nd.id).toLowerCase().includes(q) || nd.domain.toLowerCase().includes(q) || (!!nd.src && systemName(nd.src).toLowerCase().includes(q));
  const matchCount = q ? nodes.filter(matches).length : 0;

  const nodeState = (nd: GraphNode): 'lit' | 'dim' | 'normal' => {
    if (path && !hoveredNode) return pathSet.has(nd.id) ? 'lit' : 'dim';
    if (activeId) return neighbours.has(nd.id) ? 'lit' : 'dim';
    if (q) return matches(nd) ? 'lit' : 'dim';
    if (mode === 'focus' && !lineage.has(nd.id)) return 'dim';
    return 'normal';
  };
  const linkLit = (l: Link) => {
    if (path && !hoveredNode) return pathPairs.has(`${l.s}|${l.t}`);
    return !!activeId && (l.s === activeId || l.t === activeId);
  };
  const anyFocus = !!activeId || !!path;

  /* ------------------------------------------------------------ geometry */

  const linkGeo = (l: Link) => {
    const a = pos[l.s], b = pos[l.t];
    if (!a || !b) return null;
    const p1 = edgePoint(a, nodeW(l.s), NODE_H, b.x, b.y);
    const p2 = edgePoint(b, nodeW(l.t), NODE_H, a.x, a.y, 9);
    const dx = p2.x - p1.x, dy = p2.y - p1.y;
    const dist = Math.hypot(dx, dy) || 1;
    if (mode !== 'constellation' && Math.abs(a.x - b.x) > 1) {
      const dir = b.x > a.x ? 1 : -1;
      const s = { x: a.x + dir * (nodeW(l.s) / 2 + 4), y: a.y };
      const t = { x: b.x - dir * (nodeW(l.t) / 2 + 9), y: b.y };
      const c = Math.max(40, Math.abs(t.x - s.x) * 0.45);
      return { d: `M${s.x},${s.y} C${s.x + dir * c},${s.y} ${t.x - dir * c},${t.y} ${t.x},${t.y}`, mid: { x: (s.x + t.x) / 2, y: (s.y + t.y) / 2 } };
    }
    const bend = Math.min(46, dist * 0.14) * (l.s < l.t ? 1 : -1);
    const cx = (p1.x + p2.x) / 2 - (dy / dist) * bend;
    const cy = (p1.y + p2.y) / 2 + (dx / dist) * bend;
    return { d: `M${p1.x},${p1.y} Q${cx},${cy} ${p2.x},${p2.y}`, mid: { x: (p1.x + 2 * cx + p2.x) / 4, y: (p1.y + 2 * cy + p2.y) / 4 } };
  };

  const territories = useMemo(() => {
    if (mode === 'focus' || mode === 'network') return [];
    return visibleSystems.map(sys => {
      const members = nodes.filter(nd => nd.group === sys && pos[nd.id]);
      if (members.length === 0) return null;
      const b = bboxOf(pos, members.map(m => m.id));
      if (mode === 'lanes' || mode === 'map') {
        const padX = 26, padTop = 54, padBottom = 22;
        return { sys, count: members.length, rect: { x: b.x - padX, y: b.y - padTop, w: b.w + padX * 2, h: b.h + padTop + padBottom }, label: { x: b.x + b.w / 2, y: b.y - 30 } };
      }
      const pad = 30;
      const pts: [number, number][] = [];
      for (const m of members) {
        const p = pos[m.id], w = nodeW(m.id) / 2 + pad, h = NODE_H / 2 + pad;
        pts.push([p.x - w, p.y - h], [p.x + w, p.y - h], [p.x + w, p.y + h], [p.x - w, p.y + h]);
      }
      const hull = d3.polygonHull(pts) || pts;
      const d = d3.line().curve(d3.curveCatmullRomClosed.alpha(0.7))(hull) || '';
      return { sys, count: members.length, d, label: { x: b.x + b.w / 2, y: b.y - pad - 12 } };
    }).filter(Boolean) as { sys: string; count: number; d?: string; rect?: { x: number; y: number; w: number; h: number }; label: P }[];
  }, [mode, visibleSystems, nodes, pos]);

  const lineageLabels = useMemo(() => {
    if (mode !== 'focus') return [];
    const top = new Map<number, number>();
    let restTop = Infinity, restX = 0, restN = 0;
    for (const nd of nodes) {
      const p = pos[nd.id];
      if (!p) continue;
      const lv = lineage.get(nd.id);
      if (lv === undefined) { restTop = Math.min(restTop, p.y); restX += p.x; restN++; continue; }
      top.set(lv, Math.min(top.get(lv) ?? Infinity, p.y));
    }
    const out: { key: string; x: number; y: number; text: string }[] = [];
    for (const [lv, y] of top) {
      if (lv === 0) continue;
      const steps = Math.abs(lv);
      out.push({ key: `lv${lv}`, x: lv * LINEAGE_COL, y: y - 38, text: `${lv < 0 ? 'Upstream' : 'Downstream'}${steps > 1 ? `, ${steps} steps` : ''}` });
    }
    if (restN > 0) out.push({ key: 'rest', x: restX / restN, y: restTop - 38, text: 'Not in this lineage' });
    return out;
  }, [mode, nodes, pos, lineage]);

  const world = useMemo(() => bboxOf(pos, Object.keys(pos)), [pos]);

  /* --------------------------------------------------------------- states */

  if (loading) {
    return (
      <div className="relative h-full overflow-hidden bg-background" aria-busy="true">
        <div className="absolute left-4 top-4 flex gap-2"><Skeleton className="h-9 w-64" /><Skeleton className="h-9 w-72" /></div>
        <div className="flex h-full items-center justify-center gap-10">
          {[150, 210, 130].map((s, i) => <Skeleton key={i} className="rounded-full" style={{ width: s, height: s }} />)}
        </div>
      </div>
    );
  }
  if (loadError) {
    return <div className="mx-auto max-w-xl p-8"><InlineError onRetry={loadGraph}>The knowledge graph could not be loaded.</InlineError></div>;
  }
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <EmptyState icon="graph" title="The graph is empty" description="Run the knowledge pipeline first. Entities and their relationships appear here once they are indexed." />
      </div>
    );
  }

  const nodeEdges = selectedNode ? allLinks.filter(l => l.s === selectedNode.id || l.t === selectedNode.id) : [];
  const worldTransform = `translate(${view.x}px, ${view.y}px) scale(${view.k})`;

  const inspector = selectedNode && (
    <Inspector
      node={selectedNode}
      detail={entityDetail}
      edges={nodeEdges}
      allNodes={graphData.nodes}
      tab={rightTab}
      onTab={setRightTab}
      rules={entityMappingRules}
      rulesLoading={vdlLoading}
      preview={previewData}
      previewLoading={previewLoading}
      onRefreshPreview={handlePreviewData}
      onSelect={selectById}
      onFocus={() => focusOn(selectedNode.id)}
      onOpenEntity={() => nav('/ai-stack/data-plane?tab=virtualdata')}
      traceTo={traceTo}
      onTrace={setTraceTo}
      path={path}
    />
  );

  return (
    <div className="flex h-full min-h-0 bg-background">
      {/* ------------------------------------------------------------ canvas */}
      <div
        ref={wrapRef}
        className="relative min-w-0 flex-1 cursor-grab touch-none select-none overflow-hidden active:cursor-grabbing"
        style={{
          backgroundImage: 'radial-gradient(hsl(var(--border-strong) / 0.55) 1px, transparent 1px)',
          backgroundSize: `${22 * view.k}px ${22 * view.k}px`,
          backgroundPosition: `${view.x}px ${view.y}px`,
        }}
        onClick={(e) => { if (e.target === e.currentTarget) selectNode(null); }}
      >
        {mode === 'network' && (
          <div data-graph-ui className="absolute inset-0">
            <NetworkCanvas
              ref={netRef}
              nodes={nodes.map(nd => ({ id: nd.id, group: nd.group, domain: nd.domain || '', degree: nd.degree, fieldCount: nd.fieldCount, riskLevel: nd.riskLevel }))}
              links={links}
              colourOf={groupColour}
              groupLabel={groupLabel}
              selectedId={selectedNode?.id || null}
              onSelect={(id) => (id ? selectById(id) : selectNode(null))}
              query={q}
            />
          </div>
        )}

        {/* links and territories */}
        <svg className={cn('pointer-events-none absolute inset-0 h-full w-full', mode === 'network' && 'hidden')} aria-hidden="true">
          <defs>
            <marker id="kg-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M1,1 L9,5 L1,9" fill="none" stroke="hsl(var(--border-strong))" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </marker>
            <marker id="kg-arrow-lit" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M1,1 L9,5 L1,9" fill="none" stroke="hsl(var(--brand-hi))" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </marker>
          </defs>
          <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
            {territories.map(t => t.d ? (
              <path key={t.sys} d={t.d} fill="hsl(var(--foreground) / 0.022)" stroke="hsl(var(--border-strong))" strokeWidth={1} strokeDasharray="2 6" strokeLinecap="round" />
            ) : t.rect ? (
              <rect key={t.sys} x={t.rect.x} y={t.rect.y} width={t.rect.w} height={t.rect.h} rx={18} fill="hsl(var(--foreground) / 0.022)" stroke="hsl(var(--border))" strokeWidth={1} />
            ) : null)}
            {links.map(l => {
              const g = linkGeo(l);
              if (!g) return null;
              const lit = linkLit(l);
              return (
                <g key={l.id} opacity={anyFocus ? (lit ? 1 : 0.22) : q ? 0.3 : mode === 'focus' && !(lineage.has(l.s) && lineage.has(l.t)) ? 0.1 : 0.9} style={{ transition: 'opacity 200ms ease' }}>
                  <path d={g.d} fill="none" stroke={lit ? 'hsl(var(--brand-hi))' : 'hsl(var(--border-strong))'} strokeWidth={lit ? 1.6 : 1.1} markerEnd={`url(#${lit ? 'kg-arrow-lit' : 'kg-arrow'})`} />
                  {lit && <path d={g.d} fill="none" stroke="hsl(var(--background))" strokeWidth={1.6} className="flow-line" opacity={0.75} />}
                </g>
              );
            })}
          </g>
        </svg>

        {/* nodes and labels */}
        <div className={cn('absolute left-0 top-0 h-0 w-0', mode === 'network' && 'hidden')} style={{ transform: worldTransform, transformOrigin: '0 0' }}>
          {territories.map(t => (
            <div key={t.sys} className="pointer-events-none absolute flex -translate-x-1/2 -translate-y-1/2 items-center gap-2 whitespace-nowrap" style={{ left: t.label.x, top: t.label.y }}>
              {groupBy === 'system' && <SystemLogo system={t.sys} size="sm" />}
              <span className="text-sm font-medium text-foreground">{groupLabel(t.sys)}</span>
              <span className="num text-xs text-muted-foreground">{t.count}</span>
            </div>
          ))}

          {lineageLabels.map(l => (
            <span key={l.key} className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap text-xs font-medium text-muted-foreground" style={{ left: l.x, top: l.y }}>{l.text}</span>
          ))}

          {links.filter(l => linkLit(l)).map(l => {
            const g = linkGeo(l);
            if (!g) return null;
            return (
              <span key={`lbl-${l.id}`} className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 animate-fade-in whitespace-nowrap rounded-md border border-border bg-popover px-1.5 py-0.5 text-xs text-muted-foreground shadow-xs" style={{ left: g.mid.x, top: g.mid.y }}>
                {relLabel(l.type)}
              </span>
            );
          })}

          {nodes.map(nd => {
            const p = pos[nd.id];
            if (!p) return null;
            const w = nodeW(nd.id);
            const state = nodeState(nd);
            const selected = selectedNode?.id === nd.id;
            const isCentre = mode === 'focus' && nd.id === centreId;
            const unmapped = nd.fdwMappingStatus && nd.fdwMappingStatus !== 'mapped';
            return (
              <button
                key={nd.id}
                type="button"
                data-graph-ui
                onPointerDown={(e) => onNodePointerDown(e, nd.id)}
                onPointerMove={onNodePointerMove}
                onPointerUp={(e) => onNodePointerUp(e, nd)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectNode(nd); } }}
                onMouseEnter={() => setHoveredNode(nd.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onFocus={() => setHoveredNode(nd.id)}
                onBlur={() => setHoveredNode(null)}
                aria-pressed={selected}
                aria-label={`${pretty(nd.id)}, ${groupLabel(nd.group)}, ${nd.degree} links`}
                className={cn(
                  'absolute flex cursor-pointer items-center gap-2 rounded-full border bg-card pl-2.5 pr-3 text-left shadow-xs outline-none',
                  'transition-[opacity,box-shadow,border-color,background-color] duration-200',
                  'hover:border-brand/70 hover:shadow-md focus-visible:ring-2 focus-visible:ring-ring',
                  unmapped ? 'border-dashed border-border-strong' : 'border-border-strong',
                  selected && 'border-brand bg-accent shadow-md ring-2 ring-brand/30',
                  isCentre && !selected && 'border-brand/70',
                  state === 'dim' && 'opacity-45',
                )}
                style={{ left: p.x - w / 2, top: p.y - NODE_H / 2, width: w, height: NODE_H, zIndex: selected ? 3 : state === 'lit' ? 2 : 1 }}
              >
                {nd.src ? <SystemLogo system={nd.src} size="xs" /> : <Icon name="layers" className="h-3.5 w-3.5 shrink-0 text-subtle-foreground" />}
                <span className={cn('min-w-0 flex-1 truncate text-sm text-foreground', (selected || nd.degree >= 5) && 'font-medium')}>{pretty(nd.id)}</span>
                {nd.riskLevel === 'high' && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-destructive" title="High risk" />}
                <span className="num shrink-0 text-xs text-muted-foreground">{nd.degree}</span>
              </button>
            );
          })}
        </div>

        {/* toolbar */}
        <div data-graph-ui className="pointer-events-none absolute inset-x-3 top-3 flex flex-wrap items-start gap-2 sm:inset-x-4 sm:top-4">
          <div className="pointer-events-auto flex items-center gap-1 rounded-xl border border-border bg-popover/95 p-1 shadow-md backdrop-blur">
            <SearchInput value={searchQuery} onChange={setSearchQuery} placeholder="Find an entity" className="w-44 sm:w-56 [&_input]:h-8 [&_input]:border-0 [&_input]:bg-transparent [&_input]:shadow-none" />
            {q && <span className="num pr-2 text-xs text-muted-foreground">{matchCount} found</span>}
          </div>

          <div className="pointer-events-auto flex items-center rounded-xl border border-border bg-popover/95 p-1 shadow-md backdrop-blur" role="tablist" aria-label="Graph layout">
            {([
              { id: 'network', label: 'Network', icon: 'network' },
              { id: 'map', label: 'Map', icon: 'apps' },
              { id: 'lanes', label: 'Lanes', icon: 'layers' },
              { id: 'focus', label: 'Lineage', icon: 'route' },
              { id: 'constellation', label: 'Clusters', icon: 'target' },
            ] as const).map(m => (
              <button
                key={m.id}
                type="button"
                role="tab"
                aria-selected={mode === m.id}
                onClick={() => { if (m.id === 'focus' && selectedNode) setFocusId(selectedNode.id); setMode(m.id); }}
                className={cn(
                  'flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  mode === m.id ? 'bg-accent font-medium text-foreground' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon name={m.icon} className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">{m.label}</span>
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setCrossOnly(v => !v)}
            aria-pressed={crossOnly}
            className={cn(
              'pointer-events-auto flex h-10 items-center gap-2 rounded-xl border bg-popover/95 px-3 text-sm shadow-md backdrop-blur transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              crossOnly ? 'border-brand/60 text-foreground' : 'border-border text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon name="shuffle" className={cn('h-3.5 w-3.5', crossOnly && 'text-primary dark:text-brand-hi')} />
            <span className="hidden md:inline">{groupBy === 'domain' ? 'Cross-domain links' : 'Cross-system links'}</span>
            <span className="num text-xs">{crossCount}</span>
          </button>
        </div>

        {/* systems */}
        <div data-graph-ui className="pointer-events-none absolute inset-x-3 bottom-3 flex items-end justify-between gap-3 sm:inset-x-4 sm:bottom-4">
          <div className="pointer-events-auto flex max-w-full flex-col gap-2">
            <div className="scroll-thin flex max-w-[calc(100vw-2rem)] items-center gap-1 overflow-x-auto rounded-xl border border-border bg-popover/95 p-1 shadow-md backdrop-blur lg:max-w-[640px]">
              {systems.map(({ sys, n }) => {
                const on = systemFilters.has(sys);
                return (
                  <button
                    key={sys}
                    type="button"
                    onClick={() => toggleSystem(sys)}
                    aria-pressed={on}
                    title={on ? `Hide ${groupLabel(sys)}` : `Show ${groupLabel(sys)}`}
                    className={cn(
                      'flex h-8 shrink-0 items-center gap-1.5 rounded-lg px-2 text-sm transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      on ? 'text-foreground hover:bg-accent' : 'text-subtle-foreground opacity-50 grayscale hover:opacity-80',
                    )}
                  >
                    {mode === 'network' && <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: groupColour(sys) }} aria-hidden="true" />}
                    {groupBy === 'system' && mode !== 'network' && <SystemLogo system={sys} size="xs" />}
                    <span className={cn('whitespace-nowrap', groupBy === 'system' && 'hidden sm:inline', !on && 'line-through')}>{groupLabel(sys)}</span>
                    <span className="num text-xs text-muted-foreground">{n}</span>
                  </button>
                );
              })}
            </div>
            <p className="hidden px-1 text-xs text-muted-foreground md:block">
              <span className="num text-foreground">{nodes.length}</span> entities, <span className="num text-foreground">{links.length}</span> relationships. Drag to move, scroll to zoom, select an entity to inspect it.
            </p>
          </div>

          <div className="pointer-events-auto absolute bottom-[72px] right-0 flex shrink-0 flex-col items-end gap-2 md:bottom-[64px]">
            <div className="flex flex-col rounded-xl border border-border bg-popover/95 p-1 shadow-md backdrop-blur">
              {([
                { label: 'Zoom in', icon: 'plus', run: () => (mode === 'network' ? netRef.current?.zoomBy(1.35) : zoomBy(1.35)) },
                { label: 'Zoom out', icon: 'minus', run: () => (mode === 'network' ? netRef.current?.zoomBy(0.74) : zoomBy(0.74)) },
                { label: 'Fit to screen', icon: 'expand', run: () => (mode === 'network' ? netRef.current?.fit() : fit(posRef.current)) },
              ] as const).map(b => (
                <button key={b.label} type="button" onClick={b.run} aria-label={b.label} title={b.label}
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <Icon name={b.icon} className="h-3.5 w-3.5" />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* minimap */}
        <svg data-graph-ui className={cn('pointer-events-none absolute right-3 top-3 hidden h-[92px] w-[136px] rounded-xl border border-border bg-popover/95 shadow-md backdrop-blur sm:right-4 sm:top-4', mode !== 'network' && '2xl:block')} viewBox={`${world.x - 60} ${world.y - 60} ${world.w + 120} ${world.h + 120}`} preserveAspectRatio="xMidYMid meet" aria-hidden="true">
              {nodes.map(nd => pos[nd.id] && (
                <rect key={nd.id} x={pos[nd.id].x - 26} y={pos[nd.id].y - 9} width={52} height={18} rx={9}
                  fill={selectedNode?.id === nd.id ? 'hsl(var(--brand-hi))' : 'hsl(var(--muted-foreground))'} opacity={selectedNode?.id === nd.id ? 1 : 0.45} />
              ))}
              {size.w > 0 && (
                <rect x={-view.x / view.k} y={-view.y / view.k} width={size.w / view.k} height={size.h / view.k} fill="hsl(var(--brand-hi) / 0.08)" stroke="hsl(var(--brand-hi))" strokeWidth={Math.max(2, 2 / view.k)} rx={8} vectorEffect="non-scaling-stroke" />
              )}
            </svg>
        {/* path result */}
        {selectedNode && traceTo && (
          <div data-graph-ui className="pointer-events-auto absolute left-1/2 top-[68px] z-10 max-w-[min(92%,720px)] -translate-x-1/2 animate-fade-up rounded-xl border border-brand/40 bg-popover px-3.5 py-2 shadow-lg">
            {path ? (
              <p className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-foreground">
                <span className="text-muted-foreground">{path.length - 1} {path.length === 2 ? 'step' : 'steps'}:</span>
                {path.map((id, i) => (
                  <span key={id} className="flex items-center gap-1.5">
                    {i > 0 && <Icon name="arrow-right" className="h-3 w-3 text-primary dark:text-brand-hi" />}
                    <button type="button" onClick={() => selectById(id)} className="rounded font-medium underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{pretty(id)}</button>
                  </span>
                ))}
                <button type="button" onClick={() => setTraceTo(null)} aria-label="Clear path" className="ml-1 rounded p-0.5 text-muted-foreground hover:text-foreground"><Icon name="close" className="h-3.5 w-3.5" /></button>
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">No connection between {pretty(selectedNode.id)} and {pretty(traceTo)} in the entities shown.</p>
            )}
          </div>
        )}
      </div>

      {/* --------------------------------------------------------- inspector */}
      {isDesktop && selectedNode && (
        <aside key={selectedNode.id} className="flex w-[380px] shrink-0 animate-slide-in-right flex-col border-l border-border bg-card" aria-label="Entity details">
          <div className="flex items-start justify-between gap-3 px-5 pt-4">
            <InspectorTitle node={selectedNode} />
            <button type="button" onClick={() => selectNode(null)} aria-label="Close details" title="Close (Esc)" className="-mr-1.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <Icon name="close" className="h-4 w-4" />
            </button>
          </div>
          <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 pb-24">{inspector}</div>
        </aside>
      )}
      {!isDesktop && (
        <DetailSheet open={!!selectedNode} onOpenChange={(o) => { if (!o) selectNode(null); }} title={selectedNode ? pretty(selectedNode.id) : ''} description={selectedNode ? (selectedNode.src ? `${systemName(selectedNode.src)} · ${selectedNode.domain}` : selectedNode.domain) : undefined}>
          {inspector}
        </DetailSheet>
      )}
    </div>
  );
}

/* =============================================================== inspector */

function InspectorTitle({ node }: { node: GraphNode }) {
  return (
    <div className="flex min-w-0 items-start gap-3">
      <SystemLogo system={node.src || 'ontology'} tile size="md" />
      <div className="min-w-0">
        <h2 className="truncate text-lg font-medium tracking-tight text-foreground">{pretty(node.id)}</h2>
        <p className="truncate text-xs text-muted-foreground">{node.src ? `${systemName(node.src)} · ${node.domain}` : `Canonical entity · ${node.domain}`}</p>
      </div>
    </div>
  );
}

interface InspectorProps {
  node: GraphNode;
  detail: any | null;
  edges: Link[];
  allNodes: GraphNode[];
  tab: InspectorTab;
  onTab: (t: InspectorTab) => void;
  rules: MappingRule[];
  rulesLoading: boolean;
  preview: VirtualQueryResponse | null;
  previewLoading: boolean;
  onRefreshPreview: () => void;
  onSelect: (id: string) => void;
  onFocus: () => void;
  onOpenEntity: () => void;
  traceTo: string | null;
  onTrace: (id: string | null) => void;
  path: string[] | null;
}

function Inspector({ node, detail, edges, allNodes, tab, onTab, rules, rulesLoading, preview, previewLoading, onRefreshPreview, onSelect, onFocus, onOpenEntity, traceTo, onTrace }: InspectorProps) {
  const known = useMemo(() => new Set(allNodes.map(n => n.id)), [allNodes]);
  const outgoing = edges.filter(e => e.s === node.id);
  const incoming = edges.filter(e => e.t === node.id);
  const governance: { type: string; targetEntity: string; targetCategory: string; description: string }[] =
    (detail?.relationships || []).filter((r: any) => r.targetCategory && r.targetCategory !== 'onto_schema');
  const fields: any[] = detail?.fields || [];
  const activeRule = rules.find(r => r.status === 'active') || rules[0];
  const rows = preview?.rows || [];
  const columns = rows.length ? Object.keys(rows[0]).slice(0, 6) : [];
  const others = allNodes.filter(n => n.id !== node.id).sort((a, b) => a.id.localeCompare(b.id));

  const relRow = (e: Link, dir: 'out' | 'in') => {
    const other = dir === 'out' ? e.t : e.s;
    const otherNode = allNodes.find(n => n.id === other);
    return (
      <li key={e.id}>
        <button
          type="button"
          onClick={() => known.has(other) && onSelect(other)}
          className="group -mx-2 flex w-[calc(100%+1rem)] items-start gap-2.5 rounded-lg px-2 py-2 text-left transition-colors hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Icon name="arrow-right" className={cn('mt-1 h-3 w-3 shrink-0 text-primary dark:text-brand-hi', dir === 'in' && 'rotate-180')} />
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-1.5 text-sm">
              <span className="text-muted-foreground">{dir === 'out' ? relLabel(e.type) : `${relLabel(e.type)} this, from`}</span>
              {otherNode?.src && <SystemLogo system={otherNode.src} size="xs" />}
              <span className="truncate font-medium text-foreground group-hover:underline group-hover:underline-offset-4">{pretty(other)}</span>
            </span>
            {e.description && <span className="mt-0.5 block text-xs text-muted-foreground">{e.description}</span>}
          </span>
        </button>
      </li>
    );
  };

  return (
    <div>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5">
        <StatusPill status={node.riskLevel}>{node.riskLevel} risk</StatusPill>
        <StatusPill status={node.fdwMappingStatus || (node.isVirtual ? 'virtual' : 'mapped')} />
        <span className="text-xs text-muted-foreground"><span className="num text-foreground">{node.fieldCount}</span> fields · <span className="num text-foreground">{node.degree}</span> links</span>
      </div>
      {detail?.semantic && <p className="mt-3 text-sm text-muted-foreground">{detail.semantic}</p>}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={onFocus}><Icon name="route" className="h-3.5 w-3.5" /> Show lineage</Button>
        <Button size="sm" variant="outline" onClick={onOpenEntity}><Icon name="table" className="h-3.5 w-3.5" /> Open in virtual data</Button>
      </div>

      <div className="mt-4 rounded-xl border border-border bg-surface-2/50 p-3">
        <label htmlFor="kg-trace" className="text-xs font-medium text-foreground">Trace a path to another entity</label>
        <Select value={traceTo || '__none'} onValueChange={(v) => onTrace(v === '__none' ? null : v)}>
          <SelectTrigger id="kg-trace" className="mt-1.5 h-9 bg-card"><SelectValue placeholder="Choose an entity" /></SelectTrigger>
          <SelectContent className="max-h-72">
            <SelectItem value="__none">No path</SelectItem>
            {others.map(o => <SelectItem key={o.id} value={o.id}>{pretty(o.id)}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <Tabs value={tab} onValueChange={(v) => onTab(v as InspectorTab)} className="mt-5">
        <TabsList variant="line" className="w-full justify-start">
          <TabsTrigger value="relationships">Links</TabsTrigger>
          <TabsTrigger value="fields">Fields</TabsTrigger>
          <TabsTrigger value="vdl">Data layer</TabsTrigger>
          <TabsTrigger value="data">Sample</TabsTrigger>
        </TabsList>

        <TabsContent value="relationships" className="mt-4 space-y-5">
          {edges.length === 0 && governance.length === 0 && <p className="text-sm text-muted-foreground">This entity has no recorded relationships yet.</p>}
          {outgoing.length > 0 && (
            <section>
              <h3 className="text-xs font-medium text-muted-foreground">This entity</h3>
              <ul className="mt-1">{outgoing.map(e => relRow(e, 'out'))}</ul>
            </section>
          )}
          {incoming.length > 0 && (
            <section>
              <h3 className="text-xs font-medium text-muted-foreground">Other entities</h3>
              <ul className="mt-1">{incoming.map(e => relRow(e, 'in'))}</ul>
            </section>
          )}
          {governance.length > 0 && (
            <section>
              <h3 className="text-xs font-medium text-muted-foreground">Governed by</h3>
              <ul className="mt-1 divide-y divide-border">
                {governance.map((g, i) => (
                  <li key={i} className="flex items-start gap-2.5 py-2">
                    <Icon name={g.targetCategory === 'onto_policy' ? 'shield-check' : g.targetCategory === 'onto_workflow' ? 'workflow' : 'plug'} className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0">
                      <span className="block text-sm text-foreground">{g.description || pretty(g.targetEntity)}</span>
                      <span className="block truncate text-xs text-muted-foreground">{CATEGORY_LABEL[g.targetCategory] || 'Reference'} <span className="font-mono">{g.targetEntity}</span></span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </TabsContent>

        <TabsContent value="fields" className="mt-4">
          {!detail ? (
            <div className="space-y-2">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-9 w-full" />)}</div>
          ) : fields.length === 0 ? (
            <p className="text-sm text-muted-foreground">No fields are recorded for this entity.</p>
          ) : (
            <ul className="divide-y divide-border">
              {fields.map((f: any) => (
                <li key={f.name} className="py-2">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="truncate font-mono text-xs text-foreground">{f.name}</span>
                    <span className="shrink-0 font-mono text-xs text-muted-foreground">{f.dataType}</span>
                  </div>
                  <div className="mt-0.5 flex items-baseline justify-between gap-3">
                    <span className="truncate text-xs text-muted-foreground">{f.semantic || 'No description'}</span>
                    {f.riskLevel && f.riskLevel !== 'low' && <StatusPill status={f.riskLevel} />}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>

        <TabsContent value="vdl" className="mt-4">
          {rulesLoading ? (
            <div className="space-y-2">{[0, 1, 2].map(i => <Skeleton key={i} className="h-8 w-full" />)}</div>
          ) : !activeRule ? (
            <p className="text-sm text-muted-foreground">No mapping rule yet. Create one in Data Plane, Mapping rules, to make this entity queryable.</p>
          ) : (
            <>
              <KeyValues
                items={[
                  { label: 'Mapping rule', value: activeRule.name },
                  { label: 'Status', value: <StatusPill status={activeRule.status} /> },
                  { label: 'Source', value: <span className="inline-flex items-center gap-1.5"><SystemLogo system={activeRule.sourceSystem} size="xs" />{systemName(activeRule.sourceSystem)}</span> },
                  { label: 'Source table', value: `${activeRule.sourceSchema ? activeRule.sourceSchema + '.' : ''}${activeRule.sourceTable}`, mono: true },
                  { label: 'Access', value: activeRule.sourceType },
                  { label: 'Fields mapped', value: activeRule.fieldMaps?.length ? activeRule.fieldMaps.length : 'All columns, as they are' },
                ]}
              />
              {rules.length > 1 && <p className="mt-3 text-xs text-muted-foreground">{rules.length - 1} more {rules.length === 2 ? 'rule' : 'rules'} for this entity.</p>}
            </>
          )}
        </TabsContent>

        <TabsContent value="data" className="mt-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground">
              {previewLoading ? 'Reading live rows' : rows.length ? `${rows.length} live rows${preview?.metadata?.durationMs ? ` in ${preview.metadata.durationMs} ms` : ''}` : 'No rows returned'}
            </p>
            <Button size="sm" variant="ghost" onClick={onRefreshPreview} disabled={previewLoading}>
              <Icon name="refresh" className={cn('h-3.5 w-3.5', previewLoading && 'animate-spin')} /> Refresh
            </Button>
          </div>
          {previewLoading ? (
            <div className="space-y-2">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-7 w-full" />)}</div>
          ) : rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">This entity is not mapped to a source yet, or the source returned nothing.</p>
          ) : (
            <div className="scroll-thin overflow-x-auto rounded-lg border border-border">
              <table className="w-full border-collapse text-xs">
                <thead>
                  <tr>{columns.map(c => <th key={c} scope="col" className="whitespace-nowrap border-b border-border bg-surface-2 px-2.5 py-1.5 text-left font-medium text-muted-foreground">{c}</th>)}</tr>
                </thead>
                <tbody>
                  {rows.slice(0, 8).map((r, i) => (
                    <tr key={i} className="border-b border-border last:border-b-0">
                      {columns.map(c => <td key={c} className="max-w-[140px] truncate whitespace-nowrap px-2.5 py-1.5 font-mono text-foreground">{String(r[c] ?? '')}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
