import React, { useState, useEffect } from 'react';
import { useRBAC, RBACRole, RBACPermission, RBACCategory, RBACAuditEntry } from '@/hooks/useRBAC';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Shield, Users, Settings, Info, AlertCircle, CheckCircle, XCircle, History, RefreshCw, Save } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useEnterpriseAuth } from '@/context/EnterpriseAuthContext';

const RiskLevelBadge: React.FC<{ level: string }> = ({ level }) => {
  const getBadgeStyle = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical':
        return 'bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300 border-red-200 dark:border-red-800';
      case 'high':
        return 'bg-orange-100 dark:bg-orange-900/20 text-orange-800 dark:text-orange-300 border-orange-200 dark:border-orange-800';
      case 'medium':
        return 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800';
      case 'low':
        return 'bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-300 border-green-200 dark:border-green-800';
      default:
        return 'bg-muted text-muted-foreground border-border';
    }
  };

  const getIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical':
        return <AlertCircle className="w-3 h-3" />;
      case 'high':
        return <XCircle className="w-3 h-3" />;
      case 'medium':
        return <Info className="w-3 h-3" />;
      case 'low':
        return <CheckCircle className="w-3 h-3" />;
      default:
        return null;
    }
  };

  return (
    <Badge variant="outline" className={`${getBadgeStyle(level)} flex items-center gap-1`}>
      {getIcon(level)}
      {level.charAt(0).toUpperCase() + level.slice(1)}
    </Badge>
  );
};

const PermissionRow: React.FC<{
  permission: RBACPermission;
  roles: RBACRole[];
  rolePermissions: Record<string, string[]>;
  onTogglePermission: (roleId: string, permissionId: string) => void;
  isEditable: boolean;
  isSaving: boolean;
}> = ({ permission, roles, rolePermissions, onTogglePermission, isEditable, isSaving }) => {
  return (
    <div className="grid grid-cols-11 gap-4 py-3 border-b border-border hover:bg-muted/50">
      <div className="col-span-5">
        <div className="flex flex-col space-y-1">
          <span className="font-medium text-sm">{permission.displayName}</span>
          <span className="text-xs text-muted-foreground">{permission.description}</span>
          <div className="flex items-center gap-2">
            <RiskLevelBadge level={permission.riskLevel} />
            <Badge variant="outline" className="text-xs">
              {permission.dataScope}
            </Badge>
          </div>
        </div>
      </div>
      
      {roles.map((role) => (
        <div key={role.id} className="col-span-2 flex items-center justify-center">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center">
                  <Switch
                    checked={rolePermissions[role.id]?.includes(permission.id) || false}
                    onCheckedChange={() => isEditable && !isSaving && onTogglePermission(role.id, permission.id)}
                    disabled={!isEditable || isSaving}
                  />
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>{rolePermissions[role.id]?.includes(permission.id) ? 'Enabled' : 'Disabled'} for {role.displayName}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      ))}
    </div>
  );
};

