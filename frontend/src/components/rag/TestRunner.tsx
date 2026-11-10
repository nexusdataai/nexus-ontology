import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Icon } from '@/components/ds/Icon';
import { Meter, MetricStrip, StatusPill, TableShell } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { ontoApi } from '@/services/ontoApi';
import { typeLabel } from './ragMeta';

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

/** What every question is expected to bring back. A test passes with four of five. */
const EXPECTED = [
  { key: 'schema', label: 'Schema' },
  { key: 'policy', label: 'Policy' },
  { key: 'workflow', label: 'Workflow' },
  { key: 'integration', label: 'Integration' },
  { key: 'graph', label: 'Graph links' },
];
const PASS_SCORE = 4;

const found = (r: TestResult, key: string) => (key === 'graph' ? r.graphHits > 0 : r.categories.some(c => c.includes(key)));

/**
 * Retrieval test suite: runs a fixed set of questions through hybrid search
 * and reports, per question, which kinds of context came back.
 */
const TestRunner: React.FC = () => {
  const [results, setResults] = useState<TestResult[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  // Rows the user opened or closed by hand. Failed rows are open by default.
  const [toggled, setToggled] = useState<Record<number, boolean>>({});

  const runTests = async () => {
    setRunning(true);
    setResults([]);
    setProgress(0);
    setToggled({});

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

  const total = TEST_SCENARIOS.length;
  const avgScore = results.length > 0
    ? (results.reduce((s, r) => s + r.score, 0) / results.length).toFixed(1)
    : '0';
  const passed = results.filter((r) => r.score >= PASS_SCORE).length;
  const failed = results.length - passed;
  const avgHits = results.length > 0 ? Math.round(results.reduce((s, r) => s + r.total, 0) / results.length) : 0;
  const done = !running && results.length > 0;

  const verdict = running
    ? `Running question ${Math.min(progress, total)} of ${total}.`
    : done
      ? failed === 0
        ? `All ${results.length} questions retrieved enough context.`
        : `${failed} of ${results.length} questions did not retrieve enough context.`
      : `${total} questions check that retrieval brings back schema, policy, workflow and integration context, with links from the graph.`;

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="text-md font-medium text-foreground">Retrieval test suite</h3>
            {running && <StatusPill status="running">Running</StatusPill>}
            {done && <StatusPill status={failed === 0 ? 'passed' : 'warning'}>{failed === 0 ? 'Passed' : 'Needs attention'}</StatusPill>}
          </div>
          <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground" aria-live="polite">{verdict}</p>
        </div>
        <Button onClick={runTests} disabled={running} className="shrink-0">
          <Icon name={running ? 'spinner' : 'play'} className={cn(running && 'animate-spin')} />
          {running ? `Running ${Math.min(progress, total)} of ${total}` : done ? 'Run all again' : 'Run all'}
        </Button>
      </div>

      {running && <Meter value={results.length} max={total} label="Test progress" className="mt-4" />}

      {results.length > 0 && (
        <MetricStrip
          className="mt-4"
          items={[
            { label: 'Passed', value: passed, hint: `of ${results.length} run`, tone: 'success' },
            { label: 'Failed', value: failed, hint: failed ? 'Fewer than 4 of 5 kinds of context' : 'None', tone: failed ? 'danger' : 'neutral' },
            { label: 'Average score', value: `${avgScore} / 5`, hint: 'Pass mark is 4' },
            { label: 'Average results', value: avgHits, hint: 'Documents per question' },
          ]}
        />
      )}

      <TableShell className="mt-4">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-10 text-right">#</TableHead>
              <TableHead>Question</TableHead>
              <TableHead className="w-32">Status</TableHead>
              <TableHead className="hidden w-20 text-right sm:table-cell">Score</TableHead>
              <TableHead className="hidden w-20 text-right md:table-cell">Results</TableHead>
              <TableHead className="w-10"><span className="sr-only">Details</span></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {TEST_SCENARIOS.map((question, i) => {
              const r = results[i];
              const isRunning = running && i === results.length;
              const ok = !!r && r.score >= PASS_SCORE;
              const open = !!r && (toggled[i] ?? !ok);
              return (
                <React.Fragment key={i}>
                  <TableRow
                    className={cn('hover:bg-surface-2/60', r && 'cursor-pointer', open && 'border-b-0')}
                    onClick={r ? () => setToggled(prev => ({ ...prev, [i]: !open })) : undefined}
                  >
                    <TableCell className="num text-right text-xs text-subtle-foreground">{i + 1}</TableCell>
                    <TableCell className={cn('text-sm', r || isRunning ? 'text-foreground' : 'text-muted-foreground')}>{question}</TableCell>
                    <TableCell>
                      {r ? <StatusPill status={ok ? 'passed' : 'failed'} />
                        : isRunning ? <StatusPill status="running" />
                        : <span className="text-xs text-subtle-foreground">{running ? 'Queued' : 'Not run'}</span>}
                    </TableCell>
                    <TableCell className="num hidden text-right text-sm sm:table-cell">{r ? `${r.score} / 5` : ''}</TableCell>
                    <TableCell className="num hidden text-right text-sm text-muted-foreground md:table-cell">{r ? r.total : ''}</TableCell>
                    <TableCell className="pl-0">
                      {r && (
                        <button
                          type="button"
                          aria-expanded={open}
                          aria-label={open ? 'Hide expected and actual' : 'Show expected and actual'}
                          onClick={(e) => { e.stopPropagation(); setToggled(prev => ({ ...prev, [i]: !open })); }}
                          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <Icon name="chevron-down" className={cn('h-3.5 w-3.5 transition-transform duration-200', open && 'rotate-180')} />
                        </button>
                      )}
                    </TableCell>
                  </TableRow>
                  {open && r && (
                    <TableRow className="bg-surface-2/40 hover:bg-surface-2/40">
                      <TableCell />
                      <TableCell colSpan={5} className="pb-4 pt-0">
                        <div className="grid animate-fade-in gap-x-10 gap-y-3 text-sm md:grid-cols-2">
                          <div>
                            <p className="text-xs text-muted-foreground">Expected</p>
                            <p className="mt-1 text-foreground">{EXPECTED.map(e => e.label).join(', ')}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Actual</p>
                            <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
                              {EXPECTED.map(e => {
                                const hit = found(r, e.key);
                                return (
                                  <li key={e.key} className="inline-flex items-center gap-1.5">
                                    <Icon name={hit ? 'check' : 'close'} className={cn('h-3 w-3', hit ? 'text-success' : 'text-destructive')} />
                                    <span className={hit ? 'text-foreground' : 'text-muted-foreground'}>{e.label}</span>
                                    <span className="sr-only">{hit ? 'retrieved' : 'missing'}</span>
                                  </li>
                                );
                              })}
                            </ul>
                            <p className="mt-1.5 text-xs text-muted-foreground">
                              {r.total === 0
                                ? 'The search returned nothing or failed.'
                                : <><span className="num">{r.vectorHits}</span> by vector search, <span className="num">{r.graphHits}</span> through the graph{r.categories.length > 0 && <>. Types found: {r.categories.map(c => typeLabel(c)).join(', ')}</>}.</>}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              );
            })}
          </TableBody>
        </Table>
      </TableShell>
    </div>
  );
};

export default TestRunner;
