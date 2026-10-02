#!/usr/bin/env python3
"""
Migrate from Multiple Tables to Single BusinessCapability Table
================================================================
This script migrates data from the old multi-table structure to the 
new consolidated single-table design.

Old tables:
- BusinessCapabilitySystem
- CapabilityComponents  
- ImplementationJobs
- PerformanceMetrics

New table:
- BusinessCapability (single consolidated table)
"""

import boto3
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal
from botocore.exceptions import ClientError

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def print_with_flush(message):
    """Print message and flush stdout immediately"""
    print(message)
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


def table_exists(dynamodb, table_name):
    """Check if a table exists"""
    try:
        table = dynamodb.Table(table_name)
        table.load()
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise


def scan_table(table):
    """Scan entire table and return all items"""
    items = []
    try:
        response = table.scan()
        items.extend(response.get('Items', []))
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        return items
    except Exception as e:
        print_with_flush(f'❌ Error scanning table: {str(e)}')
        return []


def migrate_capabilities(old_table, new_table):
    """Migrate capabilities from BusinessCapabilitySystem to BusinessCapability"""
    print_with_flush('\n📦 Migrating Capabilities...')
    
    items = scan_table(old_table)
    migrated_count = 0
    
    with new_table.batch_writer() as batch:
        for item in items:
            # Keep the same structure, already follows single-table pattern
            batch.put_item(Item=item)
            migrated_count += 1
            
            if migrated_count % 25 == 0:
                print_with_flush(f'  • Migrated {migrated_count} capabilities...')
    
    print_with_flush(f'✅ Migrated {migrated_count} capability records')
    return migrated_count


def migrate_components(old_table, new_table):
    """Migrate components from CapabilityComponents to BusinessCapability"""
    print_with_flush('\n🔧 Migrating Components...')
    
    items = scan_table(old_table)
    migrated_count = 0
    
    with new_table.batch_writer() as batch:
        for item in items:
            # Components already use CAPABILITY#id / COMPONENT#id pattern
            # Just ensure EntityType is set
            if 'EntityType' not in item:
                item['EntityType'] = 'Component'
            
            batch.put_item(Item=item)
            migrated_count += 1
            
            if migrated_count % 25 == 0:
                print_with_flush(f'  • Migrated {migrated_count} components...')
    
    print_with_flush(f'✅ Migrated {migrated_count} component records')
    return migrated_count


def migrate_jobs(old_table, new_table):
    """Migrate jobs from ImplementationJobs to BusinessCapability"""
    print_with_flush('\n💼 Migrating Implementation Jobs...')
    
    items = scan_table(old_table)
    migrated_count = 0
    
    with new_table.batch_writer() as batch:
        for item in items:
            # Jobs already use CAPABILITY#id / JOB#id pattern
            # Just ensure EntityType is set
            if 'EntityType' not in item:
                item['EntityType'] = 'Job'
            
            batch.put_item(Item=item)
            migrated_count += 1
            
            if migrated_count % 25 == 0:
                print_with_flush(f'  • Migrated {migrated_count} jobs...')
    
    print_with_flush(f'✅ Migrated {migrated_count} job records')
    return migrated_count


def migrate_metrics(old_table, new_table):
    """Migrate metrics from PerformanceMetrics to BusinessCapability"""
    print_with_flush('\n📊 Migrating Performance Metrics...')
    
    items = scan_table(old_table)
    migrated_count = 0
    
    with new_table.batch_writer() as batch:
        for item in items:
            # Metrics already use CAPABILITY#id / METRIC#timestamp#id pattern
            # Just ensure EntityType is set
            if 'EntityType' not in item:
                item['EntityType'] = 'Metric'
            
            batch.put_item(Item=item)
            migrated_count += 1
            
            if migrated_count % 25 == 0:
                print_with_flush(f'  • Migrated {migrated_count} metrics...')
    
    print_with_flush(f'✅ Migrated {migrated_count} metric records')
    return migrated_count