const CategorySection: React.FC<{
  category: RBACCategory;
  permissions: RBACPermission[];
  roles: RBACRole[];
  rolePermissions: Record<string, string[]>;
  onTogglePermission: (roleId: string, permissionId: string) => void;
  isEditable: boolean;
  isSaving: boolean;
}> = ({ category, permissions, roles, rolePermissions, onTogglePermission, isEditable, isSaving }) => {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-2xl">{category.icon}</span>
        <div>
          <h3 className="text-lg font-semibold">{category.name}</h3>
          <p className="text-sm text-muted-foreground">{category.description}</p>
        </div>
      </div>
      
      <div className="bg-card rounded-lg border border-border">
        <div className="p-4">
          {permissions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No permissions defined for this category
            </div>
          ) : (
            permissions.map((permission) => (
              <PermissionRow
                key={permission.id}
                permission={permission}
                roles={roles}
                rolePermissions={rolePermissions}
                onTogglePermission={onTogglePermission}
                isEditable={isEditable}
                isSaving={isSaving}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
};

const AuditLogTab: React.FC = () => {
  const { getAuditLog } = useRBAC();
  const [auditEntries, setAuditEntries] = useState<RBACAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAuditLog = async () => {
      setLoading(true);
      try {
        const entries = await getAuditLog(50);
        setAuditEntries(entries);
      } finally {
        setLoading(false);
      }
    };
    fetchAuditLog();
  }, [getAuditLog]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />
        Loading audit log...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <History className="h-5 w-5" />
        <h3 className="text-lg font-semibold">Change History</h3>
      </div>
      
      {auditEntries.length === 0 ? (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>No audit entries found.</AlertDescription>
        </Alert>
      ) : (
        <div className="space-y-2">
          {auditEntries.map((entry, index) => (
            <div key={index} className="p-4 border border-border rounded-lg bg-card">
              <div className="flex items-center justify-between mb-2">
                <Badge variant="outline">{entry.action}</Badge>
                <span className="text-xs text-muted-foreground">
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
              </div>
              <p className="text-sm">{entry.changes}</p>
              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                <span>User: {entry.userId}</span>
                {entry.roleId && <span>Role: {entry.roleId}</span>}
                <span>Version: {entry.version}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const RBACMatrix: React.FC = () => {
  const { 
    rbacData, 
    loading, 
    error,
    saving,
    updateRolePermissions,
    getPermissionsByCategory,
    fetchRBACData 
  } = useRBAC();

  const { hasPermission, profile } = useEnterpriseAuth();
  const [isEditable, setIsEditable] = useState(false);
  const [activeTab, setActiveTab] = useState('matrix');
  const [pendingPermissions, setPendingPermissions] = useState<Record<string, string[]> | null>(null);
  const [changedRoles, setChangedRoles] = useState<Set<string>>(new Set());

  const hasPendingChanges = changedRoles.size > 0;

  const handleTogglePermission = (roleId: string, permissionId: string) => {
    if (!pendingPermissions) return;
    const current = pendingPermissions[roleId] || [];
    const hasIt = current.includes(permissionId);
    const updated = hasIt ? current.filter(id => id !== permissionId) : [...current, permissionId];
    setPendingPermissions({ ...pendingPermissions, [roleId]: updated });
    setChangedRoles(prev => new Set(prev).add(roleId));
  };

  const handleSave = async () => {
    if (!pendingPermissions || changedRoles.size === 0) return;
    for (const roleId of changedRoles) {
      await updateRolePermissions(roleId, pendingPermissions[roleId] || []);
    }
    setChangedRoles(new Set());
  };

  const handleDiscard = () => {
    if (rbacData) {
      setPendingPermissions({ ...rbacData.rolePermissions });
    }
    setChangedRoles(new Set());
  };

  const handleEditModeChange = (enabled: boolean) => {
    setIsEditable(enabled);
    if (enabled && rbacData) {
      setPendingPermissions({ ...rbacData.rolePermissions });
      setChangedRoles(new Set());
    } else {
      setPendingPermissions(null);
      setChangedRoles(new Set());
    }
  };

  // Check if user has permission to manage RBAC
  const canManageRBAC = hasPermission('manage_rbac') || profile?.role === 'Admin';

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading RBAC configuration...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          {error}
          <Button variant="outline" size="sm" onClick={fetchRBACData} className="ml-2">
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!rbacData) {
    return (
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>No RBAC configuration found.</AlertDescription>
      </Alert>
    );
  }

  const { roles: allRoles, transactionCategories, rolePermissions, metadata } = rbacData;
  const roles = allRoles.filter(r => r.id !== 'Admin');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6" />
            RBAC Management
          </h2>
          <p className="text-muted-foreground mt-1">{metadata.description}</p>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant="outline">v{metadata.version}</Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchRBACData}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          {canManageRBAC && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Edit Mode:</span>
              <Switch
                checked={isEditable}
                onCheckedChange={handleEditModeChange}
                disabled={saving}
              />
            </div>
          )}
        </div>
      </div>

      {/* Permission Warning */}
      {!canManageRBAC && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            You have read-only access to RBAC configuration. Contact an administrator to make changes.
          </AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="matrix">
            <Settings className="h-4 w-4 mr-2" />
            Permission Matrix
          </TabsTrigger>
          <TabsTrigger value="roles">
            <Users className="h-4 w-4 mr-2" />
            Roles
          </TabsTrigger>
          <TabsTrigger value="audit">
            <History className="h-4 w-4 mr-2" />
            Audit Log
          </TabsTrigger>
        </TabsList>

        <TabsContent value="matrix" className="mt-6">
          {/* Metadata Info */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-lg">Configuration Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Last Updated:</span>
                  <span className="ml-2">{new Date(metadata.lastUpdated).toLocaleString()}</span>
                </div>
                <div>
                  <span className="font-medium">Updated By:</span>
                  <span className="ml-2">{metadata.updatedBy}</span>
                </div>
                <div>
                  <span className="font-medium">Environment:</span>
                  <span className="ml-2 capitalize">{metadata.environment}</span>
                </div>
                <div>
                  <span className="font-medium">Total Roles:</span>
                  <span className="ml-2">{roles.length}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Permission Matrix */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Permission Matrix
              </CardTitle>
              <CardDescription>
                {isEditable ? 'Toggle permissions, then click Save to apply changes' : 'Enable edit mode to make changes'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Matrix Header */}
              <div className="grid grid-cols-11 gap-4 py-3 border-b-2 border-border font-medium text-sm bg-muted">
                <div className="col-span-5">Permission</div>
                {roles.map((role) => (
                  <div key={role.id} className="col-span-2 text-center">
                    <Badge className={role.badgeColor}>{role.displayName}</Badge>
                  </div>
                ))}
              </div>

              {/* Permission Categories */}
              <div className="mt-6">
                {transactionCategories
                  .sort((a, b) => a.order - b.order)
                  .map((category) => (
                    <CategorySection
                      key={category.id}
                      category={category}
                      permissions={getPermissionsByCategory(category.id)}
                      roles={roles}
                      rolePermissions={isEditable && pendingPermissions ? pendingPermissions : rolePermissions}
                      onTogglePermission={handleTogglePermission}
                      isEditable={isEditable && canManageRBAC}
                      isSaving={saving}
                    />
                  ))}
              </div>

              {/* Save / Discard buttons */}
              {isEditable && canManageRBAC && (
                <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDiscard}
                    disabled={saving || !hasPendingChanges}
                  >
                    Discard Changes
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSave}
                    disabled={saving || !hasPendingChanges}
                  >
                    {saving ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-2" />
                    )}
                    {saving ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roles" className="mt-6">
          {/* Role Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Users className="h-5 w-5" />
                Role Overview
              </CardTitle>
              <CardDescription>Current roles and their access levels</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {roles.map((role) => (
                  <div key={role.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <Badge className={role.badgeColor}>{role.displayName}</Badge>
                      <span className="text-xs text-muted-foreground">Level {role.level}</span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{role.description}</p>
                    <div className="text-xs text-muted-foreground">
                      {rolePermissions[role.id]?.length || 0} permissions assigned
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {rolePermissions[role.id]?.slice(0, 5).map((permId) => (
                        <Badge key={permId} variant="secondary" className="text-xs">
                          {permId.replace(/_/g, ' ')}
                        </Badge>
                      ))}
                      {(rolePermissions[role.id]?.length || 0) > 5 && (
                        <Badge variant="secondary" className="text-xs">
                          +{(rolePermissions[role.id]?.length || 0) - 5} more
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit" className="mt-6">
          <Card>
            <CardContent className="pt-6">
              <AuditLogTab />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Backend Integration Status */}
      <Alert className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        <AlertDescription className="text-blue-800 dark:text-blue-300">
          <strong>Backend Integration Active:</strong> Changes are automatically saved to the server and synchronized across all users.
        </AlertDescription>
      </Alert>
    </div>
  );
};

export default RBACMatrix;
