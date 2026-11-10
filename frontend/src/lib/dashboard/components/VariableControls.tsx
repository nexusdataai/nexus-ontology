import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import type { VariableModel } from '../model';

interface Props {
  variables: VariableModel[];
  values: Record<string, string>;
  onChange: (values: Record<string, string>) => void;
}

export function VariableControls({ variables, values, onChange }: Props) {
  if (variables.length === 0) return null;

  const handleChange = (name: string, value: string) => {
    onChange({ ...values, [name]: value });
  };

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      {variables.map((v) => {
        const label = v.label || v.name;

        if (v.type === 'custom' && v.options?.length) {
          return (
            <div key={v.name} className="flex items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground">{label}</span>
              <Select value={values[v.name] || v.current?.value || ''} onValueChange={(val) => handleChange(v.name, val)}>
                <SelectTrigger className="h-8 w-auto min-w-[120px] text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {v.includeAll && (
                    <SelectItem value="$__all">All</SelectItem>
                  )}
                  {v.options.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.text}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          );
        }

        if (v.type === 'textbox' || v.type === 'constant') {
          return (
            <div key={v.name} className="flex items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground">{label}</span>
              <Input
                className="h-8 w-36 text-sm"
                value={values[v.name] || v.current?.value || ''}
                onChange={(e) => handleChange(v.name, e.target.value)}
                readOnly={v.type === 'constant'}
              />
            </div>
          );
        }

        return null;
      })}
    </div>
  );
}
