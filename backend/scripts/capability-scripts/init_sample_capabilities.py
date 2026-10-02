#!/usr/bin/env python3
"""
Initialize Sample Capability Data
==================================
This script creates sample data for the Business Capability System tables.

Creates sample:
- Capabilities
- Components
- Implementation Jobs
- Performance Metrics

Usage:
    python3 init_sample_capabilities.py                # Create sample data
    python3 init_sample_capabilities.py --clean       # Clean existing data first
    python3 init_sample_capabilities.py --minimal     # Create minimal test data
"""

import boto3
import sys
import os
import argparse
import uuid
import random
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def print_with_flush(message):
    """Print message and flush stdout immediately"""
    print(message)
    sys.stdout.flush()


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


def generate_capability_id():
    """Generate a unique capability ID"""
    return f"CAP-{uuid.uuid4().hex[:8].upper()}"


def generate_component_id():
    """Generate a unique component ID"""
    return f"COMP-{uuid.uuid4().hex[:8].upper()}"


def generate_job_id():
    """Generate a unique job ID"""
    return f"JOB-{uuid.uuid4().hex[:8].upper()}"


def generate_metric_id():
    """Generate a unique metric ID"""
    return f"MET-{uuid.uuid4().hex[:8].upper()}"


def create_sample_capabilities(table, minimal=False):
    """Create sample capabilities"""
    print_with_flush('\n📦 Creating sample capabilities...')
    
    sample_capabilities = [
        {
            'name': 'Customer Relationship Management',
            'description': 'Comprehensive CRM system for managing customer interactions and data',
            'businessDomain': 'customer',
            'status': 'active',
            'priority': 'high',
            'owner': 'Sarah Johnson',
            'createdBy': 'admin',
            'odaComponentType': 'CustomerEngagement'
        },
        {
            'name': 'Product Catalog Management',
            'description': 'Central repository for all product information and metadata',
            'businessDomain': 'product',
            'status': 'active',
            'priority': 'critical',
            'owner': 'Michael Chen',
            'createdBy': 'admin',
            'odaComponentType': 'ProductManagement'
        },
        {
            'name': 'Order Processing System',
            'description': 'End-to-end order lifecycle management and fulfillment',
            'businessDomain': 'sales',
            'status': 'development',
            'priority': 'critical',
            'owner': 'Emily Davis',
            'createdBy': 'admin',
            'odaComponentType': 'OrderManagement'
        },
        {
            'name': 'Inventory Management',
            'description': 'Real-time inventory tracking and optimization system',
            'businessDomain': 'supply-chain',
            'status': 'planning',
            'priority': 'high',
            'owner': 'Robert Wilson',
            'createdBy': 'admin',
            'odaComponentType': 'InventoryControl'
        },
        {
            'name': 'Analytics Dashboard',
            'description': 'Business intelligence and reporting platform',
            'businessDomain': 'analytics',
            'status': 'active',
            'priority': 'medium',
            'owner': 'Lisa Anderson',
            'createdBy': 'admin',
            'odaComponentType': 'DataAnalytics'
        }
    ]
    
    if minimal:
        sample_capabilities = sample_capabilities[:2]  # Only create first 2 for minimal
    
    created_capabilities = []
    
    try:
        with table.batch_writer() as batch:
            for cap_data in sample_capabilities:
                capability_id = generate_capability_id()
                timestamp = datetime.now(timezone.utc).isoformat()
                
                # Main capability item
                item = {
                    'PK': f"CAPABILITY#{capability_id}",
                    'SK': 'METADATA',
                    'capabilityId': capability_id,
                    'createdAt': timestamp,
                    'updatedAt': timestamp,
                    **cap_data
                }
                
                # Add GSI attributes for querying
                item['GSI1PK'] = f"STATUS#{cap_data['status']}"
                item['GSI1SK'] = f"CAPABILITY#{capability_id}"
                item['GSI2PK'] = f"OWNER#{cap_data['owner']}"
                item['GSI2SK'] = f"PRIORITY#{cap_data['priority']}"
                
                batch.put_item(Item=item)
                created_capabilities.append(capability_id)
                print_with_flush(f'  ✅ Created capability: {cap_data["name"]} ({capability_id})')
        
        print_with_flush(f'Created {len(created_capabilities)} capabilities')
        return created_capabilities
        
    except Exception as e:
        print_with_flush(f'❌ Error creating capabilities: {str(e)}')
        return []


