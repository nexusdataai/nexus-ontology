"""
Unit tests for manage_capability.py

Tests all functionality of the CapabilityManager and InteractiveCapabilityWizard classes.
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

from manage_capability import CapabilityManager, InteractiveCapabilityWizard


class TestCapabilityManager:
    """Test suite for CapabilityManager."""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_dynamodb_table, mock_boto3_session):
        """Set up test environment before each test."""
        # Inject mock dynamodb to avoid real AWS calls
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_dynamodb_table
        self.manager = CapabilityManager(dynamodb=mock_dynamodb)
        self.manager.table = mock_dynamodb_table
        self.mock_session = mock_boto3_session
    
    # ==================== Capability CRUD Tests ====================
    
    def test_list_capabilities_success(self, mock_dynamodb_table):
        """Test successful capability listing."""
        # Setup mock response
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'GSI1PK': 'CAPABILITIES',
                    'GSI1SK': 'CAP-001',
                    'Name': 'Customer Management',
                    'Status': 'active',
                    'BusinessDomain': 'Customer Experience',
                    'HealthScore': 85
                },
                {
                    'GSI1PK': 'CAPABILITIES',
                    'GSI1SK': 'CAP-002',
                    'Name': 'Order Processing',
                    'Status': 'active',
                    'BusinessDomain': 'Operations',
                    'HealthScore': 92
                }
            ]
        }
        
        # Execute
        capabilities = self.manager.list_capabilities()
        
        # Verify
        assert len(capabilities) == 2
        assert capabilities[0]['GSI1SK'] == 'CAP-001'
        assert capabilities[0]['Name'] == 'Customer Management'
        assert capabilities[1]['HealthScore'] == 92
        mock_dynamodb_table.query.assert_called_once()
    
    def test_list_capabilities_by_domain(self, mock_dynamodb_table):
        """Test listing capabilities filtered by business domain."""
        # Setup mock response
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'GSI1PK': 'DOMAIN#Customer Experience',
                    'GSI1SK': 'CAP-001',
                    'Name': 'Customer Management',
                    'BusinessDomain': 'Customer Experience'
                }
            ]
        }
        
        # Execute
        capabilities = self.manager.list_capabilities_by_domain('Customer Experience')
        
        # Verify
        assert len(capabilities) == 1
        assert capabilities[0]['BusinessDomain'] == 'Customer Experience'
    
    def test_get_capability_success(self, mock_dynamodb_table):
        """Test successful retrieval of capability details."""
        capability_id = 'CAP-001'
        
        # Setup mock response
        mock_dynamodb_table.get_item.return_value = {
            'Item': {
                'PK': f'CAPABILITY#{capability_id}',
                'SK': 'METADATA',
                'CapabilityId': capability_id,
                'Name': 'Customer Management',
                'Description': 'Manage customer data',
                'Status': 'active',
                'HealthScore': 85
            }
        }
        
        # Execute
        capability = self.manager.get_capability(capability_id)
        
        # Verify
        assert capability is not None
        assert capability['CapabilityId'] == capability_id
        assert capability['Name'] == 'Customer Management'
        assert capability['HealthScore'] == 85
    
    def test_create_capability_success(self, mock_dynamodb_table, sample_capability_data):
        """Test successful creation of a capability."""
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        capability_id = self.manager.create_capability(sample_capability_data)
        
        # Verify
        assert capability_id is not None
        assert capability_id.startswith('CAP-')
        mock_dynamodb_table.put_item.assert_called_once()
        
        # Verify the put_item call
        put_call = mock_dynamodb_table.put_item.call_args
        item = put_call.kwargs['Item']
        assert 'CAPABILITY#' in item['PK']
        assert item['SK'] == 'METADATA'
    
    def test_update_capability_success(self, mock_dynamodb_table):
        """Test successful capability update."""
        capability_id = 'CAP-001'
        update_data = {
            'status': 'inactive',
            'healthScore': 70,
            'description': 'Updated description'
        }
        
        # Setup mocks
        mock_dynamodb_table.get_item.return_value = {
            'Item': {'PK': f'CAPABILITY#{capability_id}', 'SK': 'METADATA'}
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.update_capability(capability_id, update_data)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called_once()
    
    def test_delete_capability_success(self, mock_dynamodb_table):
        """Test successful capability deletion."""
        capability_id = 'CAP-001'
        
        # Setup mock for query to get all related items
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'PK': f'CAPABILITY#{capability_id}', 'SK': 'METADATA'},
                {'PK': f'CAPABILITY#{capability_id}', 'SK': 'COMPONENT#1#COMP-001'},
                {'PK': f'CAPABILITY#{capability_id}', 'SK': 'METRIC#COMP-001#latency#2024-01-01'}
            ]
        }
        
        # Setup batch writer mock
        batch_writer = MagicMock()
        mock_dynamodb_table.batch_writer.return_value.__enter__ = Mock(return_value=batch_writer)
        mock_dynamodb_table.batch_writer.return_value.__exit__ = Mock()
        
        # Execute
        result = self.manager.delete_capability(capability_id)
        
        # Verify
        assert result is True
        mock_dynamodb_table.query.assert_called()
        batch_writer.delete_item.assert_called()
    
    # ==================== Health Score Tests ====================
    
    def test_calculate_health_score(self, mock_dynamodb_table):
        """Test health score calculation for a capability."""
        capability_id = 'CAP-001'
        
        # Setup mock - return components with health metrics
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'COMPONENT#1#COMP-001',
                    'HealthScore': 90,
                    'Availability': 99.9,
                    'ErrorRate': 0.1
                },
                {
                    'SK': 'COMPONENT#2#COMP-002',
                    'HealthScore': 80,
                    'Availability': 99.5,
                    'ErrorRate': 0.5
                }
            ]
        }
        
        # Execute
        health_score = self.manager.calculate_health_score(capability_id)
        
        # Verify
        assert health_score > 0
        assert health_score <= 100
    
    def test_get_capability_health_status(self, mock_dynamodb_table):
        """Test getting health status of a capability."""
        capability_id = 'CAP-001'
        
        # Setup mock
        mock_dynamodb_table.get_item.return_value = {
            'Item': {
                'HealthScore': 85,
                'Status': 'active',
                'LastHealthCheck': datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Execute
        health_status = self.manager.get_capability_health_status(capability_id)
        
        # Verify
        assert health_status is not None
        assert 'HealthScore' in health_status
        assert health_status['HealthScore'] == 85
    
    # ==================== Component Association Tests ====================
    
    def test_list_capability_components(self, mock_dynamodb_table):
        """Test listing components of a capability."""
        capability_id = 'CAP-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'COMPONENT#1#COMP-001',
                    'ComponentId': 'COMP-001',
                    'ComponentName': 'Customer API',
                    'ComponentType': 'microservice'
                },
                {
                    'SK': 'COMPONENT#2#COMP-002',
                    'ComponentId': 'COMP-002',
                    'ComponentName': 'Customer Database',
                    'ComponentType': 'database'
                }
            ]
        }
        
        # Execute
        components = self.manager.list_capability_components(capability_id)
        
        # Verify
        assert len(components) == 2
        assert components[0]['ComponentId'] == 'COMP-001'
        assert components[1]['ComponentType'] == 'database'
    
    def test_get_capability_metrics_summary(self, mock_dynamodb_table):
        """Test getting metrics summary for a capability."""
        capability_id = 'CAP-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'METRIC#COMP-001#latency#2024-01-01T00:00:00Z',
                    'Value': 45.5,
                    'MetricType': 'latency'
                },
                {
                    'SK': 'METRIC#COMP-001#throughput#2024-01-01T00:00:00Z',
                    'Value': 1000,
                    'MetricType': 'throughput'
                }
            ]
        }
        
        # Execute
        metrics = self.manager.get_capability_metrics_summary(capability_id)
        
        # Verify
        assert metrics is not None
        assert 'metrics' in metrics or len(metrics) > 0
    
    # ==================== Search and Filter Tests ====================
    
    def test_search_capabilities(self, mock_dynamodb_table):
        """Test searching capabilities by keyword."""
        # Setup mock
        mock_dynamodb_table.scan.return_value = {
            'Items': [
                {
                    'Name': 'Customer Management',
                    'Description': 'Manage customer data',
                    'Tags': ['customer', 'crm']
                },
                {
                    'Name': 'Order Processing',
                    'Description': 'Process customer orders',
                    'Tags': ['order', 'fulfillment']
                }
            ]
        }
        
        # Execute
        results = self.manager.search_capabilities('customer')
        
        # Verify
        assert len(results) >= 1
        assert any('customer' in str(item).lower() for item in results)
    
    def test_get_capabilities_by_status(self, mock_dynamodb_table):
        """Test filtering capabilities by status."""
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'GSI1SK': 'CAP-001',
                    'Status': 'active'
                },
                {
                    'GSI1SK': 'CAP-002',
                    'Status': 'active'
                }
            ]
        }
        
        # Execute
        capabilities = self.manager.get_capabilities_by_status('active')
        
        # Verify
        assert len(capabilities) > 0
        assert all(cap.get('Status') == 'active' for cap in capabilities)
    
    # ==================== Error Handling Tests ====================
    
    def test_get_non_existent_capability(self, mock_dynamodb_table):
        """Test getting non-existent capability."""
        mock_dynamodb_table.get_item.return_value = {'Item': None}
        
        result = self.manager.get_capability('NON-EXISTENT')
        
        assert result is None
    
    def test_update_non_existent_capability(self, mock_dynamodb_table):
        """Test updating non-existent capability."""
        mock_dynamodb_table.get_item.return_value = {'Item': None}
        
        result = self.manager.update_capability('NON-EXISTENT', {})
        
        assert result is False
    
    def test_create_capability_with_invalid_data(self, mock_dynamodb_table):
        """Test creating capability with invalid data."""
        invalid_data = {
            # Missing required 'name' field
            'description': 'Test'
        }
        
        # Execute
        result = self.manager.create_capability(invalid_data)
        
        # Verify
        assert result is None or result is False
    
    def test_handle_dynamodb_exception(self, mock_dynamodb_table):
        """Test handling DynamoDB exceptions."""
        # Setup mock to raise exception
        mock_dynamodb_table.put_item.side_effect = Exception("DynamoDB error")
        
        # Execute
        result = self.manager.create_capability({'name': 'Test'})
        
        # Verify
        assert result is None or result is False


class TestInteractiveCapabilityWizard:
    """Test suite for InteractiveCapabilityWizard."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment before each test."""
        with patch('manage_capability.CapabilityManager') as mock_manager:
            self.wizard = InteractiveCapabilityWizard()
            self.wizard.manager = mock_manager()
    
    @patch('builtins.input')
    def test_create_capability_interactive(self, mock_input):
        """Test interactive capability creation."""
        # Setup mock inputs
        mock_input.side_effect = [
            'Customer Management',  # Name
            'Manage customer data and interactions',  # Description
            'Customer Experience',  # Business Domain
            'high',  # Criticality
            'product-team',  # Owner
            'customer, crm, core'  # Tags
        ]
        
        # Setup mock manager
        self.wizard.manager.create_capability.return_value = 'CAP-001'
        
        # Execute
        capability_id = self.wizard.create_capability_interactive()
        
        # Verify
        assert capability_id == 'CAP-001'
        self.wizard.manager.create_capability.assert_called_once()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_display_capability_menu(self, mock_print, mock_input):
        """Test displaying capability management menu."""
        # Setup mock input
        mock_input.return_value = '0'  # Exit
        
        # Execute
        self.wizard.display_menu()
        
        # Verify menu was displayed
        assert mock_print.called
    
    def test_format_capability_display(self):
        """Test formatting capability for display."""
        capability = {
            'CapabilityId': 'CAP-001',
            'Name': 'Customer Management',
            'Status': 'active',
            'HealthScore': 85
        }
        
        # Execute
        formatted = self.wizard.format_capability_display(capability)
        
        # Verify
        assert formatted is not None
        assert 'CAP-001' in formatted
        assert 'Customer Management' in formatted
    
    @patch('builtins.input')
    def test_validate_user_input(self, mock_input):
        """Test user input validation."""
        # Test required field validation
        mock_input.side_effect = ['', 'Valid Input']
        
        # Execute
        result = self.wizard.get_required_input('Enter name')
        
        # Verify
        assert result == 'Valid Input'
    
    def test_display_health_dashboard(self):
        """Test displaying capability health dashboard."""
        # Setup mock data
        self.wizard.manager.list_capabilities.return_value = [
            {'Name': 'Cap1', 'HealthScore': 90},
            {'Name': 'Cap2', 'HealthScore': 75}
        ]
        
        # Execute
        dashboard = self.wizard.generate_health_dashboard()
        
        # Verify
        assert dashboard is not None
        assert len(dashboard) == 2
