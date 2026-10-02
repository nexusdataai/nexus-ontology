"""
Basic integration tests that don't require DynamoDB
"""

import pytest
import json


@pytest.mark.integration
class TestBasicIntegration:
    """Basic integration tests for the gateway"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, api_client):
        """Test the health check endpoint"""
        response = await api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "ok", True]
    
    @pytest.mark.asyncio
    async def test_tools_list(self, api_client):
        """Test listing available tools"""
        # Add API key
        api_client.headers["x-api-key"] = "super-secret"
        
        response = await api_client.get("/tools")
        assert response.status_code == 200
        
        tools = response.json()
        assert isinstance(tools, dict) or isinstance(tools, list)
        
        # Check if journeys_tool is in the list
        tools_str = str(tools)
        assert "journeys_tool" in tools_str or "journeys" in tools_str
    
    @pytest.mark.asyncio
    async def test_journey_list_action(self, api_client):
        """Test listing journeys (should work even with empty DynamoDB)"""
        # Add API key
        api_client.headers["x-api-key"] = "super-secret"
        
        # List journeys - should work even if DynamoDB is not accessible
        list_payload = {
            "arguments": {
                "action": "list"
            }
        }
        
        response = await api_client.post("/tools/journeys_tool", json=list_payload)
        
        # Even if DynamoDB fails, the endpoint should return 200
        assert response.status_code == 200
        
        result = response.json()
        
        # Parse the MCP response
        if "content" in result and result["content"]:
            content = json.loads(result["content"][0]["text"])
            # List should return success even if empty
            assert content["status"] in ["success", "error"]
            if content["status"] == "success":
                assert "data" in content
                assert isinstance(content["data"], list)
    
    @pytest.mark.asyncio  
    async def test_invalid_action(self, api_client):
        """Test error handling for invalid actions"""
        # Add API key
        api_client.headers["x-api-key"] = "super-secret"
        
        invalid_payload = {
            "arguments": {
                "action": "invalid_action"
            }
        }
        
        response = await api_client.post("/tools/journeys_tool", json=invalid_payload)
        assert response.status_code == 200  # MCP returns 200 with error in content
        
        result = response.json()
        
        # Should return an error for invalid action
        if "content" in result and result["content"]:
            content = json.loads(result["content"][0]["text"])
            assert content["status"] == "error"
            assert "invalid" in content["message"].lower() or "unknown" in content["message"].lower()
    
    @pytest.mark.asyncio
    async def test_missing_api_key(self, api_client):
        """Test that API key is required"""
        # Remove API key if present
        api_client.headers.pop("x-api-key", None)
        
        response = await api_client.get("/tools")
        assert response.status_code == 422  # Missing required header
        
        result = response.json()
        assert "detail" in result
        # Check error mentions missing header
        detail_str = str(result["detail"])
        assert "x-api-key" in detail_str or "Field required" in detail_str
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, api_client):
        """Test that invalid API key is rejected"""
        api_client.headers["x-api-key"] = "wrong-key"
        
        response = await api_client.get("/tools")
        assert response.status_code == 401  # Unauthorized
        
        result = response.json()
        assert "detail" in result
        assert "Invalid API key" in result["detail"]
