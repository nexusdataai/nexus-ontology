"""
Test Executor

Executes different types of tests (integration, BDD, endurance) and collects results.
"""

import subprocess
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .logging_config import get_logger, TestAutomationLogger
from .models import TestType, TestSuiteResult, TestCaseResult


class TestExecutor:
    """Executes test suites and collects results."""
    
    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        output_dir: Optional[Path] = None,
        project_root: Optional[Path] = None
    ):
        """
        Initialize test executor.
        
        Args:
            server_url: Gateway server URL for tests
            output_dir: Directory for test output files
            project_root: Project root directory
        """
        self.server_url = server_url
        self.logger = get_logger()
        
        # Determine project root
        if project_root:
            self.project_root = Path(project_root)
        else:
            self.project_root = Path(__file__).parent.parent.parent
        
        # Set output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.project_root / "test_reports" / "localstack"
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Test directories
        self.tests_dir = self.project_root / "tests"
        self.integration_dir = self.tests_dir / "integration"
        self.bdd_dir = self.tests_dir / "bdd"
        self.endurance_dir = self.tests_dir / "endurance"
    
    def run_integration_tests(self) -> TestSuiteResult:
        """
        Run pytest integration tests.
        
        Returns:
            TestSuiteResult with test results
        """
        TestAutomationLogger.log_step("Running integration tests...")
        
        start_time = datetime.now()
        json_output = self.output_dir / "integration_results.json"
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.integration_dir),
            f"--json-report",
            f"--json-report-file={json_output}",
            "-v",
            "--tb=short"
        ]
        
        # Set environment for LocalStack
        env = self._get_test_env()
        
        try:
            self.logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                env=env,
                timeout=600  # 10 minute timeout
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Parse results
            if json_output.exists():
                return self._parse_pytest_results(json_output, start_time, end_time)
            else:
                # Fallback: parse from output
                return self._create_result_from_output(
                    TestType.INTEGRATION,
                    result.returncode,
                    result.stdout,
                    result.stderr,
                    start_time,
                    end_time
                )
                
        except subprocess.TimeoutExpired:
            end_time = datetime.now()
            TestAutomationLogger.log_error("Integration tests timed out")
            return self._create_error_result(
                TestType.INTEGRATION,
                "Test execution timed out",
                start_time,
                end_time
            )
        except Exception as e:
            end_time = datetime.now()
            TestAutomationLogger.log_error(f"Integration tests failed: {e}")
            return self._create_error_result(
                TestType.INTEGRATION,
                str(e),
                start_time,
                end_time
            )
    
    def run_bdd_tests(self, tags: Optional[List[str]] = None) -> TestSuiteResult:
        """
        Run behave BDD tests with optional tag filtering.
        
        Args:
            tags: Optional list of tags to filter tests
            
        Returns:
            TestSuiteResult with test results
        """
        TestAutomationLogger.log_step("Running BDD tests...")
        
        start_time = datetime.now()
        json_output = self.output_dir / "bdd_results.json"
        features_dir = self.bdd_dir / "features"
        
        # Build behave command
        # Use full formatter path for JSON to avoid ModuleNotFoundError
        cmd = [
            sys.executable, "-m", "behave",
            str(features_dir),
            "-f", "behave.formatter.json:JSONFormatter",
            "-o", str(json_output),
            "-f", "pretty",
            "--no-capture"
        ]
        
        # Add tag filters
        if tags:
            for tag in tags:
                if tag.startswith("~"):
                    cmd.extend(["--tags", tag])
                else:
                    cmd.extend(["--tags", f"@{tag}"])
        
        # Set environment for LocalStack
        env = self._get_test_env()
        
        try:
            self.logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                env=env,
                timeout=900  # 15 minute timeout
            )
            
            end_time = datetime.now()
            
            # Parse results
            if json_output.exists():
                return self._parse_behave_results(json_output, start_time, end_time)
            else:
                return self._create_result_from_output(
                    TestType.BDD,
                    result.returncode,
                    result.stdout,
                    result.stderr,
                    start_time,
                    end_time
                )
                
        except subprocess.TimeoutExpired:
            end_time = datetime.now()
            TestAutomationLogger.log_error("BDD tests timed out")
            return self._create_error_result(
                TestType.BDD,
                "Test execution timed out",
                start_time,
                end_time
            )
        except Exception as e:
            end_time = datetime.now()
            TestAutomationLogger.log_error(f"BDD tests failed: {e}")
            return self._create_error_result(
                TestType.BDD,
                str(e),
                start_time,
                end_time
            )
    
    def run_endurance_tests(
        self,
        duration_seconds: Optional[int] = None,
        iterations: Optional[int] = None
    ) -> TestSuiteResult:
        """
        Run endurance tests with configurable duration or iterations.
        
        Args:
            duration_seconds: Run tests for this many seconds
            iterations: Run this many iterations
            
        Returns:
            TestSuiteResult with test results
        """
        TestAutomationLogger.log_step("Running endurance tests...")
        
        start_time = datetime.now()
        json_output = self.output_dir / "endurance_results.json"
        
        # Default to 60 seconds if neither specified
        if duration_seconds is None and iterations is None:
            duration_seconds = 60
        
        # Build pytest command for endurance tests
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.endurance_dir),
            f"--json-report",
            f"--json-report-file={json_output}",
            "-v",
            "--tb=short"
        ]
        
        # Add duration/iteration markers
        if duration_seconds:
            cmd.extend(["-m", f"endurance"])
            # Pass duration via environment
            env = self._get_test_env()
            env["ENDURANCE_DURATION"] = str(duration_seconds)
        elif iterations:
            env = self._get_test_env()
            env["ENDURANCE_ITERATIONS"] = str(iterations)
        else:
            env = self._get_test_env()
        
        try:
            self.logger.info(f"Running: {' '.join(cmd)}")
            
            # Calculate timeout based on duration
            timeout = (duration_seconds or 300) + 120  # Add 2 minutes buffer
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                env=env,
                timeout=timeout
            )
            
            end_time = datetime.now()
            
            # Parse results
            if json_output.exists():
                return self._parse_pytest_results(json_output, start_time, end_time, TestType.ENDURANCE)
            else:
                return self._create_result_from_output(
                    TestType.ENDURANCE,
                    result.returncode,
                    result.stdout,
                    result.stderr,
                    start_time,
                    end_time
                )
                
        except subprocess.TimeoutExpired:
            end_time = datetime.now()
            TestAutomationLogger.log_error("Endurance tests timed out")
            return self._create_error_result(
                TestType.ENDURANCE,
                "Test execution timed out",
                start_time,
                end_time
            )
        except Exception as e:
            end_time = datetime.now()
            TestAutomationLogger.log_error(f"Endurance tests failed: {e}")
            return self._create_error_result(
                TestType.ENDURANCE,
                str(e),
                start_time,
                end_time
            )
    
    def _get_test_env(self) -> Dict[str, str]:
        """Get environment variables for test execution."""
        import os
        env = os.environ.copy()
        
        # LocalStack configuration
        env.update({
            "USE_LOCALSTACK": "true",
            "LOCALSTACK_HOST": "localhost",
            "LOCALSTACK_PORT": "4566",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "GATEWAY_URL": self.server_url,
        })
        
        return env
    
    def _parse_pytest_results(
        self,
        json_file: Path,
        start_time: datetime,
        end_time: datetime,
        test_type: TestType = TestType.INTEGRATION
    ) -> TestSuiteResult:
        """Parse pytest JSON report into TestSuiteResult."""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            summary = data.get("summary", {})
            tests = data.get("tests", [])
            
            # Parse test cases
            test_cases = []
            for test in tests:
                outcome = test.get("outcome", "unknown")
                status = self._map_pytest_status(outcome)
                
                # Extract error info
                error_message = None
                stack_trace = None
                if outcome in ("failed", "error"):
                    call_info = test.get("call", {})
                    if "longrepr" in call_info:
                        stack_trace = call_info["longrepr"]
                    error_message = test.get("message", call_info.get("crash", {}).get("message"))
                
                test_case = TestCaseResult(
                    name=test.get("nodeid", "unknown"),
                    status=status,
                    duration=test.get("duration", 0),
                    error_message=error_message,
                    stack_trace=stack_trace,
                    output=test.get("stdout")
                )
                test_cases.append(test_case)
            
            result = TestSuiteResult(
                test_type=test_type,
                total=summary.get("total", len(tests)),
                passed=summary.get("passed", 0),
                failed=summary.get("failed", 0),
                skipped=summary.get("skipped", 0),
                errors=summary.get("error", 0),
                duration=(end_time - start_time).total_seconds(),
                start_time=start_time,
                end_time=end_time,
                test_cases=test_cases,
                raw_json=data
            )
            
            self._log_result_summary(result)
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing pytest results: {e}")
            return self._create_error_result(test_type, str(e), start_time, end_time)
    
    def _parse_behave_results(
        self,
        json_file: Path,
        start_time: datetime,
        end_time: datetime
    ) -> TestSuiteResult:
        """Parse behave JSON report into TestSuiteResult."""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            test_cases = []
            total = 0
            passed = 0
            failed = 0
            skipped = 0
            
            for feature in data:
                for element in feature.get("elements", []):
                    if element.get("type") != "scenario":
                        continue
                    
                    total += 1
                    scenario_name = f"{feature.get('name', 'Unknown')}::{element.get('name', 'Unknown')}"
                    
                    # Check all steps
                    steps = element.get("steps", [])
                    scenario_passed = True
                    scenario_skipped = False
                    error_message = None
                    stack_trace = None
                    duration = 0
                    
                    for step in steps:
                        result = step.get("result", {})
                        status = result.get("status", "undefined")
                        duration += result.get("duration", 0)
                        
                        if status == "failed":
                            scenario_passed = False
                            error_message = result.get("error_message", "Step failed")
                            stack_trace = "\n".join(result.get("error_message", []) if isinstance(result.get("error_message"), list) else [str(result.get("error_message", ""))])
                        elif status == "skipped":
                            scenario_skipped = True
                        elif status == "undefined":
                            scenario_passed = False
                            error_message = f"Undefined step: {step.get('name', 'unknown')}"
                    
                    if scenario_skipped and scenario_passed:
                        skipped += 1
                        status = "skipped"
                    elif scenario_passed:
                        passed += 1
                        status = "passed"
                    else:
                        failed += 1
                        status = "failed"
                    
                    test_case = TestCaseResult(
                        name=scenario_name,
                        status=status,
                        duration=duration,
                        error_message=error_message,
                        stack_trace=stack_trace
                    )
                    test_cases.append(test_case)
            
            result = TestSuiteResult(
                test_type=TestType.BDD,
                total=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=0,
                duration=(end_time - start_time).total_seconds(),
                start_time=start_time,
                end_time=end_time,
                test_cases=test_cases,
                raw_json=data
            )
            
            self._log_result_summary(result)
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing behave results: {e}")
            return self._create_error_result(TestType.BDD, str(e), start_time, end_time)
    
    def _map_pytest_status(self, outcome: str) -> str:
        """Map pytest outcome to standard status."""
        mapping = {
            "passed": "passed",
            "failed": "failed",
            "skipped": "skipped",
            "error": "error",
            "xfailed": "skipped",
            "xpassed": "passed"
        }
        return mapping.get(outcome, "unknown")
    
    def _create_result_from_output(
        self,
        test_type: TestType,
        return_code: int,
        stdout: str,
        stderr: str,
        start_time: datetime,
        end_time: datetime
    ) -> TestSuiteResult:
        """Create TestSuiteResult from command output when JSON not available."""
        duration = (end_time - start_time).total_seconds()
        
        # Try to parse counts from output
        passed = 0
        failed = 0
        
        if return_code == 0:
            passed = 1
            status = "passed"
        else:
            failed = 1
            status = "failed"
        
        test_case = TestCaseResult(
            name=f"{test_type.value}_tests",
            status=status,
            duration=duration,
            error_message=stderr if return_code != 0 else None,
            output=stdout
        )
        
        return TestSuiteResult(
            test_type=test_type,
            total=1,
            passed=passed,
            failed=failed,
            skipped=0,
            errors=0,
            duration=duration,
            start_time=start_time,
            end_time=end_time,
            test_cases=[test_case]
        )
    
    def _create_error_result(
        self,
        test_type: TestType,
        error_message: str,
        start_time: datetime,
        end_time: datetime
    ) -> TestSuiteResult:
        """Create TestSuiteResult for execution errors."""
        duration = (end_time - start_time).total_seconds()
        
        test_case = TestCaseResult(
            name=f"{test_type.value}_execution",
            status="error",
            duration=duration,
            error_message=error_message
        )
        
        return TestSuiteResult(
            test_type=test_type,
            total=1,
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            duration=duration,
            start_time=start_time,
            end_time=end_time,
            test_cases=[test_case]
        )
    
    def _log_result_summary(self, result: TestSuiteResult) -> None:
        """Log test result summary."""
        if result.failed > 0 or result.errors > 0:
            TestAutomationLogger.log_warning(
                f"{result.test_type.value}: {result.total} tests, "
                f"{result.passed} passed, {result.failed} failed, "
                f"{result.errors} errors ({result.duration:.1f}s)"
            )
        else:
            TestAutomationLogger.log_success(
                f"{result.test_type.value}: {result.total} tests, "
                f"{result.passed} passed ({result.duration:.1f}s)"
            )
