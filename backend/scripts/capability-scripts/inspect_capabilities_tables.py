#!/usr/bin/env python3
"""
Inspect DynamoDB Capability System Tables
==========================================
This script inspects and displays the contents of capability-related DynamoDB tables.

Tables inspected:
1. BusinessCapabilitySystem
2. CapabilityComponents
3. ImplementationJobs
4. PerformanceMetrics

Usage:
    python3 inspect_capabilities_tables.py                    # Inspect all tables
    python3 inspect_capabilities_tables.py --table BusinessCapabilitySystem  # Inspect specific table
    python3 inspect_capabilities_tables.py --capability CAP-001  # Show specific capability
    python3 inspect_capabilities_tables.py --limit 10         # Limit results
    python3 inspect_capabilities_tables.py --export output.json  # Export to file
"""

import boto3
import sys
import os
import json
import argparse
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def print_with_flush(message):
    """Print message and flush stdout immediately"""
    print(message)
    sys.stdout.flush()


def decimal_default(obj):
    """JSON encoder for Decimal types"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def format_item_display(item: Dict[str, Any]) -> str:
    """Format a single item for display"""
    lines = []
    
    # Extract key identifiers
    pk = item.get('PK', 'N/A')
    sk = item.get('SK', 'N/A')
    
    lines.append(f"  PK: {pk}")
    lines.append(f"  SK: {sk}")
    
    # Display other important fields
    important_fields = ['capabilityId', 'name', 'status', 'type', 'priority', 
                       'businessDomain', 'owner', 'componentId', 'jobId', 'metricName']
    
    for field in important_fields:
        if field in item:
            lines.append(f"  {field}: {item[field]}")
    
    # Show timestamps if available
    if 'createdAt' in item:
        lines.append(f"  Created: {item['createdAt']}")
    if 'updatedAt' in item:
        lines.append(f"  Updated: {item['updatedAt']}")
    
    return '\n'.join(lines)


def get_dynamodb_resource():
    """Get DynamoDB resource with proper authentication"""
    try:
        from src.utils.aws_client_utils import create_aws_resource
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Using role ARN: {role_arn}')
            return create_aws_resource('dynamodb', role_arn=role_arn)
        else:
            print_with_flush('🔑 Using default credential chain')
            return boto3.resource('dynamodb')
    except ImportError:
        print_with_flush('⚠️  AWS utilities not found, using boto3 directly')
        return boto3.resource('dynamodb')


def get_table_info(table):
    """Get basic information about a table"""
    try:
        response = table.meta.client.describe_table(TableName=table.table_name)
        table_desc = response['Table']
        
        info = {
            'name': table_desc['TableName'],
            'status': table_desc['TableStatus'],
            'item_count': table_desc.get('ItemCount', 0),
            'size_bytes': table_desc.get('TableSizeBytes', 0),
            'created': table_desc.get('CreationDateTime', 'N/A'),
        }
        
        # Get index information
        info['indexes'] = []
        for gsi in table_desc.get('GlobalSecondaryIndexes', []):
            info['indexes'].append({
                'name': gsi['IndexName'],
                'status': gsi.get('IndexStatus', 'N/A')
            })
        
        return info
    except Exception as e:
        return {'error': str(e)}


def scan_table_items(table, limit=None, filter_expression=None):
    """Scan table and return items"""
    items = []
    scan_kwargs = {}
    
    if limit:
        scan_kwargs['Limit'] = limit
    
    if filter_expression:
        scan_kwargs['FilterExpression'] = filter_expression
    
    try:
        done = False
        while not done:
            response = table.scan(**scan_kwargs)
            items.extend(response.get('Items', []))
            
            # Check if we've reached the limit
            if limit and len(items) >= limit:
                items = items[:limit]
                done = True
            elif 'LastEvaluatedKey' in response:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            else:
                done = True
        
        return items
    except Exception as e:
        print_with_flush(f'❌ Error scanning table: {str(e)}')
        return []


def inspect_table(table_name, limit=None, capability_id=None):
    """Inspect a single table"""
    print_with_flush(f'\n{"="*60}')
    print_with_flush(f'📋 Table: {table_name}')
    print_with_flush(f'{"="*60}')
    
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(table_name)
        
        # Get table info
        info = get_table_info(table)
        
        if 'error' in info:
            print_with_flush(f'❌ Error: {info["error"]}')
            return None
        
        # Display table information
        print_with_flush(f'Status: {info["status"]}')
        print_with_flush(f'Items: {info["item_count"]:,}')
        print_with_flush(f'Size: {info["size_bytes"] / (1024*1024):.2f} MB')
        
        if info['indexes']:
            print_with_flush(f'Indexes: {", ".join([idx["name"] for idx in info["indexes"]])}')
        
        # Build filter expression if capability_id provided
        filter_expression = None
        if capability_id:
            from boto3.dynamodb.conditions import Attr
            filter_expression = Attr('capabilityId').eq(capability_id)
            print_with_flush(f'\n🔍 Filtering for capability: {capability_id}')
        
        # Scan for items
        print_with_flush(f'\n📦 Sample Items (limit: {limit or "all"}):')
        print_with_flush('-' * 40)
        
        items = scan_table_items(table, limit, filter_expression)
        
        if not items:
            print_with_flush('  No items found')
        else:
            # Group items by type for better display
            capabilities = []
            components = []
            jobs = []
            metrics = []
            other = []
            
            for item in items:
                pk = item.get('PK', '')
                sk = item.get('SK', '')
                
                if 'CAPABILITY#' in pk and 'METADATA' in sk:
                    capabilities.append(item)
                elif 'COMPONENT#' in sk:
                    components.append(item)
                elif 'JOB#' in sk:
                    jobs.append(item)
                elif 'METRIC#' in sk:
                    metrics.append(item)
                else:
                    other.append(item)
            
            # Display grouped items
            if capabilities:
                print_with_flush(f'\n📦 Capabilities ({len(capabilities)}):')
                for item in capabilities[:5]:  # Show first 5
                    print_with_flush(format_item_display(item))
                    print_with_flush('-' * 30)
            
            if components:
                print_with_flush(f'\n🔧 Components ({len(components)}):')
                for item in components[:5]:
                    print_with_flush(format_item_display(item))
                    print_with_flush('-' * 30)
            
            if jobs:
                print_with_flush(f'\n🚀 Jobs ({len(jobs)}):')
                for item in jobs[:5]:
                    print_with_flush(format_item_display(item))
                    print_with_flush('-' * 30)
            
            if metrics:
                print_with_flush(f'\n📊 Metrics ({len(metrics)}):')
                for item in metrics[:5]:
                    print_with_flush(format_item_display(item))
                    print_with_flush('-' * 30)
            
            if other:
                print_with_flush(f'\n❓ Other Items ({len(other)}):')
                for item in other[:5]:
                    print_with_flush(format_item_display(item))
                    print_with_flush('-' * 30)
        
        return items
        
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        print_with_flush(f'❌ Table {table_name} does not exist')
        return None
    except Exception as e:
        print_with_flush(f'❌ Error inspecting table: {str(e)}')
        return None


def export_to_file(data, filename):
    """Export data to JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=decimal_default)
        print_with_flush(f'✅ Data exported to {filename}')
    except Exception as e:
        print_with_flush(f'❌ Error exporting data: {str(e)}')


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Inspect capability DynamoDB tables')
    parser.add_argument('--table', '-t', type=str,
                        help='Specific table to inspect')
    parser.add_argument('--capability', '-c', type=str,
                        help='Filter by capability ID')
    parser.add_argument('--limit', '-l', type=int, default=20,
                        help='Limit number of items to display (default: 20)')
    parser.add_argument('--export', '-e', type=str,
                        help='Export results to JSON file')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Show all items (no limit)')
    
    args = parser.parse_args()
    
    print_with_flush('\n' + '='*70)
    print_with_flush('🔍 Business Capability System - Table Inspector')
    print_with_flush('='*70)
    
    # Define tables to inspect
    tables = [
        'BusinessCapabilitySystem',
        'CapabilityComponents',
        'ImplementationJobs',
        'PerformanceMetrics'
    ]
    
    # If specific table requested, only inspect that one
    if args.table:
        if args.table not in tables:
            print_with_flush(f'❌ Unknown table: {args.table}')
            print_with_flush(f'Valid tables: {", ".join(tables)}')
            return False
        tables = [args.table]
    
    # Determine limit
    limit = None if args.all else args.limit
    
    # Inspect each table
    all_results = {}
    for table_name in tables:
        items = inspect_table(table_name, limit, args.capability)
        if items is not None:
            all_results[table_name] = items
    
    # Export if requested
    if args.export and all_results:
        export_to_file(all_results, args.export)
    
    # Print summary
    print_with_flush('\n' + '='*70)
    print_with_flush('📊 INSPECTION SUMMARY')
    print_with_flush('='*70)
    
    total_items = 0
    for table_name, items in all_results.items():
        count = len(items) if items else 0
        total_items += count
        print_with_flush(f'{table_name}: {count} items inspected')
    
    print_with_flush(f'\nTotal items inspected: {total_items}')
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
