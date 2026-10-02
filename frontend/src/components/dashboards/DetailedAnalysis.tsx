import { useState, useEffect } from 'react';
import { fetchAnalysisReport } from '@/services/dataService';
import DashboardCard from '@/components/DashboardCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function DetailedAnalysis() {
  const [report, setReport] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadReport = async () => {
      try {
        setLoading(true);
        setError(null);
        const reportData = await fetchAnalysisReport();
        setReport(reportData);
      } catch (err) {
        console.error('Failed to load analysis report:', err);
        setError('Failed to load analysis report. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadReport();
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="text-red-500 p-4">{error}</div>;

  return (
    <div className="space-y-6">
      <DashboardCard 
        title="Detailed Analysis Report"
        subtitle="A detailed breakdown of all TMF mappings."
      >
        <div className="max-h-96 overflow-y-auto pr-4 custom-scrollbar">
          <div className="prose dark:prose-invert max-w-none">
            <ReactMarkdown
              children={report}
              remarkPlugins={[remarkGfm]}
            />
          </div>
        </div>
      </DashboardCard>

      {/* Key Metrics Summary */}
      <div className="grid grid-cols-3 gap-6">
        <DashboardCard title="Mapping Quality">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">High Confidence (90%+)</span>
              <span className="text-green-600 dark:text-green-400 font-semibold">4 components</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Medium Confidence (80%+)</span>
              <span className="text-yellow-600 dark:text-yellow-400 font-semibold">1 component</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-green-500 h-2 rounded-full" style={{ width: '80%' }}></div>
            </div>
          </div>
        </DashboardCard>

        <DashboardCard title="API Coverage">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">TMF632 Party</span>
              <span className="text-blue-600 dark:text-blue-400 font-semibold">Complete</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">TMF629 Customer</span>
              <span className="text-blue-600 dark:text-blue-400 font-semibold">Complete</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">TMF670 Bill Mgmt</span>
              <span className="text-green-600 dark:text-green-400 font-semibold">Mapped</span>
            </div>
          </div>
        </DashboardCard>

        <DashboardCard title="Implementation Status">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Ready for Migration</span>
              <span className="text-green-600 dark:text-green-400 font-semibold">90%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Manual Review Needed</span>
              <span className="text-yellow-600 dark:text-yellow-400 font-semibold">10%</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-gradient-to-r from-green-500 to-blue-500 h-2 rounded-full" style={{ width: '90%' }}></div>
            </div>
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}
