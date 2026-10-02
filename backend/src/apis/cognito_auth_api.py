"""
Cognito Authentication API

Production-ready authentication endpoints that handle:
- OAuth 2.0 authorization code flow with PKCE
- ADFS SSO via Cognito hosted UI
- Token exchange and refresh
- Session management
- User profile retrieval

Replaces frontend direct Cognito integration.
"""

import os
import secrets
import time
from collections import defaultdict
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, Cookie, Depends, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from loguru import logger
import boto3
from botocore.exceptions import ClientError

from ..services.cognito_oauth_service import (
    get_cognito_service,
    CognitoOAuthService,
    UserProfile,
    AuthorizationResult
)
from ..apis.cognito_auth_middleware import get_current_user, CognitoUser
from ..services.session_service import get_session_service
from ..services.audit_service import get_audit_service, AuditEvent

try:
    from ..services.rbac_service import get_rbac_service
    RBAC_AVAILABLE = True
except ImportError:
    RBAC_AVAILABLE = False


# Router
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# Rate limiter: 5 login attempts per IP per 60 seconds
_login_attempts: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 5


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    attempts = _login_attempts[ip]
    _login_attempts[ip] = [t for t in attempts if now - t < RATE_LIMIT_WINDOW]
    if len(_login_attempts[ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait 60 seconds.")
    _login_attempts[ip].append(now)


# Request/Response Models
class DirectLoginRequest(BaseModel):
    """Direct login request with email and password."""
    email: str  # Changed from EmailStr to allow .local and .test domains
    password: str


class DirectLoginResponse(BaseModel):
    """Response from direct login."""
    user: Dict[str, Any]
    session: Dict[str, Any]
    requires_password_change: bool = False
    message: str = "Login successful"


class PasswordChallengeRequest(BaseModel):
    """Request to complete password challenge."""
    email: EmailStr
    new_password: str
    session: str  # Cognito session token from challenge


class LoginInitResponse(BaseModel):
    """Response from login initialization."""
    authorization_url: str
    state: str
    message: str = "Redirect to this URL to authenticate"


class LoginCallbackRequest(BaseModel):
    """Request for OAuth callback."""
    code: str
    state: str


class LoginCallbackResponse(BaseModel):
    """Response from successful login."""
    user: Dict[str, Any]
    session_token: Optional[str] = None  # Only if not using cookies
    expires_in: int
    message: str = "Login successful"


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str


class LogoutResponse(BaseModel):
    """Response from logout."""
    message: str = "Logged out successfully"
    logout_url: Optional[str] = None


class UserProfileResponse(BaseModel):
    """User profile response."""
    user: Dict[str, Any]


class MFAVerifyRequest(BaseModel):
    """MFA TOTP verification during login."""
    email: str
    totp_code: str
    session: str  # Cognito session from MFA challenge


class MFASetupVerifyRequest(BaseModel):
    """Verify first TOTP code to complete MFA setup."""
    access_token: str
    totp_code: str
    session: Optional[str] = None


SESSION_COOKIE_NAME = "nexus_session"
SESSION_MAX_AGE = 3600 * 12  # 12 hours
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


async def _load_permissions_for_role(role: str) -> list:
    """Load RBAC permissions for a role from DynamoDB config."""
    if not RBAC_AVAILABLE:
        return []
    try:
        rbac_svc = get_rbac_service()
        config = await rbac_svc.get_config()
        return config.rolePermissions.get(role, [])
    except Exception as e:
        logger.warning(f"RBAC permissions load failed: {e}")
        return []


async def _create_session_and_cookie(
    response: Response,
    user_profile: UserProfile,
    request: Optional[Request] = None,
) -> str:
    """Create DynamoDB session + set cookie + audit log."""
    role = user_profile.custom_role or (user_profile.cognito_groups[0] if user_profile.cognito_groups else "User")
    permissions = await _load_permissions_for_role(role)

    session_svc = get_session_service()
    session_id = session_svc.create_session(
        user_sub=user_profile.sub,
        email=user_profile.email,
        role=role,
        permissions=permissions,
        groups=user_profile.cognito_groups,
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )

    audit = get_audit_service()
    audit.log(
        AuditEvent.SESSION_CREATED,
        user_email=user_profile.email,
        details={"role": role, "groups": user_profile.cognito_groups},
        ip_address=request.client.host if request and request.client else "",
    )

    return session_id


def get_session_from_cookie(
    session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
) -> Optional[Dict[str, Any]]:
    """Get session data from DynamoDB via cookie."""
    if not session_token:
        return None
    session_svc = get_session_service()
    session = session_svc.get_session(session_token)
    if not session:
        return None
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


# Endpoints
@router.post("/login", response_model=DirectLoginResponse)
async def direct_login(
    request: DirectLoginRequest,
    response: Response,
    http_request: Request = None,
    cognito: CognitoOAuthService = Depends(get_cognito_service)
):
    """
    Direct login with email and password (no redirect).
    
    Uses Cognito ADMIN_INITIATE_AUTH for server-side authentication.
    User stays in your app - no redirect to Cognito hosted UI.
    
    Args:
        request: Email and password
        response: FastAPI response for setting cookies
    
    Returns:
        User profile and session
    """
    # Rate limiting
    client_ip = http_request.client.host if http_request and http_request.client else "unknown"
    _check_rate_limit(client_ip)

    # Input sanitization
    email = request.email.strip().lower()
    if not email or '@' not in email or len(email) > 254:
        raise HTTPException(status_code=400, detail="Invalid email format")

    try:
        config = await cognito.load_config()
        cognito_client = boto3.client('cognito-idp', region_name=config.region)
        
        logger.info(f"Direct login attempt for: {email}")
        
        # Initiate auth with ADMIN_INITIATE_AUTH (server-side only)
        auth_response = cognito_client.admin_initiate_auth(
            UserPoolId=config.user_pool_id,
            ClientId=config.client_id,
            AuthFlow='ADMIN_USER_PASSWORD_AUTH',  # Admin auth with username/password
            AuthParameters={
                'USERNAME': request.email,
                'PASSWORD': request.password
            }
        )
        
        challenge = auth_response.get('ChallengeName')

        # Handle challenges
        if challenge == 'NEW_PASSWORD_REQUIRED':
            logger.info(f"Password change required for: {request.email}")
            return DirectLoginResponse(
                user={"email": request.email},
                session={"cognito_session": auth_response['Session']},
                requires_password_change=True,
                message="New password required"
            )

        if challenge == 'SOFTWARE_TOKEN_MFA':
            logger.info(f"MFA required for: {request.email}")
            return DirectLoginResponse(
                user={"email": request.email},
                session={"cognito_session": auth_response['Session'], "challenge": "MFA_REQUIRED"},
                requires_password_change=False,
                message="MFA verification required"
            )

        if challenge == 'MFA_SETUP':
            logger.info(f"MFA setup required for: {request.email}")
            return DirectLoginResponse(
                user={"email": request.email},
                session={"cognito_session": auth_response['Session'], "challenge": "MFA_SETUP_REQUIRED"},
                requires_password_change=False,
                message="MFA setup required"
            )

        # No challenge — auth succeeded
        tokens = auth_response.get('AuthenticationResult')
        if not tokens:
            raise ValueError("No tokens returned from Cognito")

        user_response = cognito_client.get_user(AccessToken=tokens['AccessToken'])
        attributes = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}

        try:
            groups_response = cognito_client.admin_list_groups_for_user(
                Username=request.email, UserPoolId=config.user_pool_id
            )
            groups = [g['GroupName'] for g in groups_response.get('Groups', [])]
        except Exception:
            groups = []

        role = groups[0] if groups else 'User'
        permissions = await _load_permissions_for_role(role)

        user_profile = UserProfile(
            sub=attributes.get('sub', ''),
            email=attributes.get('email', request.email),
            email_verified=attributes.get('email_verified', 'false') == 'true',
            cognito_groups=groups,
            custom_role=role,
            custom_permissions=permissions,
        )

        await _create_session_and_cookie(response, user_profile, http_request)

        audit = get_audit_service()
        audit.log(AuditEvent.LOGIN_SUCCESS, user_email=request.email,
                  ip_address=http_request.client.host if http_request and http_request.client else "")

        logger.info(f"Direct login successful: {request.email}")

        return DirectLoginResponse(
            user=user_profile.to_dict(),
            session={"expires_in": tokens['ExpiresIn']},
            requires_password_change=False,
            message="Login successful"
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        audit = get_audit_service()
        audit.log(AuditEvent.LOGIN_FAILED, user_email=request.email,
                  details={"error": error_code}, success=False,
                  ip_address=http_request.client.host if http_request and http_request.client else "")

        if error_code == 'NotAuthorizedException':
            raise HTTPException(status_code=401, detail="Invalid email or password")
        elif error_code == 'UserNotFoundException':
            raise HTTPException(status_code=401, detail="Invalid email or password")
        elif error_code == 'UserNotConfirmedException':
            raise HTTPException(status_code=403, detail="Email not verified")
        elif error_code == 'PasswordResetRequiredException':
            raise HTTPException(status_code=403, detail="Password reset required")
        else:
            logger.error(f"Cognito error: {error_code} - {e}")
            raise HTTPException(status_code=500, detail="Authentication failed")
    
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Login error: {e}")
        for line in tb.split('\n'):
            if line.strip():
                logger.error(f"TB: {line}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/login/new-password")
async def complete_new_password(
    request: PasswordChallengeRequest,
    response: Response,
    http_request: Request = None,
    cognito: CognitoOAuthService = Depends(get_cognito_service)
):
    """
    Complete new password challenge (first-time login).

    After setting the new password, Cognito may return another challenge
    (SOFTWARE_TOKEN_MFA or MFA_SETUP) if MFA is enabled on the pool.
    """
    try:
        config = await cognito.load_config()
        cognito_client = boto3.client('cognito-idp', region_name=config.region)

        logger.info(f"Completing password challenge for: {request.email}")

        auth_response = cognito_client.admin_respond_to_auth_challenge(
            UserPoolId=config.user_pool_id,
            ClientId=config.client_id,
            ChallengeName='NEW_PASSWORD_REQUIRED',
            Session=request.session,
            ChallengeResponses={
                'USERNAME': request.email,
                'NEW_PASSWORD': request.new_password
            }
        )

        # Check for cascading MFA challenges
        challenge = auth_response.get('ChallengeName')

        if challenge == 'SOFTWARE_TOKEN_MFA':
            logger.info(f"MFA required after password change for: {request.email}")
            return DirectLoginResponse(
                user={"email": request.email},
                session={"cognito_session": auth_response['Session'], "challenge": "MFA_REQUIRED"},
                requires_password_change=False,
                message="Password changed. MFA verification required."
            )

        if challenge == 'MFA_SETUP':
            logger.info(f"MFA setup required after password change for: {request.email}")
            return DirectLoginResponse(
                user={"email": request.email},
                session={"cognito_session": auth_response['Session'], "challenge": "MFA_SETUP_REQUIRED"},
                requires_password_change=False,
                message="Password changed. MFA setup required."
            )

        tokens = auth_response.get('AuthenticationResult')
        if not tokens:
            raise ValueError(f"No tokens and no recognized challenge (got: {challenge})")

        user_response = cognito_client.get_user(AccessToken=tokens['AccessToken'])
        attributes = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}

        try:
            groups_response = cognito_client.admin_list_groups_for_user(
                Username=request.email,
                UserPoolId=config.user_pool_id
            )
            groups = [g['GroupName'] for g in groups_response.get('Groups', [])]
        except Exception:
            groups = []

        role = groups[0] if groups else 'User'
        permissions = await _load_permissions_for_role(role)

        user_profile = UserProfile(
            sub=attributes.get('sub', ''),
            email=attributes.get('email', request.email),
            email_verified=attributes.get('email_verified', 'false') == 'true',
            cognito_groups=groups,
            custom_role=role,
            custom_permissions=permissions,
        )

        await _create_session_and_cookie(response, user_profile, http_request)

        logger.info(f"Password change complete: {request.email}")

        return DirectLoginResponse(
            user=user_profile.to_dict(),
            session={"expires_in": tokens['ExpiresIn']},
            requires_password_change=False,
            message="Password changed successfully"
        )

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"Password challenge error: {error_code} - {e}")

        if error_code == 'InvalidPasswordException':
            raise HTTPException(status_code=400, detail="Password does not meet requirements")
        raise HTTPException(status_code=500, detail="Failed to change password")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Password challenge error: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.get("/login/init", response_model=LoginInitResponse)
