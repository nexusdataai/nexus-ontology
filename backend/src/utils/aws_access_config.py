"""
AWS access mode helper used by AWSClientManager.

The kube-operator injects ``AWS_ACCESS_MODE`` (and optionally
``AWS_DISABLE_EXPLICIT_SERVICE_ENDPOINTS=true``) into the backend pod based on
the cluster's NexusNetworkConfig.spec.awsAccessMode. This module reads that
env var and decides whether boto3 should hit explicit per-service endpoint
URLs (PrivateLink / interface endpoints) or default public regional hostnames
(routed via NAT instance, NAT gateway, or node public IP depending on the
cluster's network profile).

Valid modes:
    higher-cost   - full PrivateLink (default for production EKS clusters)
    moderate      - S3/DDB gateway + NAT instance per AZ
    lowest-cost   - S3/DDB gateway + single NAT instance
    public-nodes  - nodes carry public IPs, no NAT (dev only)
    localstack    - virtual mode for local docker-compose dev (precedence over
                    AWS_ACCESS_MODE when USE_LOCALSTACK=true)
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Any, Dict, Optional


class AWSAccessMode(str, Enum):
    HIGHER_COST = "higher-cost"
    MODERATE = "moderate"
    LOWEST_COST = "lowest-cost"
    PUBLIC_NODES = "public-nodes"
    LOCALSTACK = "localstack"


# Modes where boto3 should NOT add an explicit endpoint_url — traffic flows
# over default public regional hostnames (resolved via NAT or public IP).
_PUBLIC_ENDPOINT_MODES = {
    AWSAccessMode.MODERATE,
    AWSAccessMode.LOWEST_COST,
    AWSAccessMode.PUBLIC_NODES,
}


# Hostname templates for the AWS services this backend talks to. Used only in
# higher-cost mode when boto3 needs an explicit hostname (e.g. when Private
# DNS is not enabled on the interface endpoint).
_REGIONAL_HOSTS: Dict[str, str] = {
    "dynamodb": "dynamodb.{region}.amazonaws.com",
    "s3": "s3.{region}.amazonaws.com",
    "ssm": "ssm.{region}.amazonaws.com",
    "sts": "sts.{region}.amazonaws.com",
    "glue": "glue.{region}.amazonaws.com",
    "ecr": "api.ecr.{region}.amazonaws.com",
    "secretsmanager": "secretsmanager.{region}.amazonaws.com",
    "logs": "logs.{region}.amazonaws.com",
    "cognito-idp": "cognito-idp.{region}.amazonaws.com",
    "athena": "athena.{region}.amazonaws.com",
    "events": "events.{region}.amazonaws.com",
    "eks": "eks.{region}.amazonaws.com",
    "iam": "iam.{region}.amazonaws.com",
    "ec2": "ec2.{region}.amazonaws.com",
}


def _is_localstack_enabled() -> bool:
    return os.environ.get("USE_LOCALSTACK", "").strip().lower() in ("1", "true", "yes")


def get_access_mode() -> AWSAccessMode:
    """Resolve the active AWS access mode using documented precedence.

    Precedence (highest to lowest):
      1. USE_LOCALSTACK=true → LOCALSTACK (development override).
      2. AWS_ACCESS_MODE env var (set by kube-operator from NexusNetworkConfig).
      3. Default → HIGHER_COST (full PrivateLink — safest assumption for
         existing private EKS clusters).
    """
    if _is_localstack_enabled():
        return AWSAccessMode.LOCALSTACK
    raw = (os.environ.get("AWS_ACCESS_MODE") or "").strip().lower()
    for mode in AWSAccessMode:
        if mode.value == raw:
            return mode
    return AWSAccessMode.HIGHER_COST


def explicit_endpoints_disabled() -> bool:
    """Whether boto3 should skip adding an explicit endpoint_url.

    True for moderate / lowest-cost / public-nodes (no PrivateLink) and any
    time the operator/admin sets AWS_DISABLE_EXPLICIT_SERVICE_ENDPOINTS=true.
    LocalStack uses a separate code path and always sets endpoint_url, so
    returns False here.
    """
    if os.environ.get("AWS_DISABLE_EXPLICIT_SERVICE_ENDPOINTS", "").strip().lower() in (
        "1", "true", "yes",
    ):
        return True
    return get_access_mode() in _PUBLIC_ENDPOINT_MODES


def _resolve_region(region_name: Optional[str]) -> str:
    if region_name:
        return region_name
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-east-1"
    )


def _per_service_override(service_name: str) -> Optional[str]:
    """Honor AWS_ENDPOINT_URL_{SERVICE} as an escape hatch.

    Example: AWS_ENDPOINT_URL_DYNAMODB=https://dynamodb.eu-west-1.amazonaws.com
    Lets ops pin one specific service to a different endpoint without changing
    the cluster-wide mode.
    """
    if not service_name:
        return None
    env_key = f"AWS_ENDPOINT_URL_{service_name.upper().replace('-', '_').replace('.', '_')}"
    return os.environ.get(env_key) or None


def merge_kwargs(
    service_name: str,
    region_name: Optional[str],
    kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge mode-aware ``endpoint_url`` + ``region_name`` into boto3 kwargs.

    Behaviour per mode:
      - LOCALSTACK : caller already handled this via LocalStackConfig; this
                     helper returns kwargs unchanged so AWSClientManager's
                     existing LocalStack branch keeps owning it.
      - moderate / lowest-cost / public-nodes : never add endpoint_url
                     (default public hostnames via NAT / public IP).
      - higher-cost: leave endpoint_url unset by default (Private DNS on the
                     interface endpoint resolves the standard regional
                     hostname to a private ENI). Honor explicit
                     AWS_ENDPOINT_URL_{SERVICE} overrides.

    Caller-provided ``endpoint_url`` in ``kwargs`` always wins.
    """
    merged: Dict[str, Any] = dict(kwargs or {})
    region = _resolve_region(merged.get("region_name") or region_name)
    merged.setdefault("region_name", region)

    if merged.get("endpoint_url"):
        return merged

    mode = get_access_mode()
    if mode == AWSAccessMode.LOCALSTACK:
        return merged
    if mode in _PUBLIC_ENDPOINT_MODES:
        return merged
    if explicit_endpoints_disabled():
        # Belt-and-suspenders: respect the env override even if mode parsing
        # somehow produced a higher-cost result.
        return merged

    override = _per_service_override(service_name)
    if override:
        merged["endpoint_url"] = override
    return merged
