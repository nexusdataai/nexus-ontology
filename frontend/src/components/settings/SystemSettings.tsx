/**
 * System settings
 *
 * Administrators view and edit platform parameters, grouped by area.
 * Layout: environment facts and actions on top, then a master-detail:
 * the groups on the left, the selected group's parameters on the right.
 * Changes are saved per group to the parameter store.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { SystemLogo, resolveSystem } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
import {
  ssmConfigService,
  type ConfigParametersResponse,
  type ParameterValue,
  type EnvironmentInfo,
} from '@/services/ssmConfigService';

interface CategoryState {
  isOpen: boolean;
  isModified: boolean;
  isSaving: boolean;
  values: Record<string, string>;
  originalValues: Record<string, string>;
}

/** Short words that read better in capitals in a label. */
const ACRONYMS = new Set(['url', 'api', 'id', 'ttl', 'ms', 'db', 'ocr', 'sap', 'erp', 'crm', 'sso', 'arn', 'kms', 'ssl', 'tls', 'uri', 'ip', 's3', 'aws', 'odata']);

/** "sync_interval_minutes" becomes "Sync interval minutes". */
const humanise = (key: string) =>
  key
    .split(/[-_]+/)
    .filter(Boolean)
    .map((w, i) => (ACRONYMS.has(w.toLowerCase()) ? (w.toLowerCase() === 'odata' ? 'OData' : w.toUpperCase()) : i === 0 ? w.charAt(0).toUpperCase() + w.slice(1) : w))
    .join(' ');

/** Only real source systems get a logo; platform groups stay plain. */
const SOURCE_SYSTEMS = new Set(['salesforce', 'sap', 'oracle', 'google_drive', 'microsoft', 'slack', 'mysql']);
const systemOf = (key: string): string | null => {
  const { key: resolved, def } = resolveSystem(key);
  return def && SOURCE_SYSTEMS.has(resolved) ? key : null;
};

