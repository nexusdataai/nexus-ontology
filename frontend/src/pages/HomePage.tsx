import { useState, useEffect, useMemo, useCallback } from 'react';
import { BUILT_IN_SOURCE_IDS } from '@/config/builtInSources';
import { useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import { APP_REGISTRY } from '@/config/appRegistry';
import { apiClient } from '@/services/apiClient';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { AnimatedNumber } from '@/components/ds/AnimatedNumber';
import { Icon, type IconName } from '@/components/ds/Icon';
import { PlatformStack, type LayerId } from '@/components/home/PlatformStack';

/* ----------------------------------------------------------------- helpers */

const SYSTEM_LABELS: Record<string, string> = {
  sfdc: 'Salesforce', salesforce: 'Salesforce', sap: 'SAP', oracle: 'Oracle',
  gdrive: 'Google Drive', google_drive: 'Google Drive', social: 'Social listening',
  files: 'File uploads', external: 'External',
};
const systemLabel = (k: string) => SYSTEM_LABELS[k.toLowerCase()] || k.replace(/[_-]+/g, ' ').replace(/^\w/, c => c.toUpperCase());

const JOURNEY_TYPE_LABELS: Record<string, string> = {
  'semantic-rag': 'Knowledge pipeline', 'data-pipeline': 'Data pipeline',
};
const typeLabel = (t?: string) => {
  if (!t) return 'Journey';
  if (JOURNEY_TYPE_LABELS[t]) return JOURNEY_TYPE_LABELS[t];
  const app = APP_REGISTRY.find(a => a.journeyStageId === t);
  return app?.shortName || t.replace(/[_-]+/g, ' ').replace(/^\w/, c => c.toUpperCase());
};

function timeAgo(iso?: string) {
  if (!iso) return '';
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms)) return '';
  const m = Math.max(0, Math.round(ms / 60000));
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}

/**
 * Status to show for a journey, the same rule the journeys list uses: the
 * backend keeps a journey at "pending" after its runs have finished, so the
 * runs decide when there are any.
 */
const journeyStatus = (j: any): string => {
  const status = String(j.status || 'created').toLowerCase();
  if (status !== 'created' && status !== 'pending') return status;
  const total = Number(j.totalJobs) || 0, done = Number(j.completedJobs) || 0, failed = Number(j.failedJobs) || 0;
  if (total > done + failed) return 'running';
  if (done > 0) return 'completed';
  if (failed > 0) return 'failed';
  return 'created';
};

const STATUS_TONE: Record<string, string> = {
  running: 'text-primary dark:text-brand-hi',
  completed: 'text-success',
  failed: 'text-destructive',
  cancelled: 'text-subtle-foreground',
  paused: 'text-warning',
  created: 'text-subtle-foreground',
};

/* ------------------------------------------------------------------ pieces */

/** A number with its label, written as text. Becomes a link when onClick is set. */
function Metric({ value, label, onClick, icon }: { value: React.ReactNode; label: string; onClick?: () => void; icon?: IconName }) {
  const body = (
    <>
      {icon && <Icon name={icon} className="h-3.5 w-3.5 shrink-0 self-center text-subtle-foreground" />}
      <span className="num text-md font-medium text-foreground">{value}</span>
      <span className="text-sm text-muted-foreground">{label}</span>
    </>
  );
  if (!onClick) return <span className="inline-flex items-baseline gap-1.5">{body}</span>;
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className="group/m inline-flex items-baseline gap-1.5 rounded-sm underline-offset-4 transition-colors hover:[&>span:last-child]:text-foreground hover:[&>span:last-child]:underline"
    >
      {body}
    </button>
  );
}

function TextLink({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className="group/l inline-flex items-center gap-1 text-sm font-medium text-foreground underline-offset-4 hover:underline"
    >
      {children}
      <Icon name="arrow-right" className="h-3.5 w-3.5 text-subtle-foreground transition-transform duration-300 ease-brand-out group-hover/l:translate-x-0.5 group-hover/l:text-foreground" />
    </button>
  );
}

