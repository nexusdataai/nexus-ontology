#!/usr/bin/env python3
"""
AWS Mock Manager for BDD Testing
Manages moto mocks for AWS services during testing
"""

import os
from typing import Dict, Any, Optional
import boto3
from moto import mock_aws
import json


class AWSMockManager:
    """Manages AWS service mocks for testing"""
    
    def __init__(self, aws_region: str = 'us-east-1'):
        """Initialize AWS mock manager
        
        Args:
            aws_region: AWS region for mocked services
        """
        self.aws_region = aws_region
        self.mock = None  # Single mock_aws instance for all services
        self.resources = {
            'tables': [],
            'buckets': [],
            'log_groups': []
        }
        
    def start_all_mocks(self) -> None:
        """Start all AWS service mocks"""
        if self.mock:
            return
            
        # Start unified AWS mock
        self.mock = mock_aws()
        self.mock.start()
        
        # Now create the resources
        self.setup_dynamodb_tables()
        self.setup_s3_buckets()
        self.setup_cloudwatch_logs()
        
    def stop_all_mocks(self) -> None:
        """Stop all AWS service mocks"""
        if self.mock:
            self.mock.stop()
            self.mock = None
                
    def setup_dynamodb_tables(self) -> None:
        """Create test DynamoDB tables"""
        dynamodb = boto3.resource('dynamodb', region_name=self.aws_region)
        
        # Check if table already exists
        try:
            table = dynamodb.Table('aurorastack-transformation-jobs')
            table.table_status  # This will throw an exception if table doesn't exist
            self.resources['tables'].append('aurorastack-transformation-jobs')
            return  # Table already exists
        except:
            pass  # Table doesn't exist, create it
        
        # Create transformation table
        table = dynamodb.create_table(
            TableName='aurorastack-transformation-jobs',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'gsi1pk', 'AttributeType': 'S'},
                {'AttributeName': 'gsi1sk', 'AttributeType': 'S'},
                {'AttributeName': 'gsi2pk', 'AttributeType': 'S'},
                {'AttributeName': 'gsi2sk', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'gsi1',
                    'KeySchema': [
                        {'AttributeName': 'gsi1pk', 'KeyType': 'HASH'},
                        {'AttributeName': 'gsi1sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'gsi2',
                    'KeySchema': [
                        {'AttributeName': 'gsi2pk', 'KeyType': 'HASH'},
                        {'AttributeName': 'gsi2sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to be active
        table.wait_until_exists()
        self.resources['tables'].append('aurorastack-transformation-jobs')
        
    def setup_s3_buckets(self) -> None:
        """Create test S3 buckets"""
        # Create test buckets
        s3 = boto3.client('s3', region_name=self.aws_region)
        
        buckets = [
            'aurorastack-transformation-data',
            'aurorastack-job-logs',
            'aurorastack-exports'
        ]
        
        for bucket_name in buckets:
            s3.create_bucket(Bucket=bucket_name)
            self.resources['buckets'].append(bucket_name)
            
    def setup_cloudwatch_logs(self) -> None:
        """Create test CloudWatch log groups"""
        # Create log groups
        logs = boto3.client('logs', region_name=self.aws_region)
        
        log_groups = [
            '/aws/lambda/transformation-executor',
            '/ecs/transformation-jobs',
            '/aurora/journey-manager'
        ]
        
        for log_group in log_groups:
            logs.create_log_group(logGroupName=log_group)
            self.resources['log_groups'].append(log_group)
            
    def create_test_s3_objects(self, bucket: str, objects: Dict[str, Any]) -> None:
        """Create test objects in S3
        
        Args:
            bucket: Bucket name
            objects: Dictionary of key->content to create
        """
        s3 = boto3.client('s3', region_name=self.aws_region)
        
        for key, content in objects.items():
            if isinstance(content, dict):
                content = json.dumps(content)
            elif not isinstance(content, (str, bytes)):
                content = str(content)
                
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=content.encode('utf-8') if isinstance(content, str) else content
            )
            
    def get_dynamodb_table(self, table_name: str):
        """Get DynamoDB table resource
        
        Args:
            table_name: Name of the table
            
        Returns:
            DynamoDB table resource
        """
        dynamodb = boto3.resource('dynamodb', region_name=self.aws_region)
        return dynamodb.Table(table_name)
        
    def get_s3_client(self):
        """Get S3 client
        
        Returns:
            S3 client
        """
        return boto3.client('s3', region_name=self.aws_region)
        
    def cleanup_resources(self) -> None:
        """Clean up all created resources"""
        if not self.mock:
            return
            
        # Clean S3 buckets
        s3 = boto3.client('s3', region_name=self.aws_region)
        for bucket in self.resources['buckets']:
            try:
                # Delete all objects first
                response = s3.list_objects_v2(Bucket=bucket)
                if 'Contents' in response:
                    for obj in response['Contents']:
                        s3.delete_object(Bucket=bucket, Key=obj['Key'])
                # Then delete bucket
                s3.delete_bucket(Bucket=bucket)
            except:
                pass
                
        # Clean CloudWatch log groups
        logs = boto3.client('logs', region_name=self.aws_region)
        for log_group in self.resources['log_groups']:
            try:
                logs.delete_log_group(logGroupName=log_group)
            except:
                pass
                    
        # Clear resource tracking
        self.resources = {
            'tables': [],
            'buckets': [],
            'log_groups': []
        }
        
    def setup_environment_variables(self) -> None:
        """Set up environment variables for mocked AWS"""
        os.environ['AWS_DEFAULT_REGION'] = self.aws_region
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
        os.environ['MOTO_DYNAMODB_USE_DOCKER'] = 'false'
        
    def clear_environment_variables(self) -> None:
        """Clear AWS environment variables"""
        env_vars = [
            'AWS_DEFAULT_REGION',
            'AWS_ACCESS_KEY_ID', 
            'AWS_SECRET_ACCESS_KEY',
            'AWS_SECURITY_TOKEN',
            'AWS_SESSION_TOKEN',
            'MOTO_DYNAMODB_USE_DOCKER'
        ]
        
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]


class MockedAWSContext:
    """Context manager for AWS mocking"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.manager = AWSMockManager(region)
        
    def __enter__(self):
        """Enter context - start mocks"""
        self.manager.setup_environment_variables()
        self.manager.start_all_mocks()
        return self.manager
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - stop mocks and cleanup"""
        self.manager.cleanup_resources()
        self.manager.stop_all_mocks()
        self.manager.clear_environment_variables()
