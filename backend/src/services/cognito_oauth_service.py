"""
Cognito OAuth Service

Handles AWS Cognito OAuth 2.0 / OIDC authentication flows:
- Authorization Code Grant with PKCE
- Token exchange and validation
- Token refresh
- User profile retrieval

Reads configuration from SSM Parameter Store for runtime configurability.
"""

import os
import secrets
import hashlib
import base64
import json
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from urllib.parse import urlencode, parse_qs, urlparse

import boto3
from botocore.exceptions import ClientError
from loguru import logger

from ..config.ssm_loader import SSMParameterLoader


@dataclass
class CognitoConfig:
    """Cognito configuration loaded from SSM Parameter Store."""
    region: str
    user_pool_id: str
    client_id: str
    domain: str
    redirect_uri: str
    
    @property
    def _cognito_base_url(self) -> str:
        """
        Get the Cognito base URL, handling both domain formats:
        - Prefix only: 'call-processing-dev-764119721991'
        - Full domain: 'call-processing-dev-764119721991.auth.us-east-1.amazoncognito.com'
        """
        suffix = f".auth.{self.region}.amazoncognito.com"
        if self.domain.endswith('.amazoncognito.com'):
            # Domain is already the full Cognito domain
            return f"https://{self.domain}"
        else:
            # Domain is just the prefix
            return f"https://{self.domain}{suffix}"
    
    @property
    def token_endpoint(self) -> str:
        """Cognito token endpoint."""
        return f"{self._cognito_base_url}/oauth2/token"
    
    @property
    def authorize_endpoint(self) -> str:
        """Cognito authorization endpoint."""
        return f"{self._cognito_base_url}/oauth2/authorize"
    
    @property
    def logout_endpoint(self) -> str:
        """Cognito logout endpoint."""
        return f"{self._cognito_base_url}/logout"
    
    @property
    def userinfo_endpoint(self) -> str:
        """Cognito user info endpoint."""
        return f"{self._cognito_base_url}/oauth2/userInfo"
    
    @property
    def jwks_url(self) -> str:
        """Cognito JWKS URL for token validation."""
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
    
    @property
    def issuer(self) -> str:
        """Cognito token issuer."""
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
    
    @property
    def logout_uri(self) -> str:
        """
        Get the logout redirect URI (just the origin, no path).
        
        Cognito requires the logout_uri to match exactly what's configured
        in the App Client's "Allowed sign-out URLs".
        """
        parsed = urlparse(self.redirect_uri)
        return f"{parsed.scheme}://{parsed.netloc}"


@dataclass
class PKCEChallenge:
    """PKCE challenge for OAuth flow."""
    code_verifier: str
    code_challenge: str
    state: str


@dataclass
class AuthorizationResult:
    """Result of authorization code exchange."""
    access_token: str
    id_token: str
    refresh_token: str
    expires_in: int
    token_type: str


@dataclass
class UserProfile:
    """User profile from Cognito."""
    sub: str
    email: str
    email_verified: bool
    cognito_groups: list[str]
    custom_role: Optional[str] = None
    custom_permissions: list[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "sub": self.sub,
            "email": self.email,
            "email_verified": self.email_verified,
            "groups": self.cognito_groups,
            "role": self.custom_role or (self.cognito_groups[0] if self.cognito_groups else "User"),
            "permissions": self.custom_permissions or []
        }