/** One row of the layer list, linked to a plane in the drawing. */
function LayerRow({
  id, index, icon, title, description, active, onHover, onOpen, children,
}: {
  id: LayerId;
  index: string;
  /** The same icon the sidebar uses for this area. */
  icon: IconName;
  title: string;
  description: string;
  active: boolean;
  onHover: (id: LayerId | null) => void;
  onOpen?: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      onMouseEnter={() => onHover(id)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(id)}
      onBlur={() => onHover(null)}
      className={cn(
        'relative px-5 py-4 transition-colors duration-300 sm:px-6',
        active && 'bg-surface-2/60',
      )}
    >
      <span className={cn('absolute inset-y-0 left-0 w-0.5 bg-primary transition-transform duration-300 ease-brand-out', active ? 'scale-y-100' : 'scale-y-0')} />
      <div className="flex items-start gap-4">
        <span
          className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border transition-colors duration-300',
            active ? 'border-brand/50 bg-brand/10 text-primary dark:text-brand-hi' : 'border-border bg-surface-2 text-foreground',
          )}
          aria-hidden="true"
        >
          <Icon name={icon} className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="flex items-baseline gap-2 text-md font-medium text-foreground">
              {title}
              {index && <span className="num text-xs font-normal text-subtle-foreground">Layer {Number(index)}</span>}
            </h2>
            {onOpen && <TextLink onClick={onOpen}>Open</TextLink>}
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>
          <div className="mt-2.5 flex flex-wrap items-baseline gap-x-5 gap-y-1.5">{children}</div>
        </div>
      </div>
    </div>
  );
}

function ListSection({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="min-w-0">
      <div className="flex items-baseline justify-between gap-3 border-b border-border pb-2.5">
        <h2 className="text-md font-medium text-foreground">{title}</h2>
        {action}
      </div>
      <div className="divide-y divide-border">{children}</div>
    </section>
  );
}

const rowBtn = 'group/r flex w-full items-center gap-3 py-2.5 text-left transition-colors';

/* -------------------------------------------------------------------- page */

