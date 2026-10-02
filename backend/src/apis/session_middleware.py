"""
Session Management Middleware

Validates session tokens from HTTP-only cookies or Authorization headers.
Provides FastAPI dependencies for protected endpoints.

Supports:
- HTTP-only cookie-based sessions (recommended)
- Bearer token in Authorization header (fallback)
- Cognito JWT tokens (backward compatibility)
"""

from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import HTTPException, Depends, Cookie, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

try:
    from ..apis.cognito_auth_middleware import get_current_user as validate_cognito_user, CognitoUser
    COGNITO_MIDDLEWARE_AVAILABLE = True
except ImportError:
    COGNITO_MIDDLEWARE_AVAILABLE = False
    validate_cognito_user = None

from ..services.session_service import get_session_service


# Security scheme for Bearer tokens
security = HTTPBearer(auto_error=False)

SESSION_COOKIE_NAME = "nexus_session"


async def get_current_session(
    session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current session from cookie or Authorization header.
    Uses DynamoDB-backed session store for cross-pod persistence.
    """
    session_svc = get_session_service()

    if session_token:
        session = session_svc.get_session(session_token)
        if session:
            return {
                "user": {
                    "sub": session.get("user_sub", ""),
                    "email": session.get("email", ""),
                    "role": session.get("role", "User"),
                    "permissions": session.get("permissions", []),
                    "groups": session.get("groups", []),
                },
                "session_id": session.get("session_id", ""),
                "created_at": session.get("created_at", ""),
            }

    if credentials and credentials.credentials:
        token = credentials.credentials
        session = session_svc.get_session(token)
        if session:
            return {
                "user": {
                    "sub": session.get("user_sub", ""),
                    "email": session.get("email", ""),
                    "role": session.get("role", "User"),
                    "permissions": session.get("permissions", []),
                    "groups": session.get("groups", []),
                },
                "session_id": session.get("session_id", ""),
                "created_at": session.get("created_at", ""),
            }

        if COGNITO_MIDDLEWARE_AVAILABLE and validate_cognito_user:
            try:
                cognito_user = await validate_cognito_user(token)
                if cognito_user:
                    return {
                        "user": {
                            "sub": cognito_user.sub,
                            "email": cognito_user.email,
                            "groups": cognito_user.cognito_groups,
                            "role": cognito_user.role,
                            "permissions": cognito_user.permissions,
                            "email_verified": True,
                        },
                        "created_at": datetime.utcnow().isoformat(),
                    }
            except Exception as e:
                logger.warning(f"Failed to validate Cognito JWT: {e}")

    return None


async def require_authentication(
    session: Optional[Dict[str, Any]] = Depends(get_current_session)
) -> Dict[str, Any]:
    """
    Require valid authentication session.
    
    Use as FastAPI dependency for protected endpoints:
    
    ```python
    @app.get("/protected")
    async def protected_route(session: Dict = Depends(require_authentication)):
        user = session["user"]
        return {"message": f"Hello {user['email']}"}
    ```
    
    Args:
        session: Session data from get_current_session
    
    Returns:
        Session data
    
    Raises:
        HTTPException: If not authenticated (401)
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return session


async def get_current_user_from_session(
    session: Dict[str, Any] = Depends(require_authentication)
) -> Dict[str, Any]:
    """
    Get current user from session.
    
    Convenience wrapper for accessing user data.
    
    Args:
        session: Authenticated session
    
    Returns:
        User profile dictionary
    """
    return session["user"]


def require_role(*allowed_roles: str):
    """
    Create a dependency that requires specific role(s).
    
    Usage:
    ```python
    @app.get("/admin")
    async def admin_route(user: Dict = Depends(require_role("Admin", "Executive"))):
        return {"message": "Admin access granted"}
    ```
    
    Args:
        *allowed_roles: Role names that are allowed
    
    Returns:
        FastAPI dependency function
    """
    async def role_checker(
        session: Dict[str, Any] = Depends(require_authentication)
    ) -> Dict[str, Any]:
        user = session["user"]
        user_role = user.get("role", "")
        user_groups = user.get("groups", [])
        
        # Check if user has any of the allowed roles
        if user_role not in allowed_roles and not any(group in allowed_roles for group in user_groups):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}"
            )
        
        return session
    
    return role_checker


# Convenience dependencies for common roles
require_admin = require_role("Admin")
require_executive = require_role("Admin", "Executive")
require_sales_manager = require_role("Admin", "Executive", "SalesManager")


def has_permission(session: Dict[str, Any], permission: str) -> bool:
    """
    Check if user has specific permission.
    
    Uses the RBAC service to check role-based permissions.
    
    Args:
        session: User session
        permission: Permission string (e.g., "view_all_calls", "manage_users")
    
    Returns:
        True if user has permission
    """
    user = session["user"]
    user_role = user.get("role", "Rep")
    
    # Admins have all permissions
    if user_role == "Admin" or "Admin" in user.get("groups", []):
        return True
    
    # Check user's session permissions first (populated at login)
    session_permissions = user.get("permissions", [])
    if permission in session_permissions:
        return True
    
    # Fall back to RBAC service for dynamic permission checks
    try:
        from ..services.rbac_service import get_rbac_service
        rbac_service = get_rbac_service()
        return rbac_service.has_permission(user_role, permission)
    except Exception as e:
        logger.warning(f"RBAC service unavailable, using session permissions only: {e}")
        return permission in session_permissions


async def require_permission(
    permission: str,
    session: Dict[str, Any] = Depends(require_authentication)
) -> Dict[str, Any]:
    """
    Require specific permission.
    
    Usage:
    ```python
    from functools import partial
    
    @app.get("/calls")
    async def view_calls(session: Dict = Depends(partial(require_permission, "calls.view"))):
        return calls
    ```
    
    Args:
        permission: Required permission
        session: Authenticated session
    
    Returns:
        Session if user has permission
    
    Raises:
        HTTPException: If permission denied (403)
    """
    if not has_permission(session, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required: {permission}"
        )
    
    return session


def require_rbac_permission(permission_id: str):
    """
    Create a dependency that requires specific RBAC permission.
    
    Uses the RBAC service to check permissions dynamically.
    
    Usage:
    ```python
    @app.get("/calls")
    async def view_all_calls(session: Dict = Depends(require_rbac_permission("view_all_calls"))):
        return calls
    ```
    
    Args:
        permission_id: RBAC permission ID (e.g., "view_all_calls", "manage_users")
    
    Returns:
        FastAPI dependency function
    """
    async def permission_checker(
        session: Dict[str, Any] = Depends(require_authentication)
    ) -> Dict[str, Any]:
        if not has_permission(session, permission_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {permission_id}"
            )
        return session
    
    return permission_checker


def get_session_from_cookie(
    session: Optional[Dict[str, Any]] = Depends(get_current_session)
) -> Optional[Dict[str, Any]]:
    """
    Get session from cookie without requiring authentication.
    
    Returns None if no valid session exists.
    Useful for endpoints that have different behavior for authenticated vs anonymous users.
    """
    return session


# Export commonly used dependencies
__all__ = [
    "get_current_session",
    "get_session_from_cookie",
    "require_authentication",
    "get_current_user_from_session",
    "require_role",
    "require_admin",
    "require_executive",
    "require_sales_manager",
    "require_permission",
    "require_rbac_permission",
    "has_permission"
]
