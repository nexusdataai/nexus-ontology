#!/usr/bin/env python3
"""
Delete TMF ODA Transformation Journey

This script completely removes a transformation journey and all associated data:
- Journey metadata
- Stage definitions  
- Job executions
- S3 logs and reports
- All related DynamoDB entries

Use with caution - this operation is irreversible!
"""

import boto3
import sys
import traceback
import argparse
from datetime import datetime


def print_with_flush(message):
    """Print message and flush stdout immediately"""
    print(message)
    sys.stdout.flush()


def confirm_deletion(journey_id, journey_name=None):
    """Confirm deletion with user"""
    print_with_flush('⚠️  DANGER: This will permanently delete all data for this journey!')
    print_with_flush(f'🆔 Journey ID: {journey_id}')
    if journey_name:
        print_with_flush(f'📝 Journey Name: {journey_name}')
    print_with_flush('')
    print_with_flush('This includes:')
    print_with_flush('  • Journey metadata and configuration')
    print_with_flush('  • All stage definitions')
    print_with_flush('  • All job execution records')
    print_with_flush('  • All S3 logs and reports')
    print_with_flush('  • All related DynamoDB entries')
    print_with_flush('')
    
    response = input('Type "DELETE" (in capitals) to confirm deletion: ')
    return response == 'DELETE'


def get_journey_info(table, journey_id):
    """Get journey information before deletion"""
    try:
        print_with_flush(f'🔍 Retrieving journey information for: {journey_id}')
        
        # Get journey metadata
        response = table.get_item(
            Key={'PK': f'JOURNEY#{journey_id}', 'SK': 'METADATA'}
        )
        
        if 'Item' not in response:
            print_with_flush(f'❌ Journey {journey_id} not found')
            return None
            
        journey_data = response['Item']['Data']
        
        print_with_flush(f'✅ Found journey: {journey_data.get("name", "Unnamed")}')
        print_with_flush(f'   Status: {journey_data.get("status", "unknown")}')
        print_with_flush(f'   Created: {journey_data.get("createdAt", "unknown")}')
        print_with_flush(f'   Progress: {journey_data.get("overallProgress", 0)}%')
        
        return journey_data
        
    except Exception as e:
        print_with_flush(f'❌ Error retrieving journey info: {str(e)}')
        return None


def delete_journey_items(table, journey_id):
    """Delete all DynamoDB items for a journey"""
    print_with_flush(f'🗑️  Deleting DynamoDB items for journey: {journey_id}')
    
    deleted_count = 0
    
    try:
        # Query all items for this journey
        response = table.query(
            KeyConditionExpression='PK = :pk',
            ExpressionAttributeValues={':pk': f'JOURNEY#{journey_id}'}
        )
        
        items = response['Items']
        print_with_flush(f'📊 Found {len(items)} items to delete')
        
        # Delete items in batches
        for item in items:
            pk = item['PK']
            sk = item['SK']
            entity_type = item.get('EntityType', 'Unknown')
            
            try:
                table.delete_item(Key={'PK': pk, 'SK': sk})
                deleted_count += 1
                print_with_flush(f'   ✅ Deleted {entity_type}: {sk}')
                
            except Exception as e:
                print_with_flush(f'   ❌ Failed to delete {entity_type} {sk}: {str(e)}')
        
        print_with_flush(f'✅ Deleted {deleted_count} DynamoDB items')
        return deleted_count
        
    except Exception as e:
        print_with_flush(f'❌ Error deleting DynamoDB items: {str(e)}')
        return 0


