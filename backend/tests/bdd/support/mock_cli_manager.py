#!/usr/bin/env python3
"""
Mock CLI Manager that overrides AWS client creation
This module provides a way to run the CLI with mocked AWS services
"""

import os
import sys
import json
import tempfile
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock
import boto3
from moto import mock_aws

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


class MockedCLIManager:
    """Manages CLI execution with mocked AWS services"""
    
    def __init__(self):
        self.mock_aws = None
        self.dynamodb_resource = None
        self.s3_client = None
        self.tables_created = False
        
    def start_mocks(self):
        """Start AWS mocks"""
        self.mock_aws = mock_aws()
        self.mock_aws.start()
        
        # Create mocked resources
        self.dynamodb_resource = boto3.resource('dynamodb', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Create required tables
        self._create_tables()
        
        return self
    
    def stop_mocks(self):
        """Stop AWS mocks"""
        if self.mock_aws:
            self.mock_aws.stop()
    
    def _create_tables(self):
        """Create DynamoDB tables for testing"""
        if self.tables_created:
            return
            
        # Create TransformationSystem table
        try:
            self.dynamodb_resource.create_table(
                TableName='TransformationSystem',
                KeySchema=[
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'},
                    {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                    {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
                    {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
                    {'AttributeName': 'GSI2SK', 'AttributeType': 'S'},
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'GSI1',
                        'KeySchema': [
                            {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                            {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    },
                    {
                        'IndexName': 'GSI2',
                        'KeySchema': [
                            {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                            {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Create transformation jobs table
            self.dynamodb_resource.create_table(
                TableName='aurorastack-transformation-jobs',
                KeySchema=[
                    {'AttributeName': 'journeyId', 'KeyType': 'HASH'},
                    {'AttributeName': 'entityType', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'journeyId', 'AttributeType': 'S'},
                    {'AttributeName': 'entityType', 'AttributeType': 'S'},
                    {'AttributeName': 'status', 'AttributeType': 'S'},
                    {'AttributeName': 'createdAt', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'StatusIndex',
                        'KeySchema': [
                            {'AttributeName': 'status', 'KeyType': 'HASH'},
                            {'AttributeName': 'createdAt', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            self.tables_created = True
            
        except Exception as e:
            # Tables might already exist
            pass
    
    def add_test_journey(self, journey_data: Dict[str, Any]) -> str:
        """Add a test journey to DynamoDB"""
        table = self.dynamodb_resource.Table('TransformationSystem')
        
        journey_id = journey_data.get('journeyId', f"JRN-TEST-{os.urandom(3).hex()}")
        
        # Store in TransformationSystem table format
        item = {
            'PK': f"JOURNEY#{journey_id}",
            'SK': 'METADATA',
            'journeyId': journey_id,
            'name': journey_data.get('name', 'Test Journey'),
            'description': journey_data.get('description', 'Test Description'),
            'status': journey_data.get('status', 'pending'),
            'priority': journey_data.get('priority', 'medium'),
            'odaComponentType': journey_data.get('odaComponentType', 'Customer Management'),
            'createdAt': journey_data.get('createdAt', '2025-01-01T00:00:00Z'),
            'updatedAt': journey_data.get('updatedAt', '2025-01-01T00:00:00Z'),
            'createdBy': journey_data.get('createdBy', 'test-user@example.com'),
            'GSI1PK': 'JOURNEY',
            'GSI1SK': f"STATUS#{journey_data.get('status', 'pending')}#{journey_id}"
        }
        
        table.put_item(Item=item)
        
        # Also add to transformation-jobs table for compatibility
        jobs_table = self.dynamodb_resource.Table('aurorastack-transformation-jobs')
        jobs_item = {
            'journeyId': journey_id,
            'entityType': 'JOURNEY#METADATA',
            **journey_data
        }
        jobs_table.put_item(Item=jobs_item)
        
        return journey_id
    
    def get_dynamodb_resource(self):
        """Get mocked DynamoDB resource"""
        return self.dynamodb_resource
    
    def get_s3_client(self):
        """Get mocked S3 client"""
        return self.s3_client


def run_cli_with_mocked_aws():
    """Run the CLI with mocked AWS services"""
    manager = MockedCLIManager()
    manager.start_mocks()
    
    # Patch boto3 to use our mocked resources
    with patch('boto3.resource') as mock_resource, \
         patch('boto3.client') as mock_client:
        
        mock_resource.return_value = manager.dynamodb_resource
        mock_client.return_value = manager.s3_client
        
        # Import and run the CLI
        spec = importlib.util.spec_from_file_location(
            "journey_manager",
            os.path.join(project_root, 'scripts', 'actors', 'journeys', 'journey-manager.py')
        )
        journey_manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(journey_manager)
        
        # Create and run the manager
        cli_manager = journey_manager.EnhancedJourneyManager()
        cli_manager.run()
        
    manager.stop_mocks()


if __name__ == '__main__':
    run_cli_with_mocked_aws()
