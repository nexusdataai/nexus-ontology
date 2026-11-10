import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Shield, Copy, Check, RefreshCw, Eye, EyeOff } from 'lucide-react';

/**
 * Two usage modes:
 * 1. Login challenge flow: pass cognitoSession + email (no accessToken).
 *    Uses /mfa/setup with cognito_session, then /mfa/setup/challenge/verify.
 * 2. Settings page flow: pass accessToken (no cognitoSession).
 *    Uses /mfa/setup with email+password or Bearer, then /mfa/setup/verify.
 */
interface MFASetupProps {
  accessToken?: string;
  cognitoSession?: string;
  email?: string;
  onSetupComplete: (result?: any) => void;
  onCancel: () => void;
}

const MFASetup: React.FC<MFASetupProps> = ({
  accessToken,
  cognitoSession: initialCognitoSession,
  email: initialEmail,
  onSetupComplete,
  onCancel,
}) => {
  const [secret, setSecret] = useState('');
  const [totpUri, setTotpUri] = useState('');
  const [email, setEmail] = useState(initialEmail || '');
  const [cognitoSession, setCognitoSession] = useState(initialCognitoSession || '');
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [setupLoading, setSetupLoading] = useState(true);
  const [showSecret, setShowSecret] = useState(false);
  const [copied, setCopied] = useState(false);
  const [step, setStep] = useState<'qr' | 'verify'>('qr');

  const isChallengeMode = !!initialCognitoSession;

  useEffect(() => {
    initSetup();
  }, []);

  const initSetup = async () => {
    try {
      let resp: Response;

      if (isChallengeMode) {
        resp = await fetch('/api/v1/auth/mfa/setup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            cognito_session: initialCognitoSession,
            email: initialEmail,
          }),
        });
      } else {
        resp = await fetch('/api/v1/auth/mfa/setup', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${accessToken}` },
          credentials: 'include',
        });
      }

      const data = await resp.json();
      if (resp.ok) {
        setSecret(data.secret || '');
        setTotpUri(data.totp_uri || '');
        setEmail(data.email || initialEmail || '');
        if (data.cognito_session) {
          setCognitoSession(data.cognito_session);
        }
      } else {
        setError(data.detail || 'Failed to initiate MFA setup');
      }
    } catch {
      setError('Failed to connect to server');
    } finally {
      setSetupLoading(false);
    }
  };

  const copySecret = async () => {
    try {
      await navigator.clipboard.writeText(secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const el = document.createElement('textarea');
      el.value = secret;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const verifyCode = async () => {
    if (code.length !== 6) return;
    setLoading(true);
    setError(null);
    try {
      let resp: Response;

      if (isChallengeMode) {
        resp = await fetch('/api/v1/auth/mfa/setup/challenge/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            email,
            totp_code: code,
            cognito_session: cognitoSession,
          }),
        });
      } else {
        resp = await fetch('/api/v1/auth/mfa/setup/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ access_token: accessToken, totp_code: code }),
        });
      }

      const data = await resp.json();
      if (resp.ok && data.success) {
        onSetupComplete(data);
      } else {
        setError(data.detail || 'Invalid code. Please try again.');
        setCode('');
      }
    } catch {
      setError('Verification failed');
    } finally {
      setLoading(false);
    }
  };

  if (setupLoading) {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardContent className="py-12 text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Setting up two-factor authentication...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader className="text-center">
        <div className="mx-auto w-12 h-12 bg-success/10 rounded-full flex items-center justify-center mb-3">
          <Shield className="h-6 w-6 text-success" />
        </div>
        <CardTitle>Set Up Two-Factor Authentication</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          {isChallengeMode
            ? 'Your account requires MFA. Scan the QR code with your authenticator app to continue.'
            : 'Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.)'}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {step === 'qr' && (
          <>
            {totpUri && (
              <div className="flex justify-center p-4 bg-white rounded-lg border">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(totpUri)}`}
                  alt="TOTP QR Code"
                  className="w-48 h-48"
                />
              </div>
            )}

            <div className="text-center">
              <button
                onClick={() => setShowSecret(!showSecret)}
                className="text-xs text-primary hover:underline flex items-center justify-center gap-1 mx-auto"
              >
                {showSecret ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                {showSecret ? 'Hide secret key' : "Can't scan? Show secret key"}
              </button>
              {showSecret && (
                <div className="mt-2 flex items-center justify-center gap-2">
                  <code className="bg-muted px-3 py-1.5 rounded text-xs font-mono tracking-wider select-all">
                    {secret}
                  </code>
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={copySecret}>
                    {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
                  </Button>
                </div>
              )}
            </div>

            <Button onClick={() => setStep('verify')} className="w-full">
              I've scanned the code — Next
            </Button>
          </>
        )}

        {step === 'verify' && (
          <>
            <p className="text-sm text-center text-muted-foreground">
              Enter the 6-digit code from your authenticator app to complete setup
            </p>
            <div className="flex justify-center">
              <Input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="text-center text-2xl tracking-[0.5em] font-mono w-48 h-14"
                maxLength={6}
                autoFocus
              />
            </div>
            <Button onClick={verifyCode} className="w-full" disabled={code.length !== 6 || loading}>
              {loading ? <><RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Verifying...</> : 'Complete Setup'}
            </Button>
            <Button variant="ghost" onClick={() => setStep('qr')} className="w-full">
              Back
            </Button>
          </>
        )}

        {!isChallengeMode && (
          <Button variant="ghost" onClick={onCancel} className="w-full text-muted-foreground">
            Skip for now
          </Button>
        )}
      </CardContent>
    </Card>
  );
};

export default MFASetup;
