#!/usr/bin/env python3
"""
Implementation Jobs Management Script
Handles deployment, update, and maintenance job executions for capabilities
"""

import boto3
import json
import uuid
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from botocore.exceptions import ClientError

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from db_utils import (
    get_table_name,
    get_dynamodb_resource,
    format_decimal,
    print_with_flush,
    get_current_timestamp
)


class ImplementationJobManager:
    """Manager for Implementation Job operations"""
    
    def __init__(self, dynamodb=None):
        """
        Initialize the Implementation Job Manager
        
        Args:
            dynamodb: Optional DynamoDB resource (for dependency injection/testing)
        """
        if dynamodb is not None:
            # Dependency injection mode (for testing)
            self.dynamodb = dynamodb
            self.table_name = get_table_name()
            self.table = self.dynamodb.Table(self.table_name) if hasattr(dynamodb, 'Table') else None
        else:
            # Normal operation - create AWS client
            self.dynamodb = get_dynamodb_resource()
            self.table_name = get_table_name()
            self.table = self.dynamodb.Table(self.table_name)
        self.s3_client = boto3.client('s3')
        
        # Job types
        self.job_types = [
            'deployment', 'rollback', 'configuration', 
            'scaling', 'maintenance', 'emergency', 'migration'
        ]
        
        # Job statuses
        self.job_statuses = [
            'pending', 'approved', 'running', 'completed', 
            'failed', 'cancelled', 'rolled_back'
        ]
        
        # Deployment strategies
        self.deployment_strategies = [
            'rolling', 'blue-green', 'canary', 'recreate', 'a-b-testing'
        ]
        
        # Priorities
        self.priorities = ['low', 'medium', 'high', 'critical', 'emergency']
    
    # ==================== JOB CRUD OPERATIONS ====================
    
    def create_job(self, capability_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new implementation job
        
        Args:
            capability_id: The capability ID
            job_data: Dictionary containing job details
            
        Returns:
            Created job with metadata
        """
        try:
            # Generate job ID if not provided
            job_id = job_data.get('jobId') or f"JOB-{job_data.get('jobType', 'DEPLOY')[:3].upper()}-{uuid.uuid4().hex[:6].upper()}"
            timestamp = get_current_timestamp()
            
            # Build the data structure
            data = {
                'jobId': job_id,
                'capabilityId': capability_id,
                'jobType': job_data.get('jobType', 'deployment'),
                'status': job_data.get('status', 'pending'),
                'priority': job_data.get('priority', 'medium'),
                'triggeredBy': job_data.get('triggeredBy', 'manual'),
                'approvedBy': job_data.get('approvedBy'),
                'startTime': job_data.get('startTime'),
                'endTime': job_data.get('endTime'),
                'duration': job_data.get('duration', 0),
                'targetComponents': job_data.get('targetComponents', []),
                'strategy': job_data.get('strategy', {
                    'type': 'rolling',
                    'canary': {
                        'enabled': False,
                        'percentage': 10,
                        'duration': '5m'
                    },
                    'rollback': {
                        'automatic': True,
                        'threshold': {
                            'errorRate': 5,
                            'latency': 500
                        }
                    }
                }),
                'validation': job_data.get('validation', {
                    'preDeployment': {
                        'healthChecks': 'pending',
                        'smokeTests': 'pending',
                        'securityScan': 'pending'
                    },
                    'postDeployment': {
                        'functionalTests': 'pending',
                        'performanceTests': 'pending',
                        'integrationTests': 'pending'
                    }
                }),
                'metrics': job_data.get('metrics', {
                    'affectedUsers': 0,
                    'downtime': 0,
                    'rollbacksTriggered': 0,
                    'deploymentsCompleted': 0,
                    'totalArtifactsDeployed': 0
                }),
                'artifacts': job_data.get('artifacts', {
                    'deploymentPlan': None,
                    'logs': None,
                    'reports': None
                }),
                'notes': job_data.get('notes', '')
            }
            
            # Create the DynamoDB item
            item = {
                'PK': f'CAPABILITY#{capability_id}',
                'SK': f'JOB#{timestamp}#{job_id}',
                'EntityType': 'ImplementationJob',
                'GSI1PK': f'JOB#{job_id}',
                'GSI1SK': timestamp,
                'CreatedAt': timestamp,
                'UpdatedAt': timestamp,
                'Data': data
            }
            
            # Add GSI for job status queries
            item['GSI2PK'] = f"JOBSTATUS#{data['status']}"
            item['GSI2SK'] = f"{timestamp}#{job_id}"
            
            # Put item in DynamoDB
            self.table.put_item(Item=item)
            
            print_with_flush(f"✅ Created job: {job_id} for capability: {capability_id}")
            return item
            
        except ClientError as e:
            print_with_flush(f"❌ Error creating job: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            print_with_flush(f"❌ Unexpected error: {str(e)}")
            raise
    
    def get_job(self, capability_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific job
        
        Args:
            capability_id: The capability ID
            job_id: The job ID
            
        Returns:
            Job data or None if not found
        """
        try:
            # Query using GSI1 to find the job
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'JOB#{job_id}'
                },
                Limit=1
            )
            
            items = response.get('Items', [])
            if items:
                return items[0]
            else:
                print_with_flush(f"⚠️ Job {job_id} not found")
                return None
                
        except ClientError as e:
            print_with_flush(f"❌ Error getting job: {e.response['Error']['Message']}")
            raise
    
    def update_job(self, capability_id: str, job_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a job
        
        Args:
            capability_id: The capability ID
            job_id: The job ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated job
        """
        try:
            # Get the job first
            current = self.get_job(capability_id, job_id)
            if not current:
                raise ValueError(f"Job {job_id} not found")
            
            # Merge updates with current data
            current_data = current['Data']
            for key, value in updates.items():
                if key in current_data:
                    if isinstance(current_data[key], dict) and isinstance(value, dict):
                        current_data[key].update(value)
                    else:
                        current_data[key] = value
            
            # Update timestamp
            timestamp = get_current_timestamp()
            
            # Calculate duration if job completed
            if updates.get('status') in ['completed', 'failed', 'cancelled']:
                if current_data.get('startTime') and not current_data.get('endTime'):
                    current_data['endTime'] = timestamp
                    start = datetime.fromisoformat(current_data['startTime'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    current_data['duration'] = int((end - start).total_seconds())
            
            # Update the item
            response = self.table.update_item(
                Key={
                    'PK': current['PK'],
                    'SK': current['SK']
                },
                UpdateExpression='SET #data = :data, UpdatedAt = :timestamp',
                ExpressionAttributeNames={
                    '#data': 'Data'
                },
                ExpressionAttributeValues={
                    ':data': current_data,
                    ':timestamp': timestamp
                },
                ReturnValues='ALL_NEW'
            )
            
            print_with_flush(f"✅ Updated job: {job_id}")
            return response['Attributes']
            
        except ClientError as e:
            print_with_flush(f"❌ Error updating job: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            print_with_flush(f"❌ Unexpected error: {str(e)}")
            raise
    
    def list_jobs(self, capability_id: str, 
                  status_filter: Optional[str] = None,
                  type_filter: Optional[str] = None,
                  limit: int = 20) -> List[Dict[str, Any]]:
        """
        List jobs for a capability
        
        Args:
            capability_id: The capability ID
            status_filter: Filter by job status
            type_filter: Filter by job type
            limit: Maximum number of jobs to return
            
        Returns:
            List of jobs
        """
        try:
            jobs = []
            
            # Query jobs for the capability
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'CAPABILITY#{capability_id}',
                    ':sk': 'JOB#'
                },
                ScanIndexForward=False,  # Newest first
                Limit=limit * 2 if status_filter or type_filter else limit
            )
            
            jobs.extend(response.get('Items', []))
            
            # Apply filters
            if status_filter:
                jobs = [j for j in jobs if j.get('Data', {}).get('status') == status_filter]
            
            if type_filter:
                jobs = [j for j in jobs if j.get('Data', {}).get('jobType') == type_filter]
            
            # Limit results
            jobs = jobs[:limit]
            
            print_with_flush(f"📊 Found {len(jobs)} jobs for capability {capability_id}")
            return jobs
            
        except ClientError as e:
            print_with_flush(f"❌ Error listing jobs: {e.response['Error']['Message']}")
            return []
    
    def get_active_jobs(self, capability_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all active (running) jobs
        
        Args:
            capability_id: Optional capability ID filter
            
        Returns:
            List of active jobs
        """
        try:
            active_statuses = ['pending', 'approved', 'running']
            all_jobs = []
            
            if capability_id:
                # Get jobs for specific capability
                jobs = self.list_jobs(capability_id)
                all_jobs = [j for j in jobs if j.get('Data', {}).get('status') in active_statuses]
            else:
                # Use GSI2 to query by status
                for status in active_statuses:
                    response = self.table.query(
                        IndexName='GSI2',
                        KeyConditionExpression='GSI2PK = :pk',
                        ExpressionAttributeValues={
                            ':pk': f'JOBSTATUS#{status}'
                        }
                    )
                    all_jobs.extend(response.get('Items', []))
            
            return all_jobs
            
        except ClientError as e:
            print_with_flush(f"❌ Error getting active jobs: {e.response['Error']['Message']}")
            return []
    
    # ==================== JOB EXECUTION ====================
    
    def start_job(self, capability_id: str, job_id: str) -> bool:
        """
        Start a pending job
        
        Args:
            capability_id: The capability ID
            job_id: The job ID
            
        Returns:
            True if successful
        """
        try:
            updates = {
                'status': 'running',
                'startTime': get_current_timestamp()
            }
            
            self.update_job(capability_id, job_id, updates)
            print_with_flush(f"🚀 Started job: {job_id}")
            return True
            
        except Exception as e:
            print_with_flush(f"❌ Error starting job: {str(e)}")
            return False
    
    def complete_job(self, capability_id: str, job_id: str, success: bool = True) -> bool:
        """
        Mark a job as completed
        
        Args:
            capability_id: The capability ID
            job_id: The job ID
            success: Whether the job succeeded
            
        Returns:
            True if successful
        """
        try:
            updates = {
                'status': 'completed' if success else 'failed',
                'endTime': get_current_timestamp()
            }
            
            # Update validation results
            if success:
                updates['validation'] = {
                    'preDeployment': {
                        'healthChecks': 'passed',
                        'smokeTests': 'passed',
                        'securityScan': 'passed'
                    },
                    'postDeployment': {
                        'functionalTests': 'passed',
                        'performanceTests': 'passed',
                        'integrationTests': 'passed'
                    }
                }
            
            self.update_job(capability_id, job_id, updates)
            status_icon = "✅" if success else "❌"
            print_with_flush(f"{status_icon} Job {job_id} {'completed successfully' if success else 'failed'}")
            return True
            
        except Exception as e:
            print_with_flush(f"❌ Error completing job: {str(e)}")
            return False
    
    def cancel_job(self, capability_id: str, job_id: str, reason: str = "") -> bool:
        """
        Cancel a job
        
        Args:
            capability_id: The capability ID
            job_id: The job ID
            reason: Cancellation reason
            
        Returns:
            True if successful
        """
        try:
            updates = {
                'status': 'cancelled',
                'endTime': get_current_timestamp(),
                'notes': f"Cancelled: {reason}" if reason else "Cancelled by user"
            }
            
            self.update_job(capability_id, job_id, updates)
            print_with_flush(f"🚫 Cancelled job: {job_id}")
            return True
            
        except Exception as e:
            print_with_flush(f"❌ Error cancelling job: {str(e)}")
            return False
    
    def rollback_job(self, capability_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Create a rollback job for a failed deployment
        
        Args:
            capability_id: The capability ID
            job_id: The original job ID
            
        Returns:
            Created rollback job or None
        """
        try:
            # Get the original job
            original_job = self.get_job(capability_id, job_id)
            if not original_job:
                print_with_flush(f"❌ Original job {job_id} not found")
                return None
            
            original_data = original_job.get('Data', {})
            
            # Create rollback job
            rollback_data = {
                'jobType': 'rollback',
                'priority': 'critical',
                'triggeredBy': f"rollback-of-{job_id}",
                'targetComponents': original_data.get('targetComponents', []),
                'notes': f"Rollback of job {job_id}"
            }
            
            # Reverse the version changes
            for component in rollback_data['targetComponents']:
                from_version = component.get('fromVersion')
                to_version = component.get('toVersion')
                if from_version and to_version:
                    component['fromVersion'] = to_version
                    component['toVersion'] = from_version
            
            rollback_job = self.create_job(capability_id, rollback_data)
            
            # Start the rollback immediately
            if rollback_job:
                rollback_id = rollback_job['Data']['jobId']
                self.start_job(capability_id, rollback_id)
            
            return rollback_job
            
        except Exception as e:
            print_with_flush(f"❌ Error creating rollback: {str(e)}")
            return None
    
    # ==================== JOB ARTIFACTS ====================
    
    def upload_job_artifacts(self, capability_id: str, job_id: str, 
                           artifact_type: str, content: str) -> Optional[str]:
        """
        Upload job artifacts to S3
        
        Args:
            capability_id: The capability ID
            job_id: The job ID
            artifact_type: Type of artifact (logs, reports, plan)
            content: Content to upload
            
        Returns:
            S3 URL or None
        """
        try:
            # Construct S3 key
            bucket_name = os.environ.get('ARTIFACTS_BUCKET', 'capability-deployments')
            key = f"capabilities/{capability_id}/jobs/{job_id}/{artifact_type}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=content,
                ContentType='application/json' if artifact_type.endswith('.json') else 'text/plain'
            )
            
            s3_url = f"s3://{bucket_name}/{key}"
            
            # Update job with artifact URL
            updates = {'artifacts': {}}
            if artifact_type == 'logs':
                updates['artifacts']['logs'] = s3_url
            elif artifact_type == 'reports':
                updates['artifacts']['reports'] = s3_url
            elif artifact_type == 'plan':
                updates['artifacts']['deploymentPlan'] = s3_url
            
            self.update_job(capability_id, job_id, updates)
            
            print_with_flush(f"📤 Uploaded {artifact_type} to {s3_url}")
            return s3_url
            
        except Exception as e:
            print_with_flush(f"❌ Error uploading artifacts: {str(e)}")
            return None
    
    # ==================== DISPLAY FUNCTIONS ====================
    
    def display_job(self, job: Dict[str, Any]):
        """Display job details in a formatted way"""
        data = job.get('Data', {})
        
        print_with_flush("\n" + "="*80)
        print_with_flush(f"📦 JOB: {data.get('jobId', 'Unknown')}")
        print_with_flush("="*80)
        
        # Basic Information
        print_with_flush("\n📋 BASIC INFORMATION:")
        print_with_flush(f"  Type: {data.get('jobType', 'N/A')}")
        print_with_flush(f"  Status: {self._format_status(data.get('status', 'unknown'))}")
        print_with_flush(f"  Priority: {data.get('priority', 'N/A')}")
        print_with_flush(f"  Triggered By: {data.get('triggeredBy', 'N/A')}")
        if data.get('approvedBy'):
            print_with_flush(f"  Approved By: {data.get('approvedBy')}")
        
        # Timing
        print_with_flush("\n⏱️ TIMING:")
        if data.get('startTime'):
            print_with_flush(f"  Started: {data.get('startTime')}")
        if data.get('endTime'):
            print_with_flush(f"  Ended: {data.get('endTime')}")
        if data.get('duration'):
            duration_min = data['duration'] / 60
            print_with_flush(f"  Duration: {duration_min:.1f} minutes")
        
        # Target Components
        if data.get('targetComponents'):
            print_with_flush("\n🎯 TARGET COMPONENTS:")
            for comp in data['targetComponents']:
                print_with_flush(f"  • {comp.get('componentId', 'Unknown')}")
                if comp.get('fromVersion') and comp.get('toVersion'):
                    print_with_flush(f"    {comp['fromVersion']} → {comp['toVersion']}")
                print_with_flush(f"    Status: {comp.get('status', 'pending')}")
        
        # Strategy
        strategy = data.get('strategy', {})
        if strategy:
            print_with_flush("\n📐 DEPLOYMENT STRATEGY:")
            print_with_flush(f"  Type: {strategy.get('type', 'N/A')}")
            if strategy.get('canary', {}).get('enabled'):
                canary = strategy['canary']
                print_with_flush(f"  Canary: {canary.get('percentage', 10)}% for {canary.get('duration', 'N/A')}")
            if strategy.get('rollback', {}).get('automatic'):
                rollback = strategy['rollback']
                print_with_flush(f"  Auto-rollback: Error rate > {rollback.get('threshold', {}).get('errorRate', 5)}%")
        
        # Validation
        validation = data.get('validation', {})
        if validation:
            print_with_flush("\n✅ VALIDATION:")
            pre = validation.get('preDeployment', {})
            post = validation.get('postDeployment', {})
            
            if pre:
                print_with_flush("  Pre-deployment:")
                for check, status in pre.items():
                    icon = "✅" if status == 'passed' else "⏳" if status == 'pending' else "❌"
                    print_with_flush(f"    {icon} {check}: {status}")
            
            if post:
                print_with_flush("  Post-deployment:")
                for check, status in post.items():
                    icon = "✅" if status == 'passed' else "⏳" if status == 'pending' else "❌"
                    print_with_flush(f"    {icon} {check}: {status}")
        
        # Metrics
        metrics = data.get('metrics', {})
        if metrics and any(v for v in metrics.values() if v):
            print_with_flush("\n📊 METRICS:")
            if metrics.get('affectedUsers'):
                print_with_flush(f"  Affected Users: {metrics['affectedUsers']:,}")
            if metrics.get('downtime'):
                print_with_flush(f"  Downtime: {metrics['downtime']} seconds")
            if metrics.get('rollbacksTriggered'):
                print_with_flush(f"  Rollbacks: {metrics['rollbacksTriggered']}")
            if metrics.get('deploymentsCompleted'):
                print_with_flush(f"  Deployments: {metrics['deploymentsCompleted']}")
        
        # Notes
        if data.get('notes'):
            print_with_flush("\n📝 NOTES:")
            print_with_flush(f"  {data['notes']}")
        
        print_with_flush("\n" + "="*80)
    
    def display_jobs_table(self, jobs: List[Dict[str, Any]]):
        """Display jobs in a table format"""
        if not jobs:
            print_with_flush("No jobs found")
            return
        
        print_with_flush("\n" + "="*110)
        print_with_flush(f"{'Job ID':<25} {'Type':<12} {'Status':<12} {'Priority':<10} {'Duration':<10} {'Started':<20}")
        print_with_flush("="*110)
        
        for job in jobs:
            data = job.get('Data', {})
            
            # Format duration
            duration_str = 'N/A'
            if data.get('duration'):
                duration_min = data['duration'] / 60
                duration_str = f"{duration_min:.1f}m"
            
            # Format start time
            start_time = 'Not started'
            if data.get('startTime'):
                start_time = data['startTime'][:19].replace('T', ' ')
            
            print_with_flush(
                f"{data.get('jobId', 'Unknown')[:24]:<25} "
                f"{data.get('jobType', 'N/A'):<12} "
                f"{self._format_status_short(data.get('status', 'unknown')):<12} "
                f"{data.get('priority', 'N/A'):<10} "
                f"{duration_str:<10} "
                f"{start_time:<20}"
            )
        
        print_with_flush("="*110)
        print_with_flush(f"Total jobs: {len(jobs)}")
    
    def _format_status(self, status: str) -> str:
        """Format status with icon"""
        icons = {
            'pending': '⏳',
            'approved': '✔️',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫',
            'rolled_back': '↩️'
        }
        return f"{icons.get(status, '❓')} {status}"
    
    def _format_status_short(self, status: str) -> str:
        """Format status for table display"""
        colors = {
            'pending': status,
            'approved': status,
            'running': status,
            'completed': status,
            'failed': status,
            'cancelled': status,
            'rolled_back': 'rolled back'
        }
        return colors.get(status, status)
    
    def get_job_statistics(self, capability_id: str) -> Dict[str, Any]:
        """
        Get job statistics for a capability
        
        Args:
            capability_id: The capability ID
            
        Returns:
            Statistics dictionary
        """
        try:
            all_jobs = self.list_jobs(capability_id, limit=100)
            
            stats = {
                'total': len(all_jobs),
                'completed': 0,
                'failed': 0,
                'running': 0,
                'pending': 0,
                'success_rate': 0,
                'average_duration': 0,
                'last_deployment': None
            }
            
            total_duration = 0
            duration_count = 0
            
            for job in all_jobs:
                data = job.get('Data', {})
                status = data.get('status')
                
                if status == 'completed':
                    stats['completed'] += 1
                elif status == 'failed':
                    stats['failed'] += 1
                elif status == 'running':
                    stats['running'] += 1
                elif status == 'pending':
                    stats['pending'] += 1
                
                # Track duration
                if data.get('duration'):
                    total_duration += data['duration']
                    duration_count += 1
                
                # Track last deployment
                if data.get('jobType') == 'deployment' and data.get('startTime'):
                    if not stats['last_deployment'] or data['startTime'] > stats['last_deployment']:
                        stats['last_deployment'] = data['startTime']
            
            # Calculate averages
            if stats['completed'] + stats['failed'] > 0:
                stats['success_rate'] = (stats['completed'] / (stats['completed'] + stats['failed'])) * 100
            
            if duration_count > 0:
                stats['average_duration'] = total_duration / duration_count / 60  # In minutes
            
            return stats
            
        except Exception as e:
            print_with_flush(f"❌ Error getting statistics: {str(e)}")
            return {}


def main():
    """Main function for testing"""
    print_with_flush("\n🚀 IMPLEMENTATION JOB MANAGEMENT SYSTEM")
    print_with_flush("="*60)
    
    # Get capability ID
    capability_id = input("Enter capability ID (or 'test' for testing): ").strip()
    if not capability_id:
        capability_id = 'test'
    
    manager = ImplementationJobManager()
    
    while True:
        print_with_flush("\n📋 MAIN MENU:")
        print_with_flush("1. List jobs")
        print_with_flush("2. Create job")
        print_with_flush("3. View job details")
        print_with_flush("4. Start job")
        print_with_flush("5. Complete job")
        print_with_flush("6. Cancel job")
        print_with_flush("7. Create rollback")
        print_with_flush("8. View active jobs")
        print_with_flush("9. Job statistics")
        print_with_flush("0. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            # List jobs
            print_with_flush("\nFilter options (press Enter to skip):")
            status = input("Status filter: ").strip() or None
            job_type = input("Type filter: ").strip() or None
            
            jobs = manager.list_jobs(capability_id, status_filter=status, type_filter=job_type)
            manager.display_jobs_table(jobs)
            
        elif choice == '2':
            # Create job
            print_with_flush("\n📝 Enter job details:")
            job_type = input(f"Job type ({'/'.join(manager.job_types)}): ").strip()
            priority = input(f"Priority ({'/'.join(manager.priorities)}): ").strip()
            
            # Get target components
            components = []
            while True:
                comp_id = input("Add target component ID (or Enter to finish): ").strip()
                if not comp_id:
                    break
                components.append({
                    'componentId': comp_id,
                    'status': 'pending'
                })
            
            job_data = {
                'jobType': job_type or 'deployment',
                'priority': priority or 'medium',
                'targetComponents': components,
                'triggeredBy': 'manual'
            }
            
            job = manager.create_job(capability_id, job_data)
            if job:
                manager.display_job(job)
                
        elif choice == '3':
            # View job
            job_id = input("\nEnter job ID: ").strip()
            job = manager.get_job(capability_id, job_id)
            if job:
                manager.display_job(job)
                
        elif choice == '4':
            # Start job
            job_id = input("\nEnter job ID to start: ").strip()
            if manager.start_job(capability_id, job_id):
                print_with_flush("✅ Job started")
                
        elif choice == '5':
            # Complete job
            job_id = input("\nEnter job ID to complete: ").strip()
            success = input("Success? (Y/n): ").strip().lower() != 'n'
            if manager.complete_job(capability_id, job_id, success):
                print_with_flush("✅ Job completed")
                
        elif choice == '6':
            # Cancel job
            job_id = input("\nEnter job ID to cancel: ").strip()
            reason = input("Cancellation reason: ").strip()
            if manager.cancel_job(capability_id, job_id, reason):
                print_with_flush("✅ Job cancelled")
                
        elif choice == '7':
            # Create rollback
            job_id = input("\nEnter job ID to rollback: ").strip()
            rollback = manager.rollback_job(capability_id, job_id)
            if rollback:
                print_with_flush("✅ Rollback job created")
                manager.display_job(rollback)
                
        elif choice == '8':
            # View active jobs
            active_jobs = manager.get_active_jobs(capability_id)
            if active_jobs:
                print_with_flush(f"\n🔄 {len(active_jobs)} active jobs:")
                manager.display_jobs_table(active_jobs)
            else:
                print_with_flush("\n✅ No active jobs")
                
        elif choice == '9':
            # Job statistics
            stats = manager.get_job_statistics(capability_id)
            if stats:
                print_with_flush("\n📊 JOB STATISTICS:")
                print_with_flush("="*40)
                print_with_flush(f"Total Jobs: {stats['total']}")
                print_with_flush(f"Completed: {stats['completed']}")
                print_with_flush(f"Failed: {stats['failed']}")
                print_with_flush(f"Running: {stats['running']}")
                print_with_flush(f"Pending: {stats['pending']}")
                print_with_flush(f"Success Rate: {stats['success_rate']:.1f}%")
                print_with_flush(f"Avg Duration: {stats['average_duration']:.1f} minutes")
                if stats['last_deployment']:
                    print_with_flush(f"Last Deployment: {stats['last_deployment']}")
                print_with_flush("="*40)
                
        elif choice == '0':
            print_with_flush("\n👋 Goodbye!")
            break
        else:
            print_with_flush("❌ Invalid choice")


if __name__ == "__main__":
    main()
