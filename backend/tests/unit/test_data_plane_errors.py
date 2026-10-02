"""
Unit tests for Data Plane error types.

Tests all error classes in src/utils/data_plane_errors.py, including
attribute storage, message formatting, and inheritance.

**Validates: Requirements 6.1, 6.2**
"""

import pytest

from src.utils.data_plane_errors import (
    DataPlaneError,
    DataPlaneNotFoundError,
    DataPlaneStorageError,
    DataPlaneValidationError,
)


class TestDataPlaneError:
    """Tests for the base DataPlaneError."""

    def test_is_exception(self):
        err = DataPlaneError("something went wrong")
        assert isinstance(err, Exception)

    def test_message(self):
        err = DataPlaneError("something went wrong")
        assert str(err) == "something went wrong"


class TestDataPlaneNotFoundError:
    """Tests for DataPlaneNotFoundError."""

    def test_stores_data_plane_id(self):
        err = DataPlaneNotFoundError("abc-123")
        assert err.data_plane_id == "abc-123"

    def test_message_includes_id(self):
        err = DataPlaneNotFoundError("dp-456")
        assert "dp-456" in str(err)

    def test_inherits_from_data_plane_error(self):
        err = DataPlaneNotFoundError("id-1")
        assert isinstance(err, DataPlaneError)


class TestDataPlaneStorageError:
    """Tests for DataPlaneStorageError."""

    def test_stores_operation(self):
        err = DataPlaneStorageError("failed", operation="put_item")
        assert err.operation == "put_item"

    def test_stores_original_error(self):
        cause = RuntimeError("dynamo timeout")
        err = DataPlaneStorageError("failed", operation="get_item", original_error=cause)
        assert err.original_error is cause

    def test_original_error_defaults_to_none(self):
        err = DataPlaneStorageError("failed", operation="scan")
        assert err.original_error is None

    def test_message_includes_operation(self):
        err = DataPlaneStorageError("connection lost", operation="delete_item")
        msg = str(err)
        assert "delete_item" in msg
        assert "connection lost" in msg

    def test_inherits_from_data_plane_error(self):
        err = DataPlaneStorageError("x", operation="op")
        assert isinstance(err, DataPlaneError)


class TestDataPlaneValidationError:
    """Tests for DataPlaneValidationError."""

    def test_message(self):
        err = DataPlaneValidationError("name cannot be empty")
        assert str(err) == "name cannot be empty"

    def test_inherits_from_data_plane_error(self):
        err = DataPlaneValidationError("bad config")
        assert isinstance(err, DataPlaneError)
