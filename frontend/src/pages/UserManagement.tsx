import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';
import { apiClient } from '@/services/apiClient';
import { confirmDialog } from '@/components/ds/confirm';
import { Icon } from '@/components/ds/Icon';
import { Field, InlineError, SearchInput, StatusPill, TableShell, Toolbar, ToolbarSpacer, type Tone } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { cn } from '@/lib/utils';

interface CognitoUser {
  sub: string;
  email: string;
  /** Present when the directory has a display name. */
  name?: string;
  status: string;
  enabled: boolean;
  groups: string[];
  role: string;
  mfa_enabled: boolean;
  created: string;
  last_modified: string;
}

const ROLES = ['Admin', 'Executive', 'SalesManager', 'Rep'];

const ROLE_LABEL: Record<string, string> = {
  Admin: 'Admin',
  Executive: 'Executive',
  SalesManager: 'Sales manager',
  Rep: 'Rep',
};

const initialsOf = (user: CognitoUser) =>
  (user.name || user.email || '?')
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0]?.toUpperCase())
    .join('');

const statusOf = (user: CognitoUser): { label: string; tone: Tone } => {
  if (!user.enabled) return { label: 'Disabled', tone: 'danger' };
  if (user.status === 'CONFIRMED') return { label: 'Active', tone: 'success' };
  if (user.status === 'FORCE_CHANGE_PASSWORD') return { label: 'Pending', tone: 'warning' };
  return { label: String(user.status || 'Unknown').replace(/_/g, ' ').toLowerCase(), tone: 'warning' };
};

