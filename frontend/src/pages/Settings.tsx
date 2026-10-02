import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, Settings as SettingsIcon, User, Shield, Bell, Palette, Globe, UserPlus, Key, Server, Lock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useEnterpriseAuth } from '@/context/EnterpriseAuthContext';
import { useRole } from '@/hooks/useRole';
import Layout from '@/components/Layout';
import RBACManager from '@/components/settings/RBACManager';
import UserInviteManager from '@/components/settings/UserInviteManager';
import { UserManagementPanel } from '@/pages/UserManagement';
import LogLevelSettings from '@/components/settings/LogLevelSettings';
import SystemSettings from '@/components/settings/SystemSettings';
import SecretsSettings from '@/components/settings/SecretsSettings';
import { LicensePage } from '@/components/settings/license';
import { RefreshProvider } from '@/context/RefreshContext';

const ChangePasswordSection: React.FC = () => {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleChangePassword = async () => {
    setMessage(null);
    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'New passwords do not match' });
      return;
    }
    if (newPassword.length < 8) {
      setMessage({ type: 'error', text: 'Password must be at least 8 characters' });
      return;
    }
    setSaving(true);
    try {
      const resp = await fetch('/api/v1/auth/password/change', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_password: currentPassword, new_password: newPassword })
      });
      const data = await resp.json();
      if (resp.ok && data.success) {
        setMessage({ type: 'success', text: 'Password changed successfully' });
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to change password' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Failed to change password' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {message && (
        <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label>Current Password</Label>
          <Input type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} placeholder="Enter current password" />
        </div>
        <div className="space-y-2">
          <Label>New Password</Label>
          <Input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="Min 8 characters" />
        </div>
        <div className="space-y-2">
          <Label>Confirm New Password</Label>
          <Input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="Re-enter new password" />
        </div>
      </div>
      <p className="text-xs text-muted-foreground">Must include uppercase, lowercase, and numbers</p>
      <Button onClick={handleChangePassword} disabled={saving || !currentPassword || !newPassword || !confirmPassword}>
        {saving ? 'Changing...' : 'Change Password'}
      </Button>
    </div>
  );
};

