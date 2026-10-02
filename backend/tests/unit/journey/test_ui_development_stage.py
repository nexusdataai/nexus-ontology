#!/usr/bin/env python3
"""
Test Script for UI Development Stage

This script demonstrates how to use the UI Development stage
to automate UI development with planning, development, testing, and deployment.
"""

import os
import sys
import json
import importlib.util
from datetime import datetime

# Add parent directory to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# Since the directory has a dash, we need to import differently
spec = importlib.util.spec_from_file_location(
    "ui_development", 
    os.path.join(project_root, "src/stages/ui-development/ui_development.py")
)
ui_development = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_development)
UIDevelopmentStage = ui_development.UIDevelopmentStage


def test_ui_development_stage():
    """Test the UI development stage with all 4 steps"""
    
    print("=" * 80)
    print("TESTING UI DEVELOPMENT STAGE")
    print("=" * 80)
    
    # Create test parameters
    journey_id = "JRN-UI-TEST-001"
    stage_id = "ui_development"
    job_id = f"JOB-UI-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"\nTest Parameters:")
    print(f"  Journey ID: {journey_id}")
    print(f"  Stage ID: {stage_id}")
    print(f"  Job ID: {job_id}")
    
    # Initialize the stage
    print(f"\n🚀 Initializing UI Development Stage...")
    stage = UIDevelopmentStage(
        journey_id=journey_id,
        stage_id=stage_id,
        job_id=job_id,
        region_name='us-east-1'
    )
    
    # Execute each step
    steps = stage.steps
    
    for step in steps:
        print(f"\n{'=' * 60}")
        print(f"Step {step['order'] + 1}: {step['name']}")
        print(f"Description: {step['description']}")
        print(f"Estimated Duration: {step['estimatedDuration']}")
        print(f"{'=' * 60}")
        
        step_data = {}
        
        try:
            print(f"\n🔄 Executing step: {step['id']}...")
            result = stage.execute_step(step['id'], step_data)
            
            print(f"\n✅ Step Result:")
            print(f"  Status: {result.get('status')}")
            print(f"  Summary: {result.get('summary')}")
            
            # Show metrics if available
            if result.get('metrics'):
                print(f"\n📊 Metrics:")
                for key, value in result['metrics'].items():
                    print(f"    • {key}: {value}")
            
            # Show artifacts if available
            if result.get('artifacts'):
                print(f"\n📦 Artifacts Generated:")
                for artifact_name in result['artifacts'].keys():
                    print(f"    • {artifact_name}")
            
            # Stop if step failed
            if result.get('status') == 'failed':
                print(f"\n❌ Step failed: {result.get('error')}")
                break
                
        except Exception as e:
            print(f"\n❌ Error executing step: {str(e)}")
            break
    
    print(f"\n{'=' * 80}")
    print("TEST COMPLETED")
    print(f"{'=' * 80}")


def test_planning_only():
    """Test just the planning phase"""
    
    print("\n" + "=" * 80)
    print("TESTING PLANNING PHASE ONLY")
    print("=" * 80)
    
    # Create minimal stage instance
    stage = UIDevelopmentStage(
        journey_id="TEST",
        stage_id="test",
        job_id="TEST-PLAN-001"
    )
    
    print("\n📝 Testing Planning Phase...")
    
    try:
        result = stage.execute_step('planning', {})
        
        print(f"\n✅ Planning Result:")
        print(f"  Status: {result.get('status')}")
        print(f"  Summary: {result.get('summary')}")
        
        if result.get('status') == 'completed':
            print(f"\n📄 Documents Created:")
            for doc in result.get('documents_created', []):
                print(f"    • {doc}")
            
            if result.get('metrics'):
                print(f"\n📊 Metrics:")
                for key, value in result['metrics'].items():
                    print(f"    • {key}: {value}")
        
    except Exception as e:
        print(f"\n❌ Error in planning phase: {str(e)}")


def test_with_custom_specs():
    """Test with custom specification content"""
    
    print("\n" + "=" * 80)
    print("TESTING WITH CUSTOM SPECIFICATIONS")
    print("=" * 80)
    
    # Create stage instance
    stage = UIDevelopmentStage(
        journey_id="CUSTOM-TEST",
        stage_id="ui_development",
        job_id=f"CUSTOM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    
    # Custom specification data
    custom_spec_data = {
        'boilerplate_repo': 'https://github.com/your-org/react-template',
        'target_repo': 'https://github.com/your-org/custom-ui-app',
        'app_name': 'Custom Alert System',
        'features': [
            'Real-time monitoring dashboard',
            'Alert correlation engine',
            'Automated remediation workflows',
            'Multi-tenant support'
        ]
    }
    
    print(f"\nCustom Specification:")
    print(json.dumps(custom_spec_data, indent=2))
    
    # Execute planning with custom data
    print("\n📝 Executing Planning with custom specs...")
    
    try:
        result = stage.execute_step('planning', {'custom_spec': custom_spec_data})
        
        print(f"\n✅ Result:")
        print(f"  Status: {result.get('status')}")
        print(f"  Summary: {result.get('summary')}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def show_stage_info():
    """Show information about the UI Development stage"""
    
    print("\n" + "=" * 80)
    print("UI DEVELOPMENT STAGE INFORMATION")
    print("=" * 80)
    
    # Create stage instance
    stage = UIDevelopmentStage(
        journey_id="INFO",
        stage_id="ui_development",
        job_id="INFO-001"
    )
    
    print(f"\nStage Name: {stage.stage_name}")
    print(f"Description: {stage.stage_description}")
    
    print(f"\n📋 Stage Steps ({len(stage.steps)}):")
    for i, step in enumerate(stage.steps, 1):
        print(f"\n  {i}. {step['name']}")
        print(f"     ID: {step['id']}")
        print(f"     Description: {step['description']}")
        print(f"     Estimated Duration: {step['estimatedDuration']}")
    
    print(f"\n🔧 Configuration:")
    print(f"  Claude API: {'Configured' if stage.claude_api_key else 'Not Configured (REQUIRED)'}")
    print(f"  GitHub Token: {'Configured' if stage.github_token else 'Not Configured'}")
    print(f"  AWS Account: {'Configured' if stage.aws_account_id else 'Not Configured'}")
    
    print(f"\n📁 Working Directory: {stage.work_dir}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test UI Development Stage')
    parser.add_argument(
        '--planning-only',
        action='store_true',
        help='Test only the planning phase'
    )
    parser.add_argument(
        '--custom-spec',
        action='store_true',
        help='Test with custom specifications'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Show stage information only'
    )
    
    args = parser.parse_args()
    
    if args.info:
        show_stage_info()
    elif args.planning_only:
        test_planning_only()
    elif args.custom_spec:
        test_with_custom_specs()
    else:
        test_ui_development_stage()
    
    print("\n✅ Test script completed!")
