import { useState } from 'react';
import { CreateJourneyShell } from './studio/CreateJourneyShell';
import { CallProcessingJourney } from '../../types/callProcessingJourney';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';

interface CreateDemandForecastingDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (journey: CallProcessingJourney) => void;
}

export function CreateDemandForecastingDialog({ open, onClose, onCreated }: CreateDemandForecastingDialogProps) {
  const [name, setName] = useState('Demand Forecasting Engine');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Journey name is required'); return; }
    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        name: name.trim(),
        type: 'demand-forecasting' as const,
        odaComponentType: 'supply-chain',
        stages: [{ stageId: 'demand_forecasting', name: 'Demand Forecasting Engine', order: 0, steps: [] }],
        config: {},
      };

      const response = await callProcessingJourneyService.createJourney(payload);
      if (response.success && response.data) {
        const journeyId = response.data.id;
        try {
          await fetch(`/api/v1/journeys/${journeyId}/stages?stage_id=demand_forecasting`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'Demand Forecasting Engine', order: 0 }),
          });
        } catch (e) {
          console.warn('Stage registration (non-fatal):', e);
        }
        onCreated(response.data);
        handleClose();
      } else {
        setError(response.error?.message || 'Failed to create journey');
      }
    } catch (e: any) {
      setError(e.message || 'Failed to create journey');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setName('Demand Forecasting Engine');
    setError(null);
    onClose();
  };

  return (
    <CreateJourneyShell
      open={open}
      onClose={handleClose}
      title="New Demand Forecasting Journey"
      name={name}
      onNameChange={setName}
      namePlaceholder="Demand Forecasting Engine"
      steps={[
        "Feature Engineering (aggregate sales, inventory, signals)",
        "Model Ensemble (time-series + ML weighted average)",
        "Promotion Overlay (apply promotion response curves)",
        "Cannibalization Adjustment (cross-product substitution)",
        "Consensus Integration (merge AI + sales-team overrides)",
        "Publish Forecast (write KPIs, alerts, data to S3 + simulator)",
      ]}
      error={error}
      isSubmitting={isSubmitting}
      onSubmit={handleSubmit}
    />
  );
}
