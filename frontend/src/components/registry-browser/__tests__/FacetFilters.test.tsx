import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FacetFilters } from '../FacetFilters';
import type { FacetDescriptor, FacetState } from '../types';

const facets: FacetDescriptor[] = [
  {
    key: 'group',
    label: 'Group',
    options: [
      { value: 'o2c', count: 12 },
      { value: 'c360', count: 7 },
    ],
  },
  {
    key: 'risk_level',
    label: 'Risk',
    options: [
      { value: 'read_only', label: 'read only', count: 30 },
      { value: 'high_risk_write', label: 'high risk', count: 5 },
    ],
  },
];

describe('FacetFilters', () => {
  it('renders every option with its count', () => {
    render(<FacetFilters facets={facets} state={{}} onChange={() => {}} />);
    expect(screen.getByText('o2c')).toBeTruthy();
    expect(screen.getByText('c360')).toBeTruthy();
    expect(screen.getByText('12')).toBeTruthy();
    expect(screen.getByText('read only')).toBeTruthy();
  });

  it('toggles a single option within a facet', () => {
    const onChange = vi.fn<[FacetState], void>();
    render(<FacetFilters facets={facets} state={{}} onChange={onChange} />);

    fireEvent.click(screen.getByText('o2c'));
    expect(onChange).toHaveBeenCalledTimes(1);
    const next = onChange.mock.calls[0][0];
    expect(Array.from(next.group)).toEqual(['o2c']);
  });

  it('supports multiple selections within the same facet (OR)', () => {
    const state: FacetState = { group: new Set(['o2c']) };
    const onChange = vi.fn<[FacetState], void>();
    render(<FacetFilters facets={facets} state={state} onChange={onChange} />);

    fireEvent.click(screen.getByText('c360'));
    expect(onChange).toHaveBeenCalledTimes(1);
    const next = onChange.mock.calls[0][0];
    expect(Array.from(next.group).sort()).toEqual(['c360', 'o2c']);
  });

  it('removes the facet key entirely once the last option is unchecked', () => {
    const state: FacetState = { group: new Set(['o2c']) };
    const onChange = vi.fn<[FacetState], void>();
    render(<FacetFilters facets={facets} state={state} onChange={onChange} />);

    fireEvent.click(screen.getByText('o2c'));
    const next = onChange.mock.calls[0][0];
    expect(next.group).toBeUndefined();
  });

  it('clears all selections via the Clear button', () => {
    const state: FacetState = {
      group: new Set(['o2c']),
      risk_level: new Set(['high_risk_write']),
    };
    const onChange = vi.fn<[FacetState], void>();
    render(<FacetFilters facets={facets} state={state} onChange={onChange} />);

    // Top-bar "Clear" (capital C). The per-facet links use lowercase "clear".
    fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
    expect(onChange).toHaveBeenCalledWith({});
  });
});
