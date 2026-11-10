import { useState } from 'react';
import Layout from '@/components/Layout';
import { PageTabsBar, useUrlTab, type TabSection } from '@/components/ds/PageTabs';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ontoApi, type HybridSearchResponse } from '@/services/ontoApi';
import CopilotWorkspace from '@/components/reasoning/CopilotWorkspace';
import AgentToolsCatalogue from '@/components/reasoning/AgentToolsCatalogue';
import QueryPanel from '@/components/rag/QueryPanel';
import RetrievalBundle from '@/components/rag/RetrievalBundle';
import GraphViewer from '@/components/rag/GraphViewer';
import ScoreCard from '@/components/rag/ScoreCard';
import TestRunner from '@/components/rag/TestRunner';
import ToolBuilder from '@/components/tool-builder/ToolBuilder';
import ToolsRegistryBrowser from '@/components/registry-browser/ToolsRegistryBrowser';

/**
 * Planning playground: ask a retrieval question, then read what came back as
 * a ranked bundle or a graph, or run the fixed test suite.
 */
function PlanningPlaygroundTab() {
  const [results, setResults] = useState<HybridSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastQuery, setLastQuery] = useState('');
  // Local view state: the last failure and the arguments to retry it with.
  const [error, setError] = useState<string | null>(null);
  const [lastArgs, setLastArgs] = useState<{ contentType?: string; graphHops?: number }>({});
  const [view, setView] = useState('bundle');

  const handleSearch = async (query: string, contentType?: string, graphHops?: number) => {
    setLoading(true);
    setLastQuery(query);
    setLastArgs({ contentType, graphHops });
    setError(null);
    try {
      const response = await ontoApi.hybridSearch({ query, content_type: contentType, limit: 15, graph_hops: graphHops ?? 2 });
      setResults(response);
    } catch (e: any) {
      console.error('Search failed:', e);
      setError(e?.message || 'The search service did not respond.');
    }
    finally { setLoading(false); }
  };

  const retry = () => { if (lastQuery) handleSearch(lastQuery, lastArgs.contentType, lastArgs.graphHops); };

  return (
    <div className="page pb-24">
      <div className="mx-auto max-w-[920px]">
        <h2 className="text-xl font-medium tracking-tight text-foreground">Planning playground</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask what the agent would ask. See which schemas, policies, workflows and integrations retrieval brings back, and whether that is enough to plan with.
        </p>
        <div className="mt-5">
          <QueryPanel onSearch={handleSearch} loading={loading} />
        </div>
      </div>

      <Tabs value={view} onValueChange={setView} className="mt-8">
        <TabsList variant="line">
          <TabsTrigger value="bundle">
            Retrieval bundle
            {results && <span className="num text-xs font-normal text-muted-foreground">{results.total}</span>}
          </TabsTrigger>
          <TabsTrigger value="graph">Graph view</TabsTrigger>
          <TabsTrigger value="tests">Test suite</TabsTrigger>
        </TabsList>

        {view !== 'tests' && lastQuery && (
          <div className="mt-5 space-y-4">
            <p className="text-sm text-muted-foreground">
              {loading ? 'Searching for' : 'Results for'} <span className="font-medium text-foreground">{lastQuery}</span>
            </p>
            {results && !error && <ScoreCard results={results} />}
          </div>
        )}

        <TabsContent value="bundle" className="mt-5">
          <RetrievalBundle results={results} loading={loading} error={error} onRetry={retry} />
        </TabsContent>
        <TabsContent value="graph" className="mt-5">
          <GraphViewer results={error ? null : results} loading={loading} />
        </TabsContent>
        <TabsContent value="tests" className="mt-6">
          <TestRunner />
        </TabsContent>
      </Tabs>
    </div>
  );
}

/** Tabs grouped into sections. Item values are the original ?tab= values. */
const RP_SECTIONS: TabSection[] = [
  { label: 'Copilot', icon: 'chat-bot', items: [{ value: 'copilot', label: 'AI Copilot' }] },
  { label: 'Playground', icon: 'target', items: [{ value: 'playground', label: 'Planning playground' }] },
  { label: 'Tools', icon: 'wrench', items: [
    { value: 'tools', label: 'Catalogue' },
    { value: 'tools-reg', label: 'Registry' },
    { value: 'builder', label: 'Builder' },
  ] },
];

export default function ReasoningPage() {
  const [tab, setTab] = useUrlTab('copilot');

  return (
    <Layout>
      <Tabs value={tab} onValueChange={setTab}>
        <PageTabsBar
          title="Reasoning"
          description="Ask the agent, inspect how it reasoned, test retrieval quality, and manage the tools it can call."
          sections={RP_SECTIONS}
          value={tab}
          onChange={setTab}
        />
        <TabsContent value="copilot" className="mt-0">
          <CopilotWorkspace />
        </TabsContent>
        <TabsContent value="playground" className="mt-0">
          <PlanningPlaygroundTab />
        </TabsContent>
        <TabsContent value="tools" className="mt-0">
          <AgentToolsCatalogue />
        </TabsContent>
        <TabsContent value="tools-reg" className="mt-0 h-pane-sub">
          <ToolsRegistryBrowser />
        </TabsContent>
        <TabsContent value="builder" className="mt-0 h-pane-sub">
          <ToolBuilder />
        </TabsContent>
      </Tabs>
    </Layout>
  );
}
