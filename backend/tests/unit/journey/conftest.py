"""
Pytest fixtures for journey unit tests.

This module provides common fixtures, mocks, and test data for testing journey-related scripts.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import boto3
from datetime import datetime, timezone
from decimal import Decimal
import json
import uuid


@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table with default responses."""
    table = MagicMock()
    table.name = 'tmf-oda-transformation-journey-test'
    
    # Default mock responses for common operations
    # get_item - default to journey exists
    table.get_item.return_value = {
        'Item': {
            'PK': 'JOURNEY#TEST',
            'SK': 'METADATA',
            'journeyId': 'TEST'
        }
    }
    
    # query - default to empty
    table.query.return_value = {
        'Items': [],
        'Count': 0
    }
    
    # scan - default to empty
    table.scan.return_value = {
        'Items': [],
        'Count': 0,
        'ScannedCount': 0
    }
    
    # put_item - default success
    table.put_item.return_value = {
        'ResponseMetadata': {'HTTPStatusCode': 200}
    }
    
    # update_item - default success
    table.update_item.return_value = {
        'ResponseMetadata': {'HTTPStatusCode': 200}
    }
    
    # delete_item - default success
    table.delete_item.return_value = {
        'ResponseMetadata': {'HTTPStatusCode': 200}
    }
    
    return table


@pytest.fixture
def mock_dynamodb_resource():
    """Mock DynamoDB resource."""
    resource = MagicMock()
    return resource


@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDB client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_journey_id():
    """Generate a sample journey ID."""
    return f"JRN-{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture
def sample_journey_data():
    """Sample journey data for testing."""
    return {
        'journeyId': 'JRN-TEST001',
        'name': 'Test Journey',
        'description': 'Test journey description',
        'status': 'pending',
        'priority': 'medium',
        'odaComponentType': 'TMF620_ProductCatalog',
        'owner': 'test-user',
        'overallProgress': 0,
        'currentStageId': 'raw_analysis',
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'updatedAt': datetime.now(timezone.utc).isoformat(),
        'metadata': {
            'source': 'test',
            'version': '1.0'
        },
        'configuration': {
            'enableML': True,
            'autoApprove': False
        }
    }


@pytest.fixture
def sample_stage_data():
    """Sample stage data for testing."""
    return {
        'stageId': 'raw_analysis',
        'stageName': 'Raw Input Analysis',
        'description': 'Analyze raw input documents',
        'order': 1,
        'status': 'pending',
        'progress': 0,
        'startedAt': None,
        'completedAt': None,
        'configuration': {
            'timeout': 3600,
            'retries': 3
        },
        'inputs': ['source_document.pdf'],
        'outputs': [],
        'metrics': {
            'duration': 0,
            'errors': 0
        }
    }


