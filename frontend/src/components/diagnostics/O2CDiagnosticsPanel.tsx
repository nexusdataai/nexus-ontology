import { useState, useCallback } from 'react';
import { apiClient } from '@/services/apiClient';
import { SolutionDiagnosticsView, type SolutionDiagReport } from './SolutionDiagnosticsView';

/** Order-to-Cash diagnostics: POST /api/v1/diagnostics/o2c. The report layout is shared by all solutions. */
export default function O2CDiagnosticsPanel() {
  const [report, setReport] = useState<SolutionDiagReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runDiagnostics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.post<SolutionDiagReport>('/api/v1/diagnostics/o2c', {});
      setReport(data);
    } catch (e: any) {
      setError(e.message || 'Diagnostics failed');
    } finally {
      setLoading(false);
    }
  }, []);

  return <SolutionDiagnosticsView solution="Order-to-Cash" report={report} loading={loading} error={error} onRun={runDiagnostics} />;
}
