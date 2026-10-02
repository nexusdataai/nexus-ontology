"""
Unit tests for Journey REST API endpoints.

Tests all journey, stage, and job API endpoints in isolation with mocked services.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime
import sys
import os

# Add source paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))


class TestJourneyAPIEndpoints:
    """Test suite for Journey CRUD API endpoints."""
    
    @pytest.fixture
    def mock_journey_service(self):
        """Create mock journey service."""
        mock = MagicMock()
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = "success"
        mock_response.message = "Operation successful"
        mock_response.journey_id = "JRN-TEST-001"
        mock_response.job_id = None
        mock_response.data = {
            "journeyId": "JRN-TEST-001",
            "name": "Test Journey",
            "status": "pending"
        }
        
        mock.execute_action = AsyncMock(return_value=mock_response)
        return mock
    
    @pytest.fixture
    def test_client(self, mock_journey_service):
        """Create test client with mocked service."""
        with patch('src.apis.journey_api.journey_service', mock_journey_service):
            with patch('src.apis.journey_api.service_available', True):
                with patch('src.apis.journey_api.models_available', True):
                    from fastapi import FastAPI
                    from src.apis.journey_api import router
                    
                    app = FastAPI()
                    app.include_router(router, prefix="/api/v1/journeys")
                    
                    yield TestClient(app)
    
    def test_create_journey_endpoint(self, test_client):
        """Test POST /api/v1/journeys creates a journey."""
        response = test_client.post(
            "/api/v1/journeys/",
            json={
                "name": "Call Processing Test",
                "description": "Test journey for call processing",
                "odaComponentType": "CALLCENTER"
            }
        )
        
        # Should return success even with mock
        assert response.status_code == 200
        data = response.json()
        assert "journey_id" in data or "success" in data
    
    def test_list_journeys_endpoint(self, test_client):
        """Test GET /api/v1/journeys lists journeys."""
        response = test_client.get("/api/v1/journeys/")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data or "total" in data
    
    def test_get_journey_status_endpoint(self, test_client):
        """Test GET /api/v1/journeys/{id}/status returns status."""
        response = test_client.get("/api/v1/journeys/JRN-TEST-001/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "status" in data
    
    def test_delete_journey_endpoint(self, test_client, mock_journey_service):
        """Test DELETE /api/v1/journeys/{id} deletes journey."""
        response = test_client.delete("/api/v1/journeys/JRN-TEST-001?force=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


class TestStageAPIEndpoints:
    """Test suite for Stage management API endpoints."""
    
    @pytest.fixture
    def mock_journey_service(self):
        """Create mock journey service."""
        mock = MagicMock()
        
        mock_response = MagicMock()
        mock_response.status = "success"
        mock_response.message = "Stage added"
        mock_response.data = {
            "stageId": "call_process",
            "name": "Call Processing",
            "status": "pending"
        }
        
        mock.execute_action = AsyncMock(return_value=mock_response)
        return mock
    
    @pytest.fixture
    def test_client(self, mock_journey_service):
        """Create test client."""
        with patch('src.apis.journey_api.journey_service', mock_journey_service):
            with patch('src.apis.journey_api.service_available', True):
                with patch('src.apis.journey_api.models_available', True):
                    from fastapi import FastAPI
                    from src.apis.journey_api import router
                    
                    app = FastAPI()
                    app.include_router(router, prefix="/api/v1/journeys")
                    
                    yield TestClient(app)
    
    def test_list_stages_endpoint(self, test_client):
        """Test GET /api/v1/journeys/{id}/stages lists stages."""
        response = test_client.get("/api/v1/journeys/JRN-TEST-001/stages")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "stages" in data
    
    def test_add_stage_endpoint(self, test_client):
        """Test POST /api/v1/journeys/{id}/stages adds a stage."""
        response = test_client.post(
            "/api/v1/journeys/JRN-TEST-001/stages",
            params={
                "stage_id": "call_process",
                "name": "Call Processing",
                "description": "Process Webex CC calls",
                "order": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["stage_id"] == "call_process"
    
    def test_add_stage_with_config(self, test_client):
        """Test adding stage with configuration."""
        response = test_client.post(
            "/api/v1/journeys/JRN-TEST-001/stages",
            params={
                "stage_id": "call_process",
                "order": 0
            },
            json={
                "minutes_back": 60,
                "transcribe": True,
                "register_glue": True,
                "run_analysis": True
            }
        )
        
        assert response.status_code == 200
    
    def test_update_stage_endpoint(self, test_client):
        """Test PUT /api/v1/journeys/{id}/stages/{stage_id} updates stage."""
        response = test_client.put(
            "/api/v1/journeys/JRN-TEST-001/stages/call_process",
            params={"status": "running"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_delete_stage_endpoint(self, test_client):
        """Test DELETE /api/v1/journeys/{id}/stages/{stage_id} deletes stage."""
        response = test_client.delete(
            "/api/v1/journeys/JRN-TEST-001/stages/call_process"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


class TestJobAPIEndpoints:
    """Test suite for Job execution API endpoints."""
    
    @pytest.fixture
    def mock_journey_service(self):
        """Create mock journey service."""
        mock = MagicMock()
        
        mock_response = MagicMock()
        mock_response.status = "success"
        mock_response.message = "Job started"
        mock_response.journey_id = "JRN-TEST-001"
        mock_response.job_id = "JOB-TEST-001"
        mock_response.data = {
            "jobId": "JOB-TEST-001",
            "stageId": "call_process",
            "status": "running",
            "progress": 0
        }
        
        mock.execute_action = AsyncMock(return_value=mock_response)
        return mock
    
    @pytest.fixture
    def test_client(self, mock_journey_service):
        """Create test client."""
        with patch('src.apis.journey_api.journey_service', mock_journey_service):
            with patch('src.apis.journey_api.service_available', True):
                with patch('src.apis.journey_api.models_available', True):
                    from fastapi import FastAPI
                    from src.apis.journey_api import router
                    
                    app = FastAPI()
                    app.include_router(router, prefix="/api/v1/journeys")
                    
                    yield TestClient(app)
    
    def test_run_job_endpoint(self, test_client):
        """Test POST /api/v1/journeys/{id}/jobs runs a job."""
        response = test_client.post(
            "/api/v1/journeys/JRN-TEST-001/jobs",
            params={
                "stage_id": "call_process",
                "triggered_by": "test"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "job_id" in data
        assert data["stage_id"] == "call_process"
    
    def test_list_jobs_endpoint(self, test_client):
        """Test GET /api/v1/journeys/{id}/jobs lists jobs."""
        response = test_client.get("/api/v1/journeys/JRN-TEST-001/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "jobs" in data
    
    def test_list_jobs_with_filter(self, test_client):
        """Test listing jobs with stage filter."""
        response = test_client.get(
            "/api/v1/journeys/JRN-TEST-001/jobs",
            params={"stage_id": "call_process"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
    
    def test_get_job_endpoint(self, test_client):
        """Test GET /api/v1/journeys/{id}/jobs/{job_id} gets job details."""
        response = test_client.get(
            "/api/v1/journeys/JRN-TEST-001/jobs/JOB-TEST-001"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
    
    def test_get_job_status_endpoint(self, test_client):
        """Test GET /api/v1/journeys/{id}/jobs/{job_id}/status gets status."""
        response = test_client.get(
            "/api/v1/journeys/JRN-TEST-001/jobs/JOB-TEST-001/status"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "status" in data
        assert "progress" in data
    
    def test_cancel_job_endpoint(self, test_client):
        """Test POST /api/v1/journeys/{id}/jobs/{job_id}/cancel cancels job."""
        response = test_client.post(
            "/api/v1/journeys/JRN-TEST-001/jobs/JOB-TEST-001/cancel",
            params={"reason": "Test cancellation"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_retry_job_endpoint(self, test_client):
        """Test POST /api/v1/journeys/{id}/jobs/{job_id}/retry retries job."""
        response = test_client.post(
            "/api/v1/journeys/JRN-TEST-001/jobs/JOB-TEST-001/retry",
            params={"reason": "Test retry"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "new_job_id" in data


class TestAPIValidation:
    """Test suite for API input validation."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client without mocked service (uses fallback)."""
        from fastapi import FastAPI
        from src.apis.journey_api import router
        
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/journeys")
        
        yield TestClient(app)
    
    def test_create_journey_requires_name(self, test_client):
        """Test that create journey requires name field."""
        response = test_client.post(
            "/api/v1/journeys/",
            json={
                "description": "No name provided",
                "odaComponentType": "CALLCENTER"
            }
        )
        
        # Should return validation error
        assert response.status_code == 422
    
    def test_add_stage_requires_stage_id(self, test_client):
        """Test that add stage requires stage_id."""
        response = test_client.post(
            "/api/v1/journeys/JRN-TEST-001/stages"
        )
        
        # Should return validation error
        assert response.status_code == 422
    
    def test_run_job_requires_stage_id(self, test_client):
        """Test that run job requires stage_id."""
        response = test_client.post(
            "/api/v1/journeys/JRN-TEST-001/jobs"
        )
        
        # Should return validation error
        assert response.status_code == 422


