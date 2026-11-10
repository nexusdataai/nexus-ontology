import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
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
    <div className="rounded-lg border border-border bg-surface-2/60">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Icon name="sparkles" className="h-3.5 w-3.5 text-primary dark:text-brand-hi" />
          Describe it in words
        </span>
        <Icon name={expanded ? 'chevron-up' : 'chevron-down'} className="h-3.5 w-3.5 text-muted-foreground" />
      </button>

      {expanded && (
        <div className="space-y-2 px-3 pb-3">
          <Textarea
            className="max-h-28 min-h-[64px] resize-none bg-card text-sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="For example: top 10 vendors by risk score, or forecast accuracy by region as a bar chart"
            aria-label="Describe the data you want to see"
            disabled={loading}
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-subtle-foreground">Fills in the entity, fields and filters below. You can adjust them after.</p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerate}
              disabled={loading || !query.trim()}
              type="button"
            >
              <Icon name={loading ? 'spinner' : 'sparkles'} className={loading ? 'h-3.5 w-3.5 animate-spin' : 'h-3.5 w-3.5'} />
              {loading ? 'Working it out' : 'Build the query'}
            </Button>
          </div>

          {error && <InlineError onRetry={handleGenerate}>{error}</InlineError>}

          {lastExplanation && !error && (
            <p className="rounded-md border border-border bg-card px-2.5 py-2 text-xs text-muted-foreground">
              {lastExplanation}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
