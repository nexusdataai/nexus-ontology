"""
Data Plane Error Classes for nexus-backend

This module provides custom exception classes for Data Plane
related errors, following the same pattern as fdw_errors.py.

Error Hierarchy:
    DataPlaneError (base)
    ├── DataPlaneNotFoundError       - Data Plane record not found in DynamoDB
    ├── DataPlaneStorageError        - DynamoDB operation failure
    └── DataPlaneValidationError     - Invalid data plane configuration
"""

from typing import Optional


class DataPlaneError(Exception):
    """Base exception for all Data Plane related errors."""
    pass


class DataPlaneNotFoundError(DataPlaneError):
    """Data Plane record not found in DynamoDB."""

    def __init__(self, data_plane_id: str):
        self.data_plane_id = data_plane_id
        super().__init__(f"Data plane not found: {data_plane_id}")


class DataPlaneStorageError(DataPlaneError):
    """DynamoDB operation failure."""

    def __init__(self, message: str, operation: str, original_error: Optional[Exception] = None):
        self.operation = operation
        self.original_error = original_error
        super().__init__(f"Storage error during {operation}: {message}")


class DataPlaneValidationError(DataPlaneError):
    """Invalid data plane configuration."""

    def __init__(self, message: str):
        super().__init__(message)
