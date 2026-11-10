/**
 * OAuth Callback Page
 * 
 * Handles OAuth 2.0 redirect from Cognito after authentication.
 * Extracts authorization code and state from URL parameters,
 * sends to backend to exchange for session.
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

export const AuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Processing authentication...');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Extract OAuth parameters from URL
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');

        // Handle OAuth errors
        if (error) {
          console.error('OAuth error:', error, errorDescription);
          setStatus('error');
          setMessage(errorDescription || error || 'Authentication failed');
          
          // Redirect to login after delay
          setTimeout(() => navigate('/login'), 3000);
          return;
        }

        // Validate required parameters
        if (!code || !state) {
          console.error('Missing code or state parameter');
          setStatus('error');
          setMessage('Invalid callback parameters');
          
          setTimeout(() => navigate('/login'), 3000);
          return;
        }

        console.log('✅ OAuth callback received, exchanging code for session...');

        // Call the global callback function exposed by EnterpriseAuthContext
        if (typeof (window as any).__completeOAuthCallback === 'function') {
          await (window as any).__completeOAuthCallback(code, state);
          
          setStatus('success');
          setMessage('Authentication successful! Redirecting...');
          
          // Context will handle navigation
        } else {
          throw new Error('Auth context not initialized');
        }

      } catch (error: any) {
        console.error('❌ Callback handling error:', error);
        setStatus('error');
        setMessage(error.message || 'Authentication failed');
        
        // Redirect to login after delay
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-surface-2 to-surface-2 dark:from-card dark:to-surface-3 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">
            {status === 'processing' && 'Completing Sign In...'}
            {status === 'success' && 'Sign In Successful'}
            {status === 'error' && 'Sign In Failed'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-4">
            {status === 'processing' && (
              <>
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
                <p className="text-center text-muted-foreground">{message}</p>
              </>
            )}
            
            {status === 'success' && (
              <>
                <CheckCircle2 className="h-12 w-12 text-success" />
                <p className="text-center text-muted-foreground">{message}</p>
              </>
            )}
            
            {status === 'error' && (
              <>
                <XCircle className="h-12 w-12 text-destructive" />
                <p className="text-center text-destructive">{message}</p>
                <p className="text-sm text-muted-foreground">Redirecting to login page...</p>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AuthCallback;
