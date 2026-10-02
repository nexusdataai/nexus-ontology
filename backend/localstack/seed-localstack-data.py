#!/usr/bin/env python3
"""
LocalStack Test Data Seeding Script for nexus-backend

Seeds sample data into LocalStack for development and testing:
- Sample transformation journeys
- Sample Second Brain rules
- Sample stage definitions

Usage:
    python localstack/seed-localstack-data.py [OPTIONS]

Options:
    --skip-seed     Skip seeding (useful for clean database testing)
    --endpoint URL  LocalStack endpoint (default: http://localhost:4566)
    --region REGION AWS region (default: us-east-1)
    --table TABLE   DynamoDB table name (default: TransformationSystem)

**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    import boto3
    from botocore.config import Config
except ImportError:
    print("Error: boto3 is required. Install with: pip install boto3")
    sys.exit(1)


def create_dynamodb_client(endpoint: str, region: str):
    """Create DynamoDB client for LocalStack."""
    return boto3.client(
        'dynamodb',
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id='test',
        aws_secret_access_key='test',
        config=Config(retries={'max_attempts': 3})
    )


def create_s3_client(endpoint: str, region: str):
    """Create S3 client for LocalStack."""
    return boto3.client(
        's3',
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id='test',
        aws_secret_access_key='test',
        config=Config(retries={'max_attempts': 3})
    )


def generate_sample_journeys() -> List[Dict[str, Any]]:
    """Generate sample transformation journey data."""
    now = datetime.now(timezone.utc).isoformat()
    
    journeys = [
        {
            "PK": {"S": "JOURNEY#journey-001"},
            "SK": {"S": "METADATA"},
            "GSI1PK": {"S": "TENANT#demo-tenant"},
            "GSI1SK": {"S": f"JOURNEY#{now}"},
            "id": {"S": "journey-001"},
            "name": {"S": "Network Element Classification"},
            "description": {"S": "Classify network elements using AI-powered analysis"},
            "status": {"S": "active"},
            "created_at": {"S": now},
            "updated_at": {"S": now},
            "tenant_id": {"S": "demo-tenant"},
            "stages": {"L": [
                {"S": "data-collection"},
                {"S": "preprocessing"},
                {"S": "classification"},
                {"S": "validation"}
            ]}
        },
        {
            "PK": {"S": "JOURNEY#journey-002"},
            "SK": {"S": "METADATA"},
            "GSI1PK": {"S": "TENANT#demo-tenant"},
            "GSI1SK": {"S": f"JOURNEY#{now}"},
            "id": {"S": "journey-002"},
            "name": {"S": "TMF Mapping Pipeline"},
            "description": {"S": "Map legacy data to TMF Open API standards"},
            "status": {"S": "active"},
            "created_at": {"S": now},
            "updated_at": {"S": now},
            "tenant_id": {"S": "demo-tenant"},
            "stages": {"L": [
                {"S": "extraction"},
                {"S": "transformation"},
                {"S": "mapping"},
                {"S": "export"}
            ]}
        },
        {
            "PK": {"S": "JOURNEY#journey-003"},
            "SK": {"S": "METADATA"},
            "GSI1PK": {"S": "TENANT#demo-tenant"},
            "GSI1SK": {"S": f"JOURNEY#{now}"},
            "id": {"S": "journey-003"},
            "name": {"S": "Alert Processing"},
            "description": {"S": "Process and route network alerts"},
            "status": {"S": "draft"},
            "created_at": {"S": now},
            "updated_at": {"S": now},
            "tenant_id": {"S": "demo-tenant"},
            "stages": {"L": [
                {"S": "ingestion"},
                {"S": "enrichment"},
                {"S": "routing"}
            ]}
        }
    ]
    
    return journeys


def generate_sample_rules() -> List[Dict[str, Any]]:
    """Generate sample Second Brain rules."""
    now = datetime.now(timezone.utc).isoformat()
    
    rules = [
        {
            "PK": {"S": "RULE#rule-001"},
            "SK": {"S": "METADATA"},
            "GSI1PK": {"S": "JOURNEY#journey-001"},
            "GSI1SK": {"S": "RULE#classification"},
            "id": {"S": "rule-001"},
            "name": {"S": "Router Classification"},
            "description": {"S": "Classify network elements as routers based on attributes"},
            "type": {"S": "classification"},
            "condition": {"S": "element.type == 'network_device' AND element.ports > 4"},
            "action": {"S": "classify_as('router')"},
            "priority": {"N": "100"},
            "enabled": {"BOOL": True},
            "created_at": {"S": now},
            "journey_id": {"S": "journey-001"}
        },
        {
            "PK": {"S": "RULE#rule-002"},
            "SK": {"S": "METADATA"},
            "GSI1PK": {"S": "JOURNEY#journey-001"},
            "GSI1SK": {"S": "RULE#classification"},
            "id": {"S": "rule-002"},
            "name": {"S": "Switch Classification"},
            "description": {"S": "Classify network elements as switches"},
            "type": {"S": "classification"},
            "condition": {"S": "element.type == 'network_device' AND element.layer == 2"},
            "action": {"S": "classify_as('switch')"},
            "priority": {"N": "90"},
            "enabled": {"BOOL": True},
            "created_at": {"S": now},
            "journey_id": {"S": "journey-001"}
        },
        {
            "PK": {"S": "RULE#rule-003"},
            "SK": {"S": "METADATA"},
            "GSI1PK": {"S": "JOURNEY#journey-002"},
            "GSI1SK": {"S": "RULE#mapping"},
            "id": {"S": "rule-003"},
            "name": {"S": "TMF Resource Mapping"},
            "description": {"S": "Map legacy resources to TMF Resource model"},
            "type": {"S": "mapping"},
            "condition": {"S": "source.entity_type == 'resource'"},
            "action": {"S": "map_to_tmf('TMF639_Resource')"},
            "priority": {"N": "100"},
            "enabled": {"BOOL": True},
            "created_at": {"S": now},
            "journey_id": {"S": "journey-002"}
        }
    ]
    
    return rules


def generate_sample_stages() -> List[Dict[str, Any]]:
    """Generate sample stage definitions."""
    now = datetime.now(timezone.utc).isoformat()
    
    stages = [
        {
            "PK": {"S": "STAGE#data-collection"},
            "SK": {"S": "DEFINITION"},
            "GSI1PK": {"S": "STAGES"},
            "GSI1SK": {"S": "STAGE#data-collection"},
            "id": {"S": "data-collection"},
            "name": {"S": "Data Collection"},
            "description": {"S": "Collect data from source systems"},
            "order": {"N": "1"},
            "type": {"S": "input"},
            "config": {"M": {
                "timeout_seconds": {"N": "300"},
                "retry_count": {"N": "3"}
            }},
            "created_at": {"S": now}
        },
        {
            "PK": {"S": "STAGE#preprocessing"},
            "SK": {"S": "DEFINITION"},
            "GSI1PK": {"S": "STAGES"},
            "GSI1SK": {"S": "STAGE#preprocessing"},
            "id": {"S": "preprocessing"},
            "name": {"S": "Preprocessing"},
            "description": {"S": "Clean and normalize data"},
            "order": {"N": "2"},
            "type": {"S": "transform"},
            "config": {"M": {
                "normalize": {"BOOL": True},
                "deduplicate": {"BOOL": True}
            }},
            "created_at": {"S": now}
        },
        {
            "PK": {"S": "STAGE#classification"},
            "SK": {"S": "DEFINITION"},
            "GSI1PK": {"S": "STAGES"},
            "GSI1SK": {"S": "STAGE#classification"},
            "id": {"S": "classification"},
            "name": {"S": "Classification"},
            "description": {"S": "Classify elements using AI models"},
            "order": {"N": "3"},
            "type": {"S": "ai"},
            "config": {"M": {
                "model": {"S": "network-classifier-v2"},
                "confidence_threshold": {"N": "0.85"}
            }},
            "created_at": {"S": now}
        },
        {
            "PK": {"S": "STAGE#validation"},
            "SK": {"S": "DEFINITION"},
            "GSI1PK": {"S": "STAGES"},
            "GSI1SK": {"S": "STAGE#validation"},
            "id": {"S": "validation"},
            "name": {"S": "Validation"},
            "description": {"S": "Validate results against rules"},
            "order": {"N": "4"},
            "type": {"S": "validation"},
            "config": {"M": {
                "strict_mode": {"BOOL": False}
            }},
            "created_at": {"S": now}
        }
    ]
    
    return stages


def seed_dynamodb(client, table_name: str, items: List[Dict[str, Any]], item_type: str):
    """Seed items into DynamoDB table."""
    print(f"  Seeding {len(items)} {item_type}...")
    
    for item in items:
        try:
            client.put_item(
                TableName=table_name,
                Item=item,
                ConditionExpression="attribute_not_exists(PK)"
            )
            print(f"    ✓ Created: {item['PK']['S']}")
        except client.exceptions.ConditionalCheckFailedException:
            print(f"    - Exists: {item['PK']['S']}")
        except Exception as e:
            print(f"    ✗ Error: {item['PK']['S']} - {e}")


def seed_s3_sample_files(client, bucket: str):
    """Seed sample files into S3 bucket."""
    print(f"  Seeding sample files to {bucket}...")
    
    sample_files = [
        {
            "key": "samples/network-elements.json",
            "content": json.dumps({
                "elements": [
                    {"id": "ne-001", "type": "router", "name": "Core Router 1"},
                    {"id": "ne-002", "type": "switch", "name": "Access Switch 1"}
                ]
            }, indent=2)
        },
        {
            "key": "samples/config-template.yaml",
            "content": """# Sample Configuration Template