def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate to single BusinessCapability table')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform dry run without actually migrating'
    )
    parser.add_argument(
        '--skip-confirmation',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    print_with_flush('\n' + '='*70)
    print_with_flush('🔄 Business Capability Table Migration')
    print_with_flush('='*70)
    
    try:
        # Get DynamoDB resource
        dynamodb = get_dynamodb_resource()
        
        # Define old and new table names
        old_tables = {
            'BusinessCapabilitySystem': 'capabilities',
            'CapabilityComponents': 'components',
            'ImplementationJobs': 'jobs',
            'PerformanceMetrics': 'metrics'
        }
        new_table_name = 'BusinessCapability'
        
        # Check which old tables exist
        existing_old_tables = {}
        for table_name, data_type in old_tables.items():
            if table_exists(dynamodb, table_name):
                existing_old_tables[table_name] = data_type
                print_with_flush(f'✅ Found old table: {table_name}')
            else:
                print_with_flush(f'⚠️  Old table not found: {table_name}')
        
        if not existing_old_tables:
            print_with_flush('\n❌ No old tables found to migrate from')
            return False
        
        # Check if new table exists
        if not table_exists(dynamodb, new_table_name):
            print_with_flush(f'\n❌ New table {new_table_name} does not exist')
            print_with_flush('   Run setup_business_capability_table.py first')
            return False
        
        print_with_flush(f'\n✅ Target table {new_table_name} exists')
        
        # Count items to migrate
        print_with_flush('\n📊 Analyzing data to migrate:')
        total_items = 0
        counts = {}
        
        for table_name, data_type in existing_old_tables.items():
            table = dynamodb.Table(table_name)
            items = scan_table(table)
            count = len(items)
            counts[table_name] = count
            total_items += count
            print_with_flush(f'   • {table_name}: {count:,} items')
        
        print_with_flush(f'\n   Total items to migrate: {total_items:,}')
        
        if args.dry_run:
            print_with_flush('\n🔍 DRY RUN - No data will be migrated')
            return True
        
        # Confirmation
        if not args.skip_confirmation:
            print_with_flush('\n⚠️  This will migrate all data to the new single table')
            response = input('   Type "yes" to continue: ')
            if response.lower() != 'yes':
                print_with_flush('❌ Migration cancelled')
                return False
        
        # Perform migration
        print_with_flush('\n🚀 Starting migration...')
        new_table = dynamodb.Table(new_table_name)
        
        migration_stats = {}
        
        # Migrate each table type
        if 'BusinessCapabilitySystem' in existing_old_tables:
            old_table = dynamodb.Table('BusinessCapabilitySystem')
            count = migrate_capabilities(old_table, new_table)
            migration_stats['capabilities'] = count
        
        if 'CapabilityComponents' in existing_old_tables:
            old_table = dynamodb.Table('CapabilityComponents')
            count = migrate_components(old_table, new_table)
            migration_stats['components'] = count
        
        if 'ImplementationJobs' in existing_old_tables:
            old_table = dynamodb.Table('ImplementationJobs')
            count = migrate_jobs(old_table, new_table)
            migration_stats['jobs'] = count
        
        if 'PerformanceMetrics' in existing_old_tables:
            old_table = dynamodb.Table('PerformanceMetrics')
            count = migrate_metrics(old_table, new_table)
            migration_stats['metrics'] = count
        
        # Print summary
        print_with_flush('\n' + '='*70)
        print_with_flush('📊 MIGRATION SUMMARY')
        print_with_flush('='*70)
        
        total_migrated = sum(migration_stats.values())
        for data_type, count in migration_stats.items():
            print_with_flush(f'   • {data_type.capitalize()}: {count:,} items')
        
        print_with_flush(f'\n   Total migrated: {total_migrated:,} items')
        
        if total_migrated == total_items:
            print_with_flush('\n✅ Migration completed successfully!')
            print_with_flush('\n📝 Next steps:')
            print_with_flush('   1. Verify data in new table using inspect script')
            print_with_flush('   2. Update all scripts to use BusinessCapability table')
            print_with_flush('   3. Test functionality with new table')
            print_with_flush('   4. When confident, delete old tables')
        else:
            print_with_flush(f'\n⚠️  Migration incomplete: {total_migrated}/{total_items} items migrated')
        
        return True
        
    except Exception as e:
        print_with_flush(f'\n❌ Fatal error: {str(e)}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
