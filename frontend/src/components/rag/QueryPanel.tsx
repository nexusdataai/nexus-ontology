import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Search, Loader2, Sliders } from 'lucide-react';

interface QueryPanelProps {
  onSearch: (query: string, contentType?: string, graphHops?: number) => void;
  loading: boolean;
}

const CONTENT_TYPES = [
  { value: '', label: 'All Categories' },
  { value: 'onto_schema', label: 'Schema' },
  { value: 'onto_policy', label: 'Policy' },
  { value: 'onto_workflow', label: 'Workflow' },
  { value: 'onto_integration', label: 'Integration' },
];

const QueryPanel: React.FC<QueryPanelProps> = ({ onSearch, loading }) => {
  const [query, setQuery] = useState('');
  const [contentType, setContentType] = useState('');
  const [graphHops, setGraphHops] = useState(2);
  const [showFilters, setShowFilters] = useState(false);

  const handleSearch = () => {
    if (query.trim()) {
      onSearch(query.trim(), contentType || undefined, graphHops);
    }
  };

  const sampleQueries = [
    'What is Material_Master and how is it mapped to a data source?',
    'What policies apply to inventory safety stock levels?',
    'How does the demand forecasting workflow use Salesforce and SAP data?',
    'What entities are needed for the Order-to-Cash use case?',
    'Which system is the source of truth for customer credit limit?',
    'What happens when AR_Invoice is disputed?',
  ];

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Search className="h-5 w-5" />
          Semantic RAG Query
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Input
            placeholder="Ask about schemas, policies, workflows, integrations..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="flex-1"
          />
          <Button onClick={handleSearch} disabled={loading || !query.trim()}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          </Button>
          <Button variant="outline" size="icon" onClick={() => setShowFilters(!showFilters)}>
            <Sliders className="h-4 w-4" />
          </Button>
        </div>

        {showFilters && (
          <div className="flex gap-3 items-center text-sm">
            <span className="text-muted-foreground">Category:</span>
            <div className="flex gap-1 flex-wrap">
              {CONTENT_TYPES.map((ct) => (
                <Badge
                  key={ct.value}
                  variant={contentType === ct.value ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => setContentType(ct.value)}
                >
                  {ct.label}
                </Badge>
              ))}
            </div>
            <span className="text-muted-foreground ml-2">Graph hops:</span>
            <select
              value={graphHops}
              onChange={(e) => setGraphHops(Number(e.target.value))}
              className="bg-background border rounded px-2 py-1 text-sm"
            >
              {[0, 1, 2, 3].map((h) => (
                <option key={h} value={h}>{h}</option>
              ))}
            </select>
          </div>
        )}

        <div className="space-y-1">
          <span className="text-xs text-muted-foreground">Try:</span>
          <div className="flex flex-wrap gap-1">
            {sampleQueries.map((sq, i) => (
              <Badge
                key={i}
                variant="outline"
                className="cursor-pointer text-xs hover:bg-accent"
                onClick={() => { setQuery(sq); onSearch(sq, contentType || undefined, graphHops); }}
              >
                {sq.length > 50 ? sq.slice(0, 50) + '...' : sq}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default QueryPanel;
