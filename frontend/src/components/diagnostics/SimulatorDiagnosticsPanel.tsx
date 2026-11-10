import { useState, useCallback, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, Play, ChevronDown, ChevronRight, HardDrive, Database, RefreshCw, Clock, Zap, BarChart3, ExternalLink } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { getSimulatorConfig } from '@/services/simulatorLink';
import { Section, StatusBadge } from './_shared';

interface DiagCheck {
  name: string;
  status: string;
  message: string;
  details: Record<string, any>;
}

interface DiagSection {
  status: string;
  checks: DiagCheck[];
}

interface DiagReport {
  timestamp: string;
  overall_status: string;
  sections: {
    s3_source_data: DiagSection;
    redis_cache_health: DiagSection;
    data_loading: DiagSection;
    ttl_and_refresh: DiagSection;
    data_access: DiagSection;
    data_volume: DiagSection;
  };
}




function CheckTable({ checks }: { checks: DiagCheck[] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-border text-left text-xs text-muted-foreground">
          <th className="py-1.5 pr-4">Component</th>
          <th className="py-1.5 pr-4">Status</th>
          <th className="py-1.5">Details</th>
        </tr>
      </thead>
      <tbody>
        {checks.map((c, i) => (
          <tr key={i} className="border-b border-border">
            <td className="py-2 pr-4 font-medium">{c.name}</td>
            <td className="py-2 pr-4"><StatusBadge status={c.status} /></td>
            <td className="py-2 text-muted-foreground">{c.message}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RedisDetails({ check }: { check: DiagCheck }) {
  const d = check.details;
  const hasMetrics = d.dbsize !== undefined || d.used_memory_mb !== undefined;
  return (
    <div className="space-y-3">
      {check.message && (
        <div className={`text-xs px-3 py-2 rounded-md ${check.status === 'fail' ? 'bg-destructive/10 text-destructive' : check.status === 'warn' ? 'bg-warning/10 text-warning' : 'text-muted-foreground'}`}>
          {check.message}
        </div>
      )}
      {hasMetrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Total Keys" value={d.dbsize ?? '-'} />
          <MetricCard label="Memory Used" value={d.used_memory_mb != null ? `${d.used_memory_mb} MB` : '-'} />
          <MetricCard label="Peak Memory" value={d.used_memory_peak_mb != null ? `${d.used_memory_peak_mb} MB` : '-'} />
          <MetricCard label="Max Memory" value={typeof d.maxmemory_mb === 'number' ? `${d.maxmemory_mb} MB` : d.maxmemory_mb ?? '-'} />
        </div>
      )}
      {d.memory_usage_pct !== undefined && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Memory Usage</span>
            <span>{d.memory_usage_pct}%</span>
          </div>
          <div className="h-2 bg-secondary rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${d.memory_usage_pct > 80 ? 'bg-destructive' : d.memory_usage_pct > 60 ? 'bg-warning' : 'bg-success'}`}
              style={{ width: `${Math.min(d.memory_usage_pct, 100)}%` }}
            />
          </div>
        </div>
      )}
      <div className="flex items-center gap-2 text-xs flex-wrap">
        <span className="text-muted-foreground">Eviction Policy:</span>
        <Badge variant="outline" className={d.maxmemory_policy === 'allkeys-lru' ? 'bg-warning/10 text-warning border-warning/30' : 'bg-secondary'}>
          {d.maxmemory_policy ?? 'unknown'}
        </Badge>
        <span className="text-muted-foreground ml-4">Default TTL:</span>
        <span>{d.default_ttl_seconds ? `${Math.round(d.default_ttl_seconds / 3600)}h` : '-'}</span>
        {d.fallback_active && (
          <Badge variant="outline" className="bg-warning/10 text-warning border-warning/30 ml-4">
            Fallback Active ({d.fallback_keys ?? 0} keys)
          </Badge>
        )}
      </div>
      {d.keys_per_simulator && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {Object.entries(d.keys_per_simulator as Record<string, number>).map(([name, count]) => (
            <div key={name} className="bg-card border border-border rounded-lg p-2 text-center">
              <div className="text-xs text-muted-foreground">{name}</div>
              <div className="text-sm font-semibold text-foreground">{count} tables</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-card border border-border rounded-lg p-3 text-center">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold mt-0.5 text-foreground">{value}</div>
    </div>
  );
}

function VolumeDetails({ checks }: { checks: DiagCheck[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  return (
    <div className="space-y-2">
      {checks.map((c, i) => (
        <div key={i} className="border border-border/50 rounded-lg">
          <div
            className="flex items-center justify-between p-2.5 cursor-pointer"
            onClick={() => setExpanded(expanded === c.name ? null : c.name)}
          >
            <div className="flex items-center gap-2 text-xs">
              {expanded === c.name ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
              <span className="font-medium">{c.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{c.message}</span>
              <StatusBadge status={c.status} />
            </div>
          </div>
          {expanded === c.name && c.details.zero_row_tables && c.details.zero_row_count > 0 && (
            <div className="px-3 pb-3 border-t border-border/50">
              <div className="text-xs text-warning mt-2 mb-1">Empty tables ({c.details.zero_row_count}):</div>
              <div className="flex flex-wrap gap-1">
                {(c.details.zero_row_tables as string[]).map(t => (
                  <Badge key={t} variant="outline" className="bg-warning/10 text-warning border-warning/30 text-xs">{t}</Badge>
                ))}
                {c.details.zero_row_count > 10 && (
                  <Badge variant="outline" className="bg-secondary text-xs">+{c.details.zero_row_count - 10} more</Badge>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function SimulatorDiagnosticsPanel() {
  const [report, setReport] = useState<DiagReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [simulatorUiUrl, setSimulatorUiUrl] = useState('http://localhost:8082');

  useEffect(() => {
    getSimulatorConfig().then(cfg => {
      if (cfg.uiUrl) setSimulatorUiUrl(cfg.uiUrl);
    }).catch(() => {});
  }, []);

  const runDiagnostics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.post<DiagReport>('/api/v1/diagnostics/simulators', {});
      setReport(data);
    } catch (e: any) {
      setError(e.message || 'Diagnostics failed');
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="page space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-medium tracking-tight text-foreground">Simulator Reachability</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Lightweight health and catalog checks against the remote nexus-simulator service.
            Admin, seed, and table tools live in the simulator UI.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {report && <StatusBadge status={report.overall_status} />}
          <Button variant="outline" asChild>
            <a href={simulatorUiUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4 mr-2" /> Open Simulator
            </a>
          </Button>
          <Button onClick={runDiagnostics} disabled={loading}>
            {loading ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Running checks</> : <><Play className="h-4 w-4 mr-2" /> Run checks</>}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/25 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          The checks could not run: {error}
        </div>
      )}

      {!report && !loading && !error && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border-strong py-16 text-muted-foreground">
          <Database className="h-12 w-12 mb-4 opacity-30" />
          <p className="text-sm">Run the checks to see the state of the simulator pipeline</p>
        </div>
      )}

      {report && (
        <div className="space-y-3">
          {report.timestamp && (
            <div className="text-xs text-muted-foreground">Last run: {new Date(report.timestamp).toLocaleString()}</div>
          )}

          <Section title="S3 Source Data" icon={HardDrive} status={report.sections.s3_source_data.status}>
            <CheckTable checks={report.sections.s3_source_data.checks} />
          </Section>

          <Section title="Redis Cache Health" icon={Database} status={report.sections.redis_cache_health.status}>
            {report.sections.redis_cache_health.checks.map((c, i) => (
              <RedisDetails key={i} check={c} />
            ))}
          </Section>

          <Section title="Data Loading Status" icon={RefreshCw} status={report.sections.data_loading.status}>
            <CheckTable checks={report.sections.data_loading.checks} />
          </Section>

          <Section title="TTL & Refresh" icon={Clock} status={report.sections.ttl_and_refresh.status}>
            <CheckTable checks={report.sections.ttl_and_refresh.checks} />
          </Section>

          <Section title="Backend Data Access" icon={Zap} status={report.sections.data_access.status}>
            <CheckTable checks={report.sections.data_access.checks} />
          </Section>

          <Section title="Data Volume Summary" icon={BarChart3} status={report.sections.data_volume.status} defaultOpen={false}>
            <VolumeDetails checks={report.sections.data_volume.checks} />
          </Section>
        </div>
      )}
    </div>
  );
}
