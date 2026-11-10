/**
 * Logo of a source system (Salesforce, SAP, Oracle, Google Drive, Microsoft…).
 * Use wherever a system is named, instead of a coloured dot or an initial.
 * Unknown systems fall back to a neutral product icon.
 *
 * Logos live in src/assets/brands (Freepik / Flaticon brand set). They are
 * trademarks of their owners and are used only to identify the integration.
 */
import salesforce from '@/assets/brands/salesforce.svg';
import googleDrive from '@/assets/brands/google-drive.svg';
import slack from '@/assets/brands/slack.svg';
import sap from '@/assets/brands/sap.svg';
import oracle from '@/assets/brands/oracle.svg';
import mysql from '@/assets/brands/mysql.svg';
import microsoftRaw from '@/assets/brands/microsoft.svg?raw';
import googleRaw from '@/assets/brands/google.svg?raw';
import { cn } from '@/lib/utils';
import { Icon, type IconName } from '@/components/ds/Icon';

type Def = { src?: string; raw?: string; icon?: IconName; name: string };

const DEFS: Record<string, Def> = {
  salesforce: { src: salesforce, name: 'Salesforce' },
  sap: { src: sap, name: 'SAP' },
  oracle: { src: oracle, name: 'Oracle' },
  google_drive: { src: googleDrive, name: 'Google Drive' },
  microsoft: { raw: microsoftRaw, name: 'Microsoft 365' },
  google: { raw: googleRaw, name: 'Google' },
  slack: { src: slack, name: 'Slack' },
  mysql: { src: mysql, name: 'MySQL' },
  social: { icon: 'megaphone-or-rss', name: 'Social listening' },
  files: { icon: 'upload', name: 'File uploads' },
  knowledge: { icon: 'brain-ai', name: 'Knowledge base' },
  external: { icon: 'globe', name: 'External systems' },
  langflow: { icon: 'workflow', name: 'Langflow' },
};

/** Every spelling the backend and the UI use for a system. */
const ALIASES: Record<string, string> = {
  sfdc: 'salesforce', salesforce_crm: 'salesforce', 'sample-crm': 'salesforce', crm: 'salesforce', simulator: 'salesforce',
  'sap_s/4hana': 'sap', sap_s4hana: 'sap', 'sample-sap': 'sap', s4hana: 'sap',
  oracle_erp: 'oracle', 'oracle-erp': 'oracle', 'sample-erp': 'oracle', erp: 'oracle',
  gdrive: 'google_drive', 'google-drive': 'google_drive', drive: 'google_drive', 'sample-drive': 'google_drive', cloud_drive: 'google_drive',
  office365: 'microsoft', office_365: 'microsoft', o365: 'microsoft', microsoft_365: 'microsoft', teams: 'microsoft',
  social_listening: 'social', 'sample-social': 'social',
  file_uploads: 'files', file_upload: 'files', 'sample-files': 'files', uploads: 'files',
  'knowledge-base': 'knowledge', knowledgebase: 'knowledge',
  'bss-studio': 'langflow', external_systems: 'external',
};

export function resolveSystem(system?: string | null): { key: string; def: Def | null } {
  const raw = String(system || '').trim().toLowerCase().replace(/\s+/g, '_');
  const key = ALIASES[raw] || raw;
  if (DEFS[key]) return { key, def: DEFS[key] };
  const partial = Object.keys(DEFS).find(k => raw.includes(k));
  return partial ? { key: partial, def: DEFS[partial] } : { key: raw, def: null };
}

/** Display name for a system key, e.g. "sfdc" → "Salesforce". */
export function systemName(system?: string | null): string {
  const { def } = resolveSystem(system);
  if (def) return def.name;
  const s = String(system || '').replace(/[_-]+/g, ' ').trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : 'Unknown';
}

interface SystemLogoProps {
  system?: string | null;
  /** Bare mark (default) or the mark on a neutral tile. */
  tile?: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
}

const MARK = { xs: 'h-3.5 w-3.5', sm: 'h-4 w-4', md: 'h-5 w-5', lg: 'h-7 w-7' };
const TILE = { xs: 'h-6 w-6 rounded-md', sm: 'h-8 w-8 rounded-md', md: 'h-10 w-10 rounded-lg', lg: 'h-12 w-12 rounded-xl' };

export function SystemLogo({ system, tile, size = 'sm', className }: SystemLogoProps) {
  const { def } = resolveSystem(system);
  const label = systemName(system);
  const mark = def?.src ? (
    <img src={def.src} alt="" className={cn(MARK[size], 'shrink-0 object-contain')} draggable={false} />
  ) : def?.raw ? (
    <span className={cn(MARK[size], 'inline-flex shrink-0 text-foreground [&_svg]:h-full [&_svg]:w-full')} dangerouslySetInnerHTML={{ __html: def.raw }} />
  ) : (
    <Icon name={def?.icon || 'database'} className={cn(MARK[size], 'text-muted-foreground')} />
  );
  if (!tile) return <span className={cn('inline-flex shrink-0', className)} title={label} aria-label={label} role="img">{mark}</span>;
  return (
    <span className={cn('inline-flex shrink-0 items-center justify-center border border-border bg-card', TILE[size], className)} title={label} aria-label={label} role="img">
      {mark}
    </span>
  );
}

export default SystemLogo;
