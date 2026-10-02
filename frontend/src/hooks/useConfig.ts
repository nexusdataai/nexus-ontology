import { useState, useEffect } from 'react';
import { getConfig, AppConfig } from '@/services/configService';

export interface UseConfigResult {
  config: AppConfig | null;
  loading: boolean;
  error: string | null;
}

/**
 * React hook for accessing application configuration
 * Wraps the configService for use in React components
 */
export const useConfig = (): UseConfigResult => {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const loadConfig = async () => {
      try {
        const loadedConfig = await getConfig();
        if (mounted) {
          setConfig(loadedConfig);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load configuration');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadConfig();

    return () => {
      mounted = false;
    };
  }, []);

  return { config, loading, error };
};

export default useConfig;
