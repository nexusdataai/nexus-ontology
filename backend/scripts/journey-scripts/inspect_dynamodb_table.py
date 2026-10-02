#!/usr/bin/env python3
"""
Inspect DynamoDB TransformationSystem Table
===========================================
This script provides a comprehensive view of all data in the TransformationSystem table.

Features:
- Lists all journeys with detailed information
- Shows stages for each journey
- Displays Second Brain rules
- Lists jobs and their status
- Shows logs and reports
- Provides statistics and summaries

Usage:
    python3 inspect_dynamodb_table.py
    python3 inspect_dynamodb_table.py --journey-id JRN-123  # Detailed view of specific journey
    python3 inspect_dynamodb_table.py --format json  # Output as JSON
    python3 inspect_dynamodb_table.py --stats-only  # Only show statistics
"""

import boto3
import sys
import os
import argparse
import json
import traceback
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any


def print_with_flush(message, end='\n'):
    """Print message and flush stdout immediately"""
    print(message, end=end)
    sys.stdout.flush()


class TableInspector:
    """Inspector for TransformationSystem DynamoDB table"""
    
    def __init__(self, dynamodb_resource, table_name: str = None):
        """Initialize the inspector"""
        self.dynamodb = dynamodb_resource
        if table_name is None:
            table_name = os.environ.get('DYNAMODB_TABLE', 'TransformationSystem')
        self.table_name = table_name
        self.table = dynamodb_resource.Table(table_name)
        self.data = {
            'journeys': [],
            'stages': defaultdict(list),
            'rules': defaultdict(list),
            'jobs': defaultdict(list),
            'logs': defaultdict(list),
            'reports': defaultdict(list),
            'other': []
        }
        self.stats = {
            'total_items': 0,
            'by_entity_type': defaultdict(int),
            'journeys_by_status': defaultdict(int),
            'stages_by_status': defaultdict(int),
            'jobs_by_status': defaultdict(int),
            'rules_by_type': defaultdict(int),
            'rules_by_priority': defaultdict(int),
        }
    
    def scan_table(self):
        """Scan the entire table and organize data"""
        print_with_flush(f'🔍 Scanning {self.table_name} table...')
        
        scan_kwargs = {}
        scanned_count = 0
        
        try:
            while True:
                response = self.table.scan(**scan_kwargs)
                items = response.get('Items', [])
                
                for item in items:
                    self._process_item(item)
                    scanned_count += 1
                
                print_with_flush(f'   • Scanned {scanned_count} items...', end='\r')
                
                # Check if there are more items
                if 'LastEvaluatedKey' in response:
                    scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                else:
                    break
            
            print_with_flush(f'\n✅ Scanned {scanned_count} items successfully')
            self.stats['total_items'] = scanned_count
            return True
            
        except Exception as e:
            print_with_flush(f'\n❌ Error scanning table: {str(e)}')
            traceback.print_exc()
            return False
    
    def _process_item(self, item):
        """Process and categorize a single item"""
        entity_type = item.get('EntityType', 'Unknown')
        self.stats['by_entity_type'][entity_type] += 1
        
        pk = item.get('PK', '')
        sk = item.get('SK', '')
        
        # Categorize by entity type
        if entity_type == 'Journey':
            self.data['journeys'].append(item)
            status = item.get('Data', {}).get('status', 'unknown')
            self.stats['journeys_by_status'][status] += 1
            
        elif entity_type == 'StageDefinition':
            journey_id = pk.replace('JOURNEY#', '')
            self.data['stages'][journey_id].append(item)
            status = item.get('Data', {}).get('status', 'unknown')
            self.stats['stages_by_status'][status] += 1
            
        elif entity_type == 'SecondBrainRule':
            journey_id = pk.replace('JOURNEY#', '')
            self.data['rules'][journey_id].append(item)
            rule_data = item.get('Data', {})
            rule_type = rule_data.get('type', 'unknown')
            priority = rule_data.get('priority', 'unknown')
            self.stats['rules_by_type'][rule_type] += 1
            self.stats['rules_by_priority'][priority] += 1
            
        elif entity_type == 'Job':
            journey_id = pk.replace('JOURNEY#', '')
            self.data['jobs'][journey_id].append(item)
            status = item.get('Data', {}).get('status', 'unknown')
            self.stats['jobs_by_status'][status] += 1
            
        elif entity_type == 'LogEntry':
            journey_id = pk.replace('JOURNEY#', '')
            self.data['logs'][journey_id].append(item)
            
        elif entity_type == 'Report':
            journey_id = pk.replace('JOURNEY#', '')
            self.data['reports'][journey_id].append(item)
            
        else:
            self.data['other'].append(item)
    
    def get_journey_id_from_pk(self, pk: str) -> str:
        """Extract journey ID from PK"""
        if pk.startswith('JOURNEY#'):
            return pk.replace('JOURNEY#', '')
        return pk
    
    def display_statistics(self):
        """Display overall statistics"""
        print_with_flush('\n' + '=' * 80)
        print_with_flush('📊 OVERALL STATISTICS')
        print_with_flush('=' * 80)
        
        print_with_flush(f'\n📦 Total Items: {self.stats["total_items"]:,}')
        
        # Entity type breakdown
        print_with_flush('\n📋 Items by Entity Type:')
        for entity_type, count in sorted(self.stats['by_entity_type'].items()):
            print_with_flush(f'   • {entity_type}: {count}')
        
        # Journeys statistics
        if self.data['journeys']:
            print_with_flush(f'\n🗂️  Journeys: {len(self.data["journeys"])}')
            if self.stats['journeys_by_status']:
                print_with_flush('   Status breakdown:')
                for status, count in sorted(self.stats['journeys_by_status'].items()):
                    print_with_flush(f'      • {status}: {count}')
        
        # Stages statistics
        total_stages = sum(len(stages) for stages in self.data['stages'].values())
        if total_stages > 0:
            print_with_flush(f'\n📚 Stages: {total_stages}')
            if self.stats['stages_by_status']:
                print_with_flush('   Status breakdown:')
                for status, count in sorted(self.stats['stages_by_status'].items()):
                    print_with_flush(f'      • {status}: {count}')
        
        # Rules statistics
        total_rules = sum(len(rules) for rules in self.data['rules'].values())
        if total_rules > 0:
            print_with_flush(f'\n🧠 Second Brain Rules: {total_rules}')
            if self.stats['rules_by_type']:
                print_with_flush('   By type:')
                for rule_type, count in sorted(self.stats['rules_by_type'].items()):
                    print_with_flush(f'      • {rule_type}: {count}')
            if self.stats['rules_by_priority']:
                print_with_flush('   By priority:')
                for priority, count in sorted(self.stats['rules_by_priority'].items()):
                    print_with_flush(f'      • {priority}: {count}')
        
        # Jobs statistics
        total_jobs = sum(len(jobs) for jobs in self.data['jobs'].values())
        if total_jobs > 0:
            print_with_flush(f'\n⚙️  Jobs: {total_jobs}')
            if self.stats['jobs_by_status']:
                print_with_flush('   Status breakdown:')
                for status, count in sorted(self.stats['jobs_by_status'].items()):
                    print_with_flush(f'      • {status}: {count}')
        
        # Logs statistics
        total_logs = sum(len(logs) for logs in self.data['logs'].values())
        if total_logs > 0:
            print_with_flush(f'\n📝 Log Entries: {total_logs}')
        
        # Reports statistics
        total_reports = sum(len(reports) for reports in self.data['reports'].values())
        if total_reports > 0:
            print_with_flush(f'\n📄 Reports: {total_reports}')
    
    def display_journeys(self):
        """Display detailed journey information"""
        if not self.data['journeys']:
            print_with_flush('\n📭 No journeys found')
            return
        
        print_with_flush('\n' + '=' * 80)
        print_with_flush('🗂️  JOURNEYS')
        print_with_flush('=' * 80)
        
        for journey_item in sorted(self.data['journeys'], 
                                   key=lambda x: x.get('CreatedAt', ''), 
                                   reverse=True):
            journey_data = journey_item.get('Data', {})
            journey_id = journey_data.get('journeyId', 'Unknown')
            
            print_with_flush(f'\n🔹 Journey ID: {journey_id}')
            print_with_flush(f'   Name: {journey_data.get("name", "N/A")}')
            print_with_flush(f'   Status: {journey_data.get("status", "N/A")}')
            print_with_flush(f'   Priority: {journey_data.get("priority", "N/A")}')
            print_with_flush(f'   Component Type: {journey_data.get("odaComponentType", "N/A")}')
            print_with_flush(f'   Created: {journey_item.get("CreatedAt", "N/A")}')
            print_with_flush(f'   Updated: {journey_item.get("UpdatedAt", "N/A")}')
            print_with_flush(f'   Created By: {journey_data.get("createdBy", "N/A")}')
            
            # Progress information
            print_with_flush(f'   Overall Progress: {journey_data.get("overallProgress", 0)}%')
            print_with_flush(f'   Current Stage: {journey_data.get("currentStageId", "N/A")}')
            print_with_flush(f'   Current Stage Index: {journey_data.get("currentStageIndex", 0)}')
            
            # Source information
            source = journey_data.get('source', {})
            if source:
                print_with_flush(f'   Source Type: {source.get("type", "N/A")}')
                print_with_flush(f'   Source Schema: {source.get("schemaName", "N/A")}')
            
            # Configuration
            config = journey_data.get('configuration', {})
            if config:
                print_with_flush(f'   Second Brain Enabled: {config.get("secondBrainEnabled", False)}')
                print_with_flush(f'   TMF Spec Version: {config.get("tmfSpecVersion", "N/A")}')
            
            # Aggregates
            aggregates = journey_data.get('aggregates', {})
            if aggregates:
                print_with_flush(f'   Total Jobs: {aggregates.get("totalJobs", 0)}')
                print_with_flush(f'   Completed Jobs: {aggregates.get("completedJobs", 0)}')
                print_with_flush(f'   Failed Jobs: {aggregates.get("failedJobs", 0)}')
                print_with_flush(f'   Total Rules: {aggregates.get("totalRules", 0)}')
                print_with_flush(f'   Active Rules: {aggregates.get("activeRules", 0)}')
            
            # Display stages for this journey
            self._display_journey_stages(journey_id)
            
            # Display rules for this journey
            self._display_journey_rules(journey_id)
            
            # Display jobs for this journey
            self._display_journey_jobs(journey_id)
            
            # Display logs summary for this journey
            self._display_journey_logs_summary(journey_id)
            
            # Display reports for this journey
            self._display_journey_reports(journey_id)
    
    def _display_journey_stages(self, journey_id: str):
        """Display stages for a specific journey"""
        stages = self.data['stages'].get(journey_id, [])
        
        if not stages:
            return
        
        print_with_flush(f'\n   📚 Stages ({len(stages)}):')
        
        for stage in sorted(stages, key=lambda x: x.get('Data', {}).get('order', 0)):
            stage_data = stage.get('Data', {})
            print_with_flush(f'      • [{stage_data.get("order", "?")}] {stage_data.get("name", "Unknown")}')
            print_with_flush(f'        Stage ID: {stage_data.get("stageId", "N/A")}')
            print_with_flush(f'        Status: {stage_data.get("status", "N/A")}')
            print_with_flush(f'        Can Skip: {stage_data.get("canSkip", False)}')
            print_with_flush(f'        Est. Duration: {stage_data.get("estimatedDuration", "N/A")}')
            print_with_flush(f'        Second Brain Enabled: {stage_data.get("secondBrainEnabled", False)}')
            
            steps = stage_data.get('steps', [])
            if steps:
                print_with_flush(f'        Steps: {len(steps)}')
                for step in steps:
                    ai_marker = '🤖' if step.get('aiAssisted') else '  '
                    print_with_flush(f'          {ai_marker} [{step.get("order", "?")}] {step.get("name", "Unknown")}')
    
    def _display_journey_rules(self, journey_id: str):
        """Display Second Brain rules for a specific journey"""
        rules = self.data['rules'].get(journey_id, [])
        
        if not rules:
            return
        
        print_with_flush(f'\n   🧠 Second Brain Rules ({len(rules)}):')
        
        for rule in sorted(rules, 
                          key=lambda x: (x.get('Data', {}).get('stageId', ''),
                                        x.get('Data', {}).get('priority', ''))):
            rule_data = rule.get('Data', {})
            print_with_flush(f'      • {rule_data.get("title", "Unknown")}')
            print_with_flush(f'        Rule ID: {rule_data.get("ruleId", "N/A")}')
            print_with_flush(f'        Stage: {rule_data.get("stageId", "N/A")}')
            print_with_flush(f'        Type: {rule_data.get("type", "N/A")}')
            print_with_flush(f'        Priority: {rule_data.get("priority", "N/A")}')
            print_with_flush(f'        Status: {rule_data.get("status", "N/A")}')
            print_with_flush(f'        Scope: {rule_data.get("scope", "N/A")}')
            
            description = rule_data.get('description', '')
            if description:
                # Truncate long descriptions
                desc_preview = description[:100] + '...' if len(description) > 100 else description
                print_with_flush(f'        Description: {desc_preview}')
    
    def _display_journey_jobs(self, journey_id: str):
        """Display jobs for a specific journey"""
        jobs = self.data['jobs'].get(journey_id, [])
        
        if not jobs:
            return
        
        print_with_flush(f'\n   ⚙️  Jobs ({len(jobs)}):')
        
        for job in sorted(jobs, key=lambda x: x.get('CreatedAt', ''), reverse=True):
            job_data = job.get('Data', {})
            print_with_flush(f'      • Job ID: {job_data.get("jobId", "Unknown")}')
            print_with_flush(f'        Stage: {job_data.get("stageId", "N/A")}')
            print_with_flush(f'        Status: {job_data.get("status", "N/A")}')
            print_with_flush(f'        Progress: {job_data.get("progress", 0)}%')
            print_with_flush(f'        Current Step: {job_data.get("currentStep", "N/A")}')
            print_with_flush(f'        Started: {job.get("CreatedAt", "N/A")}')
            print_with_flush(f'        Updated: {job.get("UpdatedAt", "N/A")}')
            
            error = job_data.get('error')
            if error:
                print_with_flush(f'        ❌ Error: {error}')
    
    def _display_journey_logs_summary(self, journey_id: str):
        """Display log summary for a specific journey"""
        logs = self.data['logs'].get(journey_id, [])
        
        if not logs:
            return
        
        print_with_flush(f'\n   📝 Logs ({len(logs)} entries):')
        
        # Count by level
        by_level = defaultdict(int)
        for log in logs:
            level = log.get('Data', {}).get('level', 'unknown')
            by_level[level] += 1
        
        for level, count in sorted(by_level.items()):
            print_with_flush(f'      • {level}: {count}')
    
    def _display_journey_reports(self, journey_id: str):
        """Display reports for a specific journey"""
        reports = self.data['reports'].get(journey_id, [])
        
        if not reports:
            return
        
        print_with_flush(f'\n   📄 Reports ({len(reports)}):')
        
        for report in sorted(reports, key=lambda x: x.get('CreatedAt', ''), reverse=True):
            report_data = report.get('Data', {})
            print_with_flush(f'      • {report_data.get("title", "Unknown")}')
            print_with_flush(f'        Report ID: {report_data.get("reportId", "N/A")}')
            print_with_flush(f'        Type: {report_data.get("type", "N/A")}')
            print_with_flush(f'        Format: {report_data.get("format", "N/A")}')
            print_with_flush(f'        Created: {report.get("CreatedAt", "N/A")}')
    
    def display_specific_journey(self, journey_id: str):
        """Display detailed information for a specific journey"""
        # Find the journey
        journey = None
        for j in self.data['journeys']:
            if j.get('Data', {}).get('journeyId') == journey_id:
                journey = j
                break
        
        if not journey:
            print_with_flush(f'❌ Journey not found: {journey_id}')
            return
        
        # Temporarily store only this journey
        temp_journeys = self.data['journeys']
        self.data['journeys'] = [journey]
        
        self.display_journeys()
        
        # Restore
        self.data['journeys'] = temp_journeys
    
    def export_as_json(self):
        """Export all data as JSON"""
        export_data = {
            'statistics': dict(self.stats),
            'journeys': self.data['journeys'],
            'stages': {k: v for k, v in self.data['stages'].items()},
            'rules': {k: v for k, v in self.data['rules'].items()},
            'jobs': {k: v for k, v in self.data['jobs'].items()},
            'logs': {k: v for k, v in self.data['logs'].items()},
            'reports': {k: v for k, v in self.data['reports'].items()},
            'other': self.data['other'],
            'generated_at': datetime.now().isoformat()
        }
        
        return json.dumps(export_data, indent=2, default=str)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Inspect TransformationSystem DynamoDB table',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Full inspection
  python3 inspect_dynamodb_table.py
  
  # View specific journey
  python3 inspect_dynamodb_table.py --journey-id JRN-SAMPLE-001
  
  # Only show statistics
  python3 inspect_dynamodb_table.py --stats-only
  
  # Export as JSON
  python3 inspect_dynamodb_table.py --format json > table_data.json
  
  # With AWS profile
  AWS_PROFILE=external-access python3 inspect_dynamodb_table.py
        '''
    )
    
    parser.add_argument(
        '--journey-id',
        help='Show detailed information for a specific journey'
    )
    
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only show statistics, not detailed data'
    )
    
    args = parser.parse_args()
    
    try:
        print_with_flush('🔍 TransformationSystem Table Inspector')
        print_with_flush('=' * 80)
        
        # Setup AWS client
        print_with_flush('🔗 Connecting to DynamoDB...')
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from src.utils.aws_client_utils import create_aws_resource
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Using role ARN: {role_arn}')
            dynamodb = create_aws_resource('dynamodb', role_arn=role_arn)
        else:
            print_with_flush('🔑 Using default credential chain')
            profile = os.environ.get('AWS_PROFILE')
            if profile:
                print_with_flush(f'🔑 Using AWS profile: {profile}')
            dynamodb = boto3.resource('dynamodb')
        
        print_with_flush('✅ Connected to DynamoDB')
        print_with_flush('=' * 80)
        
        # Create inspector and scan table
        inspector = TableInspector(dynamodb)
        
        if not inspector.scan_table():
            sys.exit(1)
        
        # Output based on format and options
        if args.format == 'json':
            print_with_flush(inspector.export_as_json())
        else:
            # Display statistics
            inspector.display_statistics()
            
            # Display detailed data unless stats-only
            if not args.stats_only:
                if args.journey_id:
                    inspector.display_specific_journey(args.journey_id)
                else:
                    inspector.display_journeys()
            
            print_with_flush('\n' + '=' * 80)
            print_with_flush('✅ Inspection complete!')
            print_with_flush('=' * 80)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print_with_flush('\n⚠️  Inspection interrupted by user')
        sys.exit(1)
        
    except Exception as e:
        print_with_flush(f'\n❌ Unexpected error: {str(e)}')
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

