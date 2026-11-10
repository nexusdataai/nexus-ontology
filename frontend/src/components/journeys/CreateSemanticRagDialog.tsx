import { useState } from 'react';
import { Field } from '@/components/ds/kit';
import { CreateJourneyShell } from './studio/CreateJourneyShell';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
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
    <CreateJourneyShell
      open={open}
      onClose={handleClose}
      title="New knowledge pipeline"
      description="Builds the enterprise knowledge graph from source metadata, policies, workflows and integration mappings."
      name={name}
      onNameChange={setName}
      namePlaceholder="Enterprise knowledge build"
      error={error}
      isSubmitting={isSubmitting}
      onSubmit={handleSubmit}
    >
      <Field label="Policy documents (optional)" htmlFor="policyPath" hint="A local path or an S3 prefix.">
        <Input
          id="policyPath"
          placeholder="src/stages/semantic-rag/sample-data/policies"
          value={policyPath}
          onChange={(e) => setPolicyPath(e.target.value)}
          className="font-mono text-xs"
        />
      </Field>

      <Field label="Workflow definitions (optional)" htmlFor="workflowPath">
        <Input
          id="workflowPath"
          placeholder="src/stages/semantic-rag/sample-data/workflows"
          value={workflowPath}
          onChange={(e) => setWorkflowPath(e.target.value)}
          className="font-mono text-xs"
        />
      </Field>

      <Field label="Integration mappings (optional)" htmlFor="integrationPath">
        <Input
          id="integrationPath"
          placeholder="src/stages/semantic-rag/sample-data/integrations"
          value={integrationPath}
          onChange={(e) => setIntegrationPath(e.target.value)}
          className="font-mono text-xs"
        />
      </Field>

      <div className="flex items-center justify-between gap-4 border-t border-border pt-4">
        <label htmlFor="enrichWithLlm" className="min-w-0 cursor-pointer">
          <span className="block text-sm font-medium text-foreground">Describe entities with AI</span>
          <span className="block text-xs text-muted-foreground">A language model writes a plain description for each entity.</span>
        </label>
        <Switch id="enrichWithLlm" checked={enrichWithLlm} onCheckedChange={setEnrichWithLlm} />
      </div>
    </CreateJourneyShell>
  );
}
