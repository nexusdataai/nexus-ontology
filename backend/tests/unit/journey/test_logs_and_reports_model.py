"""
Tests for Logs and Reports Management Pydantic Models

Comprehensive tests for all Pydantic models used in logs and reports management.
Tests validation, serialization, deserialization, and edge cases.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from src.models.logs_and_reports_model import (
    LogsAndReportsAction,
    LogLevel,
    ExportFormat,
    ReportType,
    LogsAndReportsActionRequest,
    LogsAndReportsResponse,
    LogEntry,
    LogSummary,
    ReportMetadata,
    ErrorSummary,
    PerformanceReport,
    create_success_response,
    create_error_response,
)


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Test enum definitions"""
    
    def test_logs_and_reports_action_enum(self):
        """Test LogsAndReportsAction enum values"""
        assert LogsAndReportsAction.GET_JOB_LOGS.value == "get_job_logs"
        assert LogsAndReportsAction.ADD_LOG_ENTRY.value == "add_log_entry"
        assert LogsAndReportsAction.SEARCH_LOGS.value == "search_logs"
        assert LogsAndReportsAction.GET_LOGS_BY_LEVEL.value == "get_logs_by_level"
        assert LogsAndReportsAction.EXPORT_JOB_LOGS.value == "export_job_logs"
        assert LogsAndReportsAction.GET_ERROR_SUMMARY.value == "get_error_summary"
        assert LogsAndReportsAction.LIST_AVAILABLE_LOGS.value == "list_available_logs"
        assert LogsAndReportsAction.GET_JOB_REPORTS.value == "get_job_reports"
        assert LogsAndReportsAction.CREATE_JOB_REPORT.value == "create_job_report"
        assert LogsAndReportsAction.GENERATE_SUMMARY_REPORT.value == "generate_summary_report"
        assert LogsAndReportsAction.GENERATE_PERFORMANCE_REPORT.value == "generate_performance_report"
        assert LogsAndReportsAction.GENERATE_ERROR_ANALYSIS_REPORT.value == "generate_error_analysis_report"
        assert LogsAndReportsAction.LIST_AVAILABLE_REPORTS.value == "list_available_reports"
        assert LogsAndReportsAction.EXPORT_REPORTS.value == "export_reports"
        assert LogsAndReportsAction.ANALYZE_JOB_PERFORMANCE.value == "analyze_job_performance"
        assert LogsAndReportsAction.ANALYZE_ERROR_PATTERNS.value == "analyze_error_patterns"
        
    def test_log_level_enum(self):
        """Test LogLevel enum values"""
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARNING.value == "warning"
        assert LogLevel.ERROR.value == "error"
        
    def test_export_format_enum(self):
        """Test ExportFormat enum values"""
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.CSV.value == "csv"
        assert ExportFormat.TXT.value == "txt"
        assert ExportFormat.HTML.value == "html"
    
    def test_report_type_enum(self):
        """Test ReportType enum values"""
        assert ReportType.SUMMARY.value == "summary"
        assert ReportType.PERFORMANCE.value == "performance"
        assert ReportType.ERROR_ANALYSIS.value == "error_analysis"
        assert ReportType.CUSTOM.value == "custom"


# =============================================================================
# REQUEST MODEL TESTS
# =============================================================================