def delete_s3_logs_and_reports(s3_client, journey_id):
    """Delete S3 logs and reports for a journey"""
    print_with_flush(f'🪣 Deleting S3 logs and reports for journey: {journey_id}')
    
    buckets_to_clean = [
        ('transformation-journey-logs', f'journeys/{journey_id}/'),
        ('transformation-journey-reports', f'journeys/{journey_id}/')
    ]
    
    total_deleted = 0
    
    for bucket_name, prefix in buckets_to_clean:
        try:
            print_with_flush(f'   🔍 Checking bucket: {bucket_name} with prefix: {prefix}')
            
            # List objects with the journey prefix
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                print_with_flush(f'   ℹ️  No objects found in {bucket_name} with prefix {prefix}')
                continue
                
            objects = response['Contents']
            print_with_flush(f'   📊 Found {len(objects)} objects to delete in {bucket_name}')
            
            # Delete objects in batches (max 1000 per batch)
            batch_size = 1000
            for i in range(0, len(objects), batch_size):
                batch = objects[i:i + batch_size]
                delete_keys = [{'Key': obj['Key']} for obj in batch]
                
                s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': delete_keys}
                )
                
                total_deleted += len(delete_keys)
                print_with_flush(f'   ✅ Deleted {len(delete_keys)} objects from {bucket_name}')
                
        except s3_client.exceptions.NoSuchBucket:
            print_with_flush(f'   ⚠️  Bucket {bucket_name} does not exist')
        except Exception as e:
            print_with_flush(f'   ❌ Error cleaning bucket {bucket_name}: {str(e)}')
    
    print_with_flush(f'✅ Deleted {total_deleted} S3 objects total')
    return total_deleted


def delete_transformation_journey(journey_id, force=False):
    """Delete a complete transformation journey"""
    print_with_flush(f'🚀 Starting deletion of transformation journey: {journey_id}')
    print_with_flush('=' * 60)

    try:
        print_with_flush('🔗 Creating AWS clients...')
        
        # Import AWS client utilities  
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from src.utils.aws_client_utils import create_aws_resource, create_aws_client
        
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
            s3 = create_aws_client('s3', role_arn=role_arn)
        else:
            print_with_flush('🔑 Using default credential chain')
            dynamodb = boto3.resource('dynamodb')
            s3 = boto3.client('s3')
        
        table = dynamodb.Table(table_name)
        print_with_flush('✅ AWS clients created successfully')
        
    except Exception as e:
        print_with_flush(f'❌ Failed to create AWS clients: {str(e)}')
        traceback.print_exc()
        return False

    print_with_flush('=' * 60)

    # Get journey information
    journey_info = get_journey_info(table, journey_id)
    if not journey_info:
        return False

    print_with_flush('=' * 60)

    # Confirm deletion unless force flag is used
    if not force:
        if not confirm_deletion(journey_id, journey_info.get('name')):
            print_with_flush('❌ Deletion cancelled by user')
            return False

    print_with_flush('=' * 60)

    # Track deletion statistics
    deletion_stats = {
        'dynamodb_items': 0,
        's3_objects': 0,
        'start_time': datetime.utcnow(),
        'errors': []
    }

    try:
        # Delete DynamoDB items
        print_with_flush('🗑️  Phase 1: Deleting DynamoDB items...')
        deletion_stats['dynamodb_items'] = delete_journey_items(table, journey_id)
        
        print_with_flush('=' * 60)
        
        # Delete S3 objects
        print_with_flush('🪣 Phase 2: Deleting S3 logs and reports...')
        deletion_stats['s3_objects'] = delete_s3_logs_and_reports(s3, journey_id)
        
        print_with_flush('=' * 60)
        
        # Calculate total time
        end_time = datetime.utcnow()
        duration = (end_time - deletion_stats['start_time']).total_seconds()
        
        # Summary
        print_with_flush('🎉 Journey deletion completed successfully!')
        print_with_flush(f'📊 Deletion Summary:')
        print_with_flush(f'   🆔 Journey ID: {journey_id}')
        print_with_flush(f'   📝 Journey Name: {journey_info.get("name", "Unknown")}')
        print_with_flush(f'   🗄️  DynamoDB items deleted: {deletion_stats["dynamodb_items"]}')
        print_with_flush(f'   🪣 S3 objects deleted: {deletion_stats["s3_objects"]}')
        print_with_flush(f'   ⏱️  Total time: {duration:.2f} seconds')
        print_with_flush('')
        print_with_flush('✅ All data for this journey has been permanently removed')
        
        return True
        
    except Exception as e:
        print_with_flush(f'❌ Error during journey deletion: {str(e)}')
        traceback.print_exc()
        return False


