import { EnterpriseLoginForm } from "@/components/auth/EnterpriseLoginForm";
import PasswordChangeForm from "@/components/auth/PasswordChangeForm";
import MFAVerify from "@/components/auth/MFAVerify";
import MFASetup from "@/components/auth/MFASetup";
import { useEnterpriseAuth } from "@/context/EnterpriseAuthContext";
import { useState, useEffect, useCallback } from "react";
import { Logo } from "@/components/ds/Logo";
import { PlatformStack, type LayerId } from "@/components/home/PlatformStack";

const Login = () => {
  const { needsPasswordChange, passwordChangeUser, confirmNewPassword, cancelPasswordChange, loading, loadUserFromSession } = useEnterpriseAuth();

  const [mfaState, setMfaState] = useState<{
    type: 'none' | 'verify' | 'setup';
    email: string;
    cognitoSession: string;
  }>({ type: 'none', email: '', cognitoSession: '' });

  useEffect(() => {
    const handleMfaEvent = (e: any) => {
      const { challenge, email, session } = e.detail;
      if (challenge === 'MFA_REQUIRED') {
        setMfaState({ type: 'verify', email, cognitoSession: session || '' });
      } else if (challenge === 'MFA_SETUP_REQUIRED') {
        setMfaState({ type: 'setup', email, cognitoSession: session || '' });
      }
    };
    window.addEventListener('mfa-challenge', handleMfaEvent);
    return () => window.removeEventListener('mfa-challenge', handleMfaEvent);
  }, []);

  const handleAuthComplete = useCallback(async () => {
    try {
      await loadUserFromSession();
    } catch {
      window.location.href = '/';
    }
  }, [loadUserFromSession]);

  const handleMfaVerified = useCallback(async (_result: any) => {
    await handleAuthComplete();
  }, [handleAuthComplete]);

  const handleMfaSetupComplete = useCallback(async (result: any) => {
    if (result?.user) {
      await handleAuthComplete();
    } else {
      setMfaState(prev => ({ ...prev, type: 'verify' }));
    }
  }, [handleAuthComplete]);

  // Slow walk up the platform drawing on the brand panel.
  const [tour, setTour] = useState<LayerId>('data');
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
    const order: LayerId[] = ['data', 'control', 'reasoning', 'solutions', 'ops'];
    const t = window.setInterval(() => setTour(cur => order[(order.indexOf(cur) + 1) % order.length]), 2600);
    return () => window.clearInterval(t);
  }, []);

  const handleMfaCancel = () => {
    setMfaState({ type: 'none', email: '', cognitoSession: '' });
  };

  return (
    <div className="flex min-h-[100dvh] bg-background text-foreground">
      {/* Brand panel: always graphite, like the website hero */}
      <div className="dark relative hidden w-[46%] max-w-[720px] flex-col justify-between overflow-hidden border-r border-border bg-background p-10 text-foreground lg:flex xl:p-14">
        <div className="canvas-dots pointer-events-none absolute inset-0 opacity-60 [mask-image:radial-gradient(ellipse_at_center,black,transparent_78%)]" />
        <div className="relative [--logo-bg:var(--background)]"><Logo /></div>

        <div className="relative mx-auto w-full max-w-[400px]">
          <PlatformStack active={tour} onHover={() => {}} onSelect={() => {}} className="pointer-events-none animate-fade-up" />
        </div>

        <div className="relative">
          <span className="eyebrow-brand">AI OS for the enterprise</span>
          <h1 className="mt-3 max-w-md text-3xl font-medium leading-[1.08] tracking-tight xl:text-4xl">
            The intelligent AI operating layer for the <span className="text-brand-hi">enterprise.</span>
          </h1>
          <p className="mt-4 max-w-md text-sm leading-6 text-muted-foreground">
            Connect your systems, build a verified ontology of your business, and deploy agents that reason and act, with people in control of every decision.
          </p>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center px-5 py-10 sm:px-8">
        <div className="w-full max-w-md animate-fade-up">
          <div className="mb-8 flex justify-center lg:hidden [--logo-bg:var(--background)]">
            <Logo />
          </div>

          {mfaState.type === 'verify' ? (
            <MFAVerify
              email={mfaState.email}
              cognitoSession={mfaState.cognitoSession}
              onVerified={handleMfaVerified}
              onCancel={handleMfaCancel}
            />
          ) : mfaState.type === 'setup' ? (
            <MFASetup
              cognitoSession={mfaState.cognitoSession}
              email={mfaState.email}
              onSetupComplete={handleMfaSetupComplete}
              onCancel={handleMfaCancel}
            />
          ) : needsPasswordChange ? (
            <PasswordChangeForm
              userEmail={passwordChangeUser || ''}
              onPasswordChange={confirmNewPassword}
              onCancel={cancelPasswordChange}
              loading={loading}
            />
          ) : (
            <EnterpriseLoginForm
              defaultTab="cognito"
              showTabSwitcher={false}
            />
          )}

          <p className="mt-8 text-center text-xs text-subtle-foreground">
            Powered by PTR Technologies
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
