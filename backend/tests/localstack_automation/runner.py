"""
LocalStack Test Runner

Main orchestrator for LocalStack test automation.
Coordinates environment setup, test execution, report generation, and S3 upload.
"""

import argparse
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import (
    TestType, TestRunnerConfig, TestSuiteResult, TestRunResult, ReportInfo
)
from .localstack_manager import LocalStackManager
from .gateway_manager import GatewayManager
from .test_executor import TestExecutor
from .report_generator import LocalStackReportGenerator
from .s3_uploader import S3ReportUploader
from .logging_config import get_logger, TestAutomationLogger


class LocalStackTestRunner:
    """Main orchestrator for LocalStack test automation."""
    
    def __init__(self, config: TestRunnerConfig):
        """
        Initialize test runner with configuration.
        
        Args:
            config: TestRunnerConfig with all settings
        """
        self.config = config
        self.logger = get_logger()
        
        # Initialize components
        self.localstack = LocalStackManager(endpoint=config.localstack_endpoint)
        self.gateway = GatewayManager(server_url=config.gateway_url)
        self.executor = TestExecutor(
            server_url=config.gateway_url,
            output_dir=config.output_dir
        )
        self.report_generator = LocalStackReportGenerator(output_dir=config.output_dir)
        self.s3_uploader = S3ReportUploader(
            bucket_name=config.s3_bucket,
            endpoint_url=config.localstack_endpoint if not config.skip_localstack else None,
            region=config.s3_region
        )
        
        # Track state for cleanup
        self._localstack_started = False
        self._gateway_started = False
        self._shutdown_requested = False

    def run(self) -> TestRunResult:
        """
        Execute the complete test automation workflow.
        
        Returns:
            TestRunResult with all results and status
        """
        start_time = datetime.now()
        errors = []
        suite_results = {}
        reports_generated = []
        reports_uploaded = []
        
        TestAutomationLogger.log_step("Starting LocalStack Test Automation")
        
        try:
            # Setup environment
            if not self.setup_environment():
                errors.append("Environment setup failed")
                return self._create_result(
                    False, start_time, suite_results, 
                    reports_generated, reports_uploaded, errors
                )
            
            # Run tests
            suite_results = self.run_tests()
            
            # Generate reports
            reports_generated = self.generate_reports(suite_results)
            
            # Upload to S3 if requested
            if self.config.upload_to_s3 and reports_generated:
                reports_uploaded = self.upload_reports(reports_generated)
            
            # Determine success
            success = all(
                r.failed == 0 and r.errors == 0 
                for r in suite_results.values()
            )
            
            return self._create_result(
                success, start_time, suite_results,
                reports_generated, reports_uploaded, errors
            )
            
        except Exception as e:
            TestAutomationLogger.log_error(f"Test run failed: {e}")
            errors.append(str(e))
            return self._create_result(
                False, start_time, suite_results,
                reports_generated, reports_uploaded, errors
            )
        finally:
            if not self.config.keep_running:
                self.cleanup()
    
    def setup_environment(self) -> bool:
        """
        Start LocalStack and Gateway if needed.
        
        Returns:
            True if environment is ready, False otherwise
        """
        TestAutomationLogger.log_step("Setting up environment...")
        
        # Start LocalStack
        if not self.config.skip_localstack:
            if not self.localstack.start(timeout=self.config.localstack_timeout):
                TestAutomationLogger.log_error("Failed to start LocalStack")
                return False
            self._localstack_started = True
            
            # Initialize resources
            if not self.localstack.initialize_resources():
                TestAutomationLogger.log_warning("Resource initialization had issues")
        
        # Start Gateway
        if not self.config.skip_gateway:
            if not self.gateway.start(timeout=self.config.gateway_timeout):
                TestAutomationLogger.log_error("Failed to start Gateway")
                return False
            self._gateway_started = True
        
        TestAutomationLogger.log_success("Environment ready")
        return True

    def run_tests(self) -> Dict[str, TestSuiteResult]:
        """
        Execute selected test suites.
        
        Returns:
            Dictionary mapping test type to results
        """
        TestAutomationLogger.log_step("Running tests...")
        results = {}
        
        test_types = self.config.test_types
        if TestType.ALL in test_types:
            test_types = [TestType.INTEGRATION, TestType.BDD, TestType.ENDURANCE]
        
        for test_type in test_types:
            if self._shutdown_requested:
                break
                
            try:
                if test_type == TestType.INTEGRATION:
                    results['integration'] = self.executor.run_integration_tests()
                elif test_type == TestType.BDD:
                    results['bdd'] = self.executor.run_bdd_tests(tags=self.config.bdd_tags)
                elif test_type == TestType.ENDURANCE:
                    results['endurance'] = self.executor.run_endurance_tests(
                        duration_seconds=self.config.endurance_duration,
                        iterations=self.config.endurance_iterations
                    )
            except Exception as e:
                TestAutomationLogger.log_error(f"Error running {test_type.value} tests: {e}")
        
        return results
    
    def generate_reports(self, results: Dict[str, TestSuiteResult]) -> List[Path]:
        """
        Generate HTML reports from test results.
        
        Args:
            results: Dictionary of test results
            
        Returns:
            List of generated report paths
        """
        TestAutomationLogger.log_step("Generating reports...")
        report_paths = []
        report_infos = []
        
        for test_type, result in results.items():
            try:
                if test_type == 'integration':
                    path = self.report_generator.generate_integration_report(result)
                elif test_type == 'bdd':
                    path = self.report_generator.generate_bdd_report(result)
                elif test_type == 'endurance':
                    path = self.report_generator.generate_endurance_report(result)
                else:
                    continue
                
                report_paths.append(path)
                report_infos.append(ReportInfo(
                    test_type=result.test_type,
                    local_path=path,
                    total_tests=result.total,
                    passed_tests=result.passed,
                    failed_tests=result.failed
                ))
            except Exception as e:
                TestAutomationLogger.log_error(f"Error generating {test_type} report: {e}")
        
        # Generate index page
        if report_infos:
            try:
                index_path = self.report_generator.generate_index(report_infos)
                report_paths.append(index_path)
            except Exception as e:
                TestAutomationLogger.log_error(f"Error generating index: {e}")
        
        return report_paths
    
    def upload_reports(self, report_paths: List[Path]) -> List[str]:
        """
        Upload reports to S3.
        
        Args:
            report_paths: List of local report paths
            
        Returns:
            List of S3 URLs
        """
        TestAutomationLogger.log_step("Uploading reports to S3...")
        
        try:
            return self.s3_uploader.upload_reports(report_paths)
        except Exception as e:
            TestAutomationLogger.log_error(f"Error uploading reports: {e}")
            return []

    def cleanup(self) -> None:
        """Stop services and clean up resources."""
        TestAutomationLogger.log_step("Cleaning up...")
        
        # Stop Gateway
        if self._gateway_started:
            self.gateway.stop()
        
        # Stop LocalStack
        if self._localstack_started and self.config.cleanup:
            self.localstack.stop(remove_volumes=True)
        elif self._localstack_started and not self.config.keep_running:
            self.localstack.stop(remove_volumes=False)
        
        TestAutomationLogger.log_success("Cleanup complete")
    
    def _create_result(
        self,
        success: bool,
        start_time: datetime,
        suite_results: Dict[str, TestSuiteResult],
        reports_generated: List[Path],
        reports_uploaded: List[str],
        errors: List[str]
    ) -> TestRunResult:
        """Create TestRunResult from collected data."""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return TestRunResult(
            success=success,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            suite_results=suite_results,
            reports_generated=reports_generated,
            reports_uploaded=reports_uploaded,
            errors=errors
        )
    
    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown on SIGINT/SIGTERM."""
        if self._shutdown_requested:
            TestAutomationLogger.log_warning("Force quit. Resources may not be cleaned up.")
            sys.exit(1)
        
        TestAutomationLogger.log_warning("Shutdown requested. Cleaning up...")
        self._shutdown_requested = True
        self.cleanup()
        sys.exit(0)


def parse_arguments(args: Optional[List[str]] = None) -> TestRunnerConfig:
    """
    Parse command line arguments into TestRunnerConfig.
    
    Args:
        args: Command line arguments (defaults to sys.argv)
        
    Returns:
        TestRunnerConfig with parsed values
    """
    parser = argparse.ArgumentParser(
        description='LocalStack Test Automation Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python -m tests.localstack_automation.runner integration
  python -m tests.localstack_automation.runner bdd --tags smoke
  python -m tests.localstack_automation.runner all --upload
  python -m tests.localstack_automation.runner endurance --duration 300
        '''
    )
    
    # Test type selection
    parser.add_argument(
        'test_types',
        nargs='*',
        choices=['integration', 'bdd', 'endurance', 'all'],
        help='Test types to run (default: all)'
    )
    
    # Skip flags
    parser.add_argument(
        '--skip-localstack',
        action='store_true',
        help='Skip LocalStack startup (use existing instance)'
    )
    parser.add_argument(
        '--skip-gateway',
        action='store_true',
        help='Skip Gateway startup (use existing instance)'
    )
    
    # Upload flag
    parser.add_argument(
        '--upload',
        action='store_true',
        help='Upload reports to S3'
    )
    
    # Lifecycle flags
    parser.add_argument(
        '--keep-running',
        action='store_true',
        help='Keep services running after tests complete'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Remove LocalStack volumes after tests'
    )
    
    # Test configuration
    parser.add_argument(
        '--tags',
        type=str,
        help='Comma-separated BDD tags to filter'
    )
    parser.add_argument(
        '--duration',
        type=int,
        help='Endurance test duration in seconds'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        help='Endurance test iteration count'
    )
    
    # Output configuration
    parser.add_argument(
        '--output-dir',
        type=str,
        default='test_reports/localstack',
        help='Output directory for reports'
    )
    
    parsed = parser.parse_args(args)
    
    # Convert test types (default to 'all' if none specified)
    raw_types = parsed.test_types if parsed.test_types else ['all']
    test_types = []
    for t in raw_types:
        test_types.append(TestType(t))
    
    # Parse tags
    bdd_tags = None
    if parsed.tags:
        bdd_tags = [t.strip() for t in parsed.tags.split(',')]
    
    return TestRunnerConfig(
        test_types=test_types,
        skip_localstack=parsed.skip_localstack,
        skip_gateway=parsed.skip_gateway,
        upload_to_s3=parsed.upload,
        keep_running=parsed.keep_running,
        cleanup=parsed.cleanup,
        bdd_tags=bdd_tags,
        endurance_duration=parsed.duration,
        endurance_iterations=parsed.iterations,
        output_dir=Path(parsed.output_dir)
    )


def main():
    """Main entry point."""
    config = parse_arguments()
    runner = LocalStackTestRunner(config)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, runner.handle_shutdown)
    signal.signal(signal.SIGTERM, runner.handle_shutdown)
    
    # Run tests
    result = runner.run()
    
    # Print summary
    print("\n" + "=" * 60)
    if result.success:
        print("✅ TEST RUN PASSED")
    else:
        print("❌ TEST RUN FAILED")
    
    print(f"Duration: {result.duration:.1f}s")
    print(f"Total tests: {result.total_tests}")
    print(f"Passed: {result.total_passed}")
    print(f"Failed: {result.total_failed}")
    
    if result.reports_generated:
        print(f"\nReports: {result.reports_generated[0].parent}")
    
    if result.errors:
        print(f"\nErrors: {', '.join(result.errors)}")
    
    print("=" * 60)
    
    sys.exit(0 if result.success else 1)


if __name__ == '__main__':
    main()
