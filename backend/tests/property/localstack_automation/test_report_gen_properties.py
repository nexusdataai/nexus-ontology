"""
Property Tests for Report HTML Content Completeness

Feature: localstack-test-automation
Property 6: Report HTML Content Completeness

For any test suite result, the generated HTML report SHALL contain:
summary statistics (total, passed, failed, skipped), timestamp information,
duration, and for each test case, its name and status. Failed test cases
SHALL have their error messages included.

Validates: Requirements 6.1, 6.2, 6.4, 6.6
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.localstack_automation.models import TestType, TestSuiteResult, TestCaseResult
from tests.localstack_automation.report_generator import LocalStackReportGenerator


class TestReportHTMLContentCompleteness:
    """Property tests for report HTML content completeness (Property 6)."""
    
    @given(
        total=st.integers(min_value=1, max_value=50),
        passed=st.integers(min_value=0, max_value=50),
        failed=st.integers(min_value=0, max_value=50),
        skipped=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=50, deadline=None)
    def test_report_contains_summary_statistics(
        self, total: int, passed: int, failed: int, skipped: int
    ):
        """
        Feature: localstack-test-automation, Property 6: Report HTML Content Completeness
        
        Generated report contains summary statistics (total, passed, failed, skipped).
        """
        # Ensure counts are valid
        assume(passed + failed + skipped <= total)
        errors = total - passed - failed - skipped
        
        results = TestSuiteResult(
            test_type=TestType.INTEGRATION,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=10.0,
            start_time=datetime.now(),
            end_time=datetime.now(),
            test_cases=[]
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = LocalStackReportGenerator(output_dir=Path(tmpdir))
            report_path = generator.generate_integration_report(results)
            
            with open(report_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # Verify summary statistics are present
            assert f'>{total}<' in html, "Total count not found in report"
            assert f'>{passed}<' in html, "Passed count not found in report"
            assert f'>{failed}<' in html, "Failed count not found in report"
            assert f'>{skipped}<' in html, "Skipped count not found in report"
    
    @given(
        duration=st.floats(min_value=0.001, max_value=3600, allow_nan=False)
    )
    @settings(max_examples=30, deadline=None)
    def test_report_contains_duration(self, duration: float):
        """
        Feature: localstack-test-automation, Property 6: Report HTML Content Completeness
        
        Generated report contains duration information.
        """
        results = TestSuiteResult(
            test_type=TestType.INTEGRATION,
            total=1,
            passed=1,
            failed=0,
            skipped=0,
            errors=0,
            duration=duration,
            start_time=datetime.now(),
            end_time=datetime.now(),
            test_cases=[]
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = LocalStackReportGenerator(output_dir=Path(tmpdir))
            report_path = generator.generate_integration_report(results)
            
            with open(report_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # Duration should be present (formatted)
            assert 'Duration' in html, "Duration label not found"

    @given(
        test_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', '_'))),
        status=st.sampled_from(["passed", "failed", "skipped", "error"])
    )
    @settings(max_examples=50, deadline=None)
    def test_report_contains_test_case_info(self, test_name: str, status: str):
        """
        Feature: localstack-test-automation, Property 6: Report HTML Content Completeness
        
        Generated report contains test case name and status.
        """
        test_case = TestCaseResult(
            name=test_name,
            status=status,
            duration=1.0,
            error_message="Test error" if status in ("failed", "error") else None
        )
        
        results = TestSuiteResult(
            test_type=TestType.INTEGRATION,
            total=1,
            passed=1 if status == "passed" else 0,
            failed=1 if status == "failed" else 0,
            skipped=1 if status == "skipped" else 0,
            errors=1 if status == "error" else 0,
            duration=1.0,
            start_time=datetime.now(),
            end_time=datetime.now(),
            test_cases=[test_case]
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = LocalStackReportGenerator(output_dir=Path(tmpdir))
            report_path = generator.generate_integration_report(results)
            
            with open(report_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # Test name should be in report (HTML escaped)
            assert test_name in html or generator._escape_html(test_name) in html, \
                f"Test name '{test_name}' not found in report"
    
    @given(
        error_message=st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N', ' ')))
    )
    @settings(max_examples=30, deadline=None)
    def test_failed_test_error_in_report(self, error_message: str):
        """
        Feature: localstack-test-automation, Property 6: Report HTML Content Completeness
        
        Failed test cases have their error messages included in the report.
        """
        test_case = TestCaseResult(
            name="test_failure",
            status="failed",
            duration=1.0,
            error_message=error_message
        )
        
        results = TestSuiteResult(
            test_type=TestType.INTEGRATION,
            total=1,
            passed=0,
            failed=1,
            skipped=0,
            errors=0,
            duration=1.0,
            start_time=datetime.now(),
            end_time=datetime.now(),
            test_cases=[test_case]
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = LocalStackReportGenerator(output_dir=Path(tmpdir))
            report_path = generator.generate_integration_report(results)
            
            with open(report_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # Error message should be in report (HTML escaped)
            escaped_error = generator._escape_html(error_message)
            assert escaped_error in html, \
                f"Error message not found in report"


class TestReportGenerationForAllTypes:
    """Property tests for report generation across all test types."""
    
    @given(
        test_type=st.sampled_from([TestType.INTEGRATION, TestType.BDD, TestType.ENDURANCE])
    )
    @settings(max_examples=10, deadline=None)
    def test_report_generated_for_all_types(self, test_type: TestType):
        """
        Feature: localstack-test-automation, Property 6: Report HTML Content Completeness
        
        Reports can be generated for all test types.
        """
        results = TestSuiteResult(
            test_type=test_type,
            total=5,
            passed=4,
            failed=1,
            skipped=0,
            errors=0,
            duration=10.0,
            start_time=datetime.now(),
            end_time=datetime.now(),
            test_cases=[]
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = LocalStackReportGenerator(output_dir=Path(tmpdir))
            
            if test_type == TestType.INTEGRATION:
                report_path = generator.generate_integration_report(results)
            elif test_type == TestType.BDD:
                report_path = generator.generate_bdd_report(results)
            else:
                report_path = generator.generate_endurance_report(results)
            
            assert report_path.exists(), f"Report not created for {test_type.value}"
            
            with open(report_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # Basic HTML structure check
            assert '<!DOCTYPE html>' in html
            assert '</html>' in html
            assert test_type.value in html.lower() or test_type.value.title() in html


class TestIndexPageGeneration:
    """Property tests for index page generation."""
    
    @given(
        num_reports=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=20, deadline=None)
    def test_index_contains_all_reports(self, num_reports: int):
        """
        Feature: localstack-test-automation, Property 6: Report HTML Content Completeness
        
        Index page contains links to all generated reports.
        """
        from tests.localstack_automation.models import ReportInfo
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            generator = LocalStackReportGenerator(output_dir=tmpdir_path)
            
            # Create mock report files and ReportInfo objects
            reports = []
            test_types = [TestType.INTEGRATION, TestType.BDD, TestType.ENDURANCE]
            
            for i in range(num_reports):
                test_type = test_types[i % len(test_types)]
                report_file = tmpdir_path / f"report_{i}.html"
                report_file.write_text("<html></html>")
                
                reports.append(ReportInfo(
                    test_type=test_type,
                    local_path=report_file,
                    total_tests=10,
                    passed_tests=8,
                    failed_tests=2
                ))
            
            index_path = generator.generate_index(reports)
            
            with open(index_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # Verify each report is linked
            for report in reports:
                assert report.local_path.name in html, \
                    f"Report {report.local_path.name} not linked in index"
