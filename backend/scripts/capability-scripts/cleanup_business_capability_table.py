#!/usr/bin/env python3
"""
Cleanup Business Capability Table
==================================
Removes all data from the consolidated BusinessCapability table.
This is a destructive operation and will delete ALL records.
"""

import boto3
import sys
import os
import time
from botocore.exceptions import ClientError

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def print_with_flush(message, end='\n'):
    """Print message and flush stdout immediately"""
    print(message, end=end)
    sys.stdout.flush()


def get_dynamodb_resource():
    """Get DynamoDB resource with proper authentication"""
    try:
        from src.utils.aws_client_utils import create_aws_resource
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Using role ARN: {role_arn}')
            return create_aws_resource('dynamodb', role_arn=role_arn)
        else:
            print_with_flush('🔑 Using default credential chain')
            return boto3.resource('dynamodb')
    except ImportError:
        print_with_flush('⚠️  AWS utilities not found, using boto3 directly')
        return boto3.resource('dynamodb')


def count_items(table):
    """Count total items in the table"""
    try:
        response = table.scan(Select='COUNT')
        count = response.get('Count', 0)
        
        # Handle pagination for large tables
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                Select='COUNT',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            count += response.get('Count', 0)
        
        return count
    except Exception as e:
        print_with_flush(f'❌ Error counting items: {str(e)}')
        return 0


def get_item_breakdown(table):
    """Get breakdown of items by entity type"""
    breakdown = {
        'capabilities': 0,
        'components': 0,
        'jobs': 0,
        'metrics': 0,
        'versions': 0,
        'dependencies': 0,
        'other': 0
    }
    
    try:
        response = table.scan(
            ProjectionExpression='PK, SK, EntityType',
            ReturnConsumedCapacity='NONE'
        )
        
        items = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression='PK, SK, EntityType',
                ExclusiveStartKey=response['LastEvaluatedKey'],
                ReturnConsumedCapacity='NONE'
            )
            items.extend(response.get('Items', []))
        
        # Categorize items
        for item in items:
            sk = item.get('SK', '')
            entity_type = item.get('EntityType', '')
            
            if sk == 'METADATA' or entity_type == 'Capability':
                breakdown['capabilities'] += 1
            elif sk.startswith('COMPONENT#'):
                breakdown['components'] += 1
            elif sk.startswith('JOB#'):
                breakdown['jobs'] += 1
            elif sk.startswith('METRIC#'):
                breakdown['metrics'] += 1
            elif sk.startswith('VERSION#'):
                breakdown['versions'] += 1
            elif sk.startswith('DEPENDENCY#'):
                breakdown['dependencies'] += 1
            else:
                breakdown['other'] += 1
        
        return breakdown
        
    except Exception as e:
        print_with_flush(f'⚠️  Could not get item breakdown: {str(e)}')
        return breakdown


def delete_all_items(table):
    """Delete all items from the table"""
    deleted_count = 0
    batch_count = 0
    
    try:
        print_with_flush('\n📊 Scanning table for deletion...')
        
        # Scan and delete in batches
        response = table.scan(
            ProjectionExpression='PK, SK',
            ReturnConsumedCapacity='NONE'
        )
        
        while True:
            items = response.get('Items', [])
            
            if not items:
                break
            
            batch_count += 1
            print_with_flush(f'  • Processing batch {batch_count} ({len(items)} items)...', end='')
            
            # Delete items in batch
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(
                        Key={
                            'PK': item['PK'],
                            'SK': item['SK']
                        }
                    )
                    deleted_count += 1
            
            print_with_flush(' ✅')
            
            # Check for more items
            if 'LastEvaluatedKey' in response:
                response = table.scan(
                    ProjectionExpression='PK, SK',
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                    ReturnConsumedCapacity='NONE'
                )
            else:
                break
        
        return deleted_count
        
    except Exception as e:
        print_with_flush(f'\n❌ Error during deletion: {str(e)}')
        return deleted_count


def cleanup_table(table_name='BusinessCapability', skip_confirmation=False):
    """
    Clean up the BusinessCapability table
    
    Args:
        table_name: Name of the table to clean
        skip_confirmation: If True, skip confirmation prompt
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get DynamoDB resource
        dynamodb = get_dynamodb_resource()
        
        # Check if table exists
        try:
            table = dynamodb.Table(table_name)
            table.load()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print_with_flush(f'❌ Table {table_name} does not exist')
                return False
            raise
        
        # Get current item count and breakdown
        print_with_flush(f'\n📊 Analyzing table: {table_name}')
        total_count = count_items(table)
        
        if total_count == 0:
            print_with_flush('✅ Table is already empty!')
            return True
        
        # Get item breakdown
        breakdown = get_item_breakdown(table)
        
        print_with_flush(f'\n📈 Current table contents:')
        print_with_flush(f'   • Total items: {total_count:,}')
        print_with_flush(f'   • Capabilities: {breakdown["capabilities"]:,}')
        print_with_flush(f'   • Components: {breakdown["components"]:,}')
        print_with_flush(f'   • Jobs: {breakdown["jobs"]:,}')
        print_with_flush(f'   • Metrics: {breakdown["metrics"]:,}')
        print_with_flush(f'   • Versions: {breakdown["versions"]:,}')
        print_with_flush(f'   • Dependencies: {breakdown["dependencies"]:,}')
        if breakdown["other"] > 0:
            print_with_flush(f'   • Other: {breakdown["other"]:,}')
        
        # Confirmation
        if not skip_confirmation:
            print_with_flush('\n⚠️  WARNING: This will DELETE ALL data from the table!')
            print_with_flush('    This action cannot be undone.')
            response = input('\n    Type "yes" to continue: ')
            if response.lower() != 'yes':
                print_with_flush('❌ Operation cancelled')
                return False
        
        # Start deletion
        print_with_flush(f'\n🗑️  Starting deletion of {total_count:,} items...')
        start_time = time.time()
        
        deleted_count = delete_all_items(table)
        
        elapsed_time = time.time() - start_time
        
        # Verify deletion
        remaining = count_items(table)
        
        print_with_flush('\n' + '='*60)
        print_with_flush('📊 CLEANUP SUMMARY')
        print_with_flush('='*60)
        print_with_flush(f'   • Items deleted: {deleted_count:,}')
        print_with_flush(f'   • Items remaining: {remaining:,}')
        print_with_flush(f'   • Time taken: {elapsed_time:.2f} seconds')
        
        if remaining == 0:
            print_with_flush('\n✅ Table successfully cleaned!')
            return True
        else:
            print_with_flush(f'\n⚠️  {remaining} items could not be deleted')
            return False
            
    except Exception as e:
        print_with_flush(f'\n❌ Fatal error: {str(e)}')
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to clean up the BusinessCapability table"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up BusinessCapability table')
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )
    parser.add_argument(
        '--table',
        default='BusinessCapability',
        help='Table name (default: BusinessCapability)'
    )
    
    args = parser.parse_args()
    
    print_with_flush('\n' + '='*60)
    print_with_flush('🧹 Business Capability Table Cleanup')
    print_with_flush('='*60)
    
    success = cleanup_table(args.table, args.yes)
    
    if success:
        print_with_flush('\n📝 Next steps:')
        print_with_flush('   • Run setup_business_capability_table.py to recreate table structure')
        print_with_flush('   • Run init_sample_capabilities.py to add sample data')
        print_with_flush('   • Use manage_capability.py to add new capabilities')
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
