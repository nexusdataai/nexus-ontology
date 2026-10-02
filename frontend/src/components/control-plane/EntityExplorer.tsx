import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable';
import {
  Database, Search, Loader2, ChevronRight, Eye,
  Shield, AlertTriangle, Link2, Table2,
  X, Layers, ChevronDown, ChevronUp, RotateCcw,
} from 'lucide-react';
import type { ImperativePanelHandle } from 'react-resizable-panels';
import { apiClient } from '@/services/apiClient';
import { fdwService } from '@/services/fdwService';
import { virtualQueryService } from '@/services/virtualQueryService';
import { mappingRuleService, type MappingRule } from '@/services/mappingRuleService';
import type { QueryRequest } from '@/types/fdwTypes';

const FDW_SCHEMA = 'sfdc_itxp2dev';

interface SchemaEntity {
  name: string;
  system: string;
  domain: string;
  semantic: string;
  riskLevel: string;
  isVirtual: boolean;
  fdwMappingStatus: string;
  scorProcess: string;
  fields: { name: string; dataType: string; semantic: string; riskLevel: string; constraints: string[] }[];
  relationships: { type: string; targetEntity: string; targetCategory: string; description: string }[];
}

// Grouping axis for the entity list. Canonical entities are source-agnostic
// (system field is typically empty), so business taxonomy is the useful
// partition: by `domain` (15+ today) or by `scorProcess` (Plan/Source/Make/…).
type GroupAxis = 'domain' | 'scor';

const GROUP_AXIS_LABEL: Record<GroupAxis, string> = {
  domain: 'Domain',
  scor:   'SCOR Process',
};

// Stable palette cycled by group index so we don't have to maintain a per-
// domain colour table (the catalog grows over time).
const GROUP_PALETTE_HEX = [
  '#3b82f6', '#22c55e', '#f59e0b', '#f43f5e', '#a855f7',
  '#06b6d4', '#f97316', '#14b8a6', '#ec4899', '#84cc16',
  '#6366f1', '#eab308', '#10b981', '#ef4444', '#8b5cf6',
];

const groupKeyOf = (e: SchemaEntity, axis: GroupAxis): string => {
  const raw = axis === 'domain' ? e.domain : e.scorProcess;
  const v = (raw || '').trim();
  return v || 'Uncategorized';
};

const FDW_STATUS_STYLES: Record<string, string> = {
  mapped: 'bg-green-500/20 text-green-300',
  virtual: 'bg-yellow-500/20 text-yellow-300',
  unmapped: 'bg-gray-500/20 text-gray-400',
};

const RISK_STYLES: Record<string, string> = {
  high: 'text-red-400',
  medium: 'text-amber-400',
  low: 'text-green-400',
};

const RISK_HEX: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#22c55e',
};

const RELATIONSHIP_STYLES: Record<string, string> = {
  triggers: 'bg-purple-500/20 text-purple-300',
  syncs_to: 'bg-blue-500/20 text-blue-300',
  depends_on: 'bg-green-500/20 text-green-300',
  constrained_by: 'bg-amber-500/20 text-amber-300',
};

type RightTab = 'relationships' | 'vdl';

