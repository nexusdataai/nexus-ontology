import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "@/hooks/use-toast";
import { 
  UserRole, 
  AuthMethod, 
  Permission, 
  EnterpriseProfile, 
  ROLE_PERMISSIONS,
  EnterpriseSession 
} from "@/types/auth";
import { isAuthBypassEnabled } from "@/services/configService";
import backendAuthService, { type UserProfile } from "@/services/backendAuthService";

// ============================================================================
// Mock User Profile for Auth Bypass
// ============================================================================

const createMockUserProfile = (): EnterpriseProfile => {
  const now = new Date().toISOString();
  
  return {
    id: 'local-dev-user',
    email: 'dev@local.test',
    full_name: 'Local Dev User',
    avatar_url: null,
    role: 'Admin',
    department: 'Development',
    managerId: null,
    employeeId: 'LOCAL-DEV-001',
    permissions: ROLE_PERMISSIONS['Admin'],
    lastLogin: now,
    authMethod: 'LOCAL',
    teamIds: [],
    created_at: now,
    updated_at: now,
    adfsGroups: []
  };
};

const createMockSession = (): EnterpriseSession => {
  const now = Date.now();
  const expiresIn = 24 * 60 * 60; // 24 hours for dev
  
  return {
    accessToken: 'mock-bypass-access-token',
    idToken: 'mock-bypass-id-token',
    refreshToken: 'mock-bypass-refresh-token',
    tokenType: 'Bearer',
    expiresIn,
    authMethod: 'LOCAL',
    issuedAt: Math.floor(now / 1000),
    expiresAt: Math.floor(now / 1000) + expiresIn
  };
};

// Authentication Context Interface
interface EnterpriseAuthContextType {
  user: any | null;
  profile: EnterpriseProfile | null;
  session: EnterpriseSession | null;
  loading: boolean;
  authMethod: AuthMethod | null;
  
  // Auth bypass state
  isAuthBypassed: boolean;
  
  // Password change flow state
  needsPasswordChange: boolean;
  passwordChangeUser: string | null;
  
  // Authentication methods
  signInWithADFS: () => Promise<void>;
  signInWithCognito: (email: string, password: string) => Promise<void>;
  confirmNewPassword: (newPassword: string) => Promise<void>;
  cancelPasswordChange: () => void;
  signOutUser: () => Promise<void>;
  
  // Post-auth helpers
  setUser: React.Dispatch<React.SetStateAction<any | null>>;
  loadUserFromSession: () => Promise<void>;
  
  // Permission utilities
  hasPermission: (permission: Permission) => boolean;
  canAccessCall: (callId: string) => Promise<boolean>;
  canViewTeamMember: (memberId: string) => Promise<boolean>;
}

// Create Context
const EnterpriseAuthContext = createContext<EnterpriseAuthContextType | undefined>(undefined);

