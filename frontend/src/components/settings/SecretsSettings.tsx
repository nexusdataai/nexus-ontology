/**
 * Secrets Settings Component
 * 
 * Allows administrators to view and manage secrets stored in AWS Secrets Manager.
 * Secret values are always masked for security.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Key,
  Eye,
  EyeOff,
  Save,
  ExternalLink,
  Lock,
  Shield,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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

  // Open edit dialog
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

  // Handle value change in edit dialog
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
      
      setSuccess(`Secret "${editState.secret.label}" updated successfully.`);
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

  // Close edit dialog
  const handleCloseDialog = () => {
    setEditState({
      isOpen: false,
      secret: null,
      values: {},
      showValues: {},
      isSaving: false,
    });
  };

  // Get status badge for secret
  const getStatusBadge = (secret: SecretInfo) => {
    if (secret.managed_by) {
      return (
        <Badge variant="outline" className="bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800">
          Managed by {secret.managed_by}
        </Badge>
      );
    }
    if (secret.exists) {
      return (
        <Badge variant="outline" className="bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800">
          Configured
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="bg-muted text-muted-foreground border-border">
        Not Set
      </Badge>
    );
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Secrets Management
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading secrets...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Secrets Management
          </CardTitle>
          <CardDescription>
            Manage sensitive credentials stored in AWS Secrets Manager. Values are always encrypted and masked for security.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Alerts */}
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert className="mb-4 border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20">
              <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
              <AlertDescription className="text-green-800 dark:text-green-300">{success}</AlertDescription>
            </Alert>
          )}

          {/* Security Notice */}
          <div className="p-4 bg-amber-50 dark:bg-amber-900/15 rounded-lg border border-amber-100 dark:border-amber-800 mb-4">
            <div className="flex items-start gap-2">
              <Shield className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-800 dark:text-amber-300">Security Notice</p>
                <p className="text-sm text-amber-700 dark:text-amber-400">
                  Secret values are never displayed in full. When editing, you must enter the complete new value.
                  Some secrets are managed by integration connectors and cannot be edited here directly.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={fetchSecrets}
              disabled={loading}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Secrets List */}
      <div className="grid gap-4">
        {secrets.map((secret) => (
          <Card key={secret.name}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-muted rounded-lg">
                    <Lock className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="font-medium">{secret.label}</h3>
                    <p className="text-sm text-muted-foreground">{secret.description}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-muted-foreground">
                        Keys: {secret.keys.join(', ')}
                      </span>
                      {secret.last_modified && (
                        <span className="text-xs text-muted-foreground">
                          | Last modified: {new Date(secret.last_modified).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {getStatusBadge(secret)}
                  {secret.managed_by ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex items-center gap-2"
                      onClick={() => {
                        // Navigate directly to the specific connector tool
                        const searchParams = new URLSearchParams(location.search);
                        searchParams.set('view', 'tools');
                        // Map managed_by to tool ID
                        const toolId = secret.managed_by === 'webex-connector' ? 'webex-connector' : secret.managed_by;
                        searchParams.set('tool', toolId);
                        navigate(`${location.pathname}?${searchParams.toString()}`);
                      }}
                    >
                      <ExternalLink className="h-4 w-4" />
                      Go to Connector
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditSecret(secret.name)}
                      className="flex items-center gap-2"
                    >
                      <Key className="h-4 w-4" />
                      Edit
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Edit Secret Dialog */}
      <Dialog open={editState.isOpen} onOpenChange={(open) => !open && handleCloseDialog()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Secret: {editState.secret?.label}</DialogTitle>
            <DialogDescription>
              Enter new values for the secret keys. Leave fields empty to keep existing values.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {editState.secret?.keys.map((key) => (
              <div key={key} className="space-y-2">
                <Label htmlFor={key}>{key}</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Input
                      id={key}
                      type={editState.showValues[key] ? 'text' : 'password'}
                      value={editState.values[key] || ''}
                      onChange={(e) => handleValueChange(key, e.target.value)}
                      placeholder={`Enter new ${key}`}
                      className="pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                      onClick={() => toggleShowValue(key)}
                    >
                      {editState.showValues[key] ? (
                        <EyeOff className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <Eye className="h-4 w-4 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                </div>
                {editState.secret?.values[key] && (
                  <p className="text-xs text-muted-foreground">
                    Current (masked): <code className="bg-muted px-1 rounded">{editState.secret.values[key]}</code>
                  </p>
                )}
              </div>
            ))}
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseDialog} disabled={editState.isSaving}>
              Cancel
            </Button>
            <Button onClick={handleSaveSecret} disabled={editState.isSaving}>
              {editState.isSaving ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Secret
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SecretsSettings;
