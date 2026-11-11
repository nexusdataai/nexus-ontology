import { Button } from '../ui/button';
import { OpsFacts, OpsPreview, pending } from './OpsPreview';

export function DataProtectionSection() {
  return (
    <OpsPreview
      title="Data protection"
      description="Backups of the platform and its data, and the points you can restore to."
      coming="Backup and restore are not connected on this installation, so no figures are shown and the buttons are switched off."
    >
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <OpsFacts
          index={0}
          title="Platform backup"
          items={pending(['Last backup', 'Size', 'Schedule', 'Kept for'])}
          action={<Button variant="outline" size="sm" className="w-full" disabled>Back up now</Button>}
        />
        <OpsFacts
          index={1}
          title="Analytics data"
          items={pending(['Database recovery', 'File versioning', 'Catalogue snapshots', 'Total data'])}
          action={<Button variant="outline" size="sm" className="w-full" disabled>Create snapshot</Button>}
        />
        <OpsFacts
          index={2}
          title="Restore points"
          items={pending(['Latest', 'Earlier points', 'Time to restore'])}
          action={<Button variant="outline" size="sm" className="w-full" disabled>Restore from backup</Button>}
        />
      </div>
    </OpsPreview>
  );
}
