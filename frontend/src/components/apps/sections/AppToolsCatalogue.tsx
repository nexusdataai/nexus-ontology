import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { AppConfig } from '@/config/appRegistry';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { Chips, SearchInput, StatusPill, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';

interface Props { app: AppConfig; }

interface RegistryTool {
  toolId: string;
  description?: string;
  group?: string;
  toolKind?: string;
  riskLevel?: string;
  requiresApproval?: boolean;
  connectorApi?: string | null;
}

/**
 * The group each solution's tools are registered under in the tool registry.
 * The supply-chain solutions share one group.
 */
const GROUP_OF: Record<string, string> = {
  'order-to-cash': 'o2c',
  'customer-360': 'customer-360',
  'esg-sustainability': 'esg',
  'demand-forecasting': 'supply-chain',
  'inventory-optimization': 'supply-chain',
  'procurement-analytics': 'supply-chain',
  'production-quality': 'supply-chain',
  'supply-chain-risk': 'supply-chain',
};

type Kind = 'all' | 'read' | 'write';
const isWrite = (t: RegistryTool) => t.toolKind === 'mutate' || /write/i.test(t.riskLevel || '');
const nameOf = (id: string) => id.replace(/[_-]+/g, ' ').replace(/^\w/, c => c.toUpperCase());
const riskWord = (r?: string) => String(r || '').replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());

/** Tools: the agent tools registered for this solution, read from the tool registry. */
export function AppToolsCatalogue({ app }: Props) {
  const nav = useNavigate();
  const [tools, setTools] = useState<RegistryTool[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState<Kind>('all');
  const group = GROUP_OF[app.id];

  const load = () => {
    setTools(null);
    setFailed(false);
    apiClient.get<any>('/api/v1/tools-registry')
      .then(d => {
        const items: RegistryTool[] = Array.isArray(d) ? d : d?.items || [];
        setTools(group ? items.filter(t => t.group === group) : []);
      })
      .catch(() => { setFailed(true); setTools([]); });
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [app.id]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (tools || [])
      .filter(t => kind === 'all' || (kind === 'write') === isWrite(t))
      .filter(t => !q || `${t.toolId} ${t.description || ''} ${t.connectorApi || ''}`.toLowerCase().includes(q))
      .sort((a, b) => a.toolId.localeCompare(b.toolId));
  }, [tools, query, kind]);

  const writes = (tools || []).filter(isWrite).length;
  const shared = group === 'supply-chain';

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-lg font-medium tracking-tight text-foreground">Tools</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            The agent tools registered for {app.name}{shared ? ', shared with the other supply-chain solutions' : ''}. This list comes from the tool registry.
          </p>
        </div>
        <Button variant="outline" onClick={() => nav('/ai-stack/reasoning?tab=tools-reg')}>
          Open tool registry <Icon name="arrow-right" className="h-3.5 w-3.5" />
        </Button>
      </header>

      {tools === null ? (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-10 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      ) : failed ? (
        <EmptyState
          icon="alert-triangle"
          title="The tool registry could not be read"
          description="Check that the backend is running, then try again."
          action={<Button variant="outline" onClick={load}>Try again</Button>}
        />
      ) : tools.length === 0 ? (
        <EmptyState icon="wrench" title="No tools registered for this solution" description="Tools appear here once they are registered under this solution in the tool registry." />
      ) : (
        <>
          <Toolbar>
            <Chips<Kind>
              label="Tool kind"
              value={kind}
              onChange={setKind}
              options={[
                { value: 'all', label: 'All', count: tools.length },
                { value: 'read', label: 'Read', count: tools.length - writes },
                { value: 'write', label: 'Write', count: writes },
              ]}
            />
            <ToolbarSpacer />
            <SearchInput value={query} onChange={setQuery} placeholder="Search tools" />
          </Toolbar>

          {visible.length === 0 ? (
            <EmptyState icon="search" title="No tools match" description="Try a different search or kind." />
          ) : (
            <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-card shadow-xs">
              {visible.map(t => (
                <li key={t.toolId} className="flex flex-wrap items-start gap-x-4 gap-y-2 px-5 py-4">
                  <div className="min-w-0 flex-1 basis-80">
                    <p className="truncate text-sm font-medium text-foreground">{nameOf(t.toolId)}</p>
                    <p className="mt-0.5 font-mono text-xs text-subtle-foreground">{t.toolId}</p>
                    {t.description && <p className="mt-1.5 line-clamp-2 text-sm text-muted-foreground">{t.description}</p>}
                    {t.connectorApi && <p className="mt-1.5 text-xs text-muted-foreground">Calls <span className="font-mono text-foreground">{t.connectorApi}</span></p>}
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <StatusPill tone={isWrite(t) ? 'warning' : 'neutral'}>{isWrite(t) ? 'Write' : 'Read'}</StatusPill>
                    {t.riskLevel && <StatusPill tone="neutral" className="font-normal text-muted-foreground">{riskWord(t.riskLevel)}</StatusPill>}
                    {t.requiresApproval && <StatusPill tone="info">Needs approval</StatusPill>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
