"""
LocalStack Test Automation Framework

A comprehensive test automation framework for running integration, BDD, and endurance tests
against a server running on LocalStack. The framework automates the complete test lifecycle:
starting LocalStack, running the gateway server, executing test suites, generating reports,
and uploading results to S3.
"""

from .models import (
    TestType,
    TestRunnerConfig,
    TestCaseResult,
    TestSuiteResult,
    TestRunResult,
    ReportInfo,
    ServiceHealth,
    EnvironmentHealth,
)
from .localstack_manager import LocalStackManager
from .gateway_manager import GatewayManager
from .test_executor import TestExecutor
from .report_generator import LocalStackReportGenerator
from .s3_uploader import S3ReportUploader
from .runner import LocalStackTestRunner, parse_arguments
from .logging_config import get_logger, TestAutomationLogger

__all__ = [
    # Models
    "TestType",
    "TestRunnerConfig",
    "TestCaseResult",
    "TestSuiteResult",
    "TestRunResult",
    "ReportInfo",
    "ServiceHealth",
    "EnvironmentHealth",
    # Managers
    "LocalStackManager",
    "GatewayManager",
    # Executor
    "TestExecutor",
    # Reporting
    "LocalStackReportGenerator",
    "S3ReportUploader",
    # Runner
    "LocalStackTestRunner",
    "parse_arguments",
    # Logging
    "get_logger",
    "TestAutomationLogger",
]
