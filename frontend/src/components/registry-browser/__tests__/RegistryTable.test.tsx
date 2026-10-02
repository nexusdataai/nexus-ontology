import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RegistryTable } from '../RegistryTable';
import type { RegistryColumn } from '../types';

interface Row {
  id: string;
  name: string;
  age: number;
}

const rows: Row[] = [
  { id: 'a', name: 'Charlie', age: 22 },
  { id: 'b', name: 'Alice',   age: 35 },
  { id: 'c', name: 'Bob',     age: 28 },
];

const columns: RegistryColumn<Row>[] = [
  { key: 'name', label: 'Name', sortBy: (r) => r.name, render: (r) => r.name },
  { key: 'age',  label: 'Age',  sortBy: (r) => r.age,  render: (r) => r.age },
];

describe('RegistryTable', () => {
  it('renders every row when no filter is applied', () => {
    render(
      <RegistryTable rows={rows} columns={columns} rowKey={(r) => r.id} />,
    );
    expect(screen.getByText('Charlie')).toBeTruthy();
    expect(screen.getByText('Alice')).toBeTruthy();
    expect(screen.getByText('Bob')).toBeTruthy();
  });

  it('filters rows via the supplied filterFn + search prop', () => {
    render(
      <RegistryTable
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        search="ali"
        filterFn={(r, q) => r.name.toLowerCase().includes(q.toLowerCase())}
      />,
    );
    expect(screen.getByText('Alice')).toBeTruthy();
    expect(screen.queryByText('Bob')).toBeNull();
    expect(screen.queryByText('Charlie')).toBeNull();
  });

  it('invokes onSelect when a row is clicked', () => {
    const onSelect = vi.fn();
    render(
      <RegistryTable rows={rows} columns={columns} rowKey={(r) => r.id} onSelect={onSelect} />,
    );
    const aliceCell = screen.getByText('Alice');
    fireEvent.click(aliceCell);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0].id).toBe('b');
  });

  it('sorts ascending then descending when a sortable header is clicked', () => {
    render(
      <RegistryTable rows={rows} columns={columns} rowKey={(r) => r.id} />,
    );
    const nameHeader = screen.getByText('Name');

    // First click -> asc by name: Alice, Bob, Charlie
    fireEvent.click(nameHeader);
    const bodyRows1 = screen.getAllByRole('row').slice(1).map((r) => r.textContent || '');
    expect(bodyRows1[0]).toContain('Alice');
    expect(bodyRows1[1]).toContain('Bob');
    expect(bodyRows1[2]).toContain('Charlie');

    // Second click -> desc: Charlie, Bob, Alice
    fireEvent.click(nameHeader);
    const bodyRows2 = screen.getAllByRole('row').slice(1).map((r) => r.textContent || '');
    expect(bodyRows2[0]).toContain('Charlie');
    expect(bodyRows2[1]).toContain('Bob');
    expect(bodyRows2[2]).toContain('Alice');
  });

  it('renders the empty-state message when filter eliminates everything', () => {
    render(
      <RegistryTable
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        search="zzz"
        filterFn={(r, q) => r.name.includes(q)}
        emptyMessage="no rows :)"
      />,
    );
    expect(screen.getByText('no rows :)')).toBeTruthy();
  });
});
