"""
FDW Error Classes for nexus-backend

This module provides custom exception classes for FDW (Foreign Data Wrapper)
related errors, following the same pattern as localstack_errors.py.

Error Hierarchy:
    FDWError (base)
    ├── FDWConnectionError      - PostgreSQL connection failure
    ├── FDWQueryError            - Query execution failure
    ├── FDWTableNotFoundError    - Referenced table does not exist
    ├── FDWTimeoutError          - Query exceeded timeout
    └── FDWConfigurationError    - Missing or invalid configuration
"""

from typing import List, Optional


class FDWError(Exception):
    """Base exception for all FDW-related errors."""
    pass


class FDWConnectionError(FDWError):
    """
    PostgreSQL connection failure.

    Stores host and port for programmatic access but MUST NOT
    include any password in its message or string representation.
    """

    def __init__(self, message: str, host: str, port: int, original_error: Optional[Exception] = None):
        self.host = host
        self.port = port
        self.original_error = original_error
        # Build a safe message that includes host:port but never a password
        self.message = f"{message} (host={host}, port={port})"
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"FDWConnectionError(host={self.host!r}, port={self.port!r})"


class FDWQueryError(FDWError):
    """Query execution failure."""

    def __init__(self, message: str, table: str, original_error: Optional[Exception] = None):
        self.table = table
        self.original_error = original_error
        self.message = f"{message} (table={table})"
        super().__init__(self.message)


class FDWTableNotFoundError(FDWError):
    """Referenced table does not exist."""

    def __init__(self, schema: str, table: str):
        self.schema = schema
        self.table = table
        self.message = f"Table not found: {schema}.{table}"
        super().__init__(self.message)


class FDWTimeoutError(FDWError):
    """Query exceeded timeout."""

    def __init__(self, timeout_seconds: int, table: str):
        self.timeout_seconds = timeout_seconds
        self.table = table
        self.message = f"Query exceeded {timeout_seconds}s timeout on table {table}"
        super().__init__(self.message)


class FDWConfigurationError(FDWError):
    """
    Missing or invalid FDW configuration.

    Raised when FDW_PG_HOST is set but required parameters are missing.
    """

    def __init__(self, missing_params: List[str]):
        self.missing_params = missing_params
        message = (
            f"FDW configuration incomplete. Missing required parameters: "
            f"{', '.join(missing_params)}"
        )
        super().__init__(message)

