/**
 * Cover art for a solution card: a small data motif drawn in the brand blue
 * that hints at what the solution does (a flow for order-to-cash, a forecast
 * curve, stock bars, a spend donut, an OEE gauge, a risk radar, a customer
 * network, growth rings). One hue, no photos, crisp in both themes.
 *
 * The motif reacts when the parent card (className "group") is hovered.
 */
import { cn } from '@/lib/utils';
import { Icon, type IconName } from '@/components/ds/Icon';

export type CoverMotif = 'flow' | 'forecast' | 'bars' | 'donut' | 'gauge' | 'radar' | 'network' | 'rings' | 'waterfall' | 'grid';

const BY_ICON: Record<string, CoverMotif> = {
  'shopping-cart': 'flow', 'trend-up': 'forecast', box: 'bars', document: 'donut', factory: 'gauge',
  'shield-check': 'radar', users: 'network', leaf: 'rings', receipt: 'waterfall', clipboard: 'donut',
  truck: 'flow', 'chart-bar': 'bars', sparkles: 'grid',
};

export const motifFor = (icon: IconName): CoverMotif => BY_ICON[icon] || 'grid';

const S = 'currentColor';
const draw = 'transition-all duration-700 ease-brand-out';

function Motif({ kind }: { kind: CoverMotif }) {
  switch (kind) {
    case 'flow':
      return (
        <g fill="none" stroke={S} strokeWidth="1.6" strokeLinecap="round">
          {[34, 98, 162, 226].map((x, i) => (
            <g key={x}>
              {i < 3 && <line x1={x + 15} y1={48} x2={x + 49} y2={48} className="flow-line" opacity={0.7} />}
              <circle cx={x} cy={48} r={i === 3 ? 12 : 10} fill={i === 3 ? S : 'hsl(var(--card))'} fillOpacity={i === 3 ? 0.18 : 1} />
              <circle cx={x} cy={48} r={3} fill={S} stroke="none" opacity={i === 3 ? 1 : 0.55} />
            </g>
          ))}
        </g>
      );
    case 'forecast':
      return (
        <g fill="none" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16,70 C46,66 58,40 88,46 S128,62 150,38" stroke={S} strokeWidth="2" />
          <path d="M16,70 C46,66 58,40 88,46 S128,62 150,38 L150,84 L16,84 Z" fill={S} opacity={0.1} />
          <path d="M150,38 C176,20 204,30 244,14" stroke={S} strokeWidth="2" strokeDasharray="3 6" className={cn(draw, 'opacity-60 group-hover:opacity-100')} />
          <path d="M150,38 C176,8 204,18 244,4 L244,30 C204,44 176,34 150,38 Z" fill={S} className={cn(draw, 'opacity-[0.07] group-hover:opacity-[0.16]')} />
          <circle cx={150} cy={38} r={4} fill="hsl(var(--card))" stroke={S} strokeWidth="2" />
        </g>
      );
    case 'bars':
      return (
        <g>
          {[30, 52, 40, 66, 48, 74, 58].map((h, i) => (
            <g key={i} className={cn(draw, 'origin-bottom [transform-box:fill-box] group-hover:scale-y-110')} style={{ transitionDelay: `${i * 30}ms` }}>
              <rect x={24 + i * 32} y={84 - h} width={18} height={h} rx={4} fill={S} opacity={0.16} />
              <rect x={24 + i * 32} y={84 - h * 0.55} width={18} height={h * 0.55} rx={4} fill={S} opacity={i === 5 ? 0.95 : 0.5} />
            </g>
          ))}
        </g>
      );
    case 'donut':
      return (
        <g fill="none" strokeWidth="11" strokeLinecap="butt" transform="translate(64,48)">
          <circle r={28} stroke={S} opacity={0.14} />
          <circle r={28} stroke={S} pathLength={100} strokeDasharray="46 54" transform="rotate(-90)" />
          <circle r={28} stroke={S} opacity={0.5} pathLength={100} strokeDasharray="22 78" strokeDashoffset={-48} transform="rotate(-90)" className={cn(draw, 'group-hover:[stroke-dasharray:30_70]')} />
          <g transform="translate(58,-22)" stroke="none" fill={S}>
            {[1, 0.5, 0.2].map((o, i) => (
              <g key={i} opacity={o === 0.2 ? 0.35 : 1}>
                <rect y={i * 18} width={8} height={8} rx={2} opacity={o} />
                <rect x={16} y={i * 18 + 1} width={[84, 62, 46][i]} height={6} rx={3} opacity={0.16} />
              </g>
            ))}
          </g>
        </g>
      );
    case 'gauge':
      return (
        <g fill="none" strokeLinecap="round" transform="translate(132,80)">
          <path d="M-58,0 A58,58 0 0 1 58,0" stroke={S} strokeWidth="10" opacity={0.14} />
          <path d="M-58,0 A58,58 0 0 1 58,0" stroke={S} strokeWidth="10" pathLength={100} strokeDasharray="100" className={cn(draw, '[stroke-dashoffset:28] group-hover:[stroke-dashoffset:15]')} />
          {[-80, -40, 0, 40, 80].map(a => (
            <line key={a} x1={0} y1={-72} x2={0} y2={-68} stroke={S} strokeWidth="1.5" opacity={0.4} transform={`rotate(${a})`} />
          ))}
          <g className={cn(draw, 'origin-bottom [transform-box:fill-box] rotate-[38deg] group-hover:rotate-[62deg]')}>
            <line x1={0} y1={0} x2={0} y2={-40} stroke={S} strokeWidth="2.5" />
          </g>
          <circle r={5} fill={S} />
        </g>
      );
    case 'radar': {
      const pts = (r: number[]) => r.map((v, i) => { const a = (i / r.length) * Math.PI * 2 - Math.PI / 2; return `${Math.cos(a) * v},${Math.sin(a) * v}`; }).join(' ');
      return (
        <g transform="translate(132,48)" fill="none" stroke={S} strokeLinejoin="round">
          {[40, 27, 14].map(r => <polygon key={r} points={pts([r, r, r, r, r, r])} strokeWidth="1" opacity={0.22} />)}
          {[0, 1, 2].map(i => <line key={i} x1={Math.cos((i / 6) * Math.PI * 2 - Math.PI / 2) * 40} y1={Math.sin((i / 6) * Math.PI * 2 - Math.PI / 2) * 40} x2={-Math.cos((i / 6) * Math.PI * 2 - Math.PI / 2) * 40} y2={-Math.sin((i / 6) * Math.PI * 2 - Math.PI / 2) * 40} strokeWidth="1" opacity={0.16} />)}
          <polygon points={pts([34, 20, 30, 16, 26, 36])} strokeWidth="2" fill={S} fillOpacity={0.14} className={cn(draw, 'origin-center [transform-box:fill-box] group-hover:scale-110')} />
          <circle cx={0} cy={-34} r={3.5} fill={S} stroke="none" />
        </g>
      );
    }
    case 'network': {
      const sat: [number, number][] = [[-70, -22], [-48, 26], [58, -26], [76, 18], [4, -34], [-6, 34]];
      return (
        <g transform="translate(132,48)" stroke={S} fill="none">
          {sat.map(([x, y], i) => <line key={i} x1={0} y1={0} x2={x} y2={y} strokeWidth="1.2" opacity={0.4} className={i % 2 ? 'flow-line' : undefined} />)}
          {sat.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={i % 3 === 0 ? 7 : 5} fill="hsl(var(--card))" strokeWidth="1.6" />)}
          <circle r={13} fill={S} fillOpacity={0.18} strokeWidth="1.8" />
          <circle r={4} fill={S} stroke="none" className={cn(draw, 'origin-center [transform-box:fill-box] group-hover:scale-150')} />
        </g>
      );
    }
    case 'rings':
      return (
        <g transform="translate(132,84)" fill="none" stroke={S} strokeLinecap="round">
          {[70, 52, 34].map((r, i) => <path key={r} d={`M${-r},0 A${r},${r} 0 0 1 ${r},0`} strokeWidth="1.4" opacity={0.2 + i * 0.12} strokeDasharray={i === 0 ? '2 7' : undefined} />)}
          <path d="M0,0 C0,-30 22,-46 44,-50 C42,-26 28,-6 0,0 Z" fill={S} fillOpacity={0.2} strokeWidth="1.8" className={cn(draw, 'origin-bottom-left [transform-box:fill-box] group-hover:scale-110')} />
          <path d="M0,0 C-2,-22 -18,-34 -34,-36 C-34,-18 -22,-4 0,0 Z" fill={S} fillOpacity={0.1} strokeWidth="1.4" opacity={0.7} />
        </g>
      );
    case 'waterfall':
      return (
        <g>
          {[[0, 64], [14, 50], [24, 26], [36, 14], [0, 36]].map(([top, h], i) => (
            <rect key={i} x={36 + i * 42} y={20 + top} width={26} height={h} rx={4} fill={S} opacity={i === 0 || i === 4 ? 0.9 : 0.3}
              className={cn(draw, 'origin-bottom [transform-box:fill-box]', i > 0 && i < 4 && 'group-hover:opacity-50')} />
          ))}
          <path d="M62,20 H78 M104,34 H120 M146,44 H162 M188,56 H204" stroke={S} strokeWidth="1" strokeDasharray="2 3" opacity={0.5} />
        </g>
      );
    default:
      return (
        <g fill={S}>
          {Array.from({ length: 5 * 11 }).map((_, i) => {
            const c = i % 11, r = Math.floor(i / 11);
            const hot = (c * 7 + r * 3) % 9 === 0;
            return <circle key={i} cx={26 + c * 21} cy={14 + r * 17} r={hot ? 3.5 : 1.8} opacity={hot ? 0.9 : 0.22} />;
          })}
        </g>
      );
  }
}

export function SolutionCover({ icon, className, tall }: { icon: IconName; className?: string; tall?: boolean }) {
  const kind = motifFor(icon);
  return (
    <div
      className={cn('relative overflow-hidden bg-surface-2 text-primary dark:text-brand-hi', tall ? 'h-full min-h-[180px]' : 'h-28', className)}
      style={{ backgroundImage: 'radial-gradient(hsl(var(--border-strong) / 0.5) 1px, transparent 1px)', backgroundSize: '16px 16px' }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 264 96" preserveAspectRatio="xMidYMid meet" className="absolute inset-0 h-full w-full p-2">
        <Motif kind={kind} />
      </svg>
      <span className="absolute left-4 top-4 flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-foreground shadow-xs">
        <Icon name={icon} className="h-[18px] w-[18px]" />
      </span>
    </div>
  );
}

export default SolutionCover;
