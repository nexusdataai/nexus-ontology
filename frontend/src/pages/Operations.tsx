import React from 'react';
import Layout from '@/components/Layout';
import { PageTabsBar, useUrlTab, type TabSection } from '@/components/ds/PageTabs';
import { AiHealthMonitoringPanel } from '@/components/operations/AiHealthMonitoringPanel';
import { DiagnosticsAuditPanel } from '@/components/operations/DiagnosticsAuditPanel';
import { EndUsageSection } from '@/components/operations/EndUsageSection';
import { DataProtectionSection } from '@/components/operations/DataProtectionSection';
import { CostSection } from '@/components/operations/CostSection';
import { BatchSchedulesPanel } from '@/components/journeys/BatchSchedulesPanel';
import { TestReportsPanel } from '@/components/operations/TestReportsPanel';

/** Tabs grouped into sections. Item values are the original ?tab= values. */
const SECTIONS: TabSection[] = [
  { label: 'Monitoring', icon: 'activity', items: [{ value: 'monitoring', label: 'Monitoring' }] },
  { label: 'Jobs', icon: 'calendar', items: [{ value: 'jobs', label: 'Jobs' }] },
  { label: 'Audit logs', icon: 'history', items: [{ value: 'audit', label: 'Audit logs' }] },
  { label: 'Usage and cost', icon: 'coins', items: [
    { value: 'end-usage', label: 'End usage' },
    { value: 'data-protection', label: 'Data protection' },
    { value: 'cost', label: 'Cost' },
  ] },
  { label: 'Test reports', icon: 'flask', items: [{ value: 'test-reports', label: 'Test reports' }] },
];

const Operations: React.FC = () => {
  const [activeTab, setActiveTab] = useUrlTab('monitoring');

  const renderContent = () => {
    switch (activeTab) {
      case 'jobs':
        return <BatchSchedulesPanel />;
      case 'audit':
        return <DiagnosticsAuditPanel />;
      case 'end-usage':
        return <EndUsageSection />;
      case 'data-protection':
        return <DataProtectionSection />;
      case 'cost':
        return <CostSection />;
      case 'test-reports':
        return <TestReportsPanel />;
      case 'monitoring':
      default:
        return <AiHealthMonitoringPanel />;
    }
  };

  return (
    <Layout>
      <PageTabsBar
        title="Health"
        description="Platform monitoring, scheduled jobs, audit history, usage and test reports."
        sections={SECTIONS}
        value={activeTab}
        onChange={setActiveTab}
      />
      <div key={activeTab} className="page animate-fade-in">
        {renderContent()}
      </div>
    </Layout>
  );
};

export default Operations;
