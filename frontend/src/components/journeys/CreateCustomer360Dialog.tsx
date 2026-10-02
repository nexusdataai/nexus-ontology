import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2 } from 'lucide-react';
import { CallProcessingJourney } from '../../types/callProcessingJourney';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';

interface CreateCustomer360DialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (journey: CallProcessingJourney) => void;
}

export function CreateCustomer360Dialog({ open, onClose, onCreated }: CreateCustomer360DialogProps) {
  const [name, setName] = useState('Customer 360 & Revenue Growth');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Journey name is required'); return; }
    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        name: name.trim(),
        type: 'customer-360' as const,
        odaComponentType: 'supply-chain',
        stages: [{ stageId: 'customer_360', name: 'Customer 360 & Revenue Growth', order: 0, steps: [] }],
        config: {},
      };

      const response = await callProcessingJourneyService.createJourney(payload);
      if (response.success && response.data) {
        const journeyId = response.data.id;
        try {
          await fetch(`/api/v1/journeys/${journeyId}/stages?stage_id=customer_360`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'Customer 360 & Revenue Growth', order: 0 }),
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
    setName('Customer 360 & Revenue Growth');
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>New Customer 360 & Revenue Growth Journey</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Journey Name</Label>
            <Input value={name} onChange={e => setName(e.target.value)} placeholder="Customer 360 & Revenue Growth" />
          </div>
          <div className="text-xs text-muted-foreground space-y-1">
            <p>This journey will run 6 automated steps:</p>
            <ol className="list-decimal list-inside space-y-0.5 ml-2">
              <li>Load Customer Data</li>
              <li>CLV Calculation</li>
              <li>Churn Prediction</li>
              <li>Wallet Share Analysis</li>
              <li>Cross-Sell Scoring</li>
              <li>Publish Results</li>
            </ol>
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Create Journey
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
