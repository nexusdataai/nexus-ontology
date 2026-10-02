#!/usr/bin/env python3
"""
Call Processing Capability Infrastructure Provisioning Script.

Creates all AWS resources required for the call-processing capability:
- DynamoDB tables
- S3 buckets
- Glue database and tables
- SSM parameters
- Secrets Manager secrets

Usage:
    # Provision all resources (reads from .env.local)
    python provision_infrastructure.py --create-all
    
    # Provision specific resources
    python provision_infrastructure.py --create-dynamodb
    python provision_infrastructure.py --create-s3
    python provision_infrastructure.py --create-glue
    python provision_infrastructure.py --create-ssm
    python provision_infrastructure.py --create-secrets
    
    # Check status
    python provision_infrastructure.py --status
    
    # Delete resources
    python provision_infrastructure.py --delete-all
    
    # Use specific environment
    python provision_infrastructure.py --create-all --env prod
"""

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def load_env_file():
    """Load environment variables from .env.local"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_file = os.path.join(project_root, '.env.local')
    
    if os.path.exists(env_file):
        print(f'📁 Loading environment from: {env_file}')
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = value
        print(f'✅ Environment loaded')
    else:
        print(f'⚠️ No .env.local found at {env_file}')


# Load environment at module import
load_env_file()


# Import boto3 after loading env
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("❌ boto3 is required. Install with: pip install boto3")


# =============================================================================
# CONFIGURATION
# =============================================================================

CAPABILITY_NAME = "call-processing"

# Default values - can be overridden by environment variables
DEFAULT_CONFIG = {
    "AWS_REGION": "us-east-1",
    "ENVIRONMENT": "dev",
    "LOG_LEVEL": "INFO",
    "GATEWAY_PORT": "8000",
    "MIN_WORKERS": "2",
    "MAX_WORKERS": "8",
    "MCP_REQUEST_TIMEOUT": "60.0",
    "WXCC_SIMULATOR_ENABLED": "true",
    "WXCC_SIMULATOR_PREFIX": "wxcc-simulator",
    "WXCC_SIM_ORG_ID": "sim-org-001",
    "GLUE_TABLE_NAME": "wxcc_calls",
    "CLOUDWATCH_LOG_STREAM_PREFIX": "script",
    "ENABLE_CLOUDWATCH_LOGS": "false",
    "COGNITO_REGION": "us-east-1",
}


def get_config_value(key: str, default: str = "") -> str:
    """Get configuration value from environment or defaults."""
    return os.environ.get(key, DEFAULT_CONFIG.get(key, default))


def get_resource_name(env: str, resource: str) -> str:
    """Generate resource name following naming convention: capability-env-name"""
    return f"{CAPABILITY_NAME}-{env}-{resource}"


def get_ssm_path(env: str, category: str, resource: str) -> str:
    """Generate SSM parameter path: /capability/env/category/resource"""
    return f"/{CAPABILITY_NAME}/{env}/{category}/{resource}"


def get_secret_name(env: str, resource: str) -> str:
    """Generate secret name: capability/env/resource"""
    return f"{CAPABILITY_NAME}/{env}/{resource}"


# =============================================================================
# DYNAMODB TABLES
# =============================================================================

def get_dynamodb_table_definitions(env: str) -> List[Dict[str, Any]]:
    """Get DynamoDB table definitions."""
    return [
        # Transformation System Table (main state table)
        {
            "TableName": get_resource_name(env, "transformation-system"),
            "KeySchema": [
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            "BillingMode": "PAY_PER_REQUEST",
            "StreamSpecification": {
                "StreamEnabled": True,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "Tags": [
                {"Key": "Capability", "Value": CAPABILITY_NAME},
                {"Key": "Environment", "Value": env},
                {"Key": "Purpose", "Value": "TransformationJourneys"},
            ],
        },
        # License Table (single table for license records + audit)
        {
            "TableName": get_resource_name(env, "license"),
            "KeySchema": [
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
                {"AttributeName": "holder", "AttributeType": "S"},
                {"AttributeName": "license_id", "AttributeType": "S"},
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "status-index",
                    "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "holder-index",
                    "KeySchema": [{"AttributeName": "holder", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "license-index",
                    "KeySchema": [{"AttributeName": "license_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            "BillingMode": "PAY_PER_REQUEST",
            "Tags": [
                {"Key": "Capability", "Value": CAPABILITY_NAME},
                {"Key": "Environment", "Value": env},
                {"Key": "Purpose", "Value": "LicenseManagement"},
            ],
        },
        # WXCC Task Tracking Table
        {
            "TableName": get_resource_name(env, "wxcc-task-tracking"),
            "KeySchema": [{"AttributeName": "task_id", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "task_id", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "status-index",
                    "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            "BillingMode": "PAY_PER_REQUEST",
            "TimeToLiveSpecification": {
                "Enabled": True,
                "AttributeName": "expires_at",
            },
            "Tags": [
                {"Key": "Capability", "Value": CAPABILITY_NAME},
                {"Key": "Environment", "Value": env},
                {"Key": "Purpose", "Value": "WXCCTaskTracking"},
            ],
        },
    ]


def create_dynamodb_tables(env: str, region: str) -> bool:
    """Create all DynamoDB tables."""
    print(f"\n🗄️  Creating DynamoDB tables in {region}...")
    
    dynamodb = boto3.client("dynamodb", region_name=region)
    tables = get_dynamodb_table_definitions(env)
    success_count = 0
    
    for table_def in tables:
        table_name = table_def["TableName"]
        print(f"\n   📋 Creating table: {table_name}")
        
        try:
            # Check if table exists
            try:
                dynamodb.describe_table(TableName=table_name)
                print(f"   ✅ Table already exists: {table_name}")
                success_count += 1
                continue
            except dynamodb.exceptions.ResourceNotFoundException:
                pass
            
            # Remove TTL from create params (set separately)
            ttl_spec = table_def.pop("TimeToLiveSpecification", None)
            
            # Create table
            dynamodb.create_table(**table_def)
            print(f"   ⏳ Table creation initiated: {table_name}")
            
            # Wait for table to be active
            waiter = dynamodb.get_waiter("table_exists")
            waiter.wait(TableName=table_name)
            print(f"   ✅ Table is active: {table_name}")
            
            # Enable TTL if specified
            if ttl_spec and ttl_spec.get("Enabled"):
                dynamodb.update_time_to_live(
                    TableName=table_name,
                    TimeToLiveSpecification=ttl_spec
                )
                print(f"   ✅ TTL enabled on: {table_name}")
            
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to create table {table_name}: {e}")
    
    print(f"\n   📊 Created {success_count}/{len(tables)} tables")
    return success_count == len(tables)


# =============================================================================
# S3 BUCKETS
# =============================================================================

def get_s3_bucket_definitions(env: str) -> List[Dict[str, Any]]:
    """Get S3 bucket definitions."""
    return [
        {
            "name": get_resource_name(env, "call-data"),
            "purpose": "Processed call data for Glue tables",
            "cors": True,
        },
        {
            "name": get_resource_name(env, "wxcc-simulator"),
            "purpose": "WXCC simulator data and recordings",
            "cors": True,
        },
        {
            "name": get_resource_name(env, "journey-logs"),
            "purpose": "Journey execution logs",
            "cors": False,
        },
        {
            "name": get_resource_name(env, "journey-reports"),
            "purpose": "Journey reports and artifacts",
            "cors": False,
        },
    ]


def create_s3_buckets(env: str, region: str) -> bool:
    """Create all S3 buckets."""
    print(f"\n🪣 Creating S3 buckets in {region}...")
    
    s3 = boto3.client("s3", region_name=region)
    buckets = get_s3_bucket_definitions(env)
    success_count = 0
    
    for bucket_def in buckets:
        bucket_name = bucket_def["name"]
        print(f"\n   📦 Creating bucket: {bucket_name}")
        
        try:
            # Check if bucket exists
            try:
                s3.head_bucket(Bucket=bucket_name)
                print(f"   ✅ Bucket already exists: {bucket_name}")
                success_count += 1
                continue
            except ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    raise
            
            # Create bucket
            create_params = {"Bucket": bucket_name}
            if region != "us-east-1":
                create_params["CreateBucketConfiguration"] = {
                    "LocationConstraint": region
                }
            
            s3.create_bucket(**create_params)
            print(f"   ✅ Bucket created: {bucket_name}")
            
            # Block public access
            s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                },
            )
            print(f"   ✅ Public access blocked")
            
            # Enable versioning
            s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={"Status": "Enabled"},
            )
            print(f"   ✅ Versioning enabled")
            
            # Add CORS if needed
            if bucket_def.get("cors"):
                s3.put_bucket_cors(
                    Bucket=bucket_name,
                    CORSConfiguration={
                        "CORSRules": [
                            {
                                "AllowedHeaders": ["*"],
                                "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
                                "AllowedOrigins": ["*"],
                                "MaxAgeSeconds": 3600,
                            }
                        ]
                    },
                )
                print(f"   ✅ CORS enabled")
            
            # Add tags
            s3.put_bucket_tagging(
                Bucket=bucket_name,
                Tagging={
                    "TagSet": [
                        {"Key": "Capability", "Value": CAPABILITY_NAME},
                        {"Key": "Environment", "Value": env},
                        {"Key": "Purpose", "Value": bucket_def["purpose"]},
                    ]
                },
            )
            
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to create bucket {bucket_name}: {e}")
    
    print(f"\n   📊 Created {success_count}/{len(buckets)} buckets")
    return success_count == len(buckets)


# =============================================================================
# AWS GLUE
# =============================================================================

def create_glue_resources(env: str, region: str) -> bool:
    """Create Glue database and tables."""
    print(f"\n📚 Creating Glue resources in {region}...")
    
    glue = boto3.client("glue", region_name=region)
    
    # Database name
    db_name = f"{CAPABILITY_NAME.replace('-', '_')}_{env}_wxcc_calls_db"
    table_name = "wxcc_calls"
    bucket_name = get_resource_name(env, "call-data")
    
    # Create database
    print(f"\n   📂 Creating Glue database: {db_name}")
    try:
        glue.get_database(Name=db_name)
        print(f"   ✅ Database already exists: {db_name}")
    except glue.exceptions.EntityNotFoundException:
        try:
            glue.create_database(
                DatabaseInput={
                    "Name": db_name,
                    "Description": f"WXCC Call Data Database for {CAPABILITY_NAME} {env}",
                    "Parameters": {"classification": "json"},
                }
            )
            print(f"   ✅ Database created: {db_name}")
        except Exception as e:
            print(f"   ❌ Failed to create database: {e}")
            return False
    
    # Create table
    print(f"\n   📋 Creating Glue table: {table_name}")
    try:
        glue.get_table(DatabaseName=db_name, Name=table_name)
        print(f"   ✅ Table already exists: {table_name}")
    except glue.exceptions.EntityNotFoundException:
        try:
            glue.create_table(
                DatabaseName=db_name,
                TableInput={
                    "Name": table_name,
                    "Description": "Webex Contact Center Call Records",
                    "TableType": "EXTERNAL_TABLE",
                    "Parameters": {
                        "classification": "json",
                        "EXTERNAL": "TRUE",
                        "json.serialization.format": "1",
                    },
                    "StorageDescriptor": {
                        "Columns": [
                            {"Name": "task_id", "Type": "string", "Comment": "Unique task identifier"},
                            {"Name": "org_id", "Type": "string", "Comment": "Organization ID"},
                            {"Name": "created_at", "Type": "bigint", "Comment": "Call creation timestamp"},
                            {"Name": "status", "Type": "string", "Comment": "Call status"},
                            {"Name": "direction", "Type": "string", "Comment": "Call direction"},
                            {"Name": "origin_phone", "Type": "string", "Comment": "Caller phone number"},
                            {"Name": "destination_phone", "Type": "string", "Comment": "Destination phone"},
                            {"Name": "queue_name", "Type": "string", "Comment": "Queue name"},
                            {"Name": "queue_id", "Type": "string", "Comment": "Queue ID"},
                            {"Name": "agent_name", "Type": "string", "Comment": "Agent name"},
                            {"Name": "agent_id", "Type": "string", "Comment": "Agent ID"},
                            {"Name": "duration_seconds", "Type": "int", "Comment": "Call duration"},
                            {"Name": "recording_file", "Type": "string", "Comment": "S3 path to recording"},
                            {"Name": "transcript_file", "Type": "string", "Comment": "S3 path to transcript"},
                            {"Name": "transcript_text", "Type": "string", "Comment": "Full transcript text"},
                            {"Name": "sentiment", "Type": "string", "Comment": "Sentiment analysis result"},
                            {"Name": "summary", "Type": "string", "Comment": "Call summary"},
                        ],
                        "Location": f"s3://{bucket_name}/wxcc-data/",
                        "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                        "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                        "SerdeInfo": {
                            "SerializationLibrary": "org.openx.data.jsonserde.JsonSerDe",
                            "Parameters": {
                                "serialization.format": "1",
                                "ignore.malformed.json": "true",
                                "case.insensitive": "true",
                            },
                        },
                        "Compressed": False,
                    },
                    "PartitionKeys": [
                        {"Name": "year", "Type": "string", "Comment": "Year partition"},
                        {"Name": "month", "Type": "string", "Comment": "Month partition"},
                        {"Name": "day", "Type": "string", "Comment": "Day partition"},
                        {"Name": "hour", "Type": "string", "Comment": "Hour partition"},
                    ],
                },
            )
            print(f"   ✅ Table created: {table_name}")
        except Exception as e:
            print(f"   ❌ Failed to create table: {e}")
            return False
    
    print(f"\n   📊 Glue resources created successfully")
    return True


# =============================================================================
# SSM PARAMETERS
# =============================================================================

def get_ssm_parameters(env: str, region: str) -> List[Dict[str, str]]:
    """Get SSM parameter definitions."""
    return [
        # AWS Configuration
        {"path": get_ssm_path(env, "aws", "region"), "value": region},
        
        # Server Configuration
        {"path": get_ssm_path(env, "server", "environment"), "value": env},
        {"path": get_ssm_path(env, "server", "log-level"), "value": get_config_value("LOG_LEVEL")},
        {"path": get_ssm_path(env, "server", "port"), "value": get_config_value("GATEWAY_PORT")},
        {"path": get_ssm_path(env, "server", "min-workers"), "value": get_config_value("MIN_WORKERS")},
        {"path": get_ssm_path(env, "server", "max-workers"), "value": get_config_value("MAX_WORKERS")},
        {"path": get_ssm_path(env, "server", "timeout"), "value": get_config_value("MCP_REQUEST_TIMEOUT")},
        
        # WXCC Configuration
        {"path": get_ssm_path(env, "wxcc", "enabled"), "value": get_config_value("WXCC_SIMULATOR_ENABLED")},
        {"path": get_ssm_path(env, "wxcc", "bucket"), "value": get_resource_name(env, "wxcc-simulator")},
        {"path": get_ssm_path(env, "wxcc", "prefix"), "value": get_config_value("WXCC_SIMULATOR_PREFIX")},
        {"path": get_ssm_path(env, "wxcc", "org-id"), "value": get_config_value("WXCC_SIM_ORG_ID")},
        
        # S3 Buckets
        {"path": get_ssm_path(env, "s3", "recordings-bucket"), "value": get_resource_name(env, "call-data")},
        {"path": get_ssm_path(env, "s3", "journey-logs-bucket"), "value": get_resource_name(env, "journey-logs")},
        {"path": get_ssm_path(env, "s3", "journey-reports-bucket"), "value": get_resource_name(env, "journey-reports")},
        
        # DynamoDB Tables
        {"path": get_ssm_path(env, "dynamodb", "transformation-table"), "value": get_resource_name(env, "transformation-system")},
        {"path": get_ssm_path(env, "dynamodb", "license-table"), "value": get_resource_name(env, "license")},
        {"path": get_ssm_path(env, "dynamodb", "wxcc-task-table"), "value": get_resource_name(env, "wxcc-task-tracking")},
        
        # Glue Configuration
        {"path": get_ssm_path(env, "glue", "database"), "value": f"{CAPABILITY_NAME.replace('-', '_')}_{env}_wxcc_calls_db"},
        {"path": get_ssm_path(env, "glue", "table"), "value": get_config_value("GLUE_TABLE_NAME")},
        
        # CloudWatch Configuration
        {"path": get_ssm_path(env, "cloudwatch", "log-group"), "value": f"/aws/{CAPABILITY_NAME}/{env}"},
        {"path": get_ssm_path(env, "cloudwatch", "stream-prefix"), "value": get_config_value("CLOUDWATCH_LOG_STREAM_PREFIX")},
        
        # Cognito Configuration (placeholders)
        {"path": get_ssm_path(env, "cognito", "region"), "value": get_config_value("COGNITO_REGION")},
        {"path": get_ssm_path(env, "cognito", "user-pool-id"), "value": os.environ.get("COGNITO_USER_POOL_ID", "PLACEHOLDER")},
        {"path": get_ssm_path(env, "cognito", "app-client-id"), "value": os.environ.get("COGNITO_APP_CLIENT_ID", "PLACEHOLDER")},
    ]


def create_ssm_parameters(env: str, region: str) -> bool:
    """Create all SSM parameters."""
    print(f"\n🔧 Creating SSM parameters in {region}...")
    
    ssm = boto3.client("ssm", region_name=region)
    parameters = get_ssm_parameters(env, region)
    success_count = 0
    
    tags = [
        {"Key": "Capability", "Value": CAPABILITY_NAME},
        {"Key": "Environment", "Value": env},
    ]
    
    for param in parameters:
        path = param["path"]
        value = param["value"]
        
        try:
            # First, try to create new parameter with tags
            try:
                ssm.put_parameter(
                    Name=path,
                    Value=value,
                    Type="String",
                    Tags=tags,
                )
                print(f"   ✅ Created: {path} = {value[:50]}{'...' if len(value) > 50 else ''}")
                success_count += 1
            except ssm.exceptions.ParameterAlreadyExists:
                # Parameter exists, update without tags (can't use both)
                ssm.put_parameter(
                    Name=path,
                    Value=value,
                    Type="String",
                    Overwrite=True,
                )
                print(f"   ✅ Updated: {path} = {value[:50]}{'...' if len(value) > 50 else ''}")
                success_count += 1
        except Exception as e:
            print(f"   ❌ Failed to create {path}: {e}")
    
    print(f"\n   📊 Created {success_count}/{len(parameters)} parameters")
    return success_count == len(parameters)


# =============================================================================
# SECRETS MANAGER
# =============================================================================

def get_secrets_definitions(env: str) -> List[Dict[str, Any]]:
    """Get Secrets Manager secret definitions."""
    return [
        {
            "name": get_secret_name(env, "api-keys"),
            "description": "API keys for the gateway",
            "secret": {
                "API_KEY": os.environ.get("API_KEY", "super-secret-change-me"),
            },
        },
        {
            "name": get_secret_name(env, "wxcc"),
            "description": "WXCC simulator and API tokens",
            "secret": {
                "WXCC_SIM_TOKEN": os.environ.get("WXCC_SIM_TOKEN", "test-token-12345"),
            },
        },
        {
            "name": get_secret_name(env, "openai"),
            "description": "OpenAI API keys for transcription",
            "secret": {
                "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "PLACEHOLDER"),
            },
        },
        {
            "name": get_secret_name(env, "license"),
            "description": "License signing/verification keys",
            "secret": {
                "LICENSE_PUBLIC_KEY": os.environ.get("LICENSE_PUBLIC_KEY", "PLACEHOLDER"),
                "LICENSE_PRIVATE_KEY": os.environ.get("LICENSE_PRIVATE_KEY", "PLACEHOLDER"),
            },
        },
        {
            "name": get_secret_name(env, "anthropic"),
            "description": "Anthropic/Claude API keys (optional)",
            "secret": {
                "CLAUDE_API_KEY": os.environ.get("CLAUDE_API_KEY", "PLACEHOLDER"),
                "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "PLACEHOLDER"),
            },
        },
        {
            "name": get_secret_name(env, "github"),
            "description": "GitHub tokens (optional)",
            "secret": {
                "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", "PLACEHOLDER"),
            },
        },
    ]


def create_secrets(env: str, region: str) -> bool:
    """Create all Secrets Manager secrets."""
    print(f"\n🔐 Creating Secrets Manager secrets in {region}...")
    
    secrets = boto3.client("secretsmanager", region_name=region)
    secret_defs = get_secrets_definitions(env)
    success_count = 0
    
    for secret_def in secret_defs:
        name = secret_def["name"]
        description = secret_def["description"]
        secret_value = json.dumps(secret_def["secret"])
        
        try:
            # Try to create new secret
            secrets.create_secret(
                Name=name,
                Description=description,
                SecretString=secret_value,
                Tags=[
                    {"Key": "Capability", "Value": CAPABILITY_NAME},
                    {"Key": "Environment", "Value": env},
                ],
            )
            print(f"   ✅ Created: {name}")
            success_count += 1
        except secrets.exceptions.ResourceExistsException:
            # Update existing secret
            try:
                secrets.put_secret_value(SecretId=name, SecretString=secret_value)
                print(f"   ✅ Updated: {name}")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Failed to update {name}: {e}")
        except Exception as e:
            print(f"   ❌ Failed to create {name}: {e}")
    
    print(f"\n   📊 Created/Updated {success_count}/{len(secret_defs)} secrets")
    return success_count == len(secret_defs)


# =============================================================================
# CLOUDWATCH LOG GROUPS
# =============================================================================

def create_cloudwatch_log_groups(env: str, region: str) -> bool:
    """Create CloudWatch log groups."""
    print(f"\n📝 Creating CloudWatch log groups in {region}...")
    
    logs = boto3.client("logs", region_name=region)
    
    log_groups = [
        f"/ecs/{CAPABILITY_NAME}-{env}",
        f"/aws/application/{CAPABILITY_NAME}-{env}",
        f"/aws/{CAPABILITY_NAME}/{env}",
    ]
    
    success_count = 0
    
    for log_group in log_groups:
        try:
            logs.create_log_group(
                logGroupName=log_group,
                tags={
                    "Capability": CAPABILITY_NAME,
                    "Environment": env,
                },
            )
            print(f"   ✅ Created: {log_group}")
            
            # Set retention
            logs.put_retention_policy(
                logGroupName=log_group,
                retentionInDays=30 if env != "prod" else 90,
            )
            success_count += 1
        except logs.exceptions.ResourceAlreadyExistsException:
            print(f"   ✅ Already exists: {log_group}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ Failed to create {log_group}: {e}")
    
    print(f"\n   📊 Created {success_count}/{len(log_groups)} log groups")
    return success_count == len(log_groups)


# =============================================================================
# STATUS CHECK
# =============================================================================

def check_status(env: str, region: str):
    """Check the status of all resources."""
    print(f"\n📊 Checking infrastructure status for {CAPABILITY_NAME}-{env} in {region}...")
    
    # DynamoDB
    print(f"\n🗄️  DynamoDB Tables:")
    dynamodb = boto3.client("dynamodb", region_name=region)
    for table_def in get_dynamodb_table_definitions(env):
        table_name = table_def["TableName"]
        try:
            response = dynamodb.describe_table(TableName=table_name)
            status = response["Table"]["TableStatus"]
            print(f"   ✅ {table_name}: {status}")
        except dynamodb.exceptions.ResourceNotFoundException:
            print(f"   ❌ {table_name}: NOT FOUND")
        except Exception as e:
            print(f"   ⚠️  {table_name}: Error - {e}")
    
    # S3 Buckets
    print(f"\n🪣 S3 Buckets:")
    s3 = boto3.client("s3", region_name=region)
    for bucket_def in get_s3_bucket_definitions(env):
        bucket_name = bucket_def["name"]
        try:
            s3.head_bucket(Bucket=bucket_name)
            print(f"   ✅ {bucket_name}: EXISTS")
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                print(f"   ❌ {bucket_name}: NOT FOUND")
            else:
                print(f"   ⚠️  {bucket_name}: {e.response['Error']['Code']}")
        except Exception as e:
            print(f"   ⚠️  {bucket_name}: Error - {e}")
    
    # Glue
    print(f"\n📚 Glue Resources:")
    glue = boto3.client("glue", region_name=region)
    db_name = f"{CAPABILITY_NAME.replace('-', '_')}_{env}_wxcc_calls_db"
    try:
        glue.get_database(Name=db_name)
        print(f"   ✅ Database {db_name}: EXISTS")
        try:
            glue.get_table(DatabaseName=db_name, Name="wxcc_calls")
            print(f"   ✅ Table wxcc_calls: EXISTS")
        except glue.exceptions.EntityNotFoundException:
            print(f"   ❌ Table wxcc_calls: NOT FOUND")
    except glue.exceptions.EntityNotFoundException:
        print(f"   ❌ Database {db_name}: NOT FOUND")
    except Exception as e:
        print(f"   ⚠️  Glue: Error - {e}")
    
    # SSM Parameters
    print(f"\n🔧 SSM Parameters:")
    ssm = boto3.client("ssm", region_name=region)
    prefix = f"/{CAPABILITY_NAME}/{env}/"
    try:
        paginator = ssm.get_paginator("get_parameters_by_path")
        count = 0
        for page in paginator.paginate(Path=prefix, Recursive=True):
            count += len(page.get("Parameters", []))
        print(f"   ✅ Found {count} parameters under {prefix}")
    except Exception as e:
        print(f"   ⚠️  SSM: Error - {e}")
    
    # Secrets
    print(f"\n🔐 Secrets Manager:")
    secrets = boto3.client("secretsmanager", region_name=region)
    for secret_def in get_secrets_definitions(env):
        name = secret_def["name"]
        try:
            secrets.describe_secret(SecretId=name)
            print(f"   ✅ {name}: EXISTS")
        except secrets.exceptions.ResourceNotFoundException:
            print(f"   ❌ {name}: NOT FOUND")
        except Exception as e:
            print(f"   ⚠️  {name}: Error - {e}")


# =============================================================================
# DELETION
# =============================================================================

def delete_all_resources(env: str, region: str, confirm: bool = False):
    """Delete all resources (use with caution)."""
    if not confirm:
        response = input(f"\n⚠️  This will DELETE all {CAPABILITY_NAME}-{env} resources. Type 'DELETE' to confirm: ")
        if response != "DELETE":
            print("Cancelled.")
            return
    
    print(f"\n🗑️  Deleting all resources for {CAPABILITY_NAME}-{env} in {region}...")
    
    # Delete SSM Parameters
    print(f"\n🔧 Deleting SSM parameters...")
    ssm = boto3.client("ssm", region_name=region)
    prefix = f"/{CAPABILITY_NAME}/{env}/"
    try:
        paginator = ssm.get_paginator("get_parameters_by_path")
        for page in paginator.paginate(Path=prefix, Recursive=True):
            for param in page.get("Parameters", []):
                ssm.delete_parameter(Name=param["Name"])
                print(f"   ✅ Deleted: {param['Name']}")
    except Exception as e:
        print(f"   ⚠️  Error deleting SSM parameters: {e}")
    
    # Delete Secrets
    print(f"\n🔐 Deleting secrets...")
    secrets = boto3.client("secretsmanager", region_name=region)
    for secret_def in get_secrets_definitions(env):
        name = secret_def["name"]
        try:
            secrets.delete_secret(SecretId=name, ForceDeleteWithoutRecovery=True)
            print(f"   ✅ Deleted: {name}")
        except secrets.exceptions.ResourceNotFoundException:
            pass
        except Exception as e:
            print(f"   ⚠️  Error deleting {name}: {e}")
    
    # Delete DynamoDB Tables
    print(f"\n🗄️  Deleting DynamoDB tables...")
    dynamodb = boto3.client("dynamodb", region_name=region)
    for table_def in get_dynamodb_table_definitions(env):
        table_name = table_def["TableName"]
        try:
            dynamodb.delete_table(TableName=table_name)
            print(f"   ✅ Deleted: {table_name}")
        except dynamodb.exceptions.ResourceNotFoundException:
            pass
        except Exception as e:
            print(f"   ⚠️  Error deleting {table_name}: {e}")
    
    # Delete Glue table and database
    print(f"\n📚 Deleting Glue resources...")
    glue = boto3.client("glue", region_name=region)
    db_name = f"{CAPABILITY_NAME.replace('-', '_')}_{env}_wxcc_calls_db"
    try:
        glue.delete_table(DatabaseName=db_name, Name="wxcc_calls")
        print(f"   ✅ Deleted table: wxcc_calls")
    except:
        pass
    try:
        glue.delete_database(Name=db_name)
        print(f"   ✅ Deleted database: {db_name}")
    except:
        pass
    
    # Note: S3 buckets are NOT deleted (they may contain important data)
    print(f"\n⚠️  S3 buckets were NOT deleted (may contain data). Delete manually if needed:")
    for bucket_def in get_s3_bucket_definitions(env):
        print(f"   - {bucket_def['name']}")
    
    print(f"\n✅ Resource deletion complete")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Provision Call Processing Infrastructure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Actions
    parser.add_argument("--create-all", action="store_true", help="Create all resources")
    parser.add_argument("--create-dynamodb", action="store_true", help="Create DynamoDB tables only")
    parser.add_argument("--create-s3", action="store_true", help="Create S3 buckets only")
    parser.add_argument("--create-glue", action="store_true", help="Create Glue resources only")
    parser.add_argument("--create-ssm", action="store_true", help="Create SSM parameters only")
    parser.add_argument("--create-secrets", action="store_true", help="Create Secrets Manager secrets only")
    parser.add_argument("--create-logs", action="store_true", help="Create CloudWatch log groups only")
    parser.add_argument("--status", action="store_true", help="Check resource status")
    parser.add_argument("--delete-all", action="store_true", help="Delete all resources (DANGEROUS)")
    
    # Configuration
    parser.add_argument("--env", type=str, default=None, help="Environment (dev/stage/test/prod)")
    parser.add_argument("--region", type=str, default=None, help="AWS region")
    
    args = parser.parse_args()
    
    if not BOTO3_AVAILABLE:
        print("❌ boto3 is required. Install with: pip install boto3")
        sys.exit(1)
    
    # Get configuration
    env = args.env or get_config_value("ENVIRONMENT", "dev")
    region = args.region or get_config_value("AWS_REGION", "us-east-1")
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║         Call Processing Infrastructure Provisioning                  ║
╚══════════════════════════════════════════════════════════════════════╝

   Capability: {CAPABILITY_NAME}
   Environment: {env}
   Region: {region}
""")
    
    # Execute action
    if args.create_all:
        success = True
        success = create_dynamodb_tables(env, region) and success
        success = create_s3_buckets(env, region) and success
        success = create_glue_resources(env, region) and success
        success = create_ssm_parameters(env, region) and success
        success = create_secrets(env, region) and success
        success = create_cloudwatch_log_groups(env, region) and success
        
        if success:
            print(f"\n🎉 All infrastructure provisioned successfully!")
        else:
            print(f"\n⚠️  Some resources failed to provision. Check errors above.")
            sys.exit(1)
    
    elif args.create_dynamodb:
        create_dynamodb_tables(env, region)
    elif args.create_s3:
        create_s3_buckets(env, region)
    elif args.create_glue:
        create_glue_resources(env, region)
    elif args.create_ssm:
        create_ssm_parameters(env, region)
    elif args.create_secrets:
        create_secrets(env, region)
    elif args.create_logs:
        create_cloudwatch_log_groups(env, region)
    elif args.status:
        check_status(env, region)
    elif args.delete_all:
        delete_all_resources(env, region)
    else:
        # Default: show status
        check_status(env, region)
        print("\n💡 Use --create-all to provision all infrastructure")
        print("   Use --help for more options")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

