#!/usr/bin/env python3
"""
Cleanup DynamoDB TransformationSystem Table
============================================
This script deletes ALL data from the TransformationSystem DynamoDB table.

WARNING: This operation is destructive and cannot be undone!
Use with caution, especially in production environments.

Usage:
    python3 cleanup_dynamodb_table.py
    python3 cleanup_dynamodb_table.py --yes  # Skip confirmation prompt
"""

import boto3
import sys
import os
import argparse
import traceback
from datetime import datetime


def print_with_flush(message, end='\n'):
    """Print message and flush stdout immediately"""
    print(message, end=end)
    sys.stdout.flush()


def get_table_stats(table):
    """Get statistics about the table before deletion"""
    try:
        print_with_flush('📊 Gathering table statistics...')
        
        # Get table description
        response = table.meta.client.describe_table(TableName='TransformationSystem')
        item_count = response['Table'].get('ItemCount', 0)
        table_size_bytes = response['Table'].get('TableSizeBytes', 0)
        table_size_mb = table_size_bytes / (1024 * 1024)
        
        print_with_flush(f'   • Approximate item count: {item_count:,}')
        print_with_flush(f'   • Table size: {table_size_mb:.2f} MB')
        
        return item_count
        
    except Exception as e:
        print_with_flush(f'⚠️  Could not retrieve exact stats: {str(e)}')
        return 0


def scan_all_items(table):
    """Scan and return all items from the table"""
    print_with_flush('🔍 Scanning table for all items...')
    
    items = []
    scan_kwargs = {}
    done = False
    scanned_count = 0
    
    while not done:
        try:
            response = table.scan(**scan_kwargs)
            items.extend(response.get('Items', []))
            scanned_count += response['ScannedCount']
            
            print_with_flush(f'   • Scanned {scanned_count} items...', end='\r')
            
            # Check if there are more items to scan
            if 'LastEvaluatedKey' in response:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            else:
                done = True
                
        except Exception as e:
            print_with_flush(f'\n❌ Error scanning table: {str(e)}')
            traceback.print_exc()
            return None
    
    print_with_flush(f'\n✅ Found {len(items)} items to delete')
    return items


def delete_items_batch(table, items):
    """Delete items in batches for efficiency"""
    if not items:
        print_with_flush('ℹ️  No items to delete')
        return True
    
    print_with_flush(f'🗑️  Deleting {len(items)} items in batches...')
    
    batch_size = 25  # DynamoDB batch write limit
    deleted_count = 0
    failed_count = 0
    
    try:
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Prepare batch delete requests
            with table.batch_writer() as batch_writer:
                for item in batch:
                    try:
                        batch_writer.delete_item(
                            Key={
                                'PK': item['PK'],
                                'SK': item['SK']
                            }
                        )
                        deleted_count += 1
                    except Exception as e:
                        print_with_flush(f'\n⚠️  Failed to delete item: {str(e)}')
                        failed_count += 1
            
            # Progress update
            progress_pct = (i + len(batch)) / len(items) * 100
            print_with_flush(
                f'   • Progress: {deleted_count}/{len(items)} ({progress_pct:.1f}%) - '
                f'Failed: {failed_count}',
                end='\r'
            )
        
        print_with_flush(f'\n✅ Deleted {deleted_count} items successfully')
        
        if failed_count > 0:
            print_with_flush(f'⚠️  Failed to delete {failed_count} items')
            return False
        
        return True
        
    except Exception as e:
        print_with_flush(f'\n❌ Error during batch deletion: {str(e)}')
        traceback.print_exc()
        return False


def analyze_items(items):
    """Analyze items and show breakdown by entity type"""
    if not items:
        return
    
    print_with_flush('\n📋 Data breakdown by entity type:')
    
    entity_types = {}
    journeys = set()
    
    for item in items:
        entity_type = item.get('EntityType', 'Unknown')
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        # Track unique journeys
        pk = item.get('PK', '')
        if pk.startswith('JOURNEY#'):
            journey_id = pk.replace('JOURNEY#', '')
            journeys.add(journey_id)
    
    for entity_type, count in sorted(entity_types.items()):
        print_with_flush(f'   • {entity_type}: {count} items')
    
    print_with_flush(f'\n🗂️  Total unique journeys: {len(journeys)}')
    if journeys:
        print_with_flush('   Journey IDs:')
        for journey_id in sorted(journeys):
            print_with_flush(f'      - {journey_id}')


