import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { Icon } from '@/components/ds/Icon';
import { Field, InlineError, StatusPill } from '@/components/ds/kit';
import { SystemLogo } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
import apiClient from '@/services/apiClient';
import GoogleDriveDiagnostics from './GoogleDriveDiagnostics';

interface Props {
  onBack: () => void;
}

interface GDriveSettings {
  auth_type: string;
  oauth2_config?: {
    client_id: string;
    client_secret: string;
    redirect_uri: string;
    scopes: string[];
  };
  scan_config: {
    folder_ids: string[];
    mime_type_filters: string[];
    max_files_per_scan: number;
    include_subfolders: boolean;
  };
  enable_auto_scan: boolean;
  enable_ocr_extraction: boolean;
  scan_schedule: string;
  last_updated?: string;
}

interface TestResult {
  success: boolean;
  message: string;
  files_found: number;
  latency_ms?: number;
}

const DEFAULT_SETTINGS: GDriveSettings = {
  auth_type: 'oauth2',
  oauth2_config: { client_id: '', client_secret: '', redirect_uri: 'http://localhost:3000/gdrive/callback', scopes: ['https://www.googleapis.com/auth/drive.readonly'] },
  scan_config: { folder_ids: [], mime_type_filters: ['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/csv'], max_files_per_scan: 100, include_subfolders: true },
  enable_auto_scan: false,
  enable_ocr_extraction: true,
  scan_schedule: '0 */6 * * *',
};

type Tab = 'settings' | 'diagnostics';

