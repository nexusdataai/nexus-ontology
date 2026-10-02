#!/usr/bin/env python3
"""
Manage TMF ODA Transformation Journey Metadata and Stages

This script provides comprehensive management of journey metadata and stage definitions:

Journey Management:
- Create new journeys
- Update journey metadata 
- Delete journeys
- List and filter journeys
- Clone journeys
- Enable/disable journeys

Stage Management:
- Add stages to journeys
- Update stage definitions
- Reorder stages
- Enable/disable stages
- Update stage steps
- Manage stage configurations
- Clone stages between journeys

Usage:
    # Journey operations
    python3 manage_journey_stages.py --action list-journeys
    python3 manage_journey_stages.py --action get-journey --journey-id JRN-12345
    python3 manage_journey_stages.py --action update-journey --journey-id JRN-12345 --journey-file metadata.json
    python3 manage_journey_stages.py --action delete-journey --journey-id JRN-12345
    
    # Stage operations
    python3 manage_journey_stages.py --action list-stages --journey-id JRN-12345
    python3 manage_journey_stages.py --action add-stage --journey-id JRN-12345 --stage-file stage.json
    python3 manage_journey_stages.py --action update-stage --journey-id JRN-12345 --stage-id raw_analysis --stage-file updated_stage.json
    python3 manage_journey_stages.py --action delete-stage --journey-id JRN-12345 --stage-id raw_analysis
    
    # Interactive mode
    python3 manage_journey_stages.py --action interactive
"""

import boto3
import sys
import traceback
import json
import uuid
import argparse
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any


def print_with_flush(message):
    """Print message and flush stdout immediately"""
    print(message)
    sys.stdout.flush()


