"""
Cognito JWT Authentication Middleware
Validates AWS Cognito JWT tokens for API authentication
"""

import os
import json
import time
from typing import Optional, Dict, Any
from functools import lru_cache

import httpx
from jose import jwt, jwk, JWTError
from jose.utils import base64url_decode
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

# Security scheme
security = HTTPBearer(auto_error=False)

# Try to load Cognito configuration from config provider (SSM)
def _load_cognito_config():
    """Load Cognito configuration from SSM via config provider, with env var fallbacks"""
    region = os.getenv('COGNITO_REGION', 'us-east-1')
    user_pool_id = os.getenv('COGNITO_USER_POOL_ID', '')
    app_client_id = os.getenv('COGNITO_APP_CLIENT_ID', '')
    
    # Try to load from config provider if env vars are not set
    if not user_pool_id or not app_client_id:
        try:
            from ..config.config_provider import get_config
            config = get_config()
            if hasattr(config, 'cognito_user_pool_id') and config.cognito_user_pool_id:
                user_pool_id = user_pool_id or config.cognito_user_pool_id
            if hasattr(config, 'cognito_app_client_id') and config.cognito_app_client_id:
                app_client_id = app_client_id or config.cognito_app_client_id
            if hasattr(config, 'cognito_region') and config.cognito_region:
                region = config.cognito_region
            logger.info(f"✅ Loaded Cognito config from SSM: pool={user_pool_id}, region={region}")
        except Exception as e:
            logger.warning(f"⚠️ Could not load Cognito config from SSM: {e}")
    
    return region, user_pool_id, app_client_id

# Initialize Cognito configuration
COGNITO_REGION, COGNITO_USER_POOL_ID, COGNITO_APP_CLIENT_ID = _load_cognito_config()

# Log configuration for debugging
logger.info(f"Cognito Auth Middleware initialized: region={COGNITO_REGION}, pool_id={COGNITO_USER_POOL_ID}")

# JWKS URL for the Cognito User Pool
COGNITO_JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
COGNITO_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"

# Cache for JWKS keys
_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_time: float = 0
JWKS_CACHE_TTL = 3600  # Cache JWKS for 1 hour


