import { useState } from 'react';
import { CreateJourneyShell } from './studio/CreateJourneyShell';
import { CallProcessingJourney } from '../../types/callProcessingJourney';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';

interface CreateSupplyChainRiskDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (journey: CallProcessingJourney) => void;
}

export function CreateSupplyChainRiskDialog({ open, onClose, onCreated }: CreateSupplyChainRiskDialogProps) {
  const [name, setName] = useState('Supply Chain Risk Radar');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Journey name is required'); return; }
    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        name: name.trim(),
        type: 'supply-chain-risk' as const,
        odaComponentType: 'supply-chain',
        stages: [{ stageId: 'supply_chain_risk', name: 'Supply Chain Risk Radar', order: 0, steps: [] }],
        config: {},
      };

      const response = await callProcessingJourneyService.createJourney(payload);
      if (response.success && response.data) {
        const journeyId = response.data.id;
        try {
          await fetch(`/api/v1/journeys/${journeyId}/stages?stage_id=supply_chain_risk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'Supply Chain Risk Radar', order: 0 }),
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
    setName('Supply Chain Risk Radar');
    setError(null);
    onClose();
  };

  return (
    <CreateJourneyShell
      open={open}
      onClose={handleClose}
      title="New Supply Chain Risk Radar Journey"
      name={name}
      onNameChange={setName}
      namePlaceholder="Supply Chain Risk Radar"
      steps={[
        "Load Supplier Data",
        "Delivery Scoring",
        "Quality Scoring",
        "Financial Risk",
        "Market Signal Integration",
        "Publish Results",
      ]}
      error={error}
      isSubmitting={isSubmitting}
      onSubmit={handleSubmit}
    />
  );
}
