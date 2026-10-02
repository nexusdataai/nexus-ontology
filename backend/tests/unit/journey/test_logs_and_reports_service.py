"""
Tests for Logs and Reports Management Service

Comprehensive tests for the LogsAndReportsService class.
Tests all service methods with mocked DynamoDB/S3 operations.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timezone

from src.services.logs_and_reports_service import LogsAndReportsService
from src.models.logs_and_reports_model import LogsAndReportsActionRequest, LogsAndReportsAction


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def service():
    """Create LogsAndReportsService instance with mocked manager"""
    with patch('src.services.logs_and_reports_service.ComprehensiveJourneyManager'):
        service = LogsAndReportsService()
        return service


@pytest.fixture
def mock_manager():
    """Create mock ComprehensiveJourneyManager"""
    manager = Mock()
    manager.table = Mock()
    manager.clean_journey_id = Mock(side_effect=lambda x: x.replace('JOURNEY#', ''))
    return manager


# =============================================================================
# HELPER METHOD TESTS
# =============================================================================

class TestHelperMethods:
    """Test service helper methods"""
    
    def test_convert_decimal_simple(self, service):
        """Test converting simple Decimal to float"""
        result = service._convert_decimal(Decimal('123.45'))
        assert result == 123.45
        assert isinstance(result, float)
    
    def test_convert_decimal_dict(self, service):
        """Test converting dict with Decimals"""
        data = {
            'count': Decimal('100'),
            'rate': Decimal('0.95'),
            'name': 'test'
        }
        result = service._convert_decimal(data)
        assert result['count'] == 100.0
        assert result['rate'] == 0.95
        assert result['name'] == 'test'
    
    def test_convert_decimal_nested(self, service):
        """Test converting nested structures"""
        data = {
            'metrics': {
                'total': Decimal('500'),
                'values': [Decimal('1.1'), Decimal('2.2')]
            }
        }
        result = service._convert_decimal(data)
        assert result['metrics']['total'] == 500.0
        assert result['metrics']['values'][0] == 1.1
        assert result['metrics']['values'][1] == 2.2
    
    def test_convert_decimal_list(self, service):
        """Test converting list with Decimals"""
        data = [Decimal('1'), Decimal('2'), Decimal('3.14')]
        result = service._convert_decimal(data)
        assert result == [1.0, 2.0, 3.14]
    
    def test_convert_decimal_set(self, service):
        """Test converting set with Decimals"""
        data = {Decimal('1'), Decimal('2')}
        result = service._convert_decimal(data)
        assert isinstance(result, set)
        assert 1.0 in result
        assert 2.0 in result


# =============================================================================
# GET JOB LOGS TESTS
# =============================================================================

class TestGetJobLogs:
    """Test get_job_logs service method"""
    
    @pytest.mark.asyncio
    async def test_get_job_logs_success(self, service):
        """Test successful log retrieval"""
        # Mock manager method
        mock_logs = {
            'jobId': 'JOB-456',
            'stageId': 'raw_analysis',
            'totalLogs': 10,
            'logs': [
                {'timestamp': '2025-10-13T10:00:00Z', 'level': 'info', 'message': 'Test'}
            ]
        }
        service.manager.get_job_logs = Mock(return_value=mock_logs)
        
        request = LogsAndReportsActionRequest(
            action="get_job_logs",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="raw_analysis"
        )
        
        result = await service.get_job_logs(request)
        
        assert result["result"]["status"] == "success"
        assert result["result"]["operation"] == "get_job_logs"
        assert result["result"]["data"]["totalLogs"] == 10
        assert result["result"]["metadata"]["total_count"] == 10
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_get_job_logs_not_found(self, service):
        """Test log retrieval when logs not found"""
        service.manager.get_job_logs = Mock(return_value=None)
        
        request = LogsAndReportsActionRequest(
            action="get_job_logs",
            journey_id="JRN-123",
            job_id="JOB-999",
            stage_name="raw_analysis"
        )
        
        result = await service.get_job_logs(request)
        
        assert result["result"]["status"] == "error"
        assert result["result"]["error_code"] == "RETRIEVAL_FAILED"
        assert "JOB-999" in result["result"]["message"]
    
    @pytest.mark.asyncio
    async def test_get_job_logs_with_decimal(self, service):
        """Test log retrieval with Decimal values"""
        mock_logs = {
            'jobId': 'JOB-456',
            'totalLogs': Decimal('25'),
            'logs': []
        }
        service.manager.get_job_logs = Mock(return_value=mock_logs)
        
        request = LogsAndReportsActionRequest(
            action="get_job_logs",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="raw_analysis"
        )
        
        result = await service.get_job_logs(request)
        
        assert result["result"]["data"]["totalLogs"] == 25.0
        assert isinstance(result["result"]["data"]["totalLogs"], (int, float))


# =============================================================================
# ADD LOG ENTRY TESTS
# =============================================================================

class TestAddLogEntry:
    """Test add_log_entry service method"""
    
    @pytest.mark.asyncio
    async def test_add_log_entry_success(self, service):
        """Test successful log entry addition"""
        service.manager.add_job_log_entry = Mock(return_value=True)
        
        request = LogsAndReportsActionRequest(
            action="add_log_entry",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="raw_analysis",
            step_name="validation",
            log_level="error",
            log_message="Test error"
        )
        
        result = await service.add_log_entry(request)
        
        assert result["result"]["status"] == "success"
        assert result["result"]["data"]["added"] is True
        assert result["result"]["data"]["jobId"] == "JOB-456"
    
    @pytest.mark.asyncio
    async def test_add_log_entry_failure(self, service):
        """Test log entry addition failure"""
        service.manager.add_job_log_entry = Mock(return_value=False)
        
        request = LogsAndReportsActionRequest(
            action="add_log_entry",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="test",
            step_name="test",
            log_level="info",
            log_message="Test"
        )
        
        result = await service.add_log_entry(request)
        
        assert result["result"]["status"] == "error"
        assert result["result"]["error_code"] == "ADD_FAILED"


# =============================================================================
# SEARCH LOGS TESTS
# =============================================================================

class TestSearchLogs:
    """Test search_logs service method"""
    
    @pytest.mark.asyncio
    async def test_search_logs_success(self, service):
        """Test successful log search"""
        mock_results = {
            'searchQuery': 'error',
            'totalMatches': 5,
            'logs': [{'message': 'error found'}],
            'filters': {}
        }
        service.manager.search_logs = Mock(return_value=mock_results)
        
        request = LogsAndReportsActionRequest(
            action="search_logs",
            journey_id="JRN-123",
            search_query="error"
        )
        
        result = await service.search_logs(request)
        
        assert result["result"]["status"] == "success"
        assert result["result"]["metadata"]["total_count"] == 5
        assert "Found 5 matching" in result["result"]["message"]
    
    @pytest.mark.asyncio
    async def test_search_logs_with_filters(self, service):
        """Test log search with filters"""
        mock_results = {
            'searchQuery': 'error',
            'totalMatches': 3,
            'logs': [],
            'filters': {'level': 'error', 'step': 'validation'}
        }
        service.manager.search_logs = Mock(return_value=mock_results)
        
        request = LogsAndReportsActionRequest(
            action="search_logs",
            journey_id="JRN-123",
            search_query="error",
            level_filter="error",
            step_filter="validation"
        )
        
        result = await service.search_logs(request)
        
        assert result["result"]["status"] == "success"
        service.manager.search_logs.assert_called_once()


# =============================================================================
# EXPORT JOB LOGS TESTS
# =============================================================================

class TestExportJobLogs:
    """Test export_job_logs service method"""
    
    @pytest.mark.asyncio
    async def test_export_job_logs_success(self, service):
        """Test successful log export"""
        service.manager.export_job_logs = Mock(return_value=True)
        
        request = LogsAndReportsActionRequest(
            action="export_job_logs",
            journey_id="JRN-123",
            job_id="JOB-456",
            output_file="/tmp/logs.json",
            export_format="json"
        )
        
        result = await service.export_job_logs(request)
        
        assert result["result"]["status"] == "success"
        assert result["result"]["data"]["exported"] is True
        assert "/tmp/logs.json" in result["result"]["message"]


# =============================================================================
# GET ERROR SUMMARY TESTS
# =============================================================================

class TestGetErrorSummary:
    """Test get_error_summary service method"""
    
    @pytest.mark.asyncio
    async def test_get_error_summary_success(self, service):
        """Test successful error summary generation"""
        mock_summary = {
            'journeyId': 'JRN-123',
            'jobId': 'JOB-456',
            'summary': {
                'totalErrors': 10,
                'totalWarnings': 5,
                'errorCategories': {'validation': 7, 'connectivity': 3}
            }
        }
        service.manager.get_error_summary = Mock(return_value=mock_summary)
        
        request = LogsAndReportsActionRequest(
            action="get_error_summary",
            journey_id="JRN-123",
            job_id="JOB-456"
        )
        
        result = await service.get_error_summary(request)
        
        assert result["result"]["status"] == "success"
        assert result["result"]["metadata"]["total_errors"] == 10
        assert result["result"]["metadata"]["total_warnings"] == 5


# =============================================================================
# GENERATE PERFORMANCE REPORT TESTS
# =============================================================================

class TestGeneratePerformanceReport:
    """Test generate_performance_report service method"""
    
    @pytest.mark.asyncio
    async def test_generate_performance_report_success(self, service):
        """Test successful performance report generation"""
        mock_report = {
            'reportId': 'PERF-123',
            'jobId': 'JOB-456',
            'recommendations': [
                {'type': 'performance', 'priority': 'high'}
            ]
        }
        service.manager.generate_performance_report = Mock(return_value=mock_report)
        
        request = LogsAndReportsActionRequest(
            action="generate_performance_report",
            journey_id="JRN-123",
            job_id="JOB-456"
        )
        
        result = await service.generate_performance_report(request)
        
        assert result["result"]["status"] == "success"
        assert result["result"]["metadata"]["recommendations_count"] == 1


# =============================================================================
# ANALYZE JOB PERFORMANCE TESTS
# =============================================================================

class TestAnalyzeJobPerformance:
    """Test analyze_job_performance service method"""
    
    @pytest.mark.asyncio
    async def test_analyze_job_performance_success(self, service):
        """Test successful job performance analysis"""
        mock_metrics = {
            'jobId': 'JOB-456',
            'duration': 120.5,
            'performanceMetrics': {'errorRate': 0.05}
        }
        service.manager.get_job_metrics = Mock(return_value=mock_metrics)
        
        request = LogsAndReportsActionRequest(
            action="analyze_job_performance",
            journey_id="JRN-123",
            job_id="JOB-456"
        )
        
        result = await service.analyze_job_performance(request)
        
        assert result["result"]["status"] == "success"
        assert result["result"]["metadata"]["duration"] == 120.5
        assert result["result"]["metadata"]["error_rate"] == 0.05


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error handling across service methods"""
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, service):
        """Test handling of validation errors"""
        # Invalid request should be caught at model level before service
        with pytest.raises(Exception):
            request = LogsAndReportsActionRequest(
                action="get_job_logs",
                # Missing required fields
            )
    
    @pytest.mark.asyncio
    async def test_manager_exception_handling(self, service):
        """Test handling of manager exceptions"""
        service.manager.get_job_logs = Mock(side_effect=Exception("Database error"))
        
        request = LogsAndReportsActionRequest(
            action="get_job_logs",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="test"
        )
        
        result = await service.get_job_logs(request)
        
        assert result["result"]["status"] == "error"
        assert result["result"]["error_code"] == "INTERNAL_ERROR"
    
    @pytest.mark.asyncio
    async def test_execute_action_with_invalid_action(self, service):
        """Test execute_action with unknown action"""
        request = Mock()
        request.action = "unknown_action"
        
        result = await service.execute_action(request)
        
        assert result["result"]["status"] == "error"
        assert "Unknown action" in result["result"]["message"]