export default function HomePage() {
  const nav = useNavigate();
  const [stats, setStats] = useState<any>(null);
  const [journeys, setJourneys] = useState<any[] | null>(null);
  const [journeyCount, setJourneyCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [hovered, setHovered] = useState<LayerId | null>(null);
  const [tour, setTour] = useState<LayerId>('data');
  // Walk up the stack slowly while nobody is pointing at it.
  const active: LayerId = hovered ?? tour;
  const setActive = setHovered;

  const appStats = useMemo(() => {
    const available = APP_REGISTRY.filter(a => a.status === 'available').length;
    const comingSoon = APP_REGISTRY.filter(a => a.status === 'coming_soon').length;
    return { available, comingSoon, total: APP_REGISTRY.length };
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    const a = apiClient.get<any>('/api/v1/control-plane/stats').then(setStats).catch(() => {});
    const b = apiClient.get<any>('/api/v1/journeys/').then(d => {
      const items = d?.data || d?.journeys || d?.items || [];
      const list = Array.isArray(items) ? items : [];
      setJourneys(list);
      setJourneyCount(d?.total != null ? d.total : list.length);
    }).catch(() => setJourneys([]));
    Promise.allSettled([a, b]).then(() => {
      setLoading(false);
      setUpdatedAt(new Date());
    });
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (hovered) return;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
    const order: LayerId[] = ['data', 'control', 'reasoning', 'solutions', 'ops'];
    const t = window.setInterval(() => {
      setTour(cur => order[(order.indexOf(cur) + 1) % order.length]);
    }, 2600);
    return () => window.clearInterval(t);
  }, [hovered]);

  const go = (path: string, tab?: string) => {
    nav(tab ? `${path}?tab=${tab}` : path);
  };

  const n = (v: unknown) => <AnimatedNumber value={typeof v === 'number' ? v : null} />;
  const systems: [string, number][] = stats?.entities_by_system
    ? Object.entries(stats.entities_by_system as Record<string, number>).sort((x, y) => y[1] - x[1])
    : [];
  // The same sources the Data Plane page lists.
  const sourceCount = BUILT_IN_SOURCE_IDS.length;
  const maxSystem = Math.max(1, ...systems.map(s => s[1]));

  const recent = useMemo(() => {
    return [...(journeys || [])]
      .sort((x, y) => new Date(y.updated_at || y.created_at || 0).getTime() - new Date(x.updated_at || x.created_at || 0).getTime())
      .slice(0, 5);
  }, [journeys]);

  const openLayer = (id: LayerId) => {
    if (id === 'solutions') go('/workspace/apps');
    else if (id === 'reasoning') go('/ai-stack/reasoning');
    else if (id === 'control') go('/ai-stack/control-plane');
    else if (id === 'data') go('/ai-stack/data-plane');
    else go('/operations/health');
  };

  return (
    <Layout>
      <div className="page">
        {/* Heading */}
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
          <div className="min-w-0">
            <h1 className="text-lg font-medium tracking-tight text-foreground">Platform overview</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              How your enterprise data becomes governed AI action, layer by layer.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {updatedAt && (
              <span className="text-xs text-subtle-foreground">
                Updated {updatedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            <Button variant="outline" size="sm" onClick={load} disabled={loading}>
              <Icon name="refresh" className={cn(loading && 'animate-spin')} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Platform map */}
        <section className="mt-6 overflow-hidden rounded-xl border border-border bg-card shadow-xs">
          <div className="grid lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
            {/* drawing */}
            <div className="canvas-dots relative flex items-center justify-center border-b border-border px-6 py-8 lg:border-b-0 lg:border-r">
              <span className="eyebrow-brand absolute left-5 top-4 sm:left-6">Platform map</span>
              <PlatformStack
                active={active}
                onHover={setActive}
                onSelect={openLayer}
                className="max-w-[420px] animate-fade-up"
              />
            </div>

            {/* layers */}
            <div className="divide-y divide-border">
              <LayerRow
                id="solutions" index="04" icon="apps" title="Solutions" active={active === 'solutions'} onHover={setActive}
                description="Packaged business applications and the automations behind them."
              >
                <Metric value={n(appStats.available)} label="active solutions" icon="apps" onClick={() => go('/workspace/apps')} />
                {appStats.comingSoon > 0 && <Metric value={n(appStats.comingSoon)} label="planned" icon="clock" onClick={() => go('/workspace/apps')} />}
                <Metric value={n(journeyCount)} label="journeys" icon="workflow" onClick={() => go('/workspace/automation')} />
              </LayerRow>

              <LayerRow
                id="reasoning" index="03" icon="brain-ai" title="Reasoning Plane" active={active === 'reasoning'} onHover={setActive}
                description="ReAct agent that plans, calls tools and checks policy before it acts."
                onOpen={() => go('/ai-stack/reasoning')}
              >
                <Metric value="AI Copilot" label="natural language" icon="chat-bot" onClick={() => go('/ai-stack/reasoning', 'copilot')} />
                <Metric value={<AnimatedNumber value={stats?.tools_count || 14} />} label="ReAct tools" icon="wrench" onClick={() => go('/ai-stack/reasoning', 'tools')} />
                <Metric value="Playground" label="RAG validation" icon="flask" onClick={() => go('/ai-stack/reasoning', 'playground')} />
              </LayerRow>

              <LayerRow
                id="control" index="02" icon="layers" title="Control Plane" active={active === 'control'} onHover={setActive}
                description="Enterprise ontology, knowledge graph and semantic index."
                onOpen={() => go('/ai-stack/control-plane')}
              >
                <Metric value={n(stats?.onto_schema)} label="schemas" icon="table" onClick={() => go('/ai-stack/control-plane', 'knowledge')} />
                <Metric value={n(stats?.onto_policy)} label="policies" icon="shield-check" onClick={() => go('/ai-stack/control-plane', 'policies')} />
                <Metric value={n(stats?.onto_workflow)} label="workflows" icon="workflow" onClick={() => go('/ai-stack/control-plane', 'workflows')} />
                <Metric value={n(stats?.onto_integration)} label="integrations" icon="link" onClick={() => go('/ai-stack/control-plane', 'integrations')} />
                <Metric value={n(stats?.graph_nodes)} label="graph nodes" icon="network" onClick={() => go('/ai-stack/control-plane', 'explorer')} />
                <Metric value={n(stats?.total_embeddings)} label="embeddings" icon="cube" onClick={() => go('/ai-stack/control-plane', 'knowledge')} />
              </LayerRow>

              <LayerRow
                id="data" index="01" icon="database" title="Data Plane" active={active === 'data'} onHover={setActive}
                description="Virtual data layer over your systems: FDW connections, simulators and files."
                onOpen={() => go('/ai-stack/data-plane')}
              >
                <Metric value={n(sourceCount)} label="data sources" icon="plug" />
                <Metric value={n(stats?.virtual_entities)} label="entities" icon="cube" />
                <Metric value={n(stats?.mapped_entities)} label="mapped" icon="link" />
                <Metric value={n(stats?.mapping_rules_active)} label="mapping rules" icon="route" />
              </LayerRow>

              <LayerRow
                id="ops" index="" icon="heartbeat" title="AI Ops" active={active === 'ops'} onHover={setActive}
                description="Checks and monitoring that run alongside every layer."
              >
                <TextLink onClick={() => go('/operations/diagnostics')}><Icon name="stethoscope" className="h-3.5 w-3.5 text-subtle-foreground" /> Diagnostics</TextLink>
                <TextLink onClick={() => go('/operations/health')}><Icon name="heartbeat" className="h-3.5 w-3.5 text-subtle-foreground" /> Health</TextLink>
              </LayerRow>
            </div>
          </div>
        </section>

        {/* Lists */}
        <div className="mt-10 grid gap-x-10 gap-y-10 lg:grid-cols-3">
          <ListSection title="Recent journeys" action={<TextLink onClick={() => go('/workspace/automation')}>All journeys</TextLink>}>
            {journeys === null && [0, 1, 2, 3].map(i => (
              <div key={i} className="flex items-center gap-3 py-3"><Skeleton className="h-4 w-full" /></div>
            ))}
            {journeys !== null && recent.length === 0 && (
              <p className="py-6 text-sm text-muted-foreground">No journeys yet. Create one in AI Automation.</p>
            )}
            {recent.map(j => {
              const status = journeyStatus(j);
              return (
                <button key={j.journeyId || j.id} type="button" onClick={() => nav(`/workspace/automation?journeyId=${encodeURIComponent(j.journeyId || j.id)}`)} className={rowBtn}>
                  <span className={cn(status === 'running' ? 'dot-live' : 'inline-block h-2 w-2 rounded-full bg-current', 'shrink-0', STATUS_TONE[status] || 'text-subtle-foreground')} aria-hidden="true" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-foreground group-hover/r:underline group-hover/r:underline-offset-4">{j.name || j.journeyId || j.id}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {typeLabel(j.type)} · <span className="capitalize">{status}</span>
                    </span>
                  </span>
                  <span className="shrink-0 text-xs text-subtle-foreground">{timeAgo(j.updated_at || j.created_at)}</span>
                </button>
              );
            })}
          </ListSection>

          <ListSection title="Solutions" action={<TextLink onClick={() => go('/workspace/apps')}>All solutions</TextLink>}>
            {APP_REGISTRY.slice(0, 5).map(app => (
              <button key={app.id} type="button" onClick={() => nav(`/apps/${app.id}`)} className={rowBtn}>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-foreground group-hover/r:underline group-hover/r:underline-offset-4">{app.name}</span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {app.kpis.slice(0, 2).map(k => `${k.label} ${k.target}`).join(' · ')}
                  </span>
                </span>
                <Icon name="chevron-right" className="h-4 w-4 shrink-0 text-subtle-foreground transition-transform duration-300 ease-brand-out group-hover/r:translate-x-0.5 group-hover/r:text-foreground" />
              </button>
            ))}
          </ListSection>

          <ListSection title="Entities by system" action={<TextLink onClick={() => go('/ai-stack/data-plane')}>Data Plane</TextLink>}>
            {!stats && loading && [0, 1, 2, 3].map(i => (
              <div key={i} className="py-3"><Skeleton className="h-4 w-full" /></div>
            ))}
            {!loading && systems.length === 0 && (
              <p className="py-6 text-sm text-muted-foreground">No mapped systems yet. Connect a source in the Data Plane.</p>
            )}
            {systems.map(([key, count]) => (
              <div key={key} className="py-2.5">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="truncate text-sm text-foreground">{systemLabel(key)}</span>
                  <span className="num text-sm text-muted-foreground">{count}</span>
                </div>
                <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-surface-3">
                  <div
                    className="h-full origin-left rounded-full bg-primary transition-transform duration-slow ease-brand-out"
                    style={{ width: `${(count / maxSystem) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </ListSection>
        </div>
      </div>
    </Layout>
  );
}
