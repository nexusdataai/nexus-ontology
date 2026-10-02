"""
Authentication and Authorization REST API
User authentication, token management, and access control
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import secrets
from loguru import logger

# Create router
router = APIRouter()

# Security scheme
security = HTTPBearer()

# Mock user database
MOCK_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin",
        "email": "admin@example.com"
    },
    "user": {
        "password_hash": hashlib.sha256("user123".encode()).hexdigest(),
        "role": "user",
        "email": "user@example.com"
    }
}

# Mock token storage (in production, use Redis or database)
ACTIVE_TOKENS = {}


# ==========================================
# Authentication Endpoints
# ==========================================

from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(request: LoginRequest) -> Dict[str, Any]:
    """
    User login endpoint
    
    Authenticates user and returns access token.
    """
    try:
        # Validate credentials
        if request.username not in MOCK_USERS:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = MOCK_USERS[request.username]
        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        
        if password_hash != user["password_hash"]:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Generate token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Store token
        ACTIVE_TOKENS[token] = {
            "username": request.username,
            "role": user["role"],
            "expires_at": expires_at.isoformat()
        }
        
        return {
            "success": True,
            "message": "Login successful",
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 86400,  # 24 hours in seconds
            "user": {
                "username": request.username,
                "email": user["email"],
                "role": user["role"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    User logout endpoint
    
    Invalidates the access token.
    """
    try:
        token = credentials.credentials
        
        if token in ACTIVE_TOKENS:
            del ACTIVE_TOKENS[token]
            
        return {
            "success": True,
            "message": "Logout successful"
        }
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Refresh access token
    
    Issues a new token before the current one expires.
    """
    try:
        old_token = credentials.credentials
        
        if old_token not in ACTIVE_TOKENS:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        token_data = ACTIVE_TOKENS[old_token]
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if expires_at < datetime.utcnow():
            del ACTIVE_TOKENS[old_token]
            raise HTTPException(status_code=401, detail="Token expired")
        
        # Generate new token
        new_token = secrets.token_urlsafe(32)
        new_expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Store new token
        ACTIVE_TOKENS[new_token] = {
            "username": token_data["username"],
            "role": token_data["role"],
            "expires_at": new_expires_at.isoformat()
        }
        
        # Remove old token
        del ACTIVE_TOKENS[old_token]
        
        return {
            "success": True,
            "message": "Token refreshed",
            "access_token": new_token,
            "token_type": "Bearer",
            "expires_in": 86400  # 24 hours
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/verify")
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Verify access token
    
    Checks if the token is valid and returns user info.
    """
    try:
        token = credentials.credentials
        
        if token not in ACTIVE_TOKENS:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        token_data = ACTIVE_TOKENS[token]
        
        # Check expiration
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if expires_at < datetime.utcnow():
            del ACTIVE_TOKENS[token]
            raise HTTPException(status_code=401, detail="Token expired")
        
        # Get user info
        username = token_data["username"]
        user = MOCK_USERS.get(username, {})
        
        return {
            "valid": True,
            "username": username,
            "role": token_data["role"],
            "email": user.get("email"),
            "expires_at": token_data["expires_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current user information
    
    Returns details about the authenticated user.
    """
    try:
        token = credentials.credentials
        
        if token not in ACTIVE_TOKENS:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        token_data = ACTIVE_TOKENS[token]
        username = token_data["username"]
        user = MOCK_USERS.get(username, {})
        
        return {
            "username": username,
            "email": user.get("email"),
            "role": token_data["role"],
            "created_at": "2024-01-01T00:00:00Z",  # Mock creation date
            "last_login": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str
    role: str = "user"

@router.post("/register")
async def register(request: RegisterRequest) -> Dict[str, Any]:
    """
    Register new user
    
    Creates a new user account.
    """
    try:
        # Check if user exists
        if request.username in MOCK_USERS:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Validate role
        if request.role not in ["user", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        # Create user (in production, save to database)
        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        MOCK_USERS[request.username] = {
            "password_hash": password_hash,
            "role": request.role,
            "email": request.email
        }
        
        # Auto-login: generate token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        ACTIVE_TOKENS[token] = {
            "username": request.username,
            "role": request.role,
            "expires_at": expires_at.isoformat()
        }
        
        return {
            "success": True,
            "message": "Registration successful",
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 86400,
            "user": {
                "username": request.username,
                "email": request.email,
                "role": request.role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/permissions")
async def get_permissions(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get user permissions
    
    Returns the permissions for the authenticated user.
    """
    try:
        token = credentials.credentials
        
        if token not in ACTIVE_TOKENS:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        token_data = ACTIVE_TOKENS[token]
        role = token_data["role"]
        
        # Define permissions by role
        permissions_map = {
            "admin": [
                "journeys.create",
                "journeys.read",
                "journeys.update",
                "journeys.delete",
                "analytics.view",
                "analytics.export",
                "users.manage",
                "system.configure"
            ],
            "user": [
                "journeys.create",
                "journeys.read",
                "journeys.update",
                "analytics.view"
            ]
        }
        
        permissions = permissions_map.get(role, [])
        
        return {
            "role": role,
            "permissions": permissions,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting permissions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==========================================
# Helper Functions
# ==========================================

async def validate_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """
    Validate API key from header
    
    Used for simple API key authentication.
    """
    if not x_api_key:
        return False
    
    # In production, check against database or environment variable
    valid_keys = ["super-secret", "test-key-123"]
    return x_api_key in valid_keys


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current user from token
    
    Helper function for protected endpoints.
    """
    token = credentials.credentials
    
    if token not in ACTIVE_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    token_data = ACTIVE_TOKENS[token]
    
    # Check expiration
    expires_at = datetime.fromisoformat(token_data["expires_at"])
    if expires_at < datetime.utcnow():
        del ACTIVE_TOKENS[token]
        raise HTTPException(status_code=401, detail="Token expired")
    
    return {
        "username": token_data["username"],
        "role": token_data["role"]
    }