#!/usr/bin/env python3
"""
Setup Consolidated BusinessCapability DynamoDB Table
====================================================
Creates a single DynamoDB table for managing all business capability data:
- Business Capabilities (CAPABILITY#id / METADATA)
- Software Components (CAPABILITY#id / COMPONENT#id)
- Implementation Jobs (CAPABILITY#id / JOB#id)  
- Performance Metrics (CAPABILITY#id / METRIC#timestamp#id)

Following the single table design pattern similar to TransformationSystem.
"""

import boto3
import sys
import os
import traceback
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def print_with_flush(message):
    """Print message and flush stdout immediately"""
    # Suppress output when running in MCP stdio mode (stdin is not a tty)
    if sys.stdin.isatty():
        print(message)
        sys.stdout.flush()
    else:
        # In MCP mode, log to stderr without emojis to avoid JSON parsing issues
        import logging
        # Remove emojis for clean logging
        clean_message = message.encode('ascii', 'ignore').decode('ascii').strip()
        if clean_message:
            logging.info(clean_message)


def get_dynamodb_client():
    """Get DynamoDB client with proper authentication"""
    try:
        from src.utils.aws_client_utils import create_aws_client
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Using role ARN: {role_arn}')
            return create_aws_client('dynamodb', role_arn=role_arn)
        else:
            print_with_flush('🔑 Using default credential chain')
            return boto3.client('dynamodb')
    except ImportError:
        print_with_flush('⚠️  AWS utilities not found, using boto3 directly')
        return boto3.client('dynamodb')


def table_exists(dynamodb, table_name):
    """Check if a table exists"""
    try:
        response = dynamodb.describe_table(TableName=table_name)
        return response['Table']['TableStatus'] == 'ACTIVE'
    except dynamodb.exceptions.ResourceNotFoundException:
        return False
    except Exception as e:
        print_with_flush(f'❌ Error checking table {table_name}: {str(e)}')
        return False


def wait_for_table(dynamodb, table_name):
    """Wait for table to be active"""
    waiter = dynamodb.get_waiter('table_exists')
    print_with_flush(f'⏳ Waiting for {table_name} to be active...')
    try:
        waiter.wait(
            TableName=table_name,
            WaiterConfig={
                'Delay': 2,
                'MaxAttempts': 30
            }
        )
        print_with_flush(f'✅ Table {table_name} is active!')
        return True
    except Exception as e:
        print_with_flush(f'❌ Error waiting for table: {str(e)}')
        return False


