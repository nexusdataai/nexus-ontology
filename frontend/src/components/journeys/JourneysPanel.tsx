/**
 * JourneysPanel Component
 * 
 * Main container that manages navigation between list and studio views.
 * Preserves state on view switches.
 * 
 * Requirements: 1.3, 1.4
 */

import { useState, useCallback, useEffect } from 'react';
import { CallProcessingJourney } from '../../types/callProcessingJourney';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';
import { JourneyListView } from './JourneyListView';
import { JourneyStudioView } from './JourneyStudioView';
import { CreateSemanticRagDialog } from './CreateSemanticRagDialog';
import { CreateO2CDialog } from './CreateO2CDialog';
import { CreateDemandForecastingDialog } from './CreateDemandForecastingDialog';
import { CreateInventoryOptDialog } from './CreateInventoryOptDialog';
import { CreateProcurementDialog } from './CreateProcurementDialog';
import { CreateProductionQualityDialog } from './CreateProductionQualityDialog';
import { CreateSupplyChainRiskDialog } from './CreateSupplyChainRiskDialog';
import { CreateCustomer360Dialog } from './CreateCustomer360Dialog';
import { CreateESGDialog } from './CreateESGDialog';
import { confirmDialog } from '@/components/ds/confirm';

export interface JourneysPanelProps {
  initialJourneyId?: string;
}

export interface JourneysPanelState {
  view: 'list' | 'studio';
  selectedJourneyId: string | null;
  filters: JourneyFilter;
}

export function JourneysPanel({ initialJourneyId }: JourneysPanelProps) {
  // View state
  const [view, setView] = useState<'list' | 'studio'>(
    initialJourneyId ? 'studio' : 'list'
  );
  const [selectedJourneyId, setSelectedJourneyId] = useState<string | null>(
    initialJourneyId || null
  );

  useEffect(() => {
    if (initialJourneyId) {
      setSelectedJourneyId(initialJourneyId);
      setView('studio');
    }
  }, [initialJourneyId]);
  
  // Journey data
  const [journeys, setJourneys] = useState<CallProcessingJourney[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  // The last list load failed (shown as an error with a retry in the list).
  const [loadError, setLoadError] = useState(false);
  
  // Dialog state
  const [createRagDialogOpen, setCreateRagDialogOpen] = useState(false);
  const [createO2CDialogOpen, setCreateO2CDialogOpen] = useState(false);
  const [createDFDialogOpen, setCreateDFDialogOpen] = useState(false);
  const [createIODialogOpen, setCreateIODialogOpen] = useState(false);
  const [createProcDialogOpen, setCreateProcDialogOpen] = useState(false);
  const [createPQDialogOpen, setCreatePQDialogOpen] = useState(false);
  const [createSCRDialogOpen, setCreateSCRDialogOpen] = useState(false);
  const [createC360DialogOpen, setCreateC360DialogOpen] = useState(false);
  const [createESGDialogOpen, setCreateESGDialogOpen] = useState(false);

  // Load journeys
  const loadJourneys = useCallback(async () => {
    setIsLoading(true);
    setLoadError(false);
    try {
      console.log('🔄 JourneysPanel: Loading journeys from backend...');
      const response = await callProcessingJourneyService.listJourneys();
      console.log('📥 JourneysPanel: Response received:', {
        success: response.success,
        count: response.data?.length,
        firstJourney: response.data?.[0]?.id,
        error: response.error
      });
      
      if (response.success && response.data) {
        console.log('✅ JourneysPanel: Setting', response.data.length, 'journeys in state');
        setJourneys(response.data);
      } else {
        console.warn('⚠️  JourneysPanel: No journey data in response');
        setJourneys([]);
      }
    } catch (err) {
      console.error('❌ JourneysPanel: Error loading journeys:', err);
      setJourneys([]);
      setLoadError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadJourneys();
  }, [loadJourneys]);

  // Handlers
  const handleSelectJourney = (journeyId: string) => {
    setSelectedJourneyId(journeyId);
    setView('studio');
  };

  const handleBackToList = () => {
    setView('list');
    // Refresh list when coming back from studio
    loadJourneys();
  };

  const handleJourneyCreated = (_journey: CallProcessingJourney) => {
    loadJourneys();
  };

  // Delete journey handler
  const handleDelete = async (journeyId: string) => {
    if (!(await confirmDialog({ title: 'Delete this journey?', description: 'This cannot be undone.', destructive: true }))) {
      return;
    }
    
    setActionLoadingId(journeyId);
    try {
      await callProcessingJourneyService.deleteJourney(journeyId);
      // Refresh list after deletion
      await loadJourneys();
    } catch (err) {
      console.error('Error deleting journey:', err);
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <div className="h-full" data-testid="journeys-panel">
      {view === 'list' ? (
        <div className="h-full overflow-auto">
          <JourneyListView
            journeys={journeys}
            isLoading={isLoading}
            onSelectJourney={handleSelectJourney}
            onCreateSemanticRag={() => setCreateRagDialogOpen(true)}
            onCreateO2C={() => setCreateO2CDialogOpen(true)}
            onCreateDemandForecasting={() => setCreateDFDialogOpen(true)}
            onCreateInventoryOpt={() => setCreateIODialogOpen(true)}
            onCreateProcurement={() => setCreateProcDialogOpen(true)}
            onCreateProductionQuality={() => setCreatePQDialogOpen(true)}
            onCreateSupplyChainRisk={() => setCreateSCRDialogOpen(true)}
            onCreateCustomer360={() => setCreateC360DialogOpen(true)}
            onCreateESG={() => setCreateESGDialogOpen(true)}
            onDelete={handleDelete}
            onRefresh={loadJourneys}
            actionLoadingId={actionLoadingId}
            error={loadError}
          />
        </div>
      ) : (
        selectedJourneyId && (
          <div className="page">
            <JourneyStudioView
              journeyId={selectedJourneyId}
              onBack={handleBackToList}
            />
          </div>
        )
      )}

      <CreateSemanticRagDialog
        open={createRagDialogOpen}
        onClose={() => setCreateRagDialogOpen(false)}
        onCreated={handleJourneyCreated}
      />

      <CreateO2CDialog
        open={createO2CDialogOpen}
        onClose={() => setCreateO2CDialogOpen(false)}
        onCreated={handleJourneyCreated}
      />

      <CreateDemandForecastingDialog
        open={createDFDialogOpen}
        onClose={() => setCreateDFDialogOpen(false)}
        onCreated={handleJourneyCreated}
      />

      <CreateInventoryOptDialog
        open={createIODialogOpen}
        onClose={() => setCreateIODialogOpen(false)}
        onCreated={handleJourneyCreated}
      />

      <CreateProcurementDialog
        open={createProcDialogOpen}
        onClose={() => setCreateProcDialogOpen(false)}
        onCreated={handleJourneyCreated}
      />

      <CreateProductionQualityDialog
        open={createPQDialogOpen}
        onClose={() => setCreatePQDialogOpen(false)}
        onCreated={handleJourneyCreated}
      />

      <CreateSupplyChainRiskDialog
        open={createSCRDialogOpen}
        onClose={() => setCreateSCRDialogOpen(false)}
        onCreated={handleJourneyCreated}
      />

      <CreateCustomer360Dialog
        open={createC360DialogOpen}
        onClose={() => setCreateC360DialogOpen(false)}
        onCreated={handleJourneyCreated}
      />

      <CreateESGDialog
        open={createESGDialogOpen}
        onClose={() => setCreateESGDialogOpen(false)}
        onCreated={handleJourneyCreated}
      />
    </div>
  );
}

export default JourneysPanel;