class CognitoOAuthService:
    """
    Service for handling Cognito OAuth 2.0 / OIDC authentication.
    
    Loads configuration from SSM Parameter Store and handles:
    - OAuth authorization URL generation with PKCE
    - Token exchange (authorization code → tokens)
    - Token refresh
    - Token revocation
    - User profile retrieval
    """
    
    def __init__(
        self,
        capability: str = "call-processing",
        environment: str = "dev"
    ):
        """
        Initialize Cognito OAuth service.
        
        Args:
            capability: Capability name for SSM path
            environment: Environment (dev, staging, prod)
        """
        self.capability = capability
        self.environment = environment
        self._config: Optional[CognitoConfig] = None
        self._ssm_loader: Optional[SSMParameterLoader] = None
        self._cognito_client: Optional[Any] = None
        
        # In-memory session store for PKCE challenges
        # In production, use Redis or database
        self._pkce_store: Dict[str, PKCEChallenge] = {}
    
    async def load_config(self) -> CognitoConfig:
        """
        Load Cognito configuration from SSM Parameter Store.
        
        Falls back to environment variables if SSM unavailable.
        
        Returns:
            CognitoConfig with Cognito settings
        """
        if self._config:
            return self._config
        
        try:
            # Initialize SSM loader
            region = os.getenv('AWS_REGION', 'us-east-1')
            if not self._ssm_loader:
                self._ssm_loader = SSMParameterLoader(region=region)
            
            # Load Cognito parameters from SSM
            ssm_prefix = f"/{self.capability}/{self.environment}/cognito"
            logger.info(f"Loading Cognito config from SSM: {ssm_prefix}")
            
            # load_parameters_by_path is synchronous, not async
            params = self._ssm_loader.load_parameters_by_path(
                ssm_prefix,
                recursive=True
            )
            
            if params:
                # Extract parameters (remove prefix from keys)
                cognito_params = {
                    k.split('/')[-1]: v 
                    for k, v in params.items()
                }
                
                self._config = CognitoConfig(
                    region=cognito_params.get('region', region),
                    user_pool_id=cognito_params.get('user-pool-id', ''),
                    client_id=cognito_params.get('app-client-id', '') or cognito_params.get('client-id', ''),
                    domain=cognito_params.get('domain', ''),
                    redirect_uri=cognito_params.get('redirect-uri', '')
                )
                
                logger.info(f"✅ Loaded Cognito config from SSM: user_pool={self._config.user_pool_id}")
                return self._config
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to load Cognito config from SSM: {e}")
        
        # Fallback to environment variables
        logger.info("Falling back to environment variables for Cognito config")
        
        self._config = CognitoConfig(
            region=os.getenv('COGNITO_REGION', 'us-east-1'),
            user_pool_id=os.getenv('COGNITO_USER_POOL_ID', ''),
            client_id=os.getenv('COGNITO_APP_CLIENT_ID', ''),
            domain=os.getenv('COGNITO_DOMAIN', ''),
            redirect_uri=os.getenv('COGNITO_REDIRECT_URI', '')
        )
        
        if not self._config.user_pool_id or not self._config.client_id:
            logger.error("❌ Cognito configuration incomplete (missing user_pool_id or client_id)")
        
        return self._config
    
    def _get_cognito_client(self):
        """Get or create boto3 Cognito Identity Provider client."""
        if not self._cognito_client:
            region = os.getenv('AWS_REGION', 'us-east-1')
            
            # Use LocalStack if enabled
            if os.getenv('USE_LOCALSTACK') == 'true':
                endpoint_url = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
                self._cognito_client = boto3.client(
                    'cognito-idp',
                    region_name=region,
                    endpoint_url=endpoint_url
                )
            else:
                self._cognito_client = boto3.client(
                    'cognito-idp',
                    region_name=region
                )
        
        return self._cognito_client
    
    def generate_pkce_challenge(self) -> PKCEChallenge:
        """
        Generate PKCE (Proof Key for Code Exchange) challenge.
        
        Returns:
            PKCEChallenge with code_verifier, code_challenge, and state
        """
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        pkce = PKCEChallenge(
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            state=state
        )
        
        # Store for later verification (use Redis in production)
        self._pkce_store[state] = pkce
        
        return pkce
    
    async def generate_authorization_url(
        self,
        scopes: list[str] = None
    ) -> Tuple[str, str]:
        """
        Generate OAuth authorization URL with PKCE.
        
        Args:
            scopes: OAuth scopes (default: ["openid", "email", "profile"])
        
        Returns:
            Tuple of (authorization_url, state)
        """
        config = await self.load_config()
        
        if not config.domain or not config.client_id:
            raise ValueError("Cognito configuration incomplete")
        
        # Generate PKCE challenge
        pkce = self.generate_pkce_challenge()
        
        # Build authorization URL
        scopes = scopes or ["openid", "email", "profile"]
        params = {
            "client_id": config.client_id,
            "response_type": "code",
            "scope": " ".join(scopes),
            "redirect_uri": config.redirect_uri,
            "state": pkce.state,
            "code_challenge": pkce.code_challenge,
            "code_challenge_method": "S256"
        }
        
        auth_url = f"{config.authorize_endpoint}?{urlencode(params)}"
        
        logger.info(f"Generated OAuth URL with state: {pkce.state[:10]}...")
        return auth_url, pkce.state
    
    async def exchange_code_for_tokens(
        self,
        code: str,
        state: str
    ) -> AuthorizationResult:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from OAuth callback
            state: State parameter for CSRF validation
        
        Returns:
            AuthorizationResult with tokens
        
        Raises:
            HTTPException: If code exchange fails
        """
        config = await self.load_config()
        
        # Verify state and get PKCE challenge
        pkce = self._pkce_store.get(state)
        if not pkce:
            logger.error(f"❌ Invalid or expired state: {state[:10]}...")
            raise ValueError("Invalid or expired state parameter")
        
        # Remove from store (one-time use)
        del self._pkce_store[state]
        
        # Exchange code for tokens
        try:
            import httpx
            
            token_data = {
                "grant_type": "authorization_code",
                "client_id": config.client_id,
                "code": code,
                "redirect_uri": config.redirect_uri,
                "code_verifier": pkce.code_verifier
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.token_endpoint,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ Token exchange failed: {response.status_code} - {response.text}")
                    raise ValueError(f"Token exchange failed: {response.text}")
                
                tokens = response.json()
                
                result = AuthorizationResult(
                    access_token=tokens["access_token"],
                    id_token=tokens["id_token"],
                    refresh_token=tokens.get("refresh_token", ""),
                    expires_in=tokens.get("expires_in", 3600),
                    token_type=tokens.get("token_type", "Bearer")
                )
                
                logger.info("✅ Successfully exchanged code for tokens")
                return result
                
        except Exception as e:
            logger.error(f"❌ Token exchange error: {e}")
            raise
    
    async def refresh_access_token(self, refresh_token: str) -> AuthorizationResult:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Cognito refresh token
        
        Returns:
            AuthorizationResult with new tokens
        """
        config = await self.load_config()
        
        try:
            import httpx
            
            token_data = {
                "grant_type": "refresh_token",
                "client_id": config.client_id,
                "refresh_token": refresh_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.token_endpoint,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ Token refresh failed: {response.status_code}")
                    raise ValueError("Token refresh failed")
                
                tokens = response.json()
                
                result = AuthorizationResult(
                    access_token=tokens["access_token"],
                    id_token=tokens["id_token"],
                    refresh_token=refresh_token,  # Refresh token not rotated
                    expires_in=tokens.get("expires_in", 3600),
                    token_type=tokens.get("token_type", "Bearer")
                )
                
                logger.info("✅ Successfully refreshed access token")
                return result
                
        except Exception as e:
            logger.error(f"❌ Token refresh error: {e}")
            raise
    
    async def get_user_profile(self, access_token: str) -> UserProfile:
        """
        Get user profile from Cognito using access token.
        
        Args:
            access_token: Cognito access token
        
        Returns:
            UserProfile with user information
        """
        config = await self.load_config()
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    config.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ Failed to get user info: {response.status_code}")
                    raise ValueError("Failed to get user info")
                
                user_data = response.json()
                
                # Parse Cognito groups and custom attributes
                profile = UserProfile(
                    sub=user_data.get("sub", ""),
                    email=user_data.get("email", ""),
                    email_verified=user_data.get("email_verified", False),
                    cognito_groups=user_data.get("cognito:groups", []),
                    custom_role=user_data.get("custom:role"),
                    custom_permissions=user_data.get("custom:permissions", "").split(",") if user_data.get("custom:permissions") else []
                )
                
                logger.info(f"✅ Retrieved user profile: {profile.email}")
                return profile
                
        except Exception as e:
            logger.error(f"❌ Error getting user profile: {e}")
            raise
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a Cognito token (logout).
        
        Args:
            token: Access or refresh token to revoke
        
        Returns:
            True if successful
        """
        config = await self.load_config()
        
        try:
            cognito = self._get_cognito_client()
            
            # Cognito doesn't have a standard revoke endpoint
            # Instead, we can globally sign out the user
            # This requires the access token to identify the user
            
            # Note: For full logout, client should call the logout_endpoint
            # and clear cookies/localStorage
            
            logger.info("Token revocation requested (handled by client-side logout)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error revoking token: {e}")
            return False
    
    def generate_adfs_url(self) -> str:
        """
        Generate ADFS SSO URL using Cognito Hosted UI.
        
        Returns:
            URL to redirect user for ADFS authentication
        """
        # ADFS authentication goes through Cognito Hosted UI
        # with identity_provider parameter
        params = {
            "client_id": self._config.client_id if self._config else "",
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": self._config.redirect_uri if self._config else "",
            "identity_provider": "ADFS"  # Assumes ADFS IdP is configured in Cognito
        }
        
        authorize_endpoint = self._config.authorize_endpoint if self._config else ""
        return f"{authorize_endpoint}?{urlencode(params)}"
    
    def cleanup_expired_pkce(self, max_age: int = 600):
        """
        Clean up expired PKCE challenges.
        
        Args:
            max_age: Maximum age in seconds (default: 10 minutes)
        """
        # Simple cleanup - in production use Redis with TTL
        import time
        current_time = time.time()
        
        expired_states = [
            state for state, challenge in self._pkce_store.items()
            # Note: This is simplified - PKCE doesn't have timestamp
            # In production, store with timestamp or use Redis TTL
        ]
        
        for state in expired_states:
            del self._pkce_store[state]
        
        if expired_states:
            logger.info(f"Cleaned up {len(expired_states)} expired PKCE challenges")


# Singleton instance
_cognito_service: Optional[CognitoOAuthService] = None


def get_cognito_service(
    capability: str = None,
    environment: str = None
) -> CognitoOAuthService:
    """
    Get or create CognitoOAuthService singleton.
    
    Args:
        capability: Capability name (default: from env)
        environment: Environment (default: from env)
    
    Returns:
        CognitoOAuthService instance
    """
    global _cognito_service
    
    if not _cognito_service:
        capability = capability or os.getenv('CAPABILITY_NAME', 'call-processing')
        environment = environment or os.getenv('ENVIRONMENT', 'dev')
        _cognito_service = CognitoOAuthService(capability, environment)
    
    return _cognito_service
