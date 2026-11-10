import { useState, useCallback } from 'react';
import { apiClient } from '@/services/apiClient';
import { SolutionDiagnosticsView, type SolutionDiagReport } from './SolutionDiagnosticsView';

/** ESG and sustainability diagnostics: POST /api/v1/diagnostics/esg. The report layout is shared by all solutions. */
export default function ESGDiagnosticsPanel() {
  const [report, setReport] = useState<SolutionDiagReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runDiagnostics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.post<SolutionDiagReport>('/api/v1/diagnostics/esg', {});
      setReport(data);
    } catch (e: any) {
      setError(e.message || 'Diagnostics failed');
    } finally {
      setLoading(false);
    }
  }, []);

  return <SolutionDiagnosticsView solution="ESG and sustainability" report={report} loading={loading} error={error} onRun={runDiagnostics} />;
}
