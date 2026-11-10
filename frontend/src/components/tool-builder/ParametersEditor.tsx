import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icon } from '@/components/ds/Icon';
import { CodeBlock, SubHeading, TableShell } from '@/components/ds/kit';

interface PropertyRow {
  key: string;
  type: 'string' | 'integer' | 'number' | 'boolean' | 'object' | 'array';
  description: string;
  required: boolean;
  enumStr: string;
}

interface Props {
  schema: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}

const TYPE_OPTIONS: { value: PropertyRow['type']; label: string }[] = [
  { value: 'string', label: 'Text' },
  { value: 'integer', label: 'Whole number' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Yes or no' },
  { value: 'object', label: 'Object' },
  { value: 'array', label: 'List' },
];

function schemaToRows(schema: Record<string, unknown>): PropertyRow[] {
  const props = (schema.properties as Record<string, any>) || {};
  const required = new Set<string>(((schema.required as string[]) || []));
  return Object.entries(props).map(([key, p]) => ({
    key,
    type: (p?.type as PropertyRow['type']) || 'string',
    description: String(p?.description || ''),
    required: required.has(key),
    enumStr: Array.isArray(p?.enum) ? (p.enum as unknown[]).join(', ') : '',
  }));
}

function rowsToSchema(rows: PropertyRow[]): Record<string, unknown> {
  const properties: Record<string, unknown> = {};
  const required: string[] = [];
  for (const r of rows) {
    if (!r.key.trim()) continue;
    const node: Record<string, unknown> = { type: r.type };
    if (r.description) node.description = r.description;
    if (r.enumStr.trim()) {
      const items = r.enumStr.split(',').map((s) => s.trim()).filter(Boolean);
      if (items.length) {
        if (r.type === 'integer' || r.type === 'number') {
          node.enum = items.map((s) => Number(s));
        } else {
          node.enum = items;
        }
      }
    }
    properties[r.key] = node;
    if (r.required) required.push(r.key);
  }
  return { type: 'object', properties, required };
}

const th = 'h-10 whitespace-nowrap px-3 text-left text-xs font-medium text-muted-foreground';

/** The inputs a tool accepts: one row per parameter, with the schema it produces. */
export default function ParametersEditor({ schema, onChange }: Props) {
  const [rows, setRows] = useState<PropertyRow[]>(() => schemaToRows(schema || {}));

  const update = (next: PropertyRow[]) => {
    setRows(next);
    onChange(rowsToSchema(next));
  };

  const patch = (idx: number, change: Partial<PropertyRow>) => {
    const next = [...rows];
    next[idx] = { ...rows[idx], ...change };
    update(next);
  };

  const addRow = () => update([
    ...rows,
    { key: '', type: 'string', description: '', required: false, enumStr: '' },
  ]);

  const preview = useMemo(() => JSON.stringify(rowsToSchema(rows), null, 2), [rows]);

  return (
    <div className="grid gap-x-8 gap-y-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="text-md font-medium text-foreground">Parameters</h3>
            <p className="mt-0.5 text-sm text-muted-foreground">The inputs the tool accepts. Every run is checked against them before the code starts.</p>
          </div>
          <Button variant="outline" size="sm" onClick={addRow}>
            <Icon name="plus" /> Add parameter
          </Button>
        </div>

        <TableShell className="mt-4">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-surface-2/60">
              <tr className="border-b border-border">
                <th className={th}>Name</th>
                <th className={th}>Type</th>
                <th className={th}>Required</th>
                <th className={th}>Allowed values</th>
                <th className={th}>Description</th>
                <th className={th}><span className="sr-only">Remove</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, idx) => (
                <tr key={idx} className="border-b border-border last:border-b-0">
                  <td className="w-[180px] px-3 py-2">
                    <Input value={r.key} onChange={(e) => patch(idx, { key: e.target.value })} aria-label="Parameter name" placeholder="name" className="h-8 font-mono text-xs" />
                  </td>
                  <td className="w-[150px] px-3 py-2">
                    <Select value={r.type} onValueChange={(v) => patch(idx, { type: v as PropertyRow['type'] })}>
                      <SelectTrigger className="h-8" aria-label="Parameter type"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {TYPE_OPTIONS.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="px-3 py-2">
                    <Checkbox checked={r.required} onCheckedChange={(v) => patch(idx, { required: !!v })} aria-label="Required" />
                  </td>
                  <td className="w-[170px] px-3 py-2">
                    <Input value={r.enumStr} onChange={(e) => patch(idx, { enumStr: e.target.value })} aria-label="Allowed values, separated by commas" placeholder="Any" className="h-8 text-xs" />
                  </td>
                  <td className="px-3 py-2">
                    <Input value={r.description} onChange={(e) => patch(idx, { description: e.target.value })} aria-label="Description" className="h-8 text-xs" />
                  </td>
                  <td className="w-12 px-3 py-2 text-right">
                    <Button size="icon-sm" variant="ghost" aria-label={`Remove parameter ${r.key || idx + 1}`} onClick={() => update(rows.filter((_, i) => i !== idx))}>
                      <Icon name="trash" />
                    </Button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-sm text-muted-foreground">
                    No parameters. The tool runs with an empty payload.
                    <div className="mt-3"><Button variant="outline" size="sm" onClick={addRow}><Icon name="plus" /> Add parameter</Button></div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </TableShell>
        <p className="mt-2 text-xs text-subtle-foreground">Separate allowed values with commas. Leave empty to accept anything of that type.</p>
      </div>

      <div className="min-w-0">
        <SubHeading>Generated schema</SubHeading>
        <CodeBlock maxHeight={360}>{preview}</CodeBlock>
      </div>
    </div>
  );
}
