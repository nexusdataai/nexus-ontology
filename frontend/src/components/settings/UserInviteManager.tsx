import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from '@/hooks/use-toast';
import { useEnterpriseAuth } from '@/context/EnterpriseAuthContext';
import { UserRole, UserInvitation, Permission } from '@/types/auth';
import {
  inviteUser,
  getUserInvitations,
  resendInvitation,
  revokeInvitation,
  isValidEmail
} from '@/services/userInviteService';
import { confirmDialog } from '@/components/ds/confirm';
import { Icon } from '@/components/ds/Icon';
import { Field, StatusPill, TableShell, type Tone } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { cn } from '@/lib/utils';

const ROLE_LABEL: Record<string, string> = {
  Admin: 'Admin',
  Executive: 'Executive',
  SalesManager: 'Sales manager',
  Rep: 'Rep',
};

const STATUS_TONE: Record<string, Tone> = {
  pending: 'warning',
  accepted: 'success',
  expired: 'neutral',
  revoked: 'danger',
};

const formatDate = (iso: string) => {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? 'Not recorded' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

const HEAD = 'whitespace-nowrap border-b border-border bg-surface-2 px-5 py-2.5 text-left text-xs font-medium text-muted-foreground';

const UserInviteManager: React.FC = () => {
  const { profile, hasPermission } = useEnterpriseAuth();
  const [email, setEmail] = useState('');
  const [selectedRole, setSelectedRole] = useState<UserRole>('Rep');
  const [invitations, setInvitations] = useState<UserInvitation[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchingInvitations, setFetchingInvitations] = useState(false);
  const [lastInvitedPassword, setLastInvitedPassword] = useState<string | null>(null);
  const [copiedPassword, setCopiedPassword] = useState(false);

  const canInviteUsers = hasPermission(Permission.INVITE_USERS);

  useEffect(() => {
    if (canInviteUsers) {
      loadInvitations();
    }
  }, [canInviteUsers]);

  const loadInvitations = async () => {
    try {
      setFetchingInvitations(true);
      const data = await getUserInvitations();
      setInvitations(data);
    } catch (error) {
      console.error('Error loading invitations:', error);
      toast({
        title: 'Error',
        description: 'Failed to load user invitations',
        variant: 'destructive',
      });
    } finally {
      setFetchingInvitations(false);
    }
  };

  const handleInviteUser = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isValidEmail(email)) {
      toast({
        title: 'Invalid email',
        description: 'Please enter a valid email address',
        variant: 'destructive',
      });
      return;
    }

    if (!profile) {
      toast({
        title: 'Error',
        description: 'User profile not loaded',
        variant: 'destructive',
      });
      return;
    }

    try {
      setLoading(true);
      const invitation = await inviteUser(email, selectedRole, profile.id, profile.full_name || profile.email);

      setLastInvitedPassword(invitation.temporaryPassword || null);

      toast({
        title: 'Invitation sent',
        description: `Invitation sent to ${email} with role ${selectedRole}`,
      });

      setEmail('');
      setSelectedRole('Rep');
      await loadInvitations();
    } catch (error) {
      console.error('Error inviting user:', error);
      toast({
        title: 'Invitation failed',
        description: 'Failed to invite user. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleResendInvitation = async (invitationId: string, userEmail: string) => {
    try {
      await resendInvitation(invitationId);
      toast({
        title: 'Invitation resent',
        description: `Invitation email resent to ${userEmail}`,
      });
    } catch (error) {
      console.error('Error resending invitation:', error);
      toast({
        title: 'Resend failed',
        description: 'Failed to resend invitation',
        variant: 'destructive',
      });
    }
  };

  const handleRevokeInvitation = async (invitationId: string, userEmail: string) => {
    if (!(await confirmDialog({ title: `Revoke the invitation for ${userEmail}?`, description: 'This deletes the user from the system.', confirmLabel: 'Revoke', destructive: true }))) {
      return;
    }

    try {
      await revokeInvitation(invitationId);
      toast({
        title: 'Invitation revoked',
        description: `Invitation for ${userEmail} has been revoked`,
      });
      await loadInvitations();
    } catch (error) {
      console.error('Error revoking invitation:', error);
      toast({
        title: 'Revoke failed',
        description: 'Failed to revoke invitation',
        variant: 'destructive',
      });
    }
  };

  const copyPasswordToClipboard = async () => {
    if (lastInvitedPassword) {
      await navigator.clipboard.writeText(lastInvitedPassword);
      setCopiedPassword(true);
      setTimeout(() => setCopiedPassword(false), 2000);
      toast({
        title: 'Copied',
        description: 'Password copied to clipboard',
      });
    }
  };

  if (!canInviteUsers) {
    return (
      <EmptyState
        icon="lock"
        title="Inviting users is restricted"
        description="Only administrators can invite new people. Ask an administrator if someone needs access."
      />
    );
  }

  const pending = invitations.filter(i => i.status === 'pending').length;

  return (
    <div className="space-y-6">
      {/* Invite someone */}
      <section className="grid gap-x-10 gap-y-4 border-b border-border pb-6 xl:grid-cols-[240px_minmax(0,1fr)]">
        <div>
          <h2 className="text-md font-medium text-foreground">Invite someone</h2>
          <p className="mt-1 text-sm text-muted-foreground">They get a role and a temporary password, and choose their own the first time they sign in.</p>
        </div>
        <div className="min-w-0">
          <form onSubmit={handleInviteUser} className="grid max-w-2xl items-end gap-3 sm:grid-cols-[minmax(0,1fr)_180px_auto]">
            <Field label="Email" htmlFor="invite-email">
              <Input
                id="invite-email"
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </Field>
            <Field label="Role" htmlFor="invite-role">
              <Select value={selectedRole} onValueChange={(value) => setSelectedRole(value as UserRole)}>
                <SelectTrigger id="invite-role">
                  <SelectValue placeholder="Select role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Executive">Executive</SelectItem>
                  <SelectItem value="SalesManager">Sales manager</SelectItem>
                  <SelectItem value="Rep">Rep</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Button type="submit" disabled={loading}>
              <Icon name={loading ? 'spinner' : 'send'} className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
              {loading ? 'Sending' : 'Send invitation'}
            </Button>
          </form>

          {lastInvitedPassword && (
            <div className="mt-4 max-w-2xl border-t border-border pt-4 animate-fade-up">
              <p className="text-sm font-medium text-foreground">Temporary password for the last invitation</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <code className="select-all rounded-md border border-border bg-surface-2 px-2.5 py-1.5 font-mono text-sm text-foreground">{lastInvitedPassword}</code>
                <Button variant="outline" size="sm" onClick={copyPasswordToClipboard}>
                  <Icon name={copiedPassword ? 'check' : 'copy'} className="h-3.5 w-3.5" />
                  {copiedPassword ? 'Copied' : 'Copy'}
                </Button>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Share it with the person over a safe channel. They must change it when they first sign in.
              </p>
            </div>
          )}

          <p className="mt-4 flex max-w-2xl items-start gap-2 text-xs text-muted-foreground">
            <Icon name="info" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-subtle-foreground" />
            Invitations are a preview: sending them for real needs the sign-in directory to be connected on the server.
          </p>
        </div>
      </section>

      {/* Invitations */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-md font-medium text-foreground">Invitations</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {invitations.length === 0
                ? 'Who has been invited and whether they have joined.'
                : <>
                    <span className="num font-medium text-foreground">{invitations.length}</span> sent,{' '}
                    <span className="num font-medium text-foreground">{pending}</span> still waiting.
                  </>}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={loadInvitations} disabled={fetchingInvitations}>
            <Icon name="refresh" className={cn('h-3.5 w-3.5', fetchingInvitations && 'animate-spin')} /> Refresh
          </Button>
        </div>

        {fetchingInvitations && invitations.length === 0 ? (
          <div className="space-y-px overflow-hidden rounded-xl border border-border" aria-busy="true">
            {[0, 1, 2].map(i => <Skeleton key={i} className="h-14 w-full rounded-none" />)}
          </div>
        ) : invitations.length === 0 ? (
          <EmptyState icon="mail" title="No invitations yet" description="People you invite appear here until they sign in for the first time." />
        ) : (
          <TableShell>
            <table className="w-full min-w-[720px] border-collapse text-sm">
              <thead>
                <tr>
                  <th scope="col" className={HEAD}>Email</th>
                  <th scope="col" className={HEAD}>Role</th>
                  <th scope="col" className={HEAD}>Status</th>
                  <th scope="col" className={HEAD}>Invited by</th>
                  <th scope="col" className={HEAD}>Invited</th>
                  <th scope="col" className={HEAD}><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {invitations.map((invitation, i) => (
                  <tr key={invitation.id} className="rise border-b border-border transition-colors last:border-b-0 hover:bg-surface-2/60" style={{ '--i': Math.min(i, 12) } as React.CSSProperties}>
                    <td className="max-w-[280px] truncate px-5 py-3 font-medium text-foreground" title={invitation.email}>{invitation.email}</td>
                    <td className="whitespace-nowrap px-5 py-3 text-foreground">{ROLE_LABEL[invitation.role] || invitation.role}</td>
                    <td className="whitespace-nowrap px-5 py-3">
                      <StatusPill tone={STATUS_TONE[invitation.status] || 'neutral'}>{invitation.status}</StatusPill>
                    </td>
                    <td className="px-5 py-3 text-muted-foreground">{invitation.invitedByName}</td>
                    <td className="num whitespace-nowrap px-5 py-3 text-muted-foreground">{formatDate(invitation.invitedAt)}</td>
                    <td className="px-5 py-2 text-right">
                      {invitation.status === 'pending' && (
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => handleResendInvitation(invitation.id, invitation.email)}>
                            <Icon name="mail" className="h-3.5 w-3.5" /> Resend
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-muted-foreground hover:text-destructive"
                            aria-label={`Revoke the invitation for ${invitation.email}`}
                            title="Revoke invitation"
                            onClick={() => handleRevokeInvitation(invitation.id, invitation.email)}
                          >
                            <Icon name="trash" className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </section>
    </div>
  );
};

export default UserInviteManager;
