"""
Property Tests for Test Result Capture

Feature: localstack-test-automation
Property 3: Test Result JSON Validity
Property 4: Failed Test Error Capture

Validates: Requirements 3.2, 3.4, 3.5, 4.2, 4.4, 4.5, 5.4
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
import json

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.localstack_automation.models import (
    TestType, TestSuiteResult, TestCaseResult
)


class TestResultJSONValidity:
    """Property tests for test result JSON validity (Property 3)."""
    
    @given(
        total=st.integers(min_value=0, max_value=1000),
        passed_ratio=st.floats(min_value=0, max_value=1),
        failed_ratio=st.floats(min_value=0, max_value=1),
        skipped_ratio=st.floats(min_value=0, max_value=1)
    )
    @settings(max_examples=100, deadline=None)
    def test_result_counts_sum_to_total(
        self, 
        total: int, 
        passed_ratio: float, 
        failed_ratio: float,
        skipped_ratio: float
    ):
        """
        Feature: localstack-test-automation, Property 3: Test Result JSON Validity
        
        For any test execution, the sum of passed, failed, skipped, error counts
        equals the total count.
        """
        # Normalize ratios to sum to 1
        ratio_sum = passed_ratio + failed_ratio + skipped_ratio
        if ratio_sum > 0:
            passed_ratio /= ratio_sum
            failed_ratio /= ratio_sum
            skipped_ratio /= ratio_sum
        else:
            passed_ratio = 1.0
            failed_ratio = 0.0
            skipped_ratio = 0.0
        
        # Calculate counts
        passed = int(total * passed_ratio)
        failed = int(total * failed_ratio)
        skipped = int(total * skipped_ratio)
        errors = total - passed - failed - skipped  # Remainder goes to errors
        
        # Ensure non-negative
        if errors < 0:
            passed += errors
            errors = 0
        
        result = TestSuiteResult(
            test_type=TestType.INTEGRATION,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=1.0,
            start_time=datetime.now(),
            end_time=datetime.now(),
        )
        
        assert result.validate_counts(), \
            f"Counts don't sum to total: {passed}+{failed}+{skipped}+{errors} != {total}"
    
    @given(
        test_type=st.sampled_from([TestType.INTEGRATION, TestType.BDD, TestType.ENDURANCE]),
        duration=st.floats(min_value=0, max_value=3600, allow_nan=False),
        total=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_result_contains_required_fields(
        self,
        test_type: TestType,
        duration: float,
        total: int
    ):
        """
        Feature: localstack-test-automation, Property 3: Test Result JSON Validity
        
        Test results contain all required fields: total, passed, failed, duration,
        and test cases list.
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration)
        
        result = TestSuiteResult(
            test_type=test_type,
            total=total,
            passed=total,
            failed=0,
            skipped=0,
            errors=0,
            duration=duration,
            start_time=start_time,
            end_time=end_time,
            test_cases=[]
        )
        
        # Verify required fields exist
        assert result.test_type == test_type
        assert result.total == total
        assert result.passed >= 0
        assert result.failed >= 0
        assert result.skipped >= 0
        assert result.errors >= 0
        assert result.duration >= 0
        assert result.start_time is not None
        assert result.end_time is not None
        assert isinstance(result.test_cases, list)
    
    @given(
        total=st.integers(min_value=0, max_value=100),
        passed=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_pass_rate_calculation(self, total: int, passed: int):
        """
        Feature: localstack-test-automation, Property 3: Test Result JSON Validity
        
        Pass rate is correctly calculated as (passed/total) * 100.
        """
        assume(passed <= total)
        
        result = TestSuiteResult(
            test_type=TestType.INTEGRATION,
            total=total,
            passed=passed,
            failed=total - passed,
            skipped=0,
            errors=0,
            duration=1.0,
            start_time=datetime.now(),
            end_time=datetime.now(),
        )
        
        if total == 0:
            assert result.pass_rate == 0.0
        else:
            expected_rate = (passed / total) * 100
            assert abs(result.pass_rate - expected_rate) < 0.001


class TestFailedTestErrorCapture:
    """Property tests for failed test error capture (Property 4)."""
    
    @given(
        error_message=st.text(min_size=1, max_size=500),
        stack_trace=st.text(min_size=0, max_size=2000)
    )
    @settings(max_examples=100, deadline=None)
    def test_failed_test_has_error_message(self, error_message: str, stack_trace: str):
        """
        Feature: localstack-test-automation, Property 4: Failed Test Error Capture
        
        For any test case that fails, the result includes a non-empty error message.
        """
        test_case = TestCaseResult(
            name="test_example",
            status="failed",
            duration=1.0,
            error_message=error_message,
            stack_trace=stack_trace if stack_trace else None
        )
        
        assert test_case.is_failed()
        assert test_case.error_message is not None
        assert len(test_case.error_message) > 0
    
    @given(
        name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', '_'))),
        duration=st.floats(min_value=0, max_value=1000, allow_nan=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_passed_test_status_detection(self, name: str, duration: float):
        """
        Feature: localstack-test-automation, Property 4: Failed Test Error Capture
        
        Passed tests are correctly identified as not failed.
        """
        test_case = TestCaseResult(
            name=name,
            status="passed",
            duration=duration
        )
        
        assert test_case.is_passed()
        assert not test_case.is_failed()
    
    @given(
        status=st.sampled_from(["failed", "error"]),
        error_message=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=50, deadline=None)
    def test_failed_or_error_status_detection(self, status: str, error_message: str):
        """
        Feature: localstack-test-automation, Property 4: Failed Test Error Capture
        
        Both 'failed' and 'error' statuses are detected as failures.
        """
        test_case = TestCaseResult(
            name="test_example",
            status=status,
            duration=1.0,
            error_message=error_message
        )
        
        assert test_case.is_failed()
        assert not test_case.is_passed()


class TestTestCaseResultModel:
    """Property tests for TestCaseResult model."""
    
    @given(
        name=st.text(min_size=1, max_size=200),
        status=st.sampled_from(["passed", "failed", "skipped", "error"]),
        duration=st.floats(min_value=0, max_value=3600, allow_nan=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_case_result_stores_all_fields(
        self,
        name: str,
        status: str,
        duration: float
    ):
        """
        Feature: localstack-test-automation, Property 3: Test Result JSON Validity
        
        TestCaseResult correctly stores all provided fields.
        """
        test_case = TestCaseResult(
            name=name,
            status=status,
            duration=duration
        )
        
        assert test_case.name == name
        assert test_case.status == status
        assert test_case.duration == duration
    
    @given(
        num_cases=st.integers(min_value=0, max_value=50),
        passed_count=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=50, deadline=None)
    def test_suite_with_test_cases(self, num_cases: int, passed_count: int):
        """
        Feature: localstack-test-automation, Property 3: Test Result JSON Validity
        
        TestSuiteResult correctly stores list of test cases.
        """
        assume(passed_count <= num_cases)
        
        test_cases = []
        for i in range(num_cases):
            status = "passed" if i < passed_count else "failed"
            test_cases.append(TestCaseResult(
                name=f"test_{i}",
                status=status,
                duration=0.1,
                error_message="Test failed" if status == "failed" else None
            ))
        
        result = TestSuiteResult(
            test_type=TestType.INTEGRATION,
            total=num_cases,
            passed=passed_count,
            failed=num_cases - passed_count,
            skipped=0,
            errors=0,
            duration=num_cases * 0.1,
            start_time=datetime.now(),
            end_time=datetime.now(),
            test_cases=test_cases
        )
        
        assert len(result.test_cases) == num_cases
        assert sum(1 for tc in result.test_cases if tc.is_passed()) == passed_count
        assert sum(1 for tc in result.test_cases if tc.is_failed()) == num_cases - passed_count
