import { useState, useEffect, useMemo } from 'react';
import Layout from '@/components/Layout';
import { useNavigate } from 'react-router-dom';
import { APP_REGISTRY } from '@/config/appRegistry';
import {
  Database, Layers, Zap, Server, Globe, FileText, Upload, Rss,
  Bot, Shield, Workflow, LayoutGrid, Sparkles,
  Network, Search, BookOpen, ArrowUpRight,
  HeartPulse, Play, Activity,
} from 'lucide-react';
import { apiClient } from '@/services/apiClient';

const PLATE_STYLES: Record<string, { plate: string; glow: string; text: string; statBg: string; iconBg: string; heading: string; btnBg: string; btnHover: string }> = {
  emerald: {
    plate: 'bg-gradient-to-b from-emerald-50 to-emerald-100/80 dark:from-emerald-950/80 dark:to-emerald-950/60 border-emerald-200 dark:border-emerald-500/20',
    glow: 'shadow-sm dark:shadow-[0_0_40px_-10px_rgba(16,185,129,0.2)]',
    text: 'text-emerald-600 dark:text-emerald-400',
    statBg: 'bg-emerald-100 dark:bg-emerald-500/10',
    iconBg: 'bg-emerald-200/60 dark:bg-emerald-500/15',
    heading: 'text-emerald-900 dark:text-white',
    btnBg: 'bg-emerald-100/80 dark:bg-emerald-500/10',
    btnHover: 'hover:bg-emerald-200 dark:hover:bg-emerald-500/20',
  },
  blue: {
    plate: 'bg-gradient-to-b from-blue-50 to-blue-100/80 dark:from-blue-950/80 dark:to-blue-950/60 border-blue-200 dark:border-blue-500/20',
    glow: 'shadow-sm dark:shadow-[0_0_40px_-10px_rgba(59,130,246,0.2)]',
    text: 'text-blue-600 dark:text-blue-400',
    statBg: 'bg-blue-100 dark:bg-blue-500/10',
    iconBg: 'bg-blue-200/60 dark:bg-blue-500/15',
    heading: 'text-blue-900 dark:text-white',
    btnBg: 'bg-blue-100/80 dark:bg-blue-500/10',
    btnHover: 'hover:bg-blue-200 dark:hover:bg-blue-500/20',
  },
  purple: {
    plate: 'bg-gradient-to-b from-purple-50 to-purple-100/80 dark:from-purple-950/80 dark:to-purple-950/60 border-purple-200 dark:border-purple-500/20',
    glow: 'shadow-sm dark:shadow-[0_0_40px_-10px_rgba(168,85,247,0.2)]',
    text: 'text-purple-600 dark:text-purple-400',
    statBg: 'bg-purple-100 dark:bg-purple-500/10',
    iconBg: 'bg-purple-200/60 dark:bg-purple-500/15',
    heading: 'text-purple-900 dark:text-white',
    btnBg: 'bg-purple-100/80 dark:bg-purple-500/10',
    btnHover: 'hover:bg-purple-200 dark:hover:bg-purple-500/20',
  },
  amber: {
    plate: 'bg-gradient-to-b from-amber-50 to-amber-100/80 dark:from-amber-950/70 dark:to-amber-950/50 border-amber-200 dark:border-amber-500/20',
    glow: 'shadow-sm dark:shadow-[0_0_40px_-10px_rgba(245,158,11,0.15)]',
    text: 'text-amber-600 dark:text-amber-400',
    statBg: 'bg-amber-100 dark:bg-amber-500/10',
    iconBg: 'bg-amber-200/60 dark:bg-amber-500/15',
    heading: 'text-amber-900 dark:text-white',
    btnBg: 'bg-amber-100/80 dark:bg-amber-500/10',
    btnHover: 'hover:bg-amber-200 dark:hover:bg-amber-500/20',
  },
  teal: {
    plate: 'bg-gradient-to-b from-teal-50 to-teal-100/80 dark:from-teal-950/80 dark:to-teal-950/60 border-teal-200 dark:border-teal-500/20',
    glow: 'shadow-sm dark:shadow-[0_0_40px_-10px_rgba(20,184,166,0.15)]',
    text: 'text-teal-600 dark:text-teal-400',
    statBg: 'bg-teal-100 dark:bg-teal-500/10',
    iconBg: 'bg-teal-200/60 dark:bg-teal-500/15',
    heading: 'text-teal-900 dark:text-white',
    btnBg: 'bg-teal-100/80 dark:bg-teal-500/10',
    btnHover: 'hover:bg-teal-200 dark:hover:bg-teal-500/20',
  },
};

