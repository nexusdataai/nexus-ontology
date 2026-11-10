import React from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { DetailSheet, KeyValues, StatusPill, SubHeading } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import type { HybridSearchResponse, SearchResult } from '@/services/ontoApi';
import { docSystem, docTitle, pct, typeLabel } from './ragMeta';

interface GraphViewerProps {
  results: HybridSearchResponse | null;
  /** Optional: show a loading skeleton while a search runs. */
  loading?: boolean;
}

const NODE_W = 248;
const NODE_H = 36;
const ROW = 52;
const COL = NODE_W + 28;
const GROUP_GAP = 150;
const HEAD = 44;
const PER_COL = 8;

/**
 * Graph view of a retrieval: the documents found by vector search on the
 * left, the ones the knowledge graph added on the right, and the links the
 * expansion followed. Same visual language as the knowledge graph screen.
 */
const GraphViewer: React.FC<GraphViewerProps> = ({ results, loading }) => {
  const wrapRef = React.useRef<HTMLDivElement>(null);
  const [view, setView] = React.useState({ x: 24, y: 24, k: 1 });
  const [hovered, setHovered] = React.useState<string | null>(null);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const drag = React.useRef<{ px: number; py: number; x: number; y: number } | null>(null);

  const list = results?.results || [];

  const nodes = list.map((r) => ({
    id: r.source_id,
    category: r.metadata?.category || r.content_type,
    system: r.metadata?.system || 'unknown',
    similarity: r.similarity,
    graphExpanded: r.graph_expanded,
    doc: r,
  }));

  const edges: { from: string; to: string; type: string }[] = [];
  const graphDocs = list.filter((r) => r.graph_expanded);
  const vectorDocs = list.filter((r) => !r.graph_expanded);

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

  // Positions: two groups of columns, eight rows each.
  const vectorCols = Math.max(1, Math.ceil(vectorDocs.length / PER_COL));
  const graphCols = Math.ceil(graphDocs.length / PER_COL);
  const graphX0 = vectorCols * COL - 28 + GROUP_GAP;
  const pos: Record<string, { x: number; y: number }> = {};
  vectorDocs.forEach((r, i) => { pos[r.source_id] = { x: Math.floor(i / PER_COL) * COL, y: HEAD + (i % PER_COL) * ROW }; });
  graphDocs.forEach((r, i) => { pos[r.source_id] = { x: graphX0 + Math.floor(i / PER_COL) * COL, y: HEAD + (i % PER_COL) * ROW }; });
  const worldW = graphCols > 0 ? graphX0 + graphCols * COL - 28 : vectorCols * COL - 28;
  const worldH = HEAD + Math.min(PER_COL, Math.max(vectorDocs.length, graphDocs.length, 1)) * ROW - (ROW - NODE_H);

  const fit = React.useCallback(() => {
    const el = wrapRef.current;
    if (!el) return;
    const w = el.clientWidth, h = el.clientHeight;
    const k = Math.max(0.45, Math.min(1, (w - 56) / worldW, (h - 112) / worldH));
    setView({ k, x: Math.max(20, (w - worldW * k) / 2), y: Math.max(64, (h - worldH * k) / 2) });
  }, [worldW, worldH]);

  React.useEffect(() => {
    fit();
    setSelectedId(null);
    const el = wrapRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => fit());
    ro.observe(el);
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results, fit]);

  if (loading && !results) {
    return (
      <div className="canvas-dots relative h-[560px] overflow-hidden rounded-xl border border-border" aria-busy="true">
        <div className="absolute left-6 top-16 space-y-4">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-9 w-60 rounded-full" />)}</div>
        <div className="absolute right-6 top-16 hidden space-y-4 sm:block">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-9 w-60 rounded-full" />)}</div>
      </div>
    );
  }

  if (!results || results.total === 0) {
    return <EmptyState icon="graph" title="Run a query to draw its graph" description="The graph shows which documents matched directly and which ones the knowledge graph pulled in." />;
  }

  const zoomBy = (factor: number) => {
    const el = wrapRef.current;
    setView(v => {
      const k = Math.max(0.4, Math.min(1.6, v.k * factor));
      if (!el) return { ...v, k };
      const cx = el.clientWidth / 2, cy = el.clientHeight / 2;
      return { k, x: cx - ((cx - v.x) / v.k) * k, y: cy - ((cy - v.y) / v.k) * k };
    });
  };

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement;
    // Ignore nodes and controls, and anything in the inspector sheet (a portal).
    if (!e.currentTarget.contains(target) || target.closest('[data-graph-ui]')) return;
    drag.current = { px: e.clientX, py: e.clientY, x: view.x, y: view.y };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d) return;
    setView(v => ({ ...v, x: d.x + (e.clientX - d.px), y: d.y + (e.clientY - d.py) }));
  };
  const onPointerUp = () => { drag.current = null; };

  const focusId = hovered || selectedId;
  const linked = (id: string) => !focusId || id === focusId || edges.some(e => (e.from === focusId && e.to === id) || (e.to === focusId && e.from === id));
  const selected = nodes.find(n => n.id === selectedId) || null;
  const selectedDoc: SearchResult | null = selected?.doc || null;
  const neighbours = selected
    ? edges.filter(e => e.from === selected.id || e.to === selected.id).map(e => nodes.find(n => n.id === (e.from === selected.id ? e.to : e.from))).filter(Boolean) as typeof nodes
    : [];

  return (
    <div
      ref={wrapRef}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      className={cn('canvas-dots relative h-[560px] cursor-grab touch-pan-y select-none overflow-hidden rounded-xl border border-border transition-opacity duration-200 active:cursor-grabbing', loading && 'opacity-60')}
    >
      {/* links */}
      <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
        <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
          {edges.map((edge, i) => {
            const a = pos[edge.from], b = pos[edge.to];
            if (!a || !b) return null;
            const x1 = a.x + NODE_W, y1 = a.y + NODE_H / 2;
            const x2 = b.x, y2 = b.y + NODE_H / 2;
            const mx = (x1 + x2) / 2;
            const d = `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
            const lit = !!focusId && (edge.from === focusId || edge.to === focusId);
            return (
              <g key={i} opacity={focusId ? (lit ? 1 : 0.18) : 0.9} style={{ transition: 'opacity 200ms ease' }}>
                <path d={d} fill="none" stroke={lit ? 'hsl(var(--brand-hi))' : 'hsl(var(--border-strong))'} strokeWidth={lit ? 1.6 : 1.1} />
                {lit && <path d={d} fill="none" stroke="hsl(var(--background))" strokeWidth={1.6} className="flow-line" opacity={0.75} />}
              </g>
            );
          })}
        </g>
      </svg>

      {/* nodes and labels */}
      <div className="absolute left-0 top-0 h-0 w-0" style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})`, transformOrigin: '0 0' }}>
        <div className="pointer-events-none absolute flex items-baseline gap-2 whitespace-nowrap" style={{ left: 0, top: 0 }}>
          <span className="text-sm font-medium text-foreground">Matched by vector search</span>
          <span className="num text-xs text-muted-foreground">{vectorDocs.length}</span>
        </div>
        {graphDocs.length > 0 && (
          <div className="pointer-events-none absolute flex items-baseline gap-2 whitespace-nowrap" style={{ left: graphX0, top: 0 }}>
            <span className="text-sm font-medium text-foreground">Added by the knowledge graph</span>
            <span className="num text-xs text-muted-foreground">{graphDocs.length}</span>
          </div>
        )}

        {nodes.map((node, i) => {
          const p = pos[node.id];
          if (!p) return null;
          const system = docSystem(node.doc);
          const isSelected = selectedId === node.id;
          const title = docTitle(node.doc);
          return (
            <button
              key={node.id}
              type="button"
              data-graph-ui
              onClick={() => setSelectedId(node.id)}
              onMouseEnter={() => setHovered(node.id)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(node.id)}
              onBlur={() => setHovered(null)}
              aria-pressed={isSelected}
              aria-label={`${title}, ${typeLabel(node.category)}, similarity ${pct(node.similarity)} percent`}
              className={cn(
                'rise absolute flex cursor-pointer items-center gap-2 rounded-full border bg-card pl-2.5 pr-3 text-left shadow-xs outline-none',
                'transition-[opacity,box-shadow,border-color,background-color] duration-200',
                'hover:border-brand/70 hover:shadow-md focus-visible:ring-2 focus-visible:ring-ring',
                node.graphExpanded ? 'border-dashed border-border-strong' : 'border-border-strong',
                isSelected && 'border-solid border-brand bg-accent shadow-md ring-2 ring-brand/30',
                !linked(node.id) && '!opacity-25',
              )}
              style={{ left: p.x, top: p.y, width: NODE_W, height: NODE_H, zIndex: isSelected ? 3 : 1, ['--i' as any]: Math.min(i, 16) }}
            >
              <SystemLogo system={system || 'knowledge'} size="xs" />
              <span className={cn('min-w-0 flex-1 truncate text-sm text-foreground', (isSelected || i === 0) && 'font-medium')}>{title}</span>
              <span className="num shrink-0 text-xs text-muted-foreground">{pct(node.similarity)}%</span>
            </button>
          );
        })}
      </div>

      {/* floating summary */}
      <div data-graph-ui className="pointer-events-none absolute left-3 top-3 max-w-[calc(100%-24px)] rounded-xl border border-border bg-popover/95 px-3 py-2 text-xs text-muted-foreground shadow-md backdrop-blur sm:left-4 sm:top-4">
        <span className="num text-foreground">{nodes.length}</span> documents, <span className="num text-foreground">{edges.length}</span> {edges.length === 1 ? 'link' : 'links'}.
        <span className="hidden sm:inline"> Dashed outlines were added by graph expansion. Drag to move, select a document to inspect it.</span>
      </div>

      {/* zoom controls */}
      <div data-graph-ui className="absolute bottom-3 left-3 flex flex-col rounded-xl border border-border bg-popover/95 p-1 shadow-md backdrop-blur sm:bottom-4 sm:left-4">
        {([
          { label: 'Zoom in', icon: 'plus', run: () => zoomBy(1.25) },
          { label: 'Zoom out', icon: 'minus', run: () => zoomBy(0.8) },
          { label: 'Fit to screen', icon: 'expand', run: fit },
        ] as const).map(b => (
          <button key={b.label} type="button" onClick={b.run} aria-label={b.label} title={b.label}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <Icon name={b.icon} className="h-3.5 w-3.5" />
          </button>
        ))}
      </div>

      {/* inspector */}
      <DetailSheet
        open={!!selectedDoc}
        onOpenChange={(o) => { if (!o) setSelectedId(null); }}
        title={selectedDoc ? docTitle(selectedDoc) : ''}
        description={selectedDoc ? `${typeLabel(selectedDoc.content_type)}${docSystem(selectedDoc) ? ` from ${systemName(docSystem(selectedDoc))}` : ''}` : undefined}
        meta={selected && <StatusPill tone={selected.graphExpanded ? 'neutral' : 'info'} variant="soft">{selected.graphExpanded ? 'Added by graph expansion' : 'Matched by vector search'}</StatusPill>}
      >
        {selectedDoc && selected && (
          <div className="space-y-7">
            <KeyValues items={[
              { label: 'Similarity', value: <span className="num">{pct(selectedDoc.similarity)}%</span> },
              { label: 'Type', value: typeLabel(selectedDoc.content_type) },
              ...(docSystem(selectedDoc) ? [{ label: 'Source system', value: <span className="inline-flex items-center gap-2"><SystemLogo system={docSystem(selectedDoc)} size="xs" />{systemName(docSystem(selectedDoc))}</span> }] : []),
              { label: 'Document ID', value: selectedDoc.source_id, mono: true },
            ]} />
            {neighbours.length > 0 && (
              <section>
                <SubHeading>{selected.graphExpanded ? 'Pulled in by' : 'Pulled in through the graph'}</SubHeading>
                <ul className="divide-y divide-border">
                  {neighbours.map(n => (
                    <li key={n.id}>
                      <button type="button" onClick={() => setSelectedId(n.id)} className="flex w-full items-center gap-2.5 py-2 text-left text-sm text-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:hover:text-brand-hi">
                        <SystemLogo system={docSystem(n.doc) || 'knowledge'} size="xs" />
                        <span className="min-w-0 flex-1 truncate">{docTitle(n.doc)}</span>
                        <span className="num shrink-0 text-xs text-muted-foreground">{pct(n.similarity)}%</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            <section>
              <SubHeading>Content</SubHeading>
              <p className="whitespace-pre-wrap break-words text-sm leading-6 text-foreground">{selectedDoc.content}</p>
            </section>
          </div>
        )}
      </DetailSheet>
    </div>
  );
};

export default GraphViewer;
