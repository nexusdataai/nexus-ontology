#!/usr/bin/env python3
"""
Update Raw Analysis Stage to Include All 5 Steps

This script updates the raw_analysis stage definition in DynamoDB to include
all 5 steps as shown in the UI design.
"""

import boto3
import sys
import traceback
from datetime import datetime
from decimal import Decimal


def print_with_flush(message):
    """Print message and flush stdout immediately"""
    print(message)
    sys.stdout.flush()


def update_raw_analysis_stage():
    """Update the raw_analysis stage definition with all 5 steps"""
    print_with_flush('🔧 Starting Raw Analysis stage update...')

    try:
        print_with_flush('🔗 Creating DynamoDB resource...')
        
        # Get table name from config provider
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        try:
            from src.config.config_provider import get_config
            config = get_config()
            table_name = config.dynamodb_transformation_table
            print_with_flush(f'📋 Using table from config: {table_name}')
        except Exception:
            table_name = os.environ.get('DYNAMODB_TABLE', 'TransformationSystem')
            print_with_flush(f'📋 Using table from env/default: {table_name}')
        
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        print_with_flush('✅ DynamoDB resource created successfully')
    except Exception as e:
        print_with_flush(f'❌ Failed to create DynamoDB resource: {str(e)}')
        traceback.print_exc()
        return False

    journey_id = 'JRN-SAMPLE-001'
    timestamp = datetime.utcnow().isoformat() + 'Z'

    print_with_flush(f'📝 Updating raw_analysis stage for journey: {journey_id}')

    # Updated stage definition with all 5 steps
    updated_stage = {
        'PK': f'JOURNEY#{journey_id}',
        'SK': 'STAGE#00#raw_analysis',
        'EntityType': 'StageDefinition',
        'GSI1PK': f'JOURNEY#{journey_id}#STAGES',
        'GSI1SK': '00',
        'UpdatedAt': timestamp,
        'Data': {
            'stageId': 'raw_analysis',
            'name': 'Raw Input Analysis',
            'description': 'Analyze the raw customer database schema to understand structure and relationships',
            'order': 0,
            'canSkip': False,
            'estimatedDuration': '15m',  # Updated duration for 5 steps
            'steps': [
                {
                    'id': 'schema_parsing',
                    'name': 'Schema File Parsing',
                    'description': 'Parse SQL schema files and extract table definitions',
                    'order': 0,
                    'estimatedDuration': '3m',
                },
                {
                    'id': 'relationship_discovery',
                    'name': 'Relationship Discovery',
                    'description': 'Identify foreign key relationships and table dependencies',
                    'order': 1,
                    'estimatedDuration': '3m',
                },
                {
                    'id': 'data_type_analysis',
                    'name': 'Data Type Analysis',
                    'description': 'Analyze column data types and constraints',
                    'order': 2,
                    'estimatedDuration': '3m',
                },
                {
                    'id': 'business_rules_extraction',
                    'name': 'Business Rules Extraction',
                    'description': 'Extract business rules from stored procedures and constraints',
                    'order': 3,
                    'estimatedDuration': '3m',
                },
                {
                    'id': 'complexity_assessment',
                    'name': 'Complexity Assessment',
                    'description': 'Assess schema complexity and identify potential challenges',
                    'order': 4,
                    'estimatedDuration': '3m',
                },
            ],
        },
    }

    try:
        # Update the stage definition
        print_with_flush('💾 Updating raw_analysis stage definition...')
        table.put_item(Item=updated_stage)
        print_with_flush('✅ Raw Analysis stage updated successfully')

        # Verify the update
        print_with_flush('🔍 Verifying stage update...')
        response = table.get_item(
            Key={
                'PK': f'JOURNEY#{journey_id}',
                'SK': 'STAGE#00#raw_analysis'
            }
        )
        
        if 'Item' in response:
            steps = response['Item']['Data']['steps']
            print_with_flush(f'✅ Verified: Stage now has {len(steps)} steps:')
            for i, step in enumerate(steps, 1):
                print_with_flush(f'   {i}. {step["name"]} - {step["description"]}')
        else:
            print_with_flush('❌ Failed to verify stage update')
            return False

        return True

    except Exception as e:
        print_with_flush(f'❌ Error updating stage: {str(e)}')
        traceback.print_exc()
        return False


def main():
    """Main function with comprehensive error handling"""
    print_with_flush('🚀 Updating Raw Analysis Stage Definition...')
    print_with_flush('=' * 60)

    # Test AWS credentials and region
    try:
        print_with_flush('🔐 Testing AWS credentials...')
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print_with_flush(f'✅ AWS Identity: {identity["Arn"]}')

        # Get current region
        session = boto3.Session()
        region = session.region_name
        print_with_flush(f'✅ AWS Region: {region}')

    except Exception as e:
        print_with_flush(f'❌ AWS authentication failed: {str(e)}')
        traceback.print_exc()
        return False

    print_with_flush('=' * 60)

    # Update raw_analysis stage
    print_with_flush('🔧 Updating Raw Analysis stage...')
    if update_raw_analysis_stage():
        print_with_flush('✅ Raw Analysis stage update complete')
    else:
        print_with_flush('❌ Raw Analysis stage update failed')
        return False

    print_with_flush('=' * 60)
    print_with_flush('🎉 Stage update complete!')
    print_with_flush('=' * 60)

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_with_flush('\n⚠️  Update interrupted by user')
        sys.exit(1)
    except Exception as e:
        print_with_flush(f'\n❌ Unexpected error: {str(e)}')
        traceback.print_exc()
        sys.exit(1) 