/** One settings block: what it is on the left, the controls on the right. */
const Block: React.FC<{ title: string; description?: string; children: React.ReactNode }> = ({ title, description, children }) => (
  <section className="grid gap-x-10 gap-y-4 border-b border-border py-7 first:pt-2 xl:grid-cols-[240px_minmax(0,1fr)]">
    <div>
      <h3 className="text-md font-medium text-foreground">{title}</h3>
      {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
    </div>
    <div className="min-w-0 max-w-2xl">{children}</div>
  </section>
);

/** A switch with its label and one line of explanation. */
const SwitchRow: React.FC<{ id: string; label: string; hint: string; checked: boolean; onChange: (v: boolean) => void }> = ({ id, label, hint, checked, onChange }) => (
  <div className="flex items-start justify-between gap-6 border-b border-border py-3.5 first:pt-0 last:border-b-0 last:pb-0">
    <div className="min-w-0">
      <label htmlFor={id} className="text-sm font-medium text-foreground">{label}</label>
      <p className="mt-0.5 text-sm text-muted-foreground">{hint}</p>
    </div>
    <Switch id={id} checked={checked} onCheckedChange={onChange} className="mt-0.5 shrink-0" />
  </div>
);

export default function GoogleDriveConnectorSettings({ onBack }: Props) {
  const [tab, setTab] = useState<Tab>('settings');
  const [settings, setSettings] = useState<GDriveSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [folderInput, setFolderInput] = useState('');

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data: any = await apiClient.get('/api/v1/connectors/gdrive/settings');
      if (data?.data) setSettings(data.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
      setSettings(DEFAULT_SETTINGS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSettings(); }, [fetchSettings]);

  const saveSettings = async () => {
    setSaving(true);
    setError(null);
    try {
      await apiClient.put('/api/v1/connectors/gdrive/settings', settings);
      setHasChanges(false);
      toast.success('Google Drive settings saved');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Save failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const data: any = await apiClient.post('/api/v1/connectors/gdrive/test');
      setTestResult(data);
      toast[data.success ? 'success' : 'error'](data.message);
    } catch (err) {
      setTestResult({ success: false, message: err instanceof Error ? err.message : 'Test failed', files_found: 0 });
      toast.error('Connection test failed');
    } finally {
      setTesting(false);
    }
  };

  const startOAuth = async () => {
    try {
      const data: any = await apiClient.post('/api/v1/connectors/gdrive/auth/start', {
        client_id: settings.oauth2_config?.client_id || '',
        redirect_uri: settings.oauth2_config?.redirect_uri || '',
      });
      if (data.authorization_url) {
        window.open(data.authorization_url, '_blank', 'width=600,height=700');
        toast.success('Google sign-in opened. Finish the approval in the new window.');
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to start OAuth');
    }
  };

  const addFolder = () => {
    if (!folderInput.trim()) return;
    const updated = { ...settings, scan_config: { ...settings.scan_config, folder_ids: [...settings.scan_config.folder_ids, folderInput.trim()] } };
    setSettings(updated);
    setFolderInput('');
    setHasChanges(true);
  };

  const removeFolder = (idx: number) => {
    const updated = { ...settings, scan_config: { ...settings.scan_config, folder_ids: settings.scan_config.folder_ids.filter((_, i) => i !== idx) } };
    setSettings(updated);
    setHasChanges(true);
  };

  const updateOAuth = (field: string, value: string) => {
    setSettings(s => ({ ...s, oauth2_config: { ...s.oauth2_config!, [field]: value } }));
    setHasChanges(true);
  };

  const backLink = (
    <button
      type="button"
      onClick={onBack}
      className="inline-flex items-center gap-1 rounded text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Icon name="chevron-left" className="h-3.5 w-3.5" /> Back
    </button>
  );

  if (loading) {
    return (
      <div className="space-y-6 p-4 sm:p-6" aria-busy="true">
        {backLink}
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-2"><Skeleton className="h-5 w-48" /><Skeleton className="h-4 w-72 max-w-full" /></div>
        </div>
        <Skeleton className="h-10 w-full" />
        {[0, 1, 2].map(i => <Skeleton key={i} className="h-24 w-full" />)}
      </div>
    );
  }

  const folders = settings.scan_config.folder_ids;

  return (
    <div className="space-y-5 p-4 sm:p-6">
      {backLink}

      <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="flex min-w-0 items-start gap-3">
          <SystemLogo system="google_drive" tile size="md" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <h2 className="text-xl font-medium tracking-tight text-foreground">Google Drive connector</h2>
              {testResult && (
                <StatusPill tone={testResult.success ? 'success' : 'danger'} variant="soft">
                  {testResult.success ? `Connected, ${testResult.files_found.toLocaleString()} files` : 'Test failed'}
                </StatusPill>
              )}
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Sign-in with Google, the folders to read and how documents are processed.
              {settings.last_updated && <> Last saved {new Date(settings.last_updated).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}.</>}
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={testConnection} disabled={testing}>
          <Icon name={testing ? 'spinner' : 'play'} className={cn('h-3.5 w-3.5', testing && 'animate-spin')} />
          {testing ? 'Testing' : 'Test connection'}
        </Button>
      </header>

      {error && <InlineError>{error}</InlineError>}

      <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)}>
        <TabsList variant="line">
          <TabsTrigger value="settings">Settings</TabsTrigger>
          <TabsTrigger value="diagnostics">Diagnostics</TabsTrigger>
        </TabsList>

        <TabsContent value="diagnostics" className="mt-6">
          {tab === 'diagnostics' && <GoogleDriveDiagnostics />}
        </TabsContent>

        <TabsContent value="settings" className="mt-4">
          <Block title="Sign-in with Google" description="The Google Cloud app this connector uses to read Drive on your behalf.">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Client ID" htmlFor="gdrive-client-id">
                <Input id="gdrive-client-id" value={settings.oauth2_config?.client_id || ''} onChange={e => updateOAuth('client_id', e.target.value)} placeholder="xxxxx.apps.googleusercontent.com" className="font-mono" />
              </Field>
              <Field label="Client secret" htmlFor="gdrive-client-secret" hint="A stored secret is not shown here.">
                <Input id="gdrive-client-secret" type="password" autoComplete="off" value={settings.oauth2_config?.client_secret || ''} onChange={e => updateOAuth('client_secret', e.target.value)} placeholder="Enter a new secret" className="font-mono" />
              </Field>
              <Field label="Redirect address" htmlFor="gdrive-redirect" className="sm:col-span-2">
                <Input id="gdrive-redirect" value={settings.oauth2_config?.redirect_uri || ''} onChange={e => updateOAuth('redirect_uri', e.target.value)} placeholder="http://localhost:3000/gdrive/callback" className="font-mono" />
              </Field>
            </div>
            <Button variant="outline" className="mt-4" onClick={startOAuth} disabled={!settings.oauth2_config?.client_id}>
              <SystemLogo system="google" size="sm" /> Authorize with Google
            </Button>
          </Block>

          <Block title="Folders" description="Drive folders the connector reads documents from.">
            <div className="flex gap-2">
              <Input
                value={folderInput}
                onChange={e => setFolderInput(e.target.value)}
                placeholder="Paste a Drive folder ID"
                aria-label="Drive folder ID"
                className="font-mono"
                onKeyDown={e => e.key === 'Enter' && addFolder()}
              />
              <Button variant="outline" className="shrink-0" onClick={addFolder}>
                <Icon name="plus" className="h-3.5 w-3.5" /> Add
              </Button>
            </div>
            {folders.length > 0 ? (
              <ul className="mt-3 border-t border-border">
                {folders.map((fid, i) => (
                  <li key={i} className="flex items-center gap-3 border-b border-border py-2">
                    <Icon name="folder" className="h-4 w-4 shrink-0 text-subtle-foreground" />
                    <span className="min-w-0 flex-1 truncate font-mono text-xs text-foreground" title={fid}>{fid}</span>
                    <Button variant="ghost" size="sm" className="h-7 w-7 shrink-0 p-0 text-muted-foreground" aria-label={`Remove folder ${fid}`} onClick={() => removeFolder(i)}>
                      <Icon name="close" className="h-3.5 w-3.5" />
                    </Button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">No folders yet. Add a folder ID to start reading documents.</p>
            )}
            <div className="mt-4 flex items-center gap-2.5">
              <Switch
                id="gdrive-subfolders"
                checked={settings.scan_config.include_subfolders}
                onCheckedChange={v => { setSettings(s => ({ ...s, scan_config: { ...s.scan_config, include_subfolders: v } })); setHasChanges(true); }}
              />
              <label htmlFor="gdrive-subfolders" className="text-sm text-foreground">Include subfolders</label>
            </div>
          </Block>

          <Block title="Processing" description="What happens to the files that are found.">
            <SwitchRow
              id="gdrive-ocr"
              label="Read text from documents"
              hint="Extract the content of downloaded files with OCR and the language model."
              checked={settings.enable_ocr_extraction}
              onChange={v => { setSettings(s => ({ ...s, enable_ocr_extraction: v })); setHasChanges(true); }}
            />
            <SwitchRow
              id="gdrive-autoscan"
              label="Scan on a schedule"
              hint="Look for new files in the folders at regular times."
              checked={settings.enable_auto_scan}
              onChange={v => { setSettings(s => ({ ...s, enable_auto_scan: v })); setHasChanges(true); }}
            />
            <div className="grid gap-4 pt-4 sm:grid-cols-2">
              {settings.enable_auto_scan && (
                <Field label="Schedule (cron)" htmlFor="gdrive-schedule" hint="For example 0 */6 * * * runs every 6 hours.">
                  <Input id="gdrive-schedule" value={settings.scan_schedule} onChange={e => { setSettings(s => ({ ...s, scan_schedule: e.target.value })); setHasChanges(true); }} placeholder="0 */6 * * *" className="font-mono" />
                </Field>
              )}
              <Field label="Most files per scan" htmlFor="gdrive-max-files">
                <Input
                  id="gdrive-max-files"
                  type="number"
                  className="num"
                  value={settings.scan_config.max_files_per_scan}
                  onChange={e => { setSettings(s => ({ ...s, scan_config: { ...s.scan_config, max_files_per_scan: parseInt(e.target.value) || 100 } })); setHasChanges(true); }}
                />
              </Field>
            </div>
          </Block>

          <div className="flex flex-wrap items-center gap-2 pt-5">
            <Button onClick={saveSettings} disabled={!hasChanges || saving}>
              {saving && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
              {saving ? 'Saving' : 'Save settings'}
            </Button>
            <Button variant="ghost" onClick={fetchSettings} disabled={loading || saving}>
              <Icon name="refresh" className="h-3.5 w-3.5" /> Reload
            </Button>
            <Button variant="ghost" onClick={() => { setSettings(DEFAULT_SETTINGS); setHasChanges(true); }}>
              Reset to defaults
            </Button>
            {hasChanges && <span className="text-sm text-muted-foreground">Unsaved changes</span>}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
