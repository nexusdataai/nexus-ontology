import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Brain } from 'lucide-react';
import Layout from '@/components/Layout';
import QueryPanel from '@/components/rag/QueryPanel';
import RetrievalBundle from '@/components/rag/RetrievalBundle';
import GraphViewer from '@/components/rag/GraphViewer';
import ScoreCard from '@/components/rag/ScoreCard';
import BundleViewer from '@/components/rag/BundleViewer';
import TestRunner from '@/components/rag/TestRunner';
import BuildIndexPanel from '@/components/rag/BuildIndexPanel';
import OntoDataManager from '@/components/rag/OntoDataManager';
import { ontoApi, type HybridSearchResponse } from '@/services/ontoApi';

const RagPlaygroundPage: React.FC = () => {
  const navigate = useNavigate();
  const [results, setResults] = useState<HybridSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastQuery, setLastQuery] = useState('');
  const [indexKey, setIndexKey] = useState(0);

  const handleSearch = async (query: string, contentType?: string, graphHops?: number) => {
    setLoading(true);
    setLastQuery(query);
    try {
      const response = await ontoApi.hybridSearch({
        query,
        content_type: contentType,
        limit: 15,
        graph_hops: graphHops ?? 2,
      });
      setResults(response);
    } catch (e) {
      console.error('Search failed:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="p-6 space-y-4 max-w-[1400px] mx-auto">
        <QueryPanel onSearch={handleSearch} loading={loading} />

        {lastQuery && (
          <div className="text-sm text-muted-foreground">
            Query: <span className="font-medium text-foreground">{lastQuery}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <Tabs defaultValue="bundle">
              <TabsList>
                <TabsTrigger value="bundle">Retrieval Bundle</TabsTrigger>
                <TabsTrigger value="graph">Graph View</TabsTrigger>
                <TabsTrigger value="tests">Test Suite</TabsTrigger>
                <TabsTrigger value="data">Knowledge Data</TabsTrigger>
              </TabsList>
              <TabsContent value="bundle" className="mt-3">
                <RetrievalBundle results={results} />
              </TabsContent>
              <TabsContent value="graph" className="mt-3">
                <GraphViewer results={results} />
              </TabsContent>
              <TabsContent value="tests" className="mt-3">
                <TestRunner />
              </TabsContent>
              <TabsContent value="data" className="mt-3">
                <OntoDataManager />
              </TabsContent>
            </Tabs>
          </div>

          <div className="space-y-4">
            <BuildIndexPanel onComplete={() => setIndexKey(k => k + 1)} />
            <ScoreCard results={results} />
            <BundleViewer key={indexKey} />
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default RagPlaygroundPage;
