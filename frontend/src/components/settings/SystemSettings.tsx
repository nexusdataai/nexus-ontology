/**
 * System Settings Component
 * 
 * Allows administrators to view and edit SSM parameters grouped by category.
 * Changes are persisted to AWS SSM Parameter Store.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Server,
  Shield,
  Phone,
  Database,
  Layers,
  Activity,
  Settings2,
  ChevronDown,
  ChevronRight,
  Save,
  RotateCcw,
  Trash2,
  Search,
  Building2,
  Factory,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  ssmConfigService,
  type ConfigParametersResponse,
  type ParameterCategory,
  type ParameterValue,
  type EnvironmentInfo,
} from '@/services/ssmConfigService';

// Icon mapping for categories
const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  server: <Settings2 className="h-4 w-4" />,
  cognito: <Shield className="h-4 w-4" />,
  'wxcc-query': <Search className="h-4 w-4" />,
  wxcc: <Phone className="h-4 w-4" />,
  data_source_mode: <Layers className="h-4 w-4" />,
  sfdc: <Database className="h-4 w-4" />,
  'oracle-erp': <Building2 className="h-4 w-4" />,
  sap: <Factory className="h-4 w-4" />,
  s3: <Database className="h-4 w-4" />,
  dynamodb: <Database className="h-4 w-4" />,
  glue: <Layers className="h-4 w-4" />,
  cloudwatch: <Activity className="h-4 w-4" />,
};

interface CategoryState {
  isOpen: boolean;
  isModified: boolean;
  isSaving: boolean;
  values: Record<string, string>;
  originalValues: Record<string, string>;
}

const SystemSettings: React.FC = () => {
  const [parameters, setParameters] = useState<ConfigParametersResponse | null>(null);
  const [environmentInfo, setEnvironmentInfo] = useState<EnvironmentInfo | null>(null);
  const [categoryStates, setCategoryStates] = useState<Record<string, CategoryState>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [invalidatingCache, setInvalidatingCache] = useState(false);

  // Fetch parameters and environment info
  const fetchParameters = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [paramsResponse, envResponse] = await Promise.all([
        ssmConfigService.getAllParameters(),
        ssmConfigService.getEnvironmentInfo(),
      ]);

      setParameters(paramsResponse);
      setEnvironmentInfo(envResponse);

      // Initialize category states
      const states: Record<string, CategoryState> = {};
      Object.entries(paramsResponse.categories).forEach(([catName, category]) => {
        const values: Record<string, string> = {};
        Object.entries(category.parameters).forEach(([paramName, param]) => {
          values[paramName] = param.value;
        });
        states[catName] = {
          isOpen: catName === 'server', // Open server by default
          isModified: false,
          isSaving: false,
          values: { ...values },
          originalValues: { ...values },
        };
      });
      setCategoryStates(states);
    } catch (err) {
      console.error('Failed to fetch parameters:', err);
      setError('Failed to fetch system parameters. Backend may be unavailable.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchParameters();
  }, [fetchParameters]);

  // Handle parameter value change
  const handleValueChange = (category: string, paramName: string, value: string) => {
    setCategoryStates(prev => {
      const catState = prev[category];
      const newValues = { ...catState.values, [paramName]: value };
      const isModified = Object.keys(newValues).some(
        key => newValues[key] !== catState.originalValues[key]
      );
      return {
        ...prev,
        [category]: {
          ...catState,
          values: newValues,
          isModified,
        },
      };
    });
  };

  // Handle category toggle
  const handleCategoryToggle = (category: string) => {
    setCategoryStates(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        isOpen: !prev[category].isOpen,
      },
    }));
  };

  // Save category parameters
  const handleSaveCategory = async (category: string) => {
    const catState = categoryStates[category];
    if (!catState.isModified) return;

    setCategoryStates(prev => ({
      ...prev,
      [category]: { ...prev[category], isSaving: true },
    }));
    setError(null);
    setSuccess(null);

    try {
      // Find changed parameters
      const changedParams = Object.entries(catState.values).filter(
        ([key, value]) => value !== catState.originalValues[key]
      );

      // Update each changed parameter
      for (const [paramName, value] of changedParams) {
        await ssmConfigService.updateParameter(category, paramName, value);
      }

      // Update state
      setCategoryStates(prev => ({
        ...prev,
        [category]: {
          ...prev[category],
          isSaving: false,
          isModified: false,
          originalValues: { ...prev[category].values },
        },
      }));

      setSuccess(`${parameters?.categories[category].label} settings saved successfully.`);

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Failed to save parameters:', err);
      setError(`Failed to save ${parameters?.categories[category].label} settings.`);
      setCategoryStates(prev => ({
        ...prev,
        [category]: { ...prev[category], isSaving: false },
      }));
    }
  };

  // Reset category to original values
  const handleResetCategory = (category: string) => {
    setCategoryStates(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        values: { ...prev[category].originalValues },
        isModified: false,
      },
    }));
  };

  // Invalidate cache
  const handleInvalidateCache = async () => {
    setInvalidatingCache(true);
    setError(null);
    try {
      await ssmConfigService.invalidateCache();
      setSuccess('Configuration cache invalidated. Values will be reloaded on next access.');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Failed to invalidate cache:', err);
      setError('Failed to invalidate cache.');
    } finally {
      setInvalidatingCache(false);
    }
  };

  // Render parameter input based on type
  const renderParameterInput = (
    category: string,
    paramName: string,
    param: ParameterValue,
    value: string
  ) => {
    const isModified = value !== categoryStates[category]?.originalValues[paramName];

    // Phase 2 (data-source-mode): render the simulator|real choice as a
    // 2-button segmented pill instead of a dropdown so the active mode
    // is obvious at a glance. Triggered by the category name only;
    // every other 'select' parameter keeps the standard dropdown.
    if (
      param.type === 'select' &&
      category === 'data_source_mode' &&
      param.options?.length === 2 &&
      param.options.includes('simulator') &&
      param.options.includes('real')
    ) {
      const opts: string[] = ['simulator', 'real'];
      return (
        <div className={`inline-flex rounded-md border ${isModified ? 'border-amber-400' : 'border-border'} overflow-hidden`}>
          {opts.map((opt) => {
            const active = value === opt;
            return (
              <button
                key={opt}
                type="button"
                onClick={() => handleValueChange(category, paramName, opt)}
                className={`px-3 py-1 text-xs font-medium transition-colors ${
                  active
                    ? opt === 'simulator'
                      ? 'bg-green-500/20 text-green-300'
                      : 'bg-amber-500/20 text-amber-300'
                    : 'bg-transparent text-muted-foreground hover:bg-muted/40'
                }`}
              >
                {opt}
              </button>
            );
          })}
        </div>
      );
    }

    switch (param.type) {
      case 'select':
        return (
          <Select
            value={value}
            onValueChange={(v) => handleValueChange(category, paramName, v)}
          >
            <SelectTrigger className={isModified ? 'border-amber-400' : ''}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {param.options?.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      case 'boolean':
        return (
          <div className="flex items-center gap-2">
            <Switch
              checked={value === 'true'}
              onCheckedChange={(checked) =>
                handleValueChange(category, paramName, checked ? 'true' : 'false')
              }
            />
            <span className={`text-sm ${isModified ? 'text-amber-600 dark:text-amber-400 font-medium' : 'text-muted-foreground'}`}>
              {value === 'true' ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        );

      case 'number':
        return (
          <Input
            type="number"
            value={value}
            onChange={(e) => handleValueChange(category, paramName, e.target.value)}
            className={isModified ? 'border-amber-400' : ''}
          />
        );

      default:
        return (
          <Input
            type="text"
            value={value}
            onChange={(e) => handleValueChange(category, paramName, e.target.value)}
            className={isModified ? 'border-amber-400' : ''}
          />
        );
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            System Settings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading system parameters...</span>
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
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Settings2 className="h-5 w-5" />
                System Settings
              </CardTitle>
              <CardDescription>
                Configure system parameters stored in AWS SSM Parameter Store
              </CardDescription>
            </div>
            {environmentInfo && (
              <Badge variant="outline" className="text-sm">
                Environment: {environmentInfo.environment}
              </Badge>
            )}
          </div>
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

          {/* Environment Info */}
          {environmentInfo && (
            <div className="p-4 bg-muted rounded-lg border border-border mb-4">
              <div className="flex items-center gap-2 mb-2">
                <Server className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-sm text-foreground">Environment Details</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground">Environment:</span>
                  <span className="ml-1 font-medium text-foreground">{environmentInfo.environment}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Region:</span>
                  <span className="ml-1 font-medium text-foreground">{environmentInfo.region}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Platform:</span>
                  <span className="ml-1 font-medium text-foreground">
                    {environmentInfo.is_localstack ? 'LocalStack' : environmentInfo.is_aws ? 'AWS' : 'Local'}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Log Level:</span>
                  <span className="ml-1 font-medium text-foreground">{environmentInfo.log_level}</span>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={fetchParameters}
              disabled={loading}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              onClick={handleInvalidateCache}
              disabled={invalidatingCache}
              className="flex items-center gap-2"
            >
              <Trash2 className={`h-4 w-4 ${invalidatingCache ? 'animate-spin' : ''}`} />
              Invalidate Cache
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Parameter Categories */}
      {parameters && Object.entries(parameters.categories).map(([catName, category]) => {
        const catState = categoryStates[catName];
        if (!catState) return null;

        return (
          <Card key={catName}>
            <Collapsible open={catState.isOpen} onOpenChange={() => handleCategoryToggle(catName)}>
              <CollapsibleTrigger asChild>
                <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {catState.isOpen ? (
                        <ChevronDown className="h-4 w-4 text-slate-500" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-slate-500" />
                      )}
                      {CATEGORY_ICONS[catName] || <Settings2 className="h-4 w-4" />}
                      <div>
                        <CardTitle className="text-base">{category.label}</CardTitle>
                        <CardDescription className="text-sm">{category.description}</CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {catState.isModified && (
                        <Badge variant="outline" className="bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800">
                          Modified
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
              </CollapsibleTrigger>

              <CollapsibleContent>
                <CardContent className="pt-0">
                  <div className="space-y-4">
                    {Object.entries(category.parameters).map(([paramName, param]) => {
                      const value = catState.values[paramName] || '';
                      const isModified = value !== catState.originalValues[paramName];

                      return (
                        <div
                          key={paramName}
                          className={`grid grid-cols-1 md:grid-cols-3 gap-4 p-3 rounded-lg ${
                            isModified ? 'bg-amber-50 dark:bg-amber-900/10' : 'bg-muted'
                          }`}
                        >
                          <div className="space-y-1">
                            <Label className="font-medium text-sm">
                              {paramName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                            </Label>
                            <p className="text-xs text-muted-foreground">{param.description}</p>
                            <p className="text-xs text-muted-foreground">
                              Default: <code className="bg-muted px-1 rounded">{param.default}</code>
                            </p>
                          </div>
                          <div className="md:col-span-2 flex items-center">
                            {renderParameterInput(catName, paramName, param, value)}
                          </div>
                        </div>
                      );
                    })}

                    {/* Category Actions */}
                    <div className="flex gap-3 pt-2 border-t">
                      <Button
                        onClick={() => handleSaveCategory(catName)}
                        disabled={!catState.isModified || catState.isSaving}
                        className="flex items-center gap-2"
                      >
                        {catState.isSaving ? (
                          <RefreshCw className="h-4 w-4 animate-spin" />
                        ) : (
                          <Save className="h-4 w-4" />
                        )}
                        {catState.isSaving ? 'Saving...' : 'Save Changes'}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handleResetCategory(catName)}
                        disabled={!catState.isModified || catState.isSaving}
                        className="flex items-center gap-2"
                      >
                        <RotateCcw className="h-4 w-4" />
                        Reset
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Collapsible>
          </Card>
        );
      })}
    </div>
  );
};

export default SystemSettings;
