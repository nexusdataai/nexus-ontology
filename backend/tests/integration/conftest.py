"""
Pytest configuration for integration tests
"""

import pytest
import pytest_asyncio
import asyncio
import os
import sys
from pathlib import Path
from typing import Generator, Any
import boto3
from moto import mock_aws
from httpx import AsyncClient
from time import sleep
import json

# Docker is optional - only import if needed
try:
    import docker
except ImportError:
    docker = None

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test configuration
# Support both TEST_BASE_URL and SERVER_URL environment variables
TEST_BASE_URL = os.getenv("TEST_BASE_URL") or os.getenv("SERVER_URL", "http://localhost:8000")
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "30"))
USE_MOCK_AWS = os.getenv("USE_MOCK_AWS", "true").lower() == "true"
USE_DOCKER_COMPOSE = os.getenv("USE_DOCKER_COMPOSE", "false").lower() == "true"

#==============================================================================
# Pytest Configuration
#==============================================================================

def pytest_addoption(parser):
    """Add command line options"""
    parser.addoption(
        "--server-url",
        action="store",
        default=TEST_BASE_URL,
        help="Server URL for integration tests"
    )
    parser.addoption(
        "--use-real-aws",
        action="store_true",
        default=False,
        help="Use real AWS services instead of mocks"
    )
    parser.addoption(
        "--skip-cleanup",
        action="store_true",
        default=False,
        help="Skip cleanup of test data after tests"
    )

def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "requires_aws: mark test as requiring AWS services"
    )

#==============================================================================
# Session Fixtures
#==============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def docker_client():
    """Docker client for container management"""
    if USE_DOCKER_COMPOSE:
        if docker is None:
            pytest.skip("Docker module not installed")
        try:
            client = docker.from_env()
            return client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
    return None

@pytest.fixture(scope="session", autouse=True)
def docker_services(docker_client):
    """Start Docker services if needed"""
    if not USE_DOCKER_COMPOSE or not docker_client:
        yield
        return
    
    # Start docker-compose services
    compose_file = PROJECT_ROOT / "tests" / "integration" / "docker-compose.test.yml"
    if compose_file.exists():
        os.system(f"docker-compose -f {compose_file} up -d")
        
        # Wait for services to be ready
        max_retries = 30
        for _ in range(max_retries):
            try:
                import httpx
                response = httpx.get(f"{TEST_BASE_URL}/health")
                if response.status_code == 200:
                    break
            except:
                pass
            sleep(1)
    
    yield
    
    # Cleanup
    if compose_file.exists():
        os.system(f"docker-compose -f {compose_file} down")

#==============================================================================
# AWS Fixtures
#==============================================================================

