import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { ScrollArea } from '../ui/scroll-area';
import {
  Loader2, CheckCircle2, XCircle, AlertTriangle, Search, ArrowUpDown,
  Database, X,
} from 'lucide-react';
import {
  mappingRuleService,
  type AuditResponse,
  type AuditEntityDetail,
} from '../../services/mappingRuleService';

type FilterMode = 'all' | 'mapped' | 'unmapped' | 'has_data' | 'no_data' | 'has_issues';
type SortKey = 'entity' | 'system' | 'mappingStatus' | 'rowCount' | 'issues';

const SYSTEM_COLORS: Record<string, string> = {
  Salesforce: 'bg-blue-500', Oracle: 'bg-orange-500', SAP: 'bg-green-500',
  Google_Drive: 'bg-red-500', Social_Listening: 'bg-pink-500', File_Uploads: 'bg-purple-500',
};

const STATUS_STYLES: Record<string, { bg: string; label: string }> = {
  mapped: { bg: 'bg-green-500/20 text-green-400 border-green-500/30', label: 'Mapped' },
  unmapped: { bg: 'bg-red-500/20 text-red-400 border-red-500/30', label: 'Unmapped' },
  error: { bg: 'bg-amber-500/20 text-amber-400 border-amber-500/30', label: 'Error' },
};

