"""
Resource naming helpers — mirrors nexus_operator.utils.naming.ResourceNaming.

Pattern: {capability}-{environment}-{purpose}
Example: ontology-local-foundry-workspace  (local K3s)
         ontology-dev-foundry-workspace     (remote K8 dev)
"""
from __future__ import annotations

import os
import re


def sanitize_name(name: str) -> str:
    sanitized = re.sub(r"[^a-z0-9-]", "-", name.lower())
    sanitized = re.sub(r"-+", "-", sanitized)
    return sanitized.strip("-")


def capability_name() -> str:
    return sanitize_name(os.getenv("CAPABILITY_NAME", "call-processing"))


def environment_name() -> str:
    return sanitize_name(os.getenv("ENVIRONMENT", "dev"))


def dynamodb_table_name(purpose: str, *, capability: str | None = None, environment: str | None = None) -> str:
    cap = sanitize_name(capability) if capability else capability_name()
    env = sanitize_name(environment) if environment else environment_name()
    return f"{cap}-{env}-{purpose}"


def glue_database_name(*, capability: str | None = None, environment: str | None = None) -> str:
    cap = sanitize_name(capability) if capability else capability_name()
    env = sanitize_name(environment) if environment else environment_name()
    return f"{cap.replace('-', '_')}_{env.replace('-', '_')}_db"


def s3_bucket_name(
    purpose: str,
    *,
    capability: str | None = None,
    environment: str | None = None,
    account_id: str | None = None,
) -> str:
    cap = sanitize_name(capability) if capability else capability_name()
    env = sanitize_name(environment) if environment else environment_name()
    base = f"{cap}-{env}-{purpose}"
    acct = account_id or os.getenv("LOCAL_AWS_ACCOUNT_ID") or os.getenv("AWS_ACCOUNT_ID")
    return f"{base}-{acct}" if acct else base
