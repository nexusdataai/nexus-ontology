#!/usr/bin/env python3
"""
Test runner for capability unit tests.

This script provides a convenient way to run all capability tests
with various options for coverage, filtering, and reporting.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def run_tests(args):
    """Run the tests with specified options."""
    # Base pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add test directory
    test_dir = Path(__file__).parent
    if args.test_file:
        cmd.append(str(test_dir / args.test_file))
    else:
        cmd.append(str(test_dir))
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage options
    if args.coverage:
        scripts_dir = project_root / "scripts" / "capability-scripts"
        cmd.extend([
            "--cov=" + str(scripts_dir),
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    # Add specific test filtering
    if args.filter:
        cmd.extend(["-k", args.filter])
    
    # Add markers
    if args.marker:
        cmd.extend(["-m", args.marker])
    
    # Show output
    if args.show_output:
        cmd.append("-s")
    
    # Stop on first failure
    if args.fail_fast:
        cmd.append("-x")
    
    # Show local variables in tracebacks
    if args.show_locals:
        cmd.append("-l")
    
    # Run tests in parallel
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])
    
    # Add any extra pytest arguments
    if args.pytest_args:
        cmd.extend(args.pytest_args.split())
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 60)
    
    # Run the tests
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run capability unit tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests with coverage
  python run_tests.py --coverage
  
  # Run specific test file
  python run_tests.py test_manage_capability.py
  
  # Run tests matching pattern
  python run_tests.py -k "test_create"
  
  # Run tests with specific marker
  python run_tests.py -m "slow"
  
  # Run tests in parallel (requires pytest-xdist)
  python run_tests.py --parallel 4
        """
    )
    
    parser.add_argument(
        "test_file",
        nargs="?",
        help="Specific test file to run (e.g., test_manage_capability.py)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    
    parser.add_argument(
        "-k", "--filter",
        help="Only run tests matching expression"
    )
    
    parser.add_argument(
        "-m", "--marker",
        help="Only run tests with marker"
    )
    
    parser.add_argument(
        "-s", "--show-output",
        action="store_true",
        help="Show print statements"
    )
    
    parser.add_argument(
        "-x", "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "-l", "--show-locals",
        action="store_true",
        help="Show local variables in tracebacks"
    )
    
    parser.add_argument(
        "-p", "--parallel",
        type=int,
        metavar="N",
        help="Run tests in N parallel processes"
    )
    
    parser.add_argument(
        "--pytest-args",
        help="Additional pytest arguments (as a single string)"
    )
    
    args = parser.parse_args()
    
    # Run the tests
    exit_code = run_tests(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
