import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import {
  Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import type { BuilderNode, OutputHint, ToolOutputHints } from './builderState';

/**
 * Per-parameter "Reads from" picker rendered next to every input in
 * the Step Editor right pane.
 *
 * Drag-to-connect on the canvas is the primary affordance; this
 * dropdown is the keyboard-friendly fallback. Both paths land on the
 * same imperative ``setEdge`` / ``removeEdgeForTarget`` on the canvas
 * handle so the on-canvas arrow stays in sync.
 *
 * Encoding: an option's ``value`` is ``"<sourceNodeId>|<outputKey>"``
 * (the empty string represents "(literal)" -- clears any chain).
 */

const LITERAL_VALUE = '';
/** The Select control cannot hold an empty value, so "typed value" gets a stand-in. */
const LITERAL_ITEM = '__literal__';

interface ReadsFromDropdownProps {
  /** The node whose param is being edited. */
  consumerNodeId: string;
  /** The param name (input port) we are wiring. */
  consumerParam: string;
  /** All canvas nodes in insertion order; we offer the ones that come BEFORE the consumer. */
  allNodes: BuilderNode[];
  /** Per-tool output catalogue. */
  outputHints: ToolOutputHints;
  /** Current resolved value for the param (string or anything else). */
  currentValue: unknown;
  /** Fired with the picked source -- {nodeId, key}. */
  onPick: (input: { fromNode: string; fromKey: string }) => void;
  /** Fired when the user picks "(literal)" -- caller drops the edge + the placeholder. */
  onClearChain: () => void;
  className?: string;
}

/** Parse ``${steps.<id>.<key>}`` -> {id, key} so the select can self-render. */
function parsePlaceholder(value: unknown): { id: string; key: string } | null {
  if (typeof value !== 'string') return null;
  const m = /^\$\{\s*steps\.([a-zA-Z0-9_-]+)\.([^}\s]+)\s*\}$/.exec(value.trim());
  if (!m) return null;
  return { id: m[1], key: m[2] };
}

export function ReadsFromDropdown({
  consumerNodeId, consumerParam, allNodes, outputHints,
  currentValue, onPick, onClearChain, className,
}: ReadsFromDropdownProps) {
  // Only show producers that appear BEFORE the consumer in the
  // canvas's insertion order. (Topological order is computed
  // elsewhere; for the dropdown we keep the simpler insertion-order
  // heuristic so the picker stays predictable while the user is
  // mid-edit and the graph may not yet be a DAG.)
  const consumerIdx = allNodes.findIndex((n) => n.id === consumerNodeId);
  const sources = consumerIdx >= 0 ? allNodes.slice(0, consumerIdx) : [];

  const options = useMemo(() => {
    const opts: { value: string; label: string; group: string; desc?: string }[] = [];
    for (const src of sources) {
      const td = src.data.toolDef;
      const hints: OutputHint[] = (td && outputHints[td.name]) || outputHints[src.data.tool] || [];
      const group = `${src.data.name || src.data.tool} (${src.id})`;
      if (hints.length === 0) {
        // No catalogue entry -- still allow the user to type a key in
        // the canvas drag flow; the dropdown surfaces a single
        // "<no hints>" option so the producer appears in the picker.
        opts.push({ value: `${src.id}|`, label: 'No known outputs, drag on the canvas instead', group, desc: '' });
        continue;
      }
      for (const h of hints) {
        opts.push({
          value: `${src.id}|${h.key}`,
          label: h.key,
          group,
          desc: h.desc,
        });
      }
    }
    return opts;
  }, [sources, outputHints]);

  const current = parsePlaceholder(currentValue);
  const currentValueStr = current ? `${current.id}|${current.key}` : LITERAL_VALUE;

  const handleChange = (raw: string) => {
    if (raw === LITERAL_VALUE) {
      onClearChain();
      return;
    }
    // Skip "no hints" sentinel rows (key is empty).
    const sepAt = raw.indexOf('|');
    if (sepAt < 0) return;
    const id = raw.slice(0, sepAt);
    const key = raw.slice(sepAt + 1);
    if (!id || !key) return;
    onPick({ fromNode: id, fromKey: key });
  };

  const triggerClass = 'h-7 w-auto min-w-[9rem] max-w-[14rem] gap-1.5 px-2 text-xs';

  if (sources.length === 0) {
    return (
      <Select disabled value={LITERAL_ITEM}>
        <SelectTrigger className={cn(triggerClass, 'text-muted-foreground', className)} title="No prior step to read from" aria-label={`Source for ${consumerParam}`}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={LITERAL_ITEM}>No earlier steps</SelectItem>
        </SelectContent>
      </Select>
    );
  }

  // Group options by source node for the group labels.
  const grouped = new Map<string, typeof options>();
  for (const o of options) {
    if (!grouped.has(o.group)) grouped.set(o.group, []);
    grouped.get(o.group)!.push(o);
  }
  // A chained value whose key is not in the catalogue still has to show in the trigger.
  const currentKnown = !currentValueStr || options.some((o) => o.value === currentValueStr);

  return (
    <Select
      value={currentValueStr || LITERAL_ITEM}
      onValueChange={(v) => handleChange(v === LITERAL_ITEM ? LITERAL_VALUE : v)}
    >
      <SelectTrigger
        title={`Wire '${consumerParam}' to a prior step's output`}
        aria-label={`Source for ${consumerParam}`}
        className={cn(
          triggerClass,
          currentValueStr ? 'border-brand/40 font-mono text-primary dark:text-brand-hi' : 'text-muted-foreground',
          className,
        )}
      >
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={LITERAL_ITEM}>Typed value</SelectItem>
        {!currentKnown && current && (
          <SelectItem value={currentValueStr} className="font-mono text-xs">{current.id}.{current.key}</SelectItem>
        )}
        {Array.from(grouped.entries()).map(([groupLabel, opts]) => (
          <SelectGroup key={groupLabel}>
            <SelectLabel className="text-xs font-medium text-muted-foreground">{groupLabel}</SelectLabel>
            {opts.map((o) => (
              <SelectItem key={o.value} value={o.value} disabled={o.value.endsWith('|')} title={o.desc} className={cn('text-xs', !o.value.endsWith('|') && 'font-mono')}>
                {o.label}
              </SelectItem>
            ))}
          </SelectGroup>
        ))}
      </SelectContent>
    </Select>
  );
}

export default ReadsFromDropdown;
