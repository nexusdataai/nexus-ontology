import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, Target } from 'lucide-react';
import type { HybridSearchResponse } from '@/services/ontoApi';

interface ScoreCardProps {
  results: HybridSearchResponse | null;
}

const DIMENSIONS = [
  { key: 'schema', label: 'Object/Schema', contentTypes: ['onto_schema', 'schema', 'fdw_table'] },
  { key: 'policy', label: 'Policy', contentTypes: ['onto_policy', 'policy'] },
  { key: 'workflow', label: 'Workflow', contentTypes: ['onto_workflow', 'workflow'] },
  { key: 'integration', label: 'Integration', contentTypes: ['onto_integration', 'integration'] },
];

const ScoreCard: React.FC<ScoreCardProps> = ({ results }) => {
  if (!results) {
    return (
      <div className="text-center text-muted-foreground py-12">
        Run a query to see the retrieval scorecard
      </div>
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

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Target className="h-5 w-5" />
          Retrieval Quality Score
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-center">
          <div className="text-4xl font-bold">
            {fullScore}/{fullMax}
          </div>
          <div className="text-sm text-muted-foreground mt-1">
            {fullScore >= 5 ? 'Production Ready' : 'Needs Improvement'}
          </div>
          <Badge variant={fullScore >= 5 ? 'default' : 'destructive'} className="mt-2">
            {fullScore >= 5 ? 'PASS' : 'BELOW THRESHOLD'}
          </Badge>
        </div>

        <div className="space-y-2">
          {dimensionScores.map((dim) => (
            <div key={dim.key} className="flex items-center justify-between text-sm">
              <span>{dim.label}</span>
              {dim.found ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
            </div>
          ))}
          <div className="flex items-center justify-between text-sm">
            <span>Cross-System (Graph)</span>
            {hasGraph ? (
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            ) : (
              <XCircle className="h-4 w-4 text-red-500" />
            )}
          </div>
          <div className="flex items-center justify-between text-sm">
            <span>Version Awareness</span>
            {hasVersion ? (
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            ) : (
              <XCircle className="h-4 w-4 text-red-500" />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ScoreCard;