async def login_init(
    cognito: CognitoOAuthService = Depends(get_cognito_service)
):
    """
    Initialize OAuth login flow.
    
    Generates authorization URL with PKCE challenge.
    Frontend should redirect user to this URL.
    
    Returns:
        Authorization URL and state parameter
    """
    try:
        auth_url, state = await cognito.generate_authorization_url()
        
        return LoginInitResponse(
            authorization_url=auth_url,
            state=state,
            message="Redirect user to authorization_url"
        )
        
    except Exception as e:
        logger.error(f"❌ Login init failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize login: {str(e)}")


@router.post("/login/callback", response_model=LoginCallbackResponse)
async def login_callback(
    code: str = Query(..., description="Authorization code from OAuth callback"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    response: Response = None,
    cognito: CognitoOAuthService = Depends(get_cognito_service)
):
    """
    Handle OAuth callback after user authenticates.
    
    Exchanges authorization code for tokens and creates session.
    
    Args:
        code: Authorization code from Cognito
        state: State parameter for validation
        response: FastAPI response object for setting cookies
    
    Returns:
        User profile and session information
    """
    try:
        # Exchange code for tokens
        tokens = await cognito.exchange_code_for_tokens(code, state)
        
        # Get user profile
        user_profile = await cognito.get_user_profile(tokens.access_token)
        
        await _create_session_and_cookie(response, user_profile)
        
        return LoginCallbackResponse(
            user=user_profile.to_dict(),
            session_token=None,
            expires_in=tokens.expires_in,
            message="Login successful"
        )
        
    except ValueError as e:
        logger.error(f"❌ Login callback failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Login callback error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.get("/sso/adfs")
async def adfs_sso_redirect(
    cognito: CognitoOAuthService = Depends(get_cognito_service)
):
    """
    Initiate ADFS SSO via Cognito hosted UI.
    
    Redirects user to Cognito with identity_provider=ADFS.
    After authentication, Cognito redirects back to callback URL.
    
    Returns:
        Redirect response to Cognito hosted UI
    """
    try:
        await cognito.load_config()  # Ensure config is loaded
        adfs_url = cognito.generate_adfs_url()
        
        logger.info("Redirecting to ADFS SSO via Cognito")
        return RedirectResponse(url=adfs_url, status_code=302)
        
    except Exception as e:
        logger.error(f"❌ ADFS redirect failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize ADFS login")


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie)
):
    """
    Get current authenticated user profile.
    
    Reads session from HTTP-only cookie.
    
    Returns:
        User profile information
    """
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    return UserProfileResponse(user=session["user"])