class JourneyStageManager:
    """Manages TMF ODA transformation journey metadata and stages"""
    
    def __init__(self, table=None, dynamodb=None):
        """
        Initialize Journey Stage Manager
        
        Args:
            table: Optional DynamoDB table (for dependency injection/testing)
            dynamodb: Optional DynamoDB resource (for dependency injection/testing)
        """
        if table is not None:
            # Dependency injection mode (for testing)
            self.table = table
            self.dynamodb = dynamodb
        else:
            # Normal operation - create AWS clients
            self.dynamodb = None
            self.table = None
            self.setup_aws_client()
        
        # Valid journey statuses
        self.valid_journey_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled', 'paused']
        
        # Valid priorities
        self.valid_priorities = ['low', 'medium', 'high', 'critical']
        
        # Valid ODA component types
        self.valid_oda_components = [
            'customer-management',
            'product-catalog', 
            'order-management',
            'billing',
            'resource-inventory',
            'service-catalog',
            'party-management',
            'account-management',
            'data-pipeline'
        ]
        
        # Available stage IDs
        self.available_stage_ids = [
            'raw_analysis',
            'stripped_schema',
            'tmf_mapping', 
            'migration_planning',
            'data_migration',
            'verification_validation'
        ]
        
        # Default stage templates
        self.stage_templates = {
            'raw_analysis': {
                'name': 'Raw Input Analysis',
                'description': 'Analyze the raw database schema and structure',
                'estimatedDuration': '15m',
                'canSkip': False,
                'secondBrainEnabled': True,
                'ruleTypes': ['field_mapping', 'contextual_recommendations', 'data_interpretation'],
                'steps': [
                    {
                        'id': 'schema_parsing',
                        'name': 'Schema File Parsing',
                        'description': 'Parse SQL schema files and extract structure',
                        'order': 0,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations', 'data_interpretation']
                    },
                    {
                        'id': 'relationship_discovery',
                        'name': 'Relationship Discovery', 
                        'description': 'Identify table relationships and foreign keys',
                        'order': 1,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['field_mapping', 'contextual_recommendations']
                    },
                    {
                        'id': 'data_type_analysis',
                        'name': 'Data Type Analysis',
                        'description': 'Analyze column data types and constraints',
                        'order': 2,
                        'estimatedDuration': '3m',
                        'aiAssisted': True,
                        'applicableRules': ['data_interpretation']
                    },
                    {
                        'id': 'business_rules_extraction',
                        'name': 'Business Rules Extraction',
                        'description': 'Extract business rules from schema constraints',
                        'order': 3,
                        'estimatedDuration': '2m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations', 'data_interpretation']
                    }
                ]
            }
        }
    
    def setup_aws_client(self):
        """Set up AWS DynamoDB client"""
        try:
            print_with_flush('🔗 Setting up AWS DynamoDB client...')
            
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
                print_with_flush(f'📋 Using table from config: {table_name}')
            except Exception:
                table_name = os.environ.get('DYNAMODB_TABLE', 'TransformationSystem')
                print_with_flush(f'📋 Using table from env/default: {table_name}')
            
            role_arn = os.environ.get('AWS_ROLE_ARN')
            if role_arn:
                print_with_flush(f'🔑 Using role ARN: {role_arn}')
                self.dynamodb = create_aws_resource('dynamodb', role_arn=role_arn)
            else:
                print_with_flush('🔑 Using default credential chain')
                self.dynamodb = boto3.resource('dynamodb')
            
            self.table = self.dynamodb.Table(table_name)
            print_with_flush('✅ AWS DynamoDB client ready')
            
        except Exception as e:
            print_with_flush(f'❌ Failed to setup AWS client: {str(e)}')
            raise
    
    def convert_floats_to_decimal(self, obj):
        """Convert float values to Decimal for DynamoDB compatibility"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self.convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_floats_to_decimal(item) for item in obj]
        else:
            return obj
    
    def clean_journey_id(self, journey_id: str) -> str:
        """Clean journey ID by removing JOURNEY# prefix if present"""
        return journey_id.replace('JOURNEY#', '') if journey_id.startswith('JOURNEY#') else journey_id
    
    def validate_journey_exists(self, journey_id: str) -> bool:
        """Check if a journey exists in the database"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            
            response = self.table.get_item(
                Key={
                    'PK': f'JOURNEY#{clean_id}',
                    'SK': 'METADATA'
                }
            )
            
            return 'Item' in response
            
        except Exception as e:
            print_with_flush(f'❌ Error checking journey existence: {str(e)}')
            return False
    
    # ==========================================
    # JOURNEY METADATA MANAGEMENT
    # ==========================================
    
    def list_journeys(self, status_filter: Optional[str] = None, 
                     component_type_filter: Optional[str] = None) -> List[Dict]:
        """List all journeys with optional filtering"""
        try:
            print_with_flush('📋 Listing transformation journeys...')
            
            # Query all journeys
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': 'JOURNEYS'
                }
            )
            
            journeys = []
            for item in response['Items']:
                journey_data = item['Data']
                
                # Apply filters
                if status_filter and journey_data.get('status') != status_filter:
                    continue
                if component_type_filter and journey_data.get('odaComponentType') != component_type_filter:
                    continue
                
                journeys.append({
                    'journeyId': journey_data.get('journeyId'),
                    'name': journey_data.get('name'),
                    'description': journey_data.get('description'),
                    'status': journey_data.get('status'),
                    'priority': journey_data.get('priority'),
                    'odaComponentType': journey_data.get('odaComponentType'),
                    'overallProgress': journey_data.get('overallProgress', 0),
                    'currentStageId': journey_data.get('currentStageId'),
                    'createdAt': item.get('CreatedAt'),
                    'updatedAt': item.get('UpdatedAt'),
                    'createdBy': journey_data.get('createdBy')
                })
            
            print_with_flush(f'✅ Found {len(journeys)} journeys')
            return journeys
            
        except Exception as e:
            print_with_flush(f'❌ Error listing journeys: {str(e)}')
            traceback.print_exc()
            return []
    
    def get_journey(self, journey_id: str, include_stages: bool = True) -> Optional[Dict]:
        """Get detailed journey information"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            print_with_flush(f'📄 Getting journey details: {clean_id}')
            
            # Get journey metadata
            response = self.table.get_item(
                Key={
                    'PK': f'JOURNEY#{clean_id}',
                    'SK': 'METADATA'
                }
            )
            
            if 'Item' not in response:
                print_with_flush(f'❌ Journey not found: {clean_id}')
                return None
            
            journey_data = response['Item']['Data']
            
            result = {
                'metadata': journey_data,
                'createdAt': response['Item'].get('CreatedAt'),
                'updatedAt': response['Item'].get('UpdatedAt')
            }
            
            # Get stages if requested
            if include_stages:
                stages = self.list_stages(clean_id)
                result['stages'] = stages
            
            return result
            
        except Exception as e:
            print_with_flush(f'❌ Error getting journey: {str(e)}')
            traceback.print_exc()
            return None
    
    def create_journey(self, journey_data: Dict[str, Any], journey_id: Optional[str] = None) -> Optional[str]:
        """Create a new journey"""
        try:
            # Generate journey ID if not provided
            if not journey_id:
                journey_id = f'JRN-{str(uuid.uuid4()).upper().replace("-", "")[:12]}'
            else:
                journey_id = self.clean_journey_id(journey_id)
            
            print_with_flush(f'➕ Creating new journey: {journey_id}')
            
            # Validate required fields
            required_fields = ['name', 'description', 'odaComponentType']
            for field in required_fields:
                if field not in journey_data:
                    print_with_flush(f'❌ Missing required field: {field}')
                    return None
            
            # Validate ODA component type
            if journey_data['odaComponentType'] not in self.valid_oda_components:
                print_with_flush(f'❌ Invalid ODA component type: {journey_data["odaComponentType"]}')
                print_with_flush(f'   Valid types: {", ".join(self.valid_oda_components)}')
                return None
            
            # Convert floats to Decimal
            journey_data = self.convert_floats_to_decimal(journey_data)
            
            # Create journey metadata
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
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
                    'name': journey_data['name'],
                    'description': journey_data['description'],
                    'status': journey_data.get('status', 'pending'),
                    'createdBy': journey_data.get('createdBy', 'user'),
                    'priority': journey_data.get('priority', 'medium'),
                    'odaComponentType': journey_data['odaComponentType'],
                    'source': journey_data.get('source', {
                        'type': 'schema-based',
                        'schemaId': f'schema-{journey_data["odaComponentType"]}-001',
                        'schemaName': f'{journey_data["odaComponentType"].replace("-", " ").title()} Database',
                        'schemaVersion': '1.0.0'
                    }),
                    'configuration': journey_data.get('configuration', {
                        'timeout': 1800,
                        'maxDepth': 5,
                        'tmfSpecVersion': '4.0.0',
                        'outputFormat': 'json',
                        'retryAttempts': 3,
                        'enableDetailedLogging': True,
                        'validateAtEachStage': True,
                        'secondBrainEnabled': True,
                        'ruleEngineVersion': 'v1.0'
                    }),
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
                        'totalRules': 0,
                        'activeRules': 0
                    },
                    'stageSummary': {},
                    'secondBrainConfig': journey_data.get('secondBrainConfig', {
                        'enabled': True,
                        'ruleTypes': ['field_mapping', 'contextual_recommendations', 'data_interpretation', 'validation_rules'],
                        'priorityLevels': ['low', 'medium', 'high', 'critical'],
                        'scopes': ['global', 'project', 'stage'],
                        'defaultScope': 'global',
                        'autoApplyRules': True,
                        'customRulesEnabled': True
                    })
                }
            }
            
            # Insert journey
            self.table.put_item(Item=journey_item)
            
            print_with_flush(f'✅ Successfully created journey: {journey_id}')
            print_with_flush(f'   📝 Name: {journey_data["name"]}')
            print_with_flush(f'   🏗️  Component: {journey_data["odaComponentType"]}')
            print_with_flush(f'   📊 Priority: {journey_data.get("priority", "medium")}')
            
            return journey_id
            
        except Exception as e:
            print_with_flush(f'❌ Error creating journey: {str(e)}')
            traceback.print_exc()
            return None
    
    def update_journey(self, journey_id: str, journey_data: Dict[str, Any]) -> bool:
        """Update journey metadata"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            print_with_flush(f'✏️ Updating journey: {clean_id}')
            
            # Check if journey exists
            if not self.validate_journey_exists(clean_id):
                print_with_flush(f'❌ Journey not found: {clean_id}')
                return False
            
            # Get existing journey
            existing_journey = self.get_journey(clean_id, include_stages=False)
            if not existing_journey:
                return False
            
            # Convert floats to Decimal
            journey_data = self.convert_floats_to_decimal(journey_data)
            
            # Update journey metadata
            updated_data = existing_journey['metadata'].copy()
            updated_data.update(journey_data)
            
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
            # Update the item
            self.table.update_item(
                Key={
                    'PK': f'JOURNEY#{clean_id}',
                    'SK': 'METADATA'
                },
                UpdateExpression='SET #data = :data, UpdatedAt = :updated_at',
                ExpressionAttributeNames={
                    '#data': 'Data'
                },
                ExpressionAttributeValues={
                    ':data': updated_data,
                    ':updated_at': timestamp
                }
            )
            
            print_with_flush(f'✅ Successfully updated journey: {clean_id}')
            return True
            
        except Exception as e:
            print_with_flush(f'❌ Error updating journey: {str(e)}')
            traceback.print_exc()
            return False
    
    def delete_journey(self, journey_id: str, confirm: bool = False) -> bool:
        """Delete a journey and all its stages/rules"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            print_with_flush(f'🗑️ Deleting journey: {clean_id}')
            
            # Check if journey exists
            if not self.validate_journey_exists(clean_id):
                print_with_flush(f'❌ Journey not found: {clean_id}')
                return False
            
            if not confirm:
                print_with_flush('⚠️ This will delete the journey and ALL its stages, rules, and job history!')
                response = input('Are you sure? Type "DELETE" to confirm: ')
                if response != 'DELETE':
                    print_with_flush('❌ Deletion cancelled')
                    return False
            
            # Get all items for this journey
            response = self.table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'JOURNEY#{clean_id}'
                }
            )
            
            # Delete all items
            items_deleted = 0
            for item in response['Items']:
                self.table.delete_item(
                    Key={
                        'PK': item['PK'],
                        'SK': item['SK']
                    }
                )
                items_deleted += 1
            
            print_with_flush(f'✅ Successfully deleted journey: {clean_id}')
            print_with_flush(f'   🗑️ Deleted {items_deleted} items')
            return True
            
        except Exception as e:
            print_with_flush(f'❌ Error deleting journey: {str(e)}')
            traceback.print_exc()
            return False
    
    # ==========================================
    # STAGE MANAGEMENT
    # ==========================================
    
    def list_stages(self, journey_id: str) -> List[Dict]:
        """List all stages for a journey"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            print_with_flush(f'📋 Listing stages for journey: {clean_id}')
            
            # Check if journey exists
            if not self.validate_journey_exists(clean_id):
                print_with_flush(f'❌ Journey not found: {clean_id}')
                return []
            
            # Query all stages for the journey
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'JOURNEY#{clean_id}#STAGES'
                }
            )
            
            stages = []
            for item in response['Items']:
                stage_data = item['Data']
                stages.append({
                    'stageId': stage_data.get('stageId'),
                    'name': stage_data.get('name'),
                    'description': stage_data.get('description'),
                    'order': stage_data.get('order'),
                    'canSkip': stage_data.get('canSkip'),
                    'estimatedDuration': stage_data.get('estimatedDuration'),
                    'status': stage_data.get('status', 'pending'),
                    'secondBrainEnabled': stage_data.get('secondBrainEnabled', False),
                    'steps': stage_data.get('steps', []),
                    'createdAt': item.get('CreatedAt'),
                    'updatedAt': item.get('UpdatedAt')
                })
            
            # Sort by order
            stages.sort(key=lambda x: x.get('order', 0))
            
            print_with_flush(f'✅ Found {len(stages)} stages')
            return stages
            
        except Exception as e:
            print_with_flush(f'❌ Error listing stages: {str(e)}')
            traceback.print_exc()
            return []
    
    def get_stage(self, journey_id: str, stage_id: str) -> Optional[Dict]:
        """Get detailed stage information"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            print_with_flush(f'📄 Getting stage details: {stage_id}')
            
            # Check if journey exists
            if not self.validate_journey_exists(clean_id):
                print_with_flush(f'❌ Journey not found: {clean_id}')
                return None
            
            # Find the stage by scanning
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
                ExpressionAttributeValues={
                    ':pk': f'JOURNEY#{clean_id}',
                    ':sk_prefix': f'STAGE#'
                }
            )
            
            for item in response['Items']:
                if item['Data'].get('stageId') == stage_id:
                    return {
                        'metadata': item['Data'],
                        'createdAt': item.get('CreatedAt'),
                        'updatedAt': item.get('UpdatedAt')
                    }
            
            print_with_flush(f'❌ Stage not found: {stage_id}')
            return None
            
        except Exception as e:
            print_with_flush(f'❌ Error getting stage: {str(e)}')
            traceback.print_exc()
            return None
    
    def add_stage(self, journey_id: str, stage_data: Dict[str, Any]) -> bool:
        """Add a new stage to a journey"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            print_with_flush(f'➕ Adding stage to journey: {clean_id}')
            
            # Check if journey exists
            if not self.validate_journey_exists(clean_id):
                print_with_flush(f'❌ Journey not found: {clean_id}')
                return False
            
            # Validate required fields
            required_fields = ['stageId', 'name', 'description']
            for field in required_fields:
                if field not in stage_data:
                    print_with_flush(f'❌ Missing required field: {field}')
                    return False
            
            stage_id = stage_data['stageId']
            
            # Check if stage already exists
            existing_stage = self.get_stage(clean_id, stage_id)
            if existing_stage:
                print_with_flush(f'❌ Stage already exists: {stage_id}')
                return False
            
            # Convert floats to Decimal
            stage_data = self.convert_floats_to_decimal(stage_data)
            
            # Get current stages to determine order
            existing_stages = self.list_stages(clean_id)
            stage_order = stage_data.get('order', len(existing_stages))
            
            # Create stage item
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
            stage_item = {
                'PK': f'JOURNEY#{clean_id}',
                'SK': f'STAGE#{stage_order:02d}#{stage_id}',
                'EntityType': 'StageDefinition',
                'GSI1PK': f'JOURNEY#{clean_id}#STAGES',
                'GSI1SK': f'{stage_order:02d}',
                'CreatedAt': timestamp,
                'UpdatedAt': timestamp,
                'Data': {
                    'stageId': stage_id,
                    'name': stage_data['name'],
                    'description': stage_data['description'],
                    'order': stage_order,
                    'canSkip': stage_data.get('canSkip', False),
                    'estimatedDuration': stage_data.get('estimatedDuration', '10m'),
                    'status': stage_data.get('status', 'pending'),
                    'secondBrainEnabled': stage_data.get('secondBrainEnabled', True),
                    'ruleTypes': stage_data.get('ruleTypes', ['contextual_recommendations']),
                    'steps': stage_data.get('steps', [])
                }
            }
            
            # Insert stage
            self.table.put_item(Item=stage_item)
            
            print_with_flush(f'✅ Successfully added stage: {stage_id}')
            print_with_flush(f'   📝 Name: {stage_data["name"]}')
            print_with_flush(f'   📊 Order: {stage_order}')
            print_with_flush(f'   ⏱️  Duration: {stage_data.get("estimatedDuration", "10m")}')
            
            return True
            
        except Exception as e:
            print_with_flush(f'❌ Error adding stage: {str(e)}')
            traceback.print_exc()
            return False
    
    def update_stage(self, journey_id: str, stage_id: str, stage_data: Dict[str, Any]) -> bool:
        """Update an existing stage"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            print_with_flush(f'✏️ Updating stage: {stage_id}')
            
            # Check if stage exists
            existing_stage = self.get_stage(clean_id, stage_id)
            if not existing_stage:
                return False
            
            # Convert floats to Decimal
            stage_data = self.convert_floats_to_decimal(stage_data)
            
            # Update stage data
            updated_data = existing_stage['metadata'].copy()
            updated_data.update(stage_data)
            
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
            # Find the exact item to update
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
                ExpressionAttributeValues={
                    ':pk': f'JOURNEY#{clean_id}',
                    ':sk_prefix': f'STAGE#'
                }
            )
            
            target_item = None
            for item in response['Items']:
                if item['Data']['stageId'] == stage_id:
                    target_item = item
                    break
            
            if not target_item:
                print_with_flush(f'❌ Stage item not found in database: {stage_id}')
                return False
            
            # Update the item
            self.table.update_item(
                Key={
                    'PK': target_item['PK'],
                    'SK': target_item['SK']
                },
                UpdateExpression='SET #data = :data, UpdatedAt = :updated_at',
                ExpressionAttributeNames={
                    '#data': 'Data'
                },
                ExpressionAttributeValues={
                    ':data': updated_data,
                    ':updated_at': timestamp
                }
            )
            
            print_with_flush(f'✅ Successfully updated stage: {stage_id}')
            return True
            
        except Exception as e:
            print_with_flush(f'❌ Error updating stage: {str(e)}')
            traceback.print_exc()
            return False
    
    def delete_stage(self, journey_id: str, stage_id: str) -> bool:
        """Delete a stage from a journey"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            print_with_flush(f'🗑️ Deleting stage: {stage_id}')
            
            # Check if stage exists
            existing_stage = self.get_stage(clean_id, stage_id)
            if not existing_stage:
                return False
            
            # Find the exact item to delete
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
                ExpressionAttributeValues={
                    ':pk': f'JOURNEY#{clean_id}',
                    ':sk_prefix': f'STAGE#'
                }
            )
            
            target_item = None
            for item in response['Items']:
                if item['Data']['stageId'] == stage_id:
                    target_item = item
                    break
            
            if not target_item:
                print_with_flush(f'❌ Stage item not found in database: {stage_id}')
                return False
            
            # Delete the item
            self.table.delete_item(
                Key={
                    'PK': target_item['PK'],
                    'SK': target_item['SK']
                }
            )
            
            print_with_flush(f'✅ Successfully deleted stage: {stage_id}')
            return True
            
        except Exception as e:
            print_with_flush(f'❌ Error deleting stage: {str(e)}')
            traceback.print_exc()
            return False
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def display_journeys_table(self, journeys: List[Dict]):
        """Display journeys in a formatted table"""
        if not journeys:
            print_with_flush('📋 No journeys found')
            return
        
        print_with_flush('\n📋 TMF ODA Transformation Journeys:')
        print_with_flush('=' * 140)
        
        # Header
        header = f'{"Journey ID":<20} {"Name":<30} {"Component":<20} {"Status":<12} {"Priority":<10} {"Progress":<10} {"Current Stage":<20}'
        print_with_flush(header)
        print_with_flush('-' * 140)
        
        # Journeys
        for journey in journeys:
            progress = f'{journey.get("overallProgress", 0)}%'
            row = f'{journey["journeyId"]:<20} {journey["name"][:29]:<30} {journey.get("odaComponentType", "N/A"):<20} {journey["status"]:<12} {journey.get("priority", "medium"):<10} {progress:<10} {journey.get("currentStageId", "N/A"):<20}'
            print_with_flush(row)
        
        print_with_flush(f'\n📊 Total: {len(journeys)} journeys')
    
    def display_stages_table(self, stages: List[Dict], journey_id: str):
        """Display stages in a formatted table"""
        if not stages:
            print_with_flush(f'📋 No stages found for journey: {journey_id}')
            return
        
        print_with_flush(f'\n📋 Stages for Journey: {journey_id}')
        print_with_flush('=' * 120)
        
        # Header
        header = f'{"Order":<6} {"Stage ID":<20} {"Name":<25} {"Duration":<10} {"Status":<12} {"AI":<5} {"Steps":<6}'
        print_with_flush(header)
        print_with_flush('-' * 120)
        
        # Stages
        for stage in stages:
            ai_enabled = '✓' if stage.get('secondBrainEnabled') else '✗'
            steps_count = len(stage.get('steps', []))
            
            row = f'{stage.get("order", 0):<6} {stage["stageId"]:<20} {stage["name"][:24]:<25} {stage.get("estimatedDuration", "N/A"):<10} {stage.get("status", "pending"):<12} {ai_enabled:<5} {steps_count:<6}'
            print_with_flush(row)
        
        print_with_flush(f'\n📊 Total: {len(stages)} stages')
    
    def interactive_journey_builder(self) -> bool:
        """Interactive journey builder"""
        try:
            print_with_flush('\n🏗️ Interactive Journey Builder')
            print_with_flush('=' * 50)
            
            # Build journey interactively
            journey_data = {}
            
            print_with_flush('\n📝 Journey Basic Information:')
            journey_data['name'] = input('Journey name: ').strip()
            journey_data['description'] = input('Journey description: ').strip()
            
            print_with_flush(f'\nAvailable ODA components: {", ".join(self.valid_oda_components)}')
            journey_data['odaComponentType'] = input('ODA component type: ').strip()
            
            print_with_flush(f'Available priorities: {", ".join(self.valid_priorities)}')
            priority = input('Priority (default: medium): ').strip()
            if priority:
                journey_data['priority'] = priority
            
            journey_data['createdBy'] = input('Created by (default: user): ').strip() or 'user'
            
            # Confirm and create
            print_with_flush('\n📋 Journey Summary:')
            print_with_flush(f'   📝 Name: {journey_data["name"]}')
            print_with_flush(f'   🏗️  Component: {journey_data["odaComponentType"]}')
            print_with_flush(f'   📊 Priority: {journey_data.get("priority", "medium")}')
            print_with_flush(f'   👤 Created by: {journey_data["createdBy"]}')
            
            confirm = input('\nCreate this journey? (y/n): ').strip().lower()
            if confirm == 'y':
                journey_id = self.create_journey(journey_data)
                if journey_id:
                    print_with_flush(f'\n✅ Journey created successfully: {journey_id}')
                    
                    # Ask if they want to add stages
                    add_stages = input('Add default stages? (y/n): ').strip().lower()
                    if add_stages == 'y':
                        self.add_default_stages(journey_id)
                    
                    return True
            else:
                print_with_flush('❌ Journey creation cancelled')
                return False
                
        except KeyboardInterrupt:
            print_with_flush('\n❌ Journey builder cancelled')
            return False
        except Exception as e:
            print_with_flush(f'❌ Error in interactive builder: {str(e)}')
            return False
    
    # ==================== Compatibility Aliases for Unit Tests ====================
    # These methods provide backward compatibility with unit tests
    
    def list_stages_for_journey(self, journey_id: str) -> List[Dict]:
        """Alias for list_stages() - compatibility with unit tests"""
        return self.list_stages(journey_id)
    
    def get_stage_details(self, journey_id: str, stage_id: str) -> Optional[Dict]:
        """Alias for get_stage() - compatibility with unit tests"""
        result = self.get_stage(journey_id, stage_id)
        # Flatten response for test compatibility
        if result and 'metadata' in result:
            return result['metadata']
        return result
    
    def create_stage(self, journey_id: str, stage_data: Dict[str, Any]) -> bool:
        """Alias for add_stage() - compatibility with unit tests"""
        return self.add_stage(journey_id, stage_data)
    
    def update_stage_progress(self, journey_id: str, stage_id: str, progress: int) -> bool:
        """Update stage progress - compatibility with unit tests"""
        return self.update_stage(journey_id, stage_id, {'progress': progress})
    
    def mark_stage_completed(self, journey_id: str, stage_id: str) -> bool:
        """Mark stage as completed - compatibility with unit tests"""
        return self.update_stage(journey_id, stage_id, {'status': 'completed', 'progress': 100})
    
    def get_next_stage(self, journey_id: str, current_stage_id: str) -> Optional[Dict]:
        """Get next stage in sequence - compatibility with unit tests"""
        stages = self.list_stages(journey_id)
        current_order = None
        
        for stage in stages:
            if stage.get('stageId') == current_stage_id:
                current_order = stage.get('order', 0)
                break
        
        if current_order is None:
            return None
        
        # Find stage with next order
        next_stages = [s for s in stages if s.get('order', 0) > current_order]
        if next_stages:
            return min(next_stages, key=lambda s: s.get('order', 0))
        return None
    
    def validate_stage_dependencies(self, journey_id: str, stage_id: str) -> bool:
        """Validate stage dependencies - compatibility with unit tests"""
        stage = self.get_stage(journey_id, stage_id)
        if not stage:
            return False
        
        dependencies = stage.get('dependencies', [])
        if not dependencies:
            return True
        
        stages = self.list_stages(journey_id)
        for dep_id in dependencies:
            dep_stage = next((s for s in stages if s.get('stageId') == dep_id), None)
            if not dep_stage or dep_stage.get('status') != 'completed':
                return False
        
        return True
    
    def get_stage_metrics(self, journey_id: str, stage_id: str) -> Dict[str, Any]:
        """Get stage metrics - compatibility with unit tests"""
        stage = self.get_stage(journey_id, stage_id)
        if not stage:
            return {}
        
        return {
            'stage_id': stage_id,
            'status': stage.get('status', 'pending'),
            'progress': stage.get('progress', 0),
            'execution_time': stage.get('executionTime', 0),
            'steps_completed': len([s for s in stage.get('steps', []) if s.get('status') == 'completed']),
            'total_steps': len(stage.get('steps', [])),
            'last_updated': stage.get('updatedAt', '')
        }
    
    def get_stage_by_order(self, journey_id: str, order: int) -> Optional[Dict]:
        """Get stage by order number - compatibility with unit tests"""
        stages = self.list_stages(journey_id)
        return next((s for s in stages if s.get('order') == order), None)
    
    def update_stage_configuration(self, journey_id: str, stage_id: str, config: Dict) -> bool:
        """Update stage configuration - compatibility with unit tests"""
        return self.update_stage(journey_id, stage_id, {'configuration': config})
    
    def validate_stage_configuration(self, journey_id: str, stage_id: str) -> bool:
        """Validate stage configuration - compatibility with unit tests"""
        stage = self.get_stage(journey_id, stage_id)
        if not stage:
            return False
        
        required_fields = ['stageId', 'name', 'order']
        return all(field in stage for field in required_fields)
    
    # ==================== End Compatibility Aliases ====================
    
    def add_default_stages(self, journey_id: str) -> bool:
        """Add default stages to a journey"""
        try:
            print_with_flush(f'➕ Adding default stages to journey: {journey_id}')
            
            default_stages = [
                {
                    'stageId': 'raw_analysis',
                    'name': 'Raw Input Analysis',
                    'description': 'Analyze the raw database schema and structure',
                    'order': 0,
                    'estimatedDuration': '15m',
                    'canSkip': False
                },
                {
                    'stageId': 'stripped_schema',
                    'name': 'Create Stripped Document',
                    'description': 'Create TMF-focused simplified schema',
                    'order': 1,
                    'estimatedDuration': '12m',
                    'canSkip': False
                },
                {
                    'stageId': 'tmf_mapping',
                    'name': 'TMF Schema Mapping',
                    'description': 'Map the stripped schema to TMF ODA standards',
                    'order': 2,
                    'estimatedDuration': '20m',
                    'canSkip': False
                },
                {
                    'stageId': 'migration_planning',
                    'name': 'Data Migration Planning',
                    'description': 'Plan and prepare data migration strategies',
                    'order': 3,
                    'estimatedDuration': '18m',
                    'canSkip': False
                },
                {
                    'stageId': 'data_migration',
                    'name': 'Data Migration',
                    'description': 'Execute the actual data migration',
                    'order': 4,
                    'estimatedDuration': '25m',
                    'canSkip': False
                },
                {
                    'stageId': 'verification_validation',
                    'name': 'Verification & Validation',
                    'description': 'Validate the mapping and migration results',
                    'order': 5,
                    'estimatedDuration': '22m',
                    'canSkip': False
                }
            ]
            
            successful_adds = 0
            for stage in default_stages:
                if self.add_stage(journey_id, stage):
                    successful_adds += 1
            
            print_with_flush(f'✅ Successfully added {successful_adds} out of {len(default_stages)} default stages')
            return successful_adds > 0
            
        except Exception as e:
            print_with_flush(f'❌ Error adding default stages: {str(e)}')
            return False


def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(description='Manage TMF ODA Transformation Journey Metadata and Stages')
    parser.add_argument('--action', required=True, choices=[
        'list-journeys', 'get-journey', 'create-journey', 'update-journey', 'delete-journey',
        'list-stages', 'get-stage', 'add-stage', 'update-stage', 'delete-stage',
        'add-default-stages', 'interactive'
    ], help='Action to perform')
    
    # Journey arguments
    parser.add_argument('--journey-id', help='Journey ID')
    parser.add_argument('--journey-file', help='JSON file with journey data')
    parser.add_argument('--status-filter', help='Filter journeys by status')
    parser.add_argument('--component-filter', help='Filter journeys by component type')
    
    # Stage arguments
    parser.add_argument('--stage-id', help='Stage ID')
    parser.add_argument('--stage-file', help='JSON file with stage data')
    parser.add_argument('--include-stages', action='store_true', help='Include stages in journey details')
    
    args = parser.parse_args()
    
    # Initialize manager
    try:
        print_with_flush('🏗️ Journey & Stage Manager')
        print_with_flush('=' * 50)
        
        manager = JourneyStageManager()
        
        # Journey operations
        if args.action == 'list-journeys':
            journeys = manager.list_journeys(
                status_filter=args.status_filter,
                component_type_filter=args.component_filter
            )
            manager.display_journeys_table(journeys)
        
        elif args.action == 'get-journey':
            if not args.journey_id:
                print_with_flush('❌ --journey-id is required for get-journey action')
                return False
            
            journey = manager.get_journey(args.journey_id, args.include_stages)
            if journey:
                print_with_flush(f'\n📋 Journey Details:')
                print_with_flush(json.dumps(journey, indent=2, default=str))
            
        elif args.action == 'create-journey':
            if not args.journey_file:
                print_with_flush('❌ --journey-file is required for create-journey action')
                return False
            
            with open(args.journey_file, 'r') as f:
                journey_data = json.load(f)
            
            manager.create_journey(journey_data, args.journey_id)
        
        elif args.action == 'update-journey':
            if not args.journey_id:
                print_with_flush('❌ --journey-id is required for update-journey action')
                return False
            if not args.journey_file:
                print_with_flush('❌ --journey-file is required for update-journey action')
                return False
            
            with open(args.journey_file, 'r') as f:
                journey_data = json.load(f)
            
            manager.update_journey(args.journey_id, journey_data)
        
        elif args.action == 'delete-journey':
            if not args.journey_id:
                print_with_flush('❌ --journey-id is required for delete-journey action')
                return False
            
            manager.delete_journey(args.journey_id)
        
        # Stage operations
        elif args.action == 'list-stages':
            if not args.journey_id:
                print_with_flush('❌ --journey-id is required for list-stages action')
                return False
            
            stages = manager.list_stages(args.journey_id)
            manager.display_stages_table(stages, args.journey_id)
        
        elif args.action == 'get-stage':
            if not args.journey_id:
                print_with_flush('❌ --journey-id is required for get-stage action')
                return False
            if not args.stage_id:
                print_with_flush('❌ --stage-id is required for get-stage action')
                return False
            
            stage = manager.get_stage(args.journey_id, args.stage_id)
            if stage:
                print_with_flush(f'\n📋 Stage Details:')
                print_with_flush(json.dumps(stage, indent=2, default=str))
        
        elif args.action == 'add-stage':
            if not args.journey_id:
                print_with_flush('❌ --journey-id is required for add-stage action')
                return False
            if not args.stage_file:
                print_with_flush('❌ --stage-file is required for add-stage action')
                return False
            
            with open(args.stage_file, 'r') as f:
                stage_data = json.load(f)
            
            manager.add_stage(args.journey_id, stage_data)
        
        elif args.action == 'update-stage':
            if not args.journey_id:
                print_with_flush('❌ --journey-id is required for update-stage action')
                return False
            if not args.stage_id:
                print_with_flush('❌ --stage-id is required for update-stage action')
                return False
            if not args.stage_file:
                print_with_flush('❌ --stage-file is required for update-stage action')
                return False
            
            with open(args.stage_file, 'r') as f:
                stage_data = json.load(f)
            
            manager.update_stage(args.journey_id, args.stage_id, stage_data)
        
        elif args.action == 'delete-stage':
            if not args.journey_id:
                print_with_flush('❌ --journey-id is required for delete-stage action')
                return False
            if not args.stage_id:
                print_with_flush('❌ --stage-id is required for delete-stage action')
                return False
            
            manager.delete_stage(args.journey_id, args.stage_id)
        
        elif args.action == 'add-default-stages':
            if not args.journey_id:
                print_with_flush('❌ --journey-id is required for add-default-stages action')
                return False
            
            manager.add_default_stages(args.journey_id)
        
        elif args.action == 'interactive':
            manager.interactive_journey_builder()
        
        return True
        
    except Exception as e:
        print_with_flush(f'❌ Error: {str(e)}')
        traceback.print_exc()
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_with_flush('\n⚠️ Operation cancelled by user')
        sys.exit(1)
    except Exception as e:
        print_with_flush(f'\n❌ Unexpected error: {str(e)}')
        traceback.print_exc()
        sys.exit(1) 