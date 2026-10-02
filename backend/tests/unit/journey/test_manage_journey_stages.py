"""
Unit tests for manage_journey_stages.py

Tests all functionality of the JourneyStageManager class.
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

from manage_journey_stages import JourneyStageManager


class TestJourneyStageManager:
    """Test suite for JourneyStageManager."""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_dynamodb_table, mock_boto3_session):
        """Set up test environment before each test."""
        # Inject mock table to avoid real AWS calls
        self.manager = JourneyStageManager(table=mock_dynamodb_table)
        self.mock_session = mock_boto3_session
    
    def test_list_stages_for_journey(self, mock_dynamodb_table):
        """Test listing stages for a specific journey."""
        journey_id = 'JRN-TEST001'
        
        # Mock journey existence check
        mock_dynamodb_table.get_item.return_value = {
            'Item': {
                'PK': f'JOURNEY#{journey_id}',
                'SK': 'METADATA',
                'journeyId': journey_id
            }
        }
        
        # Setup mock response for stages query
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'PK': f'JOURNEY#{journey_id}',
                    'SK': 'STAGE#1#raw_analysis',
                    'Data': {
                        'stageId': 'raw_analysis',
                        'stageName': 'Raw Input Analysis',
                        'order': 1,
                        'status': 'pending'
                    }
                },
                {
                    'PK': f'JOURNEY#{journey_id}',
                    'SK': 'STAGE#2#stripped_schema',
                    'Data': {
                        'stageId': 'stripped_schema',
                        'stageName': 'Create Stripped Document',
                        'order': 2,
                        'status': 'pending'
                    }
                }
            ]
        }
        
        # Execute
        stages = self.manager.list_stages_for_journey(journey_id)
        
        # Verify
        assert len(stages) == 2
        assert stages[0]['stageId'] == 'raw_analysis'
        assert stages[0]['order'] == 1
        assert stages[1]['stageId'] == 'stripped_schema'
        mock_dynamodb_table.query.assert_called_once()
    
    def test_get_stage_details(self, mock_dynamodb_table):
        """Test getting detailed stage information."""
        journey_id = 'JRN-TEST001'
        stage_id = 'raw_analysis'
        
        # Setup mock response
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'PK': f'JOURNEY#{journey_id}',
                'SK': 'STAGE#1#raw_analysis',
                'Data': {
                    'stageId': 'raw_analysis',
                    'stageName': 'Raw Input Analysis',
                    'description': 'Analyze raw input documents',
                    'order': 1,
                    'status': 'pending',
                    'progress': 0,
                    'configuration': {
                        'timeout': 3600,
                        'retries': 3
                    }
                }
            }]
        }
        
        # Execute
        stage = self.manager.get_stage_details(journey_id, stage_id)
        
        # Verify
        assert stage is not None
        assert stage['stageId'] == 'raw_analysis'
        assert stage['configuration']['timeout'] == 3600
    
    def test_create_stage(self, mock_dynamodb_table):
        """Test creating a new stage."""
        journey_id = 'JRN-TEST001'
        stage_data = {
            'stageId': 'custom_stage',
            'name': 'Custom Stage',  # Required field
            'description': 'A custom processing stage',
            'order': 7,
            'status': 'pending',
            'configuration': {
                'customParam': 'value'
            }
        }
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {'Items': []}  # No existing stage
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.create_stage(journey_id, stage_data)
        
        # Verify
        assert result is True
        mock_dynamodb_table.put_item.assert_called_once()
        
        # Verify the put_item call arguments
        put_call = mock_dynamodb_table.put_item.call_args
        assert 'Item' in put_call.kwargs
        item = put_call.kwargs['Item']
        assert item['PK'] == f'JOURNEY#{journey_id}'
        assert 'STAGE#7#custom_stage' in item['SK']
    
    def test_update_stage_progress(self, mock_dynamodb_table):
        """Test updating stage progress."""
        journey_id = 'JRN-TEST001'
        stage_id = 'raw_analysis'
        
        # Setup mock - stage exists
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'PK': f'JOURNEY#{journey_id}',
                'SK': 'STAGE#1#raw_analysis',
                'Data': {'stageId': 'raw_analysis'}
            }]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.update_stage_progress(journey_id, stage_id, 50, 'running')
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called_once()
        
        # Verify update expression includes progress and status
        update_call = mock_dynamodb_table.update_item.call_args
        assert 'UpdateExpression' in update_call.kwargs
    
    def test_delete_stage(self, mock_dynamodb_table):
        """Test deleting a stage."""
        journey_id = 'JRN-TEST001'
        stage_id = 'custom_stage'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'PK': f'JOURNEY#{journey_id}',
                'SK': 'STAGE#7#custom_stage'
            }]
        }
        mock_dynamodb_table.delete_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.delete_stage(journey_id, stage_id)
        
        # Verify
        assert result is True
        mock_dynamodb_table.delete_item.assert_called()
    
    def test_add_default_stages(self, mock_dynamodb_table):
        """Test adding default TMF ODA transformation stages."""
        journey_id = 'JRN-TEST001'
        
        # Setup batch writer mock
        batch_writer = MagicMock()
        mock_dynamodb_table.batch_writer.return_value.__enter__ = Mock(return_value=batch_writer)
        mock_dynamodb_table.batch_writer.return_value.__exit__ = Mock()
        
        # Execute
        result = self.manager.add_default_stages(journey_id, 'TMF620_ProductCatalog')
        
        # Verify
        assert result is True
        mock_dynamodb_table.batch_writer.assert_called()
        # Should create 6 default stages
        assert batch_writer.put_item.call_count == 6
    
    def test_get_stage_by_order(self, mock_dynamodb_table):
        """Test getting stage by order number."""
        journey_id = 'JRN-TEST001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'SK': 'STAGE#2#stripped_schema',
                'Data': {
                    'stageId': 'stripped_schema',
                    'order': 2
                }
            }]
        }
        
        # Execute
        stage = self.manager.get_stage_by_order(journey_id, 2)
        
        # Verify
        assert stage is not None
        assert stage['stageId'] == 'stripped_schema'
        assert stage['order'] == 2
    
    def test_update_stage_configuration(self, mock_dynamodb_table):
        """Test updating stage configuration."""
        journey_id = 'JRN-TEST001'
        stage_id = 'raw_analysis'
        new_config = {
            'timeout': 7200,
            'retries': 5,
            'parallel': True
        }
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'SK': 'STAGE#1#raw_analysis',
                'Data': {'stageId': 'raw_analysis'}
            }]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.update_stage_configuration(journey_id, stage_id, new_config)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called_once()
    
    def test_mark_stage_completed(self, mock_dynamodb_table):
        """Test marking a stage as completed."""
        journey_id = 'JRN-TEST001'
        stage_id = 'raw_analysis'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'SK': 'STAGE#1#raw_analysis',
                'Data': {'stageId': 'raw_analysis'}
            }]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.mark_stage_completed(journey_id, stage_id)
        
        # Verify
        assert result is True
        # Should update status to completed and progress to 100
        update_call = mock_dynamodb_table.update_item.call_args
        assert 'UpdateExpression' in update_call.kwargs
    
    def test_get_next_stage(self, mock_dynamodb_table):
        """Test getting the next stage in sequence."""
        journey_id = 'JRN-TEST001'
        current_stage_id = 'raw_analysis'
        
        # Setup mock - return all stages
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'STAGE#1#raw_analysis',
                    'Data': {'stageId': 'raw_analysis', 'order': 1}
                },
                {
                    'SK': 'STAGE#2#stripped_schema',
                    'Data': {'stageId': 'stripped_schema', 'order': 2}
                },
                {
                    'SK': 'STAGE#3#tmf_mapping',
                    'Data': {'stageId': 'tmf_mapping', 'order': 3}
                }
            ]
        }
        
        # Execute
        next_stage = self.manager.get_next_stage(journey_id, current_stage_id)
        
        # Verify
        assert next_stage is not None
        assert next_stage['stageId'] == 'stripped_schema'
        assert next_stage['order'] == 2
    
    def test_validate_stage_dependencies(self, mock_dynamodb_table):
        """Test validating stage dependencies."""
        journey_id = 'JRN-TEST001'
        stage_id = 'tmf_mapping'
        
        # Setup mock - check if previous stages are completed
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'STAGE#1#raw_analysis',
                    'Data': {'stageId': 'raw_analysis', 'status': 'completed', 'order': 1}
                },
                {
                    'SK': 'STAGE#2#stripped_schema',
                    'Data': {'stageId': 'stripped_schema', 'status': 'completed', 'order': 2}
                }
            ]
        }
        
        # Execute
        valid = self.manager.validate_stage_dependencies(journey_id, stage_id)
        
        # Verify
        assert valid is True
    
    def test_get_stage_metrics(self, mock_dynamodb_table):
        """Test getting stage metrics."""
        journey_id = 'JRN-TEST001'
        stage_id = 'raw_analysis'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'SK': 'STAGE#1#raw_analysis',
                'Data': {
                    'stageId': 'raw_analysis',
                    'metrics': {
                        'duration': 3600,
                        'recordsProcessed': 1000,
                        'errors': 0,
                        'startedAt': '2024-01-01T00:00:00Z',
                        'completedAt': '2024-01-01T01:00:00Z'
                    }
                }
            }]
        }
        
        # Execute
        metrics = self.manager.get_stage_metrics(journey_id, stage_id)
        
        # Verify
        assert metrics is not None
        assert metrics['duration'] == 3600
        assert metrics['recordsProcessed'] == 1000
    
    # ==================== Error Handling Tests ====================
    
    def test_create_duplicate_stage(self, mock_dynamodb_table):
        """Test creating duplicate stage."""
        journey_id = 'JRN-TEST001'
        
        # Setup mock - stage already exists
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'STAGE#1#raw_analysis'}]
        }
        
        # Execute
        result = self.manager.create_stage(journey_id, {'stageId': 'raw_analysis'})
        
        # Verify
        assert result is False
    
    def test_update_non_existent_stage(self, mock_dynamodb_table):
        """Test updating non-existent stage."""
        journey_id = 'JRN-TEST001'
        
        # Setup mock - stage doesn't exist
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        # Execute
        result = self.manager.update_stage_progress(journey_id, 'non_existent', 50)
        
        # Verify
        assert result is False
    
    def test_get_stage_details_not_found(self, mock_dynamodb_table):
        """Test getting details for non-existent stage."""
        # Setup mock
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        # Execute
        stage = self.manager.get_stage_details('JRN-TEST001', 'non_existent')
        
        # Verify
        assert stage is None
    
    def test_invalid_stage_order(self, mock_dynamodb_table):
        """Test creating stage with invalid order."""
        journey_id = 'JRN-TEST001'
        
        # Setup mock
        mock_dynamodb_table.put_item.side_effect = Exception("Invalid order")
        
        # Execute
        result = self.manager.create_stage(journey_id, {
            'stageId': 'test',
            'order': -1  # Invalid negative order
        })
        
        # Verify
        assert result is False
