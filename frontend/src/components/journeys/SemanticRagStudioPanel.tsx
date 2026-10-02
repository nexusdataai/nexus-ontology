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
import { Brain } from 'lucide-react';

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
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Loading Knowledge Processor journey...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <p className="text-destructive text-sm">{error}</p>
        <Button variant="outline" size="sm" onClick={loadSemanticRagJourney}>
          Retry
        </Button>
      </div>
    );
  }

  if (!journeyId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <Brain className="h-10 w-10 text-muted-foreground" />
        <p className="text-muted-foreground text-sm">
          No Knowledge Processor journey found. Create one from the Journeys tab first.
        </p>
        {onBackToJourneys && (
          <Button variant="outline" size="sm" onClick={onBackToJourneys}>
            Go to Journeys
          </Button>
        )}
      </div>
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
