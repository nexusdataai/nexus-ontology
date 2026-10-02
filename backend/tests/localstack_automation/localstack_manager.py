"""
LocalStack Manager

Manages LocalStack Docker container lifecycle and health checking.
"""

import subprocess
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any
import requests

from .logging_config import get_logger, TestAutomationLogger
from .models import ServiceHealth


class LocalStackManager:
    """Manages LocalStack Docker container."""
    
    # Default docker-compose file location
    DEFAULT_COMPOSE_FILE = "docker-compose-localstack.yml"
    
    # Container name from docker-compose
    CONTAINER_NAME = "nexus-localstack"
    
    def __init__(
        self,
        endpoint: str = "http://localhost:4566",
        compose_file: Optional[Path] = None,
        project_root: Optional[Path] = None
    ):
        """
        Initialize LocalStack manager.
        
        Args:
            endpoint: LocalStack endpoint URL
            compose_file: Path to docker-compose file
            project_root: Project root directory (for finding compose file)
        """
        self.endpoint = endpoint.rstrip('/')
        self.logger = get_logger()
        
        # Determine project root
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Assume we're in tests/localstack_automation
            self.project_root = Path(__file__).parent.parent.parent
        
        # Determine compose file path
        if compose_file:
            self.compose_file = Path(compose_file)
        else:
            self.compose_file = self.project_root / self.DEFAULT_COMPOSE_FILE
    
    def is_running(self) -> bool:
        """
        Check if LocalStack container is running.
        
        Returns:
            True if container is running, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.CONTAINER_NAME}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return "Up" in result.stdout
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            self.logger.debug(f"Error checking container status: {e}")
            return False
    
    def is_healthy(self) -> bool:
        """
        Check if LocalStack health endpoint responds.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.endpoint}/_localstack/health",
                timeout=5
            )
            if response.status_code == 200:
                health_data = response.json()
                # Check if key services are running
                services = health_data.get("services", {})
                return services.get("dynamodb") in ("running", "available")
            return False
        except (requests.RequestException, ValueError) as e:
            self.logger.debug(f"Health check failed: {e}")
            return False
    
    def get_health(self) -> ServiceHealth:
        """
        Get detailed health status.
        
        Returns:
            ServiceHealth object with status details
        """
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.endpoint}/_localstack/health",
                timeout=5
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                health_data = response.json()
                services = health_data.get("services", {})
                healthy = services.get("dynamodb") in ("running", "available")
                
                return ServiceHealth(
                    name="LocalStack",
                    healthy=healthy,
                    endpoint=self.endpoint,
                    response_time_ms=response_time,
                    details=services
                )
            else:
                return ServiceHealth(
                    name="LocalStack",
                    healthy=False,
                    endpoint=self.endpoint,
                    response_time_ms=response_time,
                    error=f"HTTP {response.status_code}"
                )
        except requests.RequestException as e:
            return ServiceHealth(
                name="LocalStack",
                healthy=False,
                endpoint=self.endpoint,
                error=str(e)
            )
    
    def start(self, timeout: int = 60) -> bool:
        """
        Start LocalStack using docker-compose.
        
        Args:
            timeout: Maximum time to wait for startup in seconds
            
        Returns:
            True if started successfully, False otherwise
        """
        TestAutomationLogger.log_step("Starting LocalStack...")
        
        # Check if already running
        if self.is_running() and self.is_healthy():
            TestAutomationLogger.log_success("LocalStack is already running and healthy")
            return True
        
        # Verify docker-compose file exists
        if not self.compose_file.exists():
            TestAutomationLogger.log_error(f"Docker compose file not found: {self.compose_file}")
            return False
        
        # Start with docker-compose
        try:
            self.logger.info(f"Running docker-compose up from {self.compose_file}")
            result = subprocess.run(
                ["docker", "compose", "-f", str(self.compose_file), "up", "-d"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=60
            )
            
            if result.returncode != 0:
                TestAutomationLogger.log_error(f"docker-compose failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            TestAutomationLogger.log_error("docker-compose timed out")
            return False
        except FileNotFoundError:
            TestAutomationLogger.log_error("docker compose not found. Please install Docker.")
            return False
        
        # Wait for health
        return self.wait_for_health(timeout)
    
    def wait_for_health(self, timeout: int = 60) -> bool:
        """
        Wait for LocalStack health endpoint to respond.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if healthy within timeout, False otherwise
        """
        TestAutomationLogger.log_step(f"Waiting for LocalStack to be healthy (timeout: {timeout}s)...")
        
        start_time = time.time()
        check_interval = 2  # seconds
        
        while (time.time() - start_time) < timeout:
            if self.is_healthy():
                elapsed = time.time() - start_time
                TestAutomationLogger.log_success(f"LocalStack is healthy (took {elapsed:.1f}s)")
                return True
            
            time.sleep(check_interval)
            self.logger.debug("Waiting for LocalStack...")
        
        TestAutomationLogger.log_error(f"LocalStack failed to become healthy within {timeout}s")
        return False
    
    def stop(self, remove_volumes: bool = False) -> bool:
        """
        Stop LocalStack container.
        
        Args:
            remove_volumes: If True, also remove data volumes
            
        Returns:
            True if stopped successfully, False otherwise
        """
        TestAutomationLogger.log_step("Stopping LocalStack...")
        
        if not self.compose_file.exists():
            TestAutomationLogger.log_warning("Docker compose file not found, trying direct docker stop")
            try:
                subprocess.run(
                    ["docker", "stop", self.CONTAINER_NAME],
                    capture_output=True,
                    timeout=30
                )
                return True
            except Exception as e:
                TestAutomationLogger.log_error(f"Failed to stop container: {e}")
                return False
        
        try:
            cmd = ["docker", "compose", "-f", str(self.compose_file), "down"]
            if remove_volumes:
                cmd.append("-v")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=60
            )
            
            if result.returncode == 0:
                TestAutomationLogger.log_success("LocalStack stopped")
                return True
            else:
                TestAutomationLogger.log_error(f"Failed to stop LocalStack: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            TestAutomationLogger.log_error("docker-compose down timed out")
            return False
        except Exception as e:
            TestAutomationLogger.log_error(f"Error stopping LocalStack: {e}")
            return False
    
    def get_logs(self, lines: int = 100) -> str:
        """
        Get LocalStack container logs.
        
        Args:
            lines: Number of log lines to retrieve
            
        Returns:
            Log output as string
        """
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), self.CONTAINER_NAME],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"Error getting logs: {e}"
    
    def initialize_resources(self, region: str = "us-east-1") -> bool:
        """
        Create DynamoDB tables and S3 buckets for testing.
        
        This method is idempotent - calling it multiple times will not fail
        if resources already exist.
        
        Args:
            region: AWS region for resources
            
        Returns:
            True if all resources created/exist, False on error
        """
        TestAutomationLogger.log_step("Initializing LocalStack resources...")
        
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            TestAutomationLogger.log_error("boto3 not installed. Run: pip install boto3")
            return False
        
        # Configure boto3 for LocalStack
        session = boto3.Session(
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name=region
        )
        
        success = True
        
        # Create DynamoDB tables
        success = self._create_dynamodb_tables(session, region) and success
        
        # Create S3 buckets
        success = self._create_s3_buckets(session, region) and success
        
        if success:
            TestAutomationLogger.log_success("LocalStack resources initialized")
        else:
            TestAutomationLogger.log_warning("Some resources failed to initialize")
        
        return success
    
    def _create_dynamodb_tables(self, session, region: str) -> bool:
        """Create required DynamoDB tables."""
        from botocore.exceptions import ClientError
        
        dynamodb = session.client(
            'dynamodb',
            endpoint_url=self.endpoint,
            region_name=region
        )
        
        # Tables follow call-processing-{env}-{name} pattern
        # For LocalStack, use 'local' environment
        tables_config = [
            {
                "name": "call-processing-local-transformation-system",
                "key_schema": [
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"}
                ],
                "attribute_definitions": [
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                    {"AttributeName": "GSI1PK", "AttributeType": "S"},
                    {"AttributeName": "GSI1SK", "AttributeType": "S"}
                ],
                "gsi": [
                    {
                        "IndexName": "GSI1",
                        "KeySchema": [
                            {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                            {"AttributeName": "GSI1SK", "KeyType": "RANGE"}
                        ],
                        "Projection": {"ProjectionType": "ALL"}
                    }
                ]
            },
            {
                "name": "call-processing-local-wxcc-task-tracking",
                "key_schema": [
                    {"AttributeName": "task_id", "KeyType": "HASH"}
                ],
                "attribute_definitions": [
                    {"AttributeName": "task_id", "AttributeType": "S"}
                ]
            },
            {
                "name": "call-processing-local-license",
                "key_schema": [
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"}
                ],
                "attribute_definitions": [
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                    {"AttributeName": "status", "AttributeType": "S"},
                    {"AttributeName": "holder_id", "AttributeType": "S"},
                    {"AttributeName": "license_id", "AttributeType": "S"}
                ],
                "gsi": [
                    {
                        "IndexName": "status-index",
                        "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"}
                    },
                    {
                        "IndexName": "holder-index",
                        "KeySchema": [{"AttributeName": "holder_id", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"}
                    },
                    {
                        "IndexName": "license-index",
                        "KeySchema": [
                            {"AttributeName": "license_id", "KeyType": "HASH"},
                            {"AttributeName": "SK", "KeyType": "RANGE"}
                        ],
                        "Projection": {"ProjectionType": "ALL"}
                    }
                ]
            }
        ]
        
        success = True
        for table_config in tables_config:
            table_name = table_config["name"]
            self.logger.info(f"Creating DynamoDB table: {table_name}")
            
            try:
                # Check if table exists
                dynamodb.describe_table(TableName=table_name)
                self.logger.info(f"  Table {table_name} already exists")
                continue
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    TestAutomationLogger.log_error(f"Error checking table {table_name}: {e}")
                    success = False
                    continue
            
            # Create table
            try:
                create_params = {
                    "TableName": table_name,
                    "KeySchema": table_config["key_schema"],
                    "AttributeDefinitions": table_config["attribute_definitions"],
                    "BillingMode": "PAY_PER_REQUEST"
                }
                
                if "gsi" in table_config:
                    create_params["GlobalSecondaryIndexes"] = table_config["gsi"]
                
                dynamodb.create_table(**create_params)
                self.logger.info(f"  [OK] Table {table_name} created")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceInUseException':
                    self.logger.info(f"  Table {table_name} already exists")
                else:
                    TestAutomationLogger.log_error(f"Failed to create table {table_name}: {e}")
                    success = False
        
        return success
    
    def _create_s3_buckets(self, session, region: str) -> bool:
        """Create required S3 buckets."""
        from botocore.exceptions import ClientError
        
        s3 = session.client(
            's3',
            endpoint_url=self.endpoint,
            region_name=region
        )
        
        # Buckets follow call-processing-{env}-{name} pattern
        # For LocalStack, use 'local' environment
        buckets = [
            "call-processing-local-call-data",
            "call-processing-local-journey-logs",
            "call-processing-local-journey-reports",
            "call-processing-local-wxcc-simulator",
            "test-reports",  # Keep for backwards compatibility with tests
        ]
        
        success = True
        for bucket_name in buckets:
            self.logger.info(f"Creating S3 bucket: {bucket_name}")
            
            try:
                # Check if bucket exists
                s3.head_bucket(Bucket=bucket_name)
                self.logger.info(f"  Bucket {bucket_name} already exists")
                continue
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code not in ('404', 'NoSuchBucket'):
                    TestAutomationLogger.log_error(f"Error checking bucket {bucket_name}: {e}")
                    success = False
                    continue
            
            # Create bucket
            try:
                if region == "us-east-1":
                    s3.create_bucket(Bucket=bucket_name)
                else:
                    s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                self.logger.info(f"  [OK] Bucket {bucket_name} created")
            except ClientError as e:
                if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                    self.logger.info(f"  Bucket {bucket_name} already exists")
                else:
                    TestAutomationLogger.log_error(f"Failed to create bucket {bucket_name}: {e}")
                    success = False
        
        return success