function StatPill({ label, value, color, onClick }: { label: string; value: string | number; color: string; onClick?: () => void }) {
  const s = PLATE_STYLES[color];
  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick ? (e: React.MouseEvent) => { e.stopPropagation(); onClick(); } : undefined}
      onKeyDown={onClick ? (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onClick(); }
      } : undefined}
      className={`rounded-lg ${s.statBg} px-3 py-2 text-center ${onClick ? 'hover:brightness-125 transition-all cursor-pointer' : ''}`}
    >
      <div className={`text-sm font-bold ${s.heading}`}>{value}</div>
      <div className="text-[10px] text-muted-foreground">{label}</div>
    </div>
  );
}

function SourceIcon({ label, icon: Icon, color, onClick }: { label: string; icon: React.ElementType; color: string; onClick?: () => void }) {
  const s = PLATE_STYLES[color];
  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick ? (e: React.MouseEvent) => { e.stopPropagation(); onClick(); } : undefined}
      className="flex flex-col items-center gap-1 hover:brightness-125 transition-all"
    >
      <div className={`w-8 h-8 rounded-lg ${s.iconBg} flex items-center justify-center`}>
        <Icon className={`h-4 w-4 ${s.text}`} />
      </div>
      <span className="text-[9px] text-muted-foreground">{label}</span>
    </div>
  );
}

