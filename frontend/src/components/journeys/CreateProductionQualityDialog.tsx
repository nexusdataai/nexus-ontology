import { useState } from 'react';
import { CreateJourneyShell } from './studio/CreateJourneyShell';
import { CallProcessingJourney } from '../../types/callProcessingJourney';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';

interface CreateProductionQualityDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (journey: CallProcessingJourney) => void;
}

export function CreateProductionQualityDialog({ open, onClose, onCreated }: CreateProductionQualityDialogProps) {
  const [name, setName] = useState('Production & Quality Copilot');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Journey name is required'); return; }
    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        name: name.trim(),
        type: 'production-quality' as const,
        odaComponentType: 'supply-chain',
        stages: [{ stageId: 'production_quality', name: 'Production & Quality Copilot', order: 0, steps: [] }],
        config: {},
      };

      const response = await callProcessingJourneyService.createJourney(payload);
      if (response.success && response.data) {
        const journeyId = response.data.id;
        try {
          await fetch(`/api/v1/journeys/${journeyId}/stages?stage_id=production_quality`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'Production & Quality Copilot', order: 0 }),
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
    setName('Production & Quality Copilot');
    setError(null);
    onClose();
  };

  return (
    <CreateJourneyShell
      open={open}
      onClose={handleClose}
      title="New Production & Quality Copilot Journey"
      name={name}
      onNameChange={setName}
      namePlaceholder="Production & Quality Copilot"
      steps={[
        "Load Production Data",
        "OEE Calculation",
        "Yield Analysis",
        "Quality Scoring",
        "Schedule Adherence",
        "Publish Results",
      ]}
      error={error}
      isSubmitting={isSubmitting}
      onSubmit={handleSubmit}
    />
  );
}
