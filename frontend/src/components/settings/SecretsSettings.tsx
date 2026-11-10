/**
 * Secrets
 *
 * Administrators see which credentials are stored and replace their values.
 * Values are never shown in full. Layout: heading row, one quiet note, then
 * one table; editing opens a side sheet.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { DetailSheet, Field, InlineError, StatusPill, TableShell } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { SystemLogo, resolveSystem } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
import {
  ssmConfigService,
  type SecretInfo,
  type SecretDetail,
} from '@/services/ssmConfigService';

interface EditSecretState {
  isOpen: boolean;
  secret: SecretDetail | null;
  values: Record<string, string>;
  showValues: Record<string, boolean>;
  isSaving: boolean;
}

const SOURCE_SYSTEMS = new Set(['salesforce', 'sap', 'oracle', 'google_drive', 'microsoft', 'slack', 'mysql']);

/** The source system a secret belongs to, if its name or label says so. */
const systemOfSecret = (secret: { name: string; label: string }): string | null => {
  const candidates = [secret.name, secret.name.split(/[-_]/)[0], secret.label];
  for (const c of candidates) {
    const { key, def } = resolveSystem(c);
    if (def && SOURCE_SYSTEMS.has(key)) return key;
  }
  return null;
};

const formatDate = (iso: string | null) => {
  if (!iso) return 'Never';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? 'Unknown' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

const prettyConnector = (id: string) => id.replace(/[-_]+/g, ' ').replace(/^\w/, c => c.toUpperCase());

const SecretsSettings: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [secrets, setSecrets] = useState<SecretInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editState, setEditState] = useState<EditSecretState>({
    isOpen: false,
    secret: null,
    values: {},
    showValues: {},
    isSaving: false,
  });

  // Fetch secrets list
  const fetchSecrets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await ssmConfigService.getSecretsList();
      setSecrets(response.secrets);
    } catch (err) {
      console.error('Failed to fetch secrets:', err);
      setError('Failed to fetch secrets list. Backend may be unavailable.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSecrets();
  }, [fetchSecrets]);

  // Open edit sheet
  const handleEditSecret = async (secretName: string) => {
    try {
      setError(null);
      const detail = await ssmConfigService.getSecret(secretName);

      // Initialize values from masked values (empty for editing)
      const values: Record<string, string> = {};
      const showValues: Record<string, boolean> = {};
      detail.keys.forEach(key => {
        values[key] = ''; // Start with empty for security
        showValues[key] = false;
      });

      setEditState({
        isOpen: true,
        secret: detail,
        values,
        showValues,
        isSaving: false,
      });
    } catch (err) {
      console.error('Failed to fetch secret details:', err);
      setError('Failed to fetch secret details.');
    }
  };

  // Handle value change in the edit sheet
  const handleValueChange = (key: string, value: string) => {
    setEditState(prev => ({
      ...prev,
      values: { ...prev.values, [key]: value },
    }));
  };

  // Toggle value visibility
  const toggleShowValue = (key: string) => {
    setEditState(prev => ({
      ...prev,
      showValues: { ...prev.showValues, [key]: !prev.showValues[key] },
    }));
  };

  // Save secret
  const handleSaveSecret = async () => {
    if (!editState.secret) return;

    // Filter out empty values
    const nonEmptyValues: Record<string, string> = {};
    Object.entries(editState.values).forEach(([key, value]) => {
      if (value.trim()) {
        nonEmptyValues[key] = value;
      }
    });

    if (Object.keys(nonEmptyValues).length === 0) {
      setError('Please enter at least one value to update.');
      return;
    }

    setEditState(prev => ({ ...prev, isSaving: true }));
    setError(null);

    try {
      await ssmConfigService.updateSecret(editState.secret.name, nonEmptyValues);

      setSuccess(`Secret "${editState.secret.label}" updated.`);
      setEditState({
        isOpen: false,
        secret: null,
        values: {},
        showValues: {},
        isSaving: false,
      });

      // Refresh secrets list
      await fetchSecrets();

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      console.error('Failed to save secret:', err);
      setError(err.message || 'Failed to save secret.');
      setEditState(prev => ({ ...prev, isSaving: false }));
    }
  };

  // Close edit sheet
  const handleCloseDialog = () => {
    setEditState({
      isOpen: false,
      secret: null,
      values: {},
      showValues: {},
      isSaving: false,
    });
  };

  // Go to the connector that owns a managed secret
  const openConnector = (secret: SecretInfo) => {
    const searchParams = new URLSearchParams(location.search);
    searchParams.set('view', 'tools');
    // Map managed_by to tool ID
    const toolId = secret.managed_by === 'webex-connector' ? 'webex-connector' : secret.managed_by;
    searchParams.set('tool', toolId as string);
    navigate(`${location.pathname}?${searchParams.toString()}`);
  };

  // Status of a secret
  const getStatusBadge = (secret: SecretInfo) => {
    if (secret.managed_by) return <StatusPill tone="info">Managed by connector</StatusPill>;
    if (secret.exists) return <StatusPill tone="success">Configured</StatusPill>;
    return <StatusPill tone="warning">Missing</StatusPill>;
  };

  const missing = secrets.filter(s => !s.exists && !s.managed_by).length;
  const editing = editState.secret;
  const editingSystem = editing ? systemOfSecret(editing) : null;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h2 className="text-xl font-medium tracking-tight text-foreground">Secrets</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            {secrets.length === 0
              ? 'Credentials the platform uses to reach your systems, stored encrypted.'
              : <>
                  <span className="num font-medium text-foreground">{secrets.length}</span> credentials stored encrypted
                  {missing > 0 && <>, <span className="num font-medium text-foreground">{missing}</span> not set yet</>}.
                </>}
          </p>
        </div>
        <Button variant="outline" onClick={fetchSecrets} disabled={loading}>
          <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
        </Button>
      </header>

      <p className="flex items-start gap-2 text-sm text-muted-foreground">
        <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0 text-subtle-foreground" />
        <span className="max-w-3xl">
          Values are never shown in full. To change one, enter the complete new value. Secrets managed by a connector are changed in that connector.
        </span>
      </p>

      {error && !editState.isOpen && (
        <InlineError onRetry={secrets.length === 0 ? fetchSecrets : undefined}>{error}</InlineError>
      )}

      {success && (
        <p role="status" className="flex items-center gap-2 text-sm text-foreground">
          <Icon name="check-circle" className="h-4 w-4 text-success" />
          {success}
        </p>
      )}

      {loading && secrets.length === 0 ? (
        <div className="space-y-px overflow-hidden rounded-xl border border-border" aria-busy="true">
          {[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-16 w-full rounded-none" />)}
        </div>
      ) : secrets.length === 0 && !error ? (
        <EmptyState icon="lock" title="No secrets defined" description="Credentials appear here once a connector or integration needs them." />
      ) : secrets.length > 0 ? (
        <TableShell>
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr>
                {['Secret', 'Keys', 'Last changed', 'Status', ''].map((h, i) => (
                  <th key={i} scope="col" className="whitespace-nowrap border-b border-border bg-surface-2 px-5 py-2.5 text-left text-xs font-medium text-muted-foreground">
                    {h || <span className="sr-only">Actions</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {secrets.map((secret, i) => {
                const system = systemOfSecret(secret);
                return (
                  <tr key={secret.name} className="rise border-b border-border transition-colors last:border-b-0 hover:bg-surface-2/60" style={{ '--i': i } as React.CSSProperties}>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        {system ? (
                          <SystemLogo system={system} tile size="sm" />
                        ) : (
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-card text-subtle-foreground">
                            <Icon name="key" className="h-4 w-4" />
                          </span>
                        )}
                        <div className="min-w-0">
                          <div className="font-medium text-foreground">{secret.label}</div>
                          <div className="text-xs text-muted-foreground">{secret.description}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span className="font-mono text-xs text-muted-foreground">{secret.keys.join(', ')}</span>
                    </td>
                    <td className="num whitespace-nowrap px-5 py-3 text-muted-foreground">{formatDate(secret.last_modified)}</td>
                    <td className="whitespace-nowrap px-5 py-3">
                      {getStatusBadge(secret)}
                      {secret.managed_by && <div className="mt-0.5 text-xs text-muted-foreground">{prettyConnector(secret.managed_by)}</div>}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {secret.managed_by ? (
                        <Button variant="ghost" size="sm" onClick={() => openConnector(secret)}>
                          Open connector <Icon name="arrow-right" className="h-3.5 w-3.5" />
                        </Button>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => handleEditSecret(secret.name)}>
                          <Icon name="edit" className="h-3.5 w-3.5" /> {secret.exists ? 'Edit' : 'Set'}
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableShell>
      ) : null}

      {/* Edit secret */}
      <DetailSheet
        open={editState.isOpen}
        onOpenChange={(open) => !open && handleCloseDialog()}
        title={
          <span className="flex items-center gap-2.5">
            {editingSystem && <SystemLogo system={editingSystem} size="md" />}
            {editing?.label || 'Secret'}
          </span>
        }
        description="Enter new values. A field left empty keeps its stored value."
        footer={
          <>
            <Button variant="outline" onClick={handleCloseDialog} disabled={editState.isSaving}>
              Cancel
            </Button>
            <Button onClick={handleSaveSecret} disabled={editState.isSaving}>
              {editState.isSaving && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
              {editState.isSaving ? 'Saving' : 'Save secret'}
            </Button>
          </>
        }
      >
        <div className="space-y-5">
          {editing?.description && <p className="text-sm text-muted-foreground">{editing.description}</p>}

          {editing?.keys.map((key) => {
            const id = `secret-${key}`;
            const shown = !!editState.showValues[key];
            const masked = editing.values[key];
            return (
              <Field
                key={key}
                label={key}
                htmlFor={id}
                hint={masked ? <>Stored value <span className="font-mono text-muted-foreground">{masked}</span></> : 'No value stored yet'}
              >
                <div className="relative">
                  <Input
                    id={id}
                    type={shown ? 'text' : 'password'}
                    autoComplete="off"
                    value={editState.values[key] || ''}
                    onChange={(e) => handleValueChange(key, e.target.value)}
                    placeholder="Enter the new value"
                    className="pr-16 font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => toggleShowValue(key)}
                    aria-pressed={shown}
                    aria-label={shown ? `Hide ${key}` : `Show ${key}`}
                    className="absolute right-1.5 top-1/2 h-6 -translate-y-1/2 rounded px-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {shown ? 'Hide' : 'Show'}
                  </button>
                </div>
              </Field>
            );
          })}

          {error && editState.isOpen && <InlineError>{error}</InlineError>}
        </div>
      </DetailSheet>
    </div>
  );
};

export default SecretsSettings;
