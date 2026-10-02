import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Loader2 } from 'lucide-react';
import { CallProcessingJourney } from '../../types/callProcessingJourney';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';

interface CreateSemanticRagDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (journey: CallProcessingJourney) => void;
}

export function CreateSemanticRagDialog({ open, onClose, onCreated }: CreateSemanticRagDialogProps) {
  const [name, setName] = useState('');
  const [policyPath, setPolicyPath] = useState('');
  const [workflowPath, setWorkflowPath] = useState('');
  const [integrationPath, setIntegrationPath] = useState('');
  const [enrichWithLlm, setEnrichWithLlm] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Journey name is required');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        name: name.trim(),
        type: 'semantic-rag' as const,
        odaComponentType: 'resource-management',
        stages: [{
          stageId: 'semantic_rag',
          name: 'Knowledge Processor',
          order: 0,
          steps: [],
        }],
        config: {
          policy_path: policyPath,
          workflow_path: workflowPath,
          integration_path: integrationPath,
          enrich_with_llm: enrichWithLlm,
          skip_enrichment: !enrichWithLlm,
        },
      };

      const response = await callProcessingJourneyService.createJourney(payload);

      if (response.success && response.data) {
        const journeyId = response.data.id;
        try {
          await fetch(`/api/v1/journeys/${journeyId}/stages?stage_id=semantic_rag`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'Knowledge Processor', order: 0 }),
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
    setName('');
    setPolicyPath('');
    setWorkflowPath('');
    setIntegrationPath('');
    setEnrichWithLlm(true);
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create Semantic RAG Journey</DialogTitle>
          <p className="text-sm text-muted-foreground">
            Build enterprise knowledge graph from FDW metadata, policies, workflows, and integration mappings.
          </p>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Journey Name</Label>
            <Input
              id="name"
              placeholder="e.g. Enterprise Knowledge Build"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="policyPath">Policy Documents Path (optional)</Label>
            <Input
              id="policyPath"
              placeholder="e.g. src/stages/semantic-rag/sample-data/policies"
              value={policyPath}
              onChange={(e) => setPolicyPath(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">Local path or S3 prefix for policy docs</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="workflowPath">Workflow Definitions Path (optional)</Label>
            <Input
              id="workflowPath"
              placeholder="e.g. src/stages/semantic-rag/sample-data/workflows"
              value={workflowPath}
              onChange={(e) => setWorkflowPath(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="integrationPath">Integration Mappings Path (optional)</Label>
            <Input
              id="integrationPath"
              placeholder="e.g. src/stages/semantic-rag/sample-data/integrations"
              value={integrationPath}
              onChange={(e) => setIntegrationPath(e.target.value)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>LLM Enrichment</Label>
              <p className="text-xs text-muted-foreground">Use GPT to generate semantic descriptions</p>
            </div>
            <Switch checked={enrichWithLlm} onCheckedChange={setEnrichWithLlm} />
          </div>

          {error && (
            <div className="text-sm text-destructive bg-destructive/10 rounded p-2">{error}</div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
            Create Journey
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
