import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export interface ConfigFieldSchema {
  key: string;
  type?: string;
  label?: string;
  enum?: string[];
  default?: unknown;
  placeholder?: string;
  help?: string;
  min?: number;
}

export default function NodeSchemaForm({
  fields,
  params,
  onChange,
}: {
  fields: ConfigFieldSchema[];
  params: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}) {
  if (!fields.length) return null;
  return (
    <div className="space-y-3">
      {fields.map(f => (
        <div key={f.key} className="space-y-1">
          <label className="block text-xs text-muted-foreground">{f.label || f.key}</label>
          {f.type === 'enum' && f.enum?.length ? (
            <Select
              value={String(params[f.key] ?? f.default ?? '')}
              onValueChange={v => onChange({ ...params, [f.key]: v })}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {f.enum.map(opt => (
                  <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              type={f.type === 'number' ? 'number' : 'text'}
              value={f.type === 'number' ? String(params[f.key] ?? f.default ?? '') : String(params[f.key] ?? f.default ?? '')}
              placeholder={f.placeholder}
              onChange={e => {
                const raw = e.target.value;
                onChange({
                  ...params,
                  [f.key]: f.type === 'number' ? (raw === '' ? '' : Number(raw)) : raw,
                });
              }}
            />
          )}
          {f.help && <p className="text-[10px] text-muted-foreground">{f.help}</p>}
        </div>
      ))}
    </div>
  );
}