import { EnterpriseLoginForm } from "@/components/auth/EnterpriseLoginForm";
import PasswordChangeForm from "@/components/auth/PasswordChangeForm";
import MFAVerify from "@/components/auth/MFAVerify";
import MFASetup from "@/components/auth/MFASetup";
import { useEnterpriseAuth } from "@/context/EnterpriseAuthContext";
import { useState, useEffect, useCallback } from "react";

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

  const handleMfaCancel = () => {
    setMfaState({ type: 'none', email: '', cognitoSession: '' });
  };

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-[#0b0f19]">
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-center items-center px-16 bg-gradient-to-br from-slate-100 via-slate-200 to-purple-50 dark:from-[#0b0f19] dark:via-[#141b2d] dark:to-[#1a1040]">
        <div className="max-w-md text-center">
          <div className="w-16 h-16 flex items-center justify-center mx-auto mb-6">
            <svg viewBox="0 0 32 32" className="w-16 h-16">
              <defs>
                <linearGradient id="loginLogo" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#7c3aed"/>
                  <stop offset="100%" stopColor="#4f46e5"/>
                </linearGradient>
              </defs>
              <path d="M16 1 L29 8.5 L29 23.5 L16 31 L3 23.5 L3 8.5 Z" fill="url(#loginLogo)"/>
              <path d="M16 7 L12 12 L16 17 L20 12 Z" fill="white" opacity="0.9"/>
              <path d="M12 14 L9 19 L16 25 L12 18 Z" fill="white" opacity="0.7"/>
              <path d="M20 14 L23 19 L16 25 L20 18 Z" fill="white" opacity="0.7"/>
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-3">Nexus Data-AI Platform</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
            Accurate Intelligence for your enterprise. Connect data sources, build knowledge graphs,
            and deploy AI-powered automation across your organization.
          </p>
          <div className="mt-10 grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">5+</div>
              <div className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">Foundries</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">10+</div>
              <div className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">Data Sources</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">20+</div>
              <div className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">Solutions</div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center px-8">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center justify-center gap-2 mb-8">
            <div className="w-10 h-10 flex items-center justify-center">
              <svg viewBox="0 0 32 32" className="w-10 h-10">
                <defs>
                  <linearGradient id="loginLogoMobile" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#7c3aed"/>
                    <stop offset="100%" stopColor="#4f46e5"/>
                  </linearGradient>
                </defs>
                <path d="M16 1 L29 8.5 L29 23.5 L16 31 L3 23.5 L3 8.5 Z" fill="url(#loginLogoMobile)"/>
                <path d="M16 7 L12 12 L16 17 L20 12 Z" fill="white" opacity="0.9"/>
                <path d="M12 14 L9 19 L16 25 L12 18 Z" fill="white" opacity="0.7"/>
                <path d="M20 14 L23 19 L16 25 L20 18 Z" fill="white" opacity="0.7"/>
              </svg>
            </div>
            <span className="text-xl font-bold text-slate-900 dark:text-white">Nexus AI</span>
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

          <p className="text-center text-[11px] text-slate-400 dark:text-slate-600 mt-8">
            Powered by PTR Technologies &middot; Accurate Enterprise AI
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
