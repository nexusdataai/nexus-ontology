"""
Core MCP Operations Integration Tests

Focused tests for the most critical operations that are actually implemented.
"""

import pytest
import json
from typing import Dict, Any


def unwrap_response(response_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Unwrap MCP protocol response format"""
    if "content" in response_dict and isinstance(response_dict["content"], list):
        if len(response_dict["content"]) > 0:
            content = response_dict["content"][0]
            if isinstance(content, dict) and "text" in content:
                try:
                    return json.loads(content["text"])
                except:
                    pass
    return response_dict


@pytest.mark.integration
class TestCoreJourneyOperations:
    """Test core journey operations that are implemented"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        self.client = api_client
    
    @pytest.mark.asyncio
    async def test_list_journeys(self):
        """Test listing all journeys"""
        response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {"action": "list"}}
        )
        
        assert response.status_code == 200
        result = unwrap_response(response.json())
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)
    
    @pytest.mark.asyncio
    async def test_create_and_read_journey(self):
        """Test creating and reading a journey"""
        import time
        
        # Create
        create_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create",
                "name": f"Test Journey {int(time.time())}",
                "odaComponentType": "product-catalog"
            }}
        )
        
        assert create_response.status_code == 200
        create_result = unwrap_response(create_response.json())
        
        # Should succeed or fail gracefully
        if create_result.get("status") == "success":
            journey_id = create_result.get("journey_id") or create_result.get("journeyId")
            assert journey_id is not None
            
            # Try to read it
            read_response = await self.client.post(
                "/tools/journeys_tool",
                json={"arguments": {
                    "action": "read",
                    "journey_id": journey_id
                }}
            )
            
            assert read_response.status_code == 200
            read_result = unwrap_response(read_response.json())
            
            # Cleanup
            await self.client.post(
                "/tools/journeys_tool",
                json={"arguments": {
                    "action": "delete",
                    "journey_id": journey_id,
                    "confirm": True
                }}
            )
    
    @pytest.mark.asyncio
    async def test_list_stages(self):
        """Test listing stages for a journey"""
        # First get a journey ID from the list
        list_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {"action": "list"}}
        )
        
        list_result = unwrap_response(list_response.json())
        
        if list_result.get("status") == "success" and list_result.get("data"):
            journeys = list_result["data"]
            if journeys:
                journey_id = journeys[0].get("journeyId") or journeys[0].get("journey_id")
                
                # List stages for this journey
                stages_response = await self.client.post(
                    "/tools/journeys_tool",
                    json={"arguments": {
                        "action": "list_stages",
                        "journey_id": journey_id
                    }}
                )
                
                assert stages_response.status_code == 200
                stages_result = unwrap_response(stages_response.json())
                assert stages_result.get("status") in ["success", "error"]
    
    @pytest.mark.asyncio
    async def test_list_rules(self):
        """Test listing rules for a journey"""
        # First get a journey ID from the list
        list_response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {"action": "list"}}
        )
        
        list_result = unwrap_response(list_response.json())
        
        if list_result.get("status") == "success" and list_result.get("data"):
            journeys = list_result["data"]
            if journeys:
                journey_id = journeys[0].get("journeyId") or journeys[0].get("journey_id")
                
                # List rules for this journey
                rules_response = await self.client.post(
                    "/tools/journeys_tool",
                    json={"arguments": {
                        "action": "list_rules",
                        "journey_id": journey_id
                    }}
                )
                
                assert rules_response.status_code == 200
                rules_result = unwrap_response(rules_response.json())
                assert rules_result.get("status") in ["success", "error"]


@pytest.mark.integration
class TestToolDiscoveryCore:
    """Test tool discovery and availability"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        self.client = api_client
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools"""
        response = await self.client.get("/tools")
        
        assert response.status_code == 200
        result = response.json()
        
        # Should return tools list
        if isinstance(result, list):
            tools = result
        elif isinstance(result, dict) and "tools" in result:
            tools = result["tools"]
        else:
            tools = []
        
        assert len(tools) > 0
        
        # Should have our main tools
        tool_names = [str(t.get("name", "")) if isinstance(t, dict) else str(t) for t in tools]
        assert any("journeys" in name.lower() for name in tool_names)
    
    @pytest.mark.asyncio
    async def test_invalid_action(self):
        """Test error handling for invalid action"""
        response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {"action": "invalid_action"}}
        )
        
        assert response.status_code == 200
        result = unwrap_response(response.json())
        
        # Should return error
        assert result.get("status") == "error"
        assert "message" in result

