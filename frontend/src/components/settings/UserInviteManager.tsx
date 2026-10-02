import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
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
import { UserPlus, Mail, Trash2, RefreshCw, AlertCircle, Copy, CheckCircle } from 'lucide-react';

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
        title: 'Invalid Email',
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
        title: 'User Invited Successfully',
        description: `Invitation sent to ${email} with role ${selectedRole}`,
      });

      setEmail('');
      setSelectedRole('Rep');
      await loadInvitations();
    } catch (error) {
      console.error('Error inviting user:', error);
      toast({
        title: 'Invitation Failed',
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
        title: 'Invitation Resent',
        description: `Invitation email resent to ${userEmail}`,
      });
    } catch (error) {
      console.error('Error resending invitation:', error);
      toast({
        title: 'Resend Failed',
        description: 'Failed to resend invitation',
        variant: 'destructive',
      });
    }
  };

  const handleRevokeInvitation = async (invitationId: string, userEmail: string) => {
    if (!confirm(`Are you sure you want to revoke the invitation for ${userEmail}? This will delete the user from the system.`)) {
      return;
    }

    try {
      await revokeInvitation(invitationId);
      toast({
        title: 'Invitation Revoked',
        description: `Invitation for ${userEmail} has been revoked`,
      });
      await loadInvitations();
    } catch (error) {
      console.error('Error revoking invitation:', error);
      toast({
        title: 'Revoke Failed',
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

  const getRoleBadgeColor = (role: UserRole) => {
    switch (role) {
      case 'Admin':
        return 'bg-red-500 hover:bg-red-600';
      case 'Executive':
        return 'bg-purple-500 hover:bg-purple-600';
      case 'SalesManager':
        return 'bg-blue-500 hover:bg-blue-600';
      case 'Rep':
        return 'bg-green-500 hover:bg-green-600';
      default:
        return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-500 hover:bg-yellow-600';
      case 'accepted':
        return 'bg-green-500 hover:bg-green-600';
      case 'expired':
        return 'bg-gray-500 hover:bg-gray-600';
      case 'revoked':
        return 'bg-red-500 hover:bg-red-600';
      default:
        return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  if (!canInviteUsers) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Access Restricted</CardTitle>
          <CardDescription>User invitation is only available for Admin users</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500">You need Admin privileges to invite new users to the system.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Invite User Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5" />
            Invite New User
          </CardTitle>
          <CardDescription>Send an invitation to a new user with assigned role and temporary password</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              This is a placeholder UI. Backend API integration with AWS Cognito is required for full functionality.
              Check browser console for implementation details.
            </AlertDescription>
          </Alert>

          <form onSubmit={handleInviteUser} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="user@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Select value={selectedRole} onValueChange={(value) => setSelectedRole(value as UserRole)}>
                  <SelectTrigger id="role">
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Executive">Executive</SelectItem>
                    <SelectItem value="SalesManager">Sales Manager</SelectItem>
                    <SelectItem value="Rep">Rep</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button type="submit" disabled={loading} className="w-full md:w-auto">
              {loading ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Sending Invitation...
                </>
              ) : (
                <>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Send Invitation
                </>
              )}
            </Button>
          </form>

          {lastInvitedPassword && (
            <Alert className="mt-4 bg-blue-50 border-blue-200">
              <AlertCircle className="h-4 w-4 text-blue-600" />
              <AlertDescription>
                <div className="flex items-center justify-between">
                  <div>
                    <strong>Temporary Password Generated:</strong>
                    <code className="ml-2 px-2 py-1 bg-white rounded border text-sm">{lastInvitedPassword}</code>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={copyPasswordToClipboard}
                    className="ml-2"
                  >
                    {copiedPassword ? (
                      <>
                        <CheckCircle className="h-4 w-4 mr-1" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4 mr-1" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>
                <p className="text-xs mt-2 text-gray-600">
                  Share this password securely with the invited user. They will be required to change it on first login.
                </p>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Invitations List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>User Invitations</CardTitle>
              <CardDescription>Manage pending and active user invitations</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={loadInvitations} disabled={fetchingInvitations}>
              <RefreshCw className={`h-4 w-4 mr-2 ${fetchingInvitations ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {fetchingInvitations ? (
            <div className="text-center py-8">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto text-gray-400" />
              <p className="text-gray-500 mt-2">Loading invitations...</p>
            </div>
          ) : invitations.length === 0 ? (
            <div className="text-center py-8">
              <UserPlus className="h-12 w-12 mx-auto text-gray-300" />
              <p className="text-gray-500 mt-2">No pending invitations</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Invited By</TableHead>
                    <TableHead>Invited Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invitations.map((invitation) => (
                    <TableRow key={invitation.id}>
                      <TableCell className="font-medium">{invitation.email}</TableCell>
                      <TableCell>
                        <Badge className={getRoleBadgeColor(invitation.role)}>
                          {invitation.role}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={getStatusBadgeColor(invitation.status)}>
                          {invitation.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{invitation.invitedByName}</TableCell>
                      <TableCell>{new Date(invitation.invitedAt).toLocaleDateString()}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          {invitation.status === 'pending' && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleResendInvitation(invitation.id, invitation.email)}
                                title="Resend invitation email"
                              >
                                <Mail className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleRevokeInvitation(invitation.id, invitation.email)}
                                title="Revoke invitation"
                              >
                                <Trash2 className="h-4 w-4 text-red-500" />
                              </Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default UserInviteManager;

