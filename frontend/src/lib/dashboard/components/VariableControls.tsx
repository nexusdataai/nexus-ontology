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
    <div className="flex items-center gap-2 flex-wrap">
      {variables.map((v) => {
        const label = v.label || v.name;

        if (v.type === 'custom' && v.options?.length) {
          return (
            <div key={v.name} className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">{label}:</span>
              <Select value={values[v.name] || v.current?.value || ''} onValueChange={(val) => handleChange(v.name, val)}>
                <SelectTrigger className="h-7 text-xs w-auto min-w-[100px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {v.includeAll && (
                    <SelectItem value="$__all" className="text-xs">All</SelectItem>
                  )}
                  {v.options.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value} className="text-xs">
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
            <div key={v.name} className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">{label}:</span>
              <Input
                className="h-7 text-xs w-[120px]"
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
