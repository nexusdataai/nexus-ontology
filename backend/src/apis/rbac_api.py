"""
RBAC API

REST API endpoints for managing Role-Based Access Control configuration.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from ..services.rbac_service import get_rbac_service, RBACService
from ..models.rbac_model import (
    RBACConfig,
    RBACRole,
    RBACPermission,
    RBACCategory,
    RBACAuditEntry,
    UpdateRolePermissionsRequest,
    RBACConfigResponse,
    RolesListResponse,
    PermissionsListResponse,
    AuditLogResponse
)

# Import auth dependencies
try:
    from .session_middleware import (
        get_session_from_cookie,
        require_admin,
        require_executive
    )
    AUTH_AVAILABLE = True
except ImportError:
    logger.warning("Session middleware not available for RBAC API")
    AUTH_AVAILABLE = False


# Create router
router = APIRouter(prefix="/api/v1/rbac", tags=["RBAC Management"])


@router.get("/config", response_model=RBACConfigResponse)
async def get_rbac_config(
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Get full RBAC configuration.
    
    Returns roles, permissions, categories, and role-permission mappings.
    Available to authenticated users.
    """
    try:
        config = await rbac_service.get_config()
        
        return RBACConfigResponse(
            status="success",
            data=config,
            message="RBAC configuration retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting RBAC config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get RBAC configuration: {str(e)}")


@router.get("/roles", response_model=RolesListResponse)
async def list_roles(
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    List all roles.
    
    Returns role definitions with display names and hierarchy levels.
    """
    try:
        roles = await rbac_service.get_roles()
        
        return RolesListResponse(
            status="success",
            data=roles,
            count=len(roles)
        )
        
    except Exception as e:
        logger.error(f"Error listing roles: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list roles: {str(e)}")


@router.get("/roles/{role_id}")
async def get_role(
    role_id: str,
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Get a specific role by ID.
    """
    try:
        role = await rbac_service.get_role(role_id)
        
        if not role:
            raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found")
        
        return {
            "status": "success",
            "data": role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting role {role_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get role: {str(e)}")


@router.get("/permissions", response_model=PermissionsListResponse)
async def list_permissions(
    category: Optional[str] = None,
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    List all permissions.
    
    Optionally filter by category.
    """
    try:
        permissions = await rbac_service.get_permissions()
        
        # Filter by category if specified
        if category:
            permissions = [p for p in permissions if p.category == category]
        
        return PermissionsListResponse(
            status="success",
            data=permissions,
            count=len(permissions)
        )
        
    except Exception as e:
        logger.error(f"Error listing permissions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list permissions: {str(e)}")


@router.get("/permissions/{permission_id}")
async def get_permission(
    permission_id: str,
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Get a specific permission by ID.
    """
    try:
        permission = await rbac_service.get_permission(permission_id)
        
        if not permission:
            raise HTTPException(status_code=404, detail=f"Permission '{permission_id}' not found")
        
        return {
            "status": "success",
            "data": permission
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting permission {permission_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get permission: {str(e)}")


@router.get("/categories")
async def list_categories(
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    List all permission categories.
    """
    try:
        categories = await rbac_service.get_categories()
        
        return {
            "status": "success",
            "data": categories,
            "count": len(categories)
        }
        
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list categories: {str(e)}")


@router.get("/roles/{role_id}/permissions")
async def get_role_permissions(
    role_id: str,
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Get permissions assigned to a specific role.
    """
    try:
        # Verify role exists
        role = await rbac_service.get_role(role_id)
        if not role:
            raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found")
        
        permissions = await rbac_service.get_role_permissions(role_id)
        
        return {
            "status": "success",
            "data": {
                "roleId": role_id,
                "roleName": role.displayName,
                "permissions": permissions,
                "count": len(permissions)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting permissions for role {role_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get role permissions: {str(e)}")


@router.put("/roles/{role_id}/permissions")
async def update_role_permissions(
    role_id: str,
    request: UpdateRolePermissionsRequest,
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie) if AUTH_AVAILABLE else None,
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Update permissions for a role.
    
    Requires Admin role.
    """
    # Check authorization
    if AUTH_AVAILABLE and session:
        user_data = session.get('user', {})
        user_role = user_data.get('role', session.get('role', 'Rep'))
        if user_role not in ['Admin']:
            raise HTTPException(
                status_code=403, 
                detail="Only Admins can modify RBAC permissions"
            )
        updated_by = user_data.get('email', session.get('email', 'unknown'))
    else:
        updated_by = 'system'
    
    try:
        result = await rbac_service.update_role_permissions(
            role_id=role_id,
            permissions=request.permissions,
            updated_by=updated_by
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])
        
        return {
            "status": "success",
            "message": result['message'],
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating permissions for role {role_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update role permissions: {str(e)}")


@router.get("/audit", response_model=AuditLogResponse)
async def get_audit_log(
    limit: int = 50,
    session: Optional[Dict[str, Any]] = Depends(get_session_from_cookie) if AUTH_AVAILABLE else None,
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Get RBAC audit log.
    
    Returns recent changes to RBAC configuration.
    Requires Admin or Executive role.
    """
    # Check authorization
    if AUTH_AVAILABLE and session:
        user_data = session.get('user', {})
        user_role = user_data.get('role', session.get('role', 'Rep'))
        if user_role not in ['Admin', 'Executive']:
            raise HTTPException(
                status_code=403,
                detail="Only Admins and Executives can view RBAC audit log"
            )
    
    try:
        audit_entries = await rbac_service.get_audit_log(limit=limit)
        
        return AuditLogResponse(
            status="success",
            data=audit_entries,
            count=len(audit_entries)
        )
        
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit log: {str(e)}")


@router.post("/check")
async def check_permission(
    role: str,
    permission: str,
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Check if a role has a specific permission.
    
    Utility endpoint for permission checking.
    """
    try:
        has_perm = rbac_service.has_permission(role, permission)
        
        return {
            "status": "success",
            "data": {
                "role": role,
                "permission": permission,
                "hasPermission": has_perm
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check permission: {str(e)}")


@router.get("/user/{role}/permissions")
async def get_user_permissions_by_role(
    role: str,
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Get all permissions for a user role.
    
    Returns the list of permission IDs that a role has.
    """
    try:
        permissions = rbac_service.get_user_permissions(role)
        
        return {
            "status": "success",
            "data": {
                "role": role,
                "permissions": permissions,
                "count": len(permissions)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user permissions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user permissions: {str(e)}")
