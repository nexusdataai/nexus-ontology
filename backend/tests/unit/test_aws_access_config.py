"""
Unit tests for ``src.utils.aws_access_config``.

Covers the AWS Access Dual Mode plan (Phase 2, backend side):
  * ``get_access_mode`` precedence (USE_LOCALSTACK > AWS_ACCESS_MODE > default)
  * ``explicit_endpoints_disabled`` per mode
  * ``merge_kwargs`` returns/skips endpoint_url per mode
"""
from __future__ import annotations

import os
import sys

import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils import aws_access_config
from src.utils.aws_access_config import (
    AWSAccessMode,
    explicit_endpoints_disabled,
    get_access_mode,
    merge_kwargs,
)


_AWS_ENV_VARS = (
    "USE_LOCALSTACK",
    "AWS_ACCESS_MODE",
    "AWS_DISABLE_EXPLICIT_SERVICE_ENDPOINTS",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "AWS_ENDPOINT_URL_DYNAMODB",
    "AWS_ENDPOINT_URL_S3",
    "AWS_ENDPOINT_URL_STS",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Strip AWS-access-related env vars before each test so we get clean precedence."""
    for var in _AWS_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


# ── get_access_mode precedence ──────────────────────────────────────────


def test_default_mode_is_higher_cost(monkeypatch):
    assert get_access_mode() is AWSAccessMode.HIGHER_COST


def test_localstack_takes_precedence_over_aws_access_mode(monkeypatch):
    monkeypatch.setenv("USE_LOCALSTACK", "true")
    monkeypatch.setenv("AWS_ACCESS_MODE", "moderate")
    assert get_access_mode() is AWSAccessMode.LOCALSTACK


@pytest.mark.parametrize("raw,expected", [
    ("higher-cost", AWSAccessMode.HIGHER_COST),
    ("moderate", AWSAccessMode.MODERATE),
    ("lowest-cost", AWSAccessMode.LOWEST_COST),
    ("public-nodes", AWSAccessMode.PUBLIC_NODES),
    ("MODERATE", AWSAccessMode.MODERATE),  # case-insensitive
    ("  lowest-cost  ", AWSAccessMode.LOWEST_COST),  # trimmed
])
def test_aws_access_mode_env_var(monkeypatch, raw, expected):
    monkeypatch.setenv("AWS_ACCESS_MODE", raw)
    assert get_access_mode() is expected


def test_invalid_aws_access_mode_falls_back_to_higher_cost(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_MODE", "garbage")
    assert get_access_mode() is AWSAccessMode.HIGHER_COST


# ── explicit_endpoints_disabled ─────────────────────────────────────────


def test_explicit_endpoints_disabled_false_for_higher_cost():
    assert explicit_endpoints_disabled() is False


@pytest.mark.parametrize("mode", ["moderate", "lowest-cost", "public-nodes"])
def test_explicit_endpoints_disabled_true_for_non_higher_cost(monkeypatch, mode):
    monkeypatch.setenv("AWS_ACCESS_MODE", mode)
    assert explicit_endpoints_disabled() is True


def test_explicit_endpoints_disabled_respects_env_override(monkeypatch):
    # higher-cost mode but ops forced the override on.
    monkeypatch.setenv("AWS_DISABLE_EXPLICIT_SERVICE_ENDPOINTS", "true")
    assert explicit_endpoints_disabled() is True


# ── merge_kwargs ────────────────────────────────────────────────────────


def test_merge_kwargs_sets_region_from_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    out = merge_kwargs("dynamodb", None, {})
    assert out["region_name"] == "eu-west-1"
    assert "endpoint_url" not in out


def test_merge_kwargs_caller_endpoint_url_wins(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_MODE", "moderate")
    out = merge_kwargs("dynamodb", "us-east-1", {"endpoint_url": "https://custom.example/"})
    assert out["endpoint_url"] == "https://custom.example/"


@pytest.mark.parametrize("mode", ["moderate", "lowest-cost", "public-nodes"])
def test_merge_kwargs_skips_endpoint_url_in_public_modes(monkeypatch, mode):
    monkeypatch.setenv("AWS_ACCESS_MODE", mode)
    monkeypatch.setenv("AWS_ENDPOINT_URL_DYNAMODB", "https://override.example/")
    out = merge_kwargs("dynamodb", "us-east-1", {})
    # Per-service override is ignored in public modes — boto3 must hit
    # default public regional hostnames over NAT/IGW.
    assert "endpoint_url" not in out


def test_merge_kwargs_higher_cost_no_default_endpoint_url():
    """higher-cost relies on Private DNS — no explicit endpoint_url needed."""
    out = merge_kwargs("dynamodb", "us-east-1", {})
    assert "endpoint_url" not in out


def test_merge_kwargs_higher_cost_honors_per_service_override(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL_DYNAMODB", "https://override.example/")
    out = merge_kwargs("dynamodb", "us-east-1", {})
    assert out["endpoint_url"] == "https://override.example/"


def test_merge_kwargs_higher_cost_dashed_service(monkeypatch):
    # service name with a dash should map to underscored env key.
    monkeypatch.setenv("AWS_ENDPOINT_URL_COGNITO_IDP", "https://cognito.example/")
    out = merge_kwargs("cognito-idp", "us-east-1", {})
    assert out["endpoint_url"] == "https://cognito.example/"


def test_merge_kwargs_localstack_does_not_inject_endpoint(monkeypatch):
    """LocalStack endpoint resolution lives in AWSClientManager.

    merge_kwargs must not duplicate it — returning kwargs unchanged keeps the
    LocalStack code path the single source of truth.
    """
    monkeypatch.setenv("USE_LOCALSTACK", "true")
    out = merge_kwargs("dynamodb", "us-east-1", {})
    assert "endpoint_url" not in out


def test_merge_kwargs_respects_aws_disable_explicit_endpoints(monkeypatch):
    monkeypatch.setenv("AWS_DISABLE_EXPLICIT_SERVICE_ENDPOINTS", "true")
    monkeypatch.setenv("AWS_ENDPOINT_URL_S3", "https://s3.example/")
    out = merge_kwargs("s3", "us-east-1", {})
    assert "endpoint_url" not in out


def test_merge_kwargs_does_not_mutate_input(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_MODE", "moderate")
    original = {"foo": "bar"}
    out = merge_kwargs("dynamodb", "us-east-1", original)
    assert "region_name" not in original
    assert out["region_name"] == "us-east-1"
    assert out["foo"] == "bar"
