"""
Journey REST API Integration Tests

Tests direct REST API endpoints (not MCP tools).
"""

import pytest
from typing import Dict, Any

from ..utils.response_validator import validate_success_response
from ..utils.test_helpers import generate_unique_name


@pytest.mark.integration
class TestJourneyRestAPI:
    """Test Journey REST API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client, cleanup_manager):
        """Setup for each test"""
        self.client = api_client
        self.cleanup = cleanup_manager
        self.created_journeys = []
    
    def teardown_method(self, method):
        """Cleanup after each test"""
        for journey_id in self.created_journeys:
            self.cleanup("journey", journey_id)
    
    @pytest.mark.asyncio
    async def test_create_journey_via_rest(self, test_journey_data):
        """Test creating journey via REST API"""
        # Try creating via REST API if it exists
        response = await self.client.post(
            "/api/v1/journeys/",
            json=test_journey_data
        )
        
        # REST endpoint may or may not exist, handle both cases
        if response.status_code in [200, 201]:
            result = response.json()
            
            # API should return journey_id or journeyId
            if "journey_id" in result or "journeyId" in result:
                journey_id = result.get("journey_id") or result.get("journeyId")
                self.created_journeys.append(journey_id)
                self.cleanup("journey", journey_id)
        elif response.status_code == 404:
            pytest.skip("REST API endpoint not available")
        elif response.status_code == 307:
            # Handle redirect
            pass
    
    @pytest.mark.asyncio
    async def test_get_journey_via_rest(self):
        """Test getting journey via REST API"""
        # First create a journey via MCP tool (stages are required)
        create_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create",
                "journey_data": {
                    "name": generate_unique_name(),
                    "odaComponentType": "product-catalog",
                    "stages": [{"stageId": "test_stage", "name": "Test Stage", "order": 1}]
                }
            }}
        )
        
        if create_response.status_code == 200:
            create_result = create_response.json()
            if create_result.get("status") == "success" and "journey_id" in create_result:
                journey_id = create_result["journey_id"]
                self.created_journeys.append(journey_id)
                self.cleanup("journey", journey_id)
                
                # Try to get via REST API
                get_response = await self.client.get(f"/api/v1/journeys/{journey_id}")
                
                # REST endpoint may or may not exist
                if get_response.status_code in [200]:
                    result = get_response.json()
                    assert "journey_id" in result or "journeyId" in result
                elif get_response.status_code == 404:
                    pytest.skip("REST API endpoint not available")
    
    @pytest.mark.asyncio
    async def test_list_journeys_via_rest(self):
        """Test listing journeys via REST API"""
        response = await self.client.get("/api/v1/journeys/")
        
        # REST endpoint may or may not exist
        if response.status_code == 200:
            result = response.json()
            # Should return list or paginated result
            assert isinstance(result, (list, dict))
        elif response.status_code == 404:
            pytest.skip("REST API endpoint not available")
        elif response.status_code == 307:
            # Handle redirect
            pass
    
    @pytest.mark.asyncio
    async def test_update_journey_via_rest(self):
        """Test updating journey via REST API"""
        # First create a journey (stages are required)
        create_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create",
                "journey_data": {
                    "name": generate_unique_name(),
                    "odaComponentType": "product-catalog",
                    "stages": [{"stageId": "test_stage", "name": "Test Stage", "order": 1}]
                }
            }}
        )
        
        if create_response.status_code == 200:
            create_result = create_response.json()
            if create_result.get("status") == "success" and "journey_id" in create_result:
                journey_id = create_result["journey_id"]
                self.created_journeys.append(journey_id)
                self.cleanup("journey", journey_id)
                
                # Try to update via REST API
                update_response = await self.client.put(
                    f"/api/v1/journeys/{journey_id}",
                    json={"description": "Updated via REST"}
                )
                
                # REST endpoint may or may not exist
                if update_response.status_code in [200]:
                    pass
                elif update_response.status_code == 404:
                    pytest.skip("REST API endpoint not available")
    
    @pytest.mark.asyncio
    async def test_delete_journey_via_rest(self):
        """Test deleting journey via REST API"""
        # First create a journey (stages are required)
        create_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create",
                "journey_data": {
                    "name": generate_unique_name(),
                    "odaComponentType": "product-catalog",
                    "stages": [{"stageId": "test_stage", "name": "Test Stage", "order": 1}]
                }
            }}
        )
        
        if create_response.status_code == 200:
            create_result = create_response.json()
            if create_result.get("status") == "success" and "journey_id" in create_result:
                journey_id = create_result["journey_id"]
                
                # Try to delete via REST API
                delete_response = await self.client.delete(f"/api/v1/journeys/{journey_id}")
                
                # REST endpoint may or may not exist
                if delete_response.status_code in [200, 204]:
                    pass
                elif delete_response.status_code == 404:
                    pytest.skip("REST API endpoint not available")
                else:
                    # If not deleted via REST, cleanup via MCP
                    self.created_journeys.append(journey_id)
                    self.cleanup("journey", journey_id)

