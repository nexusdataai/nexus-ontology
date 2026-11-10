import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Icon } from '@/components/ds/Icon';
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
        variant="ghost" size="sm" className="h-7 gap-1 px-1.5 text-xs text-muted-foreground"
        title="No prior steps to reference"
        disabled
      >
        <Icon name="link" className="h-3 w-3" /> Reference
      </Button>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost" size="sm" className="h-7 gap-1 px-1.5 text-xs text-muted-foreground hover:text-foreground"
          title={`Insert a reference to a prior step's output into '${consumerParam}'`}
        >
          <Icon name="link" className="h-3 w-3" /> Reference
          <Icon name="chevron-down" className="h-3 w-3" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="scroll-thin max-h-72 w-64 overflow-auto p-1">
        {sources.map((src) => {
          const tool = src.data.toolDef;
          const hints: OutputHint[] = (tool && outputHints[tool.name]) || outputHints[src.data.tool] || [];
          return (
            <div key={src.id} className="mb-1 last:mb-0">
              <div className="flex items-baseline gap-1.5 border-b border-border px-2 py-1.5 text-xs font-medium text-foreground">
                <span className="min-w-0 truncate">{src.data.name || src.data.tool}</span>
                <span className="shrink-0 font-mono font-normal text-subtle-foreground">{src.id}</span>
              </div>
              {hints.length === 0 && (
                <div className="px-2 py-1.5 text-xs text-muted-foreground">
                  No known outputs. Type a key by hand.
                </div>
              )}
              {hints.map((h) => (
                <button
                  key={h.key}
                  type="button"
                  className="flex w-full items-baseline gap-2 rounded px-2 py-1.5 text-left text-xs transition-colors hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
                  onClick={() => {
                    onPick(`\${steps.${src.id}.${h.key}}`);
                    setOpen(false);
                  }}
                  title={`${h.kind} - ${h.desc}`}
                >
                  <span className="min-w-0 truncate font-mono text-foreground">{h.key}</span>
                  <span className="ml-auto shrink-0 text-muted-foreground">{h.kind}</span>
                </button>
              ))}
            </div>
          );
        })}
      </PopoverContent>
    </Popover>
  );
}

export default OutputHintMenu;
