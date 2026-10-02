"""
Audit Service

Provides audit logging for all license operations.
Ensures immutability and completeness of audit entries.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from loguru import logger

from ..models.license_model import LicenseAuditEntry
from ..models.enums import LicenseEventType
from .license_repository import AuditRepository, LicenseRepositoryError


class AuditServiceError(Exception):
    """Exception raised for audit service errors."""
    pass


class AuditService:
    """
    Service for managing license audit logs.
    
    Provides:
    - Logging of all license operations
    - Immutable audit entries
    - Paginated retrieval with filtering
    """
    
    def __init__(self, repository: Optional[AuditRepository] = None):
        """
        Initialize audit service.
        
        Args:
            repository: Audit repository (creates default if None)
        """
        self._repository = repository or AuditRepository()
    
    async def log_event(
        self,
        event_type: LicenseEventType,
        result: str,
        license_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> LicenseAuditEntry:
        """
        Log a license operation event.
        
        Args:
            event_type: Type of event
            result: "success" or "failure"
            license_id: Associated license ID
            details: Event-specific details
            ip_address: Client IP address
            user_agent: Client user agent
            error_code: Error code if failed
            
        Returns:
            Created audit entry
        """
        entry = LicenseAuditEntry.create(
            event_type=event_type,
            result=result,
            license_id=license_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            error_code=error_code,
        )
        
        try:
            await self._repository.save_audit_entry(entry)
            logger.debug(f"Audit logged: {event_type.value} - {result}")
            return entry
        except LicenseRepositoryError as e:
            logger.error(f"Failed to save audit entry: {e}")
            raise AuditServiceError(f"Failed to log audit event: {e}")
    
    async def log_activation(
        self,
        license_id: str,
        tier: str,
        holder_id: str,
        expires_at: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> LicenseAuditEntry:
        """Log a license activation event."""
        return await self.log_event(
            event_type=LicenseEventType.ACTIVATED,
            result="success",
            license_id=license_id,
            details={
                "tier": tier,
                "holder_id": holder_id,
                "expires_at": expires_at,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    async def log_validation(
        self,
        license_id: str,
        is_valid: bool,
        cached: bool = False,
        error_code: Optional[str] = None,
    ) -> LicenseAuditEntry:
        """Log a license validation event."""
        event_type = LicenseEventType.VALIDATED if is_valid else LicenseEventType.VALIDATION_FAILED
        return await self.log_event(
            event_type=event_type,
            result="success" if is_valid else "failure",
            license_id=license_id,
            details={
                "validation_result": "valid" if is_valid else "invalid",
                "cached": cached,
            },
            error_code=error_code,
        )
    
    async def log_deactivation(
        self,
        license_id: str,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> LicenseAuditEntry:
        """Log a license deactivation event."""
        return await self.log_event(
            event_type=LicenseEventType.DEACTIVATED,
            result="success",
            license_id=license_id,
            details={"reason": reason},
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    async def log_renewal(
        self,
        license_id: str,
        previous_expiration: str,
        new_expiration: str,
        tier_changed: bool,
        new_tier: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> LicenseAuditEntry:
        """Log a license renewal event."""
        return await self.log_event(
            event_type=LicenseEventType.RENEWED,
            result="success",
            license_id=license_id,
            details={
                "previous_expiration": previous_expiration,
                "new_expiration": new_expiration,
                "tier_changed": tier_changed,
                "new_tier": new_tier,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    async def log_expiration(
        self,
        license_id: str,
        expired_at: str,
    ) -> LicenseAuditEntry:
        """Log a license expiration event."""
        return await self.log_event(
            event_type=LicenseEventType.EXPIRED,
            result="success",
            license_id=license_id,
            details={"expired_at": expired_at},
        )
    
    async def log_grace_period_started(
        self,
        license_id: str,
        grace_period_ends_at: str,
    ) -> LicenseAuditEntry:
        """Log grace period start event."""
        return await self.log_event(
            event_type=LicenseEventType.GRACE_PERIOD_STARTED,
            result="success",
            license_id=license_id,
            details={"grace_period_ends_at": grace_period_ends_at},
        )
    
    async def log_feature_access(
        self,
        license_id: str,
        feature_id: str,
        is_allowed: bool,
        current_tier: str,
        required_tier: str,
    ) -> LicenseAuditEntry:
        """Log a feature access check event."""
        event_type = (
            LicenseEventType.FEATURE_ACCESS_GRANTED 
            if is_allowed 
            else LicenseEventType.FEATURE_ACCESS_DENIED
        )
        return await self.log_event(
            event_type=event_type,
            result="success" if is_allowed else "denied",
            license_id=license_id,
            details={
                "feature_id": feature_id,
                "current_tier": current_tier,
                "required_tier": required_tier,
            },
        )
    
    async def get_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieve audit logs with pagination.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum results per page
            offset: Pagination offset
            
        Returns:
            Dict with entries and pagination info
        """
        entries, total_count = await self._repository.get_audit_logs(
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
                    "result": e.result,
                    "error_code": e.error_code,
                    "ip_address": e.ip_address,
                    "user_agent": e.user_agent,
                }
                for e in entries
            ],
        }
    
    async def get_logs_by_license(
        self,
        license_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for a specific license.
        
        Args:
            license_id: License identifier
            limit: Maximum results
            
        Returns:
            List of audit entries
        """
        entries = await self._repository.get_audit_logs_by_license(
            license_id=license_id,
            limit=limit,
        )
        
        return [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type.value,
                "details": e.details,
                "result": e.result,
            }
            for e in entries
        ]


# Singleton instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Get or create the global audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service


def reset_audit_service() -> None:
    """Reset the global audit service (for testing)."""
    global _audit_service
    _audit_service = None
