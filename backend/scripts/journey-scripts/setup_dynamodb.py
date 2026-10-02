#!/usr/bin/env python3
# setup_dynamodb.py
import boto3
import sys
import os
import traceback
from datetime import datetime, timezone


def load_env_file():
    """Load environment variables from .env.local"""
    # Find project root (nexus-backend)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_file = os.path.join(project_root, '.env.local')
    
    if os.path.exists(env_file):
        print(f'📁 Loading environment from: {env_file}')
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Don't override existing env vars
                    if key not in os.environ:
                        os.environ[key] = value
        print(f'✅ Environment loaded: ENVIRONMENT={os.environ.get("ENVIRONMENT", "not set")}, AWS_REGION={os.environ.get("AWS_REGION", "not set")}')
    else:
        print(f'⚠️ No .env.local found at {env_file}')


# Load environment variables at module load time
load_env_file()


def print_with_flush(message):
    """Print message and flush stdout immediately (suppressed in MCP mode)"""
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


def get_table_name():
    """Get the DynamoDB table name from config or environment"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Try to get from config first
    try:
        from src.config.config_provider import get_config
        config = get_config()
        table_name = config.dynamodb_transformation_table
        print_with_flush(f'📋 Using table name from config: {table_name}')
        return table_name
    except Exception as e:
        print_with_flush(f'⚠️ Could not get table name from config: {e}')
    
    # Fallback to environment variable or default
    table_name = os.environ.get('DYNAMODB_TABLE', 'TransformationSystem')
    print_with_flush(f'📋 Using table name from env/default: {table_name}')
    return table_name


def get_aws_region():
    """Get AWS region from environment"""
    return os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or 'us-east-1'


def create_transformation_table():
    """Create the TransformationSystem DynamoDB table with Second Brain rules support"""
    print_with_flush('🔧 Starting DynamoDB table creation...')

    # Get table name from config
    table_name = get_table_name()
    region = get_aws_region()
    print_with_flush(f'🌍 Using AWS region: {region}')

    try:
        print_with_flush('🔗 Creating DynamoDB client...')
        
        # Import AWS client utilities
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from src.utils.aws_client_utils import create_aws_client
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Using role ARN: {role_arn}')
            dynamodb = create_aws_client('dynamodb', role_arn=role_arn, region_name=region)
        else:
            print_with_flush('🔑 Using default credential chain')
            dynamodb = boto3.client('dynamodb', region_name=region)
        
        print_with_flush('✅ DynamoDB client created successfully')
    except Exception as e:
        print_with_flush(f'❌ Failed to create DynamoDB client: {str(e)}')
        traceback.print_exc()
        return False

    # First, check if table already exists
    try:
        print_with_flush(f'🔍 Checking if {table_name} table exists...')
        response = dynamodb.describe_table(TableName=table_name)
        print_with_flush('✅ Table already exists and is ready!')
        print_with_flush(f'🕐 Table Status: {response["Table"]["TableStatus"]}')
        
        # Check if table supports Second Brain rules (has the right structure)
        gsi_names = [gsi["IndexName"] for gsi in response["Table"].get("GlobalSecondaryIndexes", [])]
        
        if "GSI1" in gsi_names:
            print_with_flush('✅ Table structure supports Second Brain rules')
        else:
            print_with_flush('⚠️  Table exists but may not support all Second Brain features')
        
        return True
        
    except dynamodb.exceptions.ResourceNotFoundException:
        print_with_flush('📋 Table does not exist, creating new table...')
        # Continue with table creation
        pass
    except Exception as e:
        print_with_flush(f'❌ Error checking table existence: {str(e)}')
        traceback.print_exc()
        return False

    table_definition = {
        'TableName': table_name,
        'AttributeDefinitions': [
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
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
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'StreamSpecification': {'StreamEnabled': True, 'StreamViewType': 'NEW_AND_OLD_IMAGES'},
        'Tags': [
            {'Key': 'Service', 'Value': 'TMF-ODA-Transformer'},
            {'Key': 'Component', 'Value': 'DataStore'},
            {'Key': 'Purpose', 'Value': 'TransformationJourneys'},
            {'Key': 'Features', 'Value': 'SecondBrainRules'},
            {'Key': 'Environment', 'Value': 'Production'},
        ],
    }

    try:
        print_with_flush('📋 Table definition prepared with Second Brain rules support...')
        response = dynamodb.create_table(**table_definition)
        print_with_flush(
            f'✅ Table creation initiated: {response["TableDescription"]["TableName"]}'
        )
        print_with_flush(f'🕐 Table Status: {response["TableDescription"]["TableStatus"]}')

        # Wait for table to be active
        print_with_flush('⏳ Waiting for table to become active...')
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print_with_flush('✅ Table is now active!')

        return True

    except dynamodb.exceptions.ResourceInUseException:
        print_with_flush('⚠️  Table already exists (from creation attempt)')
        return True
    except Exception as e:
        print_with_flush(f'❌ Error creating table: {str(e)}')
        traceback.print_exc()
        return False


def create_s3_buckets():
    """Create S3 buckets for logs and reports"""
    print_with_flush('🪣 Starting S3 bucket creation...')

    region = get_aws_region()
    print_with_flush(f'🌍 Using AWS region: {region}')

    try:
        print_with_flush('🔗 Creating S3 client...')
        
        # Import AWS client utilities  
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from src.utils.aws_client_utils import create_aws_client
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Using role ARN: {role_arn}')
            s3 = create_aws_client('s3', role_arn=role_arn, region_name=region)
        else:
            print_with_flush('🔑 Using default credential chain')
            s3 = boto3.client('s3', region_name=region)
        
        print_with_flush('✅ S3 client created successfully')
    except Exception as e:
        print_with_flush(f'❌ Failed to create S3 client: {str(e)}')
        traceback.print_exc()
        return False

    # Get environment for bucket naming
    env = os.environ.get('ENVIRONMENT', 'dev')
    bucket_names = [
        f'call-processing-{env}-journey-logs',
        f'call-processing-{env}-journey-reports'
    ]

    for bucket_name in bucket_names:
        try:
            print_with_flush(f'📦 Creating S3 bucket: {bucket_name}...')
            # For regions other than us-east-1, we need to specify LocationConstraint
            if region != 'us-east-1':
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            else:
                s3.create_bucket(Bucket=bucket_name)
            print_with_flush(f'✅ Created S3 bucket: {bucket_name}')
        except s3.exceptions.BucketAlreadyExists:
            print_with_flush(f'⚠️  S3 bucket already exists: {bucket_name}')
        except s3.exceptions.BucketAlreadyOwnedByYou:
            print_with_flush(f'⚠️  S3 bucket already owned by you: {bucket_name}')
        except Exception as e:
            print_with_flush(f'❌ Error creating bucket {bucket_name}: {str(e)}')
            traceback.print_exc()

    return True


def create_sample_second_brain_rules(journey_id):
    """Create sample Second Brain rules for the journey"""
    sample_rules = [
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'RULE#raw_analysis#000#rule-raw_analysis-sample-001',
            'EntityType': 'SecondBrainRule',
            'GSI1PK': f'JOURNEY#{journey_id}#RULES',
            'GSI1SK': 'raw_analysis#high#000',
            'CreatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'UpdatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'Data': {
                'ruleId': 'rule-raw_analysis-sample-001',
                'journeyId': journey_id,
                'stageId': 'raw_analysis',
                'title': 'Customer data should map to TMF629 Customer entity',
                'description': 'Tables containing customer information should be mapped to TMF629 Customer Management API',
                'type': 'field_mapping',
                'priority': 'high',
                'scope': 'global',
                'status': 'active',
                'context': {
                    'appliesTo': ['tables'],
                    'conditions': [
                        {
                            'field': 'table_name',
                            'operator': 'contains',
                            'value': ['customer', 'client', 'user']
                        }
                    ]
                },
                'content': {
                    'naturalLanguage': 'When analyzing customer-related tables, ensure they map to TMF629 Customer entity. Look for customer_id, customer_name, and customer_email fields.',
                    'jsonRule': {
                        'conditions': {
                            'table_patterns': ['*customer*', '*client*', '*user*'],
                            'field_indicators': ['customer_id', 'customer_name', 'customer_email']
                        },
                        'actions': {
                            'map_to_tmf': 'TMF629_Customer',
                            'validate_fields': ['id', 'name', 'email'],
                            'entity_type': 'customer'
                        }
                    }
                },
                'metadata': {
                    'createdBy': 'system',
                    'version': '1.0',
                    'tags': ['raw_analysis', 'field_mapping', 'high'],
                    'applicableStages': ['raw_analysis'],
                    'ruleEngine': 'second_brain_v1'
                }
            }
        },
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'RULE#raw_analysis#001#rule-raw_analysis-contextual-001',
            'EntityType': 'SecondBrainRule',
            'GSI1PK': f'JOURNEY#{journey_id}#RULES',
            'GSI1SK': 'raw_analysis#medium#001',
            'CreatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'UpdatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'Data': {
                'ruleId': 'rule-raw_analysis-contextual-001',
                'journeyId': journey_id,
                'stageId': 'raw_analysis',
                'title': 'Focus on core business entities first',
                'description': 'Prioritize identification of Customer, Product, Order, and Service entities during schema analysis',
                'type': 'contextual_recommendations',
                'priority': 'medium',
                'scope': 'global',
                'status': 'active',
                'context': {
                    'appliesTo': ['analysis_process'],
                    'conditions': []
                },
                'content': {
                    'naturalLanguage': 'During schema analysis, focus on identifying core business entities first: Customer, Product, Order, Service. These are the foundation for TMF mapping.',
                    'jsonRule': {
                        'priority_entities': ['customer', 'product', 'order', 'service'],
                        'analysis_order': ['entities', 'relationships', 'constraints'],
                        'focus_areas': ['primary_keys', 'foreign_keys']
                    }
                },
                'metadata': {
                    'createdBy': 'system',
                    'version': '1.0',
                    'tags': ['raw_analysis', 'contextual_recommendations', 'medium'],
                    'applicableStages': ['raw_analysis'],
                    'ruleEngine': 'second_brain_v1'
                }
            }
        },
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'RULE#stripped_schema#000#rule-stripped_schema-data-001',
            'EntityType': 'SecondBrainRule',
            'GSI1PK': f'JOURNEY#{journey_id}#RULES',
            'GSI1SK': 'stripped_schema#critical#000',
            'CreatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'UpdatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'Data': {
                'ruleId': 'rule-stripped_schema-data-001',
                'journeyId': journey_id,
                'stageId': 'stripped_schema',
                'title': 'Preserve TMF-relevant tables during stripping',
                'description': 'When creating stripped schema, preserve all tables relevant to TMF APIs',
                'type': 'data_interpretation',
                'priority': 'critical',
                'scope': 'global',
                'status': 'active',
                'context': {
                    'appliesTo': ['tables', 'schema_stripping'],
                    'conditions': []
                },
                'content': {
                    'naturalLanguage': 'During schema stripping, preserve tables related to Customer, Product, Order, Service entities. Remove audit, log, and temporary tables.',
                    'jsonRule': {
                        'preserve_patterns': ['*customer*', '*product*', '*order*', '*service*'],
                        'remove_patterns': ['*audit*', '*log*', '*temp*', '*backup*'],
                        'preserve_relationships': ['customer_product', 'customer_order', 'order_product']
                    }
                },
                'metadata': {
                    'createdBy': 'system',
                    'version': '1.0',
                    'tags': ['stripped_schema', 'data_interpretation', 'critical'],
                    'applicableStages': ['stripped_schema'],
                    'ruleEngine': 'second_brain_v1'
                }
            }
        }
    ]
    
    return sample_rules


def seed_sample_journey():
    """Create a sample transformation journey with Second Brain rules"""
    print_with_flush('🌱 Starting sample journey creation with Second Brain rules...')

    # Get table name from config
    table_name = get_table_name()
    region = get_aws_region()
    print_with_flush(f'🌍 Using AWS region: {region}')

    try:
        print_with_flush('🔗 Creating DynamoDB resource...')
        
        # Import AWS client utilities  
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from src.utils.aws_client_utils import create_aws_resource
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Using role ARN: {role_arn}')
            dynamodb = create_aws_resource('dynamodb', role_arn=role_arn, region_name=region)
        else:
            print_with_flush('🔑 Using default credential chain')
            dynamodb = boto3.resource('dynamodb', region_name=region)
        
        table = dynamodb.Table(table_name)
        print_with_flush('✅ DynamoDB resource created successfully')
    except Exception as e:
        print_with_flush(f'❌ Failed to create DynamoDB resource: {str(e)}')
        traceback.print_exc()
        return None

    journey_id = 'JRN-SAMPLE-001'
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    print_with_flush(f'📝 Creating sample journey with ID: {journey_id}')

    # 1. Journey Metadata with Second Brain configuration
    journey_item = {
        'PK': f'JOURNEY#{journey_id}',
        'SK': 'METADATA',
        'EntityType': 'Journey',
        'GSI1PK': 'JOURNEYS',
        'GSI1SK': timestamp,
        'CreatedAt': timestamp,
        'UpdatedAt': timestamp,
        'Data': {
            'journeyId': journey_id,
            'name': 'Sample Customer Management Transformation',
            'description': 'Example transformation for testing with Second Brain AI assistance',
            'status': 'pending',
            'createdBy': 'system',
            'priority': 'medium',
            'odaComponentType': 'customer-management',
            'source': {
                'type': 'schema-based',
                'schemaId': 'schema-sample-001',
                'schemaName': 'Sample Customer DB',
                'schemaVersion': '1.0.0',
            },
            'configuration': {
                'timeout': 300,
                'maxDepth': 3,
                'tmfSpecVersion': '4.0.0',
                'outputFormat': 'json',
                'retryAttempts': 3,
                'secondBrainEnabled': True,
                'ruleEngineVersion': 'v1.0',
            },
            'currentStageIndex': 0,
            'currentStageId': 'raw_analysis',
            'overallProgress': 0,
            'currentJobs': {},
            'aggregates': {
                'totalJobs': 0,
                'completedJobs': 0,
                'failedJobs': 0,
                'totalExecutionTime': '0m',
                'totalLogs': 0,
                'totalErrors': 0,
                'totalWarnings': 0,
                'totalRules': 3,
                'activeRules': 3,
            },
            'stageSummary': {
                'raw_analysis': {'totalExecutions': 0, 'lastStatus': 'pending', 'rulesCount': 2},
                'stripped_schema': {'totalExecutions': 0, 'lastStatus': 'pending', 'rulesCount': 1},
                'tmf_mapping': {'totalExecutions': 0, 'lastStatus': 'pending', 'rulesCount': 0},
            },
            'secondBrainConfig': {
                'enabled': True,
                'ruleTypes': ['field_mapping', 'contextual_recommendations', 'data_interpretation', 'validation_rules'],
                'priorityLevels': ['low', 'medium', 'high', 'critical'],
                'scopes': ['global', 'project', 'stage'],
                'defaultScope': 'global',
                'autoApplyRules': True,
                'customRulesEnabled': True,
            },
        },
    }

    # 2. Stage Definitions with Second Brain integration
    stages = [
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'STAGE#00#raw_analysis',
            'EntityType': 'StageDefinition',
            'GSI1PK': f'JOURNEY#{journey_id}#STAGES',
            'GSI1SK': '00',
            'Data': {
                'stageId': 'raw_analysis',
                'name': 'Raw Input Analysis',
                'description': 'Analyze the raw customer database schema with AI guidance',
                'order': 0,
                'canSkip': False,
                'estimatedDuration': '10m',
                'status': 'pending',
                'secondBrainEnabled': True,
                'ruleTypes': ['field_mapping', 'contextual_recommendations', 'data_interpretation'],
                'steps': [
                    {
                        'id': 'schema_parsing',
                        'name': 'Schema File Parsing',
                        'description': 'Parse SQL schema files',
                        'order': 0,
                        'estimatedDuration': '3m',
                        'aiAssisted': True,
                        'applicableRules': ['field_mapping', 'contextual_recommendations'],
                    },
                    {
                        'id': 'relationship_discovery',
                        'name': 'Relationship Discovery',
                        'description': 'Identify table relationships',
                        'order': 1,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations'],
                    },
                    {
                        'id': 'data_type_analysis',
                        'name': 'Data Type Analysis',
                        'description': 'Analyze column data types',
                        'order': 2,
                        'estimatedDuration': '3m',
                        'aiAssisted': True,
                        'applicableRules': ['data_interpretation'],
                    },
                ],
            },
        },
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'STAGE#01#stripped_schema',
            'EntityType': 'StageDefinition',
            'GSI1PK': f'JOURNEY#{journey_id}#STAGES',
            'GSI1SK': '01',
            'Data': {
                'stageId': 'stripped_schema',
                'name': 'Create Stripped Schema',
                'description': 'Create TMF-focused simplified schema with AI assistance',
                'order': 1,
                'canSkip': False,
                'estimatedDuration': '8m',
                'status': 'pending',
                'secondBrainEnabled': True,
                'ruleTypes': ['data_interpretation', 'field_mapping'],
                'steps': [
                    {
                        'id': 'tmf_relevance_filtering',
                        'name': 'TMF Relevance Filtering',
                        'description': 'Filter tables for TMF relevance',
                        'order': 0,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['data_interpretation'],
                    },
                    {
                        'id': 'simplified_schema_creation',
                        'name': 'Simplified Schema Creation',
                        'description': 'Generate simplified schema',
                        'order': 1,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['field_mapping'],
                    },
                ],
            },
        },
    ]

    # 3. Create sample Second Brain rules
    sample_rules = create_sample_second_brain_rules(journey_id)

    try:
        # Insert journey
        print_with_flush('💾 Inserting journey metadata...')
        table.put_item(Item=journey_item)
        print_with_flush(f'✅ Created sample journey: {journey_id}')

        # Insert stages
        print_with_flush('📋 Inserting stage definitions...')
        for stage in stages:
            table.put_item(Item=stage)
            stage_name = stage["Data"]["name"]
            step_count = len(stage["Data"]["steps"])
            ai_steps = sum(1 for step in stage["Data"]["steps"] if step.get("aiAssisted", False))
            print_with_flush(f'✅ Created stage: {stage_name} ({step_count} steps, {ai_steps} AI-assisted)')

        # Insert sample Second Brain rules
        print_with_flush('🧠 Inserting sample Second Brain rules...')
        for rule in sample_rules:
            table.put_item(Item=rule)
        
        rules_by_type = {}
        for rule in sample_rules:
            rule_type = rule['Data']['type']
            if rule_type not in rules_by_type:
                rules_by_type[rule_type] = 0
            rules_by_type[rule_type] += 1
        
        print_with_flush(f'✅ Created {len(sample_rules)} sample Second Brain rules:')
        for rule_type, count in rules_by_type.items():
            print_with_flush(f'   • {rule_type}: {count} rules')

        return journey_id

    except Exception as e:
        print_with_flush(f'❌ Error creating sample data: {str(e)}')
        traceback.print_exc()
        return None


def main():
    """Main function with comprehensive error handling"""
    print_with_flush('🚀 Setting up Transformation System Infrastructure with Second Brain...')
    print_with_flush('=' * 60)

    # Test AWS credentials and region
    try:
        print_with_flush('🔐 Testing AWS credentials...')
        
        # Import AWS client utilities  
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

        # Get current region
        session = boto3.Session()
        region = session.region_name
        print_with_flush(f'✅ AWS Region: {region}')

    except Exception as e:
        print_with_flush(f'❌ AWS authentication failed: {str(e)}')
        traceback.print_exc()
        return False

    print_with_flush('=' * 60)

    # Create DynamoDB table
    print_with_flush('🗄️  Step 1: Creating DynamoDB table...')
    if create_transformation_table():
        print_with_flush('✅ DynamoDB table setup complete')
    else:
        print_with_flush('❌ DynamoDB table setup failed')
        return False

    print_with_flush('=' * 60)

    # Create S3 buckets
    print_with_flush('🪣 Step 2: Creating S3 buckets...')
    if create_s3_buckets():
        print_with_flush('✅ S3 buckets setup complete')
    else:
        print_with_flush('❌ S3 buckets setup failed')
        return False

    print_with_flush('=' * 60)

    # Create sample journey
    print_with_flush('🌱 Step 3: Creating sample journey with Second Brain...')
    journey_id = seed_sample_journey()
    if journey_id:
        print_with_flush(f'✅ Sample journey created: {journey_id}')
    else:
        print_with_flush('❌ Sample journey creation failed')
        return False

    print_with_flush('=' * 60)
    print_with_flush('🎉 Infrastructure setup complete with Second Brain!')
    print_with_flush('🧠 Features enabled:')
    print_with_flush('   • JSON-based rules system')
    print_with_flush('   • AI-assisted stage processing')
    print_with_flush('   • Contextual recommendations')
    print_with_flush('   • Field mapping intelligence')
    print_with_flush('   • Data interpretation guidance')
    print_with_flush('   • Validation rules automation')
    print_with_flush('=' * 60)

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_with_flush('\n⚠️  Setup interrupted by user')
        sys.exit(1)
    except Exception as e:
        print_with_flush(f'\n❌ Unexpected error: {str(e)}')
        traceback.print_exc()
        sys.exit(1)