const SystemSettings: React.FC = () => {
  const [parameters, setParameters] = useState<ConfigParametersResponse | null>(null);
  const [environmentInfo, setEnvironmentInfo] = useState<EnvironmentInfo | null>(null);
  const [categoryStates, setCategoryStates] = useState<Record<string, CategoryState>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [invalidatingCache, setInvalidatingCache] = useState(false);
  // Which group is shown on the right (view state only).
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

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

      setSuccess(`${parameters?.categories[category].label} settings saved.`);

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
      setSuccess('Cache cleared. Values are read again the next time they are needed.');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Failed to invalidate cache:', err);
      setError('Failed to clear the cache.');
    } finally {
      setInvalidatingCache(false);
    }
  };

  // Render parameter input based on type
  const renderParameterInput = (
    category: string,
    paramName: string,
    param: ParameterValue,
    value: string,
    inputId: string,
  ) => {
    // The simulator / real choice is a two-way switch so the active mode is
    // obvious at a glance. Triggered by the category name only; every other
    // 'select' parameter keeps the standard dropdown.
    if (
      param.type === 'select' &&
      category === 'data_source_mode' &&
      param.options?.length === 2 &&
      param.options.includes('simulator') &&
      param.options.includes('real')
    ) {
      const opts: { value: string; label: string }[] = [
        { value: 'simulator', label: 'Simulator' },
        { value: 'real', label: 'Real system' },
      ];
      return (
        <div role="radiogroup" aria-label={humanise(paramName)} className="inline-flex h-9 items-center gap-0.5 rounded-lg border border-border bg-surface-2 p-0.5">
          {opts.map((opt) => {
            const active = value === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => handleValueChange(category, paramName, opt.value)}
                className={cn(
                  'h-full rounded-md px-3 text-sm font-medium transition-colors duration-200 ease-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  active ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      );
    }

    switch (param.type) {
      case 'select':
        return (
          <Select value={value} onValueChange={(v) => handleValueChange(category, paramName, v)}>
            <SelectTrigger id={inputId} className="w-full">
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
          <div className="flex h-9 items-center gap-2.5">
            <Switch
              id={inputId}
              checked={value === 'true'}
              onCheckedChange={(checked) =>
                handleValueChange(category, paramName, checked ? 'true' : 'false')
              }
            />
            <span className="text-sm text-muted-foreground">{value === 'true' ? 'On' : 'Off'}</span>
          </div>
        );

      case 'number':
        return (
          <Input
            id={inputId}
            type="number"
            value={value}
            onChange={(e) => handleValueChange(category, paramName, e.target.value)}
            className="num w-full sm:max-w-[180px]"
          />
        );

      default:
        return (
          <Input
            id={inputId}
            type="text"
            value={value}
            onChange={(e) => handleValueChange(category, paramName, e.target.value)}
            className="w-full"
          />
        );
    }
  };

  const categories = parameters ? Object.entries(parameters.categories).filter(([name]) => categoryStates[name]) : [];
  const openByDefault = categories.find(([name]) => categoryStates[name]?.isOpen)?.[0];
  const selected =
    selectedCategory && categories.some(([name]) => name === selectedCategory)
      ? selectedCategory
      : openByDefault ?? categories[0]?.[0] ?? null;
  const selectedDef = selected ? parameters?.categories[selected] : null;
  const selectedState = selected ? categoryStates[selected] : null;
  const selectedSystem = selected ? systemOf(selected) : null;

  const platform = environmentInfo
    ? environmentInfo.is_localstack ? 'LocalStack' : environmentInfo.is_aws ? 'AWS' : 'Local'
    : null;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h2 className="text-xl font-medium tracking-tight text-foreground">System</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Platform parameters, grouped by area. A change applies to everyone using this environment.
          </p>
          {environmentInfo ? (
            <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{environmentInfo.environment}</span>
              <span aria-hidden="true">·</span>
              <span>{environmentInfo.region}</span>
              <span aria-hidden="true">·</span>
              <span>{platform}</span>
              <span aria-hidden="true">·</span>
              <span>log level {environmentInfo.log_level}</span>
            </p>
          ) : loading ? (
            <Skeleton className="mt-2 h-5 w-64" />
          ) : null}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Button variant="outline" onClick={fetchParameters} disabled={loading}>
            <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
          </Button>
          <Button variant="outline" onClick={handleInvalidateCache} disabled={invalidatingCache}>
            {invalidatingCache && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
            {invalidatingCache ? 'Clearing' : 'Clear cache'}
          </Button>
        </div>
      </header>

      {error && <InlineError onRetry={parameters ? undefined : fetchParameters}>{error}</InlineError>}

      {success && (
        <p role="status" className="flex items-center gap-2 text-sm text-foreground">
          <Icon name="check-circle" className="h-4 w-4 text-success" />
          {success}
        </p>
      )}

      {loading && !parameters ? (
        <div className="grid gap-x-8 gap-y-4 border-t border-border pt-6 lg:grid-cols-[220px_minmax(0,1fr)]" aria-busy="true">
          <div className="hidden space-y-2 lg:block">
            {[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-8 w-full" />)}
          </div>
          <div className="space-y-4">
            <Skeleton className="h-10 w-56" />
            {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-14 w-full" />)}
          </div>
        </div>
      ) : parameters && categories.length === 0 ? (
        <EmptyState icon="sliders" title="No parameters to show" description="This environment does not expose any editable parameters." />
      ) : parameters && selected && selectedDef && selectedState ? (
        <div className="grid gap-x-8 gap-y-5 border-t border-border pt-6 lg:grid-cols-[220px_minmax(0,1fr)]">
          {/* Group list: a column on desktop, a Select below lg */}
          <div className="lg:hidden">
            <Select value={selected} onValueChange={setSelectedCategory}>
              <SelectTrigger aria-label="Parameter group" className="w-full sm:w-80">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {categories.map(([name, category]) => (
                  <SelectItem key={name} value={name}>
                    {category.label}{categoryStates[name].isModified ? ' (unsaved)' : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <nav aria-label="Parameter groups" className="hidden lg:block">
            <ul className="space-y-px">
              {categories.map(([name, category], i) => {
                const on = name === selected;
                const system = systemOf(name);
                const count = Object.keys(category.parameters).length;
                return (
                  <li key={name} className="rise" style={{ '--i': i } as React.CSSProperties}>
                    <button
                      type="button"
                      onClick={() => setSelectedCategory(name)}
                      aria-current={on ? 'true' : undefined}
                      className={cn(
                        'flex h-9 w-full items-center gap-2.5 rounded-md px-2 text-left text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                        on ? 'bg-accent font-medium text-foreground' : 'text-muted-foreground hover:bg-accent/70 hover:text-foreground',
                      )}
                    >
                      <span className="flex h-4 w-4 shrink-0 items-center justify-center">
                        {system && <SystemLogo system={system} size="sm" />}
                      </span>
                      <span className="min-w-0 flex-1 truncate">{category.label}</span>
                      {categoryStates[name].isModified && (
                        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" title="Unsaved changes">
                          <span className="sr-only">Unsaved changes</span>
                        </span>
                      )}
                      <span className="num shrink-0 text-xs font-normal text-subtle-foreground">{count}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Selected group */}
          <section key={selected} className="min-w-0" aria-label={selectedDef.label}>
            <div className="flex items-start gap-3">
              {selectedSystem && <SystemLogo system={selectedSystem} tile size="md" />}
              <div className="min-w-0">
                <h3 className="text-md font-medium text-foreground">{selectedDef.label}</h3>
                <p className="mt-0.5 text-sm text-muted-foreground">{selectedDef.description}</p>
              </div>
            </div>

            {Object.keys(selectedDef.parameters).length === 0 ? (
              <EmptyState className="mt-5" title="No parameters in this group" />
            ) : (
              <div className="mt-4 border-t border-border">
                {Object.entries(selectedDef.parameters).map(([paramName, param], i) => {
                  const value = selectedState.values[paramName] || '';
                  const isModified = value !== selectedState.originalValues[paramName];
                  const inputId = `param-${selected}-${paramName}`;
                  const rowSystem = selected === 'data_source_mode' ? systemOf(paramName) : null;

                  return (
                    <div
                      key={paramName}
                      className="rise grid gap-x-8 gap-y-2.5 border-b border-border py-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,300px)] sm:items-center"
                      style={{ '--i': i } as React.CSSProperties}
                    >
                      <div className="min-w-0">
                        <label htmlFor={inputId} className="flex items-center gap-2 text-sm font-medium text-foreground">
                          {rowSystem && <SystemLogo system={rowSystem} size="sm" />}
                          <span className="min-w-0 truncate">{humanise(paramName)}</span>
                          {isModified && <span className="shrink-0 text-xs font-normal text-primary dark:text-brand-hi">Edited</span>}
                        </label>
                        {param.description && <p className="mt-0.5 text-sm text-muted-foreground">{param.description}</p>}
                        {param.default !== '' && param.default != null && (
                          <p className="mt-0.5 text-xs text-subtle-foreground">
                            Default <span className="font-mono text-muted-foreground">{param.default}</span>
                          </p>
                        )}
                      </div>
                      <div className="min-w-0 sm:flex sm:justify-end">
                        <div className="w-full sm:flex sm:justify-end">{renderParameterInput(selected, paramName, param, value, inputId)}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Save bar: only when this group has unsaved changes. Left-aligned so it never sits under the assistant launcher. */}
            {selectedState.isModified && (
              <div className="sticky bottom-4 z-10 mt-5 flex w-fit max-w-full flex-wrap items-center gap-3 rounded-xl border border-border-strong bg-popover px-4 py-2.5 shadow-md animate-fade-up">
                <span className="text-sm text-muted-foreground">
                  Unsaved changes in <span className="text-foreground">{selectedDef.label}</span>
                </span>
                <div className="flex items-center gap-2">
                  <Button size="sm" onClick={() => handleSaveCategory(selected)} disabled={!selectedState.isModified || selectedState.isSaving}>
                    {selectedState.isSaving && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
                    {selectedState.isSaving ? 'Saving' : 'Save changes'}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleResetCategory(selected)} disabled={!selectedState.isModified || selectedState.isSaving}>
                    Reset
                  </Button>
                </div>
              </div>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
};

export default SystemSettings;