def confirm_deletion(skip_confirmation=False):
    """Ask user to confirm the deletion"""
    if skip_confirmation:
        return True
    
    print_with_flush('\n⚠️  WARNING: This will delete ALL data from the TransformationSystem table!')
    print_with_flush('⚠️  This operation cannot be undone!')
    print_with_flush('')
    
    response = input('Type "DELETE ALL" to confirm (or anything else to cancel): ')
    
    if response.strip() == 'DELETE ALL':
        print_with_flush('✅ Confirmed. Proceeding with deletion...')
        return True
    else:
        print_with_flush('❌ Deletion cancelled')
        return False


def cleanup_table(skip_confirmation=False):
    """Main cleanup function"""
    print_with_flush('🧹 TransformationSystem Table Cleanup')
    print_with_flush('=' * 60)
    
    try:
        # Import AWS client utilities
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from src.utils.aws_client_utils import create_aws_resource
        
        # Create DynamoDB resource
        print_with_flush('🔗 Connecting to DynamoDB...')
        
        # Get table name from config provider
        try:
            from src.config.config_provider import get_config
            config = get_config()
            table_name = config.dynamodb_transformation_table
            print_with_flush(f'📋 Using table from config: {table_name}')
        except Exception:
            table_name = os.environ.get('DYNAMODB_TABLE', 'TransformationSystem')
            print_with_flush(f'📋 Using table from env/default: {table_name}')
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Using role ARN: {role_arn}')
            dynamodb = create_aws_resource('dynamodb', role_arn=role_arn)
        else:
            print_with_flush('🔑 Using default credential chain')
            # Check for AWS_PROFILE
            profile = os.environ.get('AWS_PROFILE')
            if profile:
                print_with_flush(f'🔑 Using AWS profile: {profile}')
            dynamodb = boto3.resource('dynamodb')
        
        table = dynamodb.Table(table_name)
        print_with_flush(f'✅ Connected to {table_name} table')
        
    except Exception as e:
        print_with_flush(f'❌ Failed to connect to DynamoDB: {str(e)}')
        traceback.print_exc()
        return False
    
    print_with_flush('=' * 60)
    
    # Get table stats
    get_table_stats(table)
    
    print_with_flush('=' * 60)
    
    # Scan all items
    items = scan_all_items(table)
    
    if items is None:
        return False
    
    if not items:
        print_with_flush('✅ Table is already empty. Nothing to delete.')
        return True
    
    # Analyze items
    analyze_items(items)
    
    print_with_flush('=' * 60)
    
    # Confirm deletion
    if not confirm_deletion(skip_confirmation):
        return False
    
    print_with_flush('=' * 60)
    
    # Delete all items
    start_time = datetime.now()
    success = delete_items_batch(table, items)
    end_time = datetime.now()
    
    duration = (end_time - start_time).total_seconds()
    
    print_with_flush('=' * 60)
    
    if success:
        print_with_flush(f'🎉 Cleanup complete!')
        print_with_flush(f'⏱️  Time taken: {duration:.2f} seconds')
        print_with_flush(f'📊 Items deleted: {len(items)}')
        
        if len(items) > 0:
            rate = len(items) / duration if duration > 0 else 0
            print_with_flush(f'⚡ Deletion rate: {rate:.1f} items/second')
        
        return True
    else:
        print_with_flush(f'⚠️  Cleanup completed with errors')
        return False


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Clean up all data from TransformationSystem DynamoDB table',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Interactive mode (with confirmation prompt)
  python3 cleanup_dynamodb_table.py
  
  # Non-interactive mode (skip confirmation)
  python3 cleanup_dynamodb_table.py --yes
  
  # With AWS profile
  AWS_PROFILE=external-access python3 cleanup_dynamodb_table.py
        '''
    )
    
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt and proceed with deletion'
    )
    
    args = parser.parse_args()
    
    try:
        success = cleanup_table(skip_confirmation=args.yes)
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print_with_flush('\n⚠️  Cleanup interrupted by user')
        sys.exit(1)
        
    except Exception as e:
        print_with_flush(f'\n❌ Unexpected error: {str(e)}')
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

