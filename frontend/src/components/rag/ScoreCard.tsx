import React from 'react';
import { Icon } from '@/components/ds/Icon';
import { StatusPill } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import type { HybridSearchResponse } from '@/services/ontoApi';

interface ScoreCardProps {
  results: HybridSearchResponse | null;
}

const DIMENSIONS = [
  { key: 'schema', label: 'Schema', contentTypes: ['onto_schema', 'schema', 'fdw_table'] },
  { key: 'policy', label: 'Policy', contentTypes: ['onto_policy', 'policy'] },
  { key: 'workflow', label: 'Workflow', contentTypes: ['onto_workflow', 'workflow'] },
  { key: 'integration', label: 'Integration', contentTypes: ['onto_integration', 'integration'] },
];

/**
 * Retrieval quality of the last query: a verdict, then the six checks it is
 * made of, written as one quiet strip instead of a score tile.
 */
const ScoreCard: React.FC<ScoreCardProps> = ({ results }) => {
  if (!results) {
    return (
      <p className="text-sm text-muted-foreground">Run a query to score what it retrieves.</p>
    );
  }

  const categories = Object.keys(results.by_category || {});
  const dimensionScores = DIMENSIONS.map((dim) => {
    const found = dim.contentTypes.some((ct) => categories.includes(ct));
    return { ...dim, found, score: found ? 1 : 0 };
  });

  const totalScore = dimensionScores.reduce((sum, d) => sum + d.score, 0);
  const maxScore = DIMENSIONS.length;
  const hasGraph = results.graph_hits > 0;
  const hasVersion = results.results.some((r) => !!r.metadata?.version);

  const fullScore = totalScore + (hasGraph ? 1 : 0) + (hasVersion ? 1 : 0);
  const fullMax = maxScore + 2;
  const passed = fullScore >= 5;

  const checks = [
    ...dimensionScores.map(d => ({ key: d.key, label: d.label, found: d.found })),
    { key: 'graph', label: 'Cross-system links', found: hasGraph },
    { key: 'version', label: 'Version info', found: hasVersion },
  ];

  return (
    <section aria-label="Retrieval quality" className="flex flex-col gap-x-8 gap-y-3 rounded-xl border border-border bg-card px-4 py-3.5 shadow-xs sm:px-5 md:flex-row md:items-center">
      <div className="shrink-0">
        <div className="flex items-center gap-3">
          <h3 className="text-md font-medium text-foreground">Retrieval quality</h3>
          <StatusPill status={passed ? 'pass' : 'warning'}>{passed ? 'Ready for planning' : 'Below threshold'}</StatusPill>
        </div>
        <p className="mt-0.5 text-sm text-muted-foreground">
          <span className="num text-foreground">{fullScore}</span> of <span className="num">{fullMax}</span> kinds of context were retrieved. Five are needed.
        </p>
      </div>
      <ul className="flex min-w-0 flex-1 flex-wrap items-center gap-x-5 gap-y-1.5 md:justify-end">
        {checks.map((c, i) => (
          <li key={c.key} className="rise inline-flex items-center gap-1.5 text-sm" style={{ ['--i' as any]: i }}>
            <Icon name={c.found ? 'check' : 'minus'} className={cn('h-3.5 w-3.5', c.found ? 'text-success' : 'text-subtle-foreground')} />
            <span className={c.found ? 'text-foreground' : 'text-muted-foreground'}>{c.label}</span>
            <span className="sr-only">{c.found ? 'retrieved' : 'missing'}</span>
          </li>
        ))}
      </ul>
    </section>
  );
};

export default ScoreCard;
