import { useMemo, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

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

const TYPE_OPTIONS: PropertyRow['type'][] = [
  'string', 'integer', 'number', 'boolean', 'object', 'array',
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

export default function ParametersEditor({ schema, onChange }: Props) {
  const [rows, setRows] = useState<PropertyRow[]>(() => schemaToRows(schema || {}));

  const update = (next: PropertyRow[]) => {
    setRows(next);
    onChange(rowsToSchema(next));
  };

  const preview = useMemo(() => JSON.stringify(rowsToSchema(rows), null, 2), [rows]);

  return (
    <div className="space-y-3 text-sm">
      <div className="text-[11px] text-muted-foreground">
        Parameters JSON Schema. The tool's `params` argument is validated against this on every invocation.
      </div>

      <div className="border rounded-md overflow-hidden">
        <table className="w-full text-[11px]">
          <thead className="bg-muted/40">
            <tr className="text-left">
              <th className="px-2 py-1.5">name</th>
              <th className="px-2 py-1.5">type</th>
              <th className="px-2 py-1.5">required</th>
              <th className="px-2 py-1.5">enum (comma-sep)</th>
              <th className="px-2 py-1.5">description</th>
              <th className="px-2 py-1.5"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
              <tr key={idx} className="border-t border-border/40">
                <td className="px-2 py-1">
                  <Input
                    value={r.key}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = { ...r, key: e.target.value };
                      update(next);
                    }}
                    className="h-6 text-[11px] font-mono"
                  />
                </td>
                <td className="px-2 py-1">
                  <select
                    value={r.type}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = { ...r, type: e.target.value as PropertyRow['type'] };
                      update(next);
                    }}
                    className="h-6 text-[11px] bg-background border rounded px-1"
                  >
                    {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </td>
                <td className="px-2 py-1">
                  <input
                    type="checkbox"
                    checked={r.required}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = { ...r, required: e.target.checked };
                      update(next);
                    }}
                  />
                </td>
                <td className="px-2 py-1">
                  <Input
                    value={r.enumStr}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = { ...r, enumStr: e.target.value };
                      update(next);
                    }}
                    className="h-6 text-[11px]"
                    placeholder=""
                  />
                </td>
                <td className="px-2 py-1">
                  <Input
                    value={r.description}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = { ...r, description: e.target.value };
                      update(next);
                    }}
                    className="h-6 text-[11px]"
                  />
                </td>
                <td className="px-2 py-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0"
                    onClick={() => update(rows.filter((_, i) => i !== idx))}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-3 text-center text-muted-foreground italic text-[11px]">
                  No parameters - tool will accept an empty {'{}'} payload.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Button
        size="sm"
        variant="outline"
        className="h-7 text-[11px]"
        onClick={() => update([
          ...rows,
          { key: '', type: 'string', description: '', required: false, enumStr: '' },
        ])}
      >
        <Plus className="h-3 w-3 mr-1" /> Add field
      </Button>

      <div>
        <div className="text-[11px] text-muted-foreground mb-1">Generated schema</div>
        <pre className="text-[10px] font-mono bg-muted/20 border rounded p-2 max-h-40 overflow-auto">
          {preview}
        </pre>
      </div>
    </div>
  );
}
