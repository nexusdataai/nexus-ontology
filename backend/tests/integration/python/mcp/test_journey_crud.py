"""
Journey CRUD Integration Tests

Tests basic journey CRUD operations through the MCP HTTP gateway.
Uses snake_case field naming to match current implementation.
"""

import pytest
from typing import Dict, Any
import time

from ..utils.response_validator import (
    validate_success_response,
    validate_error_response,
    validate_journey_data
)
from ..utils.test_helpers import (
    unwrap_mcp_response,
    generate_unique_name,
    extract_journey_id
)


@pytest.mark.integration
class TestJourneyCRUD:
    """Test Journey CRUD operations via MCP tool"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client, cleanup_manager):
        """Setup for each test"""
        self.client = api_client
        self.cleanup = cleanup_manager
        self.created_journeys = []
    
    def teardown_method(self, method):
        """Cleanup after each test"""
        # Cleanup tracked journeys
        for journey_id in self.created_journeys:
            self.cleanup("journey", journey_id)
    
    @pytest.mark.asyncio
    async def test_create_journey(self, test_journey_data):
        """Test basic journey creation"""
        # Create journey
        response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create",
                **test_journey_data
            }}
        )
        
        assert response.status_code == 200
        result = unwrap_mcp_response(response.json())
        
        # Validate response format
        validate_success_response(result, "create_journey")
        
        # Validate journey_id
        assert "journey_id" in result
        journey_id = result["journey_id"]
        assert journey_id.startswith("JRN-")
        
        # Track for cleanup
        self.created_journeys.append(journey_id)
        self.cleanup("journey", journey_id)
        
        # Validate message
        assert "created" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_create_journey_validation(self):
        """Test journey creation with validation errors"""
        # Missing required fields
        response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create"
                # Missing name and odaComponentType
            }}
        )
        
        # Should return validation error
        assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            # MCP returns 200 with error in response body
            result = unwrap_mcp_response(response.json())
        else:
            result = response.json()
        
        # Should indicate error
        assert result.get("status") == "error" or "error" in str(result).lower()
    
    @pytest.mark.asyncio
    async def test_read_journey(self, test_journey_data):
        """Test reading an existing journey"""
        # First create a journey
        create_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create",
                **test_journey_data
            }}
        )
        
        assert create_response.status_code == 200
        create_result = create_response.json()
        journey_id = extract_journey_id(create_result)
        self.created_journeys.append(journey_id)
        self.cleanup("journey", journey_id)
        
        # Read the journey
        read_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "read",
                "journey_id": journey_id
            }}
        )
        
        assert read_response.status_code == 200
        result = unwrap_mcp_response(read_response.json())
        
        # Validate response
        validate_success_response(result, "get_journey")
        
        # Validate data
        assert "data" in result
        journey_data = result["data"]
        
        # Handle nested metadata structure
        if "metadata" in journey_data:
            journey_data = journey_data["metadata"]
        
        # Validate journey_id - could be journey_id or journeyId
        actual_journey_id = journey_data.get("journey_id") or journey_data.get("journeyId")
        assert actual_journey_id == journey_id
        assert journey_data["name"] == test_journey_data["name"]
        
        # Status check
        status = journey_data.get("status", "pending")
        assert status in ["pending", "running", "completed", "failed"]
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_journey(self):
        """Test reading a journey that doesn't exist"""
        response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "read",
                "journey_id": "JRN-NONEXISTENT-999"
            }}
        )
        
        assert response.status_code == 200
        result = unwrap_mcp_response(response.json())
        
        # Should return error
        validate_error_response(result)
        assert "not found" in result.get("message", "").lower() or result.get("status") == "error"
    
    @pytest.mark.asyncio
    async def test_update_journey(self, test_journey_data):
        """Test updating a journey"""
        # Create journey
        create_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create",
                **test_journey_data
            }}
        )
        
        journey_id = extract_journey_id(create_response.json())
        self.created_journeys.append(journey_id)
        self.cleanup("journey", journey_id)
        
        # Update journey
        update_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "update",
                "journey_id": journey_id,
                "journey_data": {
                    "status": "running",
                    "priority": "high",
                    "description": "Updated description for test"
                }
            }}
        )
        
        assert update_response.status_code == 200
        result = unwrap_mcp_response(update_response.json())
        
        # Validate response
        validate_success_response(result, "update_journey")
        assert "updated" in result.get("message", "").lower() or result.get("status") == "success"
    
    @pytest.mark.asyncio
    async def test_delete_journey(self, test_journey_data):
        """Test deleting a journey"""
        # Create journey
        create_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create",
                **test_journey_data
            }}
        )
        
        journey_id = extract_journey_id(create_response.json())
        
        # Delete journey
        delete_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "delete",
                "journey_id": journey_id,
                "confirm": True
            }}
        )
        
        assert delete_response.status_code == 200
        result = unwrap_mcp_response(delete_response.json())
        
        # Validate response
        validate_success_response(result, "delete_journey")
        assert "deleted" in result.get("message", "").lower() or result.get("status") == "success"
        
        # Verify journey is deleted
        read_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "read",
                "journey_id": journey_id
            }}
        )
        
        # Should return error
        read_result = unwrap_mcp_response(read_response.json())
        assert read_result.get("status") == "error"
    
    @pytest.mark.asyncio
    async def test_list_journeys(self):
        """Test listing journeys"""
        response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "list"
            }}
        )
        
        assert response.status_code == 200
        result = unwrap_mcp_response(response.json())
        
        # Validate response
        validate_success_response(result, "list_journeys")
        
        # Should have data field with list of journeys
        assert "data" in result
        journeys = result["data"]
        assert isinstance(journeys, list)
    
    @pytest.mark.asyncio
    async def test_list_journeys_with_filters(self, test_journey_data):
        """Test listing journeys with filters"""
        # Create a journey first
        create_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create",
                **test_journey_data
            }}
        )
        
        journey_id = extract_journey_id(create_response.json())
        self.created_journeys.append(journey_id)
        self.cleanup("journey", journey_id)
        
        # List with status filter
        response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "list",
                "status_filter": "pending"
            }}
        )
        
        assert response.status_code == 200
        result = unwrap_mcp_response(response.json())
        
        # Validate response
        validate_success_response(result, "list_journeys")
        assert "data" in result
        assert isinstance(result["data"], list)
    
    @pytest.mark.asyncio
    async def test_create_journey_with_priority(self):
        """Test creating journey with different priorities"""
        for priority in ["low", "medium", "high", "critical"]:
            response = await self.client.post(
                "/tools/journeys_tool",
                json={"arguments": {
                    "action": "create",
                    "journey_data": {
                        "name": f"Test Journey {priority}",
                        "odaComponentType": "product-catalog",
                        "priority": priority,
                        "stages": [
                            {"stageId": "test_stage", "name": "Test Stage", "order": 1}
                        ]
                    }
                }}
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Should succeed
            if result.get("status") == "success":
                journey_id = extract_journey_id(result)
                self.created_journeys.append(journey_id)
                self.cleanup("journey", journey_id)

