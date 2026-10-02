import { useState, useEffect, useCallback } from 'react';
import { toast } from '@/hooks/use-toast';
import { useConfig } from '@/hooks/useConfig';

export interface RBACRole {
  id: string;
  name: string;
  displayName: string;
  description: string;
  level: number;
  badgeColor: string;
}

export interface RBACPermission {
  id: string;
  name: string;
  displayName: string;
  description: string;
  category: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  dataScope: 'individual' | 'team' | 'organization';
}

export interface RBACCategory {
  id: string;
  name: string;
  description: string;
  icon: string;
  order: number;
}

export interface RBACAuditEntry {
  timestamp: string;
  action: string;
  userId: string;
  roleId?: string;
  permissionId?: string;
  changes: string;
  previousValue?: Record<string, unknown>;
  newValue?: Record<string, unknown>;
  version: string;
}

export interface RBACData {
  metadata: {
    version: string;
    lastUpdated: string;
    description: string;
    updatedBy: string;
    environment: string;
  };
  roles: RBACRole[];
  transactionCategories: RBACCategory[];
  permissions: RBACPermission[];
  rolePermissions: Record<string, string[]>;
  auditLog: RBACAuditEntry[];
}

export const useRBAC = () => {
  const [rbacData, setRbacData] = useState<RBACData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const { config, loading: configLoading } = useConfig();

  // Get API base URL from config (empty string is valid for EKS nginx proxy)
  const getApiBaseUrl = useCallback((): string => {
    if (config?.api?.baseUrl !== undefined && config.api.baseUrl !== null) {
      return config.api.baseUrl;
    }
    return import.meta.env.VITE_API_BASE_URL || '';
  }, [config]);

  // Fetch RBAC data from backend API with fallback to local JSON
  const fetchRBACData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const apiBaseUrl = getApiBaseUrl();
      
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/rbac/config`, {
          credentials: 'include',
          headers: {
            'Accept': 'application/json'
          }
        });
        
        if (response.ok) {
          const result = await response.json();
          if (result.status === 'success' && result.data) {
            setRbacData(result.data);
            return;
          }
        }
        
        console.warn('Backend RBAC API not available, falling back to local JSON');
      } catch (apiError) {
        console.warn('Backend RBAC API error, falling back to local JSON:', apiError);
      }

      // Fallback to local JSON file
      const response = await fetch('/results/rbac.json');
      if (!response.ok) {
        throw new Error(`Failed to fetch RBAC data: ${response.statusText}`);
      }

      const data: RBACData = await response.json();
      setRbacData(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load RBAC configuration';
      setError(errorMessage);
      console.error('Error fetching RBAC data:', err);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [getApiBaseUrl]);

  // Update role permissions - saves to backend API
  const updateRolePermissions = useCallback(async (roleId: string, permissionIds: string[]) => {
    if (!rbacData) return;

    const apiBaseUrl = getApiBaseUrl();
    
    // Optimistic update
    const previousData = { ...rbacData };
    const updatedData = {
      ...rbacData,
      rolePermissions: {
        ...rbacData.rolePermissions,
        [roleId]: permissionIds
      },
      metadata: {
        ...rbacData.metadata,
        lastUpdated: new Date().toISOString()
      }
    };
    setRbacData(updatedData);

    try {
      setSaving(true);
      
      const response = await fetch(`${apiBaseUrl}/api/v1/rbac/roles/${roleId}/permissions`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ permissions: permissionIds })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          toast({
            title: 'Success',
            description: `Permissions updated for ${roleId}`,
          });
          await fetchRBACData();
          return;
        }
      }
      
      if (response.status === 403) {
        throw new Error('You do not have permission to modify RBAC settings');
      }
      
      throw new Error('Failed to save permissions to server');
    } catch (err) {
      // Rollback on error
      setRbacData(previousData);
      
      const errorMessage = err instanceof Error ? err.message : 'Failed to update permissions';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setSaving(false);
    }
  }, [rbacData, getApiBaseUrl, fetchRBACData]);

  // Toggle single permission for a role
  const toggleRolePermission = useCallback(async (roleId: string, permissionId: string) => {
    if (!rbacData) return;

    const currentPermissions = rbacData.rolePermissions[roleId] || [];
    const hasPermission = currentPermissions.includes(permissionId);
    
    const newPermissions = hasPermission 
      ? currentPermissions.filter(id => id !== permissionId)
      : [...currentPermissions, permissionId];

    await updateRolePermissions(roleId, newPermissions);
  }, [rbacData, updateRolePermissions]);

  // Get permissions by category
  const getPermissionsByCategory = useCallback((categoryId: string): RBACPermission[] => {
    if (!rbacData) return [];
    return rbacData.permissions.filter(permission => permission.category === categoryId);
  }, [rbacData]);

  // Check if role has permission
  const hasRolePermission = useCallback((roleId: string, permissionId: string): boolean => {
    if (!rbacData) return false;
    return rbacData.rolePermissions[roleId]?.includes(permissionId) || false;
  }, [rbacData]);

  // Get role by ID
  const getRoleById = useCallback((roleId: string): RBACRole | undefined => {
    if (!rbacData) return undefined;
    return rbacData.roles.find(role => role.id === roleId);
  }, [rbacData]);

  // Get permission by ID
  const getPermissionById = useCallback((permissionId: string): RBACPermission | undefined => {
    if (!rbacData) return undefined;
    return rbacData.permissions.find(permission => permission.id === permissionId);
  }, [rbacData]);

  // Get audit log
  const getAuditLog = useCallback(async (limit: number = 50): Promise<RBACAuditEntry[]> => {
    const apiBaseUrl = getApiBaseUrl();
    
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/rbac/audit?limit=${limit}`, {
        credentials: 'include',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success' && result.data) {
          return result.data;
        }
      }
    } catch (err) {
      console.warn('Failed to fetch audit log from API:', err);
    }
    
    // Fallback to local data
    return rbacData?.auditLog || [];
  }, [getApiBaseUrl, rbacData]);

  // Fetch data when config is loaded
  useEffect(() => {
    if (!configLoading) {
      fetchRBACData();
    }
  }, [configLoading, fetchRBACData]);

  return {
    rbacData,
    loading: loading || configLoading,
    error,
    saving,
    fetchRBACData,
    updateRolePermissions,
    toggleRolePermission,
    getPermissionsByCategory,
    hasRolePermission,
    getRoleById,
    getPermissionById,
    getAuditLog
  };
};