def create_business_capability_table(dynamodb):
    """
    Create the consolidated BusinessCapability table
    
    This single table stores all capability-related data:
    - Capabilities: PK=CAPABILITY#<id>, SK=METADATA
    - Components: PK=CAPABILITY#<id>, SK=COMPONENT#<componentId>
    - Jobs: PK=CAPABILITY#<id>, SK=JOB#<jobId>
    - Metrics: PK=CAPABILITY#<id>, SK=METRIC#<timestamp>#<metricId>
    - Versions: PK=CAPABILITY#<id>, SK=VERSION#<timestamp>
    - Dependencies: PK=CAPABILITY#<id>, SK=DEPENDENCY#<targetCapabilityId>
    """
    table_name = 'BusinessCapability'
    print_with_flush(f'\n🔧 Creating consolidated {table_name} table...')
    
    if table_exists(dynamodb, table_name):
        print_with_flush(f'✅ Table {table_name} already exists!')
        return True
    
    try:
        table_definition = {
            'TableName': table_name,
            'AttributeDefinitions': [
                # Primary key attributes
                {'AttributeName': 'PK', 'AttributeType': 'S'},  # CAPABILITY#<capabilityId>
                {'AttributeName': 'SK', 'AttributeType': 'S'},  # Entity type identifier
                
                # GSI1 - For status and type queries
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},  # STATUS#<status>, TYPE#<type>
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},  # Sorting key (e.g., timestamp, priority)
                
                # GSI2 - For owner and assignee queries  
                {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},  # OWNER#<owner>, ASSIGNEE#<assignee>
                {'AttributeName': 'GSI2SK', 'AttributeType': 'S'},  # Additional sorting
                
                # GSI3 - For domain and component type queries
                {'AttributeName': 'GSI3PK', 'AttributeType': 'S'},  # DOMAIN#<domain>, COMPONENT_TYPE#<type>
                {'AttributeName': 'GSI3SK', 'AttributeType': 'S'},  # Additional sorting
                
                # GSI4 - For date-based queries (metrics, jobs)
                {'AttributeName': 'GSI4PK', 'AttributeType': 'S'},  # DATE#<yyyy-mm-dd>
                {'AttributeName': 'GSI4SK', 'AttributeType': 'S'},  # TIME#<timestamp>
            ],
            'KeySchema': [
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'},
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'GSI1',
                    'KeySchema': [
                        {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
                {
                    'IndexName': 'GSI2',
                    'KeySchema': [
                        {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
                {
                    'IndexName': 'GSI3',
                    'KeySchema': [
                        {'AttributeName': 'GSI3PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI3SK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
                {
                    'IndexName': 'GSI4',
                    'KeySchema': [
                        {'AttributeName': 'GSI4PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI4SK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'Tags': [
                {'Key': 'Environment', 'Value': os.environ.get('ENVIRONMENT', 'development')},
                {'Key': 'System', 'Value': 'BusinessCapability'},
                {'Key': 'TableDesign', 'Value': 'SingleTable'},
                {'Key': 'ManagedBy', 'Value': 'capability-manager'},
                {'Key': 'CreatedDate', 'Value': datetime.now(timezone.utc).isoformat()},
            ]
        }
        
        response = dynamodb.create_table(**table_definition)
        print_with_flush(f'📋 Table creation initiated: {response["TableDescription"]["TableArn"]}')
        
        # Wait for table to be active
        success = wait_for_table(dynamodb, table_name)
        
        if success:
            # Enable TTL on the table for metrics data
            try:
                dynamodb.update_time_to_live(
                    TableName=table_name,
                    TimeToLiveSpecification={
                        'Enabled': True,
                        'AttributeName': 'ttl'
                    }
                )
                print_with_flush(f'⏰ TTL enabled on {table_name} (for metrics retention)')
            except Exception as e:
                print_with_flush(f'⚠️  Could not enable TTL: {str(e)}')
        
        return success
        
    except Exception as e:
        print_with_flush(f'❌ Failed to create {table_name}: {str(e)}')
        traceback.print_exc()
        return False


def print_data_model_info():
    """Print information about the data model"""
    print_with_flush('\n' + '='*70)
    print_with_flush('📚 SINGLE TABLE DATA MODEL')
    print_with_flush('='*70)
    
    print_with_flush('\n📊 Entity Types and Access Patterns:\n')
    
    print_with_flush('1️⃣  Business Capabilities:')
    print_with_flush('   • PK: CAPABILITY#<capabilityId>')
    print_with_flush('   • SK: METADATA')
    print_with_flush('   • Data: Full capability details (name, description, status, etc.)')
    print_with_flush('   • GSI1: STATUS#<status> for status-based queries')
    print_with_flush('   • GSI3: DOMAIN#<businessDomain> for domain queries')
    
    print_with_flush('\n2️⃣  Components:')
    print_with_flush('   • PK: CAPABILITY#<capabilityId>')
    print_with_flush('   • SK: COMPONENT#<componentId>')
    print_with_flush('   • Data: Component details (type, version, config, etc.)')
    print_with_flush('   • GSI1: TYPE#<componentType> for type-based queries')
    print_with_flush('   • GSI3: COMPONENT_TYPE#<type> for component filtering')
    
    print_with_flush('\n3️⃣  Implementation Jobs:')
    print_with_flush('   • PK: CAPABILITY#<capabilityId>')
    print_with_flush('   • SK: JOB#<jobId>')
    print_with_flush('   • Data: Job details (title, status, assignee, etc.)')
    print_with_flush('   • GSI1: STATUS#<status> for job status queries')
    print_with_flush('   • GSI2: ASSIGNEE#<assignee> for assignment queries')
    print_with_flush('   • GSI4: DATE#<date> for time-based queries')
    
    print_with_flush('\n4️⃣  Performance Metrics:')
    print_with_flush('   • PK: CAPABILITY#<capabilityId>')
    print_with_flush('   • SK: METRIC#<timestamp>#<metricId>')
    print_with_flush('   • Data: Metric values and metadata')
    print_with_flush('   • GSI4: DATE#<date> for date range queries')
    print_with_flush('   • TTL: Auto-expire old metrics after retention period')
    
    print_with_flush('\n5️⃣  Version History:')
    print_with_flush('   • PK: CAPABILITY#<capabilityId>')
    print_with_flush('   • SK: VERSION#<timestamp>')
    print_with_flush('   • Data: Snapshot of capability at point in time')
    
    print_with_flush('\n6️⃣  Dependencies:')
    print_with_flush('   • PK: CAPABILITY#<capabilityId>')
    print_with_flush('   • SK: DEPENDENCY#<targetCapabilityId>')
    print_with_flush('   • Data: Dependency relationship details')
    
    print_with_flush('\n📈 Query Patterns Supported:')
    print_with_flush('   • Get all data for a capability (PK query)')
    print_with_flush('   • List all capabilities (GSI1 with PK=CAPABILITIES)')
    print_with_flush('   • Filter by status, type, domain (GSI queries)')
    print_with_flush('   • Find by owner/assignee (GSI2)')
    print_with_flush('   • Time-based queries for metrics/jobs (GSI4)')
    print_with_flush('   • Component dependency tracking')


def main():
    """Main function to create the consolidated BusinessCapability table"""
    print_with_flush('\n' + '='*70)
    print_with_flush('🚀 Business Capability System - Consolidated Table Setup')
    print_with_flush('='*70)
    
    try:
        # Get DynamoDB client
        print_with_flush('\n📋 Initializing DynamoDB client...')
        dynamodb = get_dynamodb_client()
        print_with_flush('✅ DynamoDB client initialized successfully')
        
        # Create the consolidated table
        success = create_business_capability_table(dynamodb)
        
        if success:
            # Print data model information
            print_data_model_info()
            
            print_with_flush('\n' + '='*70)
            print_with_flush('🎉 SUCCESS - Table created successfully!')
            print_with_flush('='*70)
            
            print_with_flush('\n📝 Next steps:')
            print_with_flush('   1. Update manage_capability.py to use the new single table')
            print_with_flush('   2. Migrate existing data from old tables (if any)')
            print_with_flush('   3. Update all scripts to use BusinessCapability table')
            print_with_flush('   4. Test with sample data using updated scripts')
            print_with_flush('\n💡 The single table design provides:')
            print_with_flush('   • Simplified data model with single source of truth')
            print_with_flush('   • Efficient queries across all entity types')
            print_with_flush('   • Reduced operational overhead')
            print_with_flush('   • Better transaction support')
            print_with_flush('   • Cost optimization through single table')
        else:
            print_with_flush('\n⚠️  Table creation failed. Please check the errors above.')
            return False
        
        return success
        
    except Exception as e:
        print_with_flush(f'\n❌ Fatal error during setup: {str(e)}')
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
