import Layout from '@/components/Layout';
import { Tabs, TabsContent } from '@/components/ui/tabs';
import { PageTabsBar, useUrlTab, type TabSection } from '@/components/ds/PageTabs';
import O2CDiagnosticsPanel from '@/components/diagnostics/O2CDiagnosticsPanel';
import DFDiagnosticsPanel from '@/components/diagnostics/DFDiagnosticsPanel';
import IODiagnosticsPanel from '@/components/diagnostics/IODiagnosticsPanel';
import PADiagnosticsPanel from '@/components/diagnostics/PADiagnosticsPanel';
import PQDiagnosticsPanel from '@/components/diagnostics/PQDiagnosticsPanel';
import SCRDiagnosticsPanel from '@/components/diagnostics/SCRDiagnosticsPanel';
import C360DiagnosticsPanel from '@/components/diagnostics/C360DiagnosticsPanel';
import ESGDiagnosticsPanel from '@/components/diagnostics/ESGDiagnosticsPanel';
import CPQDiagnosticsPanel from '@/components/diagnostics/CPQDiagnosticsPanel';
import SimulatorDiagnosticsPanel from '@/components/diagnostics/SimulatorDiagnosticsPanel';
import DashboardDiagnosticsPanel from '@/components/diagnostics/DashboardDiagnosticsPanel';
import VirtualDataDiagnosticsPanel from '@/components/diagnostics/VirtualDataDiagnosticsPanel';
import AutomationDiagnosticsPanel from '@/components/diagnostics/AutomationDiagnosticsPanel';
import ReactToolsDiagnosticsPanel from '@/components/diagnostics/ReactToolsDiagnosticsPanel';

/** Fourteen checks grouped in two sections: per solution, and per platform subsystem. */
const SECTIONS: TabSection[] = [
  { label: 'Solutions', icon: 'apps', items: [
    { value: 'o2c', label: 'Order-to-Cash' },
    { value: 'df', label: 'Demand forecasting' },
    { value: 'io', label: 'Inventory' },
    { value: 'pa', label: 'Procurement' },
    { value: 'pq', label: 'Production' },
    { value: 'scr', label: 'Risk radar' },
    { value: 'c360', label: 'Customer 360' },
    { value: 'esg', label: 'ESG' },
    { value: 'cpq', label: 'CPQ' },
  ] },
  { label: 'Platform', icon: 'layers', items: [
    { value: 'sim', label: 'Simulators' },
    { value: 'virtual-data', label: 'Virtual data' },
    { value: 'dashboards', label: 'Dashboards' },
    { value: 'automation', label: 'Automation' },
    { value: 'react-tools', label: 'ReAct tools' },
  ] },
];

export default function DiagnosticsPage() {
  const [tab, setTab] = useUrlTab('o2c');

  return (
    <Layout>
      <Tabs value={tab} onValueChange={setTab}>
        <PageTabsBar
          title="Diagnostics"
          description="Run data and health checks for each solution and each platform subsystem."
          sections={SECTIONS}
          value={tab}
          onChange={setTab}
        />
        <TabsContent value="o2c" className="mt-0"><O2CDiagnosticsPanel /></TabsContent>
        <TabsContent value="df" className="mt-0"><DFDiagnosticsPanel /></TabsContent>
        <TabsContent value="io" className="mt-0"><IODiagnosticsPanel /></TabsContent>
        <TabsContent value="pa" className="mt-0"><PADiagnosticsPanel /></TabsContent>
        <TabsContent value="pq" className="mt-0"><PQDiagnosticsPanel /></TabsContent>
        <TabsContent value="scr" className="mt-0"><SCRDiagnosticsPanel /></TabsContent>
        <TabsContent value="c360" className="mt-0"><C360DiagnosticsPanel /></TabsContent>
        <TabsContent value="esg" className="mt-0"><ESGDiagnosticsPanel /></TabsContent>
        <TabsContent value="cpq" className="mt-0"><CPQDiagnosticsPanel /></TabsContent>
        <TabsContent value="sim" className="mt-0"><SimulatorDiagnosticsPanel /></TabsContent>
        <TabsContent value="dashboards" className="mt-0"><DashboardDiagnosticsPanel /></TabsContent>
        <TabsContent value="virtual-data" className="mt-0"><VirtualDataDiagnosticsPanel /></TabsContent>
        <TabsContent value="automation" className="mt-0"><AutomationDiagnosticsPanel /></TabsContent>
        <TabsContent value="react-tools" className="mt-0"><ReactToolsDiagnosticsPanel /></TabsContent>
      </Tabs>
    </Layout>
  );
}
