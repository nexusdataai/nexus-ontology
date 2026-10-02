"""
License API Models

Request and response models for license management REST API and MCP tools.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field

from .enums import LicenseTier, LicenseStatus


# ==========================================
# Request Models
# ==========================================

class LicenseActivationRequest(BaseModel):
    """Request model for license activation."""
    license_key: str = Field(..., description="License key to activate")
    instance_id: Optional[str] = Field(None, description="Optional instance identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class LicenseDeactivationRequest(BaseModel):
    """Request model for license deactivation."""
    reason: str = Field(..., description="Reason for deactivation")
    confirm: bool = Field(True, description="Confirmation flag")


class LicenseRenewalRequest(BaseModel):
    """Request model for license renewal."""
    renewal_key: str = Field(..., description="Renewal license key")


class LicenseAuditLogsRequest(BaseModel):
    """Request model for audit logs retrieval."""
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(0, ge=0, description="Pagination offset")


# ==========================================
# Response Data Models
# ==========================================

class LicenseActivationData(BaseModel):
    """Data returned on successful activation."""
    license_id: str = Field(..., description="Unique license identifier")
    tier: LicenseTier = Field(..., description="License tier")
    holder_name: str = Field(..., description="License holder name")
    holder_id: str = Field(..., description="License holder ID")
    activated_at: datetime = Field(..., description="Activation timestamp")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    days_remaining: int = Field(..., description="Days until expiration")
    features: List[str] = Field(..., description="Enabled features")
    is_active: bool = Field(True, description="Whether license is active")


class GracePeriodInfo(BaseModel):
    """Grace period information."""
    is_in_grace_period: bool = Field(..., description="Whether in grace period")
    grace_period_ends_at: Optional[datetime] = Field(None, description="Grace period end")
    days_remaining: Optional[int] = Field(None, description="Days remaining in grace")
    restrictions: List[str] = Field(default_factory=list, description="Active restrictions")


class LicenseStatusData(BaseModel):
    """License status data."""
    license_status: LicenseStatus = Field(..., description="Current status")
    license_id: Optional[str] = Field(None, description="License ID if activated")
    tier: Optional[LicenseTier] = Field(None, description="License tier")
    holder_name: Optional[str] = Field(None, description="Holder name")
    activated_at: Optional[datetime] = Field(None, description="Activation time")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    days_remaining: Optional[int] = Field(None, description="Days until expiration")
    is_expiring_soon: bool = Field(False, description="Expiring within 30 days")
    expiration_warning: Optional[str] = Field(None, description="Warning message")
    features: List[str] = Field(default_factory=list, description="Enabled features")
    grace_period: Optional[GracePeriodInfo] = Field(None, description="Grace period info")
    usage_stats: Optional[Dict[str, int]] = Field(None, description="Usage statistics")
    message: Optional[str] = Field(None, description="Status message")
    activation_instructions: Optional[str] = Field(None, description="How to activate")


class LicenseDeactivationData(BaseModel):
    """Data returned on successful deactivation."""
    deactivated_at: datetime = Field(..., description="Deactivation timestamp")
    previous_license_id: str = Field(..., description="Deactivated license ID")
    can_reactivate: bool = Field(True, description="Whether can reactivate")


class LicenseRenewalData(BaseModel):
    """Data returned on successful renewal."""
    license_id: str = Field(..., description="License ID")
    previous_expiration: datetime = Field(..., description="Previous expiration")
    new_expiration: datetime = Field(..., description="New expiration")
    tier: LicenseTier = Field(..., description="Current tier")
    tier_changed: bool = Field(False, description="Whether tier changed")
    features: List[str] = Field(..., description="Enabled features")


class AuditLogEntry(BaseModel):
    """Single audit log entry for API response."""
    event_id: str = Field(..., description="Event identifier")
    timestamp: datetime = Field(..., description="Event timestamp")
    event_type: str = Field(..., description="Type of event")
    license_id: Optional[str] = Field(None, description="Associated license")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")
    ip_address: Optional[str] = Field(None, description="Client IP")
    user_agent: Optional[str] = Field(None, description="Client user agent")


class FeatureAccessData(BaseModel):
    """Feature access check result."""
    feature_id: str = Field(..., description="Feature identifier")
    is_allowed: bool = Field(..., description="Whether access is allowed")
    required_tier: LicenseTier = Field(..., description="Required tier")
    current_tier: Optional[LicenseTier] = Field(None, description="Current tier")
    upgrade_message: Optional[str] = Field(None, description="Upgrade suggestion")


# ==========================================
# Response Models
# ==========================================

class LicenseActivationResponse(BaseModel):
    """Response for license activation."""
    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(..., description="Response message")
    data: Optional[LicenseActivationData] = Field(None, description="Activation data")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class LicenseStatusResponse(BaseModel):
    """Response for license status query."""
    status: Literal["success", "error"] = Field(..., description="Operation status")
    data: LicenseStatusData = Field(..., description="Status data")


class LicenseDeactivationResponse(BaseModel):
    """Response for license deactivation."""
    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(..., description="Response message")
    data: Optional[LicenseDeactivationData] = Field(None, description="Deactivation data")
    error_code: Optional[str] = Field(None, description="Error code if failed")


class LicenseRenewalResponse(BaseModel):
    """Response for license renewal."""
    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(..., description="Response message")
    data: Optional[LicenseRenewalData] = Field(None, description="Renewal data")
    error_code: Optional[str] = Field(None, description="Error code if failed")


class LicenseAuditLogsResponse(BaseModel):
    """Response for audit logs retrieval."""
    status: Literal["success", "error"] = Field(..., description="Operation status")
    data: Optional[Dict[str, Any]] = Field(None, description="Audit logs data")
    
    class AuditLogsData(BaseModel):
        """Nested audit logs data."""
        total_count: int = Field(..., description="Total entries count")
        page_size: int = Field(..., description="Page size")
        offset: int = Field(..., description="Current offset")
        entries: List[AuditLogEntry] = Field(..., description="Log entries")


class FeatureAccessResponse(BaseModel):
    """Response for feature access check."""
    status: Literal["success", "error"] = Field(..., description="Operation status")
    data: FeatureAccessData = Field(..., description="Access check result")


class LicenseValidationResult(BaseModel):
    """Result of license validation."""
    is_valid: bool = Field(..., description="Whether license is valid")
    status: LicenseStatus = Field(..., description="License status")
    license_id: Optional[str] = Field(None, description="License ID")
    tier: Optional[LicenseTier] = Field(None, description="License tier")
    error_code: Optional[str] = Field(None, description="Error code if invalid")
    message: Optional[str] = Field(None, description="Validation message")
    is_in_grace_period: bool = Field(False, description="In grace period")
    can_write: bool = Field(True, description="Can perform write operations")


class LicenseErrorResponse(BaseModel):
    """Standard error response for license operations."""
    status: Literal["error"] = "error"
    message: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
