#!/usr/bin/env python3
"""
Test CLI Adapter - Runs CLI with test data injection
This allows BDD tests to inject test data that the CLI can see
"""

import os
import sys
import json
import tempfile
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


class TestCLIAdapter:
    """Adapter to run CLI with test data"""
    
    def __init__(self):
        self.test_data_file = None
        self.test_data = {
            'journeys': [],
            'stages': [],
            'rules': [],
            'jobs': []
        }
    
    def create_test_data_file(self) -> str:
        """Create a temporary file with test data"""
        if not self.test_data_file:
            fd, self.test_data_file = tempfile.mkstemp(suffix='.json', prefix='bdd_test_data_')
            os.close(fd)
        
        with open(self.test_data_file, 'w') as f:
            json.dump(self.test_data, f, indent=2, default=str)
        
        return self.test_data_file
    
    def add_journey(self, journey_data: Dict[str, Any]) -> str:
        """Add a journey to test data"""
        journey_id = journey_data.get('journeyId', f"JRN-TEST-{len(self.test_data['journeys'])+1:03d}")
        
        journey = {
            'journeyId': journey_id,
            'name': journey_data.get('name', 'Test Journey'),
            'description': journey_data.get('description', 'Test Description'),
            'status': journey_data.get('status', 'pending'),
            'priority': journey_data.get('priority', 'medium'),
            'odaComponentType': journey_data.get('odaComponentType', 'Customer Management'),
            'createdAt': journey_data.get('createdAt', '2025-01-01T00:00:00Z'),
            'updatedAt': journey_data.get('updatedAt', '2025-01-01T00:00:00Z'),
            'createdBy': journey_data.get('createdBy', 'test-user@example.com'),
            'overallProgress': journey_data.get('overallProgress', 0),
            'totalStages': journey_data.get('totalStages', 0),
            'completedStages': journey_data.get('completedStages', 0)
        }
        
        self.test_data['journeys'].append(journey)
        self.create_test_data_file()  # Update file
        return journey_id
    
    def add_stage(self, journey_id: str, stage_data: Dict[str, Any]) -> str:
        """Add a stage to test data"""
        stage_id = stage_data.get('stageId', f"STG-TEST-{len(self.test_data['stages'])+1:03d}")
        
        stage = {
            'journeyId': journey_id,
            'stageId': stage_id,
            'stageName': stage_data.get('stageName', 'Test Stage'),
            'description': stage_data.get('description', 'Test Stage Description'),
            'sequenceOrder': stage_data.get('sequenceOrder', 1),
            'status': stage_data.get('status', 'pending'),
            'enabled': stage_data.get('enabled', True)
        }
        
        self.test_data['stages'].append(stage)
        self.create_test_data_file()  # Update file
        return stage_id
    
    def get_environment_vars(self) -> Dict[str, str]:
        """Get environment variables for test mode"""
        env = os.environ.copy()
        
        # Set test mode flag
        env['CLI_TEST_MODE'] = 'true'
        env['TEST_DATA_FILE'] = self.create_test_data_file()
        
        # Use test AWS credentials to prevent real AWS calls
        env['AWS_ACCESS_KEY_ID'] = 'test'
        env['AWS_SECRET_ACCESS_KEY'] = 'test'
        env['AWS_DEFAULT_REGION'] = 'us-east-1'
        
        # Point to local/test endpoints if using LocalStack
        if os.environ.get('LOCALSTACK_ENDPOINT'):
            env['AWS_ENDPOINT_URL'] = os.environ.get('LOCALSTACK_ENDPOINT')
        
        return env
    
    def cleanup(self):
        """Clean up test data file"""
        if self.test_data_file and os.path.exists(self.test_data_file):
            try:
                os.unlink(self.test_data_file)
            except:
                pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def create_test_cli_wrapper():
    """Create a wrapper script that loads test data"""
    wrapper_content = '''#!/usr/bin/env python3
import os
import sys
import json

# Check if in test mode
if os.environ.get('CLI_TEST_MODE') == 'true':
    test_data_file = os.environ.get('TEST_DATA_FILE')
    if test_data_file and os.path.exists(test_data_file):
        # Load test data
        with open(test_data_file, 'r') as f:
            test_data = json.load(f)
        
        # Monkey-patch the CLI to use test data
        import journey_manager
        original_list = journey_manager.EnhancedJourneyManager.list_journeys_interactive
        
        def mock_list_journeys(self):
            """Mock list journeys to show test data"""
            print("\\n📋 Available Journeys (Test Mode):")
            print("="*80)
            
            for i, journey in enumerate(test_data.get('journeys', []), 1):
                print(f"{i}. [{journey['journeyId']}] {journey['name']}")
                print(f"   Status: {journey['status']} | Priority: {journey['priority']}")
                print(f"   Component: {journey['odaComponentType']}")
            
            if not test_data.get('journeys'):
                print("No journeys found in test data")
            
            print("="*80)
            input("Press Enter to continue...")
        
        journey_manager.EnhancedJourneyManager.list_journeys_interactive = mock_list_journeys

# Run the actual CLI
from journey_manager import main
main()
'''
    
    # Create wrapper file
    wrapper_path = tempfile.mktemp(suffix='.py', prefix='cli_wrapper_')
    with open(wrapper_path, 'w') as f:
        f.write(wrapper_content)
    
    return wrapper_path