@router.post("/refresh", response_model=LoginCallbackResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    response: Response,
    cognito: CognitoOAuthService = Depends(get_cognito_service)
):
    """
    Refresh access token using refresh token.
    
    Args:
        request: Refresh token request
        response: FastAPI response for setting new session cookie
    
    Returns:
        New tokens and user profile
    """
    try:
        # Refresh tokens
        tokens = await cognito.refresh_access_token(request.refresh_token)
        
        # Get updated user profile
        user_profile = await cognito.get_user_profile(tokens.access_token)
        
        await _create_session_and_cookie(response, user_profile)
        
        return LoginCallbackResponse(
            user=user_profile.to_dict(),
            expires_in=tokens.expires_in,
            message="Token refreshed successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Token refresh failed: {e}")
        raise HTTPException(status_code=401, detail="Failed to refresh token")


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie),
    cognito: CognitoOAuthService = Depends(get_cognito_service)
):
    """
    Logout user and clear session.
    
    Clears HTTP-only cookie and provides Cognito logout URL.
    
    Args:
        response: FastAPI response for clearing cookie
        session: Current session (if any)
    
    Returns:
        Logout confirmation and Cognito logout URL
    """
    # Delete server-side session from DynamoDB
    if session and session.get("session_id"):
        try:
            session_svc = get_session_service()
            session_svc.delete_session(session["session_id"])
            audit = get_audit_service()
            audit.log(AuditEvent.LOGOUT, user_email=session.get("user", {}).get("email", ""))
        except Exception as e:
            logger.warning(f"Failed to delete session from DynamoDB: {e}")

    response.delete_cookie(key=SESSION_COOKIE_NAME)

    # Generate Cognito logout URL
    config = await cognito.load_config()
    logout_params = {
        "client_id": config.client_id,
        "logout_uri": config.logout_uri  # Use proper logout URI (just origin)
    }
    
    from urllib.parse import urlencode
    logout_url = f"{config.logout_endpoint}?{urlencode(logout_params)}"
    
    logger.info(f"Logout URL generated: {logout_url}")
    
    logger.info(f"User logged out")
    
    return LogoutResponse(
        message="Logged out successfully",
        logout_url=logout_url
    )


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/password/change")
async def change_password(
    request: ChangePasswordRequest,
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie),
    cognito: CognitoOAuthService = Depends(get_cognito_service)
):
    """Change password for the currently authenticated user."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_data = session.get("user", {})
    email = user_data.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="Cannot determine user email from session")

    try:
        config = await cognito.load_config()
        cognito_client = cognito._get_cognito_client()

        cognito_client.admin_initiate_auth(
            UserPoolId=config.user_pool_id,
            ClientId=config.client_id,
            AuthFlow='ADMIN_USER_PASSWORD_AUTH',
            AuthParameters={'USERNAME': email, 'PASSWORD': request.old_password}
        )

        cognito_client.admin_set_user_password(
            UserPoolId=config.user_pool_id,
            Username=email,
            Password=request.new_password,
            Permanent=True
        )

        return {"success": True, "message": "Password changed successfully"}

    except ClientError as e:
        code = e.response['Error']['Code']
        if code == 'NotAuthorizedException':
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        if code == 'InvalidPasswordException':
            raise HTTPException(status_code=400, detail="New password does not meet requirements (min 8 chars, uppercase, lowercase, numbers)")
        logger.error(f"Password change failed: {code} - {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.get("/health")
async def auth_health():
    """
    Health check endpoint for authentication service.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "cognito-auth",
        "timestamp": datetime.utcnow().isoformat()
    }


