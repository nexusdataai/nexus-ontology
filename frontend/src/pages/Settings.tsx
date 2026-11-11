import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useNavigate } from 'react-router-dom';
import { useEnterpriseAuth } from '@/context/EnterpriseAuthContext';
import { useRole } from '@/hooks/useRole';
import Layout from '@/components/Layout';
import { useUrlTab } from '@/components/ds/PageTabs';
import { Icon, type IconName } from '@/components/ds/Icon';
import { useTheme } from '@/hooks/use-theme';
import { Skeleton } from '@/components/ui/skeleton';
import { Field, InlineError, KeyValues } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import RBACManager from '@/components/settings/RBACManager';
import UserInviteManager from '@/components/settings/UserInviteManager';
import { UserManagementPanel } from '@/pages/UserManagement';
import LogLevelSettings from '@/components/settings/LogLevelSettings';
import SystemSettings from '@/components/settings/SystemSettings';
import SecretsSettings from '@/components/settings/SecretsSettings';
import { LicensePage } from '@/components/settings/license';
import { RefreshProvider } from '@/context/RefreshContext';

/** Settings sections, grouped. `gate` hides an item from roles that cannot use it. */
const SETTINGS_MENU: { label: string; items: { value: string; label: string; icon: IconName; gate?: string }[] }[] = [
  { label: 'Account', items: [
    { value: 'profile', label: 'Profile', icon: 'user' },
    { value: 'appearance', label: 'Appearance', icon: 'sun' },
    { value: 'notifications', label: 'Notifications', icon: 'bell' },
    { value: 'language', label: 'Language', icon: 'globe' },
  ] },
  { label: 'Organisation', items: [
    { value: 'license', label: 'License', icon: 'key', gate: 'license' },
    { value: 'users', label: 'Users', icon: 'users', gate: 'users' },
    { value: 'rbac', label: 'Roles and permissions', icon: 'shield-check', gate: 'rbac' },
  ] },
  { label: 'Platform', items: [
    { value: 'system', label: 'System', icon: 'server', gate: 'system' },
    { value: 'secrets', label: 'Secrets', icon: 'lock', gate: 'secrets' },
    { value: 'advanced', label: 'Advanced', icon: 'sliders' },
  ] },
];

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
    <div className="space-y-5">
      {message && (
        message.type === 'error'
          ? <InlineError>{message.text}</InlineError>
          : <p className="flex items-center gap-2 text-sm text-foreground"><Icon name="check-circle" className="h-4 w-4 text-success" />{message.text}</p>
      )}
      <div className="grid max-w-3xl grid-cols-1 gap-4 md:grid-cols-3">
        <Field label="Current password" htmlFor="pw-current">
          <Input id="pw-current" type="password" autoComplete="current-password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} />
        </Field>
        <Field label="New password" htmlFor="pw-new">
          <Input id="pw-new" type="password" autoComplete="new-password" value={newPassword} onChange={e => setNewPassword(e.target.value)} />
        </Field>
        <Field label="Confirm new password" htmlFor="pw-confirm">
          <Input id="pw-confirm" type="password" autoComplete="new-password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} />
        </Field>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleChangePassword} disabled={saving || !currentPassword || !newPassword || !confirmPassword}>
          {saving ? 'Changing' : 'Change password'}
        </Button>
        <span className="text-xs text-muted-foreground">At least 8 characters, with upper case, lower case and a number.</span>
      </div>
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
      <p className="flex items-center gap-2 text-sm text-foreground">
        <Icon name="shield-check" className="h-4 w-4 text-success" />
        Two-step sign-in is on. Your account asks for a code from your authenticator app.
      </p>
    );
  }

  if (step === 'qr') {
    return (
      <div className="grid max-w-2xl gap-6 sm:grid-cols-[auto_minmax(0,1fr)]">
        {totpUri && (
          <div className="flex h-[216px] w-[216px] items-center justify-center rounded-xl border border-border bg-white p-2">
            <img src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(totpUri)}`} alt="QR code for your authenticator app" className="h-48 w-48" />
          </div>
        )}
        <div className="space-y-4">
          <ol className="list-decimal space-y-1.5 pl-5 text-sm text-muted-foreground">
            <li>Open your authenticator app (Google Authenticator, Authy or similar).</li>
            <li>Scan the QR code.</li>
            <li>Enter the 6-digit code the app shows.</li>
          </ol>
          <details className="text-xs">
            <summary className="cursor-pointer text-primary dark:text-brand-hi">Cannot scan? Show the secret key</summary>
            <code className="mt-1.5 block select-all rounded-md border border-border bg-surface-2 p-2 font-mono text-foreground">{secret}</code>
          </details>
          {error && <InlineError>{error}</InlineError>}
          <div className="flex items-center gap-2">
            <Input
              type="text" inputMode="numeric" maxLength={6} placeholder="000000" aria-label="6-digit code" value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              className="w-32 text-center font-mono text-lg tracking-widest" autoFocus
            />
            <Button onClick={verifyCode} disabled={code.length !== 6}>Verify and turn on</Button>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'credentials') {
    return (
      <div className="max-w-sm space-y-4">
        {error && <InlineError>{error}</InlineError>}
        <p className="text-sm text-muted-foreground">Confirm it is you before setting up two-step sign-in.</p>
        <Field label="Email" htmlFor="mfa-email">
          <Input id="mfa-email" type="email" autoComplete="email" value={mfaEmail} onChange={e => setMfaEmail(e.target.value)} />
        </Field>
        <Field label="Password" htmlFor="mfa-password">
          <Input id="mfa-password" type="password" autoComplete="current-password" value={mfaPassword} onChange={e => setMfaPassword(e.target.value)} />
        </Field>
        <Button onClick={startSetup} disabled={!mfaEmail || !mfaPassword}>Continue</Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && <InlineError>{error}</InlineError>}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-card p-4">
        <div className="flex min-w-0 items-start gap-3">
          <Icon name="shield-check" className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
          <div>
            <p className="text-sm font-medium text-foreground">Authenticator app</p>
            <p className="text-sm text-muted-foreground">Sign in with your password and a 6-digit code from your phone.</p>
          </div>
        </div>
        <Button variant="outline" onClick={startSetup} disabled={step === 'loading'}>
          {step === 'loading' ? 'Setting up' : 'Set up'}
        </Button>
      </div>
    </div>
  );
};

/** Miniature of the app in one theme. Literal greys on purpose: it shows the theme you are not in. */
const ThemePreview: React.FC<{ dark: boolean }> = ({ dark }) => {
  const c = dark
    ? { bg: 'hsl(220 13% 7%)', side: 'hsl(220 12% 9%)', card: 'hsl(220 11% 12%)', line: 'hsl(220 9% 20%)', text: 'hsl(220 10% 62%)' }
    : { bg: 'hsl(220 20% 98%)', side: 'hsl(220 16% 96%)', card: 'hsl(0 0% 100%)', line: 'hsl(220 13% 89%)', text: 'hsl(220 9% 58%)' };
  return (
    <div className="flex h-28 overflow-hidden rounded-lg border" style={{ background: c.bg, borderColor: c.line }} aria-hidden="true">
      <div className="flex w-[26%] flex-col gap-1.5 border-r p-2" style={{ background: c.side, borderColor: c.line }}>
        <span className="h-2 w-8 rounded-full bg-primary" />
        {[10, 12, 9, 11].map((w, i) => <span key={i} className="h-1.5 rounded-full" style={{ width: w * 4, maxWidth: '100%', background: c.line }} />)}
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-2 p-2.5">
        <span className="h-2 w-16 rounded-full" style={{ background: c.text }} />
        <div className="grid flex-1 grid-cols-3 gap-1.5">
          {[0, 1, 2].map(i => (
            <div key={i} className="flex flex-col justify-end gap-1 rounded-md border p-1.5" style={{ background: c.card, borderColor: c.line }}>
              <span className="h-1.5 w-6 rounded-full" style={{ background: c.line }} />
              <span className="h-1 rounded-full bg-primary" style={{ width: `${[70, 45, 85][i]}%`, opacity: i === 1 ? 0.5 : 1 }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const AppearanceChoice: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const options: { value: 'dark' | 'light'; label: string; hint: string }[] = [
    { value: 'dark', label: 'Graphite', hint: 'Dark surfaces, easier in low light' },
    { value: 'light', label: 'Paper', hint: 'Light surfaces, best in bright rooms' },
  ];
  return (
    <div role="radiogroup" aria-label="Theme" className="grid max-w-2xl gap-4 sm:grid-cols-2">
      {options.map(o => {
        const on = theme === o.value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => setTheme(o.value)}
            className={`group rounded-xl border p-2.5 text-left transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
              on ? 'border-brand ring-2 ring-brand/25' : 'border-border hover:-translate-y-0.5 hover:border-border-strong hover:shadow-md'
            }`}
          >
            <ThemePreview dark={o.value === 'dark'} />
            <span className="mt-3 flex items-center justify-between gap-3 px-1 pb-1">
              <span className="min-w-0">
                <span className="block text-sm font-medium text-foreground">{o.label}</span>
                <span className="block text-xs text-muted-foreground">{o.hint}</span>
              </span>
              <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${on ? 'border-primary bg-primary text-primary-foreground' : 'border-border-strong'}`}>
                {on && <Icon name="check" className="h-3 w-3" />}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
};

