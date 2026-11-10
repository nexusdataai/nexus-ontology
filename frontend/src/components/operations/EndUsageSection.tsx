import { OpsFacts, OpsPreview } from './OpsPreview';

export function EndUsageSection() {
  return (
    <OpsPreview
      title="End usage"
      description="Who is using the platform, how much the API is called, and how many jobs have run."
      coming="Live usage analytics will replace these numbers in a future release."
    >
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <OpsFacts
          index={0}
          title="People"
          headline="12"
          unit="users"
          items={[
            { label: 'Active sessions now', value: '3' },
            { label: 'Sign-ins today', value: '8' },
            { label: 'Unique users, last 7 days', value: '5' },
            { label: 'Average session', value: '24 min' },
          ]}
        />
        <OpsFacts
          index={1}
          title="API requests today"
          headline="1,247"
          items={[
            { label: 'Average per minute', value: '12.3' },
            { label: 'Busiest endpoint', value: '/api/v1/journeys', mono: true },
            { label: 'Error rate', value: '0.8%' },
          ]}
        />
        <OpsFacts
          index={2}
          title="Jobs processed"
          headline="37"
          items={[
            { label: 'Today', value: '3' },
            { label: 'With transcription', value: '34' },
            { label: 'With AI analysis', value: '31' },
          ]}
        />
      </div>
    </OpsPreview>
  );
}
