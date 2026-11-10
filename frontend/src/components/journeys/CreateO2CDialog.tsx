import { useState } from 'react';
import { CreateJourneyShell } from './studio/CreateJourneyShell';
import { CallProcessingJourney } from '../../types/callProcessingJourney';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';

interface CreateO2CDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (journey: CallProcessingJourney) => void;
}

export function CreateO2CDialog({ open, onClose, onCreated }: CreateO2CDialogProps) {
  const [name, setName] = useState('Order-to-Cash Monitor');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Journey name is required'); return; }
    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        name: name.trim(),
        type: 'order-to-cash' as const,
        odaComponentType: 'resource-management',
        stages: [{ stageId: 'order_to_cash', name: 'Order-to-Cash Monitor', order: 0, steps: [] }],
        config: {},
      };

      const response = await callProcessingJourneyService.createJourney(payload);
      if (response.success && response.data) {
        const journeyId = response.data.id;
        try {
          await fetch(`/api/v1/journeys/${journeyId}/stages?stage_id=order_to_cash`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'Order-to-Cash Monitor', order: 0 }),
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
    setName('Order-to-Cash Monitor');
    setError(null);
    onClose();
  };

  return (
    <CreateJourneyShell
      open={open}
      onClose={handleClose}
      title="New Order-to-Cash Journey"
      name={name}
      onNameChange={setName}
      namePlaceholder="Order-to-Cash Monitor"
      steps={[
        "Entity Resolution (match orders across systems)",
        "Three-Way Match (PO vs delivery vs invoice)",
        "Anomaly Scoring (detect discrepancies)",
        "Risk Prioritization (rank by composite risk)",
        "Cash Flow Projection (forecast from open AR)",
        "Store Results (S3 + Glue for dashboards)",
      ]}
      error={error}
      isSubmitting={isSubmitting}
      onSubmit={handleSubmit}
    />
  );
}
