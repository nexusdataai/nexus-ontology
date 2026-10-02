import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Database, FileText, GitBranch, Link2, ChevronDown, ChevronRight } from 'lucide-react';
import type { HybridSearchResponse } from '@/services/ontoApi';

interface RetrievalBundleProps {
  results: HybridSearchResponse | null;
}

const CATEGORY_ICONS: Record<string, any> = {
  onto_schema: Database,
  schema: Database,
  onto_policy: FileText,
  policy: FileText,
  onto_workflow: GitBranch,
  workflow: GitBranch,
  onto_integration: Link2,
  integration: Link2,
};

const CATEGORY_COLORS: Record<string, string> = {
  onto_schema: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  schema: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  onto_policy: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  policy: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  onto_workflow: 'bg-green-500/10 text-green-400 border-green-500/30',
  workflow: 'bg-green-500/10 text-green-400 border-green-500/30',
  onto_integration: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  integration: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
};

const RetrievalBundle: React.FC<RetrievalBundleProps> = ({ results }) => {
  const [expanded, setExpanded] = React.useState<Record<string, boolean>>({});

  if (!results) {
    return (
      <div className="text-center text-muted-foreground py-12">
        Run a query to see the retrieval bundle
      </div>
    );
  }

  const categories = Object.entries(results.by_category || {});

  return (
    <div className="space-y-3">
      <div className="flex gap-2 text-sm text-muted-foreground">
        <Badge variant="secondary">{results.total} results</Badge>
        <Badge variant="outline">{results.vector_hits} vector</Badge>
        <Badge variant="outline">{results.graph_hits} graph</Badge>
      </div>

      <ScrollArea className="h-[500px]">
        <div className="space-y-3 pr-3">
          {categories.map(([category, docs]) => {
            const Icon = CATEGORY_ICONS[category] || Database;
            const colorClass = CATEGORY_COLORS[category] || '';
            const isExpanded = expanded[category] !== false;

            return (
              <Card key={category} className="border-border/50">
                <CardHeader
                  className="py-2 px-4 cursor-pointer"
                  onClick={() => setExpanded(prev => ({ ...prev, [category]: !isExpanded }))}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      <Icon className="h-4 w-4" />
                      <span className="font-medium capitalize">{category.replace('onto_', '')}</span>
                      <Badge variant="secondary" className="text-xs">{(docs as any[]).length}</Badge>
                    </div>
                  </div>
                </CardHeader>
                {isExpanded && (
                  <CardContent className="pt-0 px-4 pb-3 space-y-2">
                    {(docs as any[]).map((doc, i) => (
                      <div key={i} className={`rounded-md border p-3 text-sm ${colorClass}`}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono text-xs opacity-70">{doc.source_id}</span>
                          <div className="flex gap-1">
                            <Badge variant="outline" className="text-xs">
                              {(doc.similarity * 100).toFixed(0)}%
                            </Badge>
                            {doc.graph_expanded && (
                              <Badge variant="outline" className="text-xs border-green-500/50 text-green-400">
                                graph
                              </Badge>
                            )}
                          </div>
                        </div>
                        <p className="text-xs whitespace-pre-wrap opacity-90 line-clamp-4">
                          {doc.content}
                        </p>
                      </div>
                    ))}
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
};

export default RetrievalBundle;
