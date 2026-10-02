"""
Unit tests for AWSClientManager + aws_access_config integration.

Validates that ``AWSClientManager.create_client`` and ``create_resource``
honor the active access mode via ``aws_access_config.merge_kwargs``.
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


_AWS_ENV_VARS = (
    "USE_LOCALSTACK",
    "AWS_ACCESS_MODE",
    "AWS_DISABLE_EXPLICIT_SERVICE_ENDPOINTS",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "AWS_ENDPOINT_URL_DYNAMODB",
    "AWS_ENDPOINT_URL_S3",
    "AWS_PROFILE",
    "AWS_ROLE_ARN",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in _AWS_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _make_manager_with_fake_session():
    """Builds an AWSClientManager with a stubbed boto3 session that records calls."""
    from src.utils.aws_client_utils import AWSClientManager

    mgr = AWSClientManager()
    fake_client = MagicMock(name="boto3-client")
    fake_resource = MagicMock(name="boto3-resource")
    fake_session = MagicMock()
    fake_session.client.return_value = fake_client
    fake_session.resource.return_value = fake_resource
    mgr._create_session = lambda: fake_session  # type: ignore[method-assign]
    mgr._test_instance_role = lambda: False  # type: ignore[method-assign]
    return mgr, fake_session


# ── create_client ───────────────────────────────────────────────────────


def test_create_client_higher_cost_no_endpoint_url(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    mgr, sess = _make_manager_with_fake_session()
    mgr.create_client("dynamodb")
    kwargs = sess.client.call_args.kwargs
    assert "endpoint_url" not in kwargs
    # config kwarg is present (default Config from AWSClientManager)
    assert "config" in kwargs


@pytest.mark.parametrize("mode", ["moderate", "lowest-cost", "public-nodes"])
def test_create_client_public_modes_skip_endpoint_url(monkeypatch, mode):
    monkeypatch.setenv("AWS_ACCESS_MODE", mode)
    monkeypatch.setenv("AWS_ENDPOINT_URL_DYNAMODB", "https://override.example/")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    mgr, sess = _make_manager_with_fake_session()
    mgr.create_client("dynamodb")
    kwargs = sess.client.call_args.kwargs
    # Public modes must NOT pass endpoint_url — traffic goes via NAT/IGW to
    # default public regional hostnames, even if the per-service env override
    # is set.
    assert "endpoint_url" not in kwargs


def test_create_client_higher_cost_honors_per_service_override(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ENDPOINT_URL_DYNAMODB", "https://override.example/")
    mgr, sess = _make_manager_with_fake_session()
    mgr.create_client("dynamodb")
    kwargs = sess.client.call_args.kwargs
    assert kwargs.get("endpoint_url") == "https://override.example/"


def test_create_client_does_not_pass_region_name_kwarg(monkeypatch):
    """region is already on the session; passing it again raises in boto3."""
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    mgr, sess = _make_manager_with_fake_session()
    mgr.create_client("dynamodb")
    kwargs = sess.client.call_args.kwargs
    assert "region_name" not in kwargs


# ── create_resource ─────────────────────────────────────────────────────


def test_create_resource_higher_cost_no_endpoint_url(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    mgr, sess = _make_manager_with_fake_session()
    mgr.create_resource("dynamodb")
    kwargs = sess.resource.call_args.kwargs
    assert "endpoint_url" not in kwargs


@pytest.mark.parametrize("mode", ["moderate", "lowest-cost", "public-nodes"])
def test_create_resource_public_modes_skip_endpoint_url(monkeypatch, mode):
    monkeypatch.setenv("AWS_ACCESS_MODE", mode)
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    mgr, sess = _make_manager_with_fake_session()
    mgr.create_resource("s3")
    kwargs = sess.resource.call_args.kwargs
    assert "endpoint_url" not in kwargs


def test_create_resource_does_not_pass_region_name_kwarg(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    mgr, sess = _make_manager_with_fake_session()
    mgr.create_resource("dynamodb")
    kwargs = sess.resource.call_args.kwargs
    assert "region_name" not in kwargs
