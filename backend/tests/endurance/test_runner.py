#!/usr/bin/env python3
"""
Simple test runner to debug BDD endurance tests
"""

import subprocess
import sys
import time
from pathlib import Path

def run_single_bdd_test():
    """Run a single BDD test to see what happens"""
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    features_dir = project_root / "tests" / "bdd" / "features" / "journey"
    
    print("=" * 80)
    print("TESTING BDD EXECUTION")
    print("=" * 80)
    print(f"Project root: {project_root}")
    print(f"Features dir: {features_dir}")
    print(f"Features exist: {features_dir.exists()}")
    
    if features_dir.exists():
        feature_files = list(features_dir.glob("*.feature"))
        print(f"Found {len(feature_files)} feature files")
        for f in feature_files:
            print(f"  - {f.name}")
    
    print("\nTrying to run a simple behave test...")
    print("-" * 40)
    
    # Try to run behave with a specific feature
    feature_file = features_dir / "journey_management.feature"
    
    cmd = [
        sys.executable, '-m', 'behave',
        str(feature_file),
        '--dry-run',  # Just parse, don't execute
        '--no-capture',
        '--tags=@journey,@create',
        '--format', 'pretty'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print("-" * 40)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(project_root)
        )
        
        print(f"Return code: {result.returncode}")
        print(f"\nStdout:\n{result.stdout[:1000]}")
        if result.stderr:
            print(f"\nStderr:\n{result.stderr[:1000]}")
            
    except subprocess.TimeoutExpired:
        print("ERROR: Test timed out")
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n" + "=" * 80)
    print("Now trying actual test execution (not dry run)...")
    print("=" * 80)
    
    # Try to actually run a test
    cmd = [
        sys.executable, '-m', 'behave',
        str(feature_file),
        '--no-capture',
        '--tags=@journey',
        '--format', 'json',
        '-n', '"Create a new journey successfully"'  # Specific scenario
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print("-" * 40)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(project_root)
        )
        
        print(f"Return code: {result.returncode}")
        print(f"\nOutput (first 2000 chars):\n{result.stdout[:2000]}")
        if result.stderr:
            print(f"\nErrors:\n{result.stderr[:1000]}")
            
    except subprocess.TimeoutExpired:
        print("ERROR: Test timed out after 30 seconds")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    run_single_bdd_test()