const DATA_STYLES: Record<string, { bg: string; label: string }> = {
  has_data: { bg: 'bg-green-500/20 text-green-400', label: 'Has Data' },
  no_data: { bg: 'bg-amber-500/20 text-amber-400', label: 'No Data' },
  no_source: { bg: 'bg-red-500/20 text-red-400', label: 'No Source' },
};

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

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    if (sortKey === 'entity') cmp = a.entity.localeCompare(b.entity);
    else if (sortKey === 'system') cmp = a.system.localeCompare(b.system);
    else if (sortKey === 'mappingStatus') cmp = a.mappingStatus.localeCompare(b.mappingStatus);
    else if (sortKey === 'rowCount') cmp = a.rowCount - b.rowCount;
    else if (sortKey === 'issues') cmp = b.issues.length - a.issues.length;
    return sortAsc ? cmp : -cmp;
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(p => !p);
    else { setSortKey(key); setSortAsc(false); }
  };

  const rowBg = (e: AuditEntityDetail) => {
    if (e.mappingStatus === 'mapped' && e.dataStatus === 'has_data' && e.issues.length === 0) return 'hover:bg-green-500/5';
    if (e.mappingStatus === 'mapped' && (e.rowCount === 0 || e.unmappedFields > 0)) return 'bg-amber-500/5 hover:bg-amber-500/10';
    if (e.mappingStatus === 'unmapped') return 'bg-red-500/5 hover:bg-red-500/10';
    return 'hover:bg-muted/20';
  };

  const filters: { key: FilterMode; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'mapped', label: `Mapped (${data?.mapped || 0})` },
    { key: 'unmapped', label: `Unmapped (${data?.unmapped || 0})` },
    { key: 'has_data', label: `Has Data (${data?.withData || 0})` },
    { key: 'no_data', label: `No Data (${data?.withoutData || 0})` },
    { key: 'has_issues', label: `Issues (${data?.entities.filter(e => e.issues.length > 0).length || 0})` },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-card border rounded-xl shadow-2xl w-[90vw] max-w-[1200px] h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <h2 className="text-lg font-bold">Mapping Audit Report</h2>
            <p className="text-xs text-muted-foreground">Schema entities vs mapping rules vs simulator data</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadAudit} disabled={loading}>
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Database className="h-3.5 w-3.5" />}
              <span className="ml-1">Refresh</span>
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
          </div>
        </div>

        {loading && !data ? (
          <div className="flex-1 flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin" /></div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center text-red-400 text-sm">{error}</div>
        ) : data ? (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-5 gap-3 px-6 py-3 border-b">
              {[
                { label: 'Total Entities', value: data.totalEntities, color: 'text-foreground' },
                { label: 'Mapped', value: data.mapped, color: 'text-green-400' },
                { label: 'Unmapped', value: data.unmapped, color: 'text-red-400' },
                { label: 'With Data', value: data.withData, color: 'text-blue-400' },
                { label: 'No Data', value: data.withoutData, color: 'text-amber-400' },
              ].map(c => (
                <Card key={c.label} className="bg-muted/20">
                  <CardContent className="pt-3 pb-2 px-3">
                    <div className="text-[10px] text-muted-foreground">{c.label}</div>
                    <div className={`text-xl font-bold ${c.color}`}>{c.value}</div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* System breakdown */}
            <div className="flex items-center gap-3 px-6 py-2 border-b overflow-x-auto">
              {Object.entries(data.summaryBySystem).map(([sys, s]) => (
                <div key={sys} className="flex items-center gap-1.5 text-[10px] shrink-0">
                  <span className={`w-2 h-2 rounded-full ${SYSTEM_COLORS[sys] || 'bg-gray-500'}`} />
                  <span className="font-medium">{sys}</span>
                  <span className="text-green-400">{s.mapped}m</span>
                  <span className="text-red-400">{s.unmapped}u</span>
                  <span className="text-muted-foreground">{s.rows.toLocaleString()}r</span>
                </div>
              ))}
            </div>

            {/* Filter bar */}
            <div className="flex items-center gap-2 px-6 py-2 border-b">
              <div className="flex gap-1">
                {filters.map(f => (
                  <Button key={f.key} variant={filter === f.key ? 'default' : 'outline'} size="sm" className="text-[10px] h-6 px-2"
                    onClick={() => setFilter(f.key)}>{f.label}</Button>
                ))}
              </div>
              <div className="flex-1" />
              <div className="relative w-48">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
                <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search entity..." className="pl-7 h-6 text-[10px]" />
              </div>
            </div>

            {/* Table */}
            <ScrollArea className="flex-1">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-muted/30 sticky top-0">
                    {[
                      { key: 'entity' as SortKey, label: 'Entity' },
                      { key: 'system' as SortKey, label: 'System' },
                      { key: 'mappingStatus' as SortKey, label: 'Mapping' },
                      { key: 'entity' as SortKey, label: 'Source Table' },
                      { key: 'entity' as SortKey, label: 'Fields' },
                      { key: 'rowCount' as SortKey, label: 'Rows' },
                      { key: 'entity' as SortKey, label: 'Data' },
                      { key: 'issues' as SortKey, label: 'Issues' },
                    ].map((col, i) => (
                      <th key={i} className="px-3 py-2 text-left font-medium cursor-pointer hover:text-foreground"
                        onClick={() => toggleSort(col.key)}>
                        <span className="flex items-center gap-1">
                          {col.label}
                          {sortKey === col.key && <ArrowUpDown className="h-2.5 w-2.5" />}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {sorted.map(e => {
                    const ms = STATUS_STYLES[e.mappingStatus] || STATUS_STYLES.unmapped;
                    const ds = DATA_STYLES[e.dataStatus] || DATA_STYLES.no_source;
                    return (
                      <tr key={e.entity} className={`${rowBg(e)} cursor-pointer transition-colors`}
                        onClick={() => e.ruleId && onSelectRule?.(e.ruleId)}>
                        <td className="px-3 py-2 font-medium">{e.entity}</td>
                        <td className="px-3 py-2">
                          <span className="flex items-center gap-1">
                            <span className={`w-2 h-2 rounded-full ${SYSTEM_COLORS[e.system] || 'bg-gray-500'}`} />
                            {e.system}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <Badge variant="outline" className={`text-[9px] ${ms.bg}`}>{ms.label}</Badge>
                        </td>
                        <td className="px-3 py-2 font-mono text-[10px] text-muted-foreground">
                          {e.sourceTable ? `${e.sourceSchema}.${e.sourceTable}` : '--'}
                        </td>
                        <td className="px-3 py-2">
                          <span className="text-green-400">{e.mappedFields}</span>
                          <span className="text-muted-foreground">/{e.schemaFields}</span>
                          {e.unmappedFields > 0 && <span className="text-red-400 ml-1">({e.unmappedFields} gap)</span>}
                        </td>
                        <td className="px-3 py-2 font-mono">{e.rowCount > 0 ? e.rowCount.toLocaleString() : <span className="text-muted-foreground">0</span>}</td>
                        <td className="px-3 py-2">
                          <Badge variant="outline" className={`text-[9px] ${ds.bg}`}>{ds.label}</Badge>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex flex-wrap gap-1">
                            {e.issues.length === 0 ? (
                              <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                            ) : e.issues.map((issue, i) => (
                              <Badge key={i} variant="outline" className="text-[8px] bg-amber-500/10 text-amber-400 border-amber-500/20" title={issue}>
                                <AlertTriangle className="h-2 w-2 mr-0.5" />{issue.length > 25 ? issue.substring(0, 25) + '...' : issue}
                              </Badge>
                            ))}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {sorted.length === 0 && (
                <div className="text-center py-10 text-sm text-muted-foreground">No entities match the current filter</div>
              )}
            </ScrollArea>

            {/* Footer */}
            <div className="flex items-center justify-between px-6 py-2 border-t text-[10px] text-muted-foreground">
              <span>Showing {sorted.length} of {data.totalEntities} entities</span>
              <span>
                Coverage: {data.totalEntities > 0 ? Math.round((data.mapped / data.totalEntities) * 100) : 0}% mapped,{' '}
                {data.totalEntities > 0 ? Math.round((data.withData / data.totalEntities) * 100) : 0}% with data
              </span>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

export default MappingAuditPanel;
