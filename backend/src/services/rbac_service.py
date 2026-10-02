"""
RBAC Service

Service layer for managing Role-Based Access Control configuration.
Supports DynamoDB storage with fallback to default configuration.
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from loguru import logger

import boto3
from botocore.exceptions import ClientError

from ..models.rbac_model import (
    RBACConfig,
    RBACRole,
    RBACPermission,
    RBACCategory,
    RBACMetadata,
    RBACAuditEntry,
    DEFAULT_RBAC_CONFIG
)


class RBACService:
    """Service for managing RBAC configuration"""
    
    def __init__(self):
        """Initialize RBAC service"""
        self.capability = os.getenv('CAPABILITY_NAME', 'call-processing')
        self.environment = os.getenv('ENVIRONMENT', 'dev')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        
        # DynamoDB table name. Prefer the operator-injected RBAC_TABLE env var
        # (set in deploy_backend); fall back to the capability/env convention so
        # local-dev and tests that don't run via the operator still resolve a
        # sensible default.
        self.table_name = os.getenv(
            'RBAC_TABLE',
            f"{self.capability}-{self.environment}-rbac",
        )
        
        # Config key in DynamoDB
        self.config_key = "rbac_config"
        
        # Cached config
        self._config_cache: Optional[RBACConfig] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 60  # Cache for 1 minute
        
        # Initialize DynamoDB client
        try:
            self._dynamodb = boto3.resource('dynamodb', region_name=self.region)
            self._table = self._dynamodb.Table(self.table_name)
            self._dynamodb_available = True
            logger.info(f"RBAC Service initialized with DynamoDB table: {self.table_name}")
        except Exception as e:
            logger.warning(f"DynamoDB not available for RBAC: {e}. Using default config.")
            self._dynamodb_available = False
            self._table = None
    
    def _is_cache_valid(self) -> bool:
        """Check if cached config is still valid"""
        if not self._config_cache or not self._cache_timestamp:
            return False
        
        age = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
        return age < self._cache_ttl_seconds
    
    def _invalidate_cache(self):
        """Invalidate the config cache"""
        self._config_cache = None
        self._cache_timestamp = None
    
    async def get_config(self, force_refresh: bool = False) -> RBACConfig:
        """
        Get RBAC configuration.
        
        Tries to load from DynamoDB, falls back to default config.
        Uses caching to reduce DynamoDB reads.
        
        Args:
            force_refresh: If True, bypass cache and reload from source
            
        Returns:
            RBACConfig object
        """
        # Return cached config if valid
        if not force_refresh and self._is_cache_valid():
            return self._config_cache
        
        # Try loading from DynamoDB
        if self._dynamodb_available:
            try:
                response = self._table.get_item(Key={'id': self.config_key})
                
                if 'Item' in response:
                    config_data = response['Item'].get('config', {})
                    self._config_cache = RBACConfig(**config_data)
                    self._cache_timestamp = datetime.now(timezone.utc)
                    logger.debug("Loaded RBAC config from DynamoDB")
                    return self._config_cache
                else:
                    # No config in DynamoDB, initialize with defaults
                    logger.info("No RBAC config in DynamoDB, initializing with defaults")
                    await self._save_config_to_dynamodb(RBACConfig(**DEFAULT_RBAC_CONFIG))
                    return await self.get_config()
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(f"RBAC DynamoDB table not found: {self.table_name}")
                else:
                    logger.error(f"DynamoDB error loading RBAC config: {e}")
            except Exception as e:
                logger.error(f"Error loading RBAC config: {e}")
        
        # Fallback to default config
        logger.debug("Using default RBAC configuration")
        self._config_cache = RBACConfig(**DEFAULT_RBAC_CONFIG)
        self._cache_timestamp = datetime.now(timezone.utc)
        return self._config_cache
    
    async def _save_config_to_dynamodb(self, config: RBACConfig) -> bool:
        """Save config to DynamoDB"""
        if not self._dynamodb_available:
            logger.warning("DynamoDB not available, cannot save RBAC config")
            return False
        
        try:
            # Convert to dict and handle datetime serialization
            config_dict = json.loads(config.model_dump_json())
            
            self._table.put_item(
                Item={
                    'id': self.config_key,
                    'config': config_dict,
                    'updatedAt': datetime.now(timezone.utc).isoformat()
                }
            )
            
            self._invalidate_cache()
            logger.info("Saved RBAC config to DynamoDB")
            return True
            
        except Exception as e:
            logger.error(f"Error saving RBAC config to DynamoDB: {e}")
            return False
    
    async def get_roles(self) -> List[RBACRole]:
        """Get all roles"""
        config = await self.get_config()
        return config.roles
    
    async def get_role(self, role_id: str) -> Optional[RBACRole]:
        """Get a specific role by ID"""
        config = await self.get_config()
        for role in config.roles:
            if role.id == role_id:
                return role
        return None
    
    async def get_permissions(self) -> List[RBACPermission]:
        """Get all permissions"""
        config = await self.get_config()
        return config.permissions
    
    async def get_permission(self, permission_id: str) -> Optional[RBACPermission]:
        """Get a specific permission by ID"""
        config = await self.get_config()
        for perm in config.permissions:
            if perm.id == permission_id:
                return perm
        return None
    
    async def get_categories(self) -> List[RBACCategory]:
        """Get all permission categories"""
        config = await self.get_config()
        return config.transactionCategories
    
    async def get_role_permissions(self, role_id: str) -> List[str]:
        """Get permissions for a specific role"""
        config = await self.get_config()
        return config.rolePermissions.get(role_id, [])
    
    async def update_role_permissions(
        self,
        role_id: str,
        permissions: List[str],
        updated_by: str
    ) -> Dict[str, Any]:
        """
        Update permissions for a role.
        
        Args:
            role_id: Role to update
            permissions: New list of permission IDs
            updated_by: User making the change
            
        Returns:
            Dict with success status and updated permissions
        """
        config = await self.get_config(force_refresh=True)
        
        # Validate role exists
        role = await self.get_role(role_id)
        if not role:
            return {
                "success": False,
                "message": f"Role '{role_id}' not found",
                "roleId": role_id,
                "permissions": []
            }
        
        # Validate permissions exist
        valid_permission_ids = {p.id for p in config.permissions}
        invalid_permissions = [p for p in permissions if p not in valid_permission_ids]
        
        if invalid_permissions:
            return {
                "success": False,
                "message": f"Invalid permissions: {invalid_permissions}",
                "roleId": role_id,
                "permissions": []
            }
        
        # Get previous permissions for audit
        previous_permissions = config.rolePermissions.get(role_id, [])
        
        # Update permissions
        config.rolePermissions[role_id] = permissions
        
        # Update metadata
        config.metadata.lastUpdated = datetime.now(timezone.utc)
        config.metadata.updatedBy = updated_by
        config.metadata.version = self._increment_version(config.metadata.version)
        
        # Add audit entry
        audit_entry = RBACAuditEntry(
            action="UPDATE_ROLE_PERMISSIONS",
            userId=updated_by,
            roleId=role_id,
            changes=f"Updated permissions for role {role_id}",
            previousValue={"permissions": previous_permissions},
            newValue={"permissions": permissions},
            version=config.metadata.version
        )
        config.auditLog.append(audit_entry)
        
        # Keep only last 100 audit entries
        if len(config.auditLog) > 100:
            config.auditLog = config.auditLog[-100:]
        
        # Save to DynamoDB
        saved = await self._save_config_to_dynamodb(config)
        
        return {
            "success": saved or not self._dynamodb_available,
            "message": "Permissions updated successfully" if saved else "Permissions updated (local only)",
            "roleId": role_id,
            "permissions": permissions,
            "updatedAt": config.metadata.lastUpdated.isoformat()
        }
    
    async def get_audit_log(self, limit: int = 50) -> List[RBACAuditEntry]:
        """Get recent audit log entries"""
        config = await self.get_config()
        return config.auditLog[-limit:][::-1]  # Return most recent first
    
    def _increment_version(self, version: str) -> str:
        """Increment the patch version number"""
        try:
            parts = version.split('.')
            parts[-1] = str(int(parts[-1]) + 1)
            return '.'.join(parts)
        except:
            return version
    
    def has_permission(self, role: str, permission: str) -> bool:
        """
        Check if a role has a specific permission.
        
        This is a synchronous check using cached config.
        
        Args:
            role: Role ID (Admin, Executive, SalesManager, Rep)
            permission: Permission ID to check
            
        Returns:
            True if role has the permission
        """
        # Admin has all permissions
        if role == 'Admin':
            return True
        
        # Use cached config for sync check
        if self._config_cache:
            permissions = self._config_cache.rolePermissions.get(role, [])
            return permission in permissions
        
        # Fallback to default config
        default_permissions = DEFAULT_RBAC_CONFIG['rolePermissions'].get(role, [])
        return permission in default_permissions
    
    def get_user_permissions(self, role: str) -> List[str]:
        """
        Get all permissions for a role.
        
        Synchronous method using cached config.
        
        Args:
            role: Role ID
            
        Returns:
            List of permission IDs
        """
        # Admin has all permissions
        if role == 'Admin':
            if self._config_cache:
                return [p.id for p in self._config_cache.permissions]
            return [p['id'] for p in DEFAULT_RBAC_CONFIG['permissions']]
        
        if self._config_cache:
            return self._config_cache.rolePermissions.get(role, [])
        
        return DEFAULT_RBAC_CONFIG['rolePermissions'].get(role, [])


# Singleton instance
_rbac_service: Optional[RBACService] = None


def get_rbac_service() -> RBACService:
    """Get or create RBAC service singleton"""
    global _rbac_service
    if _rbac_service is None:
        _rbac_service = RBACService()
    return _rbac_service
