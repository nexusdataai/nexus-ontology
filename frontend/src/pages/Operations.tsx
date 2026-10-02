import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Activity, Users, Shield, DollarSign, CalendarClock, ScrollText, FlaskConical } from 'lucide-react';
import { AiHealthMonitoringPanel } from '@/components/operations/AiHealthMonitoringPanel';
import { DiagnosticsAuditPanel } from '@/components/operations/DiagnosticsAuditPanel';
import { EndUsageSection } from '@/components/operations/EndUsageSection';
import { DataProtectionSection } from '@/components/operations/DataProtectionSection';
import { CostSection } from '@/components/operations/CostSection';
import { BatchSchedulesPanel } from '@/components/journeys/BatchSchedulesPanel';
import { TestReportsPanel } from '@/components/operations/TestReportsPanel';

interface TabConfig {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const OPERATIONS_TABS: TabConfig[] = [
  { id: 'monitoring', label: 'Monitoring', icon: <Activity className="h-4 w-4" /> },
  { id: 'jobs', label: 'Jobs', icon: <CalendarClock className="h-4 w-4" /> },
  { id: 'audit', label: 'Audit Logs', icon: <ScrollText className="h-4 w-4" /> },
  { id: 'end-usage', label: 'End Usage', icon: <Users className="h-4 w-4" /> },
  { id: 'data-protection', label: 'Data Protection', icon: <Shield className="h-4 w-4" /> },
  { id: 'cost', label: 'Cost', icon: <DollarSign className="h-4 w-4" /> },
  { id: 'test-reports', label: 'Test Reports', icon: <FlaskConical className="h-4 w-4" /> },
];

// ============================================================================
// Component
// ============================================================================

const Operations: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'monitoring');

  // Sync tab state with URL
  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab && OPERATIONS_TABS.some(t => t.id === tab)) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    setSearchParams({ tab: tabId });
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'monitoring':
        return <AiHealthMonitoringPanel />;
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
      default:
        return <AiHealthMonitoringPanel />;
    }
  };

  return (
    <Layout>
      <div className="flex flex-col h-full">
        {/* Tab Navigation */}
        <div className="border-b border-border px-6 pt-3">
          <div className="flex gap-1 -mb-px overflow-x-auto">
            {OPERATIONS_TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={`
                  flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-t-md border-b-2 transition-colors whitespace-nowrap
                  ${activeTab === tab.id
                    ? 'bg-blue-600/20 text-blue-300 border-blue-400'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                  }
                `}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-auto p-6">
          {renderContent()}
        </div>
      </div>
    </Layout>
  );
};

export default Operations;
