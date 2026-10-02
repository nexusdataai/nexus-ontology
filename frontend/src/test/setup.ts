import { vi } from 'vitest';

// Mock import.meta.env for tests
vi.stubGlobal('import.meta', {
  env: {
    VITE_COGNITO_USER_POOL_ID: '',
    VITE_COGNITO_CLIENT_ID: '',
    VITE_COGNITO_DOMAIN: '',
    VITE_AWS_REGION: 'us-east-1',
    VITE_API_BASE_URL: '',
    VITE_API_TIMEOUT: '30000',
    VITE_BYPASS_AUTH: 'false',
    VITE_OAUTH_REDIRECT_SIGNIN: 'http://localhost:5173/auth/callback',
    VITE_OAUTH_REDIRECT_SIGNOUT: 'http://localhost:5173/login',
  },
});

// Mock window.location
Object.defineProperty(window, 'location', {
  value: {
    hostname: 'localhost',
    origin: 'http://localhost:5173',
    href: 'http://localhost:5173',
  },
  writable: true,
});

// Mock fetch
global.fetch = vi.fn();