export default function EntityExplorer() {
  const [entities, setEntities] = useState<SchemaEntity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<SchemaEntity | null>(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [previewData, setPreviewData] = useState<{ rows: any[]; metadata: any } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [rightTab, setRightTab] = useState<RightTab>('relationships');
  const [entityMappingRules, setEntityMappingRules] = useState<MappingRule[]>([]);
  const [vdlLoading, setVdlLoading] = useState(false);

  const previewGen = useRef(0);
  const bottomPanelRef = useRef<ImperativePanelHandle>(null);
  const [bottomPanelExpanded, setBottomPanelExpanded] = useState(true);

  const [groupAxis, setGroupAxis] = useState<GroupAxis>('domain');
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set());

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await apiClient.get('/api/v1/control-plane/entities');
        const list = (data as SchemaEntity[]) || [];
        setEntities(list);
        // Default: all groups on the current axis are selected. Re-seed when
        // the axis changes below.
        setSelectedGroups(new Set(list.map(e => groupKeyOf(e, 'domain'))));
      } catch {
        setEntities([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // When the user switches grouping axis, reset the filter to "all groups
  // selected" so they don't end up with an unexpected empty list.
  useEffect(() => {
    if (entities.length === 0) return;
    setSelectedGroups(new Set(entities.map(e => groupKeyOf(e, groupAxis))));
  }, [groupAxis, entities]);

  const loadPreview = useCallback(async (entity: SchemaEntity) => {
    const gen = ++previewGen.current;
    setPreviewLoading(true);
    setPreviewData(null);
    try {
      const data = await virtualQueryService.previewEntity(entity.name, 10);
      if (previewGen.current !== gen) return;
      if (data.rows && data.rows.length > 0) {
        setPreviewData({ rows: data.rows, metadata: data.metadata });
        return;
      }
    } catch {
      // VDL preview failed, fall through to FDW if not virtual
    }

    if (entity.isVirtual) {
      if (previewGen.current === gen) setPreviewData(null);
      if (previewGen.current === gen) setPreviewLoading(false);
      return;
    }

    try {
      const fdwColumns = await fdwService.getColumns(FDW_SCHEMA, entity.name);
      if (previewGen.current !== gen) return;
      const fdwColNames = new Set(fdwColumns.map(c => c.columnName));
      const schemaFieldNames = entity.fields.map(f => f.name);
      const validCols = schemaFieldNames.filter(f => fdwColNames.has(f));
      const queryCols =
        validCols.length > 0
          ? validCols.slice(0, 8)
          : fdwColumns.slice(0, 8).map(c => c.columnName);
      if (queryCols.length === 0) {
        if (previewGen.current !== gen) return;
        setPreviewData(null);
        return;
      }
      const req: QueryRequest = {
        table: entity.name,
        schemaName: FDW_SCHEMA,
        columns: queryCols,
        limit: 10,
      };
      const result = await fdwService.executeQuery(req);
      if (previewGen.current !== gen) return;
      setPreviewData({ rows: result.rows, metadata: result.metadata });
    } catch {
      if (previewGen.current !== gen) return;
      setPreviewData(null);
    } finally {
      if (previewGen.current === gen) setPreviewLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedEntity) {
      previewGen.current += 1;
      setPreviewData(null);
      setPreviewLoading(false);
      setEntityMappingRules([]);
      setRightTab('relationships');
      return;
    }
    loadPreview(selectedEntity);
  }, [selectedEntity, loadPreview]);

  useEffect(() => {
    if (!selectedEntity || rightTab !== 'vdl') return;
    setVdlLoading(true);
    mappingRuleService
      .list(selectedEntity.name)
      .then(setEntityMappingRules)
      .catch(() => setEntityMappingRules([]))
      .finally(() => setVdlLoading(false));
  }, [selectedEntity?.name, rightTab]);

  const filteredEntities = useMemo(() => {
    return entities.filter(e => {
      if (!selectedGroups.has(groupKeyOf(e, groupAxis))) return false;
      if (!searchFilter) return true;
      return e.name.toLowerCase().includes(searchFilter.toLowerCase());
    });
  }, [entities, searchFilter, selectedGroups, groupAxis]);

  const grouped = useMemo(() => {
    return filteredEntities.reduce<Record<string, SchemaEntity[]>>((acc, e) => {
      const k = groupKeyOf(e, groupAxis);
      (acc[k] ??= []).push(e);
      return acc;
    }, {});
  }, [filteredEntities, groupAxis]);

  // Stable, sorted list of all groups on the current axis (used both for the
  // filter pills and for indexing into the colour palette so a given group
  // keeps the same colour across renders).
  const allGroups = useMemo(() => {
    const s = new Set(entities.map(e => groupKeyOf(e, groupAxis)));
    return [...s].sort();
  }, [entities, groupAxis]);

  const groupHex = (key: string): string => {
    const idx = allGroups.indexOf(key);
    return GROUP_PALETTE_HEX[(idx >= 0 ? idx : 0) % GROUP_PALETTE_HEX.length];
  };

  const toggleGroup = (key: string) => {
    setSelectedGroups(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const activeRule = entityMappingRules.find(r => r.status === 'active');

  const toggleBottomPanel = () => {
    const p = bottomPanelRef.current;
    if (!p) return;
    if (p.isCollapsed()) p.expand(16);
    else p.collapse();
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <ResizablePanelGroup direction="vertical" className="flex-1 min-h-0">
        <ResizablePanel defaultSize={74} minSize={40} className="min-h-0">
          <ResizablePanelGroup direction="horizontal" className="h-full min-h-0 px-2 pt-2 gap-0">
            {/* Left: entity list */}
            <ResizablePanel defaultSize={22} minSize={14} maxSize={38} className="min-h-0 min-w-0">
              <Card className="h-full flex flex-col min-h-0 border rounded-md overflow-hidden">
                <CardHeader className="pb-2 shrink-0 py-3 px-3">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-sm">Entities</CardTitle>
                    <Badge className="bg-muted text-muted-foreground text-[9px] shrink-0">
                      {filteredEntities.length}
                    </Badge>
                  </div>
                  <div className="relative mt-2">
                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <Input
                      value={searchFilter}
                      onChange={e => setSearchFilter(e.target.value)}
                      placeholder="Search entities..."
                      className="pl-7 h-7 text-xs"
                    />
                  </div>
                  {/* Group-by axis toggle */}
                  <div className="flex items-center gap-1 mt-2 text-[10px]">
                    <span className="text-muted-foreground">Group by:</span>
                    {(['domain', 'scor'] as GroupAxis[]).map(axis => (
                      <button
                        key={axis}
                        type="button"
                        onClick={() => setGroupAxis(axis)}
                        className={`px-1.5 py-0.5 rounded border transition-colors ${
                          groupAxis === axis
                            ? 'border-blue-500 bg-blue-500/10 text-blue-300'
                            : 'border-transparent text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        {GROUP_AXIS_LABEL[axis]}
                      </button>
                    ))}
                  </div>
                  {allGroups.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {allGroups.map(key => (
                        <button
                          key={key}
                          type="button"
                          onClick={() => toggleGroup(key)}
                          className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] border transition-colors ${
                            selectedGroups.has(key)
                              ? 'border-border text-foreground'
                              : 'border-transparent text-muted-foreground/40'
                          }`}
                        >
                          <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ backgroundColor: groupHex(key) }} />
                          {key}
                        </button>
                      ))}
                    </div>
                  )}
                </CardHeader>
                <CardContent className="flex-1 min-h-0 p-0 flex flex-col">
                  <ScrollArea className="flex-1 min-h-0">
                    {loading ? (
                      <div className="p-4 flex justify-center">
                        <Loader2 className="h-4 w-4 animate-spin" />
                      </div>
                    ) : (
                      <div className="divide-y pr-2">
                        {Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([groupKey, items]) => (
                          <div key={groupKey}>
                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-muted/50">
                              <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: groupHex(groupKey) }} />
                              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider truncate">
                                {groupKey}
                              </span>
                              <span className="text-[10px] text-muted-foreground ml-auto">{items.length}</span>
                            </div>
                            {items.map(entity => (
                              <button
                                key={entity.name}
                                type="button"
                                onClick={() => {
                                  setSelectedEntity(entity);
                                  setRightTab('relationships');
                                }}
                                className={`w-full text-left p-2.5 hover:bg-muted/50 transition-colors text-xs ${
                                  selectedEntity?.name === entity.name
                                    ? 'bg-blue-600/10 border-l-2 border-blue-500'
                                    : ''
                                }`}
                              >
                                <div className="flex items-center justify-between gap-1.5">
                                  <span className="truncate font-medium">{entity.name}</span>
                                  <Badge
                                    className={`text-[9px] shrink-0 ${
                                      FDW_STATUS_STYLES[entity.fdwMappingStatus] || FDW_STATUS_STYLES.unmapped
                                    }`}
                                  >
                                    {entity.fdwMappingStatus}
                                  </Badge>
                                </div>
                                <div className="flex items-center gap-2 text-[10px] text-muted-foreground mt-0.5 flex-wrap">
                                  <span className="flex items-center gap-0.5">
                                    <Table2 className="h-2.5 w-2.5" />
                                    {entity.fields.length} fields
                                  </span>
                                  <span className={RISK_STYLES[entity.riskLevel] || 'text-muted-foreground'}>
                                    {entity.riskLevel}
                                  </span>
                                </div>
                              </button>
                            ))}
                          </div>
                        ))}
                        {filteredEntities.length === 0 && (
                          <div className="p-4 text-center text-muted-foreground text-xs">
                            {entities.length === 0 ? 'No entities loaded' : 'No matches'}
                          </div>
                        )}
                      </div>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </ResizablePanel>

            <ResizableHandle withHandle className="mx-1" />

            {/* Center: schema */}
            <ResizablePanel defaultSize={50} minSize={28} className="min-h-0 min-w-0">
              <Card className="h-full flex flex-col min-h-0 border rounded-md overflow-hidden">
                {selectedEntity ? (
                  <>
                    <CardHeader className="py-3 px-3 shrink-0 border-b bg-muted/20">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h2 className="text-sm font-semibold">{selectedEntity.name}</h2>
                        {selectedEntity.domain && (
                          <Badge
                            className="text-[9px]"
                            style={{
                              backgroundColor: `${groupHex(selectedEntity.domain)}33`,
                              color: groupHex(selectedEntity.domain),
                            }}
                          >
                            {selectedEntity.domain}
                          </Badge>
                        )}
                        {selectedEntity.scorProcess && (
                          <Badge className="text-[9px] bg-blue-500/20 text-blue-300">
                            SCOR: {selectedEntity.scorProcess}
                          </Badge>
                        )}
                        <Badge
                          className={`text-[9px] ${RISK_STYLES[selectedEntity.riskLevel] || ''} bg-transparent border`}
                        >
                          <Shield className="h-2.5 w-2.5 mr-0.5" />
                          {selectedEntity.riskLevel}
                        </Badge>
                        <Badge
                          className={`text-[9px] ${
                            selectedEntity.isVirtual
                              ? 'bg-yellow-500/20 text-yellow-300'
                              : 'bg-green-500/20 text-green-300'
                          }`}
                        >
                          {selectedEntity.isVirtual ? 'virtual' : 'mapped'}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{selectedEntity.semantic}</p>
                    </CardHeader>
                    <CardContent className="flex-1 min-h-0 p-0 flex flex-col">
                      <div className="px-3 py-2 text-xs font-medium bg-muted/30 border-b shrink-0 flex items-center gap-2">
                        <Table2 className="h-3.5 w-3.5" />
                        Schema Fields ({selectedEntity.fields.length})
                      </div>
                      <ScrollArea className="flex-1 min-h-0">
                        <div className="overflow-x-auto p-2">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="border-b text-[10px] text-muted-foreground">
                                <th className="text-left px-2 py-1.5 font-medium">Field Name</th>
                                <th className="text-left px-2 py-1.5 font-medium">Data Type</th>
                                <th className="text-left px-2 py-1.5 font-medium">Semantic</th>
                                <th className="text-left px-2 py-1.5 font-medium">Risk</th>
                                <th className="text-left px-2 py-1.5 font-medium">Constraints</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y">
                              {selectedEntity.fields.map(field => (
                                <tr key={field.name} className="hover:bg-muted/30 transition-colors">
                                  <td className="px-2 py-1.5 font-mono">{field.name}</td>
                                  <td className="px-2 py-1.5">
                                    <Badge className="bg-muted text-muted-foreground text-[9px]">
                                      {field.dataType}
                                    </Badge>
                                  </td>
                                  <td className="px-2 py-1.5 text-muted-foreground">{field.semantic}</td>
                                  <td className="px-2 py-1.5">
                                    <span className={RISK_STYLES[field.riskLevel] || 'text-muted-foreground'}>
                                      {field.riskLevel}
                                    </span>
                                  </td>
                                  <td className="px-2 py-1.5">
                                    {field.constraints.length > 0 ? (
                                      <span className="text-[10px] text-muted-foreground">
                                        {field.constraints.join(', ')}
                                      </span>
                                    ) : (
                                      <span className="text-[10px] text-muted-foreground/50">—</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </ScrollArea>
                    </CardContent>
                  </>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground text-sm border-dashed p-6">
                    <div className="text-center">
                      <Database className="h-8 w-8 mx-auto mb-2 opacity-40" />
                      <p>Select an entity to view schema</p>
                    </div>
                  </div>
                )}
              </Card>
            </ResizablePanel>

            <ResizableHandle withHandle className="mx-1" />

            {/* Right: Relationships | Data layer */}
            <ResizablePanel defaultSize={28} minSize={18} maxSize={42} className="min-h-0 min-w-0">
              {selectedEntity ? (
                <Card className="h-full flex flex-col min-h-0 border rounded-md overflow-hidden">
                  <div className="flex items-center gap-2 px-2 py-2 border-b shrink-0 bg-card">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{
                        backgroundColor: selectedEntity.domain ? groupHex(selectedEntity.domain) : '#6b7280',
                      }}
                    />
                    <span className="text-xs font-medium truncate flex-1">{selectedEntity.name}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 shrink-0"
                      onClick={() => setSelectedEntity(null)}
                      aria-label="Clear selection"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                  <div className="flex border-b text-[10px] shrink-0">
                    <button
                      type="button"
                      onClick={() => setRightTab('relationships')}
                      className={`flex-1 py-1.5 text-center transition-colors ${
                        rightTab === 'relationships'
                          ? 'border-b-2 border-blue-500 text-blue-400'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <Link2 className="h-3 w-3 inline mr-1" />
                      Relationships
                    </button>
                    <button
                      type="button"
                      onClick={() => setRightTab('vdl')}
                      className={`flex-1 py-1.5 text-center transition-colors ${
                        rightTab === 'vdl'
                          ? 'border-b-2 border-blue-500 text-blue-400'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <Layers className="h-3 w-3 inline mr-1" />
                      Data layer
                    </button>
                  </div>
                  <CardContent className="flex-1 min-h-0 p-0 flex flex-col">
                    <ScrollArea className="flex-1 min-h-0">
                      <div className="px-2 py-2 space-y-2 pb-4">
                        <div className="flex flex-wrap gap-1">
                          {selectedEntity.domain && (
                            <Badge
                              className="text-[9px]"
                              style={{
                                backgroundColor: `${groupHex(selectedEntity.domain)}33`,
                                color: groupHex(selectedEntity.domain),
                              }}
                            >
                              {selectedEntity.domain}
                            </Badge>
                          )}
                          <Badge
                            className={`text-[9px] ${
                              selectedEntity.isVirtual
                                ? 'bg-yellow-500/20 text-yellow-300'
                                : 'bg-green-500/20 text-green-300'
                            }`}
                          >
                            {selectedEntity.isVirtual ? 'virtual' : 'mapped'}
                          </Badge>
                          <Badge
                            className="text-[9px]"
                            style={{ color: RISK_HEX[selectedEntity.riskLevel] || '#9ca3af' }}
                          >
                            <Shield className="h-2.5 w-2.5 mr-0.5" />
                            {selectedEntity.riskLevel}
                          </Badge>
                        </div>

                        {rightTab === 'relationships' && (
                          <>
                            <div className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground">
                              <Table2 className="h-3 w-3" /> {selectedEntity.fields.length} fields
                            </div>
                            {selectedEntity.relationships.length > 0 ? (
                              <div className="space-y-1">
                                <div className="text-[10px] font-medium text-muted-foreground">
                                  <Link2 className="h-3 w-3 inline mr-1" />
                                  {selectedEntity.relationships.length} relationships
                                </div>
                                {selectedEntity.relationships.map((rel, i) => (
                                  <div
                                    key={i}
                                    className="flex flex-col gap-0.5 text-[10px] p-1.5 rounded bg-muted/30 border border-border/50"
                                  >
                                    <div className="flex items-center gap-1 flex-wrap">
                                      <Badge
                                        className={`text-[8px] shrink-0 ${
                                          RELATIONSHIP_STYLES[rel.type] || 'bg-gray-500/20 text-gray-400'
                                        }`}
                                      >
                                        {rel.type}
                                      </Badge>
                                      <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
                                      <span className="font-medium truncate">{rel.targetEntity}</span>
                                    </div>
                                    <Badge className="bg-muted text-muted-foreground text-[8px] w-fit">
                                      {rel.targetCategory}
                                    </Badge>
                                    {rel.description && (
                                      <p className="text-muted-foreground text-[9px] leading-snug">{rel.description}</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-[10px] text-muted-foreground">No relationships defined.</p>
                            )}
                          </>
                        )}

                        {rightTab === 'vdl' && (
                          <>
                            {vdlLoading ? (
                              <div className="flex justify-center py-4">
                                <Loader2 className="h-4 w-4 animate-spin" />
                              </div>
                            ) : (
                              <>
                                <div>
                                  <div className="text-[10px] font-medium text-muted-foreground mb-1">
                                    <Database className="h-3 w-3 inline mr-1" />
                                    Mapping rule
                                  </div>
                                  {activeRule ? (
                                    <div className="p-2 rounded bg-muted/30 space-y-1 text-[10px]">
                                      <div className="flex items-center gap-1">
                                        <Badge className="text-[8px] bg-green-500/20 text-green-300">active</Badge>
                                        <span className="truncate font-medium">{activeRule.name}</span>
                                      </div>
                                      <div className="text-muted-foreground font-mono text-[9px]">
                                        {activeRule.sourceSchema}.{activeRule.sourceTable}
                                      </div>
                                      <div className="text-muted-foreground text-[9px]">
                                        {activeRule.fieldMaps.length} field mappings · {activeRule.sourceType}
                                      </div>
                                    </div>
                                  ) : (
                                    <div className="p-2 rounded bg-muted/20 text-[10px] text-muted-foreground">
                                      No active mapping rule for this entity.
                                    </div>
                                  )}
                                </div>

                                {selectedEntity.scorProcess && (
                                  <div>
                                    <div className="text-[10px] font-medium text-muted-foreground mb-1">
                                      SCOR process
                                    </div>
                                    <Badge className="text-[9px] bg-blue-500/20 text-blue-300">
                                      {selectedEntity.scorProcess}
                                    </Badge>
                                  </div>
                                )}

                                <div>
                                  <div className="text-[10px] font-medium text-muted-foreground mb-1">
                                    FDW mapping
                                  </div>
                                  {selectedEntity.isVirtual ? (
                                    <div className="flex items-start gap-2 text-[10px] bg-yellow-500/10 rounded-md px-2 py-2">
                                      <AlertTriangle className="h-3.5 w-3.5 text-yellow-400 shrink-0 mt-0.5" />
                                      <span className="text-yellow-200/90">
                                        Virtual entity — no direct FDW table. Preview uses the virtual query path.
                                      </span>
                                    </div>
                                  ) : (
                                    <div className="flex flex-col gap-1 text-[10px]">
                                      <span className="text-muted-foreground">FDW table</span>
                                      <span className="font-mono break-all">
                                        {FDW_SCHEMA}.{selectedEntity.name}
                                      </span>
                                      <Badge
                                        className={`text-[9px] w-fit ${
                                          FDW_STATUS_STYLES[selectedEntity.fdwMappingStatus] ||
                                          FDW_STATUS_STYLES.unmapped
                                        }`}
                                      >
                                        {selectedEntity.fdwMappingStatus}
                                      </Badge>
                                    </div>
                                  )}
                                </div>

                                <div className="flex gap-1 pt-1">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    className="flex-1 text-[10px] h-7"
                                    onClick={() => selectedEntity && loadPreview(selectedEntity)}
                                    disabled={previewLoading}
                                  >
                                    {previewLoading ? (
                                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                    ) : (
                                      <RotateCcw className="h-3 w-3 mr-1" />
                                    )}
                                    Refresh preview
                                  </Button>
                                </div>
                              </>
                            )}
                          </>
                        )}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              ) : (
                <Card className="h-full flex items-center justify-center min-h-0 border rounded-md border-dashed bg-muted/10">
                  <p className="text-[10px] text-muted-foreground px-2 text-center">Select an entity for relationships and data layer</p>
                </Card>
              )}
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Bottom: data preview */}
        <ResizablePanel
          ref={bottomPanelRef}
          defaultSize={26}
          minSize={10}
          maxSize={55}
          collapsible
          collapsedSize={5}
          className="min-h-0"
          onCollapse={() => setBottomPanelExpanded(false)}
          onExpand={() => setBottomPanelExpanded(true)}
        >
          <div className="flex flex-col h-full min-h-0 border-t bg-card rounded-b-md overflow-hidden">
            <button
              type="button"
              className="flex items-center gap-2 px-3 py-1.5 border-b bg-muted/30 shrink-0 w-full text-left hover:bg-muted/40 transition-colors"
              onClick={toggleBottomPanel}
            >
              <Eye className="h-3 w-3 text-muted-foreground shrink-0" />
              <span className="text-[10px] font-medium truncate">
                {selectedEntity ? `Data preview: ${selectedEntity.name}` : 'Data preview'}
              </span>
              {previewLoading && <Loader2 className="h-3 w-3 animate-spin text-blue-400 shrink-0" />}
              {!previewLoading && previewData?.metadata && selectedEntity && (
                <span className="text-[10px] text-muted-foreground truncate hidden sm:inline">
                  {previewData.metadata.rowCount != null && ` · ${previewData.metadata.rowCount} rows`}
                  {previewData.metadata.durationMs != null && ` · ${previewData.metadata.durationMs}ms`}
                </span>
              )}
              <span className="flex-1" />
              <Button
                variant="ghost"
                size="sm"
                className="h-5 w-5 p-0 shrink-0"
                onClick={e => {
                  e.stopPropagation();
                  if (selectedEntity) loadPreview(selectedEntity);
                }}
                disabled={!selectedEntity || previewLoading}
                aria-label="Refresh data preview"
              >
                <RotateCcw className="h-3 w-3" />
              </Button>
              {bottomPanelExpanded ? (
                <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
              ) : (
                <ChevronUp className="h-3 w-3 text-muted-foreground shrink-0" />
              )}
            </button>
            <div className="flex-1 min-h-0 overflow-auto">
              {!selectedEntity ? (
                <div className="flex items-center justify-center h-full text-[10px] text-muted-foreground px-2 py-4">
                  Select an entity to load rows below.
                </div>
              ) : previewLoading && !previewData ? (
                <div className="flex items-center justify-center h-full min-h-[80px]">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : previewData && previewData.rows.length > 0 ? (
                <table className="w-full text-[10px]">
                  <thead>
                    <tr className="bg-muted/30 sticky top-0 z-10">
                      {Object.keys(previewData.rows[0]).map(col => (
                        <th
                          key={col}
                          className="px-2 py-1 text-left text-muted-foreground font-medium whitespace-nowrap border-b"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {previewData.rows.map((row, i) => (
                      <tr key={i} className="hover:bg-muted/20">
                        {Object.values(row).map((val, j) => (
                          <td key={j} className="px-2 py-1 font-mono whitespace-nowrap max-w-[220px] truncate">
                            {val == null ? '' : String(val)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex flex-col items-center justify-center h-full min-h-[80px] text-[10px] text-muted-foreground px-4 py-3 gap-1">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                    <span>
                      {selectedEntity.isVirtual
                        ? 'No rows returned for this virtual entity.'
                        : 'FDW query returned no rows or columns could not be resolved.'}
                    </span>
                  </div>
                  <p className="text-[9px] text-center max-w-md">
                    Check the Data Plane connection, mapping rules, and that the FDW table exists for mapped entities.
                  </p>
                </div>
              )}
            </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
