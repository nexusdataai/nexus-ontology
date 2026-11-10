import { useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ds/Icon';
import { Chips, SearchInput } from '@/components/ds/kit';
import { getAllPanelPlugins } from '../panels/registry';
import { PANEL_CATEGORIES, panelIconName, panelTypeLabel } from './panelIcon';

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (panelType: string) => void;
}

/** Step one of adding a panel: choose how the data is shown. */
export function AddPanelDialog({ open, onOpenChange, onSelect }: DialogProps) {
  const [category, setCategory] = useState<string>('all');
  const [search, setSearch] = useState('');
  const plugins = getAllPanelPlugins();

  const options = useMemo(
    () =>
      PANEL_CATEGORIES.map((c) => ({
        value: c.id as string,
        label: c.label,
        count: c.id === 'all' ? plugins.length : plugins.filter((p) => p.meta.category === c.id).length,
      })).filter((c) => c.value === 'all' || c.count > 0),
    [plugins],
  );

  const q = search.trim().toLowerCase();
  const shown = plugins.filter(
    (p) =>
      (category === 'all' || p.meta.category === category) &&
      (!q || p.meta.name.toLowerCase().includes(q) || p.meta.description.toLowerCase().includes(q)),
  );

  const handleSelect = (type: string) => {
    onSelect(type);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-w-2xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-5 pb-4 pt-5 pr-12 text-left">
          <DialogTitle className="text-lg font-medium">Add a panel</DialogTitle>
          <DialogDescription>
            Choose how the data should be shown. You pick the data and the display options next.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center gap-2.5 border-b border-border px-5 py-3">
          <SearchInput value={search} onChange={setSearch} placeholder="Search panel types" className="w-full sm:w-56" />
          <Chips label="Panel category" options={options} value={category} onChange={setCategory} />
        </div>

        <div className="scroll-thin max-h-[min(420px,60dvh)] overflow-y-auto p-2">
          {shown.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">No panel type matches. Try another search.</p>
          ) : (
            <ul className="grid gap-0.5 sm:grid-cols-2">
              {shown.map((p) => (
                <li key={p.meta.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(p.meta.id)}
                    className="group flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-accent focus-visible:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <Icon name={panelIconName(p.meta)} className="mt-0.5 text-muted-foreground group-hover:text-primary dark:group-hover:text-brand-hi" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-foreground">{panelTypeLabel(p.meta.name)}</span>
                      <span className="line-clamp-2 block text-xs text-muted-foreground">{p.meta.description}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface Props {
  onSelect: (panelType: string) => void;
}

/** "Add panel" button with its own dialog. */
export function AddPanelWidget({ onSelect }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Icon name="plus" className="h-3.5 w-3.5" /> Add panel
      </Button>
      <AddPanelDialog open={open} onOpenChange={setOpen} onSelect={onSelect} />
    </>
  );
}
