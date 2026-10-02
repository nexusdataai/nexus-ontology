"""
Comprehensive unit tests for manage_journey.py

Tests all functionality of the ComprehensiveJourneyManager class.
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

from manage_journey import ComprehensiveJourneyManager


class TestComprehensiveJourneyManager:
    """Test suite for ComprehensiveJourneyManager."""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_dynamodb_table, mock_boto3_session):
        """Set up test environment before each test."""
        # Inject mock table to avoid real AWS calls
        self.manager = ComprehensiveJourneyManager(table=mock_dynamodb_table)
        self.mock_session = mock_boto3_session
    
    # ==================== Journey CRUD Tests ====================
    
    def test_list_journeys_success(self, mock_dynamodb_table):
        """Test successful journey listing."""
        # Setup mock response
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'GSI1PK': 'JOURNEYS',
                    'GSI1SK': 'JRN-001',
                    'Data': {
                        'journeyId': 'JRN-001',
                        'name': 'Test Journey 1',
                        'status': 'pending'
                    }
                },
                {
                    'GSI1PK': 'JOURNEYS',
                    'GSI1SK': 'JRN-002',
                    'Data': {
                        'journeyId': 'JRN-002',
                        'name': 'Test Journey 2',
                        'status': 'running'
                    }
                }
            ]
        }
        
        # Execute
        journeys = self.manager.list_journeys()
        
        # Verify
        assert len(journeys) == 2
        assert journeys[0]['journeyId'] == 'JRN-001'
        assert journeys[1]['status'] == 'running'
        mock_dynamodb_table.query.assert_called_once()
    
    def test_list_journeys_with_filter(self, mock_dynamodb_table):
        """Test journey listing with status filter."""
        # Setup mock response
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'GSI1PK': 'JOURNEYS',
                    'GSI1SK': 'JRN-001',
                    'Data': {
                        'journeyId': 'JRN-001',
                        'name': 'Test Journey 1',
                        'status': 'pending'
                    }
                }
            ]
        }
        
        # Execute
        journeys = self.manager.list_journeys(status_filter='pending')
        
        # Verify
        assert len(journeys) == 1
        assert journeys[0]['status'] == 'pending'
    
    def test_get_journey_complete_success(self, mock_dynamodb_table):
        """Test successful retrieval of complete journey."""
        journey_id = 'JRN-001'
        
        # Setup mock responses for journey, stages, and rules
        mock_dynamodb_table.query.side_effect = [
            # Journey metadata
            {
                'Items': [{
                    'PK': f'JOURNEY#{journey_id}',
                    'SK': 'METADATA',
                    'Data': {
                        'journeyId': journey_id,
                        'name': 'Test Journey'
                    }
                }]
            },
            # Stages
            {
                'Items': [{
                    'PK': f'JOURNEY#{journey_id}',
                    'SK': 'STAGE#1#raw_analysis',
                    'Data': {
                        'stageId': 'raw_analysis',
                        'stageName': 'Raw Analysis'
                    }
                }]
            },
            # Rules
            {
                'Items': [{
                    'PK': f'JOURNEY#{journey_id}',
                    'SK': 'RULE#raw_analysis#RULE-001',
                    'Data': {
                        'ruleId': 'RULE-001',
                        'ruleName': 'Test Rule'
                    }
                }]
            }
        ]
        
        # Execute
        journey = self.manager.get_journey_complete(journey_id)
        
        # Verify
        assert journey is not None
        assert journey['journeyId'] == journey_id
        assert 'stages' in journey
        assert 'rules' in journey
        assert len(journey['stages']) == 1
        assert len(journey['rules']) == 1
    
    def test_create_journey_complete_success(self, mock_dynamodb_table, sample_journey_data):
        """Test successful creation of complete journey."""
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        mock_dynamodb_table.batch_writer.return_value.__enter__ = Mock(return_value=Mock())
        mock_dynamodb_table.batch_writer.return_value.__exit__ = Mock()
        
        # Execute
        journey_id = self.manager.create_journey_complete(
            sample_journey_data,
            create_default_stages=True,
            create_default_rules=True
        )
        
        # Verify
        assert journey_id is not None
        assert journey_id.startswith('JRN-')
        mock_dynamodb_table.put_item.assert_called()
    
    def test_update_journey_metadata_success(self, mock_dynamodb_table):
        """Test successful journey metadata update."""
        journey_id = 'JRN-001'
        update_data = {'status': 'running', 'progress': 25}
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'PK': f'JOURNEY#{journey_id}', 'SK': 'METADATA'}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.update_journey_metadata(journey_id, update_data)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called_once()
    
    def test_delete_journey_complete_success(self, mock_dynamodb_table):
        """Test successful deletion of complete journey."""
        journey_id = 'JRN-001'
        
        # Setup mock for query to get all journey items
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'PK': f'JOURNEY#{journey_id}', 'SK': 'METADATA'},
                {'PK': f'JOURNEY#{journey_id}', 'SK': 'STAGE#1#raw_analysis'},
                {'PK': f'JOURNEY#{journey_id}', 'SK': 'RULE#raw_analysis#RULE-001'}
            ]
        }
        
        # Setup batch writer mock
        batch_writer = MagicMock()
        mock_dynamodb_table.batch_writer.return_value.__enter__ = Mock(return_value=batch_writer)
        mock_dynamodb_table.batch_writer.return_value.__exit__ = Mock()
        
        # Execute
        result = self.manager.delete_journey_complete(journey_id, confirm=True)
        
        # Verify
        assert result is True
        mock_dynamodb_table.query.assert_called()
        batch_writer.delete_item.assert_called()
    
    # ==================== Stage Management Tests ====================
    
    def test_list_stages_success(self, mock_dynamodb_table):
        """Test successful stage listing."""
        journey_id = 'JRN-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'STAGE#1#raw_analysis',
                    'Data': {'stageId': 'raw_analysis', 'order': 1}
                },
                {
                    'SK': 'STAGE#2#stripped_schema',  
                    'Data': {'stageId': 'stripped_schema', 'order': 2}
                }
            ]
        }
        
        # Execute
        stages = self.manager.list_stages(journey_id)
        
        # Verify
        assert len(stages) == 2
        assert stages[0]['stageId'] == 'raw_analysis'
        assert stages[1]['order'] == 2
    
    def test_add_stage_success(self, mock_dynamodb_table, sample_stage_data):
        """Test successful stage addition."""
        journey_id = 'JRN-001'
        
        # Setup mocks
        mock_dynamodb_table.query.side_effect = [
            {'Items': [{'SK': 'METADATA'}]},  # Journey exists
            {'Items': []}  # No existing stage
        ]
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.add_stage(journey_id, sample_stage_data)
        
        # Verify
        assert result is True
        mock_dynamodb_table.put_item.assert_called_once()
    
    def test_update_stage_success(self, mock_dynamodb_table):
        """Test successful stage update."""
        journey_id = 'JRN-001'
        stage_id = 'raw_analysis'
        update_data = {'status': 'completed', 'progress': 100}
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'STAGE#1#raw_analysis', 'Data': {'stageId': stage_id}}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.update_stage(journey_id, stage_id, update_data)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called_once()
    
    def test_delete_stage_success(self, mock_dynamodb_table):
        """Test successful stage deletion."""
        journey_id = 'JRN-001'
        stage_id = 'raw_analysis'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'STAGE#1#raw_analysis'}]
        }
        mock_dynamodb_table.delete_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.delete_stage(journey_id, stage_id, confirm=True)
        
        # Verify
        assert result is True
        mock_dynamodb_table.delete_item.assert_called()
    
    # ==================== Rule Management Tests ====================
    
    def test_list_rules_success(self, mock_dynamodb_table):
        """Test successful rule listing."""
        journey_id = 'JRN-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'RULE#raw_analysis#RULE-001',
                    'Data': {'ruleId': 'RULE-001', 'priority': 'high'}
                },
                {
                    'SK': 'RULE#raw_analysis#RULE-002',
                    'Data': {'ruleId': 'RULE-002', 'priority': 'medium'}
                }
            ]
        }
        
        # Execute
        rules = self.manager.list_rules(journey_id)
        
        # Verify
        assert len(rules) == 2
        assert rules[0]['ruleId'] == 'RULE-001'
    
    def test_add_rule_success(self, mock_dynamodb_table, sample_rule_data):
        """Test successful rule addition."""
        journey_id = 'JRN-001'
        stage_id = 'raw_analysis'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {'Items': []}  # No existing rule
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.add_rule(journey_id, stage_id, sample_rule_data)
        
        # Verify
        assert result is True
        mock_dynamodb_table.put_item.assert_called_once()
    
    # ==================== Job Management Tests ====================
    
    def test_list_jobs_success(self, mock_dynamodb_table):
        """Test successful job listing."""
        journey_id = 'JRN-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'JOB#2024-01-01T00:00:00Z#JOB-001',
                    'Data': {'jobId': 'JOB-001', 'status': 'running'}
                }
            ]
        }
        
        # Execute
        jobs = self.manager.list_jobs(journey_id)
        
        # Verify
        assert len(jobs) == 1
        assert jobs[0]['jobId'] == 'JOB-001'
    
    def test_run_job_success(self, mock_dynamodb_table):
        """Test successful job execution."""
        journey_id = 'JRN-001'
        stage_id = 'raw_analysis'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'STAGE#1#raw_analysis'}]  # Stage exists
        }
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        job_id = self.manager.run_job(journey_id, stage_id, triggered_by='test-user')
        
        # Verify
        assert job_id is not None
        assert job_id.startswith('JOB-')
        mock_dynamodb_table.put_item.assert_called()
    
    def test_cancel_job_success(self, mock_dynamodb_table):
        """Test successful job cancellation."""
        journey_id = 'JRN-001'
        job_id = 'JOB-001'
        
        # Setup mocks
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': f'JOB#2024-01-01T00:00:00Z#{job_id}', 'Data': {'status': 'running'}}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.cancel_job(journey_id, job_id)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called()
    
    # ==================== Log Management Tests ====================
    
    def test_get_job_logs_success(self, mock_dynamodb_table, mock_s3_client):
        """Test successful job log retrieval."""
        self.manager.s3_client = mock_s3_client
        journey_id = 'JRN-001'
        stage_name = 'raw_analysis'
        job_id = 'JOB-001'
        
        # Setup S3 mock
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps({
                'logs': [
                    {'timestamp': '2024-01-01T00:00:00Z', 'message': 'Test log'}
                ]
            }).encode('utf-8'))
        }
        
        # Execute
        logs = self.manager.get_job_logs(journey_id, stage_name, job_id)
        
        # Verify
        assert logs is not None
        assert 'logs' in logs
        mock_s3_client.get_object.assert_called()
    
    def test_search_logs_success(self, mock_dynamodb_table):
        """Test successful log search."""
        journey_id = 'JRN-001'
        search_query = 'error'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'LOG#2024-01-01T00:00:00Z#LOG-001',
                    'Data': {
                        'message': 'Error occurred',
                        'level': 'ERROR'
                    }
                }
            ]
        }
        
        # Execute
        results = self.manager.search_logs(journey_id, search_query)
        
        # Verify
        assert results is not None
        assert 'results' in results
    
    # ==================== Import/Export Tests ====================
    
    @patch('builtins.open', create=True)
    def test_export_journey_complete_success(self, mock_open, mock_dynamodb_table):
        """Test successful journey export."""
        journey_id = 'JRN-001'
        output_file = 'export.json'
        
        # Setup mocks
        mock_dynamodb_table.query.side_effect = [
            # Journey metadata
            {'Items': [{'Data': {'journeyId': journey_id}}]},
            # Stages
            {'Items': []},
            # Rules
            {'Items': []}
        ]
        
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Execute
        result = self.manager.export_journey_complete(journey_id, output_file)
        
        # Verify
        assert result is True
        mock_file.write.assert_called()
    
    @patch('builtins.open', create=True)
    def test_import_journey_complete_success(self, mock_open, mock_dynamodb_table):
        """Test successful journey import."""
        input_file = 'import.json'
        
        # Setup mock file content
        import_data = {
            'journey': {'name': 'Imported Journey'},
            'stages': [],
            'rules': []
        }
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(import_data)
        
        # Setup DynamoDB mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        journey_id = self.manager.import_journey_complete(input_file)
        
        # Verify
        assert journey_id is not None
        assert journey_id.startswith('JRN-')
    
    # ==================== Utility Function Tests ====================
    
    def test_clean_journey_id(self):
        """Test journey ID cleaning."""
        assert self.manager.clean_journey_id('JRN-001') == 'JRN-001'
        assert self.manager.clean_journey_id('JOURNEY#JRN-001') == 'JRN-001'
        assert self.manager.clean_journey_id('jrn-001') == 'JRN-001'
    
    def test_validate_journey_exists(self, mock_dynamodb_table):
        """Test journey existence validation."""
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{'SK': 'METADATA'}]
        }
        
        # Execute
        exists = self.manager.validate_journey_exists('JRN-001')
        
        # Verify
        assert exists is True
    
    def test_convert_floats_to_decimal(self):
        """Test float to Decimal conversion."""
        data = {
            'float_val': 1.5,
            'int_val': 10,
            'str_val': 'test',
            'nested': {
                'float': 2.5
            },
            'list': [1.0, 2, 'three']
        }
        
        result = self.manager.convert_floats_to_decimal(data)
        
        assert isinstance(result['float_val'], Decimal)
        assert isinstance(result['nested']['float'], Decimal)
        assert isinstance(result['list'][0], Decimal)
        assert result['int_val'] == 10
        assert result['str_val'] == 'test'
    
    # ==================== Error Handling Tests ====================
    
    def test_get_journey_not_found(self, mock_dynamodb_table):
        """Test getting non-existent journey."""
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        result = self.manager.get_journey_complete('NON-EXISTENT')
        
        assert result is None
    
    def test_update_non_existent_journey(self, mock_dynamodb_table):
        """Test updating non-existent journey."""
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        result = self.manager.update_journey_metadata('NON-EXISTENT', {})
        
        assert result is False
    
    def test_delete_without_confirmation(self, mock_dynamodb_table):
        """Test deletion without confirmation."""
        result = self.manager.delete_journey_complete('JRN-001', confirm=False)
        
        assert result is False
        mock_dynamodb_table.delete_item.assert_not_called()
    
    def test_add_duplicate_stage(self, mock_dynamodb_table):
        """Test adding duplicate stage."""
        journey_id = 'JRN-001'
        
        # Setup mock - stage already exists
        mock_dynamodb_table.query.side_effect = [
            {'Items': [{'SK': 'METADATA'}]},  # Journey exists
            {'Items': [{'SK': 'STAGE#1#raw_analysis'}]}  # Stage exists
        ]
        
        result = self.manager.add_stage(journey_id, {'stageId': 'raw_analysis'})
        
        assert result is False
