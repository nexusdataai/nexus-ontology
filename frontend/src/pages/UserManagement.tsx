import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Users, Plus, Shield, RefreshCw, UserX, Key, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/services/apiClient';

interface CognitoUser {
  sub: string;
  email: string;
  status: string;
  enabled: boolean;
  groups: string[];
  role: string;
  mfa_enabled: boolean;
  created: string;
  last_modified: string;
}

const ROLES = ['Admin', 'Executive', 'SalesManager', 'Rep'];

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
    if (!confirm(`Disable user ${email}?`)) return;
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Users className="h-5 w-5" />
            User Management
          </h2>
          <p className="text-sm text-muted-foreground">Manage users, roles, and access</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchUsers} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            Add User
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>MFA</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2" />
                    Loading users...
                  </TableCell>
                </TableRow>
              ) : users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No users found
                  </TableCell>
                </TableRow>
              ) : users.map(user => (
                <TableRow key={user.sub}>
                  <TableCell className="font-medium">{user.email}</TableCell>
                  <TableCell>
                    <Badge variant={user.status === 'CONFIRMED' ? 'default' : 'secondary'} className="text-xs">
                      {user.status === 'CONFIRMED' ? 'Active' : user.status === 'FORCE_CHANGE_PASSWORD' ? 'Pending' : user.status}
                    </Badge>
                    {!user.enabled && <Badge variant="destructive" className="text-xs ml-1">Disabled</Badge>}
                  </TableCell>
                  <TableCell>
                    <Select
                      value={user.role}
                      onValueChange={(val) => handleRoleChange(user.sub, user.groups, val)}
                    >
                      <SelectTrigger className="h-8 w-[140px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLES.map(r => (
                          <SelectItem key={r} value={r}>{r}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    {user.mfa_enabled ? (
                      <Badge className="bg-green-100 text-green-800 text-xs">
                        <Shield className="h-3 w-3 mr-1" />
                        Enabled
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-xs text-muted-foreground">Off</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {user.created ? new Date(user.created).toLocaleDateString() : '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setResetTarget({ sub: user.sub, email: user.email })}>
                        <Key className="h-3 w-3 mr-1" />
                        Reset
                      </Button>
                      <Button variant="ghost" size="sm" className="h-7 text-xs text-orange-600" onClick={() => handleDisable(user.sub, user.email)}>
                        <UserX className="h-3 w-3 mr-1" />
                        Disable
                      </Button>
                      {user.role !== 'Admin' && (
                        <Button variant="ghost" size="sm" className="h-7 text-xs text-destructive" onClick={() => setDeleteTarget({ sub: user.sub, email: user.email })}>
                          <Trash2 className="h-3 w-3 mr-1" />
                          Delete
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create User Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New User</DialogTitle>
            <DialogDescription>
              Create a new user account. They will be prompted to change their password on first login.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" placeholder="user@example.com" value={newEmail} onChange={e => setNewEmail(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Temporary Password</Label>
              <Input type="password" placeholder="Min 8 characters" value={newPassword} onChange={e => setNewPassword(e.target.value)} />
              <p className="text-xs text-muted-foreground">Must include uppercase, lowercase, and numbers</p>
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={newRole} onValueChange={setNewRole}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map(r => (
                    <SelectItem key={r} value={r}>{r}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)} disabled={creating}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!newEmail || !newPassword || creating}>
              {creating ? <><RefreshCw className="h-4 w-4 mr-2 animate-spin" />Creating...</> : 'Create User'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Reset Password Dialog */}
      <Dialog open={!!resetTarget} onOpenChange={(open) => { if (!open) { setResetTarget(null); setResetTempPassword(''); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              Set a temporary password for <strong>{resetTarget?.email}</strong>. They will be required to choose a new password on their next login.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Temporary Password</Label>
              <Input
                type="password"
                placeholder="Min 8 characters"
                value={resetTempPassword}
                onChange={e => setResetTempPassword(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">Must include uppercase, lowercase, and numbers. The user will be logged out of all active sessions.</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setResetTarget(null); setResetTempPassword(''); }} disabled={resetting}>Cancel</Button>
            <Button onClick={handleResetPassword} disabled={resetting || resetTempPassword.length < 8}>
              {resetting ? <><RefreshCw className="h-4 w-4 mr-2 animate-spin" />Resetting...</> : 'Reset Password'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete User Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete User</DialogTitle>
            <DialogDescription>
              Are you sure you want to permanently delete <strong>{deleteTarget?.email}</strong>?
            </DialogDescription>
          </DialogHeader>
          <Alert variant="destructive">
            <AlertDescription>
              This action cannot be undone. The user account, all sessions, and associated data will be permanently removed.
            </AlertDescription>
          </Alert>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? <><RefreshCw className="h-4 w-4 mr-2 animate-spin" />Deleting...</> : 'Delete Permanently'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export { UserManagement as UserManagementPanel };
export default UserManagement;