def main():
    """Main function with command line interface"""
    print_with_flush('🗑️  TMF ODA Transformation Journey Deletion Tool')
    print_with_flush('=' * 60)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Delete a TMF ODA transformation journey')
    parser.add_argument('journey_id', type=str, help='Journey ID to delete (e.g., JRN-SAMPLE-001)')
    parser.add_argument('--force', action='store_true', 
                       help='Skip confirmation prompt (use with caution!)')
    parser.add_argument('--list-first', action='store_true',
                       help='List all journeys first to help identify the correct ID')
    
    args = parser.parse_args()

    # List journeys if requested
    if args.list_first:
        try:
            print_with_flush('📋 Available journeys:')
            
            # Import AWS client utilities  
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            from src.utils.aws_client_utils import create_aws_resource
            
            # Get table name from config provider
            try:
                from src.config.config_provider import get_config
                config = get_config()
                table_name = config.dynamodb_transformation_table
            except Exception:
                table_name = os.environ.get('DYNAMODB_TABLE', 'TransformationSystem')
            
            role_arn = os.environ.get('AWS_ROLE_ARN')
            if role_arn:
                dynamodb = create_aws_resource('dynamodb', role_arn=role_arn)
            else:
                dynamodb = boto3.resource('dynamodb')
            
            table = dynamodb.Table(table_name)
            
            # Query all journeys
            response = table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :gsi1pk',
                ExpressionAttributeValues={':gsi1pk': 'JOURNEYS'},
                ScanIndexForward=False
            )
            
            if not response['Items']:
                print_with_flush('   No journeys found')
            else:
                for item in response['Items']:
                    journey_data = item['Data']
                    print_with_flush(f'   🆔 {journey_data["journeyId"]} - {journey_data.get("name", "Unnamed")} ({journey_data.get("status", "unknown")})')
            
            print_with_flush('=' * 60)
            
        except Exception as e:
            print_with_flush(f'❌ Error listing journeys: {str(e)}')

    # Test AWS credentials
    try:
        print_with_flush('🔐 Testing AWS credentials...')
        
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from src.utils.aws_client_utils import test_aws_credentials
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Testing credentials with role ARN: {role_arn}')
            identity = test_aws_credentials(role_arn=role_arn)
        else:
            print_with_flush('🔑 Testing credentials with default credential chain')
            identity = test_aws_credentials()
        
        print_with_flush(f'✅ AWS Identity: {identity["Arn"]}')
        print_with_flush(f'✅ AWS Account: {identity["Account"]}')

    except Exception as e:
        print_with_flush(f'❌ AWS authentication failed: {str(e)}')
        traceback.print_exc()
        return False

    print_with_flush('=' * 60)

    # Validate journey ID format
    journey_id = args.journey_id.upper()
    if not journey_id.startswith('JRN-'):
        print_with_flush(f'⚠️  Warning: Journey ID "{journey_id}" does not follow expected format (JRN-*)')
        response = input('Continue anyway? (y/N): ')
        if response.lower() != 'y':
            print_with_flush('❌ Deletion cancelled')
            return False

    # Perform deletion
    success = delete_transformation_journey(journey_id, force=args.force)
    
    if success:
        print_with_flush('=' * 60)
        print_with_flush('✅ Journey deletion completed successfully!')
        return True
    else:
        print_with_flush('❌ Journey deletion failed')
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_with_flush('\n⚠️  Deletion interrupted by user')
        sys.exit(1)
    except Exception as e:
        print_with_flush(f'\n❌ Unexpected error: {str(e)}')
        traceback.print_exc()
        sys.exit(1) 