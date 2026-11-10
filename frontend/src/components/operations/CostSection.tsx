import { OpsFacts, OpsPreview } from './OpsPreview';

const GROUPS = [
  { key: 'infra', label: 'Cloud infrastructure', total: 142, tone: 'bg-primary', items: [['EKS cluster', 73], ['EC2 nodes (2)', 45], ['Load balancer', 16.2], ['NAT gateway', 7.8]] },
  { key: 'ai', label: 'AI and compute', total: 24, tone: 'bg-primary/60', items: [['OpenAI (GPT-4o)', 18], ['Athena queries', 3.5], ['Glue catalogue', 1.5], ['Cognito', 1]] },
  { key: 'storage', label: 'Storage', total: 8.5, tone: 'bg-primary/30', items: [['S3 (4 buckets)', 3.2], ['DynamoDB', 2.5], ['ECR images', 1.8], ['CloudWatch logs', 1]] },
] as const;

const money = (n: number) => `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function CostSection() {
  const total = GROUPS.reduce((s, g) => s + g.total, 0);
  return (
    <OpsPreview
      title="Cost"
      description="What this environment costs to run each month, by kind of resource."
      coming="Real figures from AWS Cost Explorer will replace these numbers in a future release."
    >
      <section className="rounded-xl border border-border bg-card p-6 shadow-xs">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h3 className="text-sm text-muted-foreground">Estimated monthly total</h3>
            <p className="mt-2 flex items-baseline gap-1.5">
              <span className="num text-4xl font-medium tracking-tight text-foreground">{money(total)}</span>
              <span className="text-sm text-muted-foreground">per month</span>
            </p>
          </div>
          <p className="text-sm text-muted-foreground">Based on current usage.</p>
        </div>
        <div className="mt-5 flex h-2.5 gap-0.5 overflow-hidden rounded-full" role="img" aria-label="Cost by kind of resource">
          {GROUPS.map((g, i) => <span key={g.key} className={`grow-x h-full ${g.tone}`} style={{ width: `${(g.total / total) * 100}%`, ['--i' as any]: i }} />)}
        </div>
        <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-1.5 text-sm">
          {GROUPS.map(g => (
            <li key={g.key} className="flex items-center gap-2 text-muted-foreground">
              <span className={`h-2 w-2 rounded-[2px] ${g.tone}`} aria-hidden="true" />
              {g.label}
              <span className="num font-medium text-foreground">{Math.round((g.total / total) * 100)}%</span>
            </li>
          ))}
        </ul>
      </section>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {GROUPS.map((g, i) => (
          <OpsFacts
            key={g.key}
            index={i}
            title={g.label}
            headline={money(g.total)}
            unit="per month"
            items={g.items.map(([label, value]) => ({ label: String(label), value: money(Number(value)) }))}
          />
        ))}
      </div>
    </OpsPreview>
  );
}
