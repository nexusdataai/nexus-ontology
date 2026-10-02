import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// Mock both services before importing the SUT so the adapters resolve
// to our spies instead of the real apiClient. ``vi.mock`` is hoisted so
// we declare the spy fns via ``vi.hoisted`` to keep the same reference
// available in both the factory and the test bodies.
const { executeOne, invoke } = vi.hoisted(() => ({
  executeOne: vi.fn(),
  invoke: vi.fn(),
}));
vi.mock('@/services/reactToolsDiagnosticsService', () => ({
  reactToolsDiagnosticsService: { executeOne },
}));
vi.mock('@/services/connectorApiWorkbenchService', () => ({
  connectorApiWorkbenchService: { invoke },
}));

import {
  ExecuteDrawer,
  adapterFromTool,
  adapterFromConnectorApi,
} from '../ExecuteDrawer';

describe('ExecuteDrawer adapters', () => {
  beforeEach(() => {
    executeOne.mockReset();
    invoke.mockReset();
  });

  it('adapterFromTool dispatches through reactToolsDiagnosticsService.executeOne and produces an envelope', async () => {
    executeOne.mockResolvedValue({
      tool_id: 'noop',
      status: 'pass',
      duration_ms: 17,
      result: { ok: true },
      result_preview: '{ok}',
      risk_level: 'read_only',
    });
    const adapter = adapterFromTool({
      toolName: 'noop',
      defaultParams: { x: 1 },
      riskLevel: 'read_only',
    });
    const env = await adapter.run({ x: 1 });
    expect(executeOne).toHaveBeenCalledWith('noop', { x: 1 });
    expect(env.status).toBe('pass');
    expect(env.duration_ms).toBe(17);
    expect((env.result as any).ok).toBe(true);
    expect(env.extras?.risk_level).toBe('read_only');
  });

  it('adapterFromConnectorApi dispatches through connectorApiWorkbenchService.invoke and maps verdicts', async () => {
    invoke.mockResolvedValue({
      api_id: 'oracle.invoice.status.set',
      operation: 'PATCH /x',
      request: { method: 'PATCH', path: '/x', body: {}, full_payload: {} },
      http_status: 200,
      response: { invoice_id: 'INV-1' },
      http_error: null,
      verification: { audit_appeared: true } as any,
      duration_ms: 42,
      verdict: 'verified',
      marker: 'diag',
    });
    const adapter = adapterFromConnectorApi({
      apiId: 'oracle.invoice.status.set',
      defaultParams: { invoice_id: 'INV-1' },
      riskLevel: 'high_risk_write',
    });
    const env = await adapter.run({ invoice_id: 'INV-1' });
    expect(invoke).toHaveBeenCalledWith('oracle.invoice.status.set', { invoice_id: 'INV-1' });
    expect(env.status).toBe('pass'); // verified -> pass
    expect((env.result as any).invoice_id).toBe('INV-1');
    expect(env.extras?.verdict).toBe('verified');
  });

  it('renders adapter id + risk pill in the drawer header', () => {
    const adapter = adapterFromTool({
      toolName: 'place_credit_hold',
      riskLevel: 'high_risk_write',
    });
    render(<ExecuteDrawer adapter={adapter} onClose={() => {}} />);
    expect(screen.getByText('place_credit_hold')).toBeTruthy();
    expect(screen.getByText('high risk write')).toBeTruthy();
  });

  it('invokes the adapter on Run click and surfaces the result envelope', async () => {
    executeOne.mockResolvedValue({
      tool_id: 'noop',
      status: 'pass',
      duration_ms: 5,
      result: { value: 7 },
    });
    const adapter = adapterFromTool({ toolName: 'noop' });
    render(<ExecuteDrawer adapter={adapter} onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /Run/i }));
    await waitFor(() => expect(executeOne).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText('pass')).toBeTruthy());
  });

  it('surfaces a JSON parse error without invoking the adapter', async () => {
    const adapter = adapterFromTool({ toolName: 'noop' });
    render(<ExecuteDrawer adapter={adapter} onClose={() => {}} />);
    const ta = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(ta, { target: { value: 'not json {' } });
    fireEvent.click(screen.getByRole('button', { name: /Run/i }));
    expect(executeOne).not.toHaveBeenCalled();
    expect(screen.getByText(/parse error/i)).toBeTruthy();
  });
});