export default function HomePage() {
  const nav = useNavigate();
  const [stats, setStats] = useState<any>(null);
  const [journeyCount, setJourneyCount] = useState(0);
  const appStats = useMemo(() => {
    const available = APP_REGISTRY.filter(a => a.status === 'available').length;
    const comingSoon = APP_REGISTRY.filter(a => a.status === 'coming_soon').length;
    return { available, comingSoon, total: APP_REGISTRY.length };
  }, []);

  useEffect(() => {
    apiClient.get<any>('/api/v1/control-plane/stats').then(setStats).catch(() => {});
    apiClient.get<any>('/api/v1/journeys/').then(d => {
      if (d?.total != null) {
        setJourneyCount(d.total);
      } else {
        const items = d?.data || d?.journeys || d?.items || [];
        setJourneyCount(Array.isArray(items) ? items.length : 0);
      }
    }).catch(() => {});
  }, []);

  const go = (path: string, tab?: string) => {
    nav(tab ? `${path}?tab=${tab}` : path);
  };

  return (
    <Layout>
      <div className="flex items-start justify-center min-h-full p-6">
        <div className="flex gap-5 w-full max-w-[1000px]">

          {/* ── Left: Main Stack ─────────────────────────── */}
          <div className="flex-1 space-y-3 min-w-0">

            {/* Solutions */}
            <div
              className={`w-full rounded-2xl border ${PLATE_STYLES.amber.plate} ${PLATE_STYLES.amber.glow} transition-all duration-300 hover:brightness-110`}
            >
              <div className="p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`w-9 h-9 rounded-lg ${PLATE_STYLES.amber.iconBg} flex items-center justify-center`}>
                    <LayoutGrid className={`h-5 w-5 ${PLATE_STYLES.amber.text}`} />
                  </div>
                  <div>
                    <h2 className={`text-[15px] font-semibold ${PLATE_STYLES.amber.heading}`}>Solutions</h2>
                    <p className="text-[11px] text-muted-foreground">Solutions Catalogue and AI Automation</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <button onClick={() => go('/workspace/apps')}
                    className={`flex items-center gap-3 rounded-lg ${PLATE_STYLES.amber.btnBg} px-4 py-3 ${PLATE_STYLES.amber.btnHover} transition-colors text-left`}>
                    <LayoutGrid className={`h-5 w-5 ${PLATE_STYLES.amber.text} shrink-0`} />
                    <div className="flex-1">
                      <div className={`text-xs font-medium ${PLATE_STYLES.amber.heading}`}>Solutions</div>
                      <div className="text-[10px] text-muted-foreground">Enterprise applications</div>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <div className="text-center">
                        <div className="text-sm font-bold text-green-600 dark:text-green-400">{appStats.available}</div>
                        <div className="text-[8px] text-muted-foreground">Active</div>
                      </div>
                      <div className="text-center">
                        <div className={`text-sm font-bold ${PLATE_STYLES.amber.text}`}>{appStats.comingSoon}</div>
                        <div className="text-[8px] text-muted-foreground">Planned</div>
                      </div>
                    </div>
                  </button>
                <button onClick={() => go('/workspace/automation')}
                    className={`flex items-center gap-3 rounded-lg ${PLATE_STYLES.amber.btnBg} px-4 py-3 ${PLATE_STYLES.amber.btnHover} transition-colors text-left`}>
                  <Sparkles className={`h-5 w-5 ${PLATE_STYLES.amber.text} shrink-0`} />
                  <div className="flex-1">
                    <div className={`text-xs font-medium ${PLATE_STYLES.amber.heading}`}>AI Automation</div>
                      <div className="text-[10px] text-muted-foreground">Workflow automations</div>
                    </div>
                    <div className="text-center shrink-0">
                      <div className={`text-sm font-bold ${PLATE_STYLES.amber.text}`}>{journeyCount}</div>
                      <div className="text-[8px] text-muted-foreground">Journeys</div>
                    </div>
                  </button>
                </div>
              </div>
            </div>

            <div className="flex justify-center"><div className="w-px h-4 bg-border" /></div>

            {/* Reasoning Plane */}
            <button
              onClick={() => go('/ai-stack/reasoning')}
              className={`w-full text-left rounded-2xl border ${PLATE_STYLES.purple.plate} ${PLATE_STYLES.purple.glow} transition-all duration-300 hover:scale-[1.005] hover:brightness-110 group`}
              style={{ transform: 'perspective(1200px) rotateX(6deg)' }}
            >
              <div className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-lg ${PLATE_STYLES.purple.iconBg} flex items-center justify-center`}>
                      <Zap className={`h-5 w-5 ${PLATE_STYLES.purple.text}`} />
                    </div>
                    <div>
                      <h2 className={`text-[15px] font-semibold ${PLATE_STYLES.purple.heading}`}>Reasoning Plane</h2>
                      <p className="text-[11px] text-muted-foreground">ReAct agent with tool orchestration and policy guardrails</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="grid grid-cols-3 gap-3 mb-3">
                  <StatPill label="Natural Language" value="AI Copilot" color="purple"
                    onClick={() => { go('/ai-stack/reasoning', 'copilot'); }} />
                  <StatPill label="Registered" value={`ReAct Tools (${stats?.tools_count || 14})`} color="purple"
                    onClick={() => { go('/ai-stack/reasoning', 'tools'); }} />
                  <StatPill label="RAG Validation" value="Planning Playground" color="purple"
                    onClick={() => { go('/ai-stack/reasoning', 'playground'); }} />
                </div>
                <div className="flex items-center gap-6 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1.5"><Bot className={`h-3 w-3 ${PLATE_STYLES.purple.text}`} /> LLM-driven planning loop</span>
                <span className="flex items-center gap-1.5"><Shield className={`h-3 w-3 ${PLATE_STYLES.purple.text}`} /> Pre-execution policy checks</span>
                <span className="flex items-center gap-1.5"><Workflow className={`h-3 w-3 ${PLATE_STYLES.purple.text}`} /> Multi-system orchestration</span>
                </div>
              </div>
            </button>

            <div className="flex justify-center"><div className="w-px h-4 bg-border" /></div>

            {/* Control Plane */}
            <button
              onClick={() => go('/ai-stack/control-plane')}
              className={`w-full text-left rounded-2xl border ${PLATE_STYLES.blue.plate} ${PLATE_STYLES.blue.glow} transition-all duration-300 hover:scale-[1.005] hover:brightness-110 group`}
              style={{ transform: 'perspective(1200px) rotateX(12deg)' }}
            >
              <div className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-lg ${PLATE_STYLES.blue.iconBg} flex items-center justify-center`}>
                      <Layers className={`h-5 w-5 ${PLATE_STYLES.blue.text}`} />
                    </div>
                    <div>
                      <h2 className={`text-[15px] font-semibold ${PLATE_STYLES.blue.heading}`}>Control Plane</h2>
                      <p className="text-[11px] text-muted-foreground">Enterprise ontology, knowledge graph, and semantic index</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="grid grid-cols-6 gap-2 mb-3">
                  <StatPill label="Schemas" value={stats?.onto_schema ?? '—'} color="blue"
                    onClick={() => { go('/ai-stack/control-plane', 'knowledge'); }} />
                  <StatPill label="Policies" value={stats?.onto_policy ?? '—'} color="blue"
                    onClick={() => { go('/ai-stack/control-plane', 'policies'); }} />
                  <StatPill label="Workflows" value={stats?.onto_workflow ?? '—'} color="blue"
                    onClick={() => { go('/ai-stack/control-plane', 'workflows'); }} />
                  <StatPill label="Integrations" value={stats?.onto_integration ?? '—'} color="blue"
                    onClick={() => { go('/ai-stack/control-plane', 'integrations'); }} />
                  <StatPill label="Graph Nodes" value={stats?.graph_nodes ?? '—'} color="blue"
                    onClick={() => { go('/ai-stack/control-plane', 'explorer'); }} />
                  <StatPill label="Embeddings" value={stats?.total_embeddings ?? '—'} color="blue"
                    onClick={() => { go('/ai-stack/control-plane', 'knowledge'); }} />
                </div>
                <div className="flex items-center gap-6 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1.5"><Network className={`h-3 w-3 ${PLATE_STYLES.blue.text}`} /> Apache AGE knowledge graph</span>
                <span className="flex items-center gap-1.5"><Search className={`h-3 w-3 ${PLATE_STYLES.blue.text}`} /> Hybrid vector + graph search</span>
                <span className="flex items-center gap-1.5"><BookOpen className={`h-3 w-3 ${PLATE_STYLES.blue.text}`} /> SCOR-aligned supply chain ontology</span>
                </div>
              </div>
            </button>

            <div className="flex justify-center"><div className="w-px h-4 bg-border" /></div>

            {/* Data Plane */}
            <button
              onClick={() => go('/ai-stack/data-plane')}
              className={`w-full text-left rounded-2xl border ${PLATE_STYLES.emerald.plate} ${PLATE_STYLES.emerald.glow} transition-all duration-300 hover:scale-[1.005] hover:brightness-110 group`}
              style={{ transform: 'perspective(1200px) rotateX(18deg)' }}
            >
              <div className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-lg ${PLATE_STYLES.emerald.iconBg} flex items-center justify-center`}>
                      <Database className={`h-5 w-5 ${PLATE_STYLES.emerald.text}`} />
                    </div>
                    <div>
                      <h2 className={`text-[15px] font-semibold ${PLATE_STYLES.emerald.heading}`}>Data Plane</h2>
                      <p className="text-[11px] text-muted-foreground">Virtual data layer — FDW connections, simulators, enterprise data sources</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="grid grid-cols-4 gap-3 mb-3">
                  <StatPill label="Data Sources" value={stats?.entities_by_system ? Object.keys(stats.entities_by_system).length : 6} color="emerald" />
                  <StatPill label="Entities" value={stats?.virtual_entities ?? '—'} color="emerald" />
                  <StatPill label="Mapped" value={stats?.mapped_entities ?? '—'} color="emerald" />
                  <StatPill label="Mapping Rules" value={stats?.mapping_rules_active ?? '—'} color="emerald" />
                </div>
                <div className="flex items-center justify-center gap-5 pt-1">
                  <SourceIcon label="Salesforce" icon={Globe} color="emerald" />
                  <SourceIcon label="Oracle" icon={Database} color="emerald" />
                  <SourceIcon label="SAP" icon={Server} color="emerald" />
                  <SourceIcon label="Google Drive" icon={FileText} color="emerald" />
                  <SourceIcon label="Social" icon={Rss} color="emerald" />
                  <SourceIcon label="File Uploads" icon={Upload} color="emerald" />
                </div>
              </div>
            </button>
          </div>

          {/* ── Right: AI Ops vertical strip ─────────────── */}
          <div
            className={`w-[100px] shrink-0 rounded-2xl border ${PLATE_STYLES.teal.plate} ${PLATE_STYLES.teal.glow} flex flex-col items-center py-4 px-2 gap-3 self-stretch transition-all duration-300 hover:brightness-110`}
          >
            <div className={`w-8 h-8 rounded-lg ${PLATE_STYLES.teal.iconBg} flex items-center justify-center`}>
              <Activity className={`h-4 w-4 ${PLATE_STYLES.teal.text}`} />
            </div>
            <span className={`text-[11px] font-semibold ${PLATE_STYLES.teal.heading}`}>AI Ops</span>

            <div className="flex-1" />

            <button onClick={() => go('/operations/diagnostics')}
              className={`w-full flex flex-col items-center gap-1 rounded-lg ${PLATE_STYLES.teal.btnBg} px-2 py-3 ${PLATE_STYLES.teal.btnHover} transition-colors`}>
              <Play className={`h-4 w-4 ${PLATE_STYLES.teal.text}`} />
              <span className={`text-[9px] font-medium ${PLATE_STYLES.teal.heading}`}>Diagnostics</span>
            </button>

            <button onClick={() => go('/operations/health')}
              className={`w-full flex flex-col items-center gap-1 rounded-lg ${PLATE_STYLES.teal.btnBg} px-2 py-3 ${PLATE_STYLES.teal.btnHover} transition-colors`}>
              <HeartPulse className={`h-4 w-4 ${PLATE_STYLES.teal.text}`} />
              <span className={`text-[9px] font-medium ${PLATE_STYLES.teal.heading}`}>Health</span>
            </button>

            <div className="flex-1" />
          </div>

        </div>
      </div>
    </Layout>
  );
}
