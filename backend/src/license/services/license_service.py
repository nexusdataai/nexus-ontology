"""
License Service

Core business logic for license management including activation, validation,
status retrieval, deactivation, and renewal.
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger

from ..models.license_model import LicenseRecord, LicenseAuditEntry, ParsedLicenseKey
from ..models.enums import LicenseTier, LicenseStatus, LicenseEventType
from ..models.api_models import (
    LicenseActivationResponse,
    LicenseActivationData,
    LicenseStatusResponse,
    LicenseStatusData,
    LicenseDeactivationResponse,
    LicenseDeactivationData,
    LicenseRenewalResponse,
    LicenseRenewalData,
    LicenseValidationResult,
    GracePeriodInfo,
    FeatureAccessData,
)
from ..utils.key_parser import LicenseKeyParser, LicenseKeyParseError
from ..utils.crypto import LicenseCrypto, LicenseCryptoError, hash_license_key
from ..consts import (
    LicenseErrorCode,
    DEFAULT_GRACE_PERIOD_DAYS,
    EXPIRATION_WARNING_DAYS,
    RENEWAL_WINDOW_DAYS,
    TIER_FEATURES,
)
from .license_repository import LicenseRepository, AuditRepository, LicenseRepositoryError
from .cache_manager import LicenseCacheManager, get_cache_manager


class LicenseServiceError(Exception):
    """Exception raised for license service errors."""
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class LicenseService:
    """
    Core license management service.
    
    Provides all license operations including activation, validation,
    status retrieval, deactivation, and renewal.
    """
    
    def __init__(
        self,
        repository: Optional[LicenseRepository] = None,
        audit_repository: Optional[AuditRepository] = None,
        cache_manager: Optional[LicenseCacheManager] = None,
        crypto: Optional[LicenseCrypto] = None,
        instance_id: Optional[str] = None,
    ):
        """
        Initialize license service.
        
        Args:
            repository: License repository (creates default if None)
            audit_repository: Audit repository (creates default if None)
            cache_manager: Cache manager (uses global if None)
            crypto: Crypto verifier (creates default if None)
            instance_id: Instance identifier (generates if None)
        """
        self._repository = repository or LicenseRepository()
        self._audit_repository = audit_repository or AuditRepository()
        self._cache = cache_manager or get_cache_manager()
        self._crypto = crypto or LicenseCrypto()
        self._instance_id = instance_id or os.environ.get(
            'INSTANCE_ID', f"INST-{uuid.uuid4().hex[:8]}"
        )

    @property
    def instance_id(self) -> str:
        """Get the instance identifier."""
        return self._instance_id
    
    async def activate_license(
        self,
        license_key: str,
        activation_metadata: Optional[Dict[str, Any]] = None,
    ) -> LicenseActivationResponse:
        """
        Activate a license key for this instance.
        
        Args:
            license_key: The license key to activate
            activation_metadata: Optional metadata about the activation
            
        Returns:
            LicenseActivationResponse with activation details or error
        """
        try:
            # Step 1: Parse the license key
            try:
                parsed = LicenseKeyParser.parse(license_key)
            except LicenseKeyParseError as e:
                await self._log_audit(
                    LicenseEventType.VALIDATION_FAILED,
                    "failure",
                    error_code=e.error_code,
                    details={"reason": e.message},
                )
                return LicenseActivationResponse(
                    status="error",
                    message=e.message,
                    error_code=e.error_code,
                    details={"reason": e.message},
                )
            
            # Step 2: Verify cryptographic signature
            try:
                self._crypto.verify_signature(parsed)
            except LicenseCryptoError as e:
                await self._log_audit(
                    LicenseEventType.VALIDATION_FAILED,
                    "failure",
                    error_code=e.error_code,
                    details={"reason": e.message},
                )
                return LicenseActivationResponse(
                    status="error",
                    message=e.message,
                    error_code=e.error_code,
                    details={"reason": e.message},
                )
            
            # Step 3: Check for existing activation
            existing = await self._repository.get_license_by_instance(self._instance_id)
            if existing and existing.status == LicenseStatus.ACTIVE:
                # Check if it's the same license key
                if existing.license_key_hash == hash_license_key(license_key):
                    # Return existing activation status
                    return LicenseActivationResponse(
                        status="success",
                        message="License already activated",
                        data=self._record_to_activation_data(existing),
                    )
                else:
                    # Different license - return error
                    return LicenseActivationResponse(
                        status="error",
                        message="A different license is already activated on this instance",
                        error_code=LicenseErrorCode.ALREADY_ACTIVATED,
                        details={"existing_license_id": existing.license_id},
                    )
            
            # Step 4: Check if license is expired
            if parsed.expiration < datetime.now(timezone.utc):
                await self._log_audit(
                    LicenseEventType.VALIDATION_FAILED,
                    "failure",
                    error_code=LicenseErrorCode.EXPIRED,
                    details={"expiration": parsed.expiration.isoformat()},
                )
                return LicenseActivationResponse(
                    status="error",
                    message="License key has expired",
                    error_code=LicenseErrorCode.EXPIRED,
                    details={"expired_at": parsed.expiration.isoformat()},
                )
            
            # Step 5: Determine enabled features based on tier
            enabled_features = self._get_features_for_tier(parsed.tier)
            
            # Step 6: Create and store license record
            record = LicenseRecord.create(
                instance_id=self._instance_id,
                license_key=license_key,
                tier=parsed.tier,
                holder_id=parsed.holder_id,
                holder_name=self._extract_holder_name(parsed.holder_id),
                issued_at=datetime.now(timezone.utc),
                expires_at=parsed.expiration,
                enabled_features=enabled_features,
                activation_metadata=activation_metadata,
                grace_period_days=DEFAULT_GRACE_PERIOD_DAYS,
            )
            
            await self._repository.save_license(record)
            
            # Step 7: Update cache
            self._cache.set_license(self._instance_id, record)
            
            # Step 8: Log audit entry
            await self._log_audit(
                LicenseEventType.ACTIVATED,
                "success",
                license_id=record.license_id,
                details={
                    "tier": record.tier.value,
                    "holder_id": record.holder_id,
                    "expires_at": record.expires_at.isoformat(),
                },
            )
            
            logger.info(f"License activated: {record.license_id} for instance {self._instance_id}")
            
            return LicenseActivationResponse(
                status="success",
                message="License activated successfully",
                data=self._record_to_activation_data(record),
            )
            
        except LicenseRepositoryError as e:
            logger.error(f"Repository error during activation: {e}")
            return LicenseActivationResponse(
                status="error",
                message="Failed to store license activation",
                error_code=LicenseErrorCode.VALIDATION_ERROR,
                details={"reason": str(e)},
            )
        except Exception as e:
            logger.exception(f"Unexpected error during activation: {e}")
            return LicenseActivationResponse(
                status="error",
                message="Internal error during license activation",
                error_code=LicenseErrorCode.VALIDATION_ERROR,
                details={"reason": str(e)},
            )

    async def validate_license(self) -> LicenseValidationResult:
        """
        Validate the currently active license.
        
        Returns:
            LicenseValidationResult with validation status
        """
        # Check cache first
        cached = self._cache.get_validation(self._instance_id)
        if cached:
            return cached
        
        # Get license from repository
        record = await self._get_current_license()
        
        # Treat no record or deactivated/revoked as not activated
        if not record or record.status in (LicenseStatus.DEACTIVATED, LicenseStatus.REVOKED):
            result = LicenseValidationResult(
                is_valid=False,
                status=LicenseStatus.NOT_ACTIVATED,
                error_code=LicenseErrorCode.NOT_ACTIVATED,
                message="No license is currently activated",
                can_write=False,
            )
            self._cache.set_validation(self._instance_id, result)
            return result
        
        now = datetime.now(timezone.utc)
        
        # Check if in grace period
        if record.is_in_grace_period():
            result = LicenseValidationResult(
                is_valid=True,
                status=LicenseStatus.GRACE_PERIOD,
                license_id=record.license_id,
                tier=record.tier,
                message="License is in grace period - read-only mode",
                is_in_grace_period=True,
                can_write=False,
            )
            self._cache.set_validation(self._instance_id, result)
            return result
        
        # Check if expired (past grace period)
        if record.is_expired():
            result = LicenseValidationResult(
                is_valid=False,
                status=LicenseStatus.EXPIRED,
                license_id=record.license_id,
                tier=record.tier,
                error_code=LicenseErrorCode.EXPIRED,
                message="License has expired",
                can_write=False,
            )
            self._cache.set_validation(self._instance_id, result)
            return result
        
        # License is valid and active
        result = LicenseValidationResult(
            is_valid=True,
            status=LicenseStatus.ACTIVE,
            license_id=record.license_id,
            tier=record.tier,
            message="License is valid",
            can_write=True,
        )
        self._cache.set_validation(self._instance_id, result)
        return result
    
    async def get_license_status(self) -> LicenseStatusResponse:
        """
        Get detailed status of current license.
        
        Returns:
            LicenseStatusResponse with full status information
        """
        record = await self._get_current_license()
        
        # Treat no record or deactivated/revoked licenses as not activated
        if not record or record.status in (LicenseStatus.DEACTIVATED, LicenseStatus.REVOKED):
            return LicenseStatusResponse(
                status="success",
                data=LicenseStatusData(
                    license_status=LicenseStatus.NOT_ACTIVATED,
                    message="No license is currently activated",
                    activation_instructions="POST /api/v1/license/activate with your license key",
                ),
            )
        
        now = datetime.now(timezone.utc)
        days_remaining = record.days_remaining()
        is_expiring_soon = days_remaining <= EXPIRATION_WARNING_DAYS
        
        # Determine current status
        if record.status == LicenseStatus.REVOKED:
            current_status = LicenseStatus.REVOKED
        elif record.status == LicenseStatus.DEACTIVATED:
            current_status = LicenseStatus.DEACTIVATED
        elif record.is_in_grace_period():
            current_status = LicenseStatus.GRACE_PERIOD
        elif record.is_expired():
            current_status = LicenseStatus.EXPIRED
        else:
            current_status = LicenseStatus.ACTIVE
        
        # Build grace period info if applicable
        grace_period_info = None
        if record.is_in_grace_period() or (record.is_expired() and record.grace_period_ends_at):
            grace_days_remaining = 0
            if record.grace_period_ends_at:
                grace_delta = record.grace_period_ends_at - now
                grace_days_remaining = max(0, grace_delta.days)
            
            grace_period_info = GracePeriodInfo(
                is_in_grace_period=record.is_in_grace_period(),
                grace_period_ends_at=record.grace_period_ends_at,
                days_remaining=grace_days_remaining,
                restrictions=["write_operations_disabled"] if record.is_in_grace_period() else [],
            )
        
        # Build expiration warning
        expiration_warning = None
        if is_expiring_soon and current_status == LicenseStatus.ACTIVE:
            expiration_warning = f"License expires in {days_remaining} days"
        
        return LicenseStatusResponse(
            status="success",
            data=LicenseStatusData(
                license_status=current_status,
                license_id=record.license_id,
                tier=record.tier,
                holder_name=record.holder_name,
                activated_at=record.activated_at,
                expires_at=record.expires_at,
                days_remaining=days_remaining,
                is_expiring_soon=is_expiring_soon,
                expiration_warning=expiration_warning,
                features=record.enabled_features,
                grace_period=grace_period_info,
            ),
        )

    async def deactivate_license(self, reason: str) -> LicenseDeactivationResponse:
        """
        Deactivate the current license.
        
        Args:
            reason: Reason for deactivation
            
        Returns:
            LicenseDeactivationResponse with deactivation details
        """
        record = await self._get_current_license()
        
        if not record or record.status in (LicenseStatus.DEACTIVATED, LicenseStatus.NOT_ACTIVATED):
            return LicenseDeactivationResponse(
                status="error",
                message="No active license to deactivate",
                error_code=LicenseErrorCode.NOT_ACTIVATED,
            )
        
        try:
            now = datetime.now(timezone.utc)
            
            # Update license status
            await self._repository.update_license_status(
                instance_id=self._instance_id,
                license_id=record.license_id,
                status=LicenseStatus.DEACTIVATED,
                deactivated_at=now,
            )
            
            # Clear cache
            self._cache.invalidate_license(self._instance_id)
            
            # Log audit entry
            await self._log_audit(
                LicenseEventType.DEACTIVATED,
                "success",
                license_id=record.license_id,
                details={"reason": reason},
            )
            
            logger.info(f"License deactivated: {record.license_id}")
            
            return LicenseDeactivationResponse(
                status="success",
                message="License deactivated successfully",
                data=LicenseDeactivationData(
                    deactivated_at=now,
                    previous_license_id=record.license_id,
                    can_reactivate=True,
                ),
            )
            
        except LicenseRepositoryError as e:
            logger.error(f"Failed to deactivate license: {e}")
            return LicenseDeactivationResponse(
                status="error",
                message="Failed to deactivate license",
                error_code=LicenseErrorCode.DEACTIVATION_FAILED,
            )
    
    async def renew_license(self, renewal_key: str) -> LicenseRenewalResponse:
        """
        Renew license with a new key.
        
        Args:
            renewal_key: The renewal license key
            
        Returns:
            LicenseRenewalResponse with renewal details
        """
        # Get current license
        record = await self._get_current_license()
        
        # Cannot renew if no license or license is deactivated/revoked
        if not record or record.status in (LicenseStatus.DEACTIVATED, LicenseStatus.REVOKED):
            return LicenseRenewalResponse(
                status="error",
                message="No active license to renew",
                error_code=LicenseErrorCode.NOT_ACTIVATED,
            )
        
        # Parse renewal key
        try:
            parsed = LicenseKeyParser.parse(renewal_key)
        except LicenseKeyParseError as e:
            return LicenseRenewalResponse(
                status="error",
                message=e.message,
                error_code=e.error_code,
            )
        
        # Verify signature
        try:
            self._crypto.verify_signature(parsed)
        except LicenseCryptoError as e:
            return LicenseRenewalResponse(
                status="error",
                message=e.message,
                error_code=e.error_code,
            )
        
        # Verify holder ID matches
        if parsed.holder_id != record.holder_id:
            return LicenseRenewalResponse(
                status="error",
                message="Renewal key holder does not match current license",
                error_code=LicenseErrorCode.RENEWAL_INVALID,
            )
        
        # Check renewal window (can renew up to 90 days before expiration)
        now = datetime.now(timezone.utc)
        days_until_expiration = (record.expires_at - now).days
        
        if days_until_expiration > RENEWAL_WINDOW_DAYS and record.status == LicenseStatus.ACTIVE:
            return LicenseRenewalResponse(
                status="error",
                message=f"Cannot renew more than {RENEWAL_WINDOW_DAYS} days before expiration",
                error_code=LicenseErrorCode.RENEWAL_INVALID,
            )
        
        # Check if renewal key is expired
        if parsed.expiration < now:
            return LicenseRenewalResponse(
                status="error",
                message="Renewal key has expired",
                error_code=LicenseErrorCode.EXPIRED,
            )
        
        previous_expiration = record.expires_at
        tier_changed = parsed.tier != record.tier
        new_features = self._get_features_for_tier(parsed.tier)
        
        try:
            # Update license
            await self._repository.update_license_expiration(
                instance_id=self._instance_id,
                license_id=record.license_id,
                expires_at=parsed.expiration,
                tier=parsed.tier if tier_changed else None,
                enabled_features=new_features if tier_changed else None,
            )
            
            # Clear cache to force refresh
            self._cache.invalidate_license(self._instance_id)
            
            # Log audit entry
            await self._log_audit(
                LicenseEventType.RENEWED,
                "success",
                license_id=record.license_id,
                details={
                    "previous_expiration": previous_expiration.isoformat(),
                    "new_expiration": parsed.expiration.isoformat(),
                    "tier_changed": tier_changed,
                    "new_tier": parsed.tier.value if tier_changed else None,
                },
            )
            
            logger.info(f"License renewed: {record.license_id}")
            
            return LicenseRenewalResponse(
                status="success",
                message="License renewed successfully",
                data=LicenseRenewalData(
                    license_id=record.license_id,
                    previous_expiration=previous_expiration,
                    new_expiration=parsed.expiration,
                    tier=parsed.tier,
                    tier_changed=tier_changed,
                    features=new_features,
                ),
            )
            
        except LicenseRepositoryError as e:
            logger.error(f"Failed to renew license: {e}")
            return LicenseRenewalResponse(
                status="error",
                message="Failed to renew license",
                error_code=LicenseErrorCode.VALIDATION_ERROR,
            )

    async def check_feature_access(self, feature_id: str) -> FeatureAccessData:
        """
        Check if current license permits feature access.
        
        Args:
            feature_id: The feature to check
            
        Returns:
            FeatureAccessData with access status
        """
        from ..consts import FEATURE_TIER_MAPPING
        
        # Get required tier for feature
        required_tier = FEATURE_TIER_MAPPING.get(feature_id)
        
        if required_tier is None:
            # Unknown feature - deny by default
            return FeatureAccessData(
                feature_id=feature_id,
                is_allowed=False,
                required_tier=LicenseTier.ENTERPRISE,  # Default to highest
                current_tier=None,
                upgrade_message=f"Unknown feature: {feature_id}",
            )
        
        # Get current license
        record = await self._get_current_license()
        
        if not record or record.status != LicenseStatus.ACTIVE:
            return FeatureAccessData(
                feature_id=feature_id,
                is_allowed=False,
                required_tier=required_tier,
                current_tier=None,
                upgrade_message="No active license",
            )
        
        # Check tier hierarchy
        is_allowed = record.tier >= required_tier
        
        upgrade_message = None
        if not is_allowed:
            upgrade_message = f"Upgrade to {required_tier.value} tier to access this feature"
        
        return FeatureAccessData(
            feature_id=feature_id,
            is_allowed=is_allowed,
            required_tier=required_tier,
            current_tier=record.tier,
            upgrade_message=upgrade_message,
        )
    
    async def get_audit_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieve license audit logs.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            Dict with audit log entries and pagination info
        """
        entries, total_count = await self._audit_repository.get_audit_logs(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        
        return {
            "total_count": total_count,
            "page_size": limit,
            "offset": offset,
            "entries": [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type.value,
                    "license_id": e.license_id,
                    "details": e.details,
                    "ip_address": e.ip_address,
                    "user_agent": e.user_agent,
                }
                for e in entries
            ],
        }
    
    # ==========================================
    # Private Helper Methods
    # ==========================================
    
    async def _get_current_license(self) -> Optional[LicenseRecord]:
        """Get the current license, checking cache first."""
        # Check cache
        cached = self._cache.get_license(self._instance_id)
        if cached:
            return cached
        
        # Get from repository
        try:
            record = await self._repository.get_license_by_instance(self._instance_id)
        except LicenseRepositoryError as e:
            logger.warning(f"Failed to get license from repository: {e}")
            return None
        
        if record:
            self._cache.set_license(self._instance_id, record)
        
        return record
    
    def _get_features_for_tier(self, tier: LicenseTier) -> List[str]:
        """Get enabled features for a tier."""
        if tier == LicenseTier.ENTERPRISE:
            return ["ALL"]
        return TIER_FEATURES.get(tier, [])
    
    def _extract_holder_name(self, holder_id: str) -> str:
        """Extract a display name from holder ID."""
        # Simple extraction - in production this might look up from a database
        parts = holder_id.split("-")
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        return holder_id
    
    def _record_to_activation_data(self, record: LicenseRecord) -> LicenseActivationData:
        """Convert a license record to activation data."""
        return LicenseActivationData(
            license_id=record.license_id,
            tier=record.tier,
            holder_name=record.holder_name,
            holder_id=record.holder_id,
            activated_at=record.activated_at,
            expires_at=record.expires_at,
            days_remaining=record.days_remaining(),
            features=record.enabled_features,
            is_active=record.status == LicenseStatus.ACTIVE,
        )
    
    async def _log_audit(
        self,
        event_type: LicenseEventType,
        result: str,
        license_id: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log an audit entry."""
        try:
            entry = LicenseAuditEntry.create(
                event_type=event_type,
                result=result,
                license_id=license_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                error_code=error_code,
            )
            await self._audit_repository.save_audit_entry(entry)
        except Exception as e:
            # Don't fail the operation if audit logging fails
            logger.error(f"Failed to log audit entry: {e}")
