"""
License REST API

FastAPI router for license management endpoints.
Provides REST API access to all license operations.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Query
from loguru import logger

from ..models.api_models import (
    LicenseActivationRequest,
    LicenseActivationResponse,
    LicenseDeactivationRequest,
    LicenseDeactivationResponse,
    LicenseRenewalRequest,
    LicenseRenewalResponse,
    LicenseStatusResponse,
    LicenseAuditLogsResponse,
    FeatureAccessResponse,
    LicenseErrorResponse,
)
from ..services.license_service import LicenseService, LicenseServiceError
from ..services.audit_service import AuditService
from ..consts import LicenseErrorCode


# Create router with prefix
router = APIRouter(prefix="/api/v1/license", tags=["license"])

# Service instances (to be initialized)
_license_service: Optional[LicenseService] = None
_audit_service: Optional[AuditService] = None


def init_services(
    license_service: LicenseService,
    audit_service: Optional[AuditService] = None,
) -> None:
    """Initialize API services."""
    global _license_service, _audit_service
    _license_service = license_service
    _audit_service = audit_service or AuditService()


def get_license_service() -> LicenseService:
    """Get the license service instance."""
    if _license_service is None:
        raise HTTPException(
            status_code=500,
            detail="License service not initialized",
        )
    return _license_service


def get_audit_service() -> AuditService:
    """Get the audit service instance."""
    if _audit_service is None:
        raise HTTPException(
            status_code=500,
            detail="Audit service not initialized",
        )
    return _audit_service


@router.post("/activate", response_model=LicenseActivationResponse)
async def activate_license(
    request: LicenseActivationRequest,
    http_request: Request,
) -> LicenseActivationResponse:
    """
    Activate a license key.
    
    Validates the license key and activates it for this instance.
    Returns activation details including tier, expiration, and features.
    """
    service = get_license_service()
    
    # Extract metadata from request
    metadata = request.metadata or {}
    metadata["ip_address"] = http_request.client.host if http_request.client else None
    metadata["user_agent"] = http_request.headers.get("user-agent")
    
    if request.instance_id:
        metadata["instance_id"] = request.instance_id
    
    result = await service.activate_license(
        license_key=request.license_key,
        activation_metadata=metadata,
    )
    
    if result.status == "error":
        raise HTTPException(
            status_code=400 if result.error_code in [
                LicenseErrorCode.INVALID_FORMAT,
                LicenseErrorCode.SIGNATURE_INVALID,
            ] else 403,
            detail={
                "message": result.message,
                "error_code": result.error_code,
                "details": result.details,
            },
        )
    
    return result


@router.get("/status", response_model=LicenseStatusResponse)
async def get_license_status() -> LicenseStatusResponse:
    """
    Get current license status.
    
    Returns detailed information about the current license including
    status, tier, expiration, features, and grace period info.
    """
    service = get_license_service()
    return await service.get_license_status()


@router.post("/deactivate", response_model=LicenseDeactivationResponse)
async def deactivate_license(
    request: LicenseDeactivationRequest,
) -> LicenseDeactivationResponse:
    """
    Deactivate the current license.
    
    Marks the license as deactivated and clears cached data.
    The license can be reactivated on another instance.
    """
    service = get_license_service()
    
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Deactivation must be confirmed",
                "error_code": "CONFIRMATION_REQUIRED",
            },
        )
    
    result = await service.deactivate_license(reason=request.reason)
    
    if result.status == "error":
        raise HTTPException(
            status_code=403 if result.error_code == LicenseErrorCode.NOT_ACTIVATED else 500,
            detail={
                "message": result.message,
                "error_code": result.error_code,
            },
        )
    
    return result


@router.post("/renew", response_model=LicenseRenewalResponse)
async def renew_license(
    request: LicenseRenewalRequest,
) -> LicenseRenewalResponse:
    """
    Renew the current license.
    
    Updates the license expiration and optionally the tier.
    The renewal key must match the current license holder.
    """
    service = get_license_service()
    
    result = await service.renew_license(renewal_key=request.renewal_key)
    
    if result.status == "error":
        status_code = 400
        if result.error_code == LicenseErrorCode.NOT_ACTIVATED:
            status_code = 403
        elif result.error_code == LicenseErrorCode.RENEWAL_INVALID:
            status_code = 400
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": result.message,
                "error_code": result.error_code,
            },
        )
    
    return result


@router.get("/audit")
async def get_audit_logs(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    Get license audit logs.
    
    Returns paginated audit entries with optional date filtering.
    """
    service = get_license_service()
    
    logs = await service.get_audit_logs(
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    
    return {
        "status": "success",
        "data": logs,
    }


@router.get("/features/{feature_id}", response_model=FeatureAccessResponse)
async def check_feature_access(feature_id: str) -> FeatureAccessResponse:
    """
    Check if a feature is accessible with the current license.
    
    Returns whether the feature is allowed and the required tier.
    """
    service = get_license_service()
    
    result = await service.check_feature_access(feature_id)
    
    return FeatureAccessResponse(
        status="success",
        data=result,
    )


@router.get("/validate")
async def validate_license():
    """
    Validate the current license.
    
    Returns the validation result including status and any restrictions.
    """
    service = get_license_service()
    
    result = await service.validate_license()
    
    return {
        "status": "success",
        "data": {
            "is_valid": result.is_valid,
            "license_status": result.status.value,
            "license_id": result.license_id,
            "tier": result.tier.value if result.tier else None,
            "message": result.message,
            "is_in_grace_period": result.is_in_grace_period,
            "can_write": result.can_write,
        },
    }