# ─── MFA Endpoints ────────────────────────────────────────────────────────────

@router.post("/mfa/verify")
async def mfa_verify(
    request: MFAVerifyRequest,
    response: Response,
    http_request: Request = None,
    cognito: CognitoOAuthService = Depends(get_cognito_service),
):
    """Verify TOTP code during login MFA challenge."""
    try:
        config = await cognito.load_config()
        cognito_client = boto3.client("cognito-idp", region_name=config.region)

        auth_response = cognito_client.admin_respond_to_auth_challenge(
            UserPoolId=config.user_pool_id,
            ClientId=config.client_id,
            ChallengeName="SOFTWARE_TOKEN_MFA",
            ChallengeResponses={
                "USERNAME": request.email,
                "SOFTWARE_TOKEN_MFA_CODE": request.totp_code,
            },
            Session=request.session,
        )

        tokens = auth_response.get("AuthenticationResult")
        if not tokens:
            raise ValueError("MFA verification failed")

        user_response = cognito_client.get_user(AccessToken=tokens["AccessToken"])
        attributes = {a["Name"]: a["Value"] for a in user_response["UserAttributes"]}

        try:
            groups_resp = cognito_client.admin_list_groups_for_user(
                Username=request.email, UserPoolId=config.user_pool_id
            )
            groups = [g["GroupName"] for g in groups_resp.get("Groups", [])]
        except Exception:
            groups = []

        role = groups[0] if groups else "User"
        permissions = await _load_permissions_for_role(role)

        user_profile = UserProfile(
            sub=attributes.get("sub", ""),
            email=attributes.get("email", request.email),
            email_verified=True,
            cognito_groups=groups,
            custom_role=role,
            custom_permissions=permissions,
        )

        await _create_session_and_cookie(response, user_profile, http_request)

        audit = get_audit_service()
        audit.log(AuditEvent.MFA_VERIFIED, user_email=request.email,
                  ip_address=http_request.client.host if http_request and http_request.client else "")
        audit.log(AuditEvent.LOGIN_SUCCESS, user_email=request.email,
                  ip_address=http_request.client.host if http_request and http_request.client else "")

        return {"success": True, "user": user_profile.to_dict(), "message": "MFA verified"}

    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg = e.response["Error"].get("Message", "")
        logger.error(f"MFA verify Cognito error: {code} - {msg}")
        audit = get_audit_service()
        audit.log(AuditEvent.MFA_FAILED, user_email=request.email, success=False,
                  details={"error": code, "message": msg})
        if code == "CodeMismatchException":
            raise HTTPException(status_code=401, detail="Invalid TOTP code")
        if code == "ExpiredCodeException":
            raise HTTPException(status_code=401, detail="TOTP code expired, please login again")
        if code == "NotAuthorizedException":
            raise HTTPException(status_code=401, detail="Session expired. Please login again.")
        raise HTTPException(status_code=500, detail=f"MFA verification failed: {code}")
    except Exception as e:
        logger.error(f"MFA verify unexpected error: {e}")
        raise HTTPException(status_code=500, detail="MFA verification failed")


