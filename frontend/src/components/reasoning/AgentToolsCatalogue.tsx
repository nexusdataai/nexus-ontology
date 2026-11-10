/**
 * Tool catalogue: every tool the agent can call, with a sheet to inspect one
 * and run it with real inputs.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import {
  Chips, CodeBlock, DetailSheet, Field, InlineError, KeyValues, SearchInput, StatusPill, SubHeading, TableShell, Toolbar, ToolbarSpacer,
} from '@/components/ds/kit';
import { apiClient } from '@/services/apiClient';
import { cn } from '@/lib/utils';
import { RiskPill, ToolSystem } from './toolMeta';

interface RegisteredTool {
  name: string;
  description: string;
  risk_level: string;
  requires_approval: boolean;
  parameters: { type: string; properties?: Record<string, { type: string; description?: string }>; required?: string[] };
  /** Sent by the catalogue endpoint when known. */
  group?: string;
  tags?: string[];
  connector_api?: string | null;
}

interface ToolExecResult {
  tool: string;
  risk_level: string;
  success: boolean;
  result: any;
  elapsed_ms: number;
}

type Scope = 'all' | 'read' | 'write';

export default function AgentToolsCatalogue() {
  const [tools, setTools] = useState<RegisteredTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testTool, setTestTool] = useState<RegisteredTool | null>(null);
  const [testArgs, setTestArgs] = useState<Record<string, string>>({});
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState<ToolExecResult | null>(null);
  const [ddbCount, setDdbCount] = useState<number | null>(null);
  // Local view state
  const [search, setSearch] = useState('');
  const [scope, setScope] = useState<Scope>('all');
  const [showSchema, setShowSchema] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    apiClient.get<{ tools: RegisteredTool[]; total: number }>('/api/v1/control-plane/tools')
      .then(d => { setTools(d.tools || []); setError(null); })
      .catch(e => setError(e.message || 'Failed to load tools'))
      .finally(() => setLoading(false));
    // The durable copy of this catalogue lives in the tools registry. Its row
    // count shows whether every tool is saved there.
    apiClient.get<{ total: number }>('/api/v1/tools-registry')
      .then(r => setDdbCount(r.total ?? null))
      .catch(() => setDdbCount(null));
  }, []);

  useEffect(() => { load(); }, [load]);

  const readTools = tools.filter(t => t.risk_level === 'read_only');
  const writeTools = tools.filter(t => t.risk_level !== 'read_only');

  const openTest = (tool: RegisteredTool) => {
    setTestTool(tool);
    setTestArgs({});
    setExecResult(null);
    setShowSchema(false);
  };

  const runTest = useCallback(async () => {
    if (!testTool) return;
    setExecuting(true);
    setExecResult(null);
    try {
      const parsedArgs: Record<string, any> = {};
      for (const [k, v] of Object.entries(testArgs)) {
        if (!v.trim()) continue;
        try { parsedArgs[k] = JSON.parse(v); } catch { parsedArgs[k] = v; }
      }
      const result = await apiClient.post<ToolExecResult>(
        `/api/v1/control-plane/tools/${testTool.name}/execute`,
        { arguments: parsedArgs },
      );
      setExecResult(result);
    } catch (e: any) {
      setExecResult({ tool: testTool.name, risk_level: testTool.risk_level, success: false, result: { error: e.message }, elapsed_ms: 0 });
    } finally {
      setExecuting(false);
    }
  }, [testTool, testArgs]);

  const paramEntries = testTool?.parameters?.properties
    ? Object.entries(testTool.parameters.properties)
    : [];
  const requiredParams = new Set(testTool?.parameters?.required || []);

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    const pool = scope === 'read' ? readTools : scope === 'write' ? writeTools : [...readTools, ...writeTools];
    if (!q) return pool;
    return pool.filter(t =>
      t.name.toLowerCase().includes(q)
      || (t.description || '').toLowerCase().includes(q)
      || (t.connector_api || '').toLowerCase().includes(q)
      || (t.tags || []).some(tag => tag.toLowerCase().includes(q)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tools, search, scope]);

  return (
    <div className="page pb-24">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-medium tracking-tight text-foreground">Tool catalogue</h2>
        <p className="max-w-2xl text-sm text-muted-foreground">
          {loading ? 'Loading the tools the agent can call.' : (
            <>
              The agent can call <span className="num text-foreground">{tools.length}</span> tools: <span className="num text-foreground">{readTools.length}</span> read data and <span className="num text-foreground">{writeTools.length}</span> change it.
              {ddbCount !== null && <> <span className="num text-foreground">{ddbCount}</span> are saved in the tools registry.</>}
              {' '}Open a tool to see its inputs and run it.
            </>
          )}
        </p>
      </div>

      <Toolbar className="mt-5">
        <SearchInput value={search} onChange={setSearch} placeholder="Search tools" />
        <Chips<Scope>
          label="Filter by access"
          value={scope}
          onChange={setScope}
          options={[
            { value: 'all', label: 'All', count: tools.length },
            { value: 'read', label: 'Read', count: readTools.length },
            { value: 'write', label: 'Write', count: writeTools.length },
          ]}
        />
        <ToolbarSpacer />
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <Icon name={loading ? 'spinner' : 'refresh'} className={cn(loading && 'animate-spin')} /> Refresh
        </Button>
      </Toolbar>

      <div className="mt-4">
        {error ? (
          <InlineError onRetry={load}>The tools could not be loaded. {error}</InlineError>
        ) : loading ? (
          <TableShell>
            <div className="divide-y divide-border" aria-busy="true">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4 px-4 py-3.5">
                  <div className="flex-1 space-y-2"><Skeleton className="h-4 w-48" /><Skeleton className="h-3 w-2/3" /></div>
                  <Skeleton className="hidden h-4 w-24 md:block" />
                  <Skeleton className="h-4 w-20" />
                </div>
              ))}
            </div>
          </TableShell>
        ) : tools.length === 0 ? (
          <EmptyState icon="wrench" title="No tools registered" description="The agent has no tools yet. Create one in the Builder tab." />
        ) : visible.length === 0 ? (
          <EmptyState icon="search" title="No tools match" description="Try another word or clear the filter." action={<Button variant="outline" size="sm" onClick={() => { setSearch(''); setScope('all'); }}>Clear filters</Button>} />
        ) : (
          <TableShell>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Tool</TableHead>
                  <TableHead className="hidden md:table-cell">Reaches</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead className="hidden lg:table-cell">Approval</TableHead>
                  <TableHead className="w-20 text-right"><span className="sr-only">Actions</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((tool, i) => (
                  <TableRow
                    key={tool.name}
                    tabIndex={0}
                    onClick={() => openTest(tool)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openTest(tool); } }}
                    style={{ ['--i' as any]: Math.min(i, 14) }}
                    className="rise group cursor-pointer hover:bg-surface-2/60 focus-visible:bg-surface-2/60 focus-visible:outline-none"
                  >
                    <TableCell className="w-full max-w-0">
                      <div className="truncate font-mono text-sm font-medium text-foreground">{tool.name}</div>
                      <div className="mt-0.5 line-clamp-2 text-sm text-muted-foreground md:line-clamp-1">{tool.description}</div>
                    </TableCell>
                    <TableCell className="hidden md:table-cell"><ToolSystem api={tool.connector_api} /></TableCell>
                    <TableCell><RiskPill risk={tool.risk_level} /></TableCell>
                    <TableCell className="hidden text-sm text-muted-foreground lg:table-cell">{tool.requires_approval ? <span className="text-foreground">Required</span> : 'Not needed'}</TableCell>
                    <TableCell className="text-right">
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100 dark:text-brand-hi">
                        <Icon name="play" className="h-3 w-3" /> Test
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableShell>
        )}
      </div>

      <DetailSheet
        open={!!testTool}
        onOpenChange={(o) => { if (!o) setTestTool(null); }}
        title={<span className="font-mono text-md">{testTool?.name}</span>}
        description={testTool?.description}
        meta={testTool && (
          <>
            <RiskPill risk={testTool.risk_level} variant="soft" />
            {testTool.requires_approval && <StatusPill tone="warning" variant="soft">Needs approval</StatusPill>}
          </>
        )}
        footer={(
          <>
            <Button variant="ghost" onClick={() => setTestTool(null)}>Close</Button>
            <Button onClick={runTest} disabled={executing}>
              <Icon name={executing ? 'spinner' : 'play'} className={cn(executing && 'animate-spin')} />
              {executing ? 'Running' : 'Run tool'}
            </Button>
          </>
        )}
      >
        {testTool && (
          <div className="space-y-7">
            <KeyValues items={[
              { label: 'Reaches', value: <ToolSystem api={testTool.connector_api} className="justify-end" /> },
              ...(testTool.connector_api ? [{ label: 'Connector API', value: testTool.connector_api, mono: true }] : []),
              ...(testTool.group ? [{ label: 'Group', value: testTool.group.replace(/_/g, ' ') }] : []),
              { label: 'Approval', value: testTool.requires_approval ? 'Required before it runs' : 'Not needed' },
              ...(testTool.tags?.length ? [{ label: 'Tags', value: testTool.tags.join(', ') }] : []),
            ]} />

            <section>
              <SubHeading>Parameters</SubHeading>
              {paramEntries.length === 0 ? (
                <p className="text-sm text-muted-foreground">This tool takes no parameters.</p>
              ) : (
                <div className="space-y-4">
                  {paramEntries.map(([key, schema]) => {
                    const numeric = schema.type === 'integer' || schema.type === 'number';
                    const id = `tool-param-${key}`;
                    return (
                      <Field
                        key={key}
                        htmlFor={id}
                        label={`${key}${requiredParams.has(key) ? ' (required)' : ''}`}
                        hint={[schema.type, schema.description].filter(Boolean).join(' · ')}
                      >
                        {schema.type === 'object' ? (
                          <Textarea
                            id={id}
                            className="min-h-[72px] font-mono text-xs"
                            placeholder="{}"
                            spellCheck={false}
                            value={testArgs[key] || ''}
                            onChange={e => setTestArgs(prev => ({ ...prev, [key]: e.target.value }))}
                          />
                        ) : (
                          <Input
                            id={id}
                            className="font-mono text-sm"
                            type={numeric ? 'number' : 'text'}
                            placeholder={numeric ? '0' : ''}
                            value={testArgs[key] || ''}
                            onChange={e => setTestArgs(prev => ({ ...prev, [key]: e.target.value }))}
                          />
                        )}
                      </Field>
                    );
                  })}
                </div>
              )}
            </section>

            {executing && !execResult && (
              <section aria-busy="true">
                <SubHeading>Result</SubHeading>
                <Skeleton className="h-28 w-full" />
              </section>
            )}

            {execResult && (
              <section className="animate-fade-up">
                <SubHeading action={<span className="num text-xs text-muted-foreground">{execResult.elapsed_ms} ms</span>}>
                  <span className="flex items-center gap-3">Result <StatusPill status={execResult.success ? 'success' : 'failed'}>{execResult.success ? 'Succeeded' : 'Failed'}</StatusPill></span>
                </SubHeading>
                <CodeBlock maxHeight={300} wrap>{JSON.stringify(execResult.result, null, 2) ?? 'null'}</CodeBlock>
              </section>
            )}

            <section>
              <button
                type="button"
                onClick={() => setShowSchema(v => !v)}
                aria-expanded={showSchema}
                className="inline-flex items-center gap-1.5 rounded text-sm font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Icon name="chevron-right" className={cn('h-3 w-3 transition-transform duration-200', showSchema && 'rotate-90')} />
                Technical details
              </button>
              {showSchema && (
                <div className="mt-3 animate-fade-in">
                  <p className="mb-1.5 text-xs text-muted-foreground">Parameter schema</p>
                  <CodeBlock maxHeight={280}>{JSON.stringify(testTool.parameters || {}, null, 2)}</CodeBlock>
                </div>
              )}
            </section>
          </div>
        )}
      </DetailSheet>
    </div>
  );
}
