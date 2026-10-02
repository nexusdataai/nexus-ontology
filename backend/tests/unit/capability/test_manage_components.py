"""
Unit tests for manage_components.py

Tests all functionality of the ComponentManager and InteractiveComponentWizard classes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal
import json
import uuid

# Add scripts path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../scripts/capability-scripts'))

from manage_components import ComponentManager, InteractiveComponentWizard


class TestComponentManager:
    """Test suite for ComponentManager."""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_dynamodb_table, mock_s3_client, mock_boto3_session):
        """Set up test environment before each test."""
        # Inject mock dynamodb to avoid real AWS calls
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_dynamodb_table
        self.manager = ComponentManager(dynamodb=mock_dynamodb)
        self.manager.table = mock_dynamodb_table
        self.manager.s3_client = mock_s3_client
        self.mock_session = mock_boto3_session
    
    # ==================== Component CRUD Tests ====================
    
    def test_list_components_for_capability(self, mock_dynamodb_table):
        """Test listing components for a specific capability."""
        capability_id = 'CAP-001'
        
        # Setup mock response
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'PK': f'CAPABILITY#{capability_id}',
                    'SK': 'COMPONENT#1#COMP-001',
                    'ComponentId': 'COMP-001',
                    'ComponentName': 'Customer API',
                    'ComponentType': 'microservice',
                    'Status': 'deployed',
                    'HealthScore': 90
                },
                {
                    'PK': f'CAPABILITY#{capability_id}',
                    'SK': 'COMPONENT#2#COMP-002',
                    'ComponentId': 'COMP-002',
                    'ComponentName': 'Customer Database',
                    'ComponentType': 'database',
                    'Status': 'deployed',
                    'HealthScore': 85
                }
            ]
        }
        
        # Execute
        components = self.manager.list_components(capability_id)
        
        # Verify
        assert len(components) == 2
        assert components[0]['ComponentId'] == 'COMP-001'
        assert components[0]['ComponentType'] == 'microservice'
        assert components[1]['HealthScore'] == 85
    
    def test_get_component_details(self, mock_dynamodb_table):
        """Test getting detailed component information."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock response
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'PK': f'CAPABILITY#{capability_id}',
                'SK': 'COMPONENT#1#COMP-001',
                'ComponentId': component_id,
                'ComponentName': 'Customer API',
                'ComponentType': 'microservice',
                'Version': '2.1.0',
                'Technology': 'Node.js',
                'Repository': 'https://github.com/org/customer-api',
                'Configuration': {
                    'port': 8080,
                    'replicas': 3
                },
                'HealthScore': 90
            }]
        }
        
        # Execute
        component = self.manager.get_component(capability_id, component_id)
        
        # Verify
        assert component is not None
        assert component['ComponentId'] == component_id
        assert component['Version'] == '2.1.0'
        assert component['Configuration']['port'] == 8080
    
    def test_create_component_success(self, mock_dynamodb_table, sample_component_data):
        """Test successful creation of a component."""
        capability_id = 'CAP-001'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {'Items': []}  # No existing component
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        component_id = self.manager.create_component(capability_id, sample_component_data)
        
        # Verify
        assert component_id is not None
        assert component_id.startswith('COMP-')
        mock_dynamodb_table.put_item.assert_called_once()
        
        # Verify the put_item call
        put_call = mock_dynamodb_table.put_item.call_args
        item = put_call.kwargs['Item']
        assert f'CAPABILITY#{capability_id}' in item['PK']
        assert 'COMPONENT#' in item['SK']
    
    def test_update_component_success(self, mock_dynamodb_table):
        """Test successful component update."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        update_data = {
            'version': '2.2.0',
            'status': 'updating',
            'healthScore': 88
        }
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'COMPONENT#1#COMP-001'}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.update_component(capability_id, component_id, update_data)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called_once()
    
    def test_delete_component_success(self, mock_dynamodb_table):
        """Test successful component deletion."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'COMPONENT#1#COMP-001'}]
        }
        mock_dynamodb_table.delete_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.delete_component(capability_id, component_id)
        
        # Verify
        assert result is True
        mock_dynamodb_table.delete_item.assert_called()
    
    # ==================== Dependency Management Tests ====================
    
    def test_add_component_dependency(self, mock_dynamodb_table):
        """Test adding a dependency between components."""
        capability_id = 'CAP-001'
        source_component = 'COMP-001'
        target_component = 'COMP-002'
        dependency_data = {
            'type': 'runtime',
            'criticality': 'high',
            'version': '^1.0.0'
        }
        
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.add_dependency(
            capability_id, source_component, target_component, dependency_data
        )
        
        # Verify
        assert result is True
        mock_dynamodb_table.put_item.assert_called_once()
    
    def test_list_component_dependencies(self, mock_dynamodb_table):
        """Test listing dependencies for a component."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'DEPENDENCY#COMP-001#COMP-002',
                    'SourceComponent': 'COMP-001',
                    'TargetComponent': 'COMP-002',
                    'DependencyType': 'runtime',
                    'Criticality': 'high'
                },
                {
                    'SK': 'DEPENDENCY#COMP-001#COMP-003',
                    'SourceComponent': 'COMP-001',
                    'TargetComponent': 'COMP-003',
                    'DependencyType': 'compile',
                    'Criticality': 'medium'
                }
            ]
        }
        
        # Execute
        dependencies = self.manager.list_dependencies(capability_id, component_id)
        
        # Verify
        assert len(dependencies) == 2
        assert dependencies[0]['TargetComponent'] == 'COMP-002'
        assert dependencies[1]['DependencyType'] == 'compile'
    
    def test_remove_component_dependency(self, mock_dynamodb_table):
        """Test removing a dependency between components."""
        capability_id = 'CAP-001'
        source = 'COMP-001'
        target = 'COMP-002'
        
        # Setup mock
        mock_dynamodb_table.delete_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.remove_dependency(capability_id, source, target)
        
        # Verify
        assert result is True
        mock_dynamodb_table.delete_item.assert_called_once()
    
    # ==================== Health Management Tests ====================
    
    def test_update_component_health(self, mock_dynamodb_table):
        """Test updating component health metrics."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        health_data = {
            'healthScore': 92,
            'availability': 99.95,
            'responseTime': 45,
            'errorRate': 0.05
        }
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'COMPONENT#1#COMP-001'}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.update_component_health(capability_id, component_id, health_data)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called_once()
    
    def test_get_component_health_history(self, mock_dynamodb_table):
        """Test retrieving component health history."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': f'METRIC#{component_id}#health#2024-01-01T00:00:00Z',
                    'Value': 90,
                    'Timestamp': '2024-01-01T00:00:00Z'
                },
                {
                    'SK': f'METRIC#{component_id}#health#2024-01-01T01:00:00Z',
                    'Value': 92,
                    'Timestamp': '2024-01-01T01:00:00Z'
                }
            ]
        }
        
        # Execute
        history = self.manager.get_health_history(capability_id, component_id)
        
        # Verify
        assert len(history) == 2
        assert history[0]['Value'] == 90
        assert history[1]['Value'] == 92
    
    # ==================== Component Type Management Tests ====================
    
    def test_list_components_by_type(self, mock_dynamodb_table):
        """Test listing components filtered by type."""
        component_type = 'microservice'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'GSI1PK': f'COMPONENT#{component_type}',
                    'GSI1SK': 'COMP-001',
                    'ComponentName': 'Customer API',
                    'ComponentType': 'microservice'
                },
                {
                    'GSI1PK': f'COMPONENT#{component_type}',
                    'GSI1SK': 'COMP-002',
                    'ComponentName': 'Order API',
                    'ComponentType': 'microservice'
                }
            ]
        }
        
        # Execute
        components = self.manager.list_components_by_type(component_type)
        
        # Verify
        assert len(components) == 2
        assert all(c['ComponentType'] == 'microservice' for c in components)
    
    # ==================== Configuration Management Tests ====================
    
    def test_update_component_configuration(self, mock_dynamodb_table):
        """Test updating component configuration."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        new_config = {
            'port': 8081,
            'replicas': 5,
            'memory': '1024Mi',
            'cpu': '500m'
        }
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'COMPONENT#1#COMP-001'}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.update_configuration(capability_id, component_id, new_config)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called_once()
    
    def test_validate_component_configuration(self):
        """Test component configuration validation."""
        valid_config = {
            'port': 8080,
            'replicas': 3,
            'memory': '512Mi',
            'cpu': '250m'
        }
        
        invalid_config = {
            'port': -1,  # Invalid port
            'replicas': 0  # Invalid replica count
        }
        
        # Execute
        assert self.manager.validate_configuration(valid_config) is True
        assert self.manager.validate_configuration(invalid_config) is False
    
    # ==================== Artifact Management Tests ====================
    
    def test_store_component_artifact(self, mock_s3_client):
        """Test storing component artifacts in S3."""
        component_id = 'COMP-001'
        artifact_type = 'deployment'
        artifact_content = b'deployment configuration content'
        
        # Setup mock
        mock_s3_client.put_object.return_value = {
            'ETag': '"test-etag"',
            'VersionId': 'v1'
        }
        
        # Execute
        result = self.manager.store_artifact(component_id, artifact_type, artifact_content)
        
        # Verify
        assert result is not None
        mock_s3_client.put_object.assert_called_once()
    
    def test_retrieve_component_artifact(self, mock_s3_client):
        """Test retrieving component artifacts from S3."""
        component_id = 'COMP-001'
        artifact_type = 'deployment'
        
        # Setup mock
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'artifact content'),
            'ContentType': 'application/octet-stream'
        }
        
        # Execute
        artifact = self.manager.get_artifact(component_id, artifact_type)
        
        # Verify
        assert artifact is not None
        mock_s3_client.get_object.assert_called_once()
    
    # ==================== Error Handling Tests ====================
    
    def test_create_duplicate_component(self, mock_dynamodb_table):
        """Test creating duplicate component."""
        capability_id = 'CAP-001'
        
        # Setup mock - component already exists
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'COMPONENT#1#COMP-001'}]
        }
        
        # Execute
        result = self.manager.create_component(capability_id, {'componentId': 'COMP-001'})
        
        # Verify
        assert result is False or result is None
    
    def test_update_non_existent_component(self, mock_dynamodb_table):
        """Test updating non-existent component."""
        capability_id = 'CAP-001'
        
        # Setup mock - component doesn't exist
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        # Execute
        result = self.manager.update_component(capability_id, 'NON-EXISTENT', {})
        
        # Verify
        assert result is False
    
    def test_handle_circular_dependency(self, mock_dynamodb_table):
        """Test handling circular dependencies."""
        capability_id = 'CAP-001'
        
        # Setup mock - existing dependencies that would create a circle
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'SourceComponent': 'COMP-002', 'TargetComponent': 'COMP-001'}
            ]
        }
        
        # Execute - try to add reverse dependency
        result = self.manager.add_dependency(
            capability_id, 'COMP-001', 'COMP-002', {'type': 'runtime'}
        )
        
        # Verify
        assert result is False  # Should prevent circular dependency


