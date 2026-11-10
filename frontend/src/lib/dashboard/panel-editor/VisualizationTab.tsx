import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';
import { getAllPanelPlugins, getPanelPlugin } from '../panels/registry';
import { panelIconName, panelTypeLabel } from '../components/panelIcon';
import type { DataFrame } from '../types';

interface TypeProps {
  panelType: string;
  onTypeChange: (type: string) => void;
}

/** "Visualisation" section: the current panel type, and the list to change it. */
export function PanelTypePicker({ panelType, onTypeChange }: TypeProps) {
  const [choosing, setChoosing] = useState(false);
  const allPlugins = getAllPanelPlugins();
  const current = getPanelPlugin(panelType);

  return (
    <div>
      <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2.5">
        <span className="flex min-w-0 items-start gap-3">
          <Icon name={current ? panelIconName(current.meta) : 'help'} className="mt-0.5 text-primary dark:text-brand-hi" />
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium text-foreground">
              {current ? panelTypeLabel(current.meta.name) : `Unknown type: ${panelType}`}
            </span>
            {current && <span className="line-clamp-2 block text-xs text-muted-foreground">{current.meta.description}</span>}
          </span>
        </span>
        <Button variant="outline" size="sm" type="button" aria-expanded={choosing} onClick={() => setChoosing((c) => !c)}>
          {choosing ? 'Done' : 'Change'}
        </Button>
      </div>

      {choosing && (
        <>
          <div role="radiogroup" aria-label="Panel type" className="mt-2 grid grid-cols-2 gap-1 sm:grid-cols-3">
            {allPlugins.map((p) => {
              const active = p.meta.id === panelType;
              return (
                <button
                  key={p.meta.id}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  title={p.meta.description}
                  onClick={() => onTypeChange(p.meta.id)}
                  className={cn(
                    'flex h-9 items-center gap-2 rounded-md border px-2.5 text-left text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    active
                      ? 'border-brand/50 bg-brand/10 font-medium text-foreground'
                      : 'border-transparent text-muted-foreground hover:bg-accent hover:text-foreground',
                  )}
                >
                  <Icon name={panelIconName(p.meta)} className={cn('h-3.5 w-3.5', active && 'text-primary dark:text-brand-hi')} />
                  <span className="truncate">{panelTypeLabel(p.meta.name)}</span>
                </button>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-subtle-foreground">Changing the type resets the display options below.</p>
        </>
      )}
    </div>
  );
}

interface OptionsProps {
  panelType: string;
  options: Record<string, unknown>;
  onOptionsChange: (options: Record<string, unknown>) => void;
  data?: DataFrame[];
}

/** "Display options" section: the options the chosen panel type offers. */
export function PanelDisplayOptions({ panelType, options, onOptionsChange, data }: OptionsProps) {
  const OptionsEditor = getPanelPlugin(panelType)?.meta.optionsEditor;
  if (!OptionsEditor) {
    return <p className="text-sm text-muted-foreground">This panel type has no display options.</p>;
  }
  return <OptionsEditor options={options} onChange={onOptionsChange} data={data} />;
}

interface Props extends TypeProps, Omit<OptionsProps, 'panelType'> {}

/** Type picker and display options together (kept for existing callers). */
export function VisualizationTab({ panelType, options, onTypeChange, onOptionsChange, data }: Props) {
  return (
    <div className="space-y-5">
      <PanelTypePicker panelType={panelType} onTypeChange={onTypeChange} />
      <PanelDisplayOptions panelType={panelType} options={options} onOptionsChange={onOptionsChange} data={data} />
    </div>
  );
}
