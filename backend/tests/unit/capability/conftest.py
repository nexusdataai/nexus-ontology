"""
Pytest fixtures for capability unit tests.

This module provides common fixtures, mocks, and test data for testing
capability-related scripts.
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
    """Mock DynamoDB table for capability data with default responses."""
    table = MagicMock()
    table.name = 'business-capabilities-test'
    
    # Default mock responses for common operations
    # get_item - default success
    table.get_item.return_value = {
        'Item': {
            'PK': 'CAP#TEST',
            'SK': 'METADATA',
            'capabilityId': 'TEST'
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
def sample_capability_id():
    """Generate a sample capability ID."""
    return f"CAP-{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture
def sample_capability_data():
    """Sample capability data for testing."""
    return {
        'capabilityId': 'CAP-TEST001',
        'name': 'Customer Management',
        'description': 'Manage customer data and interactions',
        'businessDomain': 'Customer Experience',
        'status': 'active',
        'version': '1.0',
        'owner': 'product-team',
        'criticality': 'high',
        'maturityLevel': 3,
        'tags': ['customer', 'crm', 'core'],
        'metadata': {
            'createdBy': 'test-user',
            'lastReviewDate': datetime.now(timezone.utc).isoformat(),
            'complianceStatus': 'compliant'
        }
    }


@pytest.fixture
def sample_component_data():
    """Sample software component data for testing."""
    return {
        'componentId': 'COMP-001',
        'componentName': 'Customer API',
        'componentType': 'microservice',
        'version': '2.1.0',
        'status': 'deployed',
        'technology': 'Node.js',
        'repository': 'https://github.com/org/customer-api',
        'healthScore': 85,
        'configuration': {
            'port': 8080,
            'replicas': 3,
            'memory': '512Mi',
            'cpu': '250m'
        },
        'endpoints': [
            '/api/v1/customers',
            '/api/v1/customers/{id}'
        ],
        'dependencies': ['database', 'auth-service']
    }


@pytest.fixture
def sample_dependency_data():
    """Sample component dependency data."""
    return {
        'sourceComponent': 'COMP-001',
        'targetComponent': 'COMP-002',
        'dependencyType': 'runtime',
        'criticality': 'high',
        'version': '^1.0.0',
        'protocol': 'HTTP',
        'healthCheck': '/health'
    }


@pytest.fixture
def sample_job_data():
    """Sample implementation job data."""
    return {
        'jobId': f"JOB-{uuid.uuid4().hex[:8].upper()}",
        'jobType': 'deployment',
        'status': 'pending',
        'strategy': 'blue-green',
        'componentId': 'COMP-001',
        'targetVersion': '2.2.0',
        'triggeredBy': 'test-user',
        'scheduledAt': datetime.now(timezone.utc).isoformat(),
        'configuration': {
            'rollbackEnabled': True,
            'validationRequired': True,
            'approvalRequired': False
        },
        'validationCriteria': {
            'healthCheck': True,
            'smokeTest': True,
            'performanceBaseline': True
        }
    }


@pytest.fixture
def sample_metric_data():
    """Sample performance metric data."""
    return {
        'componentId': 'COMP-001',
        'metricType': 'latency',
        'value': 125.5,
        'unit': 'ms',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'tags': {
            'environment': 'production',
            'region': 'us-east-1',
            'endpoint': '/api/v1/customers'
        },
        'metadata': {
            'percentile': 'p95',
            'sampleCount': 10000
        }
    }


@pytest.fixture
def sample_health_metric():
    """Sample health metric data."""
    return {
        'componentId': 'COMP-001',
        'healthScore': 92,
        'availability': 99.95,
        'responseTime': 45,
        'errorRate': 0.05,
        'lastCheck': datetime.now(timezone.utc).isoformat(),
        'issues': [],
        'recommendations': []
    }


@pytest.fixture
def sample_configuration_rule():
    """Sample configuration rule data."""
    return {
        'ruleId': 'RULE-CONFIG-001',
        'ruleName': 'Scaling Policy',
        'ruleType': 'configuration',
        'priority': 10,
        'conditions': {
            'metric': 'cpu_utilization',
            'threshold': 70,
            'duration': 300
        },
        'actions': {
            'scaleUp': {
                'increment': 2,
                'maxInstances': 10
            }
        },
        'enabled': True
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


def create_capability_item(capability_id, data=None):
    """Helper function to create a DynamoDB capability item."""
    item = {
        'PK': f'CAPABILITY#{capability_id}',
        'SK': 'METADATA',
        'EntityType': 'Capability',
        'GSI1PK': 'CAPABILITIES',
        'GSI1SK': capability_id,
        'CreatedAt': datetime.now(timezone.utc).isoformat(),
        'UpdatedAt': datetime.now(timezone.utc).isoformat()
    }
    
    if data:
        item.update(data)
    
    return item


def create_component_item(capability_id, component_id, order, data=None):
    """Helper function to create a DynamoDB component item."""
    item = {
        'PK': f'CAPABILITY#{capability_id}',
        'SK': f'COMPONENT#{order}#{component_id}',
        'EntityType': 'Component',
        'GSI1PK': f'COMPONENT#microservice',
        'GSI1SK': component_id,
        'ComponentId': component_id,
        'Order': order,
        'CreatedAt': datetime.now(timezone.utc).isoformat()
    }
    
    if data:
        item.update(data)
    
    return item


def create_job_item(capability_id, job_id, timestamp=None):
    """Helper function to create a DynamoDB job item."""
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    
    item = {
        'PK': f'CAPABILITY#{capability_id}',
        'SK': f'JOB#{timestamp}#{job_id}',
        'EntityType': 'Job',
        'GSI1PK': f'JOB#{job_id}',
        'GSI1SK': timestamp,
        'JobId': job_id,
        'CreatedAt': timestamp
    }
    
    return item


def create_metric_item(capability_id, component_id, metric_type, timestamp=None):
    """Helper function to create a DynamoDB metric item."""
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    
    item = {
        'PK': f'CAPABILITY#{capability_id}',
        'SK': f'METRIC#{component_id}#{metric_type}#{timestamp}',
        'EntityType': 'Metric',
        'ComponentId': component_id,
        'MetricType': metric_type,
        'Timestamp': timestamp
    }
    
    return item
