"""
Unified Models Package
Contains all models for both MCP tools and REST APIs
"""

# Journey models for MCP tools
from .journey_model import (
    JourneyAction,
    JourneyActionRequest,
    JourneyResponse,
    JourneyActionResponse  # Alias for JourneyResponse
)

# Logs and reports models for MCP tools
from .logs_and_reports_model import (
    LogsAndReportsAction,
    LogsAndReportsActionRequest
)

# API models for REST endpoints and shared use
from .api_models import (
    # Common enums
    StatusEnum,
    PriorityEnum,
    MetricType,
    TimeRange,
    StreamType,
    ExportFormat,
    HealthStatus,
    
    # Base models
    ResponseBase,
    ErrorResponse,
    
    # Journey API models
    JourneyCreateRequest,
    JourneyResponse,
    JourneyStatusResponse,
    JourneyListRequest,
    JourneyBatchRequest,
    
    # Analytics API models
    AnalyticsRequest,
    AnalyticsResponse,
    DashboardDataRequest,
    
    # Auth API models
    LoginRequest,
    TokenResponse,
    UserProfile,
    
    # Health API models
    HealthCheckResponse,
    ServiceHealthDetail,
    
    # Streaming models
    StreamRequest,
    StreamChunk,
    
    # Export models
    ExportRequest,
    ExportResponse,
    
    # Utility functions
    convert_to_camelcase,
    convert_from_camelcase
)

__all__ = [
    # Journey models
    "JourneyAction",
    "JourneyActionRequest",
    "JourneyActionResponse",
    
    # Logs and reports models
    "LogsAndReportsAction",
    "LogsAndReportsActionRequest",
    
    # Common enums
    "StatusEnum",
    "PriorityEnum",
    "MetricType",
    "TimeRange",
    "StreamType",
    "ExportFormat",
    "HealthStatus",
    
    # Base models
    "ResponseBase",
    "ErrorResponse",
    
    # Journey API models
    "JourneyCreateRequest",
    "JourneyResponse",
    "JourneyStatusResponse",
    "JourneyListRequest",
    "JourneyBatchRequest",
    
    # Analytics API models
    "AnalyticsRequest",
    "AnalyticsResponse",
    "DashboardDataRequest",
    
    # Auth API models
    "LoginRequest",
    "TokenResponse",
    "UserProfile",
    
    # Health API models
    "HealthCheckResponse",
    "ServiceHealthDetail",
    
    # Streaming models
    "StreamRequest",
    "StreamChunk",
    
    # Export models
    "ExportRequest",
    "ExportResponse",
    
    # Utility functions
    "convert_to_camelcase",
    "convert_from_camelcase"
]