/** One settings block: what it is on the left, the controls on the right. */
const Block: React.FC<{ title: string; description?: string; children: React.ReactNode }> = ({ title, description, children }) => (
  <section className="grid gap-x-10 gap-y-4 border-b border-border py-8 first:pt-0 last:border-b-0 xl:grid-cols-[240px_minmax(0,1fr)]">
    <div>
      <h2 className="text-md font-medium text-foreground">{title}</h2>
      {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
    </div>
    <div className="min-w-0">{children}</div>
  </section>
);

const Restricted: React.FC<{ what: string; who: string }> = ({ what, who }) => (
  <EmptyState icon="lock" title={`${what} is restricted`} description={`Only ${who} can open this section. Ask an administrator if you need access.`} />
);

const SettingsContent: React.FC = () => {
  const navigate = useNavigate();
  const { profile, loading } = useEnterpriseAuth();
  const { getRoleDisplayName, getRoleBadgeColor } = useRole();
  const [activeTab, setActiveTab] = useUrlTab('profile');

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


  const gates: Record<string, boolean> = {
    license: canManageLicense, users: canManageUsers, rbac: canManageRBAC,
    system: canManageSystem, secrets: canManageSecrets,
  };

  // Show loading state while profile is loading
  if (loading) {
    return (
      <Layout title="Settings">
        <div className="page text-sm text-muted-foreground">Loading settings…</div>
      </Layout>
    );
  }

  return (
    <Layout title="Settings">
      <div className="page">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-lg font-medium tracking-tight text-foreground">Settings</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">Manage your account, your organisation and the platform configuration.</p>
          </div>
          {profile && <span className="text-sm text-muted-foreground">Signed in as <span className="text-foreground">{getRoleDisplayName}</span></span>}
        </div>

        <div className="mt-6">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="grid grid-cols-[minmax(0,1fr)] gap-x-10 gap-y-6 lg:grid-cols-[210px_minmax(0,1fr)]">
            {/* Section menu: a column on desktop, a scrolling row on phones */}
            <nav aria-label="Settings sections" className="scrollbar-hide -mx-4 flex gap-1 overflow-x-auto px-4 lg:mx-0 lg:block lg:space-y-5 lg:overflow-visible lg:px-0">
              {SETTINGS_MENU.map(group => {
                const items = group.items.filter(i => !i.gate || gates[i.gate]);
                if (items.length === 0) return null;
                return (
                  <div key={group.label} className="flex gap-1 lg:block">
                    <div className="eyebrow hidden px-2 pb-1.5 lg:block">{group.label}</div>
                    <div className="flex gap-1 lg:block lg:space-y-px">
                      {items.map(item => {
                        const on = activeTab === item.value;
                        return (
                          <button
                            key={item.value}
                            type="button"
                            onClick={() => setActiveTab(item.value)}
                            aria-current={on ? 'page' : undefined}
                            className={`flex h-8 shrink-0 items-center gap-2.5 whitespace-nowrap rounded-md px-2 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring lg:w-full ${
                              on ? 'bg-accent font-medium text-foreground' : 'text-muted-foreground hover:bg-accent/70 hover:text-foreground'
                            }`}
                          >
                            <Icon name={item.icon} className={on ? 'text-primary dark:text-brand-hi' : 'text-subtle-foreground'} />
                            {item.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </nav>

            {/* Profile */}
            <TabsContent value="profile" className="mt-0">
              <Block title="Profile" description="Your details come from your organisation's directory. Ask an administrator to change them.">
                {profile ? (
                  <>
                    <div className="flex items-center gap-4">
                      <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-border bg-surface-2 text-lg font-medium text-foreground">
                        {(profile.full_name || profile.email || '?').split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((w: string) => w[0]?.toUpperCase()).join('')}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-lg font-medium tracking-tight text-foreground">{profile.full_name || 'Name not set'}</p>
                        <p className="truncate text-sm text-muted-foreground">{profile.email}</p>
                      </div>
                    </div>
                    <div className="mt-5 max-w-xl">
                      <KeyValues
                        items={[
                          { label: 'Role', value: getRoleDisplayName },
                          { label: 'Department', value: profile.department || 'Not set' },
                          { label: 'Employee ID', value: profile.employeeId || 'Not set', mono: !!profile.employeeId },
                          { label: 'Last sign-in', value: profile.lastLogin ? new Date(profile.lastLogin).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Not recorded' },
                        ]}
                      />
                    </div>
                  </>
                ) : (
                  <div className="space-y-3"><Skeleton className="h-14 w-64" /><Skeleton className="h-24 w-full max-w-xl" /></div>
                )}
              </Block>
              <Block title="Password" description="Use a password you do not use anywhere else.">
                <ChangePasswordSection />
              </Block>
              <Block title="Two-step sign-in" description="A second check when you sign in, so a stolen password is not enough.">
                <MFASetupSection />
              </Block>
            </TabsContent>

            {/* Appearance */}
            <TabsContent value="appearance" className="mt-0">
              <Block title="Theme" description="How Nexus AI looks on this device. The choice is saved in this browser.">
                <AppearanceChoice />
              </Block>
            </TabsContent>

            {/* Notifications */}
            <TabsContent value="notifications" className="mt-0">
              <Block title="Notifications" description="Choose what you are told about and where.">
                <EmptyState icon="bell" title="Not available yet" description="Alerts from solutions already appear in each solution's Reports. Email and in-app notification choices will be added here." />
              </Block>
            </TabsContent>

            {/* Language */}
            <TabsContent value="language" className="mt-0">
              <Block title="Language and region" description="Language, date and number formats.">
                <EmptyState icon="globe" title="Not available yet" description="The product is in English today. Language and regional formats will be added here." />
              </Block>
            </TabsContent>

            {/* License Management - Admin/Executive Only */}
            <TabsContent value="license" className="space-y-6">
              {canManageLicense ? (
                <LicensePage />
              ) : (
                <Restricted what="License management" who="administrators and executives" />
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
                <Restricted what="User management" who="administrators" />
              )}
            </TabsContent>

            {/* RBAC Settings - Admin/Executive Only */}
            <TabsContent value="rbac" className="space-y-6">
              {canManageRBAC ? (
                <RBACManager />
              ) : (
                <Restricted what="RBAC management" who="administrators and executives" />
              )}
            </TabsContent>

            {/* System Settings - Admin Only */}
            <TabsContent value="system" className="space-y-6">
              {canManageSystem ? (
                <SystemSettings />
              ) : (
                <Restricted what="System settings" who="administrators" />
              )}
            </TabsContent>

            {/* Secrets Settings - Admin Only */}
            <TabsContent value="secrets" className="space-y-6">
              {canManageSecrets ? (
                <SecretsSettings />
              ) : (
                <Restricted what="Secrets management" who="administrators" />
              )}
            </TabsContent>


            {/* Advanced Settings */}
            <TabsContent value="advanced" className="space-y-6">
              <div>
                <h2 className="text-md font-medium text-foreground">Advanced</h2>
                <p className="mt-1 text-sm text-muted-foreground">For administrators. Changes here affect everyone using this environment.</p>
              </div>

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
