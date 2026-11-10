import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { getAllPanelPlugins } from '../panels/registry';
import { useState } from 'react';

interface Props {
  onSelect: (panelType: string) => void;
}

const categories = [
  { id: 'all', label: 'All' },
  { id: 'stat', label: 'Stats' },
  { id: 'chart', label: 'Charts' },
  { id: 'table', label: 'Tables' },
  { id: 'timeline', label: 'Timelines' },
  { id: 'graph', label: 'Graphs' },
  { id: 'misc', label: 'Other' },
];

export function AddPanelWidget({ onSelect }: Props) {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  const plugins = getAllPanelPlugins();

  const handleSelect = (type: string) => {
    onSelect(type);
    setOpen(false);
  };

  const filteredPlugins = activeTab === 'all'
    ? plugins
    : plugins.filter((p) => p.meta.category === activeTab);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="h-8 gap-1.5">
          <Plus className="h-3.5 w-3.5" /> Add Panel
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-sm">Add Panel</DialogTitle>
        </DialogHeader>

        <div className="flex gap-1 border-b pb-2 overflow-x-auto">
          {categories.map((cat) => {
            const count = cat.id === 'all'
              ? plugins.length
              : plugins.filter((p) => p.meta.category === cat.id).length;
            if (count === 0 && cat.id !== 'all') return null;
            return (
              <button
                key={cat.id}
                onClick={() => setActiveTab(cat.id)}
                className={`px-3 py-1.5 text-xs rounded-md whitespace-nowrap transition-colors ${
                  activeTab === cat.id
                    ? 'bg-primary text-primary-foreground font-medium'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                }`}
              >
                {cat.label}
                <span className="ml-1.5 text-xs opacity-70">{count}</span>
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-3 gap-2 max-h-[400px] overflow-y-auto pt-1">
          {filteredPlugins.map((p) => {
            const Icon = p.meta.icon;
            return (
              <button
                key={p.meta.id}
                onClick={() => handleSelect(p.meta.id)}
                className="flex items-center gap-2.5 p-3 rounded-md border hover:bg-accent transition-colors text-left"
              >
                <Icon className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs font-medium truncate">{p.meta.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{p.meta.description}</p>
                </div>
              </button>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
