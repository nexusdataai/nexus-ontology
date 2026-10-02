"""
Unit tests for journey utility scripts

Tests functionality of:
- create_complete_journey.py
- delete_journey.py  
- run_transformation_job.py
- cleanup_dynamodb_table.py
- cleanup_incomplete_journeys.py
- setup_dynamodb.py
- inspect_dynamodb_table.py
- update_raw_analysis_steps.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call, mock_open
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal
import json
import uuid
import subprocess

# Add scripts path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../scripts/journey-scripts'))


class TestCreateCompleteJourney:
    """Test suite for create_complete_journey.py functionality."""
    
    @patch('subprocess.run')
    def test_create_complete_journey_with_defaults(self, mock_run):
        """Test creating a complete journey with default stages and rules."""
        # Setup mock
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps({
            'journeyId': 'JRN-TEST001',
            'status': 'created'
        })
        
        # Import and test
        from create_complete_journey import create_complete_journey
        
        journey_data = {
            'name': 'Test Journey',
            'odaComponentType': 'TMF620_ProductCatalog'
        }
        
        result = create_complete_journey(
            journey_data,
            create_default_stages=True,
            create_default_rules=True
        )
        
        # Verify
        assert result is not None
        assert 'JRN-' in result
    
    @patch('subprocess.run')
    def test_create_journey_validation(self, mock_run):
        """Test journey creation with validation."""
        from create_complete_journey import validate_journey_data
        
        # Valid data
        valid_data = {
            'name': 'Test Journey',
            'odaComponentType': 'TMF620_ProductCatalog',
            'priority': 'high'
        }
        assert validate_journey_data(valid_data) is True
        
        # Invalid data - missing required field
        invalid_data = {
            'odaComponentType': 'TMF620_ProductCatalog'
        }
        assert validate_journey_data(invalid_data) is False


class TestDeleteJourney:
    """Test suite for delete_journey.py functionality."""
    
    @patch('subprocess.run')
    def test_delete_journey_with_confirmation(self, mock_run):
        """Test deleting a journey with confirmation."""
        # Setup mock
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'Journey deleted successfully'
        
        # Import and test
        from delete_journey import delete_journey_complete
        
        result = delete_journey_complete('JRN-TEST001', confirm=True)
        
        # Verify
        assert result is True
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_delete_journey_without_confirmation(self, mock_run):
        """Test deleting a journey without confirmation fails."""
        from delete_journey import delete_journey_complete
        
        result = delete_journey_complete('JRN-TEST001', confirm=False)
        
        # Verify
        assert result is False
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_delete_non_existent_journey(self, mock_run):
        """Test deleting non-existent journey."""
        # Setup mock
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = 'Journey not found'
        
        from delete_journey import delete_journey_complete
        
        result = delete_journey_complete('NON-EXISTENT', confirm=True)
        
        # Verify
        assert result is False


class TestRunTransformationJob:
    """Test suite for run_transformation_job.py functionality."""
    
    @patch('boto3.client')
    def test_run_transformation_job(self, mock_boto_client):
        """Test running a transformation job."""
        # Setup mock
        mock_lambda = MagicMock()
        mock_boto_client.return_value = mock_lambda
        mock_lambda.invoke.return_value = {
            'StatusCode': 200,
            'Payload': MagicMock(read=lambda: json.dumps({
                'jobId': 'JOB-001',
                'status': 'started'
            }).encode())
        }
        
        from run_transformation_job import run_job
        
        result = run_job('JRN-TEST001', 'raw_analysis', 'test-user')
        
        # Verify
        assert result is not None
        assert 'JOB-' in result
        mock_lambda.invoke.assert_called_once()
    
    @patch('boto3.client')
    def test_monitor_job_status(self, mock_boto_client):
        """Test monitoring job status."""
        # Setup mock
        mock_dynamodb = MagicMock()
        mock_boto_client.return_value = mock_dynamodb
        mock_dynamodb.query.return_value = {
            'Items': [{
                'Data': {
                    'jobId': 'JOB-001',
                    'status': 'completed',
                    'progress': 100
                }
            }]
        }
        
        from run_transformation_job import get_job_status
        
        status = get_job_status('JRN-TEST001', 'JOB-001')
        
        # Verify
        assert status == 'completed'


class TestCleanupDynamoDB:
    """Test suite for cleanup_dynamodb_table.py functionality."""
    
    @patch('boto3.resource')
    def test_cleanup_old_journeys(self, mock_boto_resource):
        """Test cleaning up old journeys."""
        # Setup mock
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        
        # Mock scan results
        mock_table.scan.return_value = {
            'Items': [
                {
                    'PK': 'JOURNEY#OLD-001',
                    'SK': 'METADATA',
                    'UpdatedAt': '2020-01-01T00:00:00Z'
                }
            ]
        }
        
        batch_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = Mock(return_value=batch_writer)
        mock_table.batch_writer.return_value.__exit__ = Mock()
        
        from cleanup_dynamodb_table import cleanup_old_journeys
        
        deleted = cleanup_old_journeys(days_old=365)
        
        # Verify
        assert deleted > 0
        batch_writer.delete_item.assert_called()
    
    @patch('boto3.resource')
    def test_cleanup_incomplete_journeys(self, mock_boto_resource):
        """Test cleaning up incomplete journeys."""
        # Setup mock
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        
        mock_table.scan.return_value = {
            'Items': [
                {
                    'PK': 'JOURNEY#INCOMPLETE-001',
                    'Data': {
                        'status': 'failed',
                        'progress': 50
                    }
                }
            ]
        }
        
        from cleanup_incomplete_journeys import cleanup_incomplete
        
        result = cleanup_incomplete(status='failed')
        
        # Verify
        assert result is True


class TestSetupDynamoDB:
    """Test suite for setup_dynamodb.py functionality."""
    
    @patch('boto3.client')
    def test_create_table(self, mock_boto_client):
        """Test creating DynamoDB table."""
        # Setup mock
        mock_dynamodb = MagicMock()
        mock_boto_client.return_value = mock_dynamodb
        mock_dynamodb.create_table.return_value = {
            'TableDescription': {
                'TableName': 'test-table',
                'TableStatus': 'CREATING'
            }
        }
        
        from setup_dynamodb import create_table
        
        result = create_table('test-table')
        
        # Verify
        assert result is True
        mock_dynamodb.create_table.assert_called_once()
    
    @patch('boto3.client')
    def test_table_already_exists(self, mock_boto_client):
        """Test handling table that already exists."""
        # Setup mock
        mock_dynamodb = MagicMock()
        mock_boto_client.return_value = mock_dynamodb
        mock_dynamodb.describe_table.return_value = {
            'Table': {'TableStatus': 'ACTIVE'}
        }
        
        from setup_dynamodb import check_table_exists
        
        exists = check_table_exists('test-table')
        
        # Verify
        assert exists is True


class TestInspectDynamoDB:
    """Test suite for inspect_dynamodb_table.py functionality."""
    
    @patch('boto3.resource')
    def test_inspect_table_structure(self, mock_boto_resource):
        """Test inspecting table structure."""
        # Setup mock
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        
        mock_table.scan.return_value = {
            'Items': [
                {'PK': 'JOURNEY#JRN-001', 'SK': 'METADATA'},
                {'PK': 'JOURNEY#JRN-001', 'SK': 'STAGE#1#raw_analysis'},
                {'PK': 'JOURNEY#JRN-002', 'SK': 'METADATA'}
            ],
            'Count': 3
        }
        
        from inspect_dynamodb_table import get_table_statistics
        
        stats = get_table_statistics('test-table')
        
        # Verify
        assert stats['total_items'] == 3
        assert stats['journey_count'] == 2
    
    @patch('boto3.resource')
    def test_analyze_data_patterns(self, mock_boto_resource):
        """Test analyzing data patterns in table."""
        # Setup mock
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        
        mock_table.scan.return_value = {
            'Items': [
                {'PK': 'JOURNEY#JRN-001', 'EntityType': 'Journey'},
                {'PK': 'STAGE#STAGE-001', 'EntityType': 'Stage'},
                {'PK': 'RULE#RULE-001', 'EntityType': 'Rule'}
            ]
        }
        
        from inspect_dynamodb_table import analyze_entity_distribution
        
        distribution = analyze_entity_distribution('test-table')
        
        # Verify
        assert 'Journey' in distribution
        assert 'Stage' in distribution
        assert 'Rule' in distribution


class TestUpdateRawAnalysisSteps:
    """Test suite for update_raw_analysis_steps.py functionality."""
    
    @patch('boto3.resource')
    def test_update_raw_analysis_configuration(self, mock_boto_resource):
        """Test updating raw analysis stage configuration."""
        # Setup mock
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        
        mock_table.query.return_value = {
            'Items': [{
                'PK': 'JOURNEY#JRN-001',
                'SK': 'STAGE#1#raw_analysis',
                'Data': {
                    'stageId': 'raw_analysis',
                    'configuration': {}
                }
            }]
        }
        
        mock_table.update_item.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        from update_raw_analysis_steps import update_analysis_steps
        
        new_steps = [
            {'name': 'extract_text', 'enabled': True},
            {'name': 'analyze_structure', 'enabled': True}
        ]
        
        result = update_analysis_steps('JRN-001', new_steps)
        
        # Verify
        assert result is True
        mock_table.update_item.assert_called_once()
    
    @patch('boto3.resource')
    def test_add_analysis_step(self, mock_boto_resource):
        """Test adding a new analysis step."""
        # Setup mock
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        
        from update_raw_analysis_steps import add_analysis_step
        
        step = {
            'name': 'custom_analysis',
            'description': 'Custom analysis step',
            'order': 10
        }
        
        result = add_analysis_step('JRN-001', step)
        
        # Verify
        assert result is True


# ==================== Integration Test ====================

class TestJourneyScriptsIntegration:
    """Integration tests for journey scripts working together."""
    
    @patch('boto3.resource')
    @patch('boto3.client')
    def test_complete_journey_lifecycle(self, mock_client, mock_resource):
        """Test complete journey lifecycle from creation to deletion."""
        # Setup mocks
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        
        # 1. Create journey
        from create_complete_journey import create_complete_journey
        journey_data = {
            'name': 'Integration Test Journey',
            'odaComponentType': 'TMF620_ProductCatalog'
        }
        
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        journey_id = 'JRN-INTEGRATION-001'
        
        # 2. Run transformation job
        from run_transformation_job import run_job
        mock_lambda = MagicMock()
        mock_client.return_value = mock_lambda
        mock_lambda.invoke.return_value = {
            'StatusCode': 200,
            'Payload': MagicMock(read=lambda: json.dumps({'jobId': 'JOB-001'}).encode())
        }
        
        job_id = run_job(journey_id, 'raw_analysis', 'test-user')
        assert job_id is not None
        
        # 3. Delete journey
        from delete_journey import delete_journey_complete
        batch_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = Mock(return_value=batch_writer)
        mock_table.batch_writer.return_value.__exit__ = Mock()
        mock_table.query.return_value = {'Items': [{'PK': f'JOURNEY#{journey_id}'}]}
        
        result = delete_journey_complete(journey_id, confirm=True)
        assert result is True