@pytest.fixture
def sample_rule_data():
    """Sample Second Brain rule data for testing."""
    return {
        'ruleId': 'RULE-001',
        'ruleName': 'Field Mapping Rule',
        'ruleType': 'field_mapping',
        'description': 'Map source fields to TMF fields',
        'priority': 'high',
        'isActive': True,
        'scope': 'journey',
        'conditions': {
            'sourceField': 'product_name',
            'targetField': 'name'
        },
        'actions': {
            'mappingType': 'direct',
            'transformation': None
        },
        'validation': {
            'required': True,
            'dataType': 'string'
        },
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'updatedAt': datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return {
        'jobId': f"JOB-{uuid.uuid4().hex[:8].upper()}",
        'journeyId': 'JRN-TEST001',
        'stageId': 'raw_analysis',
        'status': 'running',
        'progress': 50,
        'triggeredBy': 'test-user',
        'reason': 'Manual trigger for testing',
        'startedAt': datetime.now(timezone.utc).isoformat(),
        'completedAt': None,
        'duration': 0,
        'attempts': 1,
        'maxAttempts': 3,
        'logs': [],
        'errors': [],
        'metrics': {
            'inputSize': 1024,
            'outputSize': 0,
            'recordsProcessed': 0
        },
        'configuration': {
            'timeout': 3600,
            'parallelism': 4
        }
    }


@pytest.fixture
def mock_boto3_session(mock_dynamodb_resource, mock_dynamodb_client, mock_s3_client):
    """Mock boto3 session with all required services."""
    with patch('boto3.resource') as mock_resource:
        with patch('boto3.client') as mock_client:
            # Configure DynamoDB resource
            mock_resource.return_value = mock_dynamodb_resource
            
            # Configure clients based on service name
            def client_side_effect(service_name, **kwargs):
                if service_name == 'dynamodb':
                    return mock_dynamodb_client
                elif service_name == 's3':
                    return mock_s3_client
                else:
                    return MagicMock()
            
            mock_client.side_effect = client_side_effect
            
            yield {
                'dynamodb_resource': mock_dynamodb_resource,
                'dynamodb_client': mock_dynamodb_client,
                's3_client': mock_s3_client
            }


@pytest.fixture
def mock_table_operations(mock_dynamodb_table):
    """Mock common DynamoDB table operations."""
    # Mock scan operation
    mock_dynamodb_table.scan.return_value = {
        'Items': [],
        'Count': 0,
        'ScannedCount': 0
    }
    
    # Mock query operation
    mock_dynamodb_table.query.return_value = {
        'Items': [],
        'Count': 0
    }
    
    # Mock get_item operation
    mock_dynamodb_table.get_item.return_value = {
        'Item': None
    }
    
    # Mock put_item operation
    mock_dynamodb_table.put_item.return_value = {
        'ResponseMetadata': {'HTTPStatusCode': 200}
    }
    
    # Mock update_item operation
    mock_dynamodb_table.update_item.return_value = {
        'ResponseMetadata': {'HTTPStatusCode': 200}
    }
    
    # Mock delete_item operation
    mock_dynamodb_table.delete_item.return_value = {
        'ResponseMetadata': {'HTTPStatusCode': 200}
    }
    
    # Mock batch operations
    mock_dynamodb_table.batch_writer.return_value.__enter__ = Mock()
    mock_dynamodb_table.batch_writer.return_value.__exit__ = Mock()
    
    return mock_dynamodb_table


@pytest.fixture
def mock_s3_operations(mock_s3_client):
    """Mock common S3 operations."""
    # Mock list_buckets
    mock_s3_client.list_buckets.return_value = {
        'Buckets': [
            {'Name': 'test-bucket', 'CreationDate': datetime.now(timezone.utc)}
        ]
    }
    
    # Mock create_bucket
    mock_s3_client.create_bucket.return_value = {
        'Location': 'us-east-1'
    }
    
    # Mock put_object
    mock_s3_client.put_object.return_value = {
        'ETag': '"test-etag"'
    }
    
    # Mock get_object
    mock_s3_client.get_object.return_value = {
        'Body': MagicMock(read=lambda: b'test content'),
        'ContentType': 'application/json'
    }
    
    # Mock delete_object
    mock_s3_client.delete_object.return_value = {
        'DeleteMarker': True
    }
    
    return mock_s3_client


def create_dynamodb_item(entity_type, entity_id, sk, data=None):
    """Helper function to create a DynamoDB item."""
    item = {
        'PK': f'{entity_type}#{entity_id}',
        'SK': sk,
        'EntityType': entity_type,
        'entityID': entity_id,
        'CreatedAt': datetime.now(timezone.utc).isoformat(),
        'UpdatedAt': datetime.now(timezone.utc).isoformat()
    }
    
    if data:
        item['Data'] = data
    
    return item


def create_gsi_item(gsi_pk, gsi_sk, data=None):
    """Helper function to create a GSI item."""
    item = {
        'GSI1PK': gsi_pk,
        'GSI1SK': gsi_sk,
        'CreatedAt': datetime.now(timezone.utc).isoformat()
    }
    
    if data:
        item['Data'] = data
    
    return item
