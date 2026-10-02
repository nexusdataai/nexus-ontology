"""
Unit tests for manage_implementation_jobs.py

Tests all functionality of the ImplementationJobManager class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import uuid

# Add scripts path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../scripts/capability-scripts'))

from manage_implementation_jobs import ImplementationJobManager


class TestImplementationJobManager:
    """Test suite for ImplementationJobManager."""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_dynamodb_table, mock_s3_client, mock_boto3_session):
        """Set up test environment before each test."""
        # Inject mock dynamodb to avoid real AWS calls
        from unittest.mock import Mock
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_dynamodb_table
        self.manager = ImplementationJobManager(dynamodb=mock_dynamodb)
        self.manager.table = mock_dynamodb_table
        self.manager.s3_client = mock_s3_client
        self.mock_session = mock_boto3_session
    
    # ==================== Job Creation Tests ====================
    
    def test_create_deployment_job(self, mock_dynamodb_table, sample_job_data):
        """Test creating a deployment job."""
        capability_id = 'CAP-001'
        
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        job_id = self.manager.create_job(capability_id, sample_job_data)
        
        # Verify
        assert job_id is not None
        assert job_id.startswith('JOB-')
        mock_dynamodb_table.put_item.assert_called_once()
        
        # Verify the put_item call
        put_call = mock_dynamodb_table.put_item.call_args
        item = put_call.kwargs['Item']
        assert f'CAPABILITY#{capability_id}' in item['PK']
        assert 'JOB#' in item['SK']
        assert item['JobType'] == sample_job_data['jobType']
    
    def test_create_migration_job(self, mock_dynamodb_table):
        """Test creating a migration job."""
        capability_id = 'CAP-001'
        job_data = {
            'jobType': 'migration',
            'componentId': 'COMP-001',
            'sourceVersion': '1.0.0',
            'targetVersion': '2.0.0',
            'strategy': 'rolling',
            'triggeredBy': 'test-user'
        }
        
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        job_id = self.manager.create_job(capability_id, job_data)
        
        # Verify
        assert job_id is not None
        assert job_id.startswith('JOB-')
    
    def test_create_scaling_job(self, mock_dynamodb_table):
        """Test creating a scaling job."""
        capability_id = 'CAP-001'
        job_data = {
            'jobType': 'scaling',
            'componentId': 'COMP-001',
            'targetReplicas': 5,
            'strategy': 'gradual',
            'triggeredBy': 'auto-scaler'
        }
        
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        job_id = self.manager.create_job(capability_id, job_data)
        
        # Verify
        assert job_id is not None
    
    # ==================== Job Retrieval Tests ====================
    
    def test_get_job_details(self, mock_dynamodb_table):
        """Test getting job details."""
        job_id = 'JOB-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'GSI1PK': f'JOB#{job_id}',
                'JobId': job_id,
                'JobType': 'deployment',
                'Status': 'running',
                'Progress': 50,
                'StartedAt': datetime.now(timezone.utc).isoformat()
            }]
        }
        
        # Execute
        job = self.manager.get_job(job_id)
        
        # Verify
        assert job is not None
        assert job['JobId'] == job_id
        assert job['Status'] == 'running'
        assert job['Progress'] == 50
    
    def test_list_jobs_for_capability(self, mock_dynamodb_table):
        """Test listing jobs for a capability."""
        capability_id = 'CAP-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': 'JOB#2024-01-01T00:00:00Z#JOB-001',
                    'JobId': 'JOB-001',
                    'JobType': 'deployment',
                    'Status': 'completed'
                },
                {
                    'SK': 'JOB#2024-01-01T01:00:00Z#JOB-002',
                    'JobId': 'JOB-002',
                    'JobType': 'scaling',
                    'Status': 'running'
                }
            ]
        }
        
        # Execute
        jobs = self.manager.list_jobs(capability_id)
        
        # Verify
        assert len(jobs) == 2
        assert jobs[0]['JobId'] == 'JOB-001'
        assert jobs[1]['Status'] == 'running'
    
    def test_list_jobs_by_status(self, mock_dynamodb_table):
        """Test listing jobs filtered by status."""
        capability_id = 'CAP-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'JobId': 'JOB-001',
                    'Status': 'running'
                },
                {
                    'JobId': 'JOB-002',
                    'Status': 'completed'
                }
            ]
        }
        
        # Execute
        running_jobs = self.manager.list_jobs_by_status(capability_id, 'running')
        
        # Verify
        assert len(running_jobs) == 1
        assert running_jobs[0]['Status'] == 'running'
    
    # ==================== Job Lifecycle Tests ====================
    
    def test_start_job(self, mock_dynamodb_table):
        """Test starting a job."""
        job_id = 'JOB-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{'JobId': job_id, 'Status': 'pending'}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.start_job(job_id)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called()
    
    def test_update_job_progress(self, mock_dynamodb_table):
        """Test updating job progress."""
        job_id = 'JOB-001'
        progress = 75
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{'JobId': job_id}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.update_job_progress(job_id, progress)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called()
    
    def test_complete_job(self, mock_dynamodb_table):
        """Test completing a job."""
        job_id = 'JOB-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{'JobId': job_id, 'Status': 'running'}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.complete_job(job_id, 'success')
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called()
    
    def test_fail_job(self, mock_dynamodb_table):
        """Test marking a job as failed."""
        job_id = 'JOB-001'
        error_message = 'Deployment failed due to health check'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{'JobId': job_id}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.fail_job(job_id, error_message)
        
        # Verify
        assert result is True
        mock_dynamodb_table.update_item.assert_called()
    
    def test_cancel_job(self, mock_dynamodb_table):
        """Test cancelling a job."""
        job_id = 'JOB-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{'JobId': job_id, 'Status': 'running'}]
        }
        mock_dynamodb_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.cancel_job(job_id, 'User requested cancellation')
        
        # Verify
        assert result is True
    
    # ==================== Rollback Tests ====================
    
    def test_create_rollback_job(self, mock_dynamodb_table):
        """Test creating a rollback job."""
        original_job_id = 'JOB-001'
        
        # Setup mock - get original job details
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'JobId': original_job_id,
                'JobType': 'deployment',
                'ComponentId': 'COMP-001',
                'SourceVersion': '1.0.0',
                'TargetVersion': '2.0.0'
            }]
        }
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        rollback_job_id = self.manager.create_rollback_job(original_job_id)
        
        # Verify
        assert rollback_job_id is not None
        assert rollback_job_id != original_job_id
        mock_dynamodb_table.put_item.assert_called()
    
    def test_rollback_deployment(self, mock_dynamodb_table):
        """Test rolling back a deployment."""
        job_id = 'JOB-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'JobId': job_id,
                'JobType': 'deployment',
                'RollbackEnabled': True
            }]
        }
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.rollback_job(job_id)
        
        # Verify
        assert result is not None
    
    # ==================== Validation Tests ====================
    
    def test_validate_job_requirements(self, mock_dynamodb_table):
        """Test validating job requirements before execution."""
        job_id = 'JOB-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'JobId': job_id,
                'ValidationCriteria': {
                    'healthCheck': True,
                    'smokeTest': True
                }
            }]
        }
        
        # Execute
        valid = self.manager.validate_job_requirements(job_id)
        
        # Verify
        assert valid is True
    
    def test_validate_deployment_strategy(self):
        """Test validating deployment strategies."""
        valid_strategies = ['blue-green', 'rolling', 'canary', 'recreate']
        
        for strategy in valid_strategies:
            assert self.manager.validate_strategy(strategy) is True
        
        assert self.manager.validate_strategy('invalid-strategy') is False
    
    # ==================== Artifact Management Tests ====================
    
    def test_store_job_artifacts(self, mock_s3_client):
        """Test storing job artifacts in S3."""
        job_id = 'JOB-001'
        artifacts = {
            'logs': b'deployment logs',
            'metrics': b'performance metrics',
            'config': b'configuration snapshot'
        }
        
        # Setup mock
        mock_s3_client.put_object.return_value = {'ETag': '"test-etag"'}
        
        # Execute
        result = self.manager.store_job_artifacts(job_id, artifacts)
        
        # Verify
        assert result is True
        assert mock_s3_client.put_object.call_count == len(artifacts)
    
    def test_retrieve_job_artifacts(self, mock_s3_client):
        """Test retrieving job artifacts from S3."""
        job_id = 'JOB-001'
        
        # Setup mock
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': f'jobs/{job_id}/logs'},
                {'Key': f'jobs/{job_id}/metrics'}
            ]
        }
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'artifact content')
        }
        
        # Execute
        artifacts = self.manager.get_job_artifacts(job_id)
        
        # Verify
        assert artifacts is not None
        assert len(artifacts) > 0
    
    # ==================== Job Metrics Tests ====================
    
    def test_record_job_metrics(self, mock_dynamodb_table):
        """Test recording job execution metrics."""
        job_id = 'JOB-001'
        metrics = {
            'duration': 300,
            'resourcesUsed': {
                'cpu': '2 cores',
                'memory': '4GB'
            },
            'recordsProcessed': 1000
        }
        
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.record_job_metrics(job_id, metrics)
        
        # Verify
        assert result is True
        mock_dynamodb_table.put_item.assert_called()
    
    def test_get_job_metrics(self, mock_dynamodb_table):
        """Test retrieving job metrics."""
        job_id = 'JOB-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{
                'JobId': job_id,
                'Metrics': {
                    'duration': 300,
                    'successRate': 100
                }
            }]
        }
        
        # Execute
        metrics = self.manager.get_job_metrics(job_id)
        
        # Verify
        assert metrics is not None
        assert metrics['duration'] == 300
    
    # ==================== Scheduling Tests ====================
    
    def test_schedule_job(self, mock_dynamodb_table):
        """Test scheduling a job for future execution."""
        capability_id = 'CAP-001'
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)
        job_data = {
            'jobType': 'deployment',
            'componentId': 'COMP-001',
            'scheduledAt': scheduled_time.isoformat()
        }
        
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        job_id = self.manager.schedule_job(capability_id, job_data, scheduled_time)
        
        # Verify
        assert job_id is not None
        mock_dynamodb_table.put_item.assert_called()
    
    def test_list_scheduled_jobs(self, mock_dynamodb_table):
        """Test listing scheduled jobs."""
        # Setup mock
        mock_dynamodb_table.scan.return_value = {
            'Items': [
                {
                    'JobId': 'JOB-001',
                    'Status': 'scheduled',
                    'ScheduledAt': datetime.now(timezone.utc).isoformat()
                },
                {
                    'JobId': 'JOB-002',
                    'Status': 'scheduled',
                    'ScheduledAt': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
                }
            ]
        }
        
        # Execute
        scheduled_jobs = self.manager.list_scheduled_jobs()
        
        # Verify
        assert len(scheduled_jobs) == 2
        assert all(job['Status'] == 'scheduled' for job in scheduled_jobs)
    
    # ==================== Error Handling Tests ====================
    
    def test_start_non_existent_job(self, mock_dynamodb_table):
        """Test starting a non-existent job."""
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        result = self.manager.start_job('NON-EXISTENT')
        
        assert result is False
    
    def test_cancel_completed_job(self, mock_dynamodb_table):
        """Test cancelling an already completed job."""
        # Setup mock - job is already completed
        mock_dynamodb_table.query.return_value = {
            'Items': [{'JobId': 'JOB-001', 'Status': 'completed'}]
        }
        
        result = self.manager.cancel_job('JOB-001')
        
        assert result is False
    
    def test_rollback_without_rollback_enabled(self, mock_dynamodb_table):
        """Test rollback when not enabled."""
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [{'JobId': 'JOB-001', 'RollbackEnabled': False}]
        }
        
        result = self.manager.rollback_job('JOB-001')
        
        assert result is None or result is False
