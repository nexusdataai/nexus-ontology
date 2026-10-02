/**
 * Backend Authentication Service
 * 
 * Replaces AWS Amplify SDK for authentication.
 * All authentication now goes through backend API which handles Cognito.
 * 
 * Features:
 * - OAuth 2.0 login flow with PKCE
 * - ADFS SSO via backend
 * - Session management via HTTP-only cookies
 * - Token refresh
 * - User profile retrieval
 */

import { getConfig } from './configService';

export interface UserProfile {
  sub: string;
  email: string;
  email_verified?: boolean;
  groups: string[];
  role: string;
  permissions: string[];
}

export interface DirectLoginRequest {
  email: string;
  password: string;
}

export interface DirectLoginResponse {
  user: UserProfile;
  session: {
    expires_in?: number;
    cognito_session?: string;
    challenge?: 'MFA_REQUIRED' | 'MFA_SETUP_REQUIRED';
    access_token?: string;
    id_token?: string;
    refresh_token?: string;
  };
  requires_password_change: boolean;
  message: string;
}

export interface PasswordChallengeRequest {
  email: string;
  new_password: string;
  session: string;  // Cognito session from challenge
}

export interface LoginInitResponse {
  authorization_url: string;
  state: string;
  message: string;
}

export interface LoginCallbackResponse {
  user: UserProfile;
  session_token?: string;  // Only if not using cookies
  expires_in: number;
  message: string;
}

export interface LogoutResponse {
  message: string;
  logout_url?: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

// Token storage key
const ACCESS_TOKEN_KEY = 'nexus_access_token';
const ID_TOKEN_KEY = 'nexus_id_token';
const REFRESH_TOKEN_KEY = 'nexus_refresh_token';

/**
 * Backend Authentication Service
 */
class BackendAuthService {
  private baseUrl: string;
  private configLoaded: boolean = false;

  constructor() {
    // Will be loaded from config.json
    this.baseUrl = '';
  }

  /**
   * Store tokens in sessionStorage
   */
  storeTokens(accessToken?: string, idToken?: string, refreshToken?: string): void {
    if (accessToken) {
      sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    }
    if (idToken) {
      sessionStorage.setItem(ID_TOKEN_KEY, idToken);
    }
    if (refreshToken) {
      sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
  }

  /**
   * Get stored access token
   */
  getAccessToken(): string | null {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY);
  }

  /**
   * Get stored ID token
   */
  getIdToken(): string | null {
    return sessionStorage.getItem(ID_TOKEN_KEY);
  }

