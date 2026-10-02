import { useState } from 'react';
import Layout from '@/components/Layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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

export default function DiagnosticsPage() {
  const [tab, setTab] = useState('o2c');

  return (
    <Layout>
      <Tabs value={tab} onValueChange={setTab} className="flex flex-col h-full">
        <div className="border-b border-border px-6 pt-3">
          <TabsList className="bg-transparent gap-1 h-auto p-0">
            {[
              { value: 'o2c', label: 'O2C' },
              { value: 'df', label: 'Demand Forecasting' },
              { value: 'io', label: 'Inventory' },
              { value: 'pa', label: 'Procurement' },
              { value: 'pq', label: 'Production' },
              { value: 'scr', label: 'Risk Radar' },
              { value: 'c360', label: 'Customer 360' },
              { value: 'esg', label: 'ESG' },
              { value: 'cpq', label: 'CPQ' },
              { value: 'sim', label: 'Simulators' },
              { value: 'dashboards', label: 'Dashboards' },
              { value: 'virtual-data', label: 'Virtual Data' },
              { value: 'automation', label: 'Automation' },
              { value: 'react-tools', label: 'ReAct Tools' },
            ].map(t => (
              <TabsTrigger key={t.value} value={t.value}
                className="data-[state=active]:bg-blue-600/20 data-[state=active]:text-blue-300 gap-1.5 text-xs px-3 py-1.5 rounded-t-md rounded-b-none border-b-2 border-transparent data-[state=active]:border-blue-400">
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        <div className="flex-1 overflow-auto">
          <TabsContent value="o2c" className="mt-0 h-full">
            <O2CDiagnosticsPanel />
          </TabsContent>
          <TabsContent value="df" className="mt-0 h-full">
            <DFDiagnosticsPanel />
          </TabsContent>
          <TabsContent value="io" className="mt-0 h-full">
            <IODiagnosticsPanel />
          </TabsContent>
          <TabsContent value="pa" className="mt-0 h-full">
            <PADiagnosticsPanel />
          </TabsContent>
          <TabsContent value="pq" className="mt-0 h-full">
            <PQDiagnosticsPanel />
          </TabsContent>
          <TabsContent value="scr" className="mt-0 h-full">
            <SCRDiagnosticsPanel />
          </TabsContent>
          <TabsContent value="c360" className="mt-0 h-full">
            <C360DiagnosticsPanel />
          </TabsContent>
          <TabsContent value="esg" className="mt-0 h-full">
            <ESGDiagnosticsPanel />
          </TabsContent>
          <TabsContent value="cpq" className="mt-0 h-full">
            <CPQDiagnosticsPanel />
          </TabsContent>
          <TabsContent value="sim" className="mt-0 h-full">
            <SimulatorDiagnosticsPanel />
          </TabsContent>
          <TabsContent value="dashboards" className="mt-0 h-full">
            <DashboardDiagnosticsPanel />
          </TabsContent>
          <TabsContent value="virtual-data" className="mt-0 h-full">
            <VirtualDataDiagnosticsPanel />
          </TabsContent>
          <TabsContent value="automation" className="mt-0 h-full">
            <AutomationDiagnosticsPanel />
          </TabsContent>
          <TabsContent value="react-tools" className="mt-0 h-full">
            <ReactToolsDiagnosticsPanel />
          </TabsContent>
        </div>
      </Tabs>
    </Layout>
  );
}
