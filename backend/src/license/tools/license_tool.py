"""
License MCP Tool

MCP tool for license management operations.
Provides AI assistant access to all license functionality.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from ..services.license_service import LicenseService
from ..services.audit_service import AuditService
from ..consts import LicenseErrorCode


class LicenseTool:
    """
    MCP tool for license management.
    
    Provides actions:
    - activate: Activate a license key
    - status: Get license status
    - deactivate: Deactivate license
    - renew: Renew license
    - check_feature: Check feature access
    - audit_logs: Get audit logs
    - validate: Validate current license
    """
    
    def __init__(
        self,
        license_service: Optional[LicenseService] = None,
        audit_service: Optional[AuditService] = None,
    ):
        """
        Initialize license tool.
        
        Args:
            license_service: License service instance
            audit_service: Audit service instance
        """
        self._license_service = license_service
        self._audit_service = audit_service
    
    def set_services(
        self,
        license_service: LicenseService,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        """Set service instances."""
        self._license_service = license_service
        self._audit_service = audit_service
    
    async def execute(
        self,
        action: str,
        license_key: Optional[str] = None,
        renewal_key: Optional[str] = None,
        reason: Optional[str] = None,
        feature_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Execute a license tool action.
        
        Args:
            action: Action to perform
            license_key: License key for activation
            renewal_key: Renewal key for renewal
            reason: Reason for deactivation
            feature_id: Feature ID for access check
            start_date: Start date for audit logs
            end_date: End date for audit logs
            limit: Limit for audit logs
            offset: Offset for audit logs
            
        Returns:
            Action result as dict
        """
        if not self._license_service:
            return {
                "status": "error",
                "message": "License service not initialized",
                "error_code": "SERVICE_NOT_INITIALIZED",
            }
        
        try:
            if action == "activate":
                return await self._activate(license_key)
            elif action == "status":
                return await self._status()
            elif action == "deactivate":
                return await self._deactivate(reason)
            elif action == "renew":
                return await self._renew(renewal_key)
            elif action == "check_feature":
                return await self._check_feature(feature_id)
            elif action == "audit_logs":
                return await self._audit_logs(start_date, end_date, limit, offset)
            elif action == "validate":
                return await self._validate()
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "error_code": "UNKNOWN_ACTION",
                    "available_actions": [
                        "activate", "status", "deactivate", "renew",
                        "check_feature", "audit_logs", "validate"
                    ],
                }
        except Exception as e:
            logger.exception(f"License tool error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "error_code": "INTERNAL_ERROR",
            }
    
    async def _activate(self, license_key: Optional[str]) -> Dict[str, Any]:
        """Activate a license key."""
        if not license_key:
            return {
                "status": "error",
                "message": "license_key is required for activation",
                "error_code": "MISSING_PARAMETER",
            }
        
        result = await self._license_service.activate_license(license_key)
        
        if result.status == "success":
            return {
                "status": "success",
                "message": result.message,
                "license_id": result.data.license_id,
                "tier": result.data.tier.value,
                "holder_name": result.data.holder_name,
                "expires_at": result.data.expires_at.isoformat(),
                "days_remaining": result.data.days_remaining,
                "features": result.data.features,
            }
        else:
            return {
                "status": "error",
                "message": result.message,
                "error_code": result.error_code,
            }
    
    async def _status(self) -> Dict[str, Any]:
        """Get license status."""
        result = await self._license_service.get_license_status()
        data = result.data
        
        response = {
            "status": "success",
            "license_status": data.license_status.value,
        }
        
        if data.license_id:
            response.update({
                "license_id": data.license_id,
                "tier": data.tier.value if data.tier else None,
                "holder_name": data.holder_name,
                "expires_at": data.expires_at.isoformat() if data.expires_at else None,
                "days_remaining": data.days_remaining,
                "is_expiring_soon": data.is_expiring_soon,
                "features": data.features,
            })
            
            if data.expiration_warning:
                response["expiration_warning"] = data.expiration_warning
            
            if data.grace_period:
                response["grace_period"] = {
                    "is_in_grace_period": data.grace_period.is_in_grace_period,
                    "ends_at": data.grace_period.grace_period_ends_at.isoformat() if data.grace_period.grace_period_ends_at else None,
                    "days_remaining": data.grace_period.days_remaining,
                    "restrictions": data.grace_period.restrictions,
                }
        else:
            response["message"] = data.message
            if data.activation_instructions:
                response["activation_instructions"] = data.activation_instructions
        
        return response
    
    async def _deactivate(self, reason: Optional[str]) -> Dict[str, Any]:
        """Deactivate the license."""
        if not reason:
            return {
                "status": "error",
                "message": "reason is required for deactivation",
                "error_code": "MISSING_PARAMETER",
            }
        
        result = await self._license_service.deactivate_license(reason)
        
        if result.status == "success":
            return {
                "status": "success",
                "message": result.message,
                "deactivated_at": result.data.deactivated_at.isoformat(),
                "previous_license_id": result.data.previous_license_id,
                "can_reactivate": result.data.can_reactivate,
            }
        else:
            return {
                "status": "error",
                "message": result.message,
                "error_code": result.error_code,
            }
    
    async def _renew(self, renewal_key: Optional[str]) -> Dict[str, Any]:
        """Renew the license."""
        if not renewal_key:
            return {
                "status": "error",
                "message": "renewal_key is required for renewal",
                "error_code": "MISSING_PARAMETER",
            }
        
        result = await self._license_service.renew_license(renewal_key)
        
        if result.status == "success":
            return {
                "status": "success",
                "message": result.message,
                "license_id": result.data.license_id,
                "previous_expiration": result.data.previous_expiration.isoformat(),
                "new_expiration": result.data.new_expiration.isoformat(),
                "tier": result.data.tier.value,
                "tier_changed": result.data.tier_changed,
                "features": result.data.features,
            }
        else:
            return {
                "status": "error",
                "message": result.message,
                "error_code": result.error_code,
            }
    
    async def _check_feature(self, feature_id: Optional[str]) -> Dict[str, Any]:
        """Check feature access."""
        if not feature_id:
            return {
                "status": "error",
                "message": "feature_id is required",
                "error_code": "MISSING_PARAMETER",
            }
        
        result = await self._license_service.check_feature_access(feature_id)
        
        return {
            "status": "success",
            "feature_id": result.feature_id,
            "is_allowed": result.is_allowed,
            "required_tier": result.required_tier.value,
            "current_tier": result.current_tier.value if result.current_tier else None,
            "upgrade_message": result.upgrade_message,
        }
    
    async def _audit_logs(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        limit: int,
        offset: int,
    ) -> Dict[str, Any]:
        """Get audit logs."""
        start = None
        end = None
        
        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return {
                    "status": "error",
                    "message": "Invalid start_date format",
                    "error_code": "INVALID_DATE_FORMAT",
                }
        
        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return {
                    "status": "error",
                    "message": "Invalid end_date format",
                    "error_code": "INVALID_DATE_FORMAT",
                }
        
        logs = await self._license_service.get_audit_logs(
            start_date=start,
            end_date=end,
            limit=limit,
            offset=offset,
        )
        
        return {
            "status": "success",
            **logs,
        }
    
    async def _validate(self) -> Dict[str, Any]:
        """Validate current license."""
        result = await self._license_service.validate_license()
        
        return {
            "status": "success",
            "is_valid": result.is_valid,
            "license_status": result.status.value,
            "license_id": result.license_id,
            "tier": result.tier.value if result.tier else None,
            "message": result.message,
            "is_in_grace_period": result.is_in_grace_period,
            "can_write": result.can_write,
            "error_code": result.error_code,
        }