async def get_jwks() -> Dict[str, Any]:
    """
    Fetch and cache the JWKS (JSON Web Key Set) from Cognito
    """
    global _jwks_cache, _jwks_cache_time
    
    current_time = time.time()
    
    # Return cached JWKS if still valid
    if _jwks_cache and (current_time - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(COGNITO_JWKS_URL, timeout=10.0)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_time = current_time
            logger.info(f"✅ Fetched JWKS from Cognito: {len(_jwks_cache.get('keys', []))} keys")
            return _jwks_cache
    except Exception as e:
        logger.error(f"❌ Failed to fetch JWKS: {e}")
        # Return cached keys if available, even if expired
        if _jwks_cache:
            logger.warning("⚠️ Using expired JWKS cache")
            return _jwks_cache
        raise HTTPException(status_code=503, detail="Authentication service unavailable")


def get_public_key(token: str, jwks: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Get the public key from JWKS that matches the token's key ID (kid)
    """
    try:
        # Decode header without verification to get kid
        header = jwt.get_unverified_header(token)
        kid = header.get('kid')
        
        if not kid:
            logger.warning("Token missing 'kid' in header")
            return None
        
        # Find matching key in JWKS
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                return key
        
        logger.warning(f"No matching key found for kid: {kid}")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting kid from token: {e}")
        return None


def verify_cognito_token(token: str, jwks: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify the Cognito JWT token and return its claims
    """
    # Get the public key
    public_key_data = get_public_key(token, jwks)
    if not public_key_data:
        raise HTTPException(status_code=401, detail="Invalid token: key not found")
    
    try:
        # Convert JWK to PEM format for verification
        public_key = jwk.construct(public_key_data)
        
        # Decode and verify the token
        claims = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            issuer=COGNITO_ISSUER,
            options={
                'verify_aud': False,  # Cognito uses 'client_id' in access tokens, not 'aud'
                'verify_exp': True,
                'verify_iat': True,
                'verify_iss': True
            }
        )
        
        # Additional validation for access tokens
        token_use = claims.get('token_use')
        if token_use not in ['access', 'id']:
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # Verify client ID if configured
        if COGNITO_APP_CLIENT_ID:
            client_id = claims.get('client_id') or claims.get('aud')
            if client_id != COGNITO_APP_CLIENT_ID:
                logger.warning(f"Token client_id mismatch: {client_id} != {COGNITO_APP_CLIENT_ID}")
                # Don't fail - might be a different valid client
        
        return claims
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTClaimsError as e:
        raise HTTPException(status_code=401, detail=f"Token claims validation failed: {str(e)}")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")


class CognitoUser:
    """
    Represents an authenticated Cognito user
    """
    def __init__(self, claims: Dict[str, Any]):
        self.claims = claims
        self.sub = claims.get('sub')  # Cognito user ID
        self.username = claims.get('username') or claims.get('cognito:username')
        self.email = claims.get('email')
        self.groups = claims.get('cognito:groups', [])
        self.token_use = claims.get('token_use')
        
        # Extract custom attributes
        self.role = self._get_role()
        self.department = claims.get('custom:department')
        self.employee_id = claims.get('custom:employee_id')
    
    def _get_role(self) -> str:
        """
        Determine user role from Cognito groups or custom attributes
        """
        groups = self.groups or []
        
        # Map Cognito groups to roles (priority order)
        if 'Admin' in groups or 'Admins' in groups:
            return 'Admin'
        elif 'Executive' in groups or 'Executives' in groups:
            return 'Executive'
        elif 'SalesManager' in groups or 'SalesManagers' in groups:
            return 'SalesManager'
        elif 'Rep' in groups or 'Reps' in groups:
            return 'Rep'
        
        # Fallback to custom attribute
        custom_role = self.claims.get('custom:role')
        if custom_role in ['Admin', 'Executive', 'SalesManager', 'Rep']:
            return custom_role
        
        return 'Rep'  # Default role
    
    def has_role(self, *roles: str) -> bool:
        """Check if user has any of the specified roles"""
        return self.role in roles
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'sub': self.sub,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'groups': self.groups,
            'department': self.department,
            'employee_id': self.employee_id
        }


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> CognitoUser:
    """
    Dependency to get the current authenticated user from Cognito JWT token
    """
    if not credentials:
        logger.warning("⚠️ No Authorization header provided in request")
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    token = credentials.credentials
    logger.debug(f"🔐 Validating token (first 20 chars): {token[:20]}...")
    
    try:
        # Fetch JWKS
        jwks = await get_jwks()
        
        # Verify token and get claims
        claims = verify_cognito_token(token, jwks)
        
        # Create user object
        user = CognitoUser(claims)
        
        logger.info(f"✅ Authenticated user: {user.username} (role: {user.role})")
        return user
        
    except HTTPException as he:
        logger.warning(f"⚠️ Token validation failed: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[CognitoUser]:
    """
    Dependency to optionally get the current user (doesn't fail if not authenticated)
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_role(*allowed_roles: str):
    """
    Dependency factory to require specific roles
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: CognitoUser = Depends(require_role("Admin"))):
            ...
    """
    async def role_checker(user: CognitoUser = Depends(get_current_user)) -> CognitoUser:
        if not user.has_role(*allowed_roles):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {' or '.join(allowed_roles)}"
            )
        return user
    
    return role_checker


# Convenience role dependencies
require_admin = require_role("Admin")
require_executive = require_role("Admin", "Executive")
require_manager = require_role("Admin", "Executive", "SalesManager")
require_any_role = require_role("Admin", "Executive", "SalesManager", "Rep")

