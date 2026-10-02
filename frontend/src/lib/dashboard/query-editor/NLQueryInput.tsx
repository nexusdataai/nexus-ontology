import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Sparkles, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { nlQueryTranslate, type NLQueryResponse } from '../datasources/vdl-datasource';

interface Props {
  onQueryGenerated: (response: NLQueryResponse) => void;
  currentEntity?: string;
}

export function NLQueryInput({ onQueryGenerated, currentEntity }: Props) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastExplanation, setLastExplanation] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);

  const handleGenerate = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setLastExplanation(null);

    try {
      const response = await nlQueryTranslate({
        query: query.trim(),
        current_entity: currentEntity || undefined,
      });

      if (response.error) {
        setError(response.error);
        return;
      }

      setLastExplanation(response.explanation || null);
      onQueryGenerated(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate query');
    } finally {
      setLoading(false);
    }
  }, [query, currentEntity, onQueryGenerated]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleGenerate();
    }
  };

  return (
    <div className="border rounded-lg bg-gradient-to-r from-primary/5 to-transparent p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          <span className="text-xs font-medium">AI Query Builder</span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
      </div>

      {expanded && (
        <>
          <div className="flex gap-2">
            <textarea
              className="flex-1 min-h-[60px] max-h-[100px] rounded-md border bg-background px-3 py-2 text-xs resize-none placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe what data you want to see... e.g. &quot;Show top 10 vendors by risk score&quot; or &quot;Forecast accuracy by region as a bar chart&quot;"
              disabled={loading}
            />
            <Button
              size="sm"
              className="h-auto px-3 self-end"
              onClick={handleGenerate}
              disabled={loading || !query.trim()}
            >
              {loading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5 mr-1" />
                  Generate
                </>
              )}
            </Button>
          </div>

          {error && (
            <p className="text-[10px] text-destructive">{error}</p>
          )}

          {lastExplanation && !error && (
            <p className="text-[10px] text-muted-foreground bg-muted/30 rounded px-2 py-1">
              {lastExplanation}
            </p>
          )}
        </>
      )}
    </div>
  );
}
