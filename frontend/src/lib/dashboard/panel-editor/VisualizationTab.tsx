import { getAllPanelPlugins, getPanelPlugin } from '../panels/registry';
import type { DataFrame } from '../types';

interface Props {
  panelType: string;
  options: Record<string, unknown>;
  onTypeChange: (type: string) => void;
  onOptionsChange: (options: Record<string, unknown>) => void;
  data?: DataFrame[];
}

export function VisualizationTab({ panelType, options, onTypeChange, onOptionsChange, data }: Props) {
  const allPlugins = getAllPanelPlugins();
  const currentPlugin = getPanelPlugin(panelType);
  const OptionsEditor = currentPlugin?.meta.optionsEditor;

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs text-muted-foreground mb-2">Panel Type</p>
        <div className="grid grid-cols-4 gap-1.5">
          {allPlugins.map((p) => {
            const Icon = p.meta.icon;
            const active = p.meta.id === panelType;
            return (
              <button
                key={p.meta.id}
                onClick={() => onTypeChange(p.meta.id)}
                className={`flex flex-col items-center gap-1 p-2 rounded-md border text-center transition-colors ${
                  active ? 'bg-primary/10 border-primary' : 'hover:bg-accent'
                }`}
              >
                <Icon className={`h-4 w-4 ${active ? 'text-primary' : 'text-muted-foreground'}`} />
                <span className="text-xs">{p.meta.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {OptionsEditor && (
        <div>
          <p className="text-xs text-muted-foreground mb-2">Options</p>
          <OptionsEditor options={options} onChange={onOptionsChange} data={data} />
        </div>
      )}
    </div>
  );
}
