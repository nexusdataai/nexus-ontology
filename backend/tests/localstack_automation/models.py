"""
Data Models for LocalStack Test Automation

Defines configuration, result, and health check models used throughout the framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path


class TestType(Enum):
    """Types of tests that can be executed."""
    INTEGRATION = "integration"
    BDD = "bdd"
    ENDURANCE = "endurance"
    ALL = "all"


@dataclass
class TestRunnerConfig:
    """Configuration for the test runner."""
    test_types: List[TestType] = field(default_factory=lambda: [TestType.ALL])
    skip_localstack: bool = False
    skip_gateway: bool = False
    upload_to_s3: bool = False
    keep_running: bool = False
    cleanup: bool = False
    
    # LocalStack settings
    localstack_endpoint: str = "http://localhost:4566"
    localstack_timeout: int = 60
    
    # Gateway settings
    gateway_url: str = "http://localhost:8000"
    gateway_timeout: int = 30
    
    # Test settings
    bdd_tags: Optional[List[str]] = None
    endurance_duration: Optional[int] = None
    endurance_iterations: Optional[int] = None
    
    # S3 settings
    s3_bucket: str = "test-reports"
    s3_region: str = "us-east-1"
    
    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("test_reports/localstack"))
    log_file: Path = field(default_factory=lambda: Path("test_reports/localstack/test_run.log"))
    
    def __post_init__(self):
        """Convert string paths to Path objects if needed."""
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        if isinstance(self.log_file, str):
            self.log_file = Path(self.log_file)


@dataclass
class TestCaseResult:
    """Result of a single test case."""
    name: str
    status: str  # "passed", "failed", "skipped", "error"
    duration: float  # seconds
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    output: Optional[str] = None
    
    def is_passed(self) -> bool:
        """Check if test passed."""
        return self.status.lower() == "passed"
    
    def is_failed(self) -> bool:
        """Check if test failed."""
        return self.status.lower() in ("failed", "error")


@dataclass
class TestSuiteResult:
    """Result of a test suite execution."""
    test_type: TestType
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float  # seconds
    start_time: datetime
    end_time: datetime
    test_cases: List[TestCaseResult] = field(default_factory=list)
    raw_json: Optional[Dict[str, Any]] = None
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100
    
    def validate_counts(self) -> bool:
        """Validate that counts sum correctly."""
        return self.passed + self.failed + self.skipped + self.errors == self.total


@dataclass
class TestRunResult:
    """Overall result of the test run."""
    success: bool
    start_time: datetime
    end_time: datetime
    duration: float
    suite_results: Dict[str, TestSuiteResult] = field(default_factory=dict)
    reports_generated: List[Path] = field(default_factory=list)
    reports_uploaded: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def total_tests(self) -> int:
        """Get total number of tests across all suites."""
        return sum(r.total for r in self.suite_results.values())
    
    @property
    def total_passed(self) -> int:
        """Get total passed tests across all suites."""
        return sum(r.passed for r in self.suite_results.values())
    
    @property
    def total_failed(self) -> int:
        """Get total failed tests across all suites."""
        return sum(r.failed for r in self.suite_results.values())


@dataclass
class ReportInfo:
    """Information about a generated report."""
    test_type: TestType
    local_path: Path
    s3_url: Optional[str] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100


@dataclass
class ServiceHealth:
    """Health status of a service."""
    name: str
    healthy: bool
    endpoint: str
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvironmentHealth:
    """Overall environment health status."""
    localstack: ServiceHealth
    gateway: ServiceHealth
    
    @property
    def ready_for_tests(self) -> bool:
        """Check if environment is ready for test execution."""
        return self.localstack.healthy and self.gateway.healthy