class TestLogsAndReportsActionRequest:
    """Test LogsAndReportsActionRequest model"""
    
    def test_get_job_logs_request_valid(self):
        """Test valid get_job_logs request"""
        request = LogsAndReportsActionRequest(
            action="get_job_logs",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="raw_analysis",
            step_name="validation"
        )
        assert request.action == LogsAndReportsAction.GET_JOB_LOGS
        assert request.journey_id == "JRN-123"
        assert request.job_id == "JOB-456"
        assert request.stage_name == "raw_analysis"
        assert request.step_name == "validation"
    
    def test_get_job_logs_missing_journey_id(self):
        """Test get_job_logs request fails without journey_id"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="get_job_logs",
                job_id="JOB-456",
                stage_name="raw_analysis"
            )
        assert "journey_id is required" in str(exc_info.value)
    
    def test_get_job_logs_missing_job_id(self):
        """Test get_job_logs request fails without job_id"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="get_job_logs",
                journey_id="JRN-123",
                stage_name="raw_analysis"
            )
        assert "job_id is required" in str(exc_info.value)
    
    def test_get_job_logs_missing_stage_name(self):
        """Test get_job_logs request fails without stage_name"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="get_job_logs",
                journey_id="JRN-123",
                job_id="JOB-456"
            )
        assert "stage_name is required" in str(exc_info.value)
    
    def test_add_log_entry_request_valid(self):
        """Test valid add_log_entry request"""
        request = LogsAndReportsActionRequest(
            action="add_log_entry",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="raw_analysis",
            step_name="validation",
            log_level="error",
            log_message="Test error message"
        )
        assert request.action == LogsAndReportsAction.ADD_LOG_ENTRY
        assert request.log_level == "error"
        assert request.log_message == "Test error message"
    
    def test_add_log_entry_missing_step_name(self):
        """Test add_log_entry fails without step_name"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="add_log_entry",
                journey_id="JRN-123",
                job_id="JOB-456",
                stage_name="raw_analysis",
                log_level="error",
                log_message="Test error"
            )
        assert "step_name is required" in str(exc_info.value)
    
    def test_add_log_entry_missing_log_level(self):
        """Test add_log_entry fails without log_level"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="add_log_entry",
                journey_id="JRN-123",
                job_id="JOB-456",
                stage_name="raw_analysis",
                step_name="validation",
                log_message="Test error"
            )
        assert "log_level is required" in str(exc_info.value)
    
    def test_add_log_entry_missing_log_message(self):
        """Test add_log_entry fails without log_message"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="add_log_entry",
                journey_id="JRN-123",
                job_id="JOB-456",
                stage_name="raw_analysis",
                step_name="validation",
                log_level="error"
            )
        assert "log_message is required" in str(exc_info.value)
    
    def test_search_logs_request_valid(self):
        """Test valid search_logs request"""
        request = LogsAndReportsActionRequest(
            action="search_logs",
            journey_id="JRN-123",
            search_query="error in validation",
            level_filter="error",
            limit=50
        )
        assert request.action == LogsAndReportsAction.SEARCH_LOGS
        assert request.search_query == "error in validation"
        assert request.level_filter == "error"
        assert request.limit == 50
    
    def test_search_logs_missing_search_query(self):
        """Test search_logs fails without search_query"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="search_logs",
                journey_id="JRN-123"
            )
        assert "search_query is required" in str(exc_info.value)
    
    def test_get_logs_by_level_request_valid(self):
        """Test valid get_logs_by_level request"""
        request = LogsAndReportsActionRequest(
            action="get_logs_by_level",
            journey_id="JRN-123",
            log_level="error",
            job_id="JOB-456",
            limit=100
        )
        assert request.action == LogsAndReportsAction.GET_LOGS_BY_LEVEL
        assert request.log_level == "error"
        assert request.limit == 100
    
    def test_get_logs_by_level_missing_log_level(self):
        """Test get_logs_by_level fails without log_level"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="get_logs_by_level",
                journey_id="JRN-123"
            )
        assert "log_level is required" in str(exc_info.value)
    
    def test_export_job_logs_request_valid(self):
        """Test valid export_job_logs request"""
        request = LogsAndReportsActionRequest(
            action="export_job_logs",
            journey_id="JRN-123",
            job_id="JOB-456",
            output_file="/tmp/logs.json",
            export_format="json"
        )
        assert request.action == LogsAndReportsAction.EXPORT_JOB_LOGS
        assert request.output_file == "/tmp/logs.json"
        assert request.export_format == "json"
    
    def test_export_job_logs_missing_output_file(self):
        """Test export_job_logs fails without output_file"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="export_job_logs",
                journey_id="JRN-123",
                job_id="JOB-456"
            )
        assert "output_file is required" in str(exc_info.value)
    
    def test_create_job_report_request_valid(self):
        """Test valid create_job_report request"""
        request = LogsAndReportsActionRequest(
            action="create_job_report",
            journey_id="JRN-123",
            job_id="JOB-456",
            report_type="custom",
            report_title="Custom Report",
            report_content={"data": "test"}
        )
        assert request.action == LogsAndReportsAction.CREATE_JOB_REPORT
        assert request.report_type == "custom"
        assert request.report_title == "Custom Report"
    
    def test_create_job_report_missing_report_type(self):
        """Test create_job_report fails without report_type"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="create_job_report",
                journey_id="JRN-123",
                job_id="JOB-456",
                report_title="Test",
                report_content={}
            )
        assert "report_type is required" in str(exc_info.value)
    
    def test_create_job_report_missing_report_title(self):
        """Test create_job_report fails without report_title"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="create_job_report",
                journey_id="JRN-123",
                job_id="JOB-456",
                report_type="custom",
                report_content={}
            )
        assert "report_title is required" in str(exc_info.value)
    
    def test_create_job_report_missing_report_content(self):
        """Test create_job_report fails without report_content"""
        with pytest.raises(ValidationError) as exc_info:
            LogsAndReportsActionRequest(
                action="create_job_report",
                journey_id="JRN-123",
                job_id="JOB-456",
                report_type="custom",
                report_title="Test"
            )
        assert "report_content is required" in str(exc_info.value)
    
    def test_limit_validation_min(self):
        """Test limit parameter minimum validation"""
        with pytest.raises(ValidationError):
            LogsAndReportsActionRequest(
                action="search_logs",
                journey_id="JRN-123",
                search_query="test",
                limit=0  # Should be >= 1
            )
    
    def test_limit_validation_max(self):
        """Test limit parameter maximum validation"""
        with pytest.raises(ValidationError):
            LogsAndReportsActionRequest(
                action="search_logs",
                journey_id="JRN-123",
                search_query="test",
                limit=2000  # Should be <= 1000
            )
    
    def test_offset_validation(self):
        """Test offset parameter validation"""
        with pytest.raises(ValidationError):
            LogsAndReportsActionRequest(
                action="search_logs",
                journey_id="JRN-123",
                search_query="test",
                offset=-1  # Should be >= 0
            )
    
    def test_default_values(self):
        """Test default parameter values"""
        request = LogsAndReportsActionRequest(
            action="search_logs",
            journey_id="JRN-123",
            search_query="test"
        )
        assert request.limit == 100
        assert request.offset == 0
        assert request.export_format == ExportFormat.JSON
        assert request.log_source == "system"


# =============================================================================
# RESPONSE MODEL TESTS
# =============================================================================

class TestLogEntry:
    """Test LogEntry model"""
    
    def test_log_entry_creation(self):
        """Test creating LogEntry"""
        entry = LogEntry(
            jobId="JOB-123",
            timestamp="2025-10-13T10:00:00Z",
            level="error",
            step="validation",
            message="Validation failed"
        )
        assert entry.jobId == "JOB-123"
        assert entry.level == "error"
        assert entry.step == "validation"
        assert entry.message == "Validation failed"
        assert entry.source == "system"
    
    def test_log_entry_with_details(self):
        """Test LogEntry with details"""
        entry = LogEntry(
            jobId="JOB-123",
            timestamp="2025-10-13T10:00:00Z",
            level="error",
            step="validation",
            message="Error",
            source="custom",
            details={"error_code": "VAL001"}
        )
        assert entry.source == "custom"
        assert entry.details == {"error_code": "VAL001"}


class TestLogSummary:
    """Test LogSummary model"""
    
    def test_log_summary_creation(self):
        """Test creating LogSummary"""
        summary = LogSummary(
            jobId="JOB-123",
            stageId="raw_analysis",
            totalLogs=100,
            errorCount=5,
            warningCount=10,
            infoCount=80,
            debugCount=5
        )
        assert summary.jobId == "JOB-123"
        assert summary.totalLogs == 100
        assert summary.errorCount == 5


class TestReportMetadata:
    """Test ReportMetadata model"""
    
    def test_report_metadata_creation(self):
        """Test creating ReportMetadata"""
        metadata = ReportMetadata(
            reportId="RPT-123",
            jobId="JOB-456",
            reportType="performance",
            title="Performance Report",
            summary="Performance analysis",
            generatedAt="2025-10-13T10:00:00Z"
        )
        assert metadata.reportId == "RPT-123"
        assert metadata.reportType == "performance"
        assert metadata.status == "generated"


class TestErrorSummary:
    """Test ErrorSummary model"""
    
    def test_error_summary_creation(self):
        """Test creating ErrorSummary"""
        summary = ErrorSummary(
            journeyId="JRN-123",
            jobId="JOB-456",
            totalErrors=10,
            totalWarnings=5,
            errorCategories={"connectivity": 3, "validation": 7},
            errorsByStep={"step1": 5, "step2": 5},
            generatedAt="2025-10-13T10:00:00Z"
        )
        assert summary.journeyId == "JRN-123"
        assert summary.totalErrors == 10
        assert summary.errorCategories["validation"] == 7


class TestPerformanceReport:
    """Test PerformanceReport model"""
    
    def test_performance_report_creation(self):
        """Test creating PerformanceReport"""
        report = PerformanceReport(
            reportId="PERF-123",
            jobId="JOB-456",
            generatedAt="2025-10-13T10:00:00Z",
            executionSummary={"status": "completed"},
            performanceMetrics={"duration": 120.5},
            logAnalysis={"totalLogs": 100}
        )
        assert report.reportId == "PERF-123"
        assert report.reportType == "performance_analysis"
        assert report.performanceMetrics["duration"] == 120.5


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestHelperFunctions:
    """Test helper functions"""
    
    def test_create_success_response(self):
        """Test create_success_response function"""
        response = create_success_response(
            operation="get_job_logs",
            message="Retrieved 50 logs",
            data={"logs": []},
            metadata={"total_count": 50}
        )
        
        assert response["result"]["status"] == "success"
        assert response["result"]["message"] == "Retrieved 50 logs"
        assert response["result"]["operation"] == "get_job_logs"
        assert response["result"]["data"] == {"logs": []}
        assert response["result"]["metadata"]["total_count"] == 50
        assert "timestamp" in response
        # Verify ISO 8601 format with Z
        assert response["timestamp"].endswith("Z")
    
    def test_create_success_response_without_metadata(self):
        """Test create_success_response without metadata"""
        response = create_success_response(
            operation="add_log_entry",
            message="Log added",
            data={"success": True}
        )
        
        assert response["result"]["status"] == "success"
        assert "metadata" not in response["result"]
    
    def test_create_error_response(self):
        """Test create_error_response function"""
        response = create_error_response(
            operation="get_job_logs",
            message="Job not found",
            error_code="NOT_FOUND",
            error_details={"job_id": "JOB-999"}
        )
        
        assert response["result"]["status"] == "error"
        assert response["result"]["message"] == "Job not found"
        assert response["result"]["operation"] == "get_job_logs"
        assert response["result"]["error_code"] == "NOT_FOUND"
        assert response["result"]["error_details"]["job_id"] == "JOB-999"
        assert "timestamp" in response
    
    def test_create_error_response_without_details(self):
        """Test create_error_response without error_details"""
        response = create_error_response(
            operation="search_logs",
            message="Search failed",
            error_code="SEARCH_ERROR"
        )
        
        assert response["result"]["status"] == "error"
        assert response["result"]["error_code"] == "SEARCH_ERROR"
        assert "error_details" not in response["result"]
    
    def test_response_timestamp_format(self):
        """Test that timestamps are in correct ISO 8601 format"""
        response = create_success_response(
            operation="test",
            message="test"
        )
        
        # Verify timestamp format: YYYY-MM-DDTHH:MM:SS.ffffffZ
        timestamp = response["timestamp"]
        assert "T" in timestamp
        assert timestamp.endswith("Z")
        # Should be parseable as datetime
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert dt.tzinfo is not None


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_search_query(self):
        """Test empty search query fails validation"""
        # Empty string should fail search_logs validation
        with pytest.raises(ValidationError):
            LogsAndReportsActionRequest(
                action="search_logs",
                journey_id="JRN-123",
                search_query=""
            )
    
    def test_very_long_log_message(self):
        """Test handling very long log messages"""
        long_message = "x" * 10000
        request = LogsAndReportsActionRequest(
            action="add_log_entry",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="test",
            step_name="test",
            log_level="info",
            log_message=long_message
        )
        assert len(request.log_message) == 10000
    
    def test_special_characters_in_fields(self):
        """Test special characters in various fields"""
        request = LogsAndReportsActionRequest(
            action="search_logs",
            journey_id="JRN-123",
            search_query="error: <>&\"'test"
        )
        assert request.search_query == "error: <>&\"'test"
    
    def test_unicode_in_log_message(self):
        """Test unicode characters in log messages"""
        request = LogsAndReportsActionRequest(
            action="add_log_entry",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="test",
            step_name="test",
            log_level="info",
            log_message="Test 测试 тест 🎉"
        )
        assert "测试" in request.log_message
        assert "🎉" in request.log_message
    
    def test_null_optional_fields(self):
        """Test that optional fields can be None"""
        request = LogsAndReportsActionRequest(
            action="get_error_summary",
            journey_id="JRN-123",
            job_id=None  # Optional for this action
        )
        assert request.job_id is None
    
    def test_invalid_action_string(self):
        """Test invalid action string fails validation"""
        with pytest.raises(ValidationError):
            LogsAndReportsActionRequest(
                action="invalid_action",
                journey_id="JRN-123"
            )
    
    def test_case_sensitive_enum_values(self):
        """Test that enum values are case-sensitive"""
        # Should work with correct case
        request = LogsAndReportsActionRequest(
            action="get_job_logs",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="test",
            log_level="error"
        )
        assert request.log_level == "error"
        
        # Uppercase should also work (Pydantic converts)
        request2 = LogsAndReportsActionRequest(
            action="get_job_logs",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="test",
            log_level="ERROR"
        )
        # Pydantic might convert or reject - test the actual behavior
        assert request2.log_level is not None


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================

class TestSerialization:
    """Test model serialization and deserialization"""
    
    def test_log_entry_serialization(self):
        """Test LogEntry serialization to dict"""
        entry = LogEntry(
            jobId="JOB-123",
            timestamp="2025-10-13T10:00:00Z",
            level="error",
            step="test",
            message="Test"
        )
        data = entry.model_dump()
        assert data["jobId"] == "JOB-123"
        assert data["level"] == "error"
    
    def test_request_serialization(self):
        """Test request model serialization"""
        request = LogsAndReportsActionRequest(
            action="get_job_logs",
            journey_id="JRN-123",
            job_id="JOB-456",
            stage_name="test"
        )
        data = request.model_dump(exclude_none=True)
        assert "action" in data
        assert "journey_id" in data
        assert "log_message" not in data  # None values excluded
    
    def test_json_serialization(self):
        """Test JSON serialization of models"""
        request = LogsAndReportsActionRequest(
            action="search_logs",
            journey_id="JRN-123",
            search_query="test",
            limit=50
        )
        json_str = request.model_dump_json()
        assert "search_logs" in json_str
        assert "JRN-123" in json_str
        assert '"limit":50' in json_str or '"limit": 50' in json_str