class TestInteractiveComponentWizard:
    """Test suite for InteractiveComponentWizard."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment before each test."""
        with patch('manage_components.ComponentManager') as mock_manager:
            self.wizard = InteractiveComponentWizard()
            self.wizard.manager = mock_manager()
    
    @patch('builtins.input')
    def test_create_component_interactive(self, mock_input):
        """Test interactive component creation."""
        # Setup mock inputs
        mock_input.side_effect = [
            'Customer API',  # Name
            'microservice',  # Type
            '2.1.0',  # Version
            'Node.js',  # Technology
            'https://github.com/org/customer-api',  # Repository
            'deployed'  # Status
        ]
        
        # Setup mock manager
        self.wizard.manager.create_component.return_value = 'COMP-001'
        
        # Execute
        component_id = self.wizard.create_component_interactive('CAP-001')
        
        # Verify
        assert component_id == 'COMP-001'
        self.wizard.manager.create_component.assert_called_once()
    
    @patch('builtins.print')
    def test_display_dependency_graph(self, mock_print):
        """Test displaying component dependency graph."""
        # Setup mock data
        self.wizard.manager.list_components.return_value = [
            {'ComponentId': 'COMP-001', 'ComponentName': 'API'},
            {'ComponentId': 'COMP-002', 'ComponentName': 'DB'}
        ]
        self.wizard.manager.list_dependencies.return_value = [
            {'SourceComponent': 'COMP-001', 'TargetComponent': 'COMP-002'}
        ]
        
        # Execute
        self.wizard.display_dependency_graph('CAP-001')
        
        # Verify graph was displayed
        assert mock_print.called
    
    def test_format_component_health(self):
        """Test formatting component health display."""
        component = {
            'ComponentId': 'COMP-001',
            'ComponentName': 'Customer API',
            'HealthScore': 92,
            'Status': 'healthy'
        }
        
        # Execute
        formatted = self.wizard.format_health_display(component)
        
        # Verify
        assert formatted is not None
        assert '92' in formatted
        assert 'healthy' in formatted.lower()
