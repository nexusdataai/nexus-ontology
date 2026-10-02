#!/usr/bin/env python3
"""
DynamoDB Table Setup Script for License Management

Creates the required DynamoDB tables for license records and audit logs.
Includes GSI for querying by status and holder_id.
"""

import boto3
import os
import sys
from botocore.exceptions import ClientError

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from license.consts import LICENSE_TABLE_NAME, LICENSE_AUDIT_TABLE_NAME


def get_dynamodb_client():
    """Get DynamoDB client with optional local endpoint."""
    endpoint_url = os.environ.get('DYNAMODB_ENDPOINT_URL')
    region = os.environ.get('AWS_REGION', 'us-east-1')
    
    if endpoint_url:
        return boto3.client('dynamodb', endpoint_url=endpoint_url, region_name=region)
    return boto3.client('dynamodb', region_name=region)


def create_license_table(client):
    """
    Create the license records table.
    
    Schema:
    - PK: INSTANCE#<instance_id>
    - SK: LICENSE#<license_id>
    
    GSIs:
    - status-index: Query by license status
    - holder-index: Query by holder_id
    """
    table_name = LICENSE_TABLE_NAME
    
    try:
        response = client.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'holder_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'status-index',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
                        {'AttributeName': 'SK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5,
                    },
                },
                {
                    'IndexName': 'holder-index',
                    'KeySchema': [
                        {'AttributeName': 'holder_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'SK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5,
                    },
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5,
            },
            Tags=[
                {'Key': 'Application', 'Value': 'AI-Job-Engine'},
                {'Key': 'Component', 'Value': 'License'},
            ],
        )
        print(f"Created table: {table_name}")
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"Table {table_name} already exists")
        else:
            raise


def create_audit_table(client):
    """
    Create the license audit logs table.
    
    Schema:
    - PK: AUDIT#<year-month>
    - SK: <timestamp>#<event_id>
    
    GSIs:
    - license-index: Query audit logs by license_id
    """
    table_name = LICENSE_AUDIT_TABLE_NAME
    
    try:
        response = client.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'license_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'license-index',
                    'KeySchema': [
                        {'AttributeName': 'license_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'SK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5,
                    },
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5,
            },
            Tags=[
                {'Key': 'Application', 'Value': 'AI-Job-Engine'},
                {'Key': 'Component', 'Value': 'License-Audit'},
            ],
        )
        print(f"Created table: {table_name}")
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"Table {table_name} already exists")
        else:
            raise


def wait_for_tables(client):
    """Wait for tables to become active."""
    waiter = client.get_waiter('table_exists')
    
    for table_name in [LICENSE_TABLE_NAME, LICENSE_AUDIT_TABLE_NAME]:
        try:
            print(f"Waiting for {table_name} to become active...")
            waiter.wait(TableName=table_name)
            print(f"Table {table_name} is active")
        except Exception as e:
            print(f"Error waiting for {table_name}: {e}")


def delete_tables(client):
    """Delete license tables (for cleanup/testing)."""
    for table_name in [LICENSE_TABLE_NAME, LICENSE_AUDIT_TABLE_NAME]:
        try:
            client.delete_table(TableName=table_name)
            print(f"Deleted table: {table_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Table {table_name} does not exist")
            else:
                raise


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup DynamoDB tables for license management')
    parser.add_argument('--delete', action='store_true', help='Delete tables instead of creating')
    parser.add_argument('--wait', action='store_true', help='Wait for tables to become active')
    args = parser.parse_args()
    
    client = get_dynamodb_client()
    
    if args.delete:
        delete_tables(client)
    else:
        create_license_table(client)
        create_audit_table(client)
        
        if args.wait:
            wait_for_tables(client)
    
    print("Done!")


if __name__ == '__main__':
    main()
