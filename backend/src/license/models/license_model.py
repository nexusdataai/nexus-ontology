"""
License Data Models

Defines Pydantic models for license records, audit entries, and feature mappings.
These models are used for DynamoDB persistence and data validation.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
import hashlib
import uuid

from .enums import LicenseTier, LicenseStatus, LicenseEventType


class LicenseRecord(BaseModel):
    """License record stored in DynamoDB."""
    
    # Primary Key
    PK: str = Field(..., description="INSTANCE#<instance_id>")
    SK: str = Field(..., description="LICENSE#<license_id>")
    
    # Entity metadata
    EntityType: Literal["License"] = "License"
    
    # License data
    license_id: str = Field(..., description="Unique license identifier")
    license_key_hash: str = Field(..., description="SHA-256 hash of license key")
    tier: LicenseTier = Field(..., description="License tier level")
    holder_id: str = Field(..., description="Customer/holder identifier")
    holder_name: str = Field(..., description="Customer/holder name")
    
    # Timestamps
    issued_at: datetime = Field(..., description="When the license was issued")
    activated_at: datetime = Field(..., description="When the license was activated")
    expires_at: datetime = Field(..., description="When the license expires")
    deactivated_at: Optional[datetime] = Field(None, description="When deactivated")
    
    # Status
    status: LicenseStatus = Field(LicenseStatus.ACTIVE, description="Current status")
    
    # Features
    enabled_features: List[str] = Field(default_factory=list, description="Enabled features")
    
    # Metadata
    activation_metadata: Dict[str, Any] = Field(default_factory=dict)
    instance_id: str = Field(..., description="Instance identifier")
    
    # Grace period
    grace_period_days: int = Field(7, description="Grace period duration")
    grace_period_ends_at: Optional[datetime] = Field(None, description="Grace period end")
    
    @classmethod
    def create(
        cls,
        instance_id: str,
        license_key: str,
        tier: LicenseTier,
        holder_id: str,
        holder_name: str,
        issued_at: datetime,
        expires_at: datetime,
        enabled_features: List[str],
        activation_metadata: Optional[Dict[str, Any]] = None,
        grace_period_days: int = 7,
    ) -> "LicenseRecord":
        """Factory method to create a new license record."""
        license_id = f"LIC-{uuid.uuid4().hex[:8].upper()}"
        license_key_hash = hashlib.sha256(license_key.encode()).hexdigest()
        now = datetime.now(timezone.utc)
        
        return cls(
            PK=f"INSTANCE#{instance_id}",
            SK=f"LICENSE#{license_id}",
            license_id=license_id,
            license_key_hash=license_key_hash,
            tier=tier,
            holder_id=holder_id,
            holder_name=holder_name,
            issued_at=issued_at,
            activated_at=now,
            expires_at=expires_at,
            status=LicenseStatus.ACTIVE,
            enabled_features=enabled_features,
            activation_metadata=activation_metadata or {},
            instance_id=instance_id,
            grace_period_days=grace_period_days,
        )
    
    def is_expired(self) -> bool:
        """Check if license is expired (past grace period)."""
        now = datetime.now(timezone.utc)
        grace_end = self.get_grace_period_end()
        return now > grace_end
    
    def is_in_grace_period(self) -> bool:
        """Check if license is in grace period."""
        now = datetime.now(timezone.utc)
        if now <= self.expires_at:
            return False
        grace_end = self.get_grace_period_end()
        return now <= grace_end
    
    def get_grace_period_end(self) -> datetime:
        """Calculate when the grace period ends."""
        if self.grace_period_ends_at:
            return self.grace_period_ends_at
        return self.expires_at + timedelta(days=self.grace_period_days)
    
    def grace_period_days_remaining(self) -> int:
        """Calculate days remaining in grace period."""
        if not self.is_in_grace_period():
            return 0
        now = datetime.now(timezone.utc)
        grace_end = self.get_grace_period_end()
        delta = grace_end - now
        return max(0, delta.days)
    
    def days_remaining(self) -> int:
        """Calculate days remaining until expiration."""
        now = datetime.now(timezone.utc)
        delta = self.expires_at - now
        return max(0, delta.days)
    
    def to_dynamo_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        item = self.model_dump()
        # Convert datetime to ISO format strings
        for key in ["issued_at", "activated_at", "expires_at", "deactivated_at", "grace_period_ends_at"]:
            if item.get(key):
                item[key] = item[key].isoformat()
        # Convert enum to string
        item["tier"] = item["tier"].value if isinstance(item["tier"], LicenseTier) else item["tier"]
        item["status"] = item["status"].value if isinstance(item["status"], LicenseStatus) else item["status"]
        # Remove None values - DynamoDB doesn't accept None
        return {k: v for k, v in item.items() if v is not None}


class LicenseAuditEntry(BaseModel):
    """Audit log entry for license operations."""
    
    # Primary Key
    PK: str = Field(..., description="AUDIT#<year-month>")
    SK: str = Field(..., description="<timestamp>#<event_id>")
    
    # Entity metadata
    EntityType: Literal["LicenseAudit"] = "LicenseAudit"
    
    # Event data
    event_id: str = Field(..., description="Unique event identifier")
    event_type: LicenseEventType = Field(..., description="Type of event")
    timestamp: datetime = Field(..., description="When the event occurred")
    license_id: Optional[str] = Field(None, description="Associated license ID")
    
    # Context
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    
    # Details
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")
    result: str = Field(..., description="success or failure")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    
    @classmethod
    def create(
        cls,
        event_type: LicenseEventType,
        result: str,
        license_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> "LicenseAuditEntry":
        """Factory method to create a new audit entry."""
        now = datetime.now(timezone.utc)
        event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
        year_month = now.strftime("%Y-%m")
        timestamp_str = now.strftime("%Y%m%d%H%M%S%f")
        
        return cls(
            PK=f"AUDIT#{year_month}",
            SK=f"{timestamp_str}#{event_id}",
            event_id=event_id,
            event_type=event_type,
            timestamp=now,
            license_id=license_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            result=result,
            error_code=error_code,
        )
    
    def to_dynamo_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        item = self.model_dump()
        item["timestamp"] = item["timestamp"].isoformat()
        item["event_type"] = item["event_type"].value if isinstance(item["event_type"], LicenseEventType) else item["event_type"]
        # Remove None values - DynamoDB doesn't accept None
        return {k: v for k, v in item.items() if v is not None}


class FeatureTierMapping(BaseModel):
    """Mapping of features to required license tiers."""
    
    PK: str = Field(..., description="FEATURE#<feature_id>")
    SK: str = Field(default="MAPPING", description="Sort key")
    
    feature_id: str = Field(..., description="Unique feature identifier")
    feature_name: str = Field(..., description="Human-readable feature name")
    description: str = Field(..., description="Feature description")
    required_tier: LicenseTier = Field(..., description="Minimum tier required")
    is_active: bool = Field(True, description="Whether feature is active")
    
    @classmethod
    def create(
        cls,
        feature_id: str,
        feature_name: str,
        description: str,
        required_tier: LicenseTier,
    ) -> "FeatureTierMapping":
        """Factory method to create a new feature mapping."""
        return cls(
            PK=f"FEATURE#{feature_id}",
            feature_id=feature_id,
            feature_name=feature_name,
            description=description,
            required_tier=required_tier,
        )
    
    def to_dynamo_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        item = self.model_dump()
        item["required_tier"] = item["required_tier"].value if isinstance(item["required_tier"], LicenseTier) else item["required_tier"]
        return item


class ParsedLicenseKey(BaseModel):
    """Parsed components of a license key."""
    
    version: str = Field(..., description="License format version")
    tier: LicenseTier = Field(..., description="License tier")
    expiration: datetime = Field(..., description="Expiration date")
    holder_id: str = Field(..., description="Holder identifier")
    features: str = Field(..., description="Feature flags or 'ALL'")
    signature: str = Field(..., description="Base64-encoded signature")
    raw_key: str = Field(..., description="Original license key")
    
    def get_data_to_sign(self) -> str:
        """Get the data portion that should be signed."""
        tier_abbrev = {"basic": "BAS", "professional": "PRO", "enterprise": "ENT"}
        return f"{self.version}.{tier_abbrev[self.tier.value]}.{self.expiration.strftime('%Y%m%d')}.{self.holder_id}.{self.features}"
    
    def to_key_string(self) -> str:
        """Convert back to license key string format."""
        tier_abbrev = {"basic": "BAS", "professional": "PRO", "enterprise": "ENT"}
        return f"{self.version}.{tier_abbrev[self.tier.value]}.{self.expiration.strftime('%Y%m%d')}.{self.holder_id}.{self.features}.{self.signature}"
