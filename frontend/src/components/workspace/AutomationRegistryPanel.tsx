/**
 * Automation registry (Workspace).
 *
 * The playbooks the Copilot plans from, read from `/api/v1/automation/registry`.
 * A collection: search and solution chips above a table; a row opens the
 * playbook in a sheet with its facts and its YAML definition, where it can be
 * edited, saved or deleted. "New playbook" opens the same sheet empty.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { confirmDialog } from '@/components/ds/confirm';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import {
  Chips, CodeBlock, DetailSheet, Field, InlineError, KeyValues, SearchInput, SubHeading, TableShell, Toolbar, ToolbarSpacer,
} from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
import { humanize, systemsIn } from '@/components/journeys/studio/format';
import {
  automationRegistryService,
  AutomationRow,
} from '@/services/automationRegistryService';

function matches(row: AutomationRow, q: string): boolean {
  if (!q) return true;
  const n = q.toLowerCase();
  return (
    (row.useCaseId || '').toLowerCase().includes(n)
    || (row.solution || '').toLowerCase().includes(n)
    || (row.sourceFile || '').toLowerCase().includes(n)
    || (row.yamlText || '').toLowerCase().includes(n)
  );
}

/* --------------------------------------------- what a definition says (view only) */

const yamlValue = (yaml: string, key: string): string => {
  const m = yaml.match(new RegExp(`^\\s*${key}\\s*:\\s*(.+)$`, 'm'));
  return m ? m[1].trim().replace(/^["']|["']$/g, '') : '';
};
const stepCount = (yaml: string): number => (yaml.match(/^\s*-?\s*tool\s*:/gm) || []).length;
const approvalCount = (yaml: string): number => (yaml.match(/requires_approval\s*:\s*true/g) || []).length;
const kb = (bytes?: number) => (bytes ? `${(bytes / 1024).toFixed(1)} KB` : '');

function describe(row: AutomationRow) {
  const yaml = row.yamlText || '';
  return {
    title: yamlValue(yaml, 'title') || yamlValue(yaml, 'display_name') || humanize(row.useCaseId),
    description: yamlValue(yaml, 'description'),
    steps: stepCount(yaml),
    approvals: approvalCount(yaml),
    systems: systemsIn(yaml),
  };
}

export function AutomationRegistryPanel() {
  const [rows, setRows] = useState<AutomationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<AutomationRow | null>(null);
  const [editorText, setEditorText] = useState('');
  const [savingId, setSavingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  // View-only: solution chip and whether the definition is being edited.
  const [solution, setSolution] = useState<string>('all');
  const [editing, setEditing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await automationRegistryService.list();
      setRows(r.items || []);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => rows.filter((r) => matches(r, search)), [rows, search]);

  const openRow = async (row: AutomationRow) => {
    setEditing(false);
    setSelected(row);
    if (row.yamlText) {
      setEditorText(row.yamlText);
    } else {
      try {
        const full = await automationRegistryService.get(row.useCaseId);
        setEditorText(full.yamlText || '');
      } catch {
        setEditorText('');
      }
    }
  };

  const closeDrawer = () => {
    setSelected(null);
    setEditorText('');
    setCreating(false);
    setEditing(false);
  };

  const openCreate = () => {
    setCreating(true);
    setEditing(true);
    setSelected({ useCaseId: '', solution: 'misc', sourceFile: '', yamlText: '' });
    setEditorText('');
  };

  const saveSelected = async () => {
    if (!selected) return;
    if (!selected.useCaseId || !selected.solution) {
      setError('useCaseId and solution are required');
      return;
    }
    setSavingId(selected.useCaseId);
    setError(null);
    try {
      await automationRegistryService.upsert({
        use_case_id: selected.useCaseId,
        solution: selected.solution,
        yaml_text: editorText,
        source_file: selected.sourceFile || `${selected.useCaseId}.yaml`,
      });
      await load();
      closeDrawer();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setSavingId(null);
    }
  };

  const deleteSelected = async () => {
    if (!selected || !selected.useCaseId) return;
    if (!(await confirmDialog({ title: `Delete playbook '${selected.useCaseId}'?`, description: 'This cannot be undone.', destructive: true }))) return;
    setSavingId(selected.useCaseId);
    try {
      await automationRegistryService.remove(selected.useCaseId);
      await load();
      closeDrawer();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setSavingId(null);
    }
  };

  /* ------------------------------------------------------------ presentation */

  const solutions = useMemo(() => {
    const counts = new Map<string, number>();
    for (const r of filtered) counts.set(r.solution || 'misc', (counts.get(r.solution || 'misc') || 0) + 1);
    return Array.from(counts.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered]);
  const shown = solution === 'all' ? filtered : filtered.filter(r => (r.solution || 'misc') === solution);
  const chipOptions = [
    { value: 'all', label: 'All', count: filtered.length },
    ...solutions.map(([s, c]) => ({ value: s, label: humanize(s), count: c })),
  ];

  const busy = !!selected && savingId === selected.useCaseId;
  const requiredMissing = error === 'useCaseId and solution are required';
  const sheetError = selected ? (requiredMissing ? 'Give the playbook an ID and a solution before saving.' : error) : null;
  const info = selected ? describe({ ...selected, yamlText: editorText }) : null;
  const firstLoad = loading && rows.length === 0;

  return (
    <div className="page">
      <div className="flex flex-col gap-1">
        <h2 className="text-md font-medium text-foreground">Playbooks</h2>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Reusable automation definitions. The Copilot matches a goal to a playbook and builds its plan from it.
        </p>
      </div>

      <Toolbar className="mt-5">
        <SearchInput value={search} onChange={setSearch} placeholder="Search playbooks" />
        <Chips label="Solution" options={chipOptions} value={chipOptions.some(o => o.value === solution) ? solution : 'all'} onChange={setSolution} />
        <ToolbarSpacer />
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          <Icon name="refresh" className={loading ? 'animate-spin' : undefined} /> Refresh
        </Button>
        <Button size="sm" onClick={openCreate}>
          <Icon name="plus" /> New playbook
        </Button>
      </Toolbar>

      <div className="mt-4">
        {error && !selected && <InlineError onRetry={load} className="mb-4">The registry could not be loaded. {error}</InlineError>}

        {firstLoad ? (
          <TableShell>
            <div className="divide-y divide-border">
              {[0, 1, 2, 3, 4, 5].map(i => (
                <div key={i} className="flex items-center gap-6 px-4 py-3.5">
                  <div className="min-w-0 flex-1 space-y-2"><Skeleton className="h-4 w-52 max-w-full" /><Skeleton className="h-3 w-36" /></div>
                  <Skeleton className="hidden h-4 w-24 md:block" />
                  <Skeleton className="hidden h-4 w-16 md:block" />
                </div>
              ))}
            </div>
          </TableShell>
        ) : shown.length === 0 ? (
          (!error || rows.length > 0) && (
            <EmptyState
              icon="list"
              title={rows.length === 0 ? 'No playbooks yet' : 'No playbooks match'}
              description={rows.length === 0 ? 'Add a playbook so the Copilot has something to plan from.' : `Nothing matches "${search}"${solution !== 'all' ? ` in ${humanize(solution)}` : ''}.`}
              action={rows.length === 0
                ? <Button size="sm" onClick={openCreate}><Icon name="plus" /> New playbook</Button>
                : <Button size="sm" variant="outline" onClick={() => { setSearch(''); setSolution('all'); }}>Clear filters</Button>}
            />
          )
        ) : (
          <TableShell>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Playbook</TableHead>
                  <TableHead>Solution</TableHead>
                  <TableHead>Systems</TableHead>
                  <TableHead className="text-right">Steps</TableHead>
                  <TableHead className="text-right">Size</TableHead>
                  <TableHead className="w-px" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {shown.map((row, i) => {
                  const d = describe(row);
                  return (
                    <TableRow
                      key={row.useCaseId}
                      onClick={() => openRow(row)}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openRow(row); } }}
                      tabIndex={0}
                      className="rise group cursor-pointer focus-visible:bg-accent/60 focus-visible:outline-none"
                      style={{ ['--i' as any]: Math.min(i, 12) }}
                    >
                      <TableCell className="max-w-[360px]">
                        <div className="truncate font-medium text-foreground">{d.title}</div>
                        <div className="mono-id truncate">{row.useCaseId}</div>
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-muted-foreground">{humanize(row.solution)}</TableCell>
                      <TableCell>
                        {d.systems.length === 0 ? <span className="text-subtle-foreground">None named</span> : (
                          <span className="flex items-center gap-2">
                            {d.systems.slice(0, 4).map(s => <SystemLogo key={s} system={s} size="sm" />)}
                            {d.systems.length === 1 && <span className="text-muted-foreground">{systemName(d.systems[0])}</span>}
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="num text-right">{row.yamlText ? d.steps : ''}</TableCell>
                      <TableCell className="num whitespace-nowrap text-right text-muted-foreground">{kb(row.sizeBytes)}</TableCell>
                      <TableCell className="text-right">
                        <Icon name="chevron-right" className="h-3.5 w-3.5 text-subtle-foreground opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100" />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableShell>
        )}

        {!firstLoad && rows.length > 0 && (
          <p className="num mt-3 text-xs text-muted-foreground">Showing {shown.length} of {rows.length} playbooks</p>
        )}
      </div>

      <DetailSheet
        open={!!selected}
        onOpenChange={(open) => { if (!open) closeDrawer(); }}
        wide
        title={creating ? 'New playbook' : info?.title || selected?.useCaseId || 'Playbook'}
        description={creating ? 'Give it an ID and a solution, then paste or write its definition.' : info?.description || 'Playbook definition and facts.'}
        footer={selected ? (
          <>
            {!creating && selected.useCaseId && (
              <Button variant="ghost" onClick={deleteSelected} disabled={busy} className="mr-auto text-destructive hover:bg-destructive/10 hover:text-destructive">
                <Icon name="trash" /> Delete
              </Button>
            )}
            <Button variant="outline" onClick={closeDrawer}>Close</Button>
            <Button onClick={saveSelected} disabled={busy}>
              {busy && <Icon name="spinner" className="animate-spin" />} Save
            </Button>
          </>
        ) : undefined}
      >
        {selected && (
          <div className="space-y-6">
            {sheetError && <InlineError>{sheetError}</InlineError>}

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Playbook ID" htmlFor="ar-id" hint={creating ? 'Lower case, with underscores. It cannot be changed later.' : undefined}>
                <Input
                  id="ar-id"
                  className="font-mono text-xs"
                  placeholder="o2c_health_check"
                  value={selected.useCaseId}
                  onChange={(e) => setSelected({ ...selected, useCaseId: e.target.value })}
                  disabled={!creating && !!selected.useCaseId}
                />
              </Field>
              <Field label="Solution" htmlFor="ar-solution">
                <Input
                  id="ar-solution"
                  placeholder="order-to-cash"
                  value={selected.solution}
                  onChange={(e) => setSelected({ ...selected, solution: e.target.value })}
                />
              </Field>
            </div>

            {!creating && info && (
              <div>
                <SubHeading>Facts</SubHeading>
                <KeyValues
                  columns={2}
                  items={[
                    { label: 'Steps', value: <span className="num">{info.steps}</span> },
                    { label: 'Approval gates', value: <span className="num">{info.approvals}</span> },
                    { label: 'Systems', value: info.systems.length ? (
                      <span className="inline-flex items-center gap-2">{info.systems.map(s => <SystemLogo key={s} system={s} size="xs" />)}<span>{info.systems.map(s => systemName(s)).join(', ')}</span></span>
                    ) : 'None named' },
                    { label: 'Size', value: kb(selected.sizeBytes) || 'Not recorded' },
                    { label: 'Source file', value: selected.sourceFile || 'Not recorded', mono: true },
                  ]}
                />
              </div>
            )}

            <div>
              <SubHeading
                action={!creating ? (
                  <button
                    type="button"
                    onClick={() => setEditing(v => !v)}
                    className="text-xs font-medium text-primary underline-offset-4 hover:underline dark:text-brand-hi"
                  >
                    {editing ? 'Preview' : 'Edit'}
                  </button>
                ) : undefined}
              >
                Definition <span className="font-normal text-muted-foreground">(YAML)</span>
              </SubHeading>
              {editing ? (
                <Textarea
                  aria-label="Playbook definition"
                  className={cn('scroll-thin min-h-[380px] font-mono text-xs leading-5')}
                  value={editorText}
                  onChange={(e) => setEditorText(e.target.value)}
                  placeholder={'use_case_id: ...\nsolution: ...\nstages:\n  - ...'}
                  spellCheck={false}
                />
              ) : editorText ? (
                <CodeBlock maxHeight={460}>{editorText}</CodeBlock>
              ) : (
                <p className="rounded-lg border border-dashed border-border-strong px-4 py-6 text-center text-sm text-muted-foreground">
                  This playbook has no definition yet. Select Edit to add one.
                </p>
              )}
            </div>
          </div>
        )}
      </DetailSheet>
    </div>
  );
}
