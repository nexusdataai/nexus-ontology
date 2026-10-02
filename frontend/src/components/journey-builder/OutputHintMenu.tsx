import { useState } from 'react';
import { ChevronDown, Link2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { BuilderNode, OutputHint, ToolOutputHints } from './builderState';

interface Props {
  /** All canvas nodes (the menu lists nodes that come BEFORE the consumer). */
  allNodes: BuilderNode[];
  /** Node whose param the user is editing. */
  consumerNodeId: string;
  /** Param name the user is wiring into (e.g. ``customer_id``). */
  consumerParam: string;
  /** Per-tool output catalogue. */
  outputHints: ToolOutputHints;
  /** Callback fired with the chosen ``${steps.<from>.<key>}`` placeholder. */
  onPick: (placeholder: string) => void;
}

/**
 * Compact popover the right-pane Step Editor renders next to a
 * parameter input. Lists every prior node + each output port that node
 * exposes via its tool's hint map. Clicking inserts a
 * ``${steps.<from_node>.<from_key>}`` placeholder into the param.
 *
 * Keyboard-friendly fallback for users who would rather not drag on
 * the canvas. The Connect-by-drag flow on the canvas remains the
 * primary affordance.
 */
export function OutputHintMenu({
  allNodes, consumerNodeId, consumerParam, outputHints, onPick,
}: Props) {
  const [open, setOpen] = useState(false);
  const consumerIdx = allNodes.findIndex((n) => n.id === consumerNodeId);
  const sources = consumerIdx >= 0 ? allNodes.slice(0, consumerIdx) : [];

  if (sources.length === 0) {
    return (
      <Button
        variant="ghost" size="sm" className="h-6 px-1 text-[10px] text-muted-foreground"
        title="No prior steps to reference"
        disabled
      >
        <Link2 className="h-3 w-3 mr-1" /> reference
      </Button>
    );
  }

  return (
    <div className="relative inline-block">
      <Button
        variant="ghost" size="sm" className="h-6 px-1 text-[10px]"
        onClick={() => setOpen((o) => !o)}
        title={`Insert a reference to a prior step's output into '${consumerParam}'`}
      >
        <Link2 className="h-3 w-3 mr-1" /> reference
        <ChevronDown className="h-3 w-3 ml-0.5" />
      </Button>
      {open && (
        <div
          className={cn(
            'absolute z-50 mt-1 left-0 w-64 max-h-72 overflow-auto rounded-md border',
            'bg-card shadow-md p-1 text-[11px]',
          )}
        >
          {sources.map((src) => {
            const tool = src.data.toolDef;
            const hints: OutputHint[] = (tool && outputHints[tool.name]) || outputHints[src.data.tool] || [];
            return (
              <div key={src.id} className="mb-1 last:mb-0">
                <div className="px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground font-medium border-b">
                  {src.data.name || src.data.tool} <span className="font-mono text-[10px] text-muted-foreground/70">{src.id}</span>
                </div>
                {hints.length === 0 && (
                  <div className="px-2 py-1 text-[10px] text-muted-foreground italic">
                    no hints; type a key manually
                  </div>
                )}
                {hints.map((h) => (
                  <button
                    key={h.key}
                    className="w-full text-left px-2 py-1 hover:bg-muted/40 rounded"
                    onClick={() => {
                      onPick(`\${steps.${src.id}.${h.key}}`);
                      setOpen(false);
                    }}
                    title={`${h.kind} - ${h.desc}`}
                  >
                    <span className="font-mono">{h.key}</span>
                    <span className="ml-1 text-[10px] text-muted-foreground">{h.kind}</span>
                  </button>
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default OutputHintMenu;