def create_sample_components(table, capability_ids, minimal=False):
    """Create sample components for capabilities"""
    print_with_flush('\n🔧 Creating sample components...')
    
    if not capability_ids:
        print_with_flush('  ⚠️  No capabilities to create components for')
        return []
    
    component_templates = [
        {
            'name': 'REST API Gateway',
            'type': 'api-server',
            'version': '2.1.0',
            'status': 'active',
            'repository': 'https://github.com/company/api-gateway',
            'description': 'RESTful API gateway for external integrations'
        },
        {
            'name': 'PostgreSQL Database',
            'type': 'database',
            'version': '14.5',
            'status': 'active',
            'repository': 'N/A',
            'description': 'Primary relational database'
        },
        {
            'name': 'React Dashboard',
            'type': 'ui-dashboard',
            'version': '1.5.2',
            'status': 'active',
            'repository': 'https://github.com/company/react-dashboard',
            'description': 'Modern React-based user interface'
        },
        {
            'name': 'Message Queue Service',
            'type': 'message-queue',
            'version': '3.0.1',
            'status': 'active',
            'repository': 'https://github.com/company/mq-service',
            'description': 'RabbitMQ-based message queue'
        },
        {
            'name': 'Redis Cache',
            'type': 'cache',
            'version': '6.2.7',
            'status': 'active',
            'repository': 'N/A',
            'description': 'In-memory data caching layer'
        }
    ]
    
    created_components = []
    
    try:
        with table.batch_writer() as batch:
            for cap_id in capability_ids[:3 if not minimal else 1]:  # Create components for first 3 capabilities
                # Select 2-3 random components for each capability
                num_components = 2 if minimal else random.randint(2, 3)
                selected_components = random.sample(component_templates, num_components)
                
                for comp_data in selected_components:
                    component_id = generate_component_id()
                    timestamp = datetime.now(timezone.utc).isoformat()
                    
                    item = {
                        'PK': f"CAPABILITY#{cap_id}",
                        'SK': f"COMPONENT#{component_id}",
                        'capabilityId': cap_id,
                        'componentId': component_id,
                        'createdAt': timestamp,
                        'updatedAt': timestamp,
                        'owner': 'DevOps Team',
                        **comp_data
                    }
                    
                    # Add GSI attributes
                    item['GSI1PK'] = f"TYPE#{comp_data['type']}"
                    item['GSI1SK'] = f"STATUS#{comp_data['status']}"
                    item['GSI2PK'] = f"COMPONENT#{component_id}"
                    item['GSI2SK'] = f"CAPABILITY#{cap_id}"
                    
                    batch.put_item(Item=item)
                    created_components.append(component_id)
                    print_with_flush(f'  ✅ Created component: {comp_data["name"]} ({component_id}) for {cap_id}')
        
        print_with_flush(f'Created {len(created_components)} components')
        return created_components
        
    except Exception as e:
        print_with_flush(f'❌ Error creating components: {str(e)}')
        return []


