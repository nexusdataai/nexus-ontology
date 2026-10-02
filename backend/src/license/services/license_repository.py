"""
License Repository

Data access layer for license records and audit logs in DynamoDB.
Implements CRUD operations with proper error handling.
"""

import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from loguru import logger
import boto3
from botocore.exceptions import ClientError

from ..models.license_model import LicenseRecord, LicenseAuditEntry
from ..models.enums import LicenseStatus, LicenseEventType, LicenseTier
from ..consts import get_license_table_name, get_license_audit_table_name


class LicenseRepositoryError(Exception):
    """Exception raised for repository errors."""
    pass


class LicenseRepository:
    """
    Repository for license record persistence in DynamoDB.
    """
    
    def __init__(self, table_name: Optional[str] = None):
        """
        Initialize repository with DynamoDB table.
        
        Args:
            table_name: Override table name (for testing)
        """
        self._table_name = table_name or get_license_table_name()
        self._client = self._get_dynamodb_client()
        self._table = self._get_table()
    
    def _get_dynamodb_client(self):
        """Get DynamoDB resource with LocalStack support."""
        try:
            from src.config.localstack_config import get_localstack_config, is_localstack_enabled
            
            if is_localstack_enabled():
                config = get_localstack_config()
                return boto3.resource(
                    'dynamodb',
                    endpoint_url=config.endpoint_url,
                    region_name=config.region,
                    aws_access_key_id=config.access_key,
                    aws_secret_access_key=config.secret_key,
                )
        except ImportError:
            pass
        
        # Fallback: check for explicit endpoint URL
        endpoint_url = os.environ.get('DYNAMODB_ENDPOINT_URL') or os.environ.get('AWS_ENDPOINT_URL_DYNAMODB')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        if endpoint_url:
            return boto3.resource('dynamodb', endpoint_url=endpoint_url, region_name=region)
        return boto3.resource('dynamodb', region_name=region)
    
    def _get_table(self):
        """Get DynamoDB table reference."""
        return self._client.Table(self._table_name)
    
    async def save_license(self, record: LicenseRecord) -> LicenseRecord:
        """
        Save a license record to DynamoDB.
        
        Args:
            record: License record to save
            
        Returns:
            Saved license record
        """
        try:
            item = record.to_dynamo_item()
            self._table.put_item(Item=item)
            logger.info(f"Saved license record: {record.license_id}")
            return record
        except ClientError as e:
            logger.error(f"Failed to save license: {e}")
            raise LicenseRepositoryError(f"Failed to save license: {e}")
    
    async def get_license_by_instance(self, instance_id: str) -> Optional[LicenseRecord]:
        """
        Get the active license for an instance.
        
        Args:
            instance_id: Instance identifier
            
        Returns:
            License record or None if not found
        """
        try:
            # First, try to find an ACTIVE license
            response = self._table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
                FilterExpression='#status = :active_status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':pk': f'INSTANCE#{instance_id}',
                    ':sk_prefix': 'LICENSE#',
                    ':active_status': 'active',
                },
                Limit=1,
            )
            
            items = response.get('Items', [])
            if items:
                return self._item_to_record(items[0])
            
            # If no active license, return the most recent one (for status checks)
            response = self._table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
                ExpressionAttributeValues={
                    ':pk': f'INSTANCE#{instance_id}',
                    ':sk_prefix': 'LICENSE#',
                },
                ScanIndexForward=False,
                Limit=1,
            )
            
            items = response.get('Items', [])
            if not items:
                return None
            
            return self._item_to_record(items[0])
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ResourceNotFoundException':
                # Table doesn't exist - treat as no license
                logger.warning(f"License table not found: {self._table_name}")
                return None
            logger.error(f"Failed to get license: {e}")
            raise LicenseRepositoryError(f"Failed to get license: {e}")
    
    async def get_license_by_id(self, instance_id: str, license_id: str) -> Optional[LicenseRecord]:
        """
        Get a specific license by ID.
        
        Args:
            instance_id: Instance identifier
            license_id: License identifier
            
        Returns:
            License record or None if not found
        """
        try:
            response = self._table.get_item(
                Key={
                    'PK': f'INSTANCE#{instance_id}',
                    'SK': f'LICENSE#{license_id}',
                }
            )
            
            item = response.get('Item')
            if not item:
                return None
            
            return self._item_to_record(item)
        except ClientError as e:
            logger.error(f"Failed to get license by ID: {e}")
            raise LicenseRepositoryError(f"Failed to get license: {e}")
    
    async def update_license_status(
        self,
        instance_id: str,
        license_id: str,
        status: LicenseStatus,
        deactivated_at: Optional[datetime] = None,
        grace_period_ends_at: Optional[datetime] = None,
    ) -> Optional[LicenseRecord]:
        """
        Update license status.
        
        Args:
            instance_id: Instance identifier
            license_id: License identifier
            status: New status
            deactivated_at: Deactivation timestamp (if deactivating)
            grace_period_ends_at: Grace period end (if entering grace period)
            
        Returns:
            Updated license record
        """
        try:
            update_expr = 'SET #status = :status'
            expr_names = {'#status': 'status'}
            expr_values = {':status': status.value}
            
            if deactivated_at:
                update_expr += ', deactivated_at = :deactivated_at'
                expr_values[':deactivated_at'] = deactivated_at.isoformat()
            
            if grace_period_ends_at:
                update_expr += ', grace_period_ends_at = :grace_period_ends_at'
                expr_values[':grace_period_ends_at'] = grace_period_ends_at.isoformat()
            
            response = self._table.update_item(
                Key={
                    'PK': f'INSTANCE#{instance_id}',
                    'SK': f'LICENSE#{license_id}',
                },
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ReturnValues='ALL_NEW',
            )
            
            return self._item_to_record(response.get('Attributes', {}))
        except ClientError as e:
            logger.error(f"Failed to update license status: {e}")
            raise LicenseRepositoryError(f"Failed to update license: {e}")
    
    async def update_license_expiration(
        self,
        instance_id: str,
        license_id: str,
        expires_at: datetime,
        tier: Optional[LicenseTier] = None,
        enabled_features: Optional[List[str]] = None,
    ) -> Optional[LicenseRecord]:
        """
        Update license expiration (for renewal).
        
        Args:
            instance_id: Instance identifier
            license_id: License identifier
            expires_at: New expiration date
            tier: New tier (if changed)
            enabled_features: New features (if changed)
            
        Returns:
            Updated license record
        """
        try:
            update_expr = 'SET expires_at = :expires_at, #status = :status'
            expr_names = {'#status': 'status'}
            expr_values = {
                ':expires_at': expires_at.isoformat(),
                ':status': LicenseStatus.ACTIVE.value,
            }
            
            if tier:
                update_expr += ', tier = :tier'
                expr_values[':tier'] = tier.value
            
            if enabled_features:
                update_expr += ', enabled_features = :features'
                expr_values[':features'] = enabled_features
            
            # Clear grace period on renewal
            update_expr += ' REMOVE grace_period_ends_at, deactivated_at'
            
            response = self._table.update_item(
                Key={
                    'PK': f'INSTANCE#{instance_id}',
                    'SK': f'LICENSE#{license_id}',
                },
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ReturnValues='ALL_NEW',
            )
            
            return self._item_to_record(response.get('Attributes', {}))
        except ClientError as e:
            logger.error(f"Failed to update license expiration: {e}")
            raise LicenseRepositoryError(f"Failed to update license: {e}")
    
    async def get_licenses_by_status(self, status: LicenseStatus, limit: int = 100) -> List[LicenseRecord]:
        """
        Get licenses by status using GSI.
        
        Args:
            status: License status to filter by
            limit: Maximum results
            
        Returns:
            List of license records
        """
        try:
            response = self._table.query(
                IndexName='status-index',
                KeyConditionExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': status.value},
                Limit=limit,
            )
            
            return [self._item_to_record(item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"Failed to get licenses by status: {e}")
            raise LicenseRepositoryError(f"Failed to query licenses: {e}")
    
    async def get_licenses_by_holder(self, holder_id: str, limit: int = 100) -> List[LicenseRecord]:
        """
        Get licenses by holder ID using GSI.
        
        Args:
            holder_id: Holder identifier
            limit: Maximum results
            
        Returns:
            List of license records
        """
        try:
            response = self._table.query(
                IndexName='holder-index',
                KeyConditionExpression='holder_id = :holder_id',
                ExpressionAttributeValues={':holder_id': holder_id},
                Limit=limit,
            )
            
            return [self._item_to_record(item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"Failed to get licenses by holder: {e}")
            raise LicenseRepositoryError(f"Failed to query licenses: {e}")
    
    async def delete_license(self, instance_id: str, license_id: str) -> bool:
        """
        Delete a license record.
        
        Args:
            instance_id: Instance identifier
            license_id: License identifier
            
        Returns:
            True if deleted
        """
        try:
            self._table.delete_item(
                Key={
                    'PK': f'INSTANCE#{instance_id}',
                    'SK': f'LICENSE#{license_id}',
                }
            )
            logger.info(f"Deleted license: {license_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete license: {e}")
            raise LicenseRepositoryError(f"Failed to delete license: {e}")
    
    def _item_to_record(self, item: Dict[str, Any]) -> LicenseRecord:
        """Convert DynamoDB item to LicenseRecord."""
        # Parse datetime fields
        for field in ['issued_at', 'activated_at', 'expires_at', 'deactivated_at', 'grace_period_ends_at']:
            if item.get(field):
                item[field] = datetime.fromisoformat(item[field].replace('Z', '+00:00'))
        
        # Parse enum fields
        if item.get('tier'):
            item['tier'] = LicenseTier(item['tier'])
        if item.get('status'):
            item['status'] = LicenseStatus(item['status'])
        
        return LicenseRecord(**item)


class AuditRepository:
    """
    Repository for license audit log persistence in DynamoDB.
    """
    
    def __init__(self, table_name: Optional[str] = None):
        """
        Initialize repository with DynamoDB table.
        
        Args:
            table_name: Override table name (for testing)
        """
        self._table_name = table_name or get_license_audit_table_name()
        self._client = self._get_dynamodb_client()
        self._table = self._get_table()
    
    def _get_dynamodb_client(self):
        """Get DynamoDB resource with LocalStack support."""
        try:
            from src.config.localstack_config import get_localstack_config, is_localstack_enabled
            
            if is_localstack_enabled():
                config = get_localstack_config()
                return boto3.resource(
                    'dynamodb',
                    endpoint_url=config.endpoint_url,
                    region_name=config.region,
                    aws_access_key_id=config.access_key,
                    aws_secret_access_key=config.secret_key,
                )
        except ImportError:
            pass
        
        # Fallback: check for explicit endpoint URL
        endpoint_url = os.environ.get('DYNAMODB_ENDPOINT_URL') or os.environ.get('AWS_ENDPOINT_URL_DYNAMODB')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        if endpoint_url:
            return boto3.resource('dynamodb', endpoint_url=endpoint_url, region_name=region)
        return boto3.resource('dynamodb', region_name=region)
    
    def _get_table(self):
        """Get DynamoDB table reference."""
        return self._client.Table(self._table_name)
    
    async def save_audit_entry(self, entry: LicenseAuditEntry) -> LicenseAuditEntry:
        """
        Save an audit log entry.
        
        Args:
            entry: Audit entry to save
            
        Returns:
            Saved audit entry
        """
        try:
            item = entry.to_dynamo_item()
            self._table.put_item(Item=item)
            logger.debug(f"Saved audit entry: {entry.event_id}")
            return entry
        except ClientError as e:
            logger.error(f"Failed to save audit entry: {e}")
            raise LicenseRepositoryError(f"Failed to save audit entry: {e}")
    
    async def get_audit_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple:
        """
        Get audit logs with pagination.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum results per page
            offset: Number of items to skip
            
        Returns:
            Tuple of (entries, total_count)
        """
        try:
            # Determine partition keys to query based on date range
            if start_date and end_date:
                # Query specific months
                pks = self._get_month_partitions(start_date, end_date)
            else:
                # Query recent months (last 3)
                now = datetime.now(timezone.utc)
                pks = [f"AUDIT#{now.strftime('%Y-%m')}"]
                for i in range(1, 3):
                    prev = datetime(now.year, now.month - i if now.month > i else 12 - i + now.month, 1)
                    pks.append(f"AUDIT#{prev.strftime('%Y-%m')}")
            
            all_items = []
            for pk in pks:
                response = self._table.query(
                    KeyConditionExpression='PK = :pk',
                    ExpressionAttributeValues={':pk': pk},
                    ScanIndexForward=False,  # Most recent first
                )
                all_items.extend(response.get('Items', []))
            
            # Sort by timestamp descending
            all_items.sort(key=lambda x: x.get('SK', ''), reverse=True)
            
            total_count = len(all_items)
            
            # Apply pagination
            paginated = all_items[offset:offset + limit]
            
            entries = [self._item_to_entry(item) for item in paginated]
            
            return entries, total_count
        except ClientError as e:
            logger.error(f"Failed to get audit logs: {e}")
            raise LicenseRepositoryError(f"Failed to get audit logs: {e}")
    
    async def get_audit_logs_by_license(
        self,
        license_id: str,
        limit: int = 100,
    ) -> List[LicenseAuditEntry]:
        """
        Get audit logs for a specific license using GSI.
        
        Args:
            license_id: License identifier
            limit: Maximum results
            
        Returns:
            List of audit entries
        """
        try:
            response = self._table.query(
                IndexName='license-index',
                KeyConditionExpression='license_id = :license_id',
                ExpressionAttributeValues={':license_id': license_id},
                ScanIndexForward=False,
                Limit=limit,
            )
            
            return [self._item_to_entry(item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"Failed to get audit logs by license: {e}")
            raise LicenseRepositoryError(f"Failed to get audit logs: {e}")
    
    def _get_month_partitions(self, start: datetime, end: datetime) -> List[str]:
        """Get list of month partition keys between dates."""
        pks = []
        current = datetime(start.year, start.month, 1)
        end_month = datetime(end.year, end.month, 1)
        
        while current <= end_month:
            pks.append(f"AUDIT#{current.strftime('%Y-%m')}")
            # Move to next month
            if current.month == 12:
                current = datetime(current.year + 1, 1, 1)
            else:
                current = datetime(current.year, current.month + 1, 1)
        
        return pks
    
    def _item_to_entry(self, item: Dict[str, Any]) -> LicenseAuditEntry:
        """Convert DynamoDB item to LicenseAuditEntry."""
        # Parse datetime
        if item.get('timestamp'):
            item['timestamp'] = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
        
        # Parse enum
        if item.get('event_type'):
            item['event_type'] = LicenseEventType(item['event_type'])
        
        return LicenseAuditEntry(**item)