class MFASetupRequest(BaseModel):
    """MFA setup request — supports two modes:
    1. Settings page: email + password (re-authenticates to get AccessToken)
    2. Login challenge: cognito_session from MFA_SETUP challenge
    """
    email: Optional[str] = None
    password: Optional[str] = None
    cognito_session: Optional[str] = None


@router.post("/mfa/setup")
async def mfa_setup(
    request: MFASetupRequest,
    http_request: Request = None,
    cognito: CognitoOAuthService = Depends(get_cognito_service),
):
    """
    Initiate TOTP MFA setup.

    Two modes:
    - Login challenge: send cognito_session (from MFA_SETUP challenge) + email.
      Uses associate_software_token(Session=...) — no AccessToken needed.
    - Settings page: send email + password. Re-authenticates to get AccessToken,
      then uses associate_software_token(AccessToken=...).
    """
    config = await cognito.load_config()
    cognito_client = boto3.client("cognito-idp", region_name=config.region)

    # Mode 1: Login challenge flow (Session-based)
    if request.cognito_session:
        try:
            resp = cognito_client.associate_software_token(
                Session=request.cognito_session,
            )
            secret = resp.get("SecretCode", "")
            new_session = resp.get("Session", "")
            email = request.email or ""

            totp_uri = f"otpauth://totp/CallSense:{email}?secret={secret}&issuer=CallSense"

            audit = get_audit_service()
            audit.log(AuditEvent.MFA_SETUP, user_email=email, details={"action": "initiated", "mode": "challenge"})

            return {
                "secret": secret,
                "totp_uri": totp_uri,
                "email": email,
                "cognito_session": new_session,
                "mode": "challenge",
            }
        except ClientError as e:
            code = e.response["Error"]["Code"]
            logger.error(f"MFA setup (challenge mode) failed: {code} - {e}")
            if code == "NotAuthorizedException":
                raise HTTPException(status_code=401, detail="Session expired. Please login again.")
            raise HTTPException(status_code=500, detail="MFA setup failed")

    # Mode 2: Settings page flow (AccessToken-based)
    access_token = ""
    if request.email and request.password:
        try:
            auth_resp = cognito_client.admin_initiate_auth(
                UserPoolId=config.user_pool_id,
                ClientId=config.client_id,
                AuthFlow="ADMIN_USER_PASSWORD_AUTH",
                AuthParameters={"USERNAME": request.email, "PASSWORD": request.password},
            )
            challenge = auth_resp.get("ChallengeName")
            if challenge:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot setup MFA: auth returned challenge '{challenge}'. Complete login first.",
                )
            tokens = auth_resp.get("AuthenticationResult", {})
            access_token = tokens.get("AccessToken", "")
            if not access_token:
                raise HTTPException(status_code=401, detail="Authentication failed. Check your password.")
        except ClientError as e:
            logger.warning(f"MFA setup auth failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        except HTTPException:
            raise
    else:
        auth_header = http_request.headers.get("Authorization", "") if http_request else ""
        access_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

    if not access_token:
        raise HTTPException(status_code=401, detail="Email and password required, or provide cognito_session for challenge flow")

    try:
        resp = cognito_client.associate_software_token(AccessToken=access_token)
        secret = resp.get("SecretCode", "")

        user_resp = cognito_client.get_user(AccessToken=access_token)
        email = ""
        for attr in user_resp.get("UserAttributes", []):
            if attr["Name"] == "email":
                email = attr["Value"]

        totp_uri = f"otpauth://totp/CallSense:{email}?secret={secret}&issuer=CallSense"

        audit = get_audit_service()
        audit.log(AuditEvent.MFA_SETUP, user_email=email, details={"action": "initiated", "mode": "settings"})

        return {
            "secret": secret,
            "totp_uri": totp_uri,
            "email": email,
            "access_token": access_token,
            "mode": "settings",
        }

    except Exception as e:
        logger.error(f"MFA setup failed: {e}")
        raise HTTPException(status_code=500, detail="MFA setup failed")


class MFASetupChallengeVerifyRequest(BaseModel):
    """Verify TOTP during login MFA_SETUP challenge flow."""
    email: str
    totp_code: str
    cognito_session: str


@router.post("/mfa/setup/challenge/verify")
async def mfa_setup_challenge_verify(
    request: MFASetupChallengeVerifyRequest,
    response: Response,
    http_request: Request = None,
    cognito: CognitoOAuthService = Depends(get_cognito_service),
):
    """
    Complete MFA setup during login challenge flow.

    1. verify_software_token(Session=...) to validate the TOTP code
    2. admin_respond_to_auth_challenge(MFA_SETUP) to complete authentication
    3. Create session + set cookie
    """
    try:
        config = await cognito.load_config()
        cognito_client = boto3.client("cognito-idp", region_name=config.region)

        # Step 1: Verify the TOTP code using the challenge Session
        verify_resp = cognito_client.verify_software_token(
            Session=request.cognito_session,
            UserCode=request.totp_code,
            FriendlyDeviceName="CallSense-TOTP",
        )

        if verify_resp.get("Status") != "SUCCESS":
            raise HTTPException(status_code=400, detail="TOTP verification failed")

        verify_session = verify_resp.get("Session", "")
        if not verify_session:
            raise HTTPException(status_code=500, detail="No session returned from TOTP verification")

        # Step 2: Complete auth by responding to MFA_SETUP challenge
        auth_response = cognito_client.admin_respond_to_auth_challenge(
            UserPoolId=config.user_pool_id,
            ClientId=config.client_id,
            ChallengeName="MFA_SETUP",
            ChallengeResponses={"USERNAME": request.email},
            Session=verify_session,
        )

        tokens = auth_response.get("AuthenticationResult")
        if not tokens:
            challenge = auth_response.get("ChallengeName", "unknown")
            logger.error(f"MFA setup challenge verify: unexpected challenge after MFA_SETUP: {challenge}")
            raise HTTPException(status_code=500, detail=f"Unexpected challenge: {challenge}")

        # Step 3: Build user profile and create session
        user_response = cognito_client.get_user(AccessToken=tokens["AccessToken"])
        attributes = {a["Name"]: a["Value"] for a in user_response["UserAttributes"]}

        try:
            groups_resp = cognito_client.admin_list_groups_for_user(
                Username=request.email, UserPoolId=config.user_pool_id
            )
            groups = [g["GroupName"] for g in groups_resp.get("Groups", [])]
        except Exception:
            groups = []

        role = groups[0] if groups else "User"
        permissions = await _load_permissions_for_role(role)

        user_profile = UserProfile(
            sub=attributes.get("sub", ""),
            email=attributes.get("email", request.email),
            email_verified=True,
            cognito_groups=groups,
            custom_role=role,
            custom_permissions=permissions,
        )

        await _create_session_and_cookie(response, user_profile, http_request)

        audit = get_audit_service()
        audit.log(AuditEvent.MFA_SETUP, user_email=request.email, details={"action": "completed", "mode": "challenge"})
        audit.log(AuditEvent.LOGIN_SUCCESS, user_email=request.email,
                  ip_address=http_request.client.host if http_request and http_request.client else "")

        return {"success": True, "user": user_profile.to_dict(), "message": "MFA setup complete and logged in"}

    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg = e.response["Error"].get("Message", "")
        logger.error(f"MFA setup challenge verify error: {code} - {msg}")
        audit = get_audit_service()
        audit.log(AuditEvent.MFA_FAILED, user_email=request.email, success=False,
                  details={"error": code, "message": msg, "flow": "setup_challenge"})
        if code in ("CodeMismatchException", "EnableSoftwareTokenMFAException"):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
        if code == "NotAuthorizedException":
            raise HTTPException(status_code=401, detail="Session expired. Please login again.")
        raise HTTPException(status_code=500, detail="MFA setup verification failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA setup challenge verify unexpected error: {e}")
        raise HTTPException(status_code=500, detail="MFA setup verification failed")


@router.post("/mfa/setup/verify")
async def mfa_setup_verify(
    request: MFASetupVerifyRequest,
    cognito: CognitoOAuthService = Depends(get_cognito_service),
):
    """Verify first TOTP code to complete MFA setup (Settings page, already authenticated)."""
    try:
        config = await cognito.load_config()
        cognito_client = boto3.client("cognito-idp", region_name=config.region)

        resp = cognito_client.verify_software_token(
            AccessToken=request.access_token,
            UserCode=request.totp_code,
            FriendlyDeviceName="CallSense-TOTP",
        )

        if resp.get("Status") == "SUCCESS":
            cognito_client.set_user_mfa_preference(
                SoftwareTokenMfaSettings={"Enabled": True, "PreferredMfa": True},
                AccessToken=request.access_token,
            )
            audit = get_audit_service()
            audit.log(AuditEvent.MFA_SETUP, user_email="", details={"action": "completed", "mode": "settings"})
            return {"success": True, "message": "MFA setup complete. TOTP is now required for login."}

        raise HTTPException(status_code=400, detail="TOTP verification failed")

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "EnableSoftwareTokenMFAException":
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
        raise HTTPException(status_code=500, detail="MFA setup verification failed")
