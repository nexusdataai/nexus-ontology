import { useMemo, useState, type ReactNode } from 'react';
import { Icon } from '@/components/ds/Icon';
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
    <div className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card shadow-xs" style={{ height }}>
      {resultSummary && (
        <div className="flex shrink-0 items-center justify-end gap-3 border-b border-border px-4 py-2 text-xs text-muted-foreground">
          {resultSummary}
        </div>
      )}
      <div className="scroll-thin min-h-0 flex-1 overflow-auto pb-14">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="sticky top-0 z-10 bg-surface-2">
            <tr className="border-b border-border text-left">
              {columns.map((c) => {
                const sortable = !!c.sortBy;
                const active = sortKey === c.key;
                return (
                  <th
                    key={c.key}
                    scope="col"
                    aria-sort={active ? (sortDir === 'asc' ? 'ascending' : 'descending') : undefined}
                    className={cn('h-10 whitespace-nowrap px-4 text-xs font-medium text-muted-foreground', c.headerClassName)}
                  >
                    {sortable ? (
                      <button
                        type="button"
                        onClick={() => toggleSort(c.key)}
                        className={cn(
                          'group/sort -mx-1 inline-flex items-center gap-1 rounded px-1 py-0.5 transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                          active && 'text-foreground',
                        )}
                      >
                        {c.label}
                        <Icon
                          name={active && sortDir === 'desc' ? 'chevron-down' : 'chevron-up'}
                          className={cn('h-3 w-3 transition-opacity', active ? 'opacity-100' : 'opacity-0 group-hover/sort:opacity-50')}
                        />
                      </button>
                    ) : c.label}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => {
              const k = rowKey(row);
              const selected = selectedKey === k;
              return (
                <tr
                  key={k}
                  data-key={k}
                  tabIndex={onSelect ? 0 : undefined}
                  aria-selected={onSelect ? selected : undefined}
                  onClick={onSelect ? () => onSelect(row) : undefined}
                  onKeyDown={onSelect ? (e) => { if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); onSelect(row); } } : undefined}
                  style={{ ['--i' as any]: Math.min(i, 14) }}
                  className={cn(
                    'rise border-b border-border transition-colors duration-150 last:border-b-0',
                    onSelect && 'cursor-pointer hover:bg-surface-2/60 focus-visible:bg-surface-2/60 focus-visible:outline-none',
                    selected && 'bg-accent hover:bg-accent',
                  )}
                >
                  {columns.map((c) => (
                    <td key={c.key} className={cn('px-4 py-2.5 align-middle', c.className)}>
                      {c.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-sm text-muted-foreground">
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
