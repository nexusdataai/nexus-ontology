#!/usr/bin/env python3
"""
Behave environment setup for BDD testing
Configures test environment, AWS mocks, and test data
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tests.bdd.support.cli_wrapper import JourneyManagerCLI
from tests.bdd.support.test_data_manager import TestDataManager
from tests.bdd.support.aws_mock_manager import AWSMockManager


def before_all(context):
    """Set up test environment before all tests"""
    print("\n" + "="*80)
    print("Setting up BDD test environment...")
    print("="*80 + "\n")
    
    # Create temp directory for test outputs
    context.test_output_dir = tempfile.mkdtemp(prefix='bdd_test_')
    print(f"Test output directory: {context.test_output_dir}")
    
    # API-based test configuration
    context.base_url = os.getenv('SERVER_URL', 'http://localhost:8000')
    context.mcp_server_url = context.base_url  # Alias for consistency
    context.api_key = os.getenv('API_KEY', 'super-secret')
    
    # Set test journey and job IDs from environment or use defaults
    context.test_journey_id = os.getenv('TEST_JOURNEY_ID', 'JRN-TEST-001')
    context.test_job_id = os.getenv('TEST_JOB_ID', 'JOB-TEST-001')
    
    # Verify backend service is accessible
    import requests
    try:
        response = requests.get(f"{context.base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Backend service accessible at {context.base_url}")
        else:
            print(f"⚠️ Backend service responded with status {response.status_code}")
    except Exception as e:
        print(f"⚠️ Backend service check failed: {e}")
        print(f"   Tests will fail if service is not running")
    
    # Set AWS region
    context.aws_region = context.config.userdata.get('aws_region', 'us-east-1')
    
    # Initialize AWS mock manager (for CLI tests if needed)
    context.aws_mock_manager = AWSMockManager(context.aws_region)
    

def after_all(context):
    """Clean up test environment after all tests"""
    print("\n" + "="*80)
    print("Cleaning up BDD test environment...")
    print("="*80 + "\n")
    
    # Clean up temp directory
    if hasattr(context, 'test_output_dir') and os.path.exists(context.test_output_dir):
        shutil.rmtree(context.test_output_dir)
        print(f"Cleaned up test output directory")
    

def before_scenario(context, scenario):
    """Set up for each scenario"""
    print(f"\n>>> Starting scenario: {scenario.name}")
    print(f"    Tags: {scenario.tags}")
    print(f"    Feature: {scenario.feature.name}\n")
    
    # Check if this is a live test (uses real AWS/Webex services)
    is_live_test = 'live' in scenario.tags
    
    if is_live_test:
        # Live test setup - no mocking, use real services
        print("    Mode: LIVE test (real services)")
        context.is_live = True
        context.test_journey_ids = []
        context.response = None
        context.response_data = None
        
        # Check if live tests are allowed
        if not os.getenv('BEHAVE_RUN_LIVE', 'false').lower() == 'true':
            scenario.skip("Live tests disabled. Set BEHAVE_RUN_LIVE=true to enable.")
            return
        return
    
    # Check if this is an API-based test (new style) or CLI-based (old style)
    is_api_test = 'api' in scenario.tags
    
    if is_api_test:
        # API-based test setup (new approach)
        print("    Mode: API-based test")
        context.test_journey_ids = []
        context.test_stage_ids = []
        context.test_rule_ids = []
        context.last_journey_id = None
        context.response = None
        context.response_data = None
    else:
        # CLI-based test setup (old approach)
        print("    Mode: CLI-based test")
        
        # Start AWS mocks
        context.aws_mock_manager.setup_environment_variables()
        context.aws_mock_manager.start_all_mocks()
        
        # Initialize test data manager
        context.test_data = TestDataManager(context.aws_region)
        context.test_data.setup_test_tables()
        
        # Create CLI wrapper
        context.cli = JourneyManagerCLI(timeout=30)
        
        # Initialize test data tracking
        context.test_journey_id = None
        context.test_stage_id = None
        context.test_rule_id = None
        context.test_job_id = None
        context.current_journey_id = None
        context.current_menu = "main"
        
        # Track if CLI was started
        context.cli_started = False
    
    # Create scenario-specific output directory
    scenario_name = scenario.name.replace(' ', '_').lower()[:50]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    context.scenario_output_dir = os.path.join(
        context.test_output_dir, 
        f"{scenario_name}_{timestamp}"
    )
    os.makedirs(context.scenario_output_dir, exist_ok=True)
    

def after_scenario(context, scenario):
    """Clean up after each scenario"""
    print(f"\n>>> Completed scenario: {scenario.name}")
    print(f"    Status: {scenario.status}")
    
    # Skip cleanup for live tests (they manage their own resources)
    is_live_test = 'live' in scenario.tags
    if is_live_test:
        print("    Mode: LIVE test cleanup (minimal)")
        return
    
    # Cleanup test data for API tests
    is_api_test = 'api' in scenario.tags
    if is_api_test and hasattr(context, 'test_journey_ids'):
        import requests
        for journey_id in context.test_journey_ids:
            try:
                payload = {
                    "arguments": {
                        "action": "delete",
                        "journeyId": journey_id
                    }
                }
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": context.api_key
                }
                requests.post(
                    f"{context.base_url}/tools/journeys_tool",
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                print(f"    Cleaned up test journey: {journey_id}")
            except Exception as e:
                print(f"    Warning: Could not cleanup journey {journey_id}: {e}")
    
    # Stop CLI if running (for old CLI-based tests)
    if hasattr(context, 'cli') and context.cli_started:
        try:
            context.cli.stop()
            print("    CLI stopped successfully")
        except Exception as e:
            print(f"    Warning: Error stopping CLI: {e}")
    
    # Clean up test data
    if hasattr(context, 'test_data'):
        try:
            context.test_data.cleanup()
            print("    Test data cleaned up")
        except Exception as e:
            print(f"    Warning: Error cleaning test data: {e}")
    
    # Stop AWS mocks
    if hasattr(context, 'aws_mock_manager'):
        context.aws_mock_manager.cleanup_resources()
        context.aws_mock_manager.stop_all_mocks()
        context.aws_mock_manager.clear_environment_variables()
        print("    AWS mocks stopped")
    
    # Save scenario output if failed
    if scenario.status == 'failed' and hasattr(context, 'cli'):
        try:
            failure_log = os.path.join(
                context.scenario_output_dir,
                'failure_output.txt'
            )
            context.cli.save_output_to_file(failure_log)
            print(f"    Failure output saved to: {failure_log}")
        except:
            pass
    
    print()


def before_step(context, step):
    """Before each step execution"""
    # Optionally log step execution
    if context.config.userdata.get('debug_steps', False):
        print(f"  >> Executing: {step.step_type} {step.name}")


def after_step(context, step):
    """After each step execution"""
    if step.status == 'failed':
        # Capture CLI output on failure
        if hasattr(context, 'cli'):
            try:
                output = context.cli.get_current_output()
                print(f"\n  !! Step failed: {step.name}")
                print(f"  !! CLI Output:\n{output[-500:]}")  # Last 500 chars
            except:
                pass
    elif context.config.userdata.get('debug_steps', False):
        print(f"  << Completed: {step.name} [{step.status}]")


def before_tag(context, tag):
    """Handle specific tags"""
    if tag == '@slow':
        # Increase timeout for slow scenarios
        if hasattr(context, 'cli'):
            context.cli.timeout = 60
    elif tag == '@skip':
        # Skip scenarios marked with @skip
        scenario.skip("Marked with @skip")


# Hooks for specific features

def before_feature(context, feature):
    """Set up before a feature file"""
    print(f"\n" + "="*80)
    print(f"Feature: {feature.name}")
    print(f"File: {feature.filename}")
    print("="*80 + "\n")
    
    # Feature-specific setup
    if 'journey_management' in feature.filename:
        # Pre-create some test data for journey management tests
        pass
    elif 'stage_management' in feature.filename:
        # Ensure a test journey exists for stage tests
        pass


def after_feature(context, feature):
    """Clean up after a feature file"""
    print(f"\n" + "-"*80)
    print(f"Completed feature: {feature.name}")
    print(f"Scenarios run: {len(feature.scenarios)}")
    passed = sum(1 for s in feature.scenarios if s.status == 'passed')
    failed = sum(1 for s in feature.scenarios if s.status == 'failed')
    print(f"Passed: {passed}, Failed: {failed}")
    print("-"*80 + "\n")