pipeline:
  name: sample-pipeline
  stages:
    - data-collection
    - preprocessing
    - classification
"""
        }
    ]
    
    for file in sample_files:
        try:
            client.put_object(
                Bucket=bucket,
                Key=file["key"],
                Body=file["content"].encode('utf-8'),
                ContentType='application/json' if file["key"].endswith('.json') else 'text/yaml'
            )
            print(f"    ✓ Created: s3://{bucket}/{file['key']}")
        except Exception as e:
            print(f"    ✗ Error: {file['key']} - {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Seed LocalStack with test data for nexus-backend"
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Skip seeding (for clean database testing)"
    )
    parser.add_argument(
        "--endpoint",
        default=os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566"),
        help="LocalStack endpoint URL"
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        help="AWS region"
    )
    parser.add_argument(
        "--table",
        default=os.getenv("DYNAMODB_TABLE_NAME", "TransformationSystem"),
        help="DynamoDB table name"
    )
    
    args = parser.parse_args()
    
    if args.skip_seed:
        print("Skipping seed (--skip-seed flag provided)")
        return 0
    
    print("=" * 50)
    print("  LocalStack Test Data Seeding")
    print("=" * 50)
    print(f"Endpoint: {args.endpoint}")
    print(f"Region:   {args.region}")
    print(f"Table:    {args.table}")
    print("")
    
    # Create clients
    dynamodb = create_dynamodb_client(args.endpoint, args.region)
    s3 = create_s3_client(args.endpoint, args.region)
    
    # Verify table exists
    try:
        dynamodb.describe_table(TableName=args.table)
        print(f"✓ Table '{args.table}' exists")
    except Exception as e:
        print(f"✗ Table '{args.table}' not found. Run initialization first.")
        print(f"  Error: {e}")
        return 1
    
    print("")
    print("Seeding DynamoDB data...")
    
    # Seed journeys
    journeys = generate_sample_journeys()
    seed_dynamodb(dynamodb, args.table, journeys, "journeys")
    
    # Seed rules
    rules = generate_sample_rules()
    seed_dynamodb(dynamodb, args.table, rules, "rules")
    
    # Seed stages
    stages = generate_sample_stages()
    seed_dynamodb(dynamodb, args.table, stages, "stages")
    
    print("")
    print("Seeding S3 sample files...")
    
    # Seed S3 files
    seed_s3_sample_files(s3, "transformation-journey-logs")
    
    print("")
    print("=" * 50)
    print("  Seeding Complete!")
    print("=" * 50)
    print("")
    print("Data seeded:")
    print(f"  - {len(journeys)} transformation journeys")
    print(f"  - {len(rules)} Second Brain rules")
    print(f"  - {len(stages)} stage definitions")
    print(f"  - Sample files in S3")
    print("")
    print("View data in DynamoDB Admin: http://localhost:8001")
    print("")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