@pytest.fixture(scope="function")
def aws_credentials():
    """Set AWS credentials for testing"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture(scope="function")
def dynamodb_client(request, aws_credentials):
    """DynamoDB client (mocked or real)"""
    if USE_MOCK_AWS and not request.config.getoption("--use-real-aws"):
        with mock_aws():
            client = boto3.client("dynamodb", region_name="us-east-1")
            
            # Create test table
            try:
                client.create_table(
                    TableName="TransformationSystem",
                    KeySchema=[
                        {"AttributeName": "PK", "KeyType": "HASH"},
                        {"AttributeName": "SK", "KeyType": "RANGE"}
                    ],
                    AttributeDefinitions=[
                        {"AttributeName": "PK", "AttributeType": "S"},
                        {"AttributeName": "SK", "AttributeType": "S"}
                    ],
                    BillingMode="PAY_PER_REQUEST"
                )
            except client.exceptions.ResourceInUseException:
                pass  # Table already exists
            
            yield client
    else:
        # Use real DynamoDB
        client = boto3.client("dynamodb", region_name="us-east-1")
        yield client

@pytest.fixture(scope="function")
def dynamodb_resource(request, aws_credentials):
    """DynamoDB resource (mocked or real)"""
    if USE_MOCK_AWS and not request.config.getoption("--use-real-aws"):
        with mock_aws():
            resource = boto3.resource("dynamodb", region_name="us-east-1")
            
            # Create test table
            try:
                table = resource.create_table(
                    TableName="TransformationSystem",
                    KeySchema=[
                        {"AttributeName": "PK", "KeyType": "HASH"},
                        {"AttributeName": "SK", "KeyType": "RANGE"}
                    ],
                    AttributeDefinitions=[
                        {"AttributeName": "PK", "AttributeType": "S"},
                        {"AttributeName": "SK", "AttributeType": "S"}
                    ],
                    BillingMode="PAY_PER_REQUEST"
                )
                table.wait_until_exists()
            except resource.meta.client.exceptions.ResourceInUseException:
                table = resource.Table("TransformationSystem")
            
            yield resource
    else:
        # Use real DynamoDB
        resource = boto3.resource("dynamodb", region_name="us-east-1")
        yield resource

#==============================================================================
# HTTP Client Fixtures
#==============================================================================

@pytest_asyncio.fixture(scope="function")
async def api_client(request):
    """Async HTTP client for API testing with correct headers"""
    server_url = request.config.getoption("--server-url") if hasattr(request.config, 'getoption') else TEST_BASE_URL
    
    # Create client with correct API key header for MCP gateway
    async with AsyncClient(
        base_url=server_url,
        timeout=TEST_TIMEOUT,
        headers={"x-api-key": "super-secret"}
    ) as client:
        yield client

@pytest.fixture(scope="function")
async def authenticated_client(api_client):
    """HTTP client with authentication headers (alias for api_client)"""
    # API client already has x-api-key header
    yield api_client

#==============================================================================
# Test Data Fixtures
#==============================================================================

@pytest.fixture(scope="function")
def test_journey_data():
    """Generate test journey data with snake_case fields. Stages are required for creation."""
    import time
    timestamp = int(time.time())
    return {
        "journey_data": {
            "name": f"Integration Test Journey {timestamp}",
            "description": "Automated integration test journey",
            "odaComponentType": "payment-management",
            "priority": "medium",
            "stages": [
                {"stageId": "test_stage", "name": "Test Stage", "order": 1}
            ]
        }
    }

@pytest.fixture(scope="function")
def test_stage_data():
    """Generate test stage data"""
    return {
        "name": "test-validation-stage",
        "type": "validation",
        "description": "Test validation stage",
        "status": "pending",
        "sequence": 1,
        "config": {
            "validation_rules": ["schema", "business_logic"]
        }
    }

@pytest.fixture(scope="function")
def test_rule_data():
    """Generate test rule data"""
    return {
        "type": "transformation",
        "name": "Test Transformation Rule",
        "description": "Test rule for integration testing",
        "condition": "test_condition",
        "action": "test_action",
        "priority": 1,
        "enabled": True
    }

#==============================================================================
# Cleanup Fixtures
#==============================================================================

@pytest.fixture(scope="function")
def cleanup_manager(request, api_client):
    """Manager for test cleanup"""
    cleanup_items = []
    
    def add_cleanup(cleanup_type: str, item_id: str):
        """Add item for cleanup"""
        cleanup_items.append((cleanup_type, item_id))
    
    yield add_cleanup
    
    # Perform cleanup after test
    if not request.config.getoption("--skip-cleanup"):
        for cleanup_type, item_id in reversed(cleanup_items):
            if cleanup_type == "journey":
                asyncio.run(_cleanup_journey(api_client, item_id))
            elif cleanup_type == "job":
                asyncio.run(_cleanup_job(api_client, item_id))

async def _cleanup_journey(client: AsyncClient, journey_id: str):
    """Clean up a journey using correct request format"""
    try:
        response = await client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "delete",
                "journey_id": journey_id,
                "confirm": True
            }}
        )
        if response.status_code == 200:
            result = response.json()
            # Response is direct tool response (no "result" wrapper)
            if result.get("status") == "success":
                print(f"Cleaned up journey: {journey_id}")
    except Exception as e:
        print(f"Failed to cleanup journey {journey_id}: {e}")

async def _cleanup_job(client: AsyncClient, job_id: str):
    """Clean up a job"""
    try:
        # Implementation depends on job cleanup API
        pass
    except Exception as e:
        print(f"Failed to cleanup job {job_id}: {e}")

#==============================================================================
# Assertion Helpers
#==============================================================================

@pytest.fixture(scope="session")
def assert_journey_response():
    """Helper for asserting journey responses (updated for direct response format)"""
    def _assert(response_json: dict, check_success: bool = True):
        # Response is direct tool response (NO "result" wrapper)
        if check_success:
            assert response_json.get("status") == "success", \
                f"Expected success, got: {response_json.get('status')}"
        
        return response_json
    
    return _assert

@pytest.fixture(scope="session")
def assert_in_dynamodb():
    """Helper for asserting data exists in DynamoDB"""
    def _assert(dynamodb_resource, journey_id: str):
        table = dynamodb_resource.Table("TransformationSystem")
        response = table.get_item(
            Key={
                "PK": f"JOURNEY#{journey_id}",
                "SK": "METADATA"
            }
        )
        assert "Item" in response, f"Journey {journey_id} not found in DynamoDB"
        return response["Item"]
    
    return _assert

#==============================================================================
# Performance Testing Fixtures
#==============================================================================

@pytest.fixture
def performance_tracker():
    """Track performance metrics"""
    import time
    
    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.metrics = {}
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            return self.end_time - self.start_time
        
        def record(self, name: str, value: float):
            self.metrics[name] = value
        
        def assert_performance(self, max_duration: float):
            duration = self.end_time - self.start_time
            assert duration < max_duration, f"Performance test failed: {duration:.2f}s > {max_duration}s"
    
    return PerformanceTracker()

#==============================================================================
# Utility Functions
#==============================================================================

def wait_for_condition(condition_func, timeout: int = 30, interval: float = 1.0):
    """Wait for a condition to be true"""
    import time
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    
    return False

def generate_test_id(prefix: str = "TEST") -> str:
    """Generate unique test ID"""
    import time
    import random
    return f"{prefix}_{int(time.time())}_{random.randint(1000, 9999)}"