// Provider Component
export const EnterpriseAuthProvider: React.FC<{ children: React.ReactNode }> = ({ 
  children 
}) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [profile, setProfile] = useState<EnterpriseProfile | null>(null);
  const [session, setSession] = useState<EnterpriseSession | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [authMethod, setAuthMethod] = useState<AuthMethod | null>(null);
  const authBypassInitial = import.meta.env.VITE_BYPASS_AUTH === 'true';
  const [isAuthBypassed, setIsAuthBypassed] = useState<boolean>(authBypassInitial);
  
  // Password change flow state
  const [needsPasswordChange, setNeedsPasswordChange] = useState<boolean>(false);
  const [passwordChangeUser, setPasswordChangeUser] = useState<string | null>(null);
  
  const navigate = useNavigate();

  // Helper: Convert backend UserProfile to EnterpriseProfile
  const buildEnterpriseProfile = (backendUser: UserProfile): EnterpriseProfile => {
    const now = new Date().toISOString();
    const role = backendUser.role as UserRole;
    const backendPerms = (backendUser.permissions || []) as Permission[];
    const permissions = backendPerms.length > 0 ? backendPerms : (ROLE_PERMISSIONS[role] || []);
    
    return {
      id: backendUser.sub,
      email: backendUser.email,
      full_name: backendUser.email.split('@')[0],
      avatar_url: null,
      role,
      department: null,
      managerId: null,
      employeeId: null,
      permissions,
      lastLogin: now,
      authMethod: 'COGNITO',
      teamIds: [],
      created_at: now,
      updated_at: now,
      adfsGroups: backendUser.groups || []
    };
  };

  // Check and setup auth bypass mode
  useEffect(() => {
    const setupAuthBypass = async () => {
      try {
        const bypass = authBypassInitial || await isAuthBypassEnabled();
        setIsAuthBypassed(bypass);
        
        if (bypass) {
          console.log('🔓 Auth bypass enabled - using mock authentication');
          setProfile(createMockUserProfile());
          setSession(createMockSession());
          setAuthMethod('LOCAL');
          setUser({ email: 'dev@local.test', sub: 'local-dev', groups: [], role: 'Admin', permissions: [] });
          setLoading(false);
          return;
        }
      } catch (error) {
        console.error('Error checking auth bypass:', error);
      }
    };

    setupAuthBypass();
  }, [authBypassInitial]);

  // Check existing session on mount
  useEffect(() => {
    const checkExistingSession = async () => {
      // Skip if auth bypassed
      if (isAuthBypassed) {
        return;
      }

      try {
        // Check if user has valid session via backend
        const currentUser = await backendAuthService.getCurrentUser();
        
        if (currentUser) {
          console.log('✅ Existing session found:', currentUser.email);
          setUser(currentUser);
          setProfile(buildEnterpriseProfile(currentUser));
          setAuthMethod('COGNITO');
          
          // Create session object (simplified - cookies handle actual session)
          setSession({
            accessToken: 'managed-by-backend',
            idToken: 'managed-by-backend',
            refreshToken: '',
            tokenType: 'Bearer',
            expiresIn: 3600,
            authMethod: 'COGNITO',
            issuedAt: Math.floor(Date.now() / 1000),
            expiresAt: Math.floor(Date.now() / 1000) + 3600
          });
        } else {
          console.log('ℹ️ No existing session');
        }
      } catch (error) {
        console.error('Error checking session:', error);
      } finally {
        setLoading(false);
      }
    };

    if (!isAuthBypassed) {
      checkExistingSession();
    }
  }, [isAuthBypassed]);

  // Sign in with ADFS (redirects to Cognito hosted UI for SSO)
  const signInWithADFS = useCallback(async () => {
    try {
      console.log('🔐 Initiating ADFS SSO via backend...');
      
      // For ADFS SSO, we need OAuth redirect (can't be direct)
      // Redirect to backend ADFS endpoint which redirects to Cognito
      const adfsUrl = await backendAuthService.getADFSLoginUrl();
      window.location.href = adfsUrl;
      
    } catch (error: any) {
      console.error('❌ ADFS sign-in error:', error);
      toast({
        title: "Sign-in Failed",
        description: error.message || "Could not initiate ADFS authentication",
        variant: "destructive"
      });
      throw error;
    }
  }, []);

  // Sign in with Cognito (email/password) - Direct auth, no redirect
  const signInWithCognito = useCallback(async (email: string, password: string) => {
    try {
      console.log('🔐 Signing in with Cognito (direct auth)...');
      
      // Direct login - no redirect!
      const response = await backendAuthService.login(email, password);
      
      // Check if password change required
      if (response.requires_password_change) {
        console.log('New password required');
        setNeedsPasswordChange(true);
        setPasswordChangeUser(email);
        (window as any).__cognitoPasswordSession = response.session?.cognito_session;
        
        toast({
          title: "Password Change Required",
          description: "Please set a new password for your account",
        });
        return;
      }

      // Check if MFA is required
      const challenge = response.session?.challenge;
      if (challenge === 'MFA_REQUIRED' || challenge === 'MFA_SETUP_REQUIRED') {
        console.log('MFA required:', challenge);
        (window as any).__mfaChallenge = {
          type: challenge,
          email: email,
          cognitoSession: response.session?.cognito_session || '',
        };
        setNeedsPasswordChange(false);
        // Force re-render by updating a state that Login.tsx can read
        window.dispatchEvent(new CustomEvent('mfa-challenge', { detail: { challenge, email, session: response.session?.cognito_session } }));
        return;
      }
      
      // Login successful — session cookie is set by backend
      const enterpriseProfile = buildEnterpriseProfile(response.user);
      setUser(response.user);
      setProfile(enterpriseProfile);
      setAuthMethod('COGNITO');

      setSession({
        accessToken: 'managed-by-backend',
        idToken: 'managed-by-backend',
        refreshToken: '',
        tokenType: 'Bearer',
        expiresIn: response.session?.expires_in || 3600,
        authMethod: 'COGNITO',
        issuedAt: Math.floor(Date.now() / 1000),
        expiresAt: Math.floor(Date.now() / 1000) + (response.session?.expires_in || 3600)
      });

      toast({
        title: "Welcome!",
        description: `Signed in as ${response.user.email}`,
      });

      navigate('/');
      
    } catch (error: any) {
      console.error('❌ Cognito sign-in error:', error);
      toast({
        title: "Sign-in Failed",
        description: error.message || "Invalid email or password",
        variant: "destructive"
      });
      throw error;
    }
  }, [navigate]);

  // Complete OAuth callback (called from callback page)
  const completeOAuthCallback = useCallback(async (code: string, state: string) => {
    try {
      console.log('🔄 Completing OAuth callback...');
      
      // Send code to backend
      const response = await backendAuthService.loginCallback(code, state);
      
      // Update state with user profile
      const enterpriseProfile = buildEnterpriseProfile(response.user);
      setUser(response.user);
      setProfile(enterpriseProfile);
      setAuthMethod('COGNITO');
      
      // Session is managed by backend cookies
      setSession({
        accessToken: 'managed-by-backend',
        idToken: 'managed-by-backend',
        refreshToken: '',
        tokenType: 'Bearer',
        expiresIn: response.expires_in,
        authMethod: 'COGNITO',
        issuedAt: Math.floor(Date.now() / 1000),
        expiresAt: Math.floor(Date.now() / 1000) + response.expires_in
      });
      
      console.log('✅ OAuth callback completed:', response.user.email);
      
      toast({
        title: "Welcome!",
        description: `Signed in as ${response.user.email}`,
      });
      
      // Redirect to home (main dashboard)
      navigate('/');
      
    } catch (error: any) {
      console.error('❌ OAuth callback error:', error);
      toast({
        title: "Authentication Failed",
        description: error.message || "Could not complete sign-in",
        variant: "destructive"
      });
      throw error;
    }
  }, [navigate]);

  // Expose callback completion for use by callback page
  (window as any).__completeOAuthCallback = completeOAuthCallback;

  // Confirm new password (for forced password change flow)
  const confirmNewPassword = useCallback(async (newPassword: string) => {
    try {
      if (!passwordChangeUser) {
        throw new Error("No user in password change flow");
      }

      console.log('🔑 Completing password change via backend...');
      
      const cognitoSession = (window as any).__cognitoPasswordSession;
      if (!cognitoSession) {
        throw new Error("No Cognito session for password change");
      }
      
      const response = await backendAuthService.completeNewPassword(
        passwordChangeUser,
        newPassword,
        cognitoSession
      );

      // Password change may trigger MFA challenge
      const challenge = response.session?.challenge;
      if (challenge === 'MFA_REQUIRED' || challenge === 'MFA_SETUP_REQUIRED') {
        setNeedsPasswordChange(false);
        setPasswordChangeUser(null);
        (window as any).__cognitoPasswordSession = null;

        window.dispatchEvent(new CustomEvent('mfa-challenge', {
          detail: {
            challenge,
            email: passwordChangeUser,
            session: response.session?.cognito_session,
          },
        }));
        return;
      }

      // No MFA challenge — direct login success
      const enterpriseProfile = buildEnterpriseProfile(response.user);
      setUser(response.user);
      setProfile(enterpriseProfile);
      setAuthMethod('COGNITO');
      setNeedsPasswordChange(false);
      setPasswordChangeUser(null);
      (window as any).__cognitoPasswordSession = null;

      setSession({
        accessToken: 'managed-by-backend',
        idToken: 'managed-by-backend',
        refreshToken: '',
        tokenType: 'Bearer',
        expiresIn: response.session?.expires_in || 3600,
        authMethod: 'COGNITO',
        issuedAt: Math.floor(Date.now() / 1000),
        expiresAt: Math.floor(Date.now() / 1000) + (response.session?.expires_in || 3600)
      });

      toast({
        title: "Password Changed!",
        description: `Welcome, ${response.user.email}`,
      });

      navigate('/');
      
    } catch (error: any) {
      console.error('❌ Password change error:', error);
      toast({
        title: "Password Change Failed",
        description: error.message || "Could not change password",
        variant: "destructive"
      });
      throw error;
    }
  }, [passwordChangeUser, navigate]);

  // Cancel password change flow
  const cancelPasswordChange = useCallback(() => {
    setNeedsPasswordChange(false);
    setPasswordChangeUser(null);
    navigate('/login');
  }, [navigate]);

  // Load user profile from existing session cookie (used after MFA/setup completes)
  const loadUserFromSession = useCallback(async () => {
    const currentUser = await backendAuthService.getCurrentUser();
    if (currentUser) {
      const enterpriseProfile = buildEnterpriseProfile(currentUser);
      setUser(currentUser);
      setProfile(enterpriseProfile);
      setAuthMethod('COGNITO');
      setNeedsPasswordChange(false);
      setPasswordChangeUser(null);
      setSession({
        accessToken: 'managed-by-backend',
        idToken: 'managed-by-backend',
        refreshToken: '',
        tokenType: 'Bearer',
        expiresIn: 3600,
        authMethod: 'COGNITO',
        issuedAt: Math.floor(Date.now() / 1000),
        expiresAt: Math.floor(Date.now() / 1000) + 3600
      });
      navigate('/');
    } else {
      throw new Error('No session found after auth');
    }
  }, [navigate]);

  // Sign out
  const signOutUser = useCallback(async () => {
    try {
      console.log('👋 Signing out...');
      
      // Call backend logout
      const response = await backendAuthService.logout();
      
      // Clear stored tokens
      backendAuthService.clearTokens();
      
      // Clear local state
      setUser(null);
      setProfile(null);
      setSession(null);
      setAuthMethod(null);
      
      if (response.logout_url && !response.logout_url.includes('localhost')) {
        const logoutUrl = new URL(response.logout_url);
        logoutUrl.searchParams.set('logout_uri', window.location.origin);
        window.location.href = logoutUrl.toString();
      } else {
        navigate('/login');
      }
      
      toast({
        title: "Signed Out",
        description: "You have been signed out successfully",
      });
      
    } catch (error: any) {
      console.error('❌ Sign-out error:', error);
      
      // Clear state anyway
      setUser(null);
      setProfile(null);
      setSession(null);
      setAuthMethod(null);
      navigate('/login');
    }
  }, [navigate]);

  // Permission check
  const hasPermission = useCallback((permission: Permission): boolean => {
    if (!profile) {
      return false;
    }
    
    // Admins have all permissions
    if (profile.role === 'Admin') {
      return true;
    }
    
    return profile.permissions?.includes(permission) || false;
  }, [profile]);

  // Call access check
  const canAccessCall = useCallback(async (callId: string): Promise<boolean> => {
    if (!profile) {
      return false;
    }
    
    // Admins can access all calls
    if (profile.role === 'Admin' || profile.role === 'Executive') {
      return true;
    }
    
    // Reps can only access their own calls
    // This would need to be validated by backend in real implementation
    return true;
  }, [profile]);

  // Team member access check
  const canViewTeamMember = useCallback(async (memberId: string): Promise<boolean> => {
    if (!profile) {
      return false;
    }
    
    // Managers and above can view team members
    if (['Admin', 'Executive', 'SalesManager'].includes(profile.role)) {
      return true;
    }
    
    // Reps can only view themselves
    return profile.id === memberId;
  }, [profile]);

  const value: EnterpriseAuthContextType = {
    user,
    profile,
    session,
    loading,
    authMethod,
    isAuthBypassed,
    needsPasswordChange,
    passwordChangeUser,
    signInWithADFS,
    signInWithCognito,
    confirmNewPassword,
    cancelPasswordChange,
    signOutUser,
    setUser,
    loadUserFromSession,
    hasPermission,
    canAccessCall,
    canViewTeamMember,
  };

  return (
    <EnterpriseAuthContext.Provider value={value}>
      {children}
    </EnterpriseAuthContext.Provider>
  );
};

// Hook to use the context
export const useEnterpriseAuth = () => {
  const context = useContext(EnterpriseAuthContext);
  if (context === undefined) {
    throw new Error("useEnterpriseAuth must be used within EnterpriseAuthProvider");
  }
  return context;
};

export default EnterpriseAuthContext;