def create_sample_jobs(table, capability_ids, minimal=False):
    """Create sample implementation jobs"""
    print_with_flush('\n🚀 Creating sample jobs...')
    
    if not capability_ids:
        print_with_flush('  ⚠️  No capabilities to create jobs for')
        return []
    
    job_templates = [
        {
            'name': 'Deploy to Production',
            'type': 'deployment',
            'status': 'completed',
            'priority': 'high',
            'assignedTo': 'DevOps Team',
            'description': 'Deploy latest version to production environment'
        },
        {
            'name': 'Database Migration',
            'type': 'migration',
            'status': 'running',
            'priority': 'critical',
            'assignedTo': 'Database Team',
            'description': 'Migrate database schema to version 2.0'
        },
        {
            'name': 'Security Audit',
            'type': 'audit',
            'status': 'pending',
            'priority': 'medium',
            'assignedTo': 'Security Team',
            'description': 'Quarterly security audit and penetration testing'
        },
        {
            'name': 'Performance Optimization',
            'type': 'optimization',
            'status': 'planning',
            'priority': 'low',
            'assignedTo': 'Performance Team',
            'description': 'Optimize API response times and database queries'
        },
        {
            'name': 'Backup Verification',
            'type': 'backup',
            'status': 'completed',
            'priority': 'medium',
            'assignedTo': 'Operations Team',
            'description': 'Verify backup integrity and restore procedures'
        }
    ]
    
    created_jobs = []
    
    try:
        with table.batch_writer() as batch:
            for cap_id in capability_ids[:3 if not minimal else 1]:  # Create jobs for first 3 capabilities
                # Create 1-3 jobs per capability
                num_jobs = 1 if minimal else random.randint(1, 3)
                selected_jobs = random.sample(job_templates, num_jobs)
                
                for job_data in selected_jobs:
                    job_id = generate_job_id()
                    timestamp = datetime.now(timezone.utc).isoformat()
                    
                    item = {
                        'PK': f"CAPABILITY#{cap_id}",
                        'SK': f"JOB#{job_id}",
                        'capabilityId': cap_id,
                        'jobId': job_id,
                        'createdAt': timestamp,
                        'updatedAt': timestamp,
                        'startedAt': timestamp if job_data['status'] in ['running', 'completed'] else None,
                        'completedAt': timestamp if job_data['status'] == 'completed' else None,
                        **job_data
                    }
                    
                    # Add GSI attributes
                    item['GSI1PK'] = f"STATUS#{job_data['status']}"
                    item['GSI1SK'] = f"CREATED#{timestamp}"
                    item['GSI2PK'] = f"ASSIGNEE#{job_data['assignedTo']}"
                    item['GSI2SK'] = f"PRIORITY#{job_data['priority']}"
                    
                    batch.put_item(Item=item)
                    created_jobs.append(job_id)
                    print_with_flush(f'  ✅ Created job: {job_data["name"]} ({job_id}) for {cap_id}')
        
        print_with_flush(f'Created {len(created_jobs)} jobs')
        return created_jobs
        
    except Exception as e:
        print_with_flush(f'❌ Error creating jobs: {str(e)}')
        return []


