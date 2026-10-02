"""
Test Suite Management REST API

Provides endpoints for triggering test runs via GitHub Actions,
polling run status, and retrieving test report metadata.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import os
import httpx
import boto3
from botocore.exceptions import ClientError

router = APIRouter()

GITHUB_OWNER = "nexusdataai"
GITHUB_REPO = "nexus-backend"
WORKFLOW_FILE = "run-tests.yml"
S3_BUCKET = "ai-engine-test-reports"
S3_PREFIX = "test-reports"
S3_REGION = "us-east-1"
CLOUDFRONT_DOMAIN = "d37vwg02pj6oqg.cloudfront.net"
VALID_TEST_TYPES = {"unit", "integration", "bdd", "endurance"}


def _get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN not configured")
    return token


class RunTestsRequest(BaseModel):
    test_types: List[str] = Field(default=["unit"], description="Test categories to run")
    server_url: str = Field(default="http://localhost:8000", description="Server URL for integration/BDD/endurance tests")


class RunTestsResponse(BaseModel):
    status: str
    message: str
    test_types: List[str]
    workflow_url: str


@router.post("/run")
async def trigger_test_run(request: RunTestsRequest) -> Dict[str, Any]:
    """Trigger a test run via GitHub Actions workflow_dispatch."""
    invalid = set(request.test_types) - VALID_TEST_TYPES
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid test types: {invalid}. Valid: {VALID_TEST_TYPES}")

    token = _get_github_token()
    test_types_str = ",".join(request.test_types)

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "ref": "dev",
        "inputs": {
            "test_types": test_types_str,
            "server_url": request.server_url,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code == 204:
            return {
                "status": "queued",
                "message": f"Test run triggered for: {test_types_str}",
                "test_types": request.test_types,
                "workflow_url": f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}",
            }
        else:
            logger.error(f"GitHub API error {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail=f"GitHub API error: {resp.text}")
    except httpx.RequestError as e:
        logger.error(f"GitHub API request failed: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to reach GitHub API: {str(e)}")


@router.get("/status")
async def get_test_run_status() -> Dict[str, Any]:
    """Get the status of the latest test workflow run."""
    token = _get_github_token()

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/runs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params = {"per_page": 5}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers, params=params)

        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"GitHub API error: {resp.text}")

        data = resp.json()
        runs = data.get("workflow_runs", [])

        if not runs:
            return {"status": "none", "message": "No test runs found", "runs": []}

        formatted_runs = []
        for run in runs[:5]:
            formatted_runs.append({
                "run_id": run["id"],
                "status": run["status"],
                "conclusion": run.get("conclusion"),
                "html_url": run["html_url"],
                "started_at": run.get("run_started_at"),
                "updated_at": run.get("updated_at"),
                "actor": run.get("actor", {}).get("login", "unknown"),
                "display_title": run.get("display_title", ""),
            })

        latest = formatted_runs[0]
        return {
            "status": latest["status"],
            "conclusion": latest["conclusion"],
            "latest_run": latest,
            "recent_runs": formatted_runs,
        }
    except httpx.RequestError as e:
        logger.error(f"GitHub API request failed: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to reach GitHub API: {str(e)}")


@router.get("/results")
async def get_test_results() -> Dict[str, Any]:
    """Get metadata about available test reports from S3."""
    try:
        s3 = boto3.client("s3", region_name=S3_REGION)
        categories = {}

        for category in VALID_TEST_TYPES:
            prefix = f"{S3_PREFIX}/{category}/"
            try:
                resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix, Delimiter="/")
                prefixes = resp.get("CommonPrefixes", [])
                if prefixes:
                    latest_prefix = sorted(prefixes, key=lambda p: p["Prefix"], reverse=True)[0]["Prefix"]
                    timestamp = latest_prefix.rstrip("/").split("/")[-1]
                    categories[category] = {
                        "available": True,
                        "timestamp": timestamp,
                        "report_url": f"https://{CLOUDFRONT_DOMAIN}/{category}/{timestamp}/report.html",
                    }
                else:
                    categories[category] = {"available": False}
            except ClientError:
                categories[category] = {"available": False}

        return {
            "dashboard_url": f"https://{CLOUDFRONT_DOMAIN}/index.html",
            "categories": categories,
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching test results from S3: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch test results: {str(e)}")
