"""
Unit tests for manage_second_brain_rules.py

Tests all functionality of the SecondBrainRuleManager class.
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../scripts/journey-scripts'))

from manage_second_brain_rules import SecondBrainRuleManager


class TestSecondBrainRuleManager:
    """Test suite for SecondBrainRuleManager."""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_dynamodb_table, mock_boto3_session):
        """Set up test environment before each test."""
        # Inject mock table to avoid real AWS calls
        self.manager = SecondBrainRuleManager(table=mock_dynamodb_table)
        self.mock_session = mock_boto3_session
    
    def test_list_rules_for_journey(self, mock_dynamodb_table):
        """Test listing rules for a specific journey."""
        journey_id = 'JRN-TEST001'
        
        # Setup mock response
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'PK': f'JOURNEY#{journey_id}',
                    'SK': 'RULE#raw_analysis#RULE-001',
                    'Data': {
                        'ruleId': 'RULE-001',
                        'ruleName': 'Field Mapping Rule',
                        'ruleType': 'field_mapping',
                        'priority': 'high',
                        'isActive': True,
                        'stageId': 'raw_analysis'
                    }
                },
                {
                    'PK': f'JOURNEY#{journey_id}',
                    'SK': 'RULE#raw_analysis#RULE-002',
                    'Data': {
                        'ruleId': 'RULE-002',
                        'ruleName': 'Validation Rule',
                        'ruleType': 'validation',
                        'priority': 'medium',
                        'isActive': True,
                        'stageId': 'raw_analysis'
                    }
                }
            ]
        }
        
        # Execute
        rules = self.manager.list_rules_for_journey(journey_id)
        
        # Verify
        assert len(rules) == 2
        assert rules[0]['ruleId'] == 'RULE-001'
        assert rules[0]['ruleType'] == 'field_mapping'
        assert rules[1]['priority'] == 'medium'
    
    def test_list_rules_for_stage(self, mock_dynamodb_table):
        """Test listing rules for a specific stage."""
        journey_id = 'JRN-TEST001'
        stage_id = 'raw_analysis'
        
        # Setup mock response
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'RULE#raw_analysis#RULE-001',
                    'Data': {
                        'ruleId': 'RULE-001',
                        'stageId': 'raw_analysis',
                        'isActive': True
                    }
                }
            ]
        }
        
        # Execute
        rules = self.manager.list_rules_for_stage(journey_id, stage_id)
        
        # Verify
        assert len(rules) == 1
        assert rules[0]['stageId'] == 'raw_analysis'
    
    def test_get_rule_details(self, mock_dynamodb_table):
        """Test getting detailed rule information."""
        journey_id = 'JRN-TEST001'
        rule_id = 'RULE-001'
        stage_id = 'raw_analysis'
        
        # Setup mock response
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'SK': f'RULE#{stage_id}#{rule_id}',
                'Data': {
                    'ruleId': 'RULE-001',
                    'ruleName': 'Field Mapping Rule',
                    'description': 'Maps source fields to TMF fields',
                    'ruleType': 'field_mapping',
                    'priority': 'high',
                    'conditions': {
                        'sourceField': 'product_name',
                        'targetField': 'name'
                    },
                    'actions': {
                        'mappingType': 'direct'
                    }
                }
            }]
        }
        
        # Execute
        rule = self.manager.get_rule_details(journey_id, rule_id, stage_id)
        
        # Verify
        assert rule is not None
        assert rule['ruleId'] == 'RULE-001'
        assert rule['conditions']['sourceField'] == 'product_name'
    
    def test_create_rule(self, mock_dynamodb_table):
        """Test creating a new rule."""
        journey_id = 'JRN-TEST001'
        stage_id = 'raw_analysis'
        rule_data = {
            'ruleId': 'RULE-NEW',
            'ruleName': 'New Validation Rule',
            'ruleType': 'validation',
            'description': 'Validates data format',
            'priority': 'high',
            'isActive': True,
            'conditions': {
                'field': 'price',
                'operator': 'greater_than',
                'value': 0
            },
            'actions': {
                'onFailure': 'reject'
            }
        }
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {'Items': []}  # No existing rule
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.create_rule(journey_id, stage_id, rule_data)
        
        # Verify
        assert result is True
        mock_dynamodb_table.put_item.assert_called_once()
        
        # Verify the put_item call
        put_call = mock_dynamodb_table.put_item.call_args
        item = put_call.kwargs['Item']
        assert item['PK'] == f'JOURNEY#{journey_id}'
        assert f'RULE#{stage_id}#RULE-NEW' in item['SK']
    
    def test_update_rule(self, mock_dynamodb_table):
        """Test updating an existing rule."""
        journey_id = 'JRN-TEST001'
        rule_id = 'RULE-001'
        stage_id = 'raw_analysis'
        update_data = {
            'priority': 'critical',
            'isActive': False,
            'description': 'Updated description'
        }
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': f'RULE#{stage_id}#{rule_id}'}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.update_rule(journey_id, rule_id, stage_id, update_data)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called_once()
    
    def test_delete_rule(self, mock_dynamodb_table):
        """Test deleting a rule."""
        journey_id = 'JRN-TEST001'
        rule_id = 'RULE-001'
        stage_id = 'raw_analysis'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': f'RULE#{stage_id}#{rule_id}'}]
        }
        mock_dynamodb_table.delete_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.delete_rule(journey_id, rule_id, stage_id)
        
        # Verify
        assert result is True
        mock_dynamodb_table.delete_item.assert_called()
    
    def test_activate_rule(self, mock_dynamodb_table):
        """Test activating a rule."""
        journey_id = 'JRN-TEST001'
        rule_id = 'RULE-001'
        stage_id = 'raw_analysis'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': f'RULE#{stage_id}#{rule_id}'}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.activate_rule(journey_id, rule_id, stage_id)
        
        # Verify
        assert result is True
        # Verify isActive was set to True
        update_call = mock_dynamodb_table.update_item.call_args
        assert 'UpdateExpression' in update_call.kwargs
    
    def test_deactivate_rule(self, mock_dynamodb_table):
        """Test deactivating a rule."""
        journey_id = 'JRN-TEST001'
        rule_id = 'RULE-001'
        stage_id = 'raw_analysis'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': f'RULE#{stage_id}#{rule_id}'}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.deactivate_rule(journey_id, rule_id, stage_id)
        
        # Verify
        assert result is True
    
    def test_add_default_rules(self, mock_dynamodb_table):
        """Test adding default rules for a component type."""
        journey_id = 'JRN-TEST001'
        component_type = 'TMF620_ProductCatalog'
        
        # Setup batch writer mock
        batch_writer = MagicMock()
        mock_dynamodb_table.batch_writer.return_value.__enter__ = Mock(return_value=batch_writer)
        mock_dynamodb_table.batch_writer.return_value.__exit__ = Mock()
        
        # Execute
        result = self.manager.add_default_rules(journey_id, component_type)
        
        # Verify
        assert result is True
        mock_dynamodb_table.batch_writer.assert_called()
        # Should create multiple default rules
        assert batch_writer.put_item.call_count > 0
    
    def test_get_rules_by_type(self, mock_dynamodb_table):
        """Test getting rules filtered by type."""
        journey_id = 'JRN-TEST001'
        rule_type = 'field_mapping'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'RULE#raw_analysis#RULE-001',
                    'Data': {
                        'ruleId': 'RULE-001',
                        'ruleType': 'field_mapping'
                    }
                },
                {
                    'SK': 'RULE#raw_analysis#RULE-002',
                    'Data': {
                        'ruleId': 'RULE-002',
                        'ruleType': 'validation'
                    }
                }
            ]
        }
        
        # Execute
        rules = self.manager.get_rules_by_type(journey_id, rule_type)
        
        # Verify - should only return field_mapping rules
        assert len(rules) == 1
        assert rules[0]['ruleType'] == 'field_mapping'
    
    def test_get_rules_by_priority(self, mock_dynamodb_table):
        """Test getting rules filtered by priority."""
        journey_id = 'JRN-TEST001'
        priority = 'high'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'RULE#raw_analysis#RULE-001',
                    'Data': {
                        'ruleId': 'RULE-001',
                        'priority': 'high'
                    }
                },
                {
                    'SK': 'RULE#raw_analysis#RULE-002',
                    'Data': {
                        'ruleId': 'RULE-002',
                        'priority': 'medium'
                    }
                }
            ]
        }
        
        # Execute
        rules = self.manager.get_rules_by_priority(journey_id, priority)
        
        # Verify
        assert len(rules) == 1
        assert rules[0]['priority'] == 'high'
    
    def test_get_active_rules(self, mock_dynamodb_table):
        """Test getting only active rules."""
        journey_id = 'JRN-TEST001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'RULE#raw_analysis#RULE-001',
                    'Data': {
                        'ruleId': 'RULE-001',
                        'isActive': True
                    }
                },
                {
                    'SK': 'RULE#raw_analysis#RULE-002',
                    'Data': {
                        'ruleId': 'RULE-002',
                        'isActive': False
                    }
                }
            ]
        }
        
        # Execute
        rules = self.manager.get_active_rules(journey_id)
        
        # Verify - should only return active rules
        assert len(rules) == 1
        assert rules[0]['isActive'] is True
    
    def test_validate_rule_conditions(self):
        """Test validating rule conditions."""
        rule_data = {
            'conditions': {
                'sourceField': 'price',
                'operator': 'greater_than',
                'value': 0
            }
        }
        
        # Execute
        valid = self.manager.validate_rule_conditions(rule_data)
        
        # Verify
        assert valid is True
    
    def test_execute_rule_actions(self, mock_dynamodb_table):
        """Test executing rule actions."""
        journey_id = 'JRN-TEST001'
        rule_id = 'RULE-001'
        
        # Mock rule retrieval
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'PK': f'JOURNEY#{journey_id}',
                'SK': f'RULE#{rule_id}',
                'Data': {
                    'ruleId': rule_id,
                    'enabled': True,
                    'actions': {
                        'mappingType': 'direct',
                        'transformation': 'uppercase'
                    }
                }
            }]
        }
        
        context = {'field': 'test'}
        
        # Execute
        result = self.manager.execute_rule_actions(journey_id, rule_id, context)
        
        # Verify
        assert result is not None
        assert result['success'] is True
    
    # ==================== Error Handling Tests ====================
    
    def test_create_duplicate_rule(self, mock_dynamodb_table):
        """Test creating duplicate rule."""
        journey_id = 'JRN-TEST001'
        stage_id = 'raw_analysis'
        
        # Setup mock - rule already exists
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'RULE#raw_analysis#RULE-001'}]
        }
        
        # Execute
        result = self.manager.create_rule(journey_id, stage_id, {'ruleId': 'RULE-001'})
        
        # Verify
        assert result is False
    
    def test_update_non_existent_rule(self, mock_dynamodb_table):
        """Test updating non-existent rule."""
        journey_id = 'JRN-TEST001'
        
        # Setup mock - rule doesn't exist
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        # Execute
        result = self.manager.update_rule(journey_id, 'non_existent', 'raw_analysis', {})
        
        # Verify
        assert result is False
    
    def test_get_rule_details_not_found(self, mock_dynamodb_table):
        """Test getting details for non-existent rule."""
        # Setup mock
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        # Execute
        rule = self.manager.get_rule_details('JRN-TEST001', 'non_existent', 'raw_analysis')
        
        # Verify
        assert rule is None
    
    def test_invalid_rule_type(self, mock_dynamodb_table):
        """Test creating rule with invalid type."""
        journey_id = 'JRN-TEST001'
        stage_id = 'raw_analysis'
        
        rule_data = {
            'ruleId': 'RULE-INVALID',
            'ruleType': 'invalid_type'  # Invalid type
        }
        
        # Execute
        result = self.manager.create_rule(journey_id, stage_id, rule_data)
        
        # Verify - should fail validation
        assert result is False
