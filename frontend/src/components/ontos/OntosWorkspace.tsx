/**
 * Ontos Workspace Container Component
 *
 * Provides a tabbed interface for FDW capabilities:
 * - Dashboard: Health status and summary metrics
 * - FDW Explorer: Browse foreign servers, tables, and columns
 * - Query Builder: Execute FDW queries
 */

import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import {
  LayoutDashboard,
  Database,
  Terminal,
} from 'lucide-react';
import { OntosDashboard } from './OntosDashboard';
import { FdwExplorer } from './FdwExplorer';
import { QueryBuilder } from './QueryBuilder';

// ============================================================================
// Types
// ============================================================================

export type OntosTabId =
  | 'dashboard'
  | 'fdw-explorer'
  | 'query-builder';

export interface OntosTabConfig {
  id: OntosTabId;
  label: string;
  icon: React.ReactNode;
}

export interface OntosWorkspaceProps {
  prefillStandard?: string;
  prefillResource?: string;
  fdwSource?: string;
}

// ============================================================================
// Constants
// ============================================================================

export const ONTOS_TAB_CONFIGS: OntosTabConfig[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: <LayoutDashboard className="h-4 w-4" />,
  },
  {
    id: 'fdw-explorer',
    label: 'FDW Explorer',
    icon: <Database className="h-4 w-4" />,
  },
  {
    id: 'query-builder',
    label: 'Query Builder',
    icon: <Terminal className="h-4 w-4" />,
  },
];

// ============================================================================
// Component
// ============================================================================

export function OntosWorkspace({ prefillStandard, prefillResource, fdwSource }: OntosWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<OntosTabId>('dashboard');

  return (
    <div className="h-full flex flex-col">
      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as OntosTabId)}
        className="flex-1 flex flex-col"
      >
        <div className="border-b border-border px-6 pt-3">
          <TabsList className="bg-transparent gap-1 h-auto p-0">
            {ONTOS_TAB_CONFIGS.map((tab) => (
              <TabsTrigger
                key={tab.id}
                value={tab.id}
                className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary gap-1.5 text-xs px-3 py-1.5 rounded-t-md rounded-b-none border-b-2 border-transparent data-[state=active]:border-primary/40"
                data-testid={`ontos-tab-${tab.id}`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <div className="flex-1 overflow-auto">
          <TabsContent value="dashboard" className="h-full m-0">
            <OntosDashboard fdwSource={fdwSource} />
          </TabsContent>

          <TabsContent value="fdw-explorer" className="h-full m-0">
            <FdwExplorer fdwSource={fdwSource} />
          </TabsContent>

          <TabsContent value="query-builder" className="h-full m-0">
            <QueryBuilder fdwSource={fdwSource} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

export default OntosWorkspace;