# =============================================================================
# ASYNC OPERATION TESTS
# =============================================================================

class TestAsyncOperations:
    """Test async operation handling"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, service):
        """Test handling multiple concurrent requests"""
        service.manager.get_job_logs = Mock(return_value={'totalLogs': 10, 'logs': []})
        
        requests = [
            LogsAndReportsActionRequest(
                action="get_job_logs",
                journey_id=f"JRN-{i}",
                job_id=f"JOB-{i}",
                stage_name="test"
            )
            for i in range(5)
        ]
        
        results = await asyncio.gather(*[
            service.get_job_logs(req) for req in requests
        ])
        
        assert len(results) == 5
        assert all(r["result"]["status"] == "success" for r in results)
    
    @pytest.mark.asyncio
    async def test_async_to_thread_execution(self, service):
        """Test that operations use asyncio.to_thread"""
        with patch('src.services.logs_and_reports_service.asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = {'totalLogs': 0, 'logs': []}
            
            request = LogsAndReportsActionRequest(
                action="get_job_logs",
                journey_id="JRN-123",
                job_id="JOB-456",
                stage_name="test"
            )
            
            await service.get_job_logs(request)
            
            # Verify async.to_thread was called
            mock_to_thread.assert_called_once()


# =============================================================================
# RESPONSE FORMAT TESTS
# =============================================================================

class TestResponseFormat:
    """Test response format compliance (Rule 9.1)"""
    
    @pytest.mark.asyncio
    async def test_success_response_format(self, service):
        """Test success response follows Rule 9.1 format"""
        service.manager.list_available_logs = Mock(return_value=[])
        
        request = LogsAndReportsActionRequest(
            action="list_available_logs",
            journey_id="JRN-123"
        )
        
        result = await service.list_available_logs(request)
        
        # Verify Rule 9.1 format
        assert "result" in result
        assert "timestamp" in result
        assert result["result"]["status"] == "success"
        assert "message" in result["result"]
        assert "operation" in result["result"]
        assert "data" in result["result"]
        assert "metadata" in result["result"]
        
        # Verify timestamp format (ISO 8601 with Z)
        assert result["timestamp"].endswith("Z")
    
    @pytest.mark.asyncio
    async def test_error_response_format(self, service):
        """Test error response follows Rule 9.1 format"""
        service.manager.get_error_summary = Mock(return_value=None)
        
        request = LogsAndReportsActionRequest(
            action="get_error_summary",
            journey_id="JRN-123"
        )
        
        result = await service.get_error_summary(request)
        
        # Verify Rule 9.1 error format
        assert "result" in result
        assert "timestamp" in result
        assert result["result"]["status"] == "error"
        assert "message" in result["result"]
        assert "operation" in result["result"]
        assert "error_code" in result["result"]

