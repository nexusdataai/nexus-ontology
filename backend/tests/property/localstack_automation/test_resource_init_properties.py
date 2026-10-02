"""
Property Tests for Resource Initialization Idempotency

Feature: localstack-test-automation
Property 2: Resource Initialization Idempotency

For any LocalStack environment, calling the resource initialization function
multiple times SHALL result in the same final state (DynamoDB tables and S3
buckets exist), and subsequent calls SHALL not fail due to resources already
existing.

Validates: Requirements 1.4, 1.6
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch
from botocore.exceptions import ClientError

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.localstack_automation.localstack_manager import LocalStackManager


class TestResourceInitializationIdempotency:
    """Property tests for resource initialization idempotency."""
    
    @given(call_count=st.integers(min_value=1, max_value=5))
    @settings(max_examples=50, deadline=None)
    def test_multiple_init_calls_succeed(self, call_count: int):
        """
        Feature: localstack-test-automation, Property 2: Resource Initialization Idempotency
        
        Multiple calls to initialize_resources should all succeed without errors.
        """
        with patch('tests.localstack_automation.localstack_manager.boto3') as mock_boto3:
            # Setup mock session and clients
            mock_session = MagicMock()
            mock_boto3.Session.return_value = mock_session
            
            mock_dynamodb = MagicMock()
            mock_s3 = MagicMock()
            
            def mock_client(service, **kwargs):
                if service == 'dynamodb':
                    return mock_dynamodb
                elif service == 's3':
                    return mock_s3
                return MagicMock()
            
            mock_session.client.side_effect = mock_client
            
            # Simulate tables/buckets already existing after first call
            mock_dynamodb.describe_table.return_value = {"Table": {"TableName": "test"}}
            mock_s3.head_bucket.return_value = {}
            
            manager = LocalStackManager()
            
            # Call initialize_resources multiple times
            results = []
            for _ in range(call_count):
                result = manager.initialize_resources()
                results.append(result)
            
            # All calls should succeed
            assert all(results), f"Expected all {call_count} calls to succeed"
    
    @given(
        tables_exist=st.lists(st.booleans(), min_size=2, max_size=2),
        buckets_exist=st.lists(st.booleans(), min_size=6, max_size=6)
    )
    @settings(max_examples=100, deadline=None)
    def test_init_handles_mixed_existing_resources(
        self, 
        tables_exist: list, 
        buckets_exist: list
    ):
        """
        Feature: localstack-test-automation, Property 2: Resource Initialization Idempotency
        
        Initialization should handle any combination of existing/non-existing resources.
        """
        with patch('tests.localstack_automation.localstack_manager.boto3') as mock_boto3:
            mock_session = MagicMock()
            mock_boto3.Session.return_value = mock_session
            
            mock_dynamodb = MagicMock()
            mock_s3 = MagicMock()
            
            def mock_client(service, **kwargs):
                if service == 'dynamodb':
                    return mock_dynamodb
                elif service == 's3':
                    return mock_s3
                return MagicMock()
            
            mock_session.client.side_effect = mock_client
            
            # Track which tables have been checked
            table_check_count = [0]
            
            def describe_table_side_effect(**kwargs):
                idx = table_check_count[0] % len(tables_exist)
                table_check_count[0] += 1
                if tables_exist[idx]:
                    return {"Table": {"TableName": kwargs.get("TableName", "test")}}
                else:
                    raise ClientError(
                        {"Error": {"Code": "ResourceNotFoundException"}},
                        "DescribeTable"
                    )
            
            mock_dynamodb.describe_table.side_effect = describe_table_side_effect
            mock_dynamodb.create_table.return_value = {}
            
            # Track which buckets have been checked
            bucket_check_count = [0]
            
            def head_bucket_side_effect(**kwargs):
                idx = bucket_check_count[0] % len(buckets_exist)
                bucket_check_count[0] += 1
                if buckets_exist[idx]:
                    return {}
                else:
                    raise ClientError(
                        {"Error": {"Code": "404"}},
                        "HeadBucket"
                    )
            
            mock_s3.head_bucket.side_effect = head_bucket_side_effect
            mock_s3.create_bucket.return_value = {}
            
            manager = LocalStackManager()
            result = manager.initialize_resources()
            
            # Should succeed regardless of which resources existed
            assert result is True
    
    @given(region=st.sampled_from(["us-east-1", "us-west-2", "eu-west-1", "us-east-1"]))
    @settings(max_examples=20, deadline=None)
    def test_init_works_across_regions(self, region: str):
        """
        Feature: localstack-test-automation, Property 2: Resource Initialization Idempotency
        
        Initialization should work correctly for any supported AWS region.
        """
        with patch('tests.localstack_automation.localstack_manager.boto3') as mock_boto3:
            mock_session = MagicMock()
            mock_boto3.Session.return_value = mock_session
            
            mock_dynamodb = MagicMock()
            mock_s3 = MagicMock()
            
            def mock_client(service, **kwargs):
                if service == 'dynamodb':
                    return mock_dynamodb
                elif service == 's3':
                    return mock_s3
                return MagicMock()
            
            mock_session.client.side_effect = mock_client
            
            # Resources don't exist, need to be created
            mock_dynamodb.describe_table.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException"}},
                "DescribeTable"
            )
            mock_dynamodb.create_table.return_value = {}
            
            mock_s3.head_bucket.side_effect = ClientError(
                {"Error": {"Code": "404"}},
                "HeadBucket"
            )
            mock_s3.create_bucket.return_value = {}
            
            manager = LocalStackManager()
            result = manager.initialize_resources(region=region)
            
            assert result is True
            
            # Verify session was created with correct region
            mock_boto3.Session.assert_called_with(
                aws_access_key_id="test",
                aws_secret_access_key="test",
                region_name=region
            )
    
    @given(st.data())
    @settings(max_examples=50, deadline=None)
    def test_final_state_consistent_after_multiple_inits(self, data):
        """
        Feature: localstack-test-automation, Property 2: Resource Initialization Idempotency
        
        After any number of initialization calls, the final state should be
        consistent (all expected resources exist).
        """
        call_count = data.draw(st.integers(min_value=1, max_value=3))
        
        with patch('tests.localstack_automation.localstack_manager.boto3') as mock_boto3:
            mock_session = MagicMock()
            mock_boto3.Session.return_value = mock_session
            
            mock_dynamodb = MagicMock()
            mock_s3 = MagicMock()
            
            # Track created resources
            created_tables = set()
            created_buckets = set()
            
            def mock_client(service, **kwargs):
                if service == 'dynamodb':
                    return mock_dynamodb
                elif service == 's3':
                    return mock_s3
                return MagicMock()
            
            mock_session.client.side_effect = mock_client
            
            def describe_table_side_effect(**kwargs):
                table_name = kwargs.get("TableName")
                if table_name in created_tables:
                    return {"Table": {"TableName": table_name}}
                raise ClientError(
                    {"Error": {"Code": "ResourceNotFoundException"}},
                    "DescribeTable"
                )
            
            def create_table_side_effect(**kwargs):
                table_name = kwargs.get("TableName")
                created_tables.add(table_name)
                return {}
            
            def head_bucket_side_effect(**kwargs):
                bucket_name = kwargs.get("Bucket")
                if bucket_name in created_buckets:
                    return {}
                raise ClientError(
                    {"Error": {"Code": "404"}},
                    "HeadBucket"
                )
            
            def create_bucket_side_effect(**kwargs):
                bucket_name = kwargs.get("Bucket")
                created_buckets.add(bucket_name)
                return {}
            
            mock_dynamodb.describe_table.side_effect = describe_table_side_effect
            mock_dynamodb.create_table.side_effect = create_table_side_effect
            mock_s3.head_bucket.side_effect = head_bucket_side_effect
            mock_s3.create_bucket.side_effect = create_bucket_side_effect
            
            manager = LocalStackManager()
            
            # Call initialize multiple times
            for _ in range(call_count):
                result = manager.initialize_resources()
                assert result is True
            
            # Verify expected resources were created
            expected_tables = {"TransformationSystem", "nexus-dev-wxcc-task-tracking"}
            expected_buckets = {
                "test-reports",
                "transformation-journey-logs",
                "transformation-journey-reports",
                "nexus-dev-wxcc-recordings",
                "nexus-dev-wxcc-transcripts",
                "nexus-dev-wxcc-simulator"
            }
            
            assert created_tables == expected_tables, f"Expected tables {expected_tables}, got {created_tables}"
            assert created_buckets == expected_buckets, f"Expected buckets {expected_buckets}, got {created_buckets}"


class TestResourceInitializationErrorHandling:
    """Property tests for error handling during resource initialization."""
    
    @given(
        failing_table_idx=st.integers(min_value=0, max_value=1),
        error_code=st.sampled_from(["AccessDeniedException", "ValidationException", "InternalServerError"])
    )
    @settings(max_examples=30, deadline=None)
    def test_handles_dynamodb_errors_gracefully(self, failing_table_idx: int, error_code: str):
        """
        Feature: localstack-test-automation, Property 2: Resource Initialization Idempotency
        
        DynamoDB errors should be handled gracefully without crashing.
        """
        with patch('tests.localstack_automation.localstack_manager.boto3') as mock_boto3:
            mock_session = MagicMock()
            mock_boto3.Session.return_value = mock_session
            
            mock_dynamodb = MagicMock()
            mock_s3 = MagicMock()
            
            def mock_client(service, **kwargs):
                if service == 'dynamodb':
                    return mock_dynamodb
                elif service == 's3':
                    return mock_s3
                return MagicMock()
            
            mock_session.client.side_effect = mock_client
            
            call_count = [0]
            
            def describe_table_side_effect(**kwargs):
                idx = call_count[0]
                call_count[0] += 1
                if idx == failing_table_idx:
                    raise ClientError(
                        {"Error": {"Code": error_code}},
                        "DescribeTable"
                    )
                raise ClientError(
                    {"Error": {"Code": "ResourceNotFoundException"}},
                    "DescribeTable"
                )
            
            mock_dynamodb.describe_table.side_effect = describe_table_side_effect
            mock_dynamodb.create_table.return_value = {}
            mock_s3.head_bucket.return_value = {}
            
            manager = LocalStackManager()
            
            # Should not raise exception, but may return False
            try:
                result = manager.initialize_resources()
                # Result can be True or False depending on error handling
                assert isinstance(result, bool)
            except Exception as e:
                pytest.fail(f"Should not raise exception: {e}")
    
    @given(
        failing_bucket_idx=st.integers(min_value=0, max_value=5),
        error_code=st.sampled_from(["AccessDenied", "InvalidBucketName", "InternalError"])
    )
    @settings(max_examples=30, deadline=None)
    def test_handles_s3_errors_gracefully(self, failing_bucket_idx: int, error_code: str):
        """
        Feature: localstack-test-automation, Property 2: Resource Initialization Idempotency
        
        S3 errors should be handled gracefully without crashing.
        """
        with patch('tests.localstack_automation.localstack_manager.boto3') as mock_boto3:
            mock_session = MagicMock()
            mock_boto3.Session.return_value = mock_session
            
            mock_dynamodb = MagicMock()
            mock_s3 = MagicMock()
            
            def mock_client(service, **kwargs):
                if service == 'dynamodb':
                    return mock_dynamodb
                elif service == 's3':
                    return mock_s3
                return MagicMock()
            
            mock_session.client.side_effect = mock_client
            
            mock_dynamodb.describe_table.return_value = {"Table": {}}
            
            call_count = [0]
            
            def head_bucket_side_effect(**kwargs):
                idx = call_count[0]
                call_count[0] += 1
                if idx == failing_bucket_idx:
                    raise ClientError(
                        {"Error": {"Code": error_code}},
                        "HeadBucket"
                    )
                return {}
            
            mock_s3.head_bucket.side_effect = head_bucket_side_effect
            mock_s3.create_bucket.return_value = {}
            
            manager = LocalStackManager()
            
            # Should not raise exception
            try:
                result = manager.initialize_resources()
                assert isinstance(result, bool)
            except Exception as e:
                pytest.fail(f"Should not raise exception: {e}")
