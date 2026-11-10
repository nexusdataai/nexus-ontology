import { useState } from 'react';
import { CreateJourneyShell } from './studio/CreateJourneyShell';
import { CallProcessingJourney } from '../../types/callProcessingJourney';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';

interface CreateInventoryOptDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (journey: CallProcessingJourney) => void;
}

export function CreateInventoryOptDialog({ open, onClose, onCreated }: CreateInventoryOptDialogProps) {
  const [name, setName] = useState('Inventory Optimization');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Journey name is required'); return; }
    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        name: name.trim(),
        type: 'inventory-optimization' as const,
        odaComponentType: 'supply-chain',
        stages: [{ stageId: 'inventory_optimization', name: 'Inventory Optimization', order: 0, steps: [] }],
        config: {},
      };

      const response = await callProcessingJourneyService.createJourney(payload);
      if (response.success && response.data) {
        const journeyId = response.data.id;
        try {
          await fetch(`/api/v1/journeys/${journeyId}/stages?stage_id=inventory_optimization`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'Inventory Optimization', order: 0 }),
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
    setName('Inventory Optimization');
    setError(null);
    onClose();
  };

  return (
    <CreateJourneyShell
      open={open}
      onClose={handleClose}
      title="New Inventory Optimization Journey"
      name={name}
      onNameChange={setName}
      namePlaceholder="Inventory Optimization"
      steps={[
        "Load Positions",
        "ABC Classification",
        "Reorder Calculation",
        "Expiry Analysis",
        "Rebalance Recommendations",
        "Publish Results",
      ]}
      error={error}
      isSubmitting={isSubmitting}
      onSubmit={handleSubmit}
    />
  );
}
