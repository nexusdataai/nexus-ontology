#!/usr/bin/env python3
"""
Database utility functions for Capability Management scripts
Provides common database operations and helper functions
"""

import os
import boto3
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def get_table_name() -> str:
    """
    Get the DynamoDB table name from environment or use default
    
    Returns:
        Table name string
    """
    # Check environment variable first
    table_name = os.environ.get('TABLE_NAME')
    if table_name:
        return table_name
    
    # Use default table name for Business Capability System
    return 'BusinessCapability'


def get_dynamodb_resource():
    """
    Get DynamoDB resource with proper configuration
    
    Returns:
        boto3 DynamoDB resource
    """
    try:
        # Check for AWS region
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Check if running locally with credentials
        if os.environ.get('AWS_ACCESS_KEY_ID'):
            return boto3.resource('dynamodb', region_name=region)
        else:
            # Use default credentials chain
            return boto3.resource('dynamodb', region_name=region)
            
    except Exception as e:
        print(f"Error creating DynamoDB resource: {str(e)}")
        raise


def format_decimal(obj: Any) -> Any:
    """
    Format Decimal objects for JSON serialization
    
    Args:
        obj: Object to format
        
    Returns:
        Formatted object
    """
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    elif isinstance(obj, dict):
        return {k: format_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [format_decimal(item) for item in obj]
    else:
        return obj


def print_with_flush(message: str):
    """
    Print message with immediate flush
    
    Args:
        message: Message to print
    """
    print(message)
    sys.stdout.flush()


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO 8601 format
    
    Returns:
        Timestamp string
    """
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def check_auth() -> bool:
    """
    Check if authentication is available (placeholder)
    
    Returns:
        True if authenticated
    """
    # For testing, always return True
    # In production, implement proper authentication check
    return True


# Additional utility functions that might be needed

def convert_to_decimal(value: Any) -> Decimal:
    """
    Convert a value to Decimal for DynamoDB
    
    Args:
        value: Value to convert
        
    Returns:
        Decimal value
    """
    if isinstance(value, float):
        return Decimal(str(value))
    elif isinstance(value, int):
        return Decimal(value)
    elif isinstance(value, str):
        return Decimal(value)
    else:
        return value


def batch_write_items(table, items: list, batch_size: int = 25):
    """
    Write items to DynamoDB in batches
    
    Args:
        table: DynamoDB table resource
        items: List of items to write
        batch_size: Size of each batch (max 25 for DynamoDB)
    """
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    print_with_flush(f"✅ Wrote {len(items)} items to table")


def query_with_pagination(table, **kwargs):
    """
    Query DynamoDB with automatic pagination
    
    Args:
        table: DynamoDB table resource
        **kwargs: Query parameters
        
    Returns:
        List of all items
    """
    items = []
    
    response = table.query(**kwargs)
    items.extend(response.get('Items', []))
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        response = table.query(**kwargs)
        items.extend(response.get('Items', []))
    
    return items


# Mock auth_utils functions if needed
class MockAuthUtils:
    @staticmethod
    def check_auth():
        return True


# If auth_utils doesn't exist, use mock
try:
    from src.utils.auth_utils import check_auth
except ImportError:
    check_auth = MockAuthUtils.check_auth
