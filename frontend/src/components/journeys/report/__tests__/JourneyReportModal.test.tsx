/**
 * Smoke tests for the schema-driven JourneyReportModal.
 *
 * Verifies the section dispatcher picks the right renderer for each
 * envelope ``kind`` and that the summary strip carries values from
 * the backend builder's output.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { JourneyReportModal } from '../JourneyReportModal';

vi.mock('@/services/callProcessingJourneyService', () => ({
  callProcessingJourneyService: {
    getAggregateReport: vi.fn(),
  },
}));

import { callProcessingJourneyService } from '@/services/callProcessingJourneyService';

const ENVELOPE = {
  schema_version: '1',
  journey_id: 'j-1',
  journey_title: 'Weekly SKU Replenishment',
  solution_id: 'demand-forecasting',
  title: 'Demand Forecasting Report',
  icon: 'TrendingUp',
  summary_kpis: [
    {
      key: 'mape', label: 'MAPE', icon: 'Target',
      format: 'percent', value: 12.5, status: 'ok',
    },
    {
      key: 'stockout_rate_pct', label: 'Stockout Risk', icon: 'AlertTriangle',
      format: 'percent', value: 8.0, status: 'warn',
    },
  ],
  sections: [
    {
      id: 'volumes', title: 'Forecast Volumes', kind: 'kpi_grid',
      kpis: [
        { key: 'total_forecast_qty', label: 'Forecast Units',
          format: 'integer', value: 12345, status: null },
      ],
    },
    {
      id: 'alerts', title: 'Demand Alerts', kind: 'alerts_list',
      alerts: [
        { type: 'demand_spike', severity: 'high', jobId: 'JOB-001',
          message: 'sudden uptick on SKU-A' },
      ],
      groups: [{ key: 'demand_spike', label: 'Demand Spike', count: 1 }],
    },
    {
      id: 'timeline', title: 'Run Timeline', kind: 'timeline',
      events: [
        { fromState: 'pending', toState: 'in_progress',
          timestamp: '2026-05-17T20:00:00Z' },
      ],
    },
    {
      id: 'breakdown', title: 'Step Breakdown', kind: 'step_breakdown',
      steps: [
        { step_id: 's1', name: 'Step 1', tool: 'do_thing',
          completed: 3, failed: 1, pending: 0, other: 0, total: 4 },
      ],
    },
  ],
  total_jobs: 3,
  generated_at: '2026-05-17T20:00:00Z',
};

beforeEach(() => {
  (callProcessingJourneyService.getAggregateReport as any).mockReset();
  (callProcessingJourneyService.getAggregateReport as any).mockResolvedValue({
    success: true,
    data: ENVELOPE,
  });
});

function openModal() {
  render(<JourneyReportModal journeyId="j-1" />);
  fireEvent.click(screen.getByText(/View Report/));
}

describe('JourneyReportModal', () => {
  it('renders the schema title (not the hard-coded "Call Processing")', async () => {
    openModal();
    expect(await screen.findByText(/Demand Forecasting Report/)).toBeTruthy();
    expect(screen.queryByText(/Call Processing Report/)).toBeNull();
  });

  it('renders the journey name alongside the report title', async () => {
    render(<JourneyReportModal journeyId="j-1" journeyName="Weekly SKU Replenishment" />);
    fireEvent.click(screen.getByText(/View Report/));
    expect(await screen.findByText(/Weekly SKU Replenishment/)).toBeTruthy();
  });

  it('renders all summary KPI cards with their values', async () => {
    openModal();
    expect(await screen.findByText('MAPE')).toBeTruthy();
    expect(screen.getByText('12.5%')).toBeTruthy();
    expect(screen.getByText('Stockout Risk')).toBeTruthy();
    expect(screen.getByText('8.0%')).toBeTruthy();
  });

  it('renders each section by kind: kpi_grid', async () => {
    openModal();
    expect(await screen.findByText('Forecast Volumes')).toBeTruthy();
    expect(screen.getByText('Forecast Units')).toBeTruthy();
    expect(screen.getByText('12,345')).toBeTruthy();
  });

  it('renders alerts_list with grouped chips', async () => {
    openModal();
    expect(await screen.findByText('Demand Alerts')).toBeTruthy();
    expect(screen.getByText('Demand Spike')).toBeTruthy();
    expect(screen.getByText('sudden uptick on SKU-A')).toBeTruthy();
  });

  it('renders timeline events with state transitions', async () => {
    openModal();
    expect(await screen.findByText('Run Timeline')).toBeTruthy();
    expect(screen.getByText('pending')).toBeTruthy();
    expect(screen.getByText('in_progress')).toBeTruthy();
  });

  it('renders step_breakdown table rows', async () => {
    openModal();
    expect(await screen.findByText('Step Breakdown')).toBeTruthy();
    expect(screen.getByText('Step 1')).toBeTruthy();
    expect(screen.getByText('do_thing')).toBeTruthy();
  });

  it('shows total_jobs footer', async () => {
    openModal();
    expect(await screen.findByText(/Based on 3 jobs/)).toBeTruthy();
  });
});
