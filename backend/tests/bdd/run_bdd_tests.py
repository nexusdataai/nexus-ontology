#!/usr/bin/env python3
"""
BDD Test Runner for Journey Manager CLI
Provides enhanced test execution with reporting and CI/CD integration
"""

import os
import sys
import argparse
import subprocess
import json
from datetime import datetime
import shutil
from typing import List, Optional, Dict, Any


class BDDTestRunner:
    """Enhanced test runner for BDD tests with reporting"""
    
    def __init__(self, features_dir: str = "features"):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.abspath(os.path.join(self.script_dir, "../.."))
        self.features_dir = os.path.join(self.script_dir, "features") if not os.path.isabs(features_dir) else features_dir
        self.reports_dir = os.path.join(self.project_root, "test_reports")
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def setup_reports_directory(self) -> str:
        """Set up directory for test reports"""
        report_path = os.path.join(self.reports_dir, f"bdd_{self.timestamp}")
        os.makedirs(report_path, exist_ok=True)
        return report_path
        
    def run_tests(self, 
                  tags: Optional[List[str]] = None,
                  features: Optional[List[str]] = None,
                  parallel: bool = False,
                  dry_run: bool = False,
                  format_type: str = "pretty",
                  stop_on_failure: bool = False) -> int:
        """Run BDD tests with specified options
        
        Args:
            tags: List of tags to include/exclude
            features: Specific feature files to run
            parallel: Run tests in parallel
            dry_run: Only parse features, don't run
            format_type: Output format (pretty, json, junit)
            stop_on_failure: Stop on first failure
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        report_path = self.setup_reports_directory()
        
        # Build behave command
        cmd = [sys.executable, "-m", "behave"]
        
        # Add format options
        if format_type == "json":
            json_output = os.path.join(report_path, "results.json")
            cmd.extend(["-f", "json", "-o", json_output])
        elif format_type == "junit":
            junit_output = os.path.join(report_path, "junit")
            cmd.extend(["-f", "junit", "-o", junit_output])
        else:
            cmd.extend(["-f", "pretty"])
            
        # Also add pretty format for console output if using other formats
        if format_type != "pretty":
            cmd.extend(["-f", "pretty"])
        
        # Add tags
        if tags:
            for tag in tags:
                if tag.startswith("~"):
                    cmd.extend(["--tags", f"{tag}"])
                else:
                    cmd.extend(["--tags", f"@{tag}"])
        
        # Add stop on failure
        if stop_on_failure:
            cmd.append("--stop")
            
        # Add dry run
        if dry_run:
            cmd.append("--dry-run")
        
        # Add specific features or use features directory
        if features:
            for feature in features:
                feature_path = os.path.join(self.features_dir, feature)
                if not feature.endswith('.feature'):
                    feature_path += '.feature'
                cmd.append(feature_path)
        else:
            cmd.append(self.features_dir)
        
        # Add additional options for better output
        cmd.extend([
            "--no-capture",  # Don't capture stdout
            "--no-capture-stderr",  # Don't capture stderr
            "-v"  # Verbose
        ])
        
        print(f"\nRunning BDD tests...")
        print(f"Command: {' '.join(cmd)}")
        print(f"Reports directory: {report_path}\n")
        
        # Run tests
        if parallel:
            return self.run_parallel_tests(cmd, report_path)
        else:
            result = subprocess.run(cmd, cwd=os.getcwd())
            
            # Generate HTML report if json output exists
            if format_type == "json":
                self.generate_html_report(json_output, report_path)
                
            return result.returncode
    
    def run_parallel_tests(self, base_cmd: List[str], report_path: str) -> int:
        """Run tests in parallel using behave-parallel"""
        print("Running tests in parallel mode...")
        
        # Modify command for parallel execution
        # Note: This requires behave-parallel to be installed
        parallel_cmd = base_cmd.copy()
        parallel_cmd[2] = "behave-parallel"  # Replace 'behave' with 'behave-parallel'
        parallel_cmd.extend(["--processes", "4"])  # Use 4 parallel processes
        
        try:
            result = subprocess.run(parallel_cmd, cwd=os.getcwd())
            return result.returncode
        except FileNotFoundError:
            print("Warning: behave-parallel not found. Install with: pip install behave-parallel")
            print("Falling back to sequential execution...")
            result = subprocess.run(base_cmd, cwd=os.getcwd())
            return result.returncode
    
    def generate_html_report(self, json_file: str, report_path: str) -> None:
        """Generate HTML report from JSON results"""
        if not os.path.exists(json_file):
            print("No JSON results found, skipping HTML report generation")
            return
            
        try:
            with open(json_file, 'r') as f:
                results = json.load(f)
            
            # Generate simple HTML report
            html_file = os.path.join(report_path, "report.html")
            self.create_html_report(results, html_file)
            print(f"\nHTML report generated: {html_file}")
            
        except Exception as e:
            print(f"Error generating HTML report: {e}")
    
    def create_html_report(self, results: List[Dict[str, Any]], output_file: str) -> None:
        """Create HTML report from test results"""
        total_scenarios = 0
        passed_scenarios = 0
        failed_scenarios = 0
        
        features_html = []
        
        for feature in results:
            feature_scenarios = 0
            feature_passed = 0
            feature_failed = 0
            
            scenarios_html = []
            
            for element in feature.get('elements', []):
                if element['type'] == 'scenario':
                    feature_scenarios += 1
                    total_scenarios += 1
                    
                    scenario_passed = all(
                        step.get('result', {}).get('status') == 'passed'
                        for step in element.get('steps', [])
                    )
                    
                    if scenario_passed:
                        feature_passed += 1
                        passed_scenarios += 1
                        status_class = 'passed'
                    else:
                        feature_failed += 1
                        failed_scenarios += 1
                        status_class = 'failed'
                    
                    steps_html = []
                    for step in element.get('steps', []):
                        step_status = step.get('result', {}).get('status', 'undefined')
                        step_html = f'''
                        <div class="step {step_status}">
                            <span class="keyword">{step.get('keyword', '')}</span>
                            <span class="name">{step.get('name', '')}</span>
                            <span class="status">{step_status}</span>
                        </div>
                        '''
                        steps_html.append(step_html)
                    
                    scenario_html = f'''
                    <div class="scenario {status_class}">
                        <h4>{element.get('name', 'Unnamed Scenario')}</h4>
                        <div class="steps">
                            {''.join(steps_html)}
                        </div>
                    </div>
                    '''
                    scenarios_html.append(scenario_html)
            
            feature_html = f'''
            <div class="feature">
                <h3>{feature.get('name', 'Unnamed Feature')}</h3>
                <div class="feature-stats">
                    Scenarios: {feature_scenarios} | 
                    Passed: {feature_passed} | 
                    Failed: {feature_failed}
                </div>
                <div class="scenarios">
                    {''.join(scenarios_html)}
                </div>
            </div>
            '''
            features_html.append(feature_html)
        
        # Create complete HTML
        html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <title>BDD Test Report - {self.timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #333; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; padding: 15px; background: #f0f0f0; border-radius: 5px; }}
        .feature {{ margin: 20px 0; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
        .scenario {{ margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 3px; }}
        .scenario.passed {{ border-left: 4px solid #4CAF50; }}
        .scenario.failed {{ border-left: 4px solid #F44336; }}
        .step {{ margin: 5px 0; padding: 5px; }}
        .step.passed {{ color: #4CAF50; }}
        .step.failed {{ color: #F44336; }}
        .step.undefined {{ color: #FF9800; }}
        .keyword {{ font-weight: bold; }}
        .status {{ float: right; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>BDD Test Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Scenarios: {total_scenarios}</p>
        <p>Passed: {passed_scenarios}</p>
        <p>Failed: {failed_scenarios}</p>
        <p>Success Rate: {(passed_scenarios/total_scenarios*100 if total_scenarios > 0 else 0):.1f}%</p>
    </div>
    
    <div class="features">
        <h2>Features</h2>
        {''.join(features_html)}
    </div>
</body>
</html>
        '''
        
        with open(output_file, 'w') as f:
            f.write(html_content)
    
    def run_specific_scenario(self, feature: str, scenario_name: str) -> int:
        """Run a specific scenario by name"""
        cmd = [
            sys.executable, "-m", "behave",
            "-n", scenario_name,
            os.path.join(self.features_dir, f"{feature}.feature")
        ]
        
        result = subprocess.run(cmd)
        return result.returncode
    
    def list_features(self) -> List[str]:
        """List all available feature files"""
        features = []
        for file in os.listdir(self.features_dir):
            if file.endswith('.feature'):
                features.append(file[:-8])  # Remove .feature extension
        return sorted(features)
    
    def list_scenarios(self, feature: str) -> List[str]:
        """List all scenarios in a feature file"""
        feature_path = os.path.join(self.features_dir, f"{feature}.feature")
        scenarios = []
        
        try:
            with open(feature_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('Scenario:'):
                        scenario_name = line[9:].strip()
                        scenarios.append(scenario_name)
        except FileNotFoundError:
            print(f"Feature file not found: {feature}")
            
        return scenarios


def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(description='Run BDD tests for Journey Manager CLI')
    
    parser.add_argument('--tags', '-t', nargs='+', 
                       help='Tags to include (use ~tag to exclude)')
    parser.add_argument('--features', '-f', nargs='+',
                       help='Specific features to run')
    parser.add_argument('--scenario', '-s',
                       help='Run specific scenario (requires --feature)')
    parser.add_argument('--feature', 
                       help='Feature file for specific scenario')
    parser.add_argument('--parallel', '-p', action='store_true',
                       help='Run tests in parallel')
    parser.add_argument('--dry-run', '-d', action='store_true',
                       help='Only parse features, do not run')
    parser.add_argument('--format', choices=['pretty', 'json', 'junit'],
                       default='pretty', help='Output format')
    parser.add_argument('--stop-on-failure', action='store_true',
                       help='Stop on first failure')
    parser.add_argument('--list-features', action='store_true',
                       help='List all available features')
    parser.add_argument('--list-scenarios', 
                       help='List scenarios for a feature')
    
    args = parser.parse_args()
    
    runner = BDDTestRunner()
    
    # Handle listing operations
    if args.list_features:
        print("\nAvailable features:")
        for feature in runner.list_features():
            print(f"  - {feature}")
        return 0
        
    if args.list_scenarios:
        print(f"\nScenarios in {args.list_scenarios}:")
        for scenario in runner.list_scenarios(args.list_scenarios):
            print(f"  - {scenario}")
        return 0
    
    # Handle specific scenario execution
    if args.scenario:
        if not args.feature:
            print("Error: --scenario requires --feature")
            return 1
        return runner.run_specific_scenario(args.feature, args.scenario)
    
    # Run tests with specified options
    return runner.run_tests(
        tags=args.tags,
        features=args.features,
        parallel=args.parallel,
        dry_run=args.dry_run,
        format_type=args.format,
        stop_on_failure=args.stop_on_failure
    )


if __name__ == '__main__':
    sys.exit(main())
