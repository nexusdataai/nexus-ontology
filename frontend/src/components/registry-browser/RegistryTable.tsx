import { useMemo, useState, type ReactNode } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RegistryColumn } from './types';

interface RegistryTableProps<T> {
  rows: T[];
  columns: RegistryColumn<T>[];
  rowKey: (row: T) => string;
  /** Free-text search; the parent decides what to match via ``filterFn``. */
  search?: string;
  filterFn?: (row: T, search: string) => boolean;
  onSelect?: (row: T) => void;
  selectedKey?: string;
  emptyMessage?: ReactNode;
  /** CSS height for the scroll body (default 60vh). */
  height?: string;
  /** Optional small label rendered above the right side of the header. */
  resultSummary?: ReactNode;
}

/**
 * Generic searchable + sortable table over a list of records.
 *
 * Designed for the registry-browser panels (~70 tools, ~30 connector
 * APIs) so client-side filter / sort is fine -- no virtualisation, no
 * debounce. Header is sticky; rows clickable; supports a selected-row
 * highlight so a parent drawer can mirror the selection.
 */
export function RegistryTable<T>(props: RegistryTableProps<T>) {
  const {
    rows,
    columns,
    rowKey,
    search = '',
    filterFn,
    onSelect,
    selectedKey,
    emptyMessage,
    height = '60vh',
    resultSummary,
  } = props;

  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const filtered = useMemo(() => {
    if (!search || !filterFn) return rows;
    const needle = search.trim();
    if (!needle) return rows;
    return rows.filter((r) => filterFn(r, needle));
  }, [rows, search, filterFn]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.sortBy) return filtered;
    const accessor = col.sortBy;
    const copy = [...filtered];
    copy.sort((a, b) => {
      const av = accessor(a);
      const bv = accessor(b);
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return copy;
  }, [filtered, columns, sortKey, sortDir]);

  const toggleSort = (key: string) => {
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir('asc');
      return;
    }
    setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
  };

  return (
    <div className="border rounded-md flex flex-col bg-card/30" style={{ height }}>
      {resultSummary && (
        <div className="flex items-center justify-end gap-3 px-2 py-1 border-b text-[11px] text-muted-foreground">
          {resultSummary}
        </div>
      )}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-[12px]">
          <thead className="sticky top-0 z-10 bg-muted/40 backdrop-blur">
            <tr className="text-left">
              {columns.map((c) => {
                const sortable = !!c.sortBy;
                const active = sortKey === c.key;
                return (
                  <th
                    key={c.key}
                    className={cn(
                      'px-2 py-1.5 font-medium text-muted-foreground select-none',
                      c.headerClassName,
                      sortable && 'cursor-pointer hover:text-foreground',
                    )}
                    onClick={sortable ? () => toggleSort(c.key) : undefined}
                  >
                    <span className="inline-flex items-center gap-1">
                      {c.label}
                      {sortable && active && (
                        sortDir === 'asc'
                          ? <ChevronUp className="h-3 w-3" />
                          : <ChevronDown className="h-3 w-3" />
                      )}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => {
              const k = rowKey(row);
              const selected = selectedKey === k;
              return (
                <tr
                  key={k}
                  data-key={k}
                  onClick={onSelect ? () => onSelect(row) : undefined}
                  className={cn(
                    'border-t border-border/30 transition-colors',
                    onSelect && 'cursor-pointer hover:bg-muted/30',
                    selected && 'bg-primary/10 hover:bg-primary/15',
                  )}
                >
                  {columns.map((c) => (
                    <td key={c.key} className={cn('px-2 py-1.5 align-top', c.className)}>
                      {c.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-muted-foreground text-xs">
                  {emptyMessage || 'No rows match the current filters.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default RegistryTable;
