import React, { useState, useEffect } from 'react';
import { useRBAC, RBACRole, RBACPermission, RBACCategory, RBACAuditEntry } from '@/hooks/useRBAC';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Icon } from '@/components/ds/Icon';
import { CodeBlock, DetailSheet, InlineError, KeyValues, Meter, StatusPill, SubHeading, TableShell } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { useEnterpriseAuth } from '@/context/EnterpriseAuthContext';
import { cn } from '@/lib/utils';

const formatDateTime = (iso: string) => {
  const d = new Date(iso);
  return isNaN(d.getTime())
    ? 'Unknown'
    : d.toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const pretty = (s: string) => String(s || '').replace(/[_.-]+/g, ' ').replace(/^\w/, c => c.toUpperCase());

const SCOPE_LABEL: Record<string, string> = {
  individual: 'Own records',
  team: 'Team records',
  organization: 'Whole organisation',
};

/** Risk of a permission: a dot and a word, never a filled badge. */
const RiskLevelBadge: React.FC<{ level: string }> = ({ level }) => (
  <StatusPill status={level}>{level.charAt(0).toUpperCase() + level.slice(1)}</StatusPill>
);

const HEAD_CELL = 'sticky top-0 z-20 border-b border-border bg-surface-2 px-4 py-2.5 text-xs font-medium text-muted-foreground';

const PermissionRow: React.FC<{
  permission: RBACPermission;
  roles: RBACRole[];
  rolePermissions: Record<string, string[]>;
  onTogglePermission: (roleId: string, permissionId: string) => void;
  isEditable: boolean;
  isSaving: boolean;
}> = ({ permission, roles, rolePermissions, onTogglePermission, isEditable, isSaving }) => {
  return (
    <tr className="group">
      <th scope="row" className="sticky left-0 z-10 border-b border-border bg-card px-4 py-3 text-left align-top font-normal transition-colors group-hover:bg-surface-2">
        <div className="text-sm font-medium text-foreground">{permission.displayName}</div>
        <div className="mt-0.5 text-xs text-muted-foreground">{permission.description}</div>
      </th>
      <td className="whitespace-nowrap border-b border-border px-4 py-3 align-top transition-colors group-hover:bg-surface-2/60">
        <RiskLevelBadge level={permission.riskLevel} />
        <div className="mt-0.5 text-xs text-muted-foreground">{SCOPE_LABEL[permission.dataScope] || pretty(permission.dataScope)}</div>
      </td>
      {roles.map((role) => {
        const on = rolePermissions[role.id]?.includes(permission.id) || false;
        return (
          <td key={role.id} className="border-b border-border px-4 py-3 text-center align-middle transition-colors group-hover:bg-surface-2/60">
            {isEditable ? (
              <Switch
                checked={on}
                onCheckedChange={() => isEditable && !isSaving && onTogglePermission(role.id, permission.id)}
                disabled={!isEditable || isSaving}
                aria-label={`${permission.displayName} for ${role.displayName}`}
              />
            ) : on ? (
              <Icon name="check" label={`Allowed for ${role.displayName}`} className="mx-auto h-4 w-4 text-foreground" />
            ) : (
              <span className="text-subtle-foreground" role="img" aria-label={`Not allowed for ${role.displayName}`}>-</span>
            )}
          </td>
        );
      })}
    </tr>
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
    <tbody>
      <tr>
        <th scope="colgroup" colSpan={roles.length + 2} className="border-b border-border bg-surface-2/50 p-0 text-left font-normal">
          <div className="sticky left-0 inline-flex max-w-[min(100%,560px)] flex-wrap items-baseline gap-x-2.5 px-4 py-2">
            <span className="text-sm font-medium text-foreground">{category.name}</span>
            <span className="text-xs text-muted-foreground">{category.description}</span>
          </div>
        </th>
      </tr>
      {permissions.length === 0 ? (
        <tr>
          <td colSpan={roles.length + 2} className="border-b border-border px-4 py-4 text-sm text-muted-foreground">
            No permissions defined for this area.
          </td>
        </tr>
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
    </tbody>
  );
};

const AuditLogTab: React.FC = () => {
  const { getAuditLog } = useRBAC();
  const [auditEntries, setAuditEntries] = useState<RBACAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [openEntry, setOpenEntry] = useState<RBACAuditEntry | null>(null);

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

  if (loading && auditEntries.length === 0) {
    return (
      <div className="space-y-px overflow-hidden rounded-xl border border-border" aria-busy="true">
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-14 w-full rounded-none" />)}
      </div>
    );
  }

  if (auditEntries.length === 0) {
    return <EmptyState icon="history" title="No changes recorded" description="Changes to roles and permissions are listed here once someone makes one." />;
  }

  return (
    <>
      <TableShell>
        <table className="w-full min-w-[680px] border-collapse text-sm">
          <thead>
            <tr>
              {['When', 'Change', 'Role', 'Changed by', 'Version'].map((h) => (
                <th key={h} scope="col" className="whitespace-nowrap border-b border-border bg-surface-2 px-5 py-2.5 text-left text-xs font-medium text-muted-foreground">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {auditEntries.map((entry, index) => (
              <tr
                key={index}
                tabIndex={0}
                onClick={() => setOpenEntry(entry)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpenEntry(entry); } }}
                className="rise cursor-pointer border-b border-border transition-colors last:border-b-0 hover:bg-surface-2/60 focus-visible:bg-surface-2/60 focus-visible:outline-none"
                style={{ '--i': index } as React.CSSProperties}
              >
                <td className="num whitespace-nowrap px-5 py-3 text-muted-foreground">{formatDateTime(entry.timestamp)}</td>
                <td className="px-5 py-3">
                  <div className="font-medium text-foreground">{entry.changes}</div>
                  <div className="text-xs text-muted-foreground">{pretty(entry.action)}</div>
                </td>
                <td className="whitespace-nowrap px-5 py-3 text-muted-foreground">{entry.roleId ? pretty(entry.roleId) : 'All roles'}</td>
                <td className="px-5 py-3 text-muted-foreground">{entry.userId}</td>
                <td className="num whitespace-nowrap px-5 py-3 text-muted-foreground">{entry.version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableShell>

      <DetailSheet
        open={!!openEntry}
        onOpenChange={(open) => { if (!open) setOpenEntry(null); }}
        title={openEntry?.changes || 'Change'}
        description={openEntry ? `${pretty(openEntry.action)}, ${formatDateTime(openEntry.timestamp)}` : undefined}
      >
        {openEntry && (
          <div className="space-y-6">
            <KeyValues
              items={[
                { label: 'Changed by', value: openEntry.userId },
                { label: 'Role', value: openEntry.roleId ? pretty(openEntry.roleId) : 'All roles' },
                { label: 'Permission', value: openEntry.permissionId || 'Not specific to one', mono: !!openEntry.permissionId },
                { label: 'Version', value: openEntry.version },
                { label: 'When', value: formatDateTime(openEntry.timestamp) },
              ]}
            />
            {(openEntry.previousValue || openEntry.newValue) && (
              <details className="text-sm">
                <summary className="cursor-pointer text-primary dark:text-brand-hi">Technical details</summary>
                <div className="mt-3 space-y-4">
                  {openEntry.previousValue && (
                    <div>
                      <SubHeading>Before</SubHeading>
                      <CodeBlock>{JSON.stringify(openEntry.previousValue, null, 2)}</CodeBlock>
                    </div>
                  )}
                  {openEntry.newValue && (
                    <div>
                      <SubHeading>After</SubHeading>
                      <CodeBlock>{JSON.stringify(openEntry.newValue, null, 2)}</CodeBlock>
                    </div>
                  )}
                </div>
              </details>
            )}
          </div>
        )}
      </DetailSheet>
    </>
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

  const heading = (
    <div className="min-w-0">
      <h2 className="text-xl font-medium tracking-tight text-foreground">Roles and permissions</h2>
      <p className="mt-1 max-w-2xl text-sm text-muted-foreground">What each role is allowed to do across the platform.</p>
    </div>
  );

  if (loading && !rbacData) {
    return (
      <div className="space-y-5" aria-busy="true">
        {heading}
        <Skeleton className="h-10 w-full" />
        <div className="space-y-px overflow-hidden rounded-xl border border-border">
          {[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-14 w-full rounded-none" />)}
        </div>
      </div>
    );
  }

  if (error && !rbacData) {
    return (
      <div className="space-y-5">
        {heading}
        <InlineError onRetry={fetchRBACData}>{error}</InlineError>
      </div>
    );
  }

  if (!rbacData) {
    return (
      <div className="space-y-5">
        {heading}
        <EmptyState
          icon="shield-check"
          title="No roles are set up"
          description="The server did not return a roles and permissions configuration."
          action={<Button variant="outline" onClick={fetchRBACData}>Try again</Button>}
        />
      </div>
    );
  }

  const { roles: allRoles, transactionCategories, rolePermissions, metadata } = rbacData;
  const roles = allRoles.filter(r => r.id !== 'Admin');
  const shownPermissions = isEditable && pendingPermissions ? pendingPermissions : rolePermissions;
  const sortedCategories = [...transactionCategories].sort((a, b) => a.order - b.order);
  const totalPermissions = rbacData.permissions.length;
  const editing = isEditable && canManageRBAC;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h2 className="text-xl font-medium tracking-tight text-foreground">Roles and permissions</h2>
          {metadata.description && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{metadata.description}</p>}
          <p className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
            <span>Version <span className="num text-foreground">{metadata.version}</span></span>
            <span aria-hidden="true">·</span>
            <span>last updated {formatDateTime(metadata.lastUpdated)}{metadata.updatedBy ? ` by ${metadata.updatedBy}` : ''}</span>
            {metadata.environment && (
              <>
                <span aria-hidden="true">·</span>
                <span>{metadata.environment}</span>
              </>
            )}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2">
          {canManageRBAC && (
            <label className="flex items-center gap-2.5 text-sm text-muted-foreground">
              <Switch checked={isEditable} onCheckedChange={handleEditModeChange} disabled={saving} />
              Edit mode
            </label>
          )}
          <Button variant="outline" onClick={fetchRBACData} disabled={loading}>
            <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
          </Button>
        </div>
      </header>

      {error && <InlineError onRetry={fetchRBACData}>{error}</InlineError>}

      {!canManageRBAC && (
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0 text-subtle-foreground" />
          You can read this configuration but not change it. Ask an administrator if a role needs different access.
        </p>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="line">
          <TabsTrigger value="matrix">Permissions</TabsTrigger>
          <TabsTrigger value="roles">Roles</TabsTrigger>
          <TabsTrigger value="audit">History</TabsTrigger>
        </TabsList>

        <TabsContent value="matrix" className="mt-5">
          {roles.length === 0 || totalPermissions === 0 ? (
            <EmptyState icon="shield-check" title="Nothing to show yet" description="No roles or no permissions are defined in this configuration." />
          ) : (
            <>
              <p className="mb-3 text-sm text-muted-foreground">
                <span className="num font-medium text-foreground">{totalPermissions}</span> permissions across{' '}
                <span className="num font-medium text-foreground">{roles.length}</span> roles.{' '}
                {editing
                  ? 'Switch permissions on or off, then save.'
                  : canManageRBAC ? 'Turn on edit mode to make changes.' : ''}
              </p>

              <div className="scroll-thin max-h-[72vh] overflow-auto rounded-xl border border-border bg-card shadow-xs">
                <table className="w-full border-separate border-spacing-0 text-sm" style={{ minWidth: 420 + roles.length * 112 }}>
                  <thead>
                    <tr>
                      <th scope="col" className={cn(HEAD_CELL, 'left-0 z-30 min-w-[220px] text-left')}>Permission</th>
                      <th scope="col" className={cn(HEAD_CELL, 'text-left')}>Risk and reach</th>
                      {roles.map((role) => (
                        <th key={role.id} scope="col" className={cn(HEAD_CELL, 'min-w-[104px] whitespace-nowrap text-center text-foreground')}>
                          {role.displayName}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  {sortedCategories.map((category) => (
                    <CategorySection
                      key={category.id}
                      category={category}
                      permissions={getPermissionsByCategory(category.id)}
                      roles={roles}
                      rolePermissions={shownPermissions}
                      onTogglePermission={handleTogglePermission}
                      isEditable={editing}
                      isSaving={saving}
                    />
                  ))}
                </table>
              </div>

              <p className="mt-3 text-xs text-muted-foreground">
                Saved changes are stored on the server and apply to every user with that role.
              </p>

              {/* Save bar: only with unsaved changes. Left-aligned so it never sits under the assistant launcher. */}
              {editing && hasPendingChanges && (
                <div className="sticky bottom-4 z-30 mt-4 flex w-fit max-w-full flex-wrap items-center gap-3 rounded-xl border border-border-strong bg-popover px-4 py-2.5 shadow-md animate-fade-up">
                  <span className="text-sm text-muted-foreground">
                    Unsaved changes in <span className="num text-foreground">{changedRoles.size}</span> {changedRoles.size === 1 ? 'role' : 'roles'}
                  </span>
                  <div className="flex items-center gap-2">
                    <Button size="sm" onClick={handleSave} disabled={saving || !hasPendingChanges}>
                      {saving && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
                      {saving ? 'Saving' : 'Save changes'}
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleDiscard} disabled={saving || !hasPendingChanges}>
                      Discard
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </TabsContent>

        <TabsContent value="roles" className="mt-5">
          {roles.length === 0 ? (
            <EmptyState icon="users" title="No roles defined" />
          ) : (
            <ul className="border-t border-border">
              {roles.map((role, i) => {
                const granted = rolePermissions[role.id] || [];
                return (
                  <li
                    key={role.id}
                    className="rise grid gap-x-10 gap-y-3 border-b border-border py-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,340px)]"
                    style={{ '--i': i } as React.CSSProperties}
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <h3 className="text-md font-medium text-foreground">{role.displayName}</h3>
                        <span className="num text-xs text-muted-foreground">Level {role.level}</span>
                      </div>
                      <p className="mt-1 max-w-xl text-sm text-muted-foreground">{role.description}</p>
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-baseline justify-between gap-3 text-sm">
                        <span className="text-foreground">
                          <span className="num font-medium">{granted.length}</span> of <span className="num">{totalPermissions}</span> permissions
                        </span>
                      </div>
                      <Meter value={granted.length} max={totalPermissions || 1} className="mt-2" label={`${role.displayName}: share of permissions`} />
                      <p className="mt-2.5 text-xs leading-5 text-muted-foreground">
                        {sortedCategories
                          .map((c) => {
                            const inCat = getPermissionsByCategory(c.id);
                            if (inCat.length === 0) return null;
                            const have = inCat.filter(p => granted.includes(p.id)).length;
                            return `${c.name} ${have}/${inCat.length}`;
                          })
                          .filter(Boolean)
                          .join(' · ') || 'No permissions assigned'}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </TabsContent>

        <TabsContent value="audit" className="mt-5">
          <AuditLogTab />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default RBACMatrix;
