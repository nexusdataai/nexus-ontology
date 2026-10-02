#!/usr/bin/env python3
"""
Test Data Manager for BDD Testing
Manages test fixtures and data for journey management testing
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError
import random
import string

class TestDataManager:
    """Manages test data creation and cleanup for BDD tests"""
    
    def __init__(self, aws_region: str = 'us-east-1'):
        """Initialize test data manager
        
        Args:
            aws_region: AWS region for mocked services
        """
        self.aws_region = aws_region
        self.dynamodb = None
        self.s3 = None
        self.transformation_table = None
        self.created_resources = {
            'journeys': [],
            'stages': [],
            'rules': [],
            'jobs': [],
            's3_objects': []
        }
        
        # Valid values for dropdowns
        self.valid_oda_components = [
            'Payment Management',
            'Customer Management', 
            'Product Catalog Management',
            'Service Order Management',
            'Resource Inventory Management',
            'Service Inventory Management',
            'Party Management',
            'Agreement Management',
            'Billing Management',
            'Service Quality Management'
        ]
        
        self.valid_journey_statuses = [
            'pending', 'running', 'completed', 'failed', 'cancelled', 'paused'
        ]
        
        self.valid_priorities = ['low', 'medium', 'high', 'critical']
        
        self.valid_stage_ids = [
            'raw_analysis', 'stripped_schema', 'tmf_mapping',
            'data_validation', 'transformation_design', 'implementation',
            'testing', 'deployment', 'validation', 'completion'
        ]
        
    def setup_test_tables(self) -> None:
        """Set up DynamoDB tables for testing"""
        self.dynamodb = boto3.resource('dynamodb', region_name=self.aws_region)
        self.s3 = boto3.client('s3', region_name=self.aws_region)
        
        # Check if table already exists
        try:
            self.transformation_table = self.dynamodb.Table('aurorastack-transformation-jobs')
            # Try to describe the table to see if it exists
            self.transformation_table.table_status
            return  # Table already exists and is accessible
        except:
            pass  # Table doesn't exist, create it
        
        # Create transformation table
        try:
            self.transformation_table = self.dynamodb.create_table(
                TableName='aurorastack-transformation-jobs',
                KeySchema=[
                    {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                    {'AttributeName': 'sk', 'AttributeType': 'S'},
                    {'AttributeName': 'gsi1pk', 'AttributeType': 'S'},
                    {'AttributeName': 'gsi1sk', 'AttributeType': 'S'},
                    {'AttributeName': 'gsi2pk', 'AttributeType': 'S'},
                    {'AttributeName': 'gsi2sk', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'gsi1',
                        'KeySchema': [
                            {'AttributeName': 'gsi1pk', 'KeyType': 'HASH'},
                            {'AttributeName': 'gsi1sk', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'}
                    },
                    {
                        'IndexName': 'gsi2',
                        'KeySchema': [
                            {'AttributeName': 'gsi2pk', 'KeyType': 'HASH'},
                            {'AttributeName': 'gsi2sk', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'}
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            # Wait for table to be created
            self.transformation_table.wait_until_exists()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                # Table already exists
                self.transformation_table = self.dynamodb.Table('aurorastack-transformation-jobs')
                
        # Create S3 bucket for test
        try:
            self.s3.create_bucket(Bucket='aurorastack-test-bucket')
        except ClientError as e:
            if e.response['Error']['Code'] != 'BucketAlreadyExists':
                raise
                
    def cleanup(self) -> None:
        """Clean up all created test resources"""
        if not self.transformation_table:
            return
            
        # Delete all created items
        for journey_id in self.created_resources['journeys']:
            self._delete_journey_and_related(journey_id)
            
        # Delete S3 objects
        for s3_key in self.created_resources['s3_objects']:
            try:
                self.s3.delete_object(Bucket='aurorastack-test-bucket', Key=s3_key)
            except:
                pass
                
        # Clear tracking
        self.created_resources = {
            'journeys': [],
            'stages': [],
            'rules': [],
            'jobs': [],
            's3_objects': []
        }
        
    def _delete_journey_and_related(self, journey_id: str) -> None:
        """Delete journey and all related items"""
        try:
            # Delete journey
            self.transformation_table.delete_item(
                Key={'pk': f'JOURNEY#{journey_id}', 'sk': f'JOURNEY#{journey_id}'}
            )
            
            # Delete stages
            response = self.transformation_table.query(
                KeyConditionExpression='pk = :pk AND begins_with(sk, :sk_prefix)',
                ExpressionAttributeValues={
                    ':pk': f'JOURNEY#{journey_id}',
                    ':sk_prefix': 'STAGE#'
                }
            )
            for item in response.get('Items', []):
                self.transformation_table.delete_item(Key={'pk': item['pk'], 'sk': item['sk']})
                
            # Delete rules
            response = self.transformation_table.query(
                KeyConditionExpression='pk = :pk AND begins_with(sk, :sk_prefix)',
                ExpressionAttributeValues={
                    ':pk': f'JOURNEY#{journey_id}',
                    ':sk_prefix': 'RULE#'
                }
            )
            for item in response.get('Items', []):
                self.transformation_table.delete_item(Key={'pk': item['pk'], 'sk': item['sk']})
                
        except Exception as e:
            print(f"Error cleaning up journey {journey_id}: {e}")
            
    # Journey Management
    
    def create_journey(self, journey_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a test journey
        
        Args:
            journey_data: Optional journey data override
            
        Returns:
            Created journey data
        """
        if journey_data is None:
            journey_data = {}
        journey_id = journey_data.get('journeyId', f"JRN-TEST-{self._generate_id(6)}")
        
        default_journey = {
            'journeyId': journey_id,
            'name': f'Test Journey {self._generate_id(4)}',
            'description': 'Test journey for BDD testing',
            'odaComponentType': random.choice(self.valid_oda_components),
            'priority': random.choice(self.valid_priorities),
            'status': 'pending',
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'updatedAt': datetime.now(timezone.utc).isoformat(),
            'createdBy': 'test-user@example.com',
            'overallProgress': 0,
            'currentStageId': None,
            'totalStages': 0,
            'completedStages': 0,
            'tags': ['test', 'bdd'],
            'metadata': {
                'testRun': True,
                'environment': 'test'
            }
        }
        
        if journey_data:
            default_journey.update(journey_data)
            
        # Store in DynamoDB
        item = {
            'pk': f'JOURNEY#{journey_id}',
            'sk': f'JOURNEY#{journey_id}',
            'entityType': 'JOURNEY',
            'gsi1pk': 'JOURNEYS',
            'gsi1sk': f"STATUS#{default_journey['status']}#JOURNEY#{journey_id}",
            'gsi2pk': f"COMPONENT#{default_journey['odaComponentType']}",
            'gsi2sk': f"JOURNEY#{journey_id}",
            **default_journey
        }
        
        self.transformation_table.put_item(Item=item)
        self.created_resources['journeys'].append(journey_id)
        
        return default_journey
        
    def create_multiple_journeys(self, count: int, status_distribution: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
        """Create multiple test journeys
        
        Args:
            count: Number of journeys to create
            status_distribution: Optional distribution of statuses
            
        Returns:
            List of created journeys
        """
        journeys = []
        
        if status_distribution:
            # Create journeys with specific status distribution
            for status, num in status_distribution.items():
                for _ in range(num):
                    journey = self.create_journey({'status': status})
                    journeys.append(journey)
        else:
            # Create journeys with random statuses
            for i in range(count):
                journey = self.create_journey({
                    'name': f'Test Journey {i+1}',
                    'status': random.choice(self.valid_journey_statuses)
                })
                journeys.append(journey)
                
        return journeys
        
    # Stage Management
    
    def create_stage(self, journey_id: str, stage_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a test stage for a journey
        
        Args:
            journey_id: Parent journey ID
            stage_data: Optional stage data override
            
        Returns:
            Created stage data
        """
        stage_id = stage_data.get('stageId') if stage_data else random.choice(self.valid_stage_ids)
        
        default_stage = {
            'stageId': stage_id,
            'stageName': f'Test Stage - {stage_id}',
            'description': f'Test stage for {stage_id}',
            'journeyId': journey_id,
            'sequenceOrder': len(self.created_resources['stages']) + 1,
            'status': 'pending',
            'enabled': True,
            'canSkip': False,
            'requiresApproval': False,
            'estimatedDuration': '2h',
            'actualDuration': None,
            'startedAt': None,
            'completedAt': None,
            'configuration': {
                'retryLimit': 3,
                'timeout': '4h'
            },
            'steps': []
        }
        
        if stage_data:
            default_stage.update(stage_data)
            
        # Store in DynamoDB
        item = {
            'pk': f'JOURNEY#{journey_id}',
            'sk': f'STAGE#{stage_id}',
            'entityType': 'STAGE',
            'gsi1pk': f'JOURNEY#{journey_id}#STAGES',
            'gsi1sk': f"ORDER#{str(default_stage['sequenceOrder']).zfill(3)}",
            **default_stage
        }
        
        self.transformation_table.put_item(Item=item)
        self.created_resources['stages'].append(f"{journey_id}#{stage_id}")
        
        return default_stage
        
    def create_stages_for_journey(self, journey_id: str, stage_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple stages for a journey
        
        Args:
            journey_id: Parent journey ID
            stage_configs: List of stage configurations
            
        Returns:
            List of created stages
        """
        stages = []
        for i, config in enumerate(stage_configs):
            config['sequenceOrder'] = i + 1
            stage = self.create_stage(journey_id, config)
            stages.append(stage)
            
        # Update journey with stage count
        self.transformation_table.update_item(
            Key={
                'pk': f'JOURNEY#{journey_id}',
                'sk': f'JOURNEY#{journey_id}'
            },
            UpdateExpression='SET totalStages = :total, currentStageId = :current',
            ExpressionAttributeValues={
                ':total': len(stages),
                ':current': stages[0]['stageId'] if stages else None
            }
        )
        
        return stages
        
    # Rules Management
    
    def create_rule(self, journey_id: str, stage_id: str, rule_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a test rule
        
        Args:
            journey_id: Parent journey ID
            stage_id: Parent stage ID
            rule_data: Optional rule data override
            
        Returns:
            Created rule data
        """
        rule_id = rule_data.get('ruleId') if rule_data else f"RULE-{self._generate_id(8)}"
        
        default_rule = {
            'ruleId': rule_id,
            'journeyId': journey_id,
            'stageId': stage_id,
            'ruleName': f'Test Rule {self._generate_id(4)}',
            'description': 'Test transformation rule',
            'ruleType': random.choice(['field_mapping', 'validation_rules', 'data_filter']),
            'priority': random.randint(1, 100),
            'enabled': True,
            'content': {
                'sourceField': 'testField',
                'targetField': 'mappedField',
                'transformationType': 'direct'
            },
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'updatedAt': datetime.now(timezone.utc).isoformat(),
            'createdBy': 'test-user@example.com'
        }
        
        if rule_data:
            default_rule.update(rule_data)
            
        # Store in DynamoDB
        item = {
            'pk': f'JOURNEY#{journey_id}',
            'sk': f'RULE#{stage_id}#{rule_id}',
            'entityType': 'RULE',
            'gsi1pk': f'STAGE#{stage_id}#RULES',
            'gsi1sk': f"PRIORITY#{str(default_rule['priority']).zfill(3)}#{rule_id}",
            **default_rule
        }
        
        self.transformation_table.put_item(Item=item)
        self.created_resources['rules'].append(f"{journey_id}#{stage_id}#{rule_id}")
        
        return default_rule
        
    # Job Management
    
    def create_job(self, journey_id: str, stage_id: str, job_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a test job execution record
        
        Args:
            journey_id: Parent journey ID
            stage_id: Stage to execute
            job_data: Optional job data override
            
        Returns:
            Created job data
        """
        job_id = job_data.get('jobId') if job_data else f"JOB-{self._generate_id(8)}"
        
        default_job = {
            'jobId': job_id,
            'journeyId': journey_id,
            'stageId': stage_id,
            'jobType': 'stage_execution',
            'status': 'pending',
            'startedAt': datetime.now(timezone.utc).isoformat(),
            'completedAt': None,
            'duration': None,
            'progress': 0,
            'result': None,
            'error': None,
            'logs': [],
            'metrics': {
                'recordsProcessed': 0,
                'recordsFailed': 0,
                'executionTime': 0
            }
        }
        
        if job_data:
            default_job.update(job_data)
            
        # Store in DynamoDB
        item = {
            'pk': f'JOURNEY#{journey_id}',
            'sk': f'JOB#{job_id}',
            'entityType': 'JOB',
            'gsi1pk': f'JOBS',
            'gsi1sk': f"STATUS#{default_job['status']}#JOB#{job_id}",
            **default_job
        }
        
        self.transformation_table.put_item(Item=item)
        self.created_resources['jobs'].append(f"{journey_id}#{job_id}")
        
        return default_job
        
    # Utility Methods
    
    def _generate_id(self, length: int) -> str:
        """Generate random ID string
        
        Args:
            length: Length of ID to generate
            
        Returns:
            Random ID string
        """
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        
    def load_journey_from_file(self, filepath: str) -> Dict[str, Any]:
        """Load journey configuration from JSON file
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Journey configuration
        """
        with open(filepath, 'r') as f:
            return json.load(f)
            
    def save_journey_to_file(self, journey_data: Dict[str, Any], filepath: str) -> None:
        """Save journey configuration to JSON file
        
        Args:
            journey_data: Journey data to save
            filepath: Path to save file
        """
        with open(filepath, 'w') as f:
            json.dump(journey_data, f, indent=2, default=str)
            
    def get_journey_by_id(self, journey_id: str) -> Optional[Dict[str, Any]]:
        """Get journey from test database
        
        Args:
            journey_id: Journey ID to retrieve
            
        Returns:
            Journey data or None if not found
        """
        try:
            response = self.transformation_table.get_item(
                Key={
                    'pk': f'JOURNEY#{journey_id}',
                    'sk': f'JOURNEY#{journey_id}'
                }
            )
            return response.get('Item')
        except:
            return None
            
    def update_journey_status(self, journey_id: str, status: str) -> None:
        """Update journey status in test database
        
        Args:
            journey_id: Journey ID to update
            status: New status
        """
        self.transformation_table.update_item(
            Key={
                'pk': f'JOURNEY#{journey_id}',
                'sk': f'JOURNEY#{journey_id}'
            },
            UpdateExpression='SET #status = :status, updatedAt = :updated',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': status,
                ':updated': datetime.now(timezone.utc).isoformat()
            }
        )
