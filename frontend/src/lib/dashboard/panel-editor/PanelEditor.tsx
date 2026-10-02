import { useState, useEffect, useRef, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Check, X, GripHorizontal } from 'lucide-react';
import type { PanelModel } from '../model';
import type { TimeRange } from '../types';
import { QueryTab } from './QueryTab';
import { VisualizationTab } from './VisualizationTab';
import { PanelChrome } from '../components/PanelChrome';

interface Props {
  panel: PanelModel | null;
  open: boolean;
  timeRange?: TimeRange;
  onSave: (panel: PanelModel) => void;
  onCancel: () => void;
}

const MIN_EDITOR_HEIGHT = 200;
const DEFAULT_EDITOR_HEIGHT = 320;

export function PanelEditor({ panel, open, timeRange, onSave, onCancel }: Props) {
  const [draft, setDraft] = useState<PanelModel | null>(null);
  const [editorHeight, setEditorHeight] = useState(DEFAULT_EDITOR_HEIGHT);
  const dragRef = useRef<{ startY: number; startH: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && panel) {
      setDraft(JSON.parse(JSON.stringify(panel)));
    } else if (!open) {
      setDraft(null);
    }
  }, [open, panel?.id]);

  const current = draft ?? panel;

  const handleSave = () => {
    if (current) {
      onSave(current);
      setDraft(null);
    }
  };

  const handleClose = () => {
    onCancel();
    setDraft(null);
  };

  const update = (patch: Partial<PanelModel>) => {
    setDraft((prev) => ({ ...(prev ?? current!), ...patch }));
  };

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = { startY: e.clientY, startH: editorHeight };

    const handleMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const delta = dragRef.current.startY - ev.clientY;
      const newH = Math.max(MIN_EDITOR_HEIGHT, Math.min(dragRef.current.startH + delta, window.innerHeight - 200));
      setEditorHeight(newH);
    };

    const handleUp = () => {
      dragRef.current = null;
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
  }, [editorHeight]);

  if (!open || !current) return null;

  return (
    <div ref={containerRef} className="flex flex-col h-full">
      {/* Top: Panel preview area */}
      <div className="flex-1 min-h-[200px] overflow-auto bg-muted/5 p-4 flex items-center justify-center">
        <div className="w-full max-w-4xl h-full min-h-[200px] rounded-md overflow-hidden border bg-background">
          <PanelChrome
            panel={current}
            width={800}
            height={Math.max(300, window.innerHeight - editorHeight - 160)}
            timeRange={timeRange}
            isEditing={false}
          />
        </div>
      </div>

      {/* Resize handle */}
      <div
        className="h-2 flex items-center justify-center cursor-row-resize bg-border/50 hover:bg-primary/20 transition-colors flex-shrink-0"
        onMouseDown={handleDragStart}
      >
        <GripHorizontal className="h-3 w-3 text-muted-foreground" />
      </div>

      {/* Bottom: Editor area */}
      <div className="flex-shrink-0 border-t bg-background overflow-hidden" style={{ height: editorHeight }}>
        {/* Editor toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30 flex-shrink-0">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <Label className="text-xs text-muted-foreground whitespace-nowrap">Title</Label>
            <Input
              className="h-7 text-xs max-w-xs"
              value={current.title}
              onChange={(e) => update({ title: e.target.value })}
            />
          </div>
          <div className="flex gap-1.5">
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={handleClose}>
              <X className="h-3.5 w-3.5 mr-1" /> Discard
            </Button>
            <Button size="sm" className="h-7 text-xs" onClick={handleSave}>
              <Check className="h-3.5 w-3.5 mr-1" /> Apply
            </Button>
          </div>
        </div>

        {/* Tabbed content */}
        <Tabs defaultValue="query" className="h-[calc(100%-44px)] flex flex-col">
          <TabsList className="mx-4 mt-2 flex-shrink-0 w-fit">
            <TabsTrigger value="query" className="text-xs">Query</TabsTrigger>
            <TabsTrigger value="visualization" className="text-xs">Visualization</TabsTrigger>
          </TabsList>
          <TabsContent value="query" className="flex-1 overflow-auto px-4 pb-4 mt-2">
            <QueryTab
              targets={current.targets}
              onChange={(targets) => update({ targets })}
              onRunQuery={() => {}}
              onPanelTypeChange={(type) => update({ type, options: {} })}
              onTitleChange={(title) => update({ title })}
            />
          </TabsContent>
          <TabsContent value="visualization" className="flex-1 overflow-auto px-4 pb-4 mt-2">
            <VisualizationTab
              panelType={current.type}
              options={current.options}
              onTypeChange={(type) => update({ type, options: {} })}
              onOptionsChange={(options) => update({ options })}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