# Tool function for MCP registration
async def license_tool(
    action: str,
    license_key: Optional[str] = None,
    renewal_key: Optional[str] = None,
    reason: Optional[str] = None,
    feature_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    License management tool for AI Job Engine.
    
    Actions:
    - activate: Activate a license key (requires license_key)
    - status: Get current license status
    - deactivate: Deactivate current license (requires reason)
    - renew: Renew license with new key (requires renewal_key)
    - check_feature: Check if feature is accessible (requires feature_id)
    - audit_logs: Get license audit logs (optional: start_date, end_date, limit, offset)
    - validate: Validate current license
    
    Args:
        action: Action to perform
        license_key: License key for activation
        renewal_key: Renewal key for renewal
        reason: Reason for deactivation
        feature_id: Feature ID for access check
        start_date: Start date for audit logs (ISO format)
        end_date: End date for audit logs (ISO format)
        limit: Maximum results for audit logs
        offset: Pagination offset for audit logs
    
    Returns:
        Action result
    """
    tool = get_license_tool()
    return await tool.execute(
        action=action,
        license_key=license_key,
        renewal_key=renewal_key,
        reason=reason,
        feature_id=feature_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


# Singleton instance
_license_tool: Optional[LicenseTool] = None


def get_license_tool() -> LicenseTool:
    """Get or create the global license tool instance."""
    global _license_tool
    if _license_tool is None:
        _license_tool = LicenseTool()
    return _license_tool


def init_license_tool(
    license_service: LicenseService,
    audit_service: Optional[AuditService] = None,
) -> LicenseTool:
    """Initialize the license tool with services."""
    tool = get_license_tool()
    tool.set_services(license_service, audit_service)
    return tool


def reset_license_tool() -> None:
    """Reset the global license tool (for testing)."""
    global _license_tool
    _license_tool = None
