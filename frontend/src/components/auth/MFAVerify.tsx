import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Shield, RefreshCw } from 'lucide-react';

interface MFAVerifyProps {
  email: string;
  cognitoSession: string;
  onVerified: (result: any) => void;
  onCancel: () => void;
}

const MFAVerify: React.FC<MFAVerifyProps> = ({ email, cognitoSession, onVerified, onCancel }) => {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleSubmit = async () => {
    if (code.length !== 6) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch('/api/v1/auth/mfa/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, totp_code: code, session: cognitoSession }),
      });
      const data = await resp.json();
      if (resp.ok && data.success) {
        onVerified(data);
      } else {
        setError(data.detail || 'Invalid code. Please try again.');
        setCode('');
        inputRef.current?.focus();
      }
    } catch {
      setError('Verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '').slice(0, 6);
    setCode(val);
    if (val.length === 6) {
      setTimeout(() => handleSubmit(), 100);
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader className="text-center">
        <div className="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
          <Shield className="h-6 w-6 text-primary" />
        </div>
        <CardTitle>Two-Factor Authentication</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Enter the 6-digit code from your authenticator app
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="flex justify-center">
          <Input
            ref={inputRef}
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="000000"
            value={code}
            onChange={handleChange}
            className="text-center text-2xl tracking-[0.5em] font-mono w-48 h-14"
            maxLength={6}
            disabled={loading}
          />
        </div>
        <Button onClick={handleSubmit} className="w-full" disabled={code.length !== 6 || loading}>
          {loading ? <><RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Verifying...</> : 'Verify'}
        </Button>
        <Button variant="ghost" onClick={onCancel} className="w-full" disabled={loading}>
          Cancel
        </Button>
      </CardContent>
    </Card>
  );
};

export default MFAVerify;