const MFASetupSection: React.FC = () => {
  const [step, setStep] = useState<'idle' | 'credentials' | 'loading' | 'qr' | 'verify' | 'done'>('idle');
  const [secret, setSecret] = useState('');
  const [totpUri, setTotpUri] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [accessToken, setAccessToken] = useState('');

  const [mfaEmail, setMfaEmail] = useState('');
  const [mfaPassword, setMfaPassword] = useState('');

  const startSetup = async () => {
    if (!mfaEmail || !mfaPassword) {
      setStep('credentials');
      return;
    }
    setStep('loading');
    setError('');
    try {
      const resp = await fetch('/api/v1/auth/mfa/setup', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: mfaEmail, password: mfaPassword }),
      });
      if (!resp.ok) {
        const d = await resp.json().catch(() => ({}));
        setError(d.detail || 'Failed to start MFA setup. Check your password.');
        setStep('credentials');
        return;
      }
      const data = await resp.json();
      setSecret(data.secret || '');
      setTotpUri(data.totp_uri || '');
      setAccessToken(data.access_token || '');
      setStep('qr');
    } catch {
      setError('Failed to connect');
      setStep('credentials');
    }
  };

  const verifyCode = async () => {
    setError('');
    try {
      const resp = await fetch('/api/v1/auth/mfa/setup/verify', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: accessToken, totp_code: code }),
      });
      if (resp.ok) {
        setStep('done');
      } else {
        const d = await resp.json().catch(() => ({}));
        setError(d.detail || 'Invalid code');
        setCode('');
      }
    } catch {
      setError('Verification failed');
    }
  };

  if (step === 'done') {
    return (
      <div className="flex items-center gap-2 text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 p-3 rounded border border-green-200 dark:border-green-800">
        <Shield className="h-5 w-5" />
        <span className="font-medium">MFA is enabled. Your account is protected with TOTP.</span>
      </div>
    );
  }

  if (step === 'qr') {
    return (
      <div className="space-y-4">
        <p className="text-sm">Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)</p>
        {totpUri && (
          <div className="flex justify-center p-4 bg-white rounded border border-border">
            <img src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(totpUri)}`} alt="TOTP QR" className="w-48 h-48" />
          </div>
        )}
        <details className="text-xs">
          <summary className="cursor-pointer text-blue-600 dark:text-blue-400">Can't scan? Show secret key</summary>
          <code className="block mt-1 p-2 bg-muted rounded font-mono select-all">{secret}</code>
        </details>
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <div className="flex items-center gap-2">
          <input type="text" inputMode="numeric" maxLength={6} placeholder="6-digit code" value={code}
            onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            className="border border-border rounded px-3 py-2 w-32 text-center font-mono text-lg tracking-widest bg-background text-foreground" autoFocus />
          <Button onClick={verifyCode} disabled={code.length !== 6}>Verify & Enable</Button>
        </div>
      </div>
    );
  }

  if (step === 'credentials') {
    return (
      <div className="space-y-3">
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <p className="text-sm text-muted-foreground">Enter your password to set up MFA.</p>
        <input type="email" placeholder="Email" value={mfaEmail} onChange={e => setMfaEmail(e.target.value)}
          className="border border-border rounded px-3 py-2 w-full text-sm bg-background text-foreground" />
        <input type="password" placeholder="Password" value={mfaPassword} onChange={e => setMfaPassword(e.target.value)}
          className="border border-border rounded px-3 py-2 w-full text-sm bg-background text-foreground" />
        <Button onClick={startSetup} disabled={!mfaEmail || !mfaPassword}>
          <Shield className="h-4 w-4 mr-2" /> Continue Setup
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <p className="text-sm text-muted-foreground">Add an extra layer of security to your account using a TOTP authenticator app.</p>
      <Button onClick={startSetup} disabled={step === 'loading'}>
        <Shield className="h-4 w-4 mr-2" />
        {step === 'loading' ? 'Setting up...' : 'Set Up MFA'}
      </Button>
    </div>
  );
};

const SettingsContent: React.FC = () => {
  const navigate = useNavigate();
  const { profile, loading } = useEnterpriseAuth();
  const { getRoleDisplayName, getRoleBadgeColor } = useRole();
  const [activeTab, setActiveTab] = useState('profile');

  // Check if user has admin access for RBAC settings (Admin and Executive can manage RBAC)
  const canManageRBAC = profile?.role === 'Admin' || profile?.role === 'Executive';
  
  // Check if user can manage users (Admin only)
  const canManageUsers = profile?.role === 'Admin';

  // Check if user can manage license (Admin or Executive)
  const canManageLicense = profile?.role === 'Admin' || profile?.role === 'Executive';

  // Check if user can manage system settings (Admin only)
  const canManageSystem = profile?.role === 'Admin';

  // Check if user can manage secrets (Admin only)
  const canManageSecrets = profile?.role === 'Admin';


  // Show loading state while profile is loading
  if (loading) {
    return (
      <Layout title="Settings">
        <div className="flex items-center justify-center h-screen">
            <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading settings...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Settings">
      <div className="min-h-screen bg-gray-50 dark:bg-transparent p-6">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <h1 className="text-3xl font-bold flex items-center gap-2">
                  <SettingsIcon className="h-8 w-8" />
                  Settings
                </h1>
                <p className="text-gray-500 dark:text-slate-400 mt-1">Manage your account and application preferences</p>
              </div>
            </div>
            {profile && (
              <div className="flex items-center gap-2">
                <Badge className={getRoleBadgeColor}>
                  {getRoleDisplayName}
                </Badge>
              </div>
            )}
          </div>

          {/* Settings Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="flex flex-wrap gap-1 h-auto p-1 justify-start">
              <TabsTrigger value="profile" className="flex items-center gap-2">
                <User className="h-4 w-4" />
                Profile
              </TabsTrigger>
              <TabsTrigger value="appearance" className="flex items-center gap-2">
                <Palette className="h-4 w-4" />
                Appearance
              </TabsTrigger>
              <TabsTrigger value="notifications" className="flex items-center gap-2">
                <Bell className="h-4 w-4" />
                Notifications
              </TabsTrigger>
              <TabsTrigger value="language" className="flex items-center gap-2">
                <Globe className="h-4 w-4" />
                Language
              </TabsTrigger>
              {canManageLicense && (
                <TabsTrigger value="license" className="flex items-center gap-2">
                  <Key className="h-4 w-4" />
                  License
                </TabsTrigger>
              )}
              {canManageUsers && (
                <TabsTrigger value="users" className="flex items-center gap-2">
                  <UserPlus className="h-4 w-4" />
                  User Management
                </TabsTrigger>
              )}
              {canManageRBAC && (
                <TabsTrigger value="rbac" className="flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  RBAC
                </TabsTrigger>
              )}
              {canManageSystem && (
                <TabsTrigger value="system" className="flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  System
                </TabsTrigger>
              )}
              {canManageSecrets && (
                <TabsTrigger value="secrets" className="flex items-center gap-2">
                  <Lock className="h-4 w-4" />
                  Secrets
                </TabsTrigger>
              )}
              <TabsTrigger value="advanced" className="flex items-center gap-2">
                <SettingsIcon className="h-4 w-4" />
                Advanced
              </TabsTrigger>
            </TabsList>

            {/* Profile Settings */}
            <TabsContent value="profile" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Profile Information</CardTitle>
                  <CardDescription>Manage your account details and personal information</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {profile ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="text-sm font-medium text-foreground">Full Name</label>
                        <p className="mt-1 p-2 bg-muted rounded border border-border">{profile.full_name || 'Not set'}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-foreground">Email</label>
                        <p className="mt-1 p-2 bg-muted rounded border border-border">{profile.email}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-foreground">Role</label>
                        <div className="mt-1">
                          <Badge className={getRoleBadgeColor}>{getRoleDisplayName}</Badge>
                        </div>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-foreground">Department</label>
                        <p className="mt-1 p-2 bg-muted rounded border border-border">{profile.department || 'Not set'}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-foreground">Employee ID</label>
                        <p className="mt-1 p-2 bg-muted rounded border border-border">{profile.employeeId || 'Not set'}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-foreground">Last Login</label>
                        <p className="mt-1 p-2 bg-muted rounded border border-border">
                          {new Date(profile.lastLogin).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-muted-foreground">Loading profile information...</p>
                  )}
                </CardContent>
              </Card>

              {/* Change Password */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><Key className="h-5 w-5" /> Change Password</CardTitle>
                  <CardDescription>Update your account password</CardDescription>
                </CardHeader>
                <CardContent>
                  <ChangePasswordSection />
                </CardContent>
              </Card>

              {/* MFA Setup */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><Lock className="h-5 w-5" /> Two-Factor Authentication</CardTitle>
                  <CardDescription>Secure your account with TOTP-based two-factor authentication</CardDescription>
                </CardHeader>
                <CardContent>
                  <MFASetupSection />
                </CardContent>
              </Card>



            </TabsContent>

            {/* Appearance Settings */}
            <TabsContent value="appearance" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Appearance Settings</CardTitle>
                  <CardDescription>Customize the look and feel of your dashboard</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">Theme and appearance customization options coming soon...</p>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Notifications Settings */}
            <TabsContent value="notifications" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Notification Preferences</CardTitle>
                  <CardDescription>Configure how and when you receive notifications</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">Notification settings coming soon...</p>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Language Settings */}
            <TabsContent value="language" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Language & Regional Settings</CardTitle>
                  <CardDescription>Choose your preferred language and regional format</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">Language settings coming soon...</p>
                </CardContent>
              </Card>
            </TabsContent>

            {/* License Management - Admin/Executive Only */}
            <TabsContent value="license" className="space-y-6">
              {canManageLicense ? (
                <LicensePage />
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Access Restricted</CardTitle>
                    <CardDescription>License management is only available for Admin and Executive users</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">You need Admin or Executive privileges to manage licenses.</p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* User Management - Admin Only */}
            <TabsContent value="users" className="space-y-6">
              {canManageUsers ? (
                <Tabs defaultValue="manage-users">
                  <TabsList>
                    <TabsTrigger value="manage-users">Users</TabsTrigger>
                    <TabsTrigger value="invitations">Invitations</TabsTrigger>
                  </TabsList>
                  <TabsContent value="manage-users" className="mt-4">
                    <UserManagementPanel />
                  </TabsContent>
                  <TabsContent value="invitations" className="mt-4">
                    <UserInviteManager />
                  </TabsContent>
                </Tabs>
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Access Restricted</CardTitle>
                    <CardDescription>User management is only available for Admin users</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">You need Admin privileges to invite and manage users.</p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* RBAC Settings - Admin/Executive Only */}
            <TabsContent value="rbac" className="space-y-6">
              {canManageRBAC ? (
                <RBACManager />
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Access Restricted</CardTitle>
                    <CardDescription>RBAC management is only available for Admin and Executive users</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">You need Admin or Executive privileges to access role and permission management.</p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* System Settings - Admin Only */}
            <TabsContent value="system" className="space-y-6">
              {canManageSystem ? (
                <SystemSettings />
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Access Restricted</CardTitle>
                    <CardDescription>System settings are only available for Admin users</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">You need Admin privileges to manage system configuration parameters.</p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Secrets Settings - Admin Only */}
            <TabsContent value="secrets" className="space-y-6">
              {canManageSecrets ? (
                <SecretsSettings />
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Access Restricted</CardTitle>
                    <CardDescription>Secrets management is only available for Admin users</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">You need Admin privileges to manage secrets and credentials.</p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>


            {/* Advanced Settings */}
            <TabsContent value="advanced" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Advanced Settings</CardTitle>
                  <CardDescription>Advanced configuration options for power users</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-4">
                    These settings are intended for advanced users and administrators.
                  </p>
                </CardContent>
              </Card>
              
              {/* Backend Log Level Settings */}
              <LogLevelSettings />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </Layout>
  );
};

const Settings: React.FC = () => {
  return (
    <RefreshProvider>
      <SettingsContent />
    </RefreshProvider>
  );
};

export default Settings;