def create_sample_metrics(table, capability_ids, component_ids, minimal=False):
    """Create sample performance metrics"""
    print_with_flush('\n📊 Creating sample metrics...')
    
    if not capability_ids or not component_ids:
        print_with_flush('  ⚠️  No capabilities or components to create metrics for')
        return []
    
    metric_templates = [
        {'name': 'Response Time', 'unit': 'ms', 'min': 50, 'max': 500},
        {'name': 'CPU Usage', 'unit': '%', 'min': 10, 'max': 80},
        {'name': 'Memory Usage', 'unit': '%', 'min': 20, 'max': 75},
        {'name': 'Success Rate', 'unit': '%', 'min': 95, 'max': 100},
        {'name': 'Error Count', 'unit': 'count', 'min': 0, 'max': 10},
        {'name': 'Throughput', 'unit': 'req/s', 'min': 100, 'max': 1000},
        {'name': 'Database Connections', 'unit': 'count', 'min': 5, 'max': 50},
        {'name': 'Cache Hit Rate', 'unit': '%', 'min': 80, 'max': 99}
    ]
    
    created_metrics = []
    
    try:
        with table.batch_writer() as batch:
            # Create metrics for first capability and its components
            cap_id = capability_ids[0]
            comp_ids = component_ids[:2] if component_ids else []
            
            # Generate metrics for the last 7 days
            for days_ago in range(7 if not minimal else 1):
                metric_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
                
                # Create 2-3 metrics per component per day
                for comp_id in comp_ids:
                    num_metrics = 1 if minimal else random.randint(2, 3)
                    selected_metrics = random.sample(metric_templates, num_metrics)
                    
                    for metric_template in selected_metrics:
                        metric_id = generate_metric_id()
                        timestamp = metric_date.isoformat()
                        
                        # Generate random value within range
                        value = random.uniform(metric_template['min'], metric_template['max'])
                        
                        item = {
                            'PK': f"CAPABILITY#{cap_id}",
                            'SK': f"METRIC#{timestamp}#{metric_id}",
                            'capabilityId': cap_id,
                            'componentId': comp_id,
                            'metricId': metric_id,
                            'metricName': metric_template['name'],
                            'value': Decimal(str(round(value, 2))),
                            'unit': metric_template['unit'],
                            'timestamp': timestamp,
                            'source': 'monitoring-system'
                        }
                        
                        # Add GSI attributes
                        item['GSI1PK'] = f"COMPONENT#{comp_id}"
                        item['GSI1SK'] = f"METRIC#{metric_template['name']}"
                        item['GSI2PK'] = f"DATE#{metric_date.date().isoformat()}"
                        item['GSI2SK'] = f"TYPE#{metric_template['name'].replace(' ', '_').upper()}"
                        
                        # Add TTL (expire after 90 days)
                        item['ttl'] = int((metric_date + timedelta(days=90)).timestamp())
                        
                        batch.put_item(Item=item)
                        created_metrics.append(metric_id)
            
            print_with_flush(f'  ✅ Created {len(created_metrics)} metrics for capability {cap_id}')
        
        print_with_flush(f'Created {len(created_metrics)} total metrics')
        return created_metrics
        
    except Exception as e:
        print_with_flush(f'❌ Error creating metrics: {str(e)}')
        return []


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Initialize sample capability data')
    parser.add_argument('--clean', action='store_true',
                        help='Clean existing data before creating samples')
    parser.add_argument('--minimal', action='store_true',
                        help='Create minimal test data only')
    
    args = parser.parse_args()
    
    print_with_flush('\n' + '='*70)
    print_with_flush('🎯 Business Capability System - Sample Data Initialization')
    print_with_flush('='*70)
    
    # Get DynamoDB resource
    dynamodb = get_dynamodb_resource()
    
    # Clean if requested
    if args.clean:
        print_with_flush('\n🧹 Cleaning existing data first...')
        from cleanup_capabilities_tables import cleanup_table
        tables_to_clean = [
            'BusinessCapabilitySystem',
            'CapabilityComponents',
            'ImplementationJobs',
            'PerformanceMetrics'
        ]
        for table_name in tables_to_clean:
            cleanup_table(table_name, skip_confirmation=True)
    
    # Create sample data
    try:
        # Create capabilities
        cap_table = dynamodb.Table('BusinessCapabilitySystem')
        capability_ids = create_sample_capabilities(cap_table, args.minimal)
        
        # Create components
        comp_table = dynamodb.Table('CapabilityComponents')
        component_ids = create_sample_components(comp_table, capability_ids, args.minimal)
        
        # Create jobs
        jobs_table = dynamodb.Table('ImplementationJobs')
        job_ids = create_sample_jobs(jobs_table, capability_ids, args.minimal)
        
        # Create metrics
        metrics_table = dynamodb.Table('PerformanceMetrics')
        metric_ids = create_sample_metrics(metrics_table, capability_ids, component_ids, args.minimal)
        
        # Print summary
        print_with_flush('\n' + '='*70)
        print_with_flush('📊 INITIALIZATION SUMMARY')
        print_with_flush('='*70)
        print_with_flush(f'✅ Capabilities created: {len(capability_ids)}')
        print_with_flush(f'✅ Components created: {len(component_ids)}')
        print_with_flush(f'✅ Jobs created: {len(job_ids)}')
        print_with_flush(f'✅ Metrics created: {len(metric_ids)}')
        
        if capability_ids:
            print_with_flush('\n📝 Sample Capability IDs (for testing):')
            for cap_id in capability_ids[:3]:
                print_with_flush(f'   • {cap_id}')
        
        print_with_flush('\n🎉 Sample data initialization complete!')
        print_with_flush('\nNext steps:')
        print_with_flush('  1. Run inspect_capabilities_tables.py to view the data')
        print_with_flush('  2. Use capability-manager.py CLI to interact with the data')
        print_with_flush('  3. Test the MCP tools with the sample data')
        
        return True
        
    except Exception as e:
        print_with_flush(f'❌ Error during initialization: {str(e)}')
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
