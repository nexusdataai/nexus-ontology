import { useState, useEffect, useCallback } from 'react';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { ModalOverlay, ModalPanel } from '@/components/ds/Modal';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { Chips, InlineError, MetricStrip, SearchInput, StatusPill, TableShell, type Tone } from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
import {
  mappingRuleService,
  type AuditResponse,
  type AuditEntityDetail,
} from '../../services/mappingRuleService';

type FilterMode = 'all' | 'mapped' | 'unmapped' | 'has_data' | 'no_data' | 'has_issues';
type SortKey = 'entity' | 'system' | 'mappingStatus' | 'sourceTable' | 'fields' | 'rowCount' | 'dataStatus' | 'issues';

const DATA_STATUS: Record<string, { tone: Tone; label: string }> = {
  has_data: { tone: 'success', label: 'Has data' },
  no_data: { tone: 'warning', label: 'No data' },
  no_source: { tone: 'danger', label: 'No source' },
};

const COLUMNS: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: 'entity', label: 'Entity' },
  { key: 'system', label: 'System' },
  { key: 'mappingStatus', label: 'Mapping' },
  { key: 'sourceTable', label: 'Source table' },
  { key: 'fields', label: 'Fields mapped', numeric: true },
  { key: 'rowCount', label: 'Rows', numeric: true },
  { key: 'dataStatus', label: 'Data' },
  { key: 'issues', label: 'Issues' },
];

const sourceTableOf = (e: AuditEntityDetail) => (e.sourceTable ? `${e.sourceSchema}.${e.sourceTable}` : '');
const pct = (n: number, total: number) => (total > 0 ? Math.round((n / total) * 100) : 0);

interface Props {
  open: boolean;
  onClose: () => void;
  onSelectRule?: (ruleId: string) => void;
}

