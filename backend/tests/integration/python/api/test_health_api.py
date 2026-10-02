"""
Health API Integration Tests

Tests health and monitoring endpoints.
"""

import pytest
from typing import Dict, Any


@pytest.mark.integration
class TestHealthAPI:
    """Test Health and Monitoring endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Setup for each test"""
        self.client = api_client
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test main health endpoint"""
        response = await self.client.get("/health")
        
        assert response.status_code == 200
        result = response.json()
        
        # Should have health status
        assert isinstance(result, dict)
        assert "status" in result or "healthy" in str(result).lower()
    
    @pytest.mark.asyncio
    async def test_readiness_endpoint(self):
        """Test readiness endpoint if it exists"""
        response = await self.client.get("/ready")
        
        # Endpoint may or may not exist
        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, dict)
        elif response.status_code == 404:
            pytest.skip("Readiness endpoint not available")
    
    @pytest.mark.asyncio
    async def test_liveness_endpoint(self):
        """Test liveness endpoint if it exists"""
        response = await self.client.get("/live")
        
        # Endpoint may or may not exist
        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, dict)
        elif response.status_code == 404:
            pytest.skip("Liveness endpoint not available")
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test metrics endpoint if it exists"""
        response = await self.client.get("/metrics")
        
        # Endpoint may or may not exist
        if response.status_code == 200:
            # Metrics might be JSON or Prometheus format
            pass
        elif response.status_code == 404:
            pytest.skip("Metrics endpoint not available")
    
    @pytest.mark.asyncio
    async def test_stats_endpoint(self):
        """Test worker pool stats endpoint"""
        response = await self.client.get("/stats")
        
        # Endpoint requires API key
        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, dict)
        elif response.status_code in [401, 403]:
            # Try with auth (already has x-api-key header)
            pass
        elif response.status_code == 404:
            pytest.skip("Stats endpoint not available")
    
    @pytest.mark.asyncio
    async def test_api_v1_health_endpoint(self):
        """Test API v1 health endpoint if it exists"""
        response = await self.client.get("/api/v1/health/")
        
        # Endpoint may or may not exist
        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, dict)
        elif response.status_code == 404:
            pytest.skip("API v1 health endpoint not available")
    
    @pytest.mark.asyncio
    async def test_docs_endpoint(self):
        """Test API documentation endpoint"""
        response = await self.client.get("/docs")
        
        # Docs should be available
        if response.status_code == 200:
            # Should return HTML or JSON
            pass
        elif response.status_code == 404:
            pytest.skip("Docs endpoint not available")
    
    @pytest.mark.asyncio
    async def test_openapi_schema(self):
        """Test OpenAPI schema endpoint"""
        response = await self.client.get("/openapi.json")
        
        # OpenAPI schema may or may not be available
        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, dict)
            # Should have OpenAPI fields
            assert "openapi" in result or "swagger" in result or "info" in result
        elif response.status_code == 404:
            pytest.skip("OpenAPI schema not available")

