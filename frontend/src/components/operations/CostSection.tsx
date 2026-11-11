import { OpsFacts, OpsPreview, pending } from './OpsPreview';

export function CostSection() {
  return (
    <OpsPreview
      title="Cost"
      description="What this environment costs to run each month, by kind of resource."
      coming="This installation has no cost feed, so no figures are shown. They will appear here once a billing source is connected."
    >
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <OpsFacts index={0} title="Infrastructure" items={pending(['Compute', 'Networking', 'Monthly total'])} />
        <OpsFacts index={1} title="AI and compute" items={pending(['Language models', 'Queries', 'Monthly total'])} />
        <OpsFacts index={2} title="Storage" items={pending(['Files', 'Databases', 'Logs', 'Monthly total'])} />
      </div>
    </OpsPreview>
  );
}
