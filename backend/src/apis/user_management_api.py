"""
User Management API

Admin-only endpoints for managing Cognito users: list, create, assign groups, disable.
All actions are audit-logged.
"""

import os
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from loguru import logger
import boto3
from botocore.exceptions import ClientError

from .session_middleware import get_session_from_cookie, has_permission
from ..services.audit_service import get_audit_service, AuditEvent
from ..services.session_service import get_session_service

router = APIRouter()

VALID_GROUPS = {"Admin", "Executive", "SalesManager", "Rep"}


def _get_cognito_client():
    region = os.getenv("AWS_REGION", "us-east-1")
    return boto3.client("cognito-idp", region_name=region)


def _get_pool_id() -> str:
    return os.getenv("COGNITO_USER_POOL_ID", "us-east-1_xMoHpgY8g")


def _require_admin(session: Optional[Dict[str, Any]]):
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = session.get("user", session)
    role = user.get("role", "")
    if role != "Admin" and not has_permission(session, "manage_users"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class CreateUserRequest(BaseModel):
    email: str
    temporary_password: str = Field(..., min_length=8)
    group: str = "Rep"


class UpdateGroupsRequest(BaseModel):
    add_groups: List[str] = []
    remove_groups: List[str] = []


@router.get("/")
async def list_users(
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """List all Cognito users with their groups and MFA status."""
    admin = _require_admin(session)
    try:
        client = _get_cognito_client()
        pool_id = _get_pool_id()

        resp = client.list_users(UserPoolId=pool_id, Limit=60)
        users = []

        for u in resp.get("Users", []):
            attrs = {a["Name"]: a["Value"] for a in u.get("Attributes", [])}

            try:
                groups_resp = client.admin_list_groups_for_user(
                    Username=u["Username"], UserPoolId=pool_id
                )
                groups = [g["GroupName"] for g in groups_resp.get("Groups", [])]
            except Exception:
                groups = []

            mfa_enabled = False
            try:
                mfa_resp = client.admin_get_user(
                    Username=u["Username"], UserPoolId=pool_id
                )
                for mfa in mfa_resp.get("UserMFASettingList", []):
                    if "SOFTWARE_TOKEN" in mfa:
                        mfa_enabled = True
            except Exception:
                pass

            users.append({
                "sub": attrs.get("sub", u["Username"]),
                "email": attrs.get("email", ""),
                "status": u.get("UserStatus", "UNKNOWN"),
                "enabled": u.get("Enabled", False),
                "groups": groups,
                "role": groups[0] if groups else "User",
                "mfa_enabled": mfa_enabled,
                "created": u.get("UserCreateDate", "").isoformat() if u.get("UserCreateDate") else "",
                "last_modified": u.get("UserLastModifiedDate", "").isoformat() if u.get("UserLastModifiedDate") else "",
            })

        return {"success": True, "users": users, "total": len(users)}

    except Exception as e:
        logger.error(f"List users failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.post("/")
async def create_user(
    request: CreateUserRequest,
    http_request: Request = None,
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """Create a new Cognito user with temporary password and assign to group."""
    admin = _require_admin(session)

    if request.group not in VALID_GROUPS:
        raise HTTPException(status_code=400, detail=f"Invalid group. Must be one of: {VALID_GROUPS}")

    try:
        client = _get_cognito_client()
        pool_id = _get_pool_id()

        resp = client.admin_create_user(
            UserPoolId=pool_id,
            Username=request.email,
            UserAttributes=[
                {"Name": "email", "Value": request.email},
                {"Name": "email_verified", "Value": "true"},
            ],
            TemporaryPassword=request.temporary_password,
            MessageAction="SUPPRESS",
        )

        client.admin_add_user_to_group(
            UserPoolId=pool_id,
            Username=request.email,
            GroupName=request.group,
        )

        audit = get_audit_service()
        audit.log(
            AuditEvent.USER_CREATED,
            user_email=admin.get("email", ""),
            details={"created_user": request.email, "group": request.group},
            ip_address=http_request.client.host if http_request and http_request.client else "",
        )

        logger.info(f"User created: {request.email} in group {request.group}")
        return {"success": True, "message": f"User {request.email} created in group {request.group}"}

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UsernameExistsException":
            raise HTTPException(status_code=409, detail="User already exists")
        logger.error(f"Create user failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.patch("/{user_sub}/groups")
async def update_user_groups(
    user_sub: str,
    request: UpdateGroupsRequest,
    http_request: Request = None,
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """Add or remove Cognito group assignments for a user."""
    admin = _require_admin(session)

    invalid = (set(request.add_groups) | set(request.remove_groups)) - VALID_GROUPS
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid groups: {invalid}")

    try:
        client = _get_cognito_client()
        pool_id = _get_pool_id()

        # Find username by sub
        username = user_sub
        try:
            resp = client.list_users(
                UserPoolId=pool_id,
                Filter=f'sub = "{user_sub}"',
                Limit=1,
            )
            if resp.get("Users"):
                username = resp["Users"][0]["Username"]
        except Exception:
            pass

        for grp in request.remove_groups:
            try:
                client.admin_remove_user_from_group(
                    UserPoolId=pool_id, Username=username, GroupName=grp
                )
            except Exception as e:
                logger.warning(f"Remove from group {grp} failed: {e}")

        for grp in request.add_groups:
            try:
                client.admin_add_user_to_group(
                    UserPoolId=pool_id, Username=username, GroupName=grp
                )
            except Exception as e:
                logger.warning(f"Add to group {grp} failed: {e}")

        audit = get_audit_service()
        audit.log(
            AuditEvent.ROLE_CHANGED,
            user_email=admin.get("email", ""),
            details={"target_user": user_sub, "added": request.add_groups, "removed": request.remove_groups},
            ip_address=http_request.client.host if http_request and http_request.client else "",
        )

        return {"success": True, "message": "Groups updated"}

    except Exception as e:
        logger.error(f"Update groups failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update groups")


@router.delete("/{user_sub}")
async def disable_user(
    user_sub: str,
    http_request: Request = None,
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """Disable a Cognito user."""
    admin = _require_admin(session)

    try:
        client = _get_cognito_client()
        pool_id = _get_pool_id()

        username = user_sub
        try:
            resp = client.list_users(
                UserPoolId=pool_id, Filter=f'sub = "{user_sub}"', Limit=1
            )
            if resp.get("Users"):
                username = resp["Users"][0]["Username"]
        except Exception:
            pass

        client.admin_disable_user(UserPoolId=pool_id, Username=username)

        try:
            client.admin_user_global_sign_out(UserPoolId=pool_id, Username=username)
        except Exception:
            pass

        session_svc = get_session_service()
        session_svc.delete_user_sessions(user_sub)

        audit = get_audit_service()
        audit.log(
            AuditEvent.USER_DISABLED,
            user_email=admin.get("email", ""),
            details={"disabled_user": user_sub},
            ip_address=http_request.client.host if http_request and http_request.client else "",
        )

        return {"success": True, "message": "User disabled, sessions invalidated"}

    except Exception as e:
        logger.error(f"Disable user failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable user")


@router.delete("/{user_sub}/permanent")
async def delete_user(
    user_sub: str,
    http_request: Request = None,
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """Permanently delete a Cognito user."""
    admin = _require_admin(session)

    try:
        client = _get_cognito_client()
        pool_id = _get_pool_id()

        username = user_sub
        user_email = user_sub
        try:
            resp = client.list_users(
                UserPoolId=pool_id, Filter=f'sub = "{user_sub}"', Limit=1
            )
            if resp.get("Users"):
                username = resp["Users"][0]["Username"]
                for attr in resp["Users"][0].get("Attributes", []):
                    if attr["Name"] == "email":
                        user_email = attr["Value"]
                        break
                user_groups = client.admin_list_groups_for_user(
                    UserPoolId=pool_id, Username=username
                ).get("Groups", [])
                if any(g["GroupName"] == "Admin" for g in user_groups):
                    raise HTTPException(status_code=400, detail="Cannot delete Admin users")
        except HTTPException:
            raise
        except Exception:
            pass

        client.admin_delete_user(UserPoolId=pool_id, Username=username)

        audit = get_audit_service()
        audit.log(
            AuditEvent.USER_DISABLED,
            user_email=admin.get("email", ""),
            details={"deleted_user": user_email},
            ip_address=http_request.client.host if http_request and http_request.client else "",
        )

        return {"success": True, "message": f"User {user_email} permanently deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")


class ResetPasswordRequest(BaseModel):
    temporary_password: str = Field(..., min_length=8)


@router.post("/{user_sub}/reset-password")
async def reset_password(
    user_sub: str,
    request: ResetPasswordRequest,
    http_request: Request = None,
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie),
) -> Dict[str, Any]:
    """Set a temporary password and force password change on next login."""
    admin = _require_admin(session)

    try:
        client = _get_cognito_client()
        pool_id = _get_pool_id()

        username = user_sub
        try:
            resp = client.list_users(
                UserPoolId=pool_id, Filter=f'sub = "{user_sub}"', Limit=1
            )
            if resp.get("Users"):
                username = resp["Users"][0]["Username"]
        except Exception:
            pass

        client.admin_set_user_password(
            UserPoolId=pool_id,
            Username=username,
            Password=request.temporary_password,
            Permanent=False
        )

        try:
            client.admin_user_global_sign_out(UserPoolId=pool_id, Username=username)
        except Exception:
            pass

        session_svc = get_session_service()
        session_svc.delete_user_sessions(user_sub)

        audit = get_audit_service()
        audit.log(
            AuditEvent.PASSWORD_RESET,
            user_email=admin.get("email", ""),
            details={"target_user": user_sub},
            ip_address=http_request.client.host if http_request and http_request.client else "",
        )

        return {"success": True, "message": "Temporary password set. User must change password on next login."}

    except Exception as e:
        logger.error(f"Reset password failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset password")
