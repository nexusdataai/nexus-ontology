import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Play, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { ontoApi } from '@/services/ontoApi';

const TEST_SCENARIOS = [
  'Which system is the source of truth for customer credit limit?',
  'What happens if I increase a customer\'s credit limit by more than 15%?',
  'If I deactivate a customer in Salesforce, what is impacted in Oracle ERP?',
  'Can customer credit limits be modified during financial close?',
  'What validations apply to the credit limit field?',
  'What workflows are triggered when a new enterprise customer is created?',
  'How is customer risk tier determined and where is it used?',
  'Who is authorized to override customer credit block?',
  'What steps are required to fully onboard a new B2B customer across systems?',
  'What is Material_Master and what GS1 identifiers does it use?',
  'What is the safety stock policy for Class A materials?',
  'How does the demand forecasting workflow generate SKU-level forecasts?',
  'What data flows from Salesforce to SAP for demand planning?',
  'How does the supplier risk scoring process work?',
  'What entities are needed for the Order-to-Cash use case?',
  'How does Account in Salesforce sync to AR_Customer?',
  'What is the inventory rebalancing workflow and when is it triggered?',
  'What SCOR Plan process entities exist in the supply chain?',
  'What mapping rules exist for Oracle ERP entities?',
];

interface TestResult {
  question: string;
  total: number;
  vectorHits: number;
  graphHits: number;
  categories: string[];
  score: number;
}

const TestRunner: React.FC = () => {
  const [results, setResults] = useState<TestResult[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);

  const runTests = async () => {
    setRunning(true);
    setResults([]);
    setProgress(0);

    const testResults: TestResult[] = [];

    for (let i = 0; i < TEST_SCENARIOS.length; i++) {
      const question = TEST_SCENARIOS[i];
      setProgress(i + 1);

      try {
        const response = await ontoApi.hybridSearch({ query: question, limit: 10, graph_hops: 2 });
        const categories = Object.keys(response.by_category || {});
        const dimensions = ['schema', 'policy', 'workflow', 'integration'];
        const score = dimensions.reduce((s, dim) => {
          return s + (categories.some((c) => c.includes(dim)) ? 1 : 0);
        }, 0) + (response.graph_hits > 0 ? 1 : 0);

        testResults.push({
          question,
          total: response.total,
          vectorHits: response.vector_hits,
          graphHits: response.graph_hits,
          categories,
          score,
        });
      } catch (e) {
        testResults.push({
          question,
          total: 0,
          vectorHits: 0,
          graphHits: 0,
          categories: [],
          score: 0,
        });
      }

      setResults([...testResults]);
    }

    setRunning(false);
  };

  const avgScore = results.length > 0
    ? (results.reduce((s, r) => s + r.score, 0) / results.length).toFixed(1)
    : '0';
  const passed = results.filter((r) => r.score >= 4).length;

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Black-Box Test Suite</CardTitle>
          <Button onClick={runTests} disabled={running} size="sm">
            {running ? (
              <><Loader2 className="h-3 w-3 animate-spin mr-1" /> {progress}/{TEST_SCENARIOS.length}</>
            ) : (
              <><Play className="h-3 w-3 mr-1" /> Run Tests</>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {results.length > 0 && (
          <div className="flex gap-3 mb-4 text-sm">
            <Badge variant="secondary">Avg: {avgScore}/5</Badge>
            <Badge variant={Number(avgScore) >= 4 ? 'default' : 'destructive'}>
              {passed}/{results.length} passed
            </Badge>
          </div>
        )}

        <ScrollArea className="h-[400px]">
          <div className="space-y-2 pr-3">
            {results.map((r, i) => (
              <div key={i} className="flex items-start gap-2 border rounded-md p-2 text-sm">
                {r.score >= 4 ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="text-xs truncate">{r.question}</div>
                  <div className="flex gap-1 mt-1">
                    <Badge variant="outline" className="text-xs">{r.score}/5</Badge>
                    <Badge variant="outline" className="text-xs">{r.total} hits</Badge>
                    {r.categories.map((c) => (
                      <Badge key={c} variant="secondary" className="text-xs capitalize">
                        {c.replace('onto_', '')}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            ))}

            {results.length === 0 && !running && (
              <div className="text-center text-muted-foreground py-8">
                Click "Run Tests" to execute the 10 black-box test scenarios
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export default TestRunner;
