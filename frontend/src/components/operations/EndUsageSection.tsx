import { OpsFacts, OpsPreview, pending } from './OpsPreview';

export function EndUsageSection() {
  return (
    <OpsPreview
      title="End usage"
      description="Who is using the platform, how much the API is called, and how many jobs have run."
      coming="Usage is not measured on this installation, so no figures are shown. They will appear here once usage analytics is switched on."
    >
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <OpsFacts index={0} title="People" items={pending(['Users', 'Active sessions now', 'Sign-ins today', 'Unique users, last 7 days', 'Average session'])} />
        <OpsFacts index={1} title="API requests" items={pending(['Requests today', 'Average per minute', 'Busiest endpoint', 'Error rate'])} />
        <OpsFacts index={2} title="Jobs processed" items={pending(['Total', 'Today', 'With AI analysis'])} />
      </div>
    </OpsPreview>
  );
}