class TestMockModeResponses:
    """Test API responses in mock mode (no service available)."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client in mock mode."""
        with patch('src.apis.journey_api.journey_service', None):
            with patch('src.apis.journey_api.service_available', False):
                with patch('src.apis.journey_api.models_available', False):
                    from fastapi import FastAPI
                    from src.apis.journey_api import router
                    
                    app = FastAPI()
                    app.include_router(router, prefix="/api/v1/journeys")
                    
                    yield TestClient(app)
    
    def test_create_journey_mock_response(self, test_client):
        """Test create journey returns mock response."""
        response = test_client.post(
            "/api/v1/journeys/",
            json={
                "name": "Mock Journey",
                "odaComponentType": "CALLCENTER"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "JRN-TEST" in data["journey_id"]
    
    def test_list_stages_mock_response(self, test_client):
        """Test list stages returns mock response."""
        response = test_client.get("/api/v1/journeys/JRN-TEST-001/stages")
        
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        assert len(data["stages"]) > 0
    
    def test_run_job_mock_response(self, test_client):
        """Test run job returns mock response."""
        response = test_client.post(
            "/api/v1/journeys/JRN-TEST-001/jobs",
            params={"stage_id": "call_process"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "running"
    
    def test_get_job_status_mock_response(self, test_client):
        """Test get job status returns mock response with progress."""
        response = test_client.get(
            "/api/v1/journeys/JRN-TEST-001/jobs/JOB-TEST-001/status"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "progress" in data
        assert data["progress"] >= 0

