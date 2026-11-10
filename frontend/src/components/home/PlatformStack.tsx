/**
 * Isometric drawing of the Nexus AI platform: four planes stacked from data
 * (bottom) to solutions (top), with AI Ops running alongside.
 * Pure SVG, token colours only. `active` highlights one plane.
 */
import { cn } from '@/lib/utils';

export type LayerId = 'solutions' | 'reasoning' | 'control' | 'data' | 'ops';

const CX = 250;
const W = 188;   // half width of a plane
const H = 60;    // half height of a plane
const T = 11;    // plane thickness
const GAP = 132; // vertical distance between plane centres
const TOP = 78;

const PLANES: { id: Exclude<LayerId, 'ops'>; y: number }[] = [
  { id: 'data', y: TOP + GAP * 3 },
  { id: 'control', y: TOP + GAP * 2 },
  { id: 'reasoning', y: TOP + GAP },
  { id: 'solutions', y: TOP },
];

/** Map plane coordinates (u, v in -1..1) to screen. */
const iso = (y: number, u: number, v: number): [number, number] => [CX + ((u - v) * W) / 2, y + ((u + v) * H) / 2];
const pt = (p: [number, number]) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`;

function Plane({ y, on, children }: { y: number; on: boolean; children?: React.ReactNode }) {
  const top = [iso(y, -1, -1), iso(y, 1, -1), iso(y, 1, 1), iso(y, -1, 1)];
  const [, right, front, left] = top;
  const down = (p: [number, number]): [number, number] => [p[0], p[1] + T];
  const grid = [-0.5, 0, 0.5];
  return (
    <g>
      {/* thickness */}
      <polygon points={[left, front, down(front), down(left)].map(pt).join(' ')} className={cn('transition-colors duration-300', on ? 'fill-brand/35' : 'fill-surface-3')} />
      <polygon points={[front, right, down(right), down(front)].map(pt).join(' ')} className={cn('transition-colors duration-300', on ? 'fill-brand/20' : 'fill-surface-2')} />
      {/* top face */}
      <polygon
        points={top.map(pt).join(' ')}
        className={cn('transition-colors duration-300', on ? 'fill-[hsl(var(--plane-on))] stroke-brand' : 'fill-[hsl(var(--plane))] stroke-[hsl(var(--plane-line))]')}
        strokeWidth={on ? 1.25 : 1}
        strokeLinejoin="round"
      />
      {/* surface grid */}
      <g className={cn('transition-opacity duration-300', on ? 'stroke-brand/25' : 'stroke-border')} strokeWidth="1">
        {grid.map(g => (
          <g key={g}>
            <line x1={iso(y, g, -1)[0]} y1={iso(y, g, -1)[1]} x2={iso(y, g, 1)[0]} y2={iso(y, g, 1)[1]} />
            <line x1={iso(y, -1, g)[0]} y1={iso(y, -1, g)[1]} x2={iso(y, 1, g)[0]} y2={iso(y, 1, g)[1]} />
          </g>
        ))}
      </g>
      <polyline points={[left, down(left), down(front), down(right), right].map(pt).join(' ')} fill="none" className={cn('transition-colors duration-300', on ? 'stroke-brand' : 'stroke-[hsl(var(--plane-line))]')} strokeWidth="1" strokeLinejoin="round" />
      {children}
    </g>
  );
}

/** Small upright block standing on a plane. */
function Block({ y, u, v, h = 12, s = 0.16, on }: { y: number; u: number; v: number; h?: number; s?: number; on: boolean }) {
  const base = [iso(y, u - s, v - s), iso(y, u + s, v - s), iso(y, u + s, v + s), iso(y, u - s, v + s)];
  const up = (p: [number, number]): [number, number] => [p[0], p[1] - h];
  const [b, r, f, l] = base;
  return (
    <g strokeLinejoin="round" strokeWidth="1" className={on ? 'stroke-brand' : 'stroke-border-strong'}>
      <polygon points={[l, f, up(f), up(l)].map(pt).join(' ')} className={on ? 'fill-brand/45' : 'fill-surface-3'} />
      <polygon points={[f, r, up(r), up(f)].map(pt).join(' ')} className={on ? 'fill-brand/25' : 'fill-surface-2'} />
      <polygon points={[up(b), up(r), up(f), up(l)].map(pt).join(' ')} className={on ? 'fill-brand/70' : 'fill-card'} />
    </g>
  );
}

/** Short cylinder: a data source. */
function Drum({ y, u, v, on }: { y: number; u: number; v: number; on: boolean }) {
  const [x, cy] = iso(y, u, v);
  const rx = 13, ry = 5.5, h = 11;
  return (
    <g strokeWidth="1" className={on ? 'stroke-brand' : 'stroke-border-strong'}>
      <path d={`M${x - rx},${cy - h} v${h} a${rx},${ry} 0 0 0 ${rx * 2},0 v${-h}`} className={on ? 'fill-brand/30' : 'fill-surface-2'} />
      <ellipse cx={x} cy={cy - h} rx={rx} ry={ry} className={on ? 'fill-brand/60' : 'fill-card'} />
    </g>
  );
}

interface PlatformStackProps {
  active: LayerId | null;
  onHover: (id: LayerId | null) => void;
  onSelect: (id: LayerId) => void;
  className?: string;
}

export function PlatformStack({ active, onHover, onSelect, className }: PlatformStackProps) {
  const isOn = (id: LayerId) => active === id;
  const yOf = (id: Exclude<LayerId, 'ops'>) => PLANES.find(p => p.id === id)!.y;

  // knowledge-graph nodes on the control plane
  const cy = yOf('control');
  const nodes: [number, number][] = [[0, 0], [-0.55, -0.35], [0.5, -0.5], [0.62, 0.3], [-0.2, 0.6], [-0.7, 0.25], [0.05, -0.7]];
  const edges: [number, number][] = [[0, 1], [0, 2], [0, 3], [0, 4], [1, 5], [2, 6], [3, 4], [1, 6]];

  // reasoning loop
  const ry = yOf('reasoning');
  const loopRx = (0.62 * W) / Math.SQRT2 * 1.42;
  const loopRy = (0.62 * H) / Math.SQRT2 * 1.42;
  const loopStops = [-90, 30, 150].map(a => {
    const r = (a * Math.PI) / 180;
    return [CX + Math.cos(r) * loopRx, ry + Math.sin(r) * loopRy] as [number, number];
  });

  const sy = yOf('solutions');
  const opsX = CX + W + 34;

  return (
    <svg
      viewBox={`0 0 500 ${TOP + GAP * 3 + H + T + 24}`}
      className={cn('h-auto w-full select-none', className)}
      role="img"
      aria-label="Platform architecture: Data Plane, Control Plane, Reasoning Plane and Solutions stacked, with AI Ops alongside"
    >
      <defs>
        <radialGradient id="stack-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="hsl(var(--brand))" stopOpacity="0.22" />
          <stop offset="100%" stopColor="hsl(var(--brand))" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* floor glow */}
      <ellipse cx={CX} cy={yOf('data') + H + T + 6} rx={W * 1.05} ry={H * 0.75} fill="url(#stack-glow)" />

      {PLANES.map((p, i) => {
        const on = isOn(p.id);
        const lower = PLANES[i - 1];
        return (
          <g
            key={p.id}
            className="cursor-pointer"
            onMouseEnter={() => onHover(p.id)}
            onMouseLeave={() => onHover(null)}
            onClick={() => onSelect(p.id)}
          >
            {/* risers from the plane below */}
            {lower && [-0.5, 0.5].map(k => {
              const x = CX + k * W;
              const y1 = lower.y - H / 2 + 6;
              const y2 = p.y + H / 2 + T;
              return (
                <g key={k}>
                  <line x1={x} y1={y1} x2={x} y2={y2} className="stroke-border-strong" strokeWidth="1" />
                  <line x1={x} y1={y1} x2={x} y2={y2} className="flow-line stroke-brand" strokeWidth="1.5" strokeLinecap="round" />
                  <circle cx={x} cy={y1} r="2.5" className="fill-brand" />
                </g>
              );
            })}

            <g
              className="transition-transform duration-500 ease-brand-out"
              style={{ transform: on ? 'translateY(-7px)' : undefined }}
            >
              <Plane y={p.y} on={on}>
                {p.id === 'data' && (
                  <>
                    {[[-0.55, -0.45], [0.05, -0.55], [0.6, -0.3], [-0.5, 0.3], [0.05, 0.2], [0.55, 0.5]].map(([u, v], k) => (
                      <Drum key={k} y={p.y} u={u} v={v} on={on} />
                    ))}
                  </>
                )}

                {p.id === 'control' && (
                  <g>
                    <g className={on ? 'stroke-brand/70' : 'stroke-border-strong'} strokeWidth="1">
                      {edges.map(([a, b], k) => {
                        const A = iso(cy, nodes[a][0], nodes[a][1]);
                        const B = iso(cy, nodes[b][0], nodes[b][1]);
                        return <line key={k} x1={A[0]} y1={A[1]} x2={B[0]} y2={B[1]} />;
                      })}
                    </g>
                    {nodes.map(([u, v], k) => {
                      const [x, y] = iso(cy, u, v);
                      return k === 0
                        ? <circle key={k} cx={x} cy={y} r="6" className="fill-brand stroke-card" strokeWidth="2" />
                        : <circle key={k} cx={x} cy={y} r="3.5" className={on ? 'fill-card stroke-brand' : 'fill-card stroke-muted-foreground'} strokeWidth="1.25" />;
                    })}
                  </g>
                )}

                {p.id === 'reasoning' && (
                  <g>
                    <ellipse cx={CX} cy={ry} rx={loopRx} ry={loopRy} fill="none" className="stroke-border-strong" strokeWidth="1" />
                    <ellipse cx={CX} cy={ry} rx={loopRx} ry={loopRy} fill="none" className="flow-line stroke-brand" strokeWidth="1.5" strokeLinecap="round" />
                    {loopStops.map(([x, y], k) => (
                      <rect key={k} x={x - 5} y={y - 5} width="10" height="10" rx="2" transform={`rotate(45 ${x} ${y})`} className={on ? 'fill-brand stroke-card' : 'fill-card stroke-muted-foreground'} strokeWidth="1.25" />
                    ))}
                    <circle cx={CX} cy={ry} r="4" className="fill-brand" />
                  </g>
                )}

                {p.id === 'solutions' && (
                  <>
                    {[[-0.5, -0.42, 10], [0, -0.42, 16], [0.5, -0.42, 8], [-0.5, 0.3, 14], [0, 0.3, 9], [0.5, 0.3, 18]].map(([u, v, h], k) => (
                      <Block key={k} y={sy} u={u} v={v} h={h} on={on} />
                    ))}
                  </>
                )}
              </Plane>
            </g>
          </g>
        );
      })}

      {/* AI Ops rail */}
      <g
        className="cursor-pointer"
        onMouseEnter={() => onHover('ops')}
        onMouseLeave={() => onHover(null)}
        onClick={() => onSelect('ops')}
      >
        <rect x={opsX - 14} y={sy - 14} width="28" height={yOf('data') - sy + 28} fill="transparent" />
        <line x1={opsX} y1={sy} x2={opsX} y2={yOf('data')} className={cn('transition-colors duration-300', isOn('ops') ? 'stroke-brand' : 'stroke-border-strong')} strokeWidth="1" />
        <line x1={opsX} y1={sy} x2={opsX} y2={yOf('data')} className="flow-line stroke-brand" strokeWidth="1.5" strokeLinecap="round" opacity={isOn('ops') ? 1 : 0.55} />
        {PLANES.map(p => (
          <g key={p.id}>
            <line x1={CX + W + 6} y1={p.y} x2={opsX} y2={p.y} className={cn('transition-colors duration-300', isOn('ops') ? 'stroke-brand' : 'stroke-border-strong')} strokeWidth="1" strokeDasharray="2 3" />
            <circle cx={opsX} cy={p.y} r="3.5" className={cn('transition-colors duration-300', isOn('ops') ? 'fill-brand stroke-card' : 'fill-card stroke-muted-foreground')} strokeWidth="1.25" />
          </g>
        ))}
      </g>
    </svg>
  );
}

export default PlatformStack;