  /**
   * Clear stored tokens
   */
  clearTokens(): void {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    sessionStorage.removeItem(ID_TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  }

  /**
   * Ensure config is loaded before making API calls.
   */
  private async ensureConfigLoaded(): Promise<void> {
    if (this.configLoaded) return;
    
    try {
      const config = await getConfig();
      this.baseUrl = config.api?.baseUrl || '';
      this.configLoaded = true;
      console.log('🔧 BackendAuthService baseUrl:', this.baseUrl || '(same origin)');
    } catch (error) {
      console.error('Failed to load config for BackendAuthService:', error);
      // Fall back to same origin
      this.baseUrl = '';
      this.configLoaded = true;
    }
  }

  /**
   * Direct login with email and password.
   * 
   * User stays in app - no redirect to Cognito hosted UI.
   * Handles first-time password change flow.
   * 
   * @param email - User email
   * @param password - User password
   * @returns Login response with user profile or password change requirement
   */
  async login(email: string, password: string): Promise<DirectLoginResponse> {
    await this.ensureConfigLoaded();
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
        method: 'POST',
        credentials: 'include',  // Receive and store cookies
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Login failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  /**
   * Complete new password challenge (first-time login).
   * 
   * @param email - User email
   * @param newPassword - New password
   * @param session - Cognito session from login response
   * @returns User profile after password change
   */
  async completeNewPassword(
    email: string,
    newPassword: string,
    session: string
  ): Promise<DirectLoginResponse> {
    await this.ensureConfigLoaded();
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/login/new-password`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ email, new_password: newPassword, session })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Password change failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Password change error:', error);
      throw error;
    }
  }

  /**
   * Initialize OAuth login flow (for SSO/ADFS).
   * 
   * Gets OAuth authorization URL from backend.
   * Frontend should redirect user to this URL.
   * 
   * @returns Authorization URL and state
   */
  async initOAuthLogin(): Promise<LoginInitResponse> {
    await this.ensureConfigLoaded();
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/login/init`, {
        method: 'GET',
        credentials: 'include',  // Include cookies
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Failed to initialize login');
      }

      return await response.json();
    } catch (error) {
      console.error('OAuth init error:', error);
      throw error;
    }
  }

  /**
   * Complete OAuth callback.
   * 
   * Sends authorization code to backend which exchanges it for tokens.
   * Backend sets HTTP-only cookie with session.
   * 
   * @param code - Authorization code from OAuth callback
   * @param state - State parameter for CSRF validation
   * @returns User profile
   */
  async loginCallback(code: string, state: string): Promise<LoginCallbackResponse> {
    await this.ensureConfigLoaded();
    try {
      const params = new URLSearchParams({ code, state });
      const response = await fetch(`${this.baseUrl}/api/v1/auth/login/callback?${params}`, {
        method: 'POST',
        credentials: 'include',  // Important: Receive and store cookies
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Login failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Login callback error:', error);
      throw error;
    }
  }

  /**
   * Initiate ADFS SSO login.
   * 
   * Redirects browser to backend which redirects to Cognito hosted UI with ADFS.
   * 
   * @returns Redirect URL
   */
  async getADFSLoginUrl(): Promise<string> {
    await this.ensureConfigLoaded();
    return `${this.baseUrl}/api/v1/auth/sso/adfs`;
  }

  /**
   * Get current user profile.
   * 
   * Reads session from HTTP-only cookie automatically.
   * 
   * @returns User profile or null if not authenticated
   */
  async getCurrentUser(): Promise<UserProfile | null> {
    await this.ensureConfigLoaded();
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/me`, {
        method: 'GET',
        credentials: 'include',  // Send cookies
        headers: {
          'Accept': 'application/json'
        }
      });

      if (response.status === 401) {
        // Not authenticated
        return null;
      }

      if (!response.ok) {
        throw new Error('Failed to get user profile');
      }

      const data = await response.json();
      return data.user;
    } catch (error) {
      console.error('Get current user error:', error);
      return null;
    }
  }

  /**
   * Refresh access token.
   * 
   * Uses refresh token to get new access token.
   * Backend updates session cookie.
   * 
   * @param refreshToken - Cognito refresh token
   * @returns New user profile
   */
  async refreshToken(refreshToken: string): Promise<LoginCallbackResponse> {
    await this.ensureConfigLoaded();
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ refresh_token: refreshToken })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Token refresh failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Token refresh error:', error);
      throw error;
    }
  }

  /**
   * Logout user.
   * 
   * Clears backend session and returns Cognito logout URL.
   * 
   * @returns Logout response with optional Cognito logout URL
   */
  async logout(): Promise<LogoutResponse> {
    await this.ensureConfigLoaded();
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include',  // Send cookies for deletion
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Logout failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
    }
  }

  /**
   * Change password.
   * 
   * @param oldPassword - Current password
   * @param newPassword - New password
   */
  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await this.ensureConfigLoaded();
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/password/change`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword
        })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Password change failed');
        }

      return await response.json();
    } catch (error) {
      console.error('Password change error:', error);
      throw error;
    }
  }

  /**
   * Check if user is authenticated.
   * 
   * @returns True if valid session exists
   */
  async isAuthenticated(): Promise<boolean> {
    const user = await this.getCurrentUser();
    return user !== null;
  }
}

// Singleton instance
export const backendAuthService = new BackendAuthService();

export default backendAuthService;
