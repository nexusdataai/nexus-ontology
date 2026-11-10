import { Button } from '../ui/button';
import { Icon } from '@/components/ds/Icon';
import { OpsFacts, OpsPreview } from './OpsPreview';

const Ok = ({ children }: { children: React.ReactNode }) => (
  <span className="flex items-center gap-2"><Icon name="check-circle" className="h-4 w-4 shrink-0 text-success" />{children}</span>
);

export function DataProtectionSection() {
  return (
    <OpsPreview
      title="Data protection"
      description="Backups of the platform and its data, and the points you can restore to."
      coming="Backup and restore actions are not connected yet, so the buttons are switched off."
    >
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <OpsFacts
          index={0}
          title="Platform backup"
          note={<Ok>Last backup succeeded</Ok>}
          items={[
            { label: 'Last backup', value: '2 hours ago' },
            { label: 'Size', value: '2.4 GB' },
            { label: 'Schedule', value: 'Every 6 hours' },
            { label: 'Kept for', value: '30 days' },
          ]}
          action={<Button variant="outline" size="sm" className="w-full" disabled>Back up now</Button>}
        />
        <OpsFacts
          index={1}
          title="Analytics data"
          note={<Ok>Data is protected</Ok>}
          items={[
            { label: 'Database recovery', value: 'Point in time, on' },
            { label: 'File versioning', value: 'On' },
            { label: 'Catalogue snapshots', value: 'Daily' },
            { label: 'Total data', value: '1.8 GB' },
          ]}
          action={<Button variant="outline" size="sm" className="w-full" disabled>Create snapshot</Button>}
        />
        <OpsFacts
          index={2}
          title="Restore points"
          note="Three points available"
          items={[
            { label: 'Latest', value: 'Today 14:00' },
            { label: 'Yesterday', value: '23:00' },
            { label: 'Two days ago', value: '23:00' },
            { label: 'Time to restore', value: 'About 15 min' },
          ]}
          action={<Button variant="outline" size="sm" className="w-full" disabled>Restore from backup</Button>}
        />
      </div>
    </OpsPreview>
  );
}