export function MappingAuditPanel({ open, onClose, onSelectRule }: Props) {
  const [data, setData] = useState<AuditResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterMode>('all');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('issues');
  const [sortAsc, setSortAsc] = useState(false);

  const loadAudit = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await mappingRuleService.audit();
      setData(result);
    } catch (e: any) {
      setError(e.message || 'Failed to load audit');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) loadAudit();
  }, [open, loadAudit]);

  if (!open) return null;

  const filtered = (data?.entities || []).filter(e => {
    if (search && !e.entity.toLowerCase().includes(search.toLowerCase())) return false;
    if (filter === 'mapped') return e.mappingStatus === 'mapped';
    if (filter === 'unmapped') return e.mappingStatus === 'unmapped';
    if (filter === 'has_data') return e.dataStatus === 'has_data';
    if (filter === 'no_data') return e.dataStatus !== 'has_data';
    if (filter === 'has_issues') return e.issues.length > 0;
    return true;
  });

  // Every column sorts by its own value; `cmp` is always ascending.
  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    if (sortKey === 'entity') cmp = a.entity.localeCompare(b.entity);
    else if (sortKey === 'system') cmp = a.system.localeCompare(b.system);
    else if (sortKey === 'mappingStatus') cmp = a.mappingStatus.localeCompare(b.mappingStatus);
    else if (sortKey === 'sourceTable') cmp = sourceTableOf(a).localeCompare(sourceTableOf(b));
    else if (sortKey === 'fields') cmp = a.mappedFields - b.mappedFields || a.unmappedFields - b.unmappedFields;
    else if (sortKey === 'rowCount') cmp = a.rowCount - b.rowCount;
    else if (sortKey === 'dataStatus') cmp = a.dataStatus.localeCompare(b.dataStatus);
    else if (sortKey === 'issues') cmp = a.issues.length - b.issues.length;
    if (cmp === 0) cmp = a.entity.localeCompare(b.entity);
    return sortAsc ? cmp : -cmp;
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(p => !p);
    else { setSortKey(key); setSortAsc(false); }
  };

  const issueCount = data?.entities.filter(e => e.issues.length > 0).length || 0;

  const filters: { value: FilterMode; label: string; count?: number }[] = [
    { value: 'all', label: 'All', count: data?.totalEntities },
    { value: 'mapped', label: 'Mapped', count: data?.mapped || 0 },
    { value: 'unmapped', label: 'Unmapped', count: data?.unmapped || 0 },
    { value: 'has_data', label: 'Has data', count: data?.withData || 0 },
    { value: 'no_data', label: 'No data', count: data?.withoutData || 0 },
    { value: 'has_issues', label: 'With issues', count: issueCount },
  ];

  const verdictTone: Tone = !data ? 'neutral' : data.unmapped === 0 && issueCount === 0 ? 'success' : data.unmapped > 0 ? 'danger' : 'warning';

  return (
    <ModalOverlay onClose={onClose}>
      <ModalPanel label="Mapping audit" className="h-[85dvh] max-w-6xl">
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3.5">
          <div className="min-w-0">
            <h2 className="text-xl font-medium tracking-tight text-foreground">Mapping audit</h2>
            <p className="text-sm text-muted-foreground">Every schema entity checked against its mapping rule and the data behind it.</p>
          </div>
          <div className="flex items-center gap-1.5">
            <Button variant="outline" size="sm" onClick={loadAudit} disabled={loading}>
              <Icon name="refresh" className={loading ? 'animate-spin' : undefined} /> Run again
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close">
              <Icon name="close" />
            </Button>
          </div>
        </header>

        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-5">
          {loading && !data ? (
            <div className="space-y-4" aria-busy="true">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-24 w-full rounded-xl" />
              {Array.from({ length: 7 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : error ? (
            <InlineError onRetry={loadAudit}>{error}</InlineError>
          ) : data ? (
            <div className="space-y-5">
              <p className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-sm text-muted-foreground">
                <StatusPill tone={verdictTone} variant="soft">
                  {verdictTone === 'success' ? 'Fully mapped' : verdictTone === 'danger' ? 'Gaps found' : 'Needs attention'}
                </StatusPill>
                <span>
                  <span className="num font-medium text-foreground">{data.mapped}</span> of <span className="num">{data.totalEntities}</span> entities are mapped
                  and <span className="num font-medium text-foreground">{data.withData}</span> return data.{' '}
                  {issueCount > 0
                    ? <><span className="num font-medium text-foreground">{issueCount}</span> {issueCount === 1 ? 'has' : 'have'} open issues.</>
                    : 'No open issues.'}
                </span>
              </p>

              <MetricStrip
                columns={5}
                items={[
                  { label: 'Entities', value: data.totalEntities },
                  { label: 'Mapped', value: data.mapped, hint: `${pct(data.mapped, data.totalEntities)}% of all` },
                  { label: 'Unmapped', value: data.unmapped, hint: data.unmapped > 0 ? 'Need a rule' : 'None', tone: data.unmapped > 0 ? 'danger' : 'neutral' },
                  { label: 'With data', value: data.withData, hint: `${pct(data.withData, data.totalEntities)}% of all` },
                  { label: 'Without data', value: data.withoutData, hint: data.withoutData > 0 ? 'Empty or no source' : 'None', tone: data.withoutData > 0 ? 'warning' : 'neutral' },
                ]}
              />

              {Object.keys(data.summaryBySystem).length > 0 && (
                <ul className="flex flex-wrap gap-x-7 gap-y-2 text-sm text-muted-foreground" aria-label="Coverage by system">
                  {Object.entries(data.summaryBySystem).map(([sys, s]) => (
                    <li key={sys} className="flex items-center gap-2">
                      <SystemLogo system={sys} size="sm" />
                      <span className="font-medium text-foreground">{systemName(sys)}</span>
                      <span>
                        <span className="num">{s.mapped}</span> mapped
                        {s.unmapped > 0 && <>, <span className="num">{s.unmapped}</span> unmapped</>}
                        {' '}· <span className="num">{s.rows.toLocaleString()}</span> rows
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              <div className="flex flex-wrap items-center justify-between gap-2.5">
                <Chips<FilterMode> options={filters} value={filter} onChange={(v) => setFilter(v)} label="Filter entities" />
                <SearchInput value={search} onChange={setSearch} placeholder="Search entities" className="sm:w-56" />
              </div>

              {sorted.length === 0 ? (
                <EmptyState icon="search" title="No entities match" description="Change the filter or the search to see entities again." />
              ) : (
                <TableShell>
                  <Table className="min-w-[980px]">
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        {COLUMNS.map(col => {
                          const on = sortKey === col.key;
                          return (
                            <TableHead key={col.key} className={cn(col.numeric && 'text-right')} aria-sort={on ? (sortAsc ? 'ascending' : 'descending') : 'none'}>
                              <button
                                type="button"
                                onClick={() => toggleSort(col.key)}
                                className={cn(
                                  'inline-flex items-center gap-1 rounded-sm transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                                  on && 'text-foreground',
                                )}
                              >
                                {col.label}
                                <Icon name={on && sortAsc ? 'chevron-up' : 'chevron-down'} className={cn('h-3 w-3', !on && 'opacity-0')} />
                              </button>
                            </TableHead>
                          );
                        })}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sorted.map(e => {
                        const ds = DATA_STATUS[e.dataStatus] || DATA_STATUS.no_source;
                        const clickable = !!e.ruleId && !!onSelectRule;
                        return (
                          <TableRow
                            key={e.entity}
                            className={cn(clickable && 'cursor-pointer')}
                            onClick={() => e.ruleId && onSelectRule?.(e.ruleId)}
                          >
                            <TableCell className="py-2.5">
                              {clickable ? (
                                <button
                                  type="button"
                                  onClick={(ev) => { ev.stopPropagation(); onSelectRule?.(e.ruleId as string); }}
                                  title="Open the mapping rule"
                                  className="rounded-sm text-left text-sm font-medium text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                >
                                  {e.entity}
                                </button>
                              ) : (
                                <span className="text-sm font-medium text-foreground">{e.entity}</span>
                              )}
                              {e.ruleName && <span className="block truncate text-xs text-muted-foreground">{e.ruleName}</span>}
                            </TableCell>
                            <TableCell className="py-2.5">
                              <span className="flex items-center gap-2 whitespace-nowrap text-sm text-muted-foreground">
                                <SystemLogo system={e.system} size="xs" />
                                {systemName(e.system)}
                              </span>
                            </TableCell>
                            <TableCell className="py-2.5"><StatusPill status={e.mappingStatus} /></TableCell>
                            <TableCell className="py-2.5 font-mono text-xs text-muted-foreground">{sourceTableOf(e) || '—'}</TableCell>
                            <TableCell className="num whitespace-nowrap py-2.5 text-right text-sm">
                              <span className="text-foreground">{e.mappedFields}</span>
                              <span className="text-muted-foreground"> of {e.schemaFields}</span>
                              {e.unmappedFields > 0 && <span className="block text-xs text-muted-foreground">{e.unmappedFields} not mapped</span>}
                            </TableCell>
                            <TableCell className={cn('num py-2.5 text-right text-sm', e.rowCount > 0 ? 'text-foreground' : 'text-subtle-foreground')}>
                              {e.rowCount.toLocaleString()}
                            </TableCell>
                            <TableCell className="py-2.5"><StatusPill tone={ds.tone}>{ds.label}</StatusPill></TableCell>
                            <TableCell className="max-w-[260px] py-2.5 text-xs text-muted-foreground">
                              {e.issues.length === 0
                                ? <span className="text-subtle-foreground">None</span>
                                : e.issues.map((issue, i) => <div key={i} className="truncate" title={issue}>{issue}</div>)}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TableShell>
              )}
            </div>
          ) : null}
        </div>

        {data && !error && (
          <footer className="flex shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-1 border-t border-border px-5 py-2.5 text-xs text-muted-foreground">
            <span>Showing <span className="num">{sorted.length}</span> of <span className="num">{data.totalEntities}</span> entities</span>
            <span>
              Coverage: <span className="num">{pct(data.mapped, data.totalEntities)}</span>% mapped, <span className="num">{pct(data.withData, data.totalEntities)}</span>% with data
            </span>
          </footer>
        )}
      </ModalPanel>
    </ModalOverlay>
  );
}

export default MappingAuditPanel;
