#!/usr/bin/env python3
"""
Cleanup Incomplete Journeys Script

This script deletes all journeys in the database that don't have exactly 6 stages.
This is useful for cleaning up test data and ensuring only properly configured journeys remain.

Usage:
    python3 cleanup_incomplete_journeys.py --dry-run          # Preview what would be deleted
    python3 cleanup_incomplete_journeys.py --confirm         # Actually delete the journeys
    python3 cleanup_incomplete_journeys.py --stages-count 4  # Delete journeys with specific stage count
"""

import boto3
import sys
import traceback
import json
import argparse
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any


def print_with_flush(message):
    """Print message and flush stdout immediately"""
    try:
        print(message)
        sys.stdout.flush()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except:
            pass


class JourneyCleanupManager:
    """Manager for cleaning up incomplete journeys"""
    
    def __init__(self, table_name: str = 'TransformationSystem'):
        """Initialize the cleanup manager"""
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        print_with_flush(f'🔧 Initialized JourneyCleanupManager with table: {table_name}')
        
        # Test table connection
        try:
            self.table.load()
            print_with_flush(f'✅ Connected to DynamoDB table: {table_name}')
        except Exception as e:
            print_with_flush(f'❌ Error connecting to table {table_name}: {str(e)}')
            print_with_flush(f'💡 Hint: Make sure the table exists and you have proper AWS credentials')
            raise
    
    def clean_journey_id(self, journey_id: str) -> str:
        """Clean and validate journey ID"""
        if not journey_id:
            raise ValueError("Journey ID cannot be empty")
        
        # Remove any whitespace
        clean_id = journey_id.strip()
        
        # Ensure it starts with JRN- if it doesn't already
        if not clean_id.startswith('JRN-'):
            clean_id = f'JRN-{clean_id}'
        
        return clean_id
    
    def list_journeys(self) -> List[Dict]:
        """List all journeys"""
        try:
            print_with_flush('📋 Listing all transformation journeys...')
            
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': 'JOURNEYS'
                }
            )
            
            journeys = []
            for item in response['Items']:
                journey_data = item['Data']
                journeys.append({
                    'journeyId': journey_data.get('journeyId'),
                    'name': journey_data.get('name'),
                    'description': journey_data.get('description'),
                    'status': journey_data.get('status'),
                    'priority': journey_data.get('priority'),
                    'odaComponentType': journey_data.get('odaComponentType'),
                    'overallProgress': journey_data.get('overallProgress', 0),
                    'createdAt': journey_data.get('createdAt'),
                    'lastUpdated': journey_data.get('lastUpdated')
                })
            
            print_with_flush(f'✅ Found {len(journeys)} journeys')
            return journeys
            
        except Exception as e:
            if 'ResourceNotFoundException' in str(e):
                print_with_flush(f'❌ Table {self.table_name} not found!')
                print_with_flush('💡 Hints:')
                print_with_flush('   • Make sure the DynamoDB table exists')
                print_with_flush('   • Run setup_dynamodb.py to create the table')
                print_with_flush('   • Check your AWS credentials and region')
            else:
                print_with_flush(f'❌ Error listing journeys: {str(e)}')
            return []
    
    def list_stages(self, journey_id: str) -> List[Dict]:
        """List all stages for a journey"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'JOURNEY#{clean_id}#STAGES'
                }
            )
            
            stages = []
            for item in response['Items']:
                stage_data = item['Data']
                stages.append({
                    'stageId': stage_data.get('stageId'),
                    'name': stage_data.get('name'),
                    'order': stage_data.get('order'),
                    'status': stage_data.get('status', 'pending')
                })
            
            # Sort by order
            stages.sort(key=lambda x: x.get('order', 0))
            return stages
            
        except Exception as e:
            print_with_flush(f'❌ Error listing stages for journey {journey_id}: {str(e)}')
            return []
    
    def delete_journey_complete(self, journey_id: str) -> bool:
        """Delete a complete journey including all stages, rules, and job history"""
        try:
            clean_id = self.clean_journey_id(journey_id)
            print_with_flush(f'🗑️ Deleting complete journey: {clean_id}')
            
            # Get all items for this journey
            response = self.table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'JOURNEY#{clean_id}'
                }
            )
            
            # Delete all items in batches
            items_deleted = 0
            for item in response['Items']:
                self.table.delete_item(
                    Key={
                        'PK': item['PK'],
                        'SK': item['SK']
                    }
                )
                items_deleted += 1
            
            print_with_flush(f'✅ Complete journey deleted: {clean_id}')
            print_with_flush(f'   🗑️ Deleted {items_deleted} items')
            return True
            
        except Exception as e:
            print_with_flush(f'❌ Error deleting journey: {str(e)}')
            traceback.print_exc()
            return False
    
    def cleanup_incomplete_journeys(self, expected_stages: int = 6, dry_run: bool = True) -> Dict[str, Any]:
        """
        Delete all journeys that don't have exactly the expected number of stages
        
        Args:
            expected_stages: Number of stages expected (default: 6)
            dry_run: If True, only show what would be deleted without actually deleting
            
        Returns:
            Dict with cleanup results
        """
        print_with_flush('🧹 Starting journey cleanup process...')
        print_with_flush(f'🎯 Target: Delete journeys with != {expected_stages} stages')
        print_with_flush(f'🔍 Mode: {"DRY RUN" if dry_run else "ACTUAL DELETION"}')
        print_with_flush('=' * 60)
        
        # Get all journeys
        journeys = self.list_journeys()
        if not journeys:
            print_with_flush('❌ No journeys found')
            return {'total_journeys': 0, 'journeys_to_delete': [], 'journeys_deleted': 0, 'journeys_kept': 0, 'errors': []}
        
        results = {
            'total_journeys': len(journeys),
            'journeys_to_delete': [],
            'journeys_deleted': 0,
            'journeys_kept': 0,
            'errors': []
        }
        
        # Check each journey
        for journey in journeys:
            journey_id = journey['journeyId']
            journey_name = journey.get('name', 'Unknown')
            
            try:
                # Get stages for this journey
                stages = self.list_stages(journey_id)
                stage_count = len(stages)
                
                print_with_flush(f'📊 Journey: {journey_id} ({journey_name})')
                print_with_flush(f'   📈 Stages: {stage_count}')
                
                if stage_count != expected_stages:
                    # Mark for deletion
                    journey_info = {
                        'journey_id': journey_id,
                        'name': journey_name,
                        'stage_count': stage_count,
                        'stages': [stage['stageId'] for stage in stages],
                        'status': journey.get('status', 'unknown'),
                        'created_at': journey.get('createdAt')
                    }
                    results['journeys_to_delete'].append(journey_info)
                    
                    if not dry_run:
                        # Actually delete the journey
                        if self.delete_journey_complete(journey_id):
                            results['journeys_deleted'] += 1
                            print_with_flush(f'   ✅ Deleted journey {journey_id}')
                        else:
                            results['errors'].append(f'Failed to delete journey {journey_id}')
                            print_with_flush(f'   ❌ Failed to delete journey {journey_id}')
                    else:
                        print_with_flush(f'   🔍 Would delete: {journey_id} (has {stage_count} stages)')
                else:
                    results['journeys_kept'] += 1
                    print_with_flush(f'   ✅ Keeping journey {journey_id} (has {stage_count} stages)')
                
            except Exception as e:
                error_msg = f'Error processing journey {journey_id}: {str(e)}'
                results['errors'].append(error_msg)
                print_with_flush(f'   ❌ {error_msg}')
        
        # Print summary
        print_with_flush('=' * 60)
        print_with_flush('🎯 CLEANUP SUMMARY')
        print_with_flush(f'📊 Total journeys found: {results["total_journeys"]}')
        print_with_flush(f'🗑️ Journeys to delete: {len(results["journeys_to_delete"])}')
        print_with_flush(f'✅ Journeys to keep: {results["journeys_kept"]}')
        
        if not dry_run:
            print_with_flush(f'🔥 Journeys actually deleted: {results["journeys_deleted"]}')
        
        if results['errors']:
            print_with_flush(f'❌ Errors encountered: {len(results["errors"])}')
            for error in results['errors']:
                print_with_flush(f'   • {error}')
        
        # Show details of journeys to delete
        if results['journeys_to_delete']:
            print_with_flush('')
            print_with_flush('📋 JOURNEYS TO DELETE:')
            for journey in results['journeys_to_delete']:
                print_with_flush(f'   🆔 {journey["journey_id"]} ({journey["name"]})')
                print_with_flush(f'      📈 Stages: {journey["stage_count"]} (expected: {expected_stages})')
                print_with_flush(f'      🏷️ Status: {journey["status"]}')
                if journey['stages']:
                    print_with_flush(f'      🎯 Stage IDs: {", ".join(journey["stages"])}')
                print_with_flush('')
        
        return results


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Cleanup incomplete journeys')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--confirm', action='store_true',
                       help='Actually delete the journeys (use with caution)')
    parser.add_argument('--stages-count', type=int, default=6,
                       help='Expected number of stages (default: 6)')
    parser.add_argument('--table-name', default='TransformationSystem',
                       help='DynamoDB table name (default: TransformationSystem)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.dry_run and not args.confirm:
        print_with_flush('❌ Error: You must specify either --dry-run or --confirm')
        print_with_flush('   Use --dry-run to preview what would be deleted')
        print_with_flush('   Use --confirm to actually delete the journeys')
        sys.exit(1)
    
    if args.confirm:
        print_with_flush('⚠️  DANGER: This will permanently delete journeys!')
        print_with_flush('   This operation cannot be undone.')
        response = input('Type "DELETE" (in capitals) to confirm: ')
        if response != 'DELETE':
            print_with_flush('❌ Operation cancelled')
            sys.exit(1)
    
    try:
        # Initialize the manager
        manager = JourneyCleanupManager(args.table_name)
        
        # Run the cleanup
        results = manager.cleanup_incomplete_journeys(
            expected_stages=args.stages_count,
            dry_run=args.dry_run
        )
        
        # Exit with appropriate code
        if results['errors']:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print_with_flush(f'❌ Fatal error: {str(e)}')
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main() 