const formatDate = (iso: string) => {
  if (!iso) return 'Not recorded';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? 'Not recorded' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

const HEAD = 'whitespace-nowrap border-b border-border bg-surface-2 px-5 py-2.5 text-left text-xs font-medium text-muted-foreground';

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<CognitoUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('Rep');
  const [creating, setCreating] = useState(false);
  const [resetTarget, setResetTarget] = useState<{ sub: string; email: string } | null>(null);
  const [resetTempPassword, setResetTempPassword] = useState('');
  const [resetting, setResetting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ sub: string; email: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  // Local filter on the loaded list (view state only).
  const [query, setQuery] = useState('');

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await apiClient.get<{ users: CognitoUser[] }>('/api/v1/users/', { requireAuth: false });
      setUsers(resp.users || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleCreate = async () => {
    if (!newEmail || !newPassword) return;
    setCreating(true);
    try {
      await apiClient.post('/api/v1/users/', { email: newEmail, temporary_password: newPassword, group: newRole }, { requireAuth: false });
      toast.success(`User ${newEmail} created`);
      setCreateDialogOpen(false);
      setNewEmail('');
      setNewPassword('');
      setNewRole('Rep');
      fetchUsers();
    } catch (err: any) {
      toast.error(err?.message || 'Failed to create user');
    } finally {
      setCreating(false);
    }
  };

  const handleRoleChange = async (sub: string, currentGroups: string[], newGroup: string) => {
    try {
      await apiClient.patch(`/api/v1/users/${sub}/groups`, {
        remove_groups: currentGroups.filter(g => ROLES.includes(g)),
        add_groups: [newGroup],
      }, { requireAuth: false });
      toast.success('Role updated');
      fetchUsers();
    } catch (err: any) {
      toast.error(err?.message || 'Failed to update role');
    }
  };

  const handleDisable = async (sub: string, email: string) => {
    if (!(await confirmDialog({ title: `Disable user ${email}?`, description: 'They will no longer be able to sign in.', confirmLabel: 'Disable', destructive: true }))) return;
    try {
      await apiClient.delete(`/api/v1/users/${sub}`, { requireAuth: false });
      toast.success(`User ${email} disabled`);
      fetchUsers();
    } catch (err: any) {
      toast.error(err?.message || 'Failed to disable user');
    }
  };

  const handleResetPassword = async () => {
    if (!resetTarget || !resetTempPassword) return;
    setResetting(true);
    try {
      await apiClient.post(`/api/v1/users/${resetTarget.sub}/reset-password`, { temporary_password: resetTempPassword }, { requireAuth: false });
      toast.success(`Temporary password set for ${resetTarget.email}. They must change it on next login.`);
      setResetTarget(null);
      setResetTempPassword('');
      fetchUsers();
    } catch (err: any) {
      toast.error(err?.message || 'Failed to reset password');
    } finally {
      setResetting(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await apiClient.delete(`/api/v1/users/${deleteTarget.sub}/permanent`, { requireAuth: false });
      toast.success(`User ${deleteTarget.email} permanently deleted`);
      setDeleteTarget(null);
      fetchUsers();
    } catch (err: any) {
      toast.error(err?.message || 'Failed to delete user');
    } finally {
      setDeleting(false);
    }
  };

  const q = query.trim().toLowerCase();
  const visible = q
    ? users.filter(u => [u.email, u.name, u.role, ROLE_LABEL[u.role], statusOf(u).label].some(v => String(v || '').toLowerCase().includes(q)))
    : users;
  const disabledCount = users.filter(u => !u.enabled).length;
  const pendingCount = users.filter(u => u.enabled && u.status !== 'CONFIRMED').length;

  return (
    <div className="space-y-4">
      <div className="min-w-0">
        <h2 className="text-md font-medium text-foreground">Users</h2>
        <p className="mt-0.5 text-sm text-muted-foreground">
          {users.length === 0
            ? 'People who can sign in, their role and their sign-in security.'
            : <>
                <span className="num font-medium text-foreground">{users.length}</span> {users.length === 1 ? 'person' : 'people'} can sign in
                {pendingCount > 0 && <>, <span className="num font-medium text-foreground">{pendingCount}</span> still to finish setting up</>}
                {disabledCount > 0 && <>, <span className="num font-medium text-foreground">{disabledCount}</span> disabled</>}.
              </>}
        </p>
      </div>

      <Toolbar>
        <SearchInput value={query} onChange={setQuery} placeholder="Search by name, email or role" className="sm:w-72" />
        <ToolbarSpacer />
        <Button variant="outline" size="sm" onClick={fetchUsers} disabled={loading}>
          <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
        </Button>
        <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
          <Icon name="plus" className="h-3.5 w-3.5" /> Add user
        </Button>
      </Toolbar>

      {error && <InlineError onRetry={fetchUsers}>{error}</InlineError>}

      {loading && users.length === 0 ? (
        <div className="space-y-px overflow-hidden rounded-xl border border-border" aria-busy="true">
          {[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-14 w-full rounded-none" />)}
        </div>
      ) : users.length === 0 ? (
        !error && (
          <EmptyState
            icon="users"
            title="No users yet"
            description="Add the first person who should be able to sign in."
            action={<Button onClick={() => setCreateDialogOpen(true)}><Icon name="plus" className="h-3.5 w-3.5" /> Add user</Button>}
          />
        )
      ) : visible.length === 0 ? (
        <EmptyState
          icon="search"
          title="No one matches that search"
          description={`Nothing found for "${query}".`}
          action={<Button variant="outline" onClick={() => setQuery('')}>Clear search</Button>}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[820px] border-collapse text-sm">
            <thead>
              <tr>
                <th scope="col" className={HEAD}>User</th>
                <th scope="col" className={HEAD}>Role</th>
                <th scope="col" className={HEAD}>Status</th>
                <th scope="col" className={HEAD}>Two-step sign-in</th>
                <th scope="col" className={HEAD}>Created</th>
                <th scope="col" className={HEAD}><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {visible.map((user, i) => {
                const status = statusOf(user);
                return (
                  <tr
                    key={user.sub}
                    className={cn('rise border-b border-border transition-colors last:border-b-0 hover:bg-surface-2/60', !user.enabled && 'text-muted-foreground')}
                    style={{ '--i': Math.min(i, 12) } as React.CSSProperties}
                  >
                    <td className="px-5 py-2.5">
                      <div className="flex items-center gap-3">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-surface-2 text-xs font-medium text-foreground" aria-hidden="true">
                          {initialsOf(user)}
                        </span>
                        <div className="min-w-0">
                          <div className={cn('max-w-[260px] truncate font-medium', user.enabled ? 'text-foreground' : 'text-muted-foreground')} title={user.name || user.email}>
                            {user.name || user.email}
                          </div>
                          {user.name && <div className="max-w-[260px] truncate text-xs text-muted-foreground" title={user.email}>{user.email}</div>}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-2.5">
                      <Select value={user.role} onValueChange={(val) => handleRoleChange(user.sub, user.groups, val)}>
                        <SelectTrigger className="h-8 w-[150px]" aria-label={`Role of ${user.email}`}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {ROLES.map(r => (
                            <SelectItem key={r} value={r}>{ROLE_LABEL[r] || r}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="whitespace-nowrap px-5 py-2.5">
                      <StatusPill tone={status.tone}>{status.label}</StatusPill>
                    </td>
                    <td className={cn('whitespace-nowrap px-5 py-2.5', user.mfa_enabled ? 'text-foreground' : 'text-muted-foreground')}>
                      {user.mfa_enabled ? 'On' : 'Off'}
                    </td>
                    <td className="num whitespace-nowrap px-5 py-2.5 text-muted-foreground">{formatDate(user.created)}</td>
                    <td className="px-5 py-2.5 text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-muted-foreground" aria-label={`More actions for ${user.email}`}>
                            <Icon name="more" className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          <DropdownMenuItem onSelect={() => setResetTarget({ sub: user.sub, email: user.email })}>
                            <Icon name="key" className="mr-2 h-3.5 w-3.5" /> Reset password
                          </DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => handleDisable(user.sub, user.email)}>
                            <Icon name="cross-circle" className="mr-2 h-3.5 w-3.5" /> Disable
                          </DropdownMenuItem>
                          {user.role !== 'Admin' && (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem className="text-destructive focus:text-destructive" onSelect={() => setDeleteTarget({ sub: user.sub, email: user.email })}>
                                <Icon name="trash" className="mr-2 h-3.5 w-3.5" /> Delete
                              </DropdownMenuItem>
                            </>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableShell>
      )}

      {/* Add user */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add user</DialogTitle>
            <DialogDescription>
              They sign in with the temporary password and choose their own the first time.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <Field label="Email" htmlFor="new-user-email">
              <Input id="new-user-email" type="email" autoComplete="off" placeholder="name@company.com" value={newEmail} onChange={e => setNewEmail(e.target.value)} />
            </Field>
            <Field label="Temporary password" htmlFor="new-user-password" hint="At least 8 characters, with upper case, lower case and a number.">
              <Input id="new-user-password" type="password" autoComplete="new-password" value={newPassword} onChange={e => setNewPassword(e.target.value)} />
            </Field>
            <Field label="Role" htmlFor="new-user-role">
              <Select value={newRole} onValueChange={setNewRole}>
                <SelectTrigger id="new-user-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map(r => (
                    <SelectItem key={r} value={r}>{ROLE_LABEL[r] || r}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)} disabled={creating}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!newEmail || !newPassword || creating}>
              {creating && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
              {creating ? 'Creating' : 'Create user'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset password */}
      <Dialog open={!!resetTarget} onOpenChange={(open) => { if (!open) { setResetTarget(null); setResetTempPassword(''); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset password</DialogTitle>
            <DialogDescription>
              Set a temporary password for <span className="font-medium text-foreground">{resetTarget?.email}</span>. They choose a new one the next time they sign in.
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <Field
              label="Temporary password"
              htmlFor="reset-user-password"
              hint="At least 8 characters, with upper case, lower case and a number. The user is signed out everywhere."
            >
              <Input
                id="reset-user-password"
                type="password"
                autoComplete="new-password"
                value={resetTempPassword}
                onChange={e => setResetTempPassword(e.target.value)}
              />
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setResetTarget(null); setResetTempPassword(''); }} disabled={resetting}>Cancel</Button>
            <Button onClick={handleResetPassword} disabled={resetting || resetTempPassword.length < 8}>
              {resetting && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
              {resetting ? 'Resetting' : 'Reset password'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete user */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this user?</DialogTitle>
            <DialogDescription>
              <span className="font-medium text-foreground">{deleteTarget?.email}</span> will be removed for good, with all sessions and associated data. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
              {deleting ? 'Deleting' : 'Delete for good'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export { UserManagement as UserManagementPanel };
export default UserManagement;
