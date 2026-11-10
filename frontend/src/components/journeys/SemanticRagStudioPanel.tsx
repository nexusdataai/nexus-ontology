/**
 * SemanticRagStudioPanel
 *
 * Shows Journey Studio for the semantic-rag journey directly in a tab.
 * Resolves the first semantic-rag journey and renders JourneyStudioView;
 * if none exists, prompts the user to open Journeys to create one.
 */

import { useState, useCallback, useEffect } from 'react';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';
import { JourneyStudioView } from './JourneyStudioView';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { EmptyState } from '../ds/primitives';
import { InlineError } from '../ds/kit';

export interface SemanticRagStudioPanelProps {
  onBackToJourneys?: () => void;
  hideBackButton?: boolean;
  hideStatsCards?: boolean;
  hideHeader?: boolean;
  extraHeaderButtons?: React.ReactNode;
  overrideReportButton?: React.ReactNode;
}

export function SemanticRagStudioPanel({ onBackToJourneys, hideBackButton, hideStatsCards, hideHeader, extraHeaderButtons, overrideReportButton }: SemanticRagStudioPanelProps) {
  const [journeyId, setJourneyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSemanticRagJourney = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await callProcessingJourneyService.listJourneys({
        typeFilter: 'semantic-rag',
      });
      if (response.success && response.data && response.data.length > 0) {
        setJourneyId(response.data[0].id);
      } else {
        setJourneyId(null);
      }
    } catch (err) {
      setError((err as Error).message ?? 'Failed to load journeys');
      setJourneyId(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSemanticRagJourney();
  }, [loadSemanticRagJourney]);

  if (loading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading the knowledge processor">
        <Skeleton className="h-9 w-72 max-w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (error) {
    return <InlineError onRetry={loadSemanticRagJourney}>{error}</InlineError>;
  }

  if (!journeyId) {
    return (
      <EmptyState
        icon="brain-ai"
        title="No knowledge processor yet"
        description="The knowledge pipeline runs as a journey. Create a Knowledge Processor journey from Journeys, then come back here to run it."
        action={onBackToJourneys && (
          <Button variant="outline" size="sm" onClick={onBackToJourneys}>
            Go to Journeys
          </Button>
        )}
      />
    );
  }

  return (
    <JourneyStudioView
      journeyId={journeyId}
      onBack={onBackToJourneys || (() => {})}
      hideBackButton={hideBackButton}
      hideStatsCards={hideStatsCards}
      hideHeader={hideHeader}
      extraHeaderButtons={extraHeaderButtons}
      overrideReportButton={overrideReportButton}
    />
  );
}
