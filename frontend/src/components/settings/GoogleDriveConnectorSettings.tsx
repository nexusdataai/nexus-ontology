import React, { useState, useEffect, useCallback } from 'react';
import {
  HardDrive, ArrowLeft, Save, RotateCcw, Play, Loader2,
  CheckCircle2, XCircle, AlertCircle, RefreshCw, FolderOpen,
  FileText, Activity,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
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
        toast.success('OAuth window opened. Complete authorization in the new tab.');
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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <ArrowLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          <div className="p-2 rounded-xl bg-gradient-to-br from-red-500 to-yellow-500">
            <HardDrive className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold">Google Drive Connector</h2>
            <p className="text-xs text-muted-foreground">Configure OAuth2, folders, and extraction settings</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {testResult && (
            <Badge variant={testResult.success ? 'default' : 'destructive'}>
              {testResult.success ? <CheckCircle2 className="h-3 w-3 mr-1" /> : <XCircle className="h-3 w-3 mr-1" />}
              {testResult.success ? `Connected (${testResult.files_found} files)` : 'Failed'}
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={testConnection} disabled={testing}>
            {testing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Play className="h-3.5 w-3.5 mr-1" />}
            Test
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex gap-1 border-b">
        <button onClick={() => setTab('settings')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'settings' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
          <HardDrive className="h-3.5 w-3.5" /> Settings
        </button>
        <button onClick={() => setTab('diagnostics')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'diagnostics' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
          <Activity className="h-3.5 w-3.5" /> Diagnostics
        </button>
      </div>

      {tab === 'diagnostics' ? (
        <GoogleDriveDiagnostics />
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2"><HardDrive className="h-4 w-4" /> OAuth2 Authentication</CardTitle>
              <CardDescription>Configure Google Cloud OAuth2 credentials for Drive API access</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Client ID</Label>
                  <Input value={settings.oauth2_config?.client_id || ''} onChange={e => updateOAuth('client_id', e.target.value)} placeholder="xxxxx.apps.googleusercontent.com" />
                </div>
                <div>
                  <Label>Client Secret</Label>
                  <Input type="password" value={settings.oauth2_config?.client_secret || ''} onChange={e => updateOAuth('client_secret', e.target.value)} placeholder="********" />
                </div>
                <div>
                  <Label>Redirect URI</Label>
                  <Input value={settings.oauth2_config?.redirect_uri || ''} onChange={e => updateOAuth('redirect_uri', e.target.value)} placeholder="http://localhost:3000/gdrive/callback" />
                </div>
                <div className="flex items-end">
                  <Button variant="outline" onClick={startOAuth} disabled={!settings.oauth2_config?.client_id}>
                    <HardDrive className="h-3.5 w-3.5 mr-1" /> Authorize with Google
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2"><FolderOpen className="h-4 w-4" /> Folder Configuration</CardTitle>
              <CardDescription>Specify Google Drive folder IDs to scan for documents</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input value={folderInput} onChange={e => setFolderInput(e.target.value)} placeholder="Enter Google Drive folder ID" onKeyDown={e => e.key === 'Enter' && addFolder()} />
                <Button variant="outline" size="sm" onClick={addFolder}>Add</Button>
              </div>
              {settings.scan_config.folder_ids.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {settings.scan_config.folder_ids.map((fid, i) => (
                    <Badge key={i} variant="outline" className="text-xs gap-1">
                      <FolderOpen className="h-3 w-3" /> {fid}
                      <button onClick={() => removeFolder(i)} className="ml-1 text-muted-foreground hover:text-foreground">&times;</button>
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No folders configured. Add folder IDs to scan.</p>
              )}
              <div className="flex items-center gap-3 pt-2">
                <Switch checked={settings.scan_config.include_subfolders} onCheckedChange={v => { setSettings(s => ({ ...s, scan_config: { ...s.scan_config, include_subfolders: v } })); setHasChanges(true); }} />
                <Label className="text-xs">Include subfolders</Label>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2"><FileText className="h-4 w-4" /> Processing Options</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label>OCR + LLM Extraction</Label>
                  <p className="text-xs text-muted-foreground">Run document extraction on downloaded files</p>
                </div>
                <Switch checked={settings.enable_ocr_extraction} onCheckedChange={v => { setSettings(s => ({ ...s, enable_ocr_extraction: v })); setHasChanges(true); }} />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label>Auto-Scan</Label>
                  <p className="text-xs text-muted-foreground">Periodically scan configured folders for new files</p>
                </div>
                <Switch checked={settings.enable_auto_scan} onCheckedChange={v => { setSettings(s => ({ ...s, enable_auto_scan: v })); setHasChanges(true); }} />
              </div>
              {settings.enable_auto_scan && (
                <div>
                  <Label>Scan Schedule (cron)</Label>
                  <Input value={settings.scan_schedule} onChange={e => { setSettings(s => ({ ...s, scan_schedule: e.target.value })); setHasChanges(true); }} placeholder="0 */6 * * *" />
                </div>
              )}
              <div>
                <Label>Max Files Per Scan</Label>
                <Input type="number" value={settings.scan_config.max_files_per_scan} onChange={e => { setSettings(s => ({ ...s, scan_config: { ...s.scan_config, max_files_per_scan: parseInt(e.target.value) || 100 } })); setHasChanges(true); }} />
              </div>
            </CardContent>
          </Card>

          <div className="flex items-center justify-between">
            <div className="flex gap-3">
              <Button variant="ghost" onClick={() => { setSettings(DEFAULT_SETTINGS); setHasChanges(true); }}>
                <RotateCcw className="h-4 w-4 mr-1" /> Reset
              </Button>
              <Button variant="ghost" onClick={fetchSettings} disabled={loading || saving}>
                <RefreshCw className="h-4 w-4 mr-1" /> Reload
              </Button>
            </div>
            <Button onClick={saveSettings} disabled={!hasChanges || saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Save className="h-4 w-4 mr-1" />}
              Save Settings
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
