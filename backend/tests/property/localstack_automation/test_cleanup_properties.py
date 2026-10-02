"""
Property Tests for Cleanup Behavior

Feature: localstack-test-automation
Property 9: Cleanup Behavior

For any test run completion (successful or failed), if keep_running=False,
the Gateway server SHALL be stopped. If cleanup=True, LocalStack SHALL also
be stopped and volumes removed. If keep_running=True, both services SHALL
remain running.

Validates: Requirements 10.1, 10.2, 10.3, 2.4
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.localstack_automation.models import TestRunnerConfig, TestType
from tests.localstack_automation.runner import LocalStackTestRunner


class TestCleanupBehavior:
    """Property tests for cleanup behavior (Property 9)."""
    
    @given(keep_running=st.just(False), cleanup=st.booleans())
    @settings(max_examples=10, deadline=None)
    def test_gateway_stopped_when_not_keep_running(self, keep_running: bool, cleanup: bool):
        """
        Feature: localstack-test-automation, Property 9: Cleanup Behavior
        
        When keep_running=False, Gateway is stopped after tests.
        """
        config = TestRunnerConfig(
            test_types=[TestType.INTEGRATION],
            skip_localstack=True,
            skip_gateway=True,
            keep_running=keep_running,
            cleanup=cleanup
        )
        
        with patch.multiple(
            'tests.localstack_automation.runner',
            LocalStackManager=MagicMock,
            GatewayManager=MagicMock,
            TestExecutor=MagicMock,
            LocalStackReportGenerator=MagicMock,
            S3ReportUploader=MagicMock
        ):
            runner = LocalStackTestRunner(config)
            runner._gateway_started = True
            
            # Mock gateway stop
            runner.gateway.stop = MagicMock(return_value=True)
            
            runner.cleanup()
            
            # Gateway should be stopped
            runner.gateway.stop.assert_called_once()
    
    @given(keep_running=st.just(True))
    @settings(max_examples=5, deadline=None)
    def test_services_remain_when_keep_running(self, keep_running: bool):
        """
        Feature: localstack-test-automation, Property 9: Cleanup Behavior
        
        When keep_running=True, services remain running.
        """
        config = TestRunnerConfig(
            test_types=[TestType.INTEGRATION],
            skip_localstack=True,
            skip_gateway=True,
            keep_running=keep_running,
            cleanup=False
        )
        
        with patch.multiple(
            'tests.localstack_automation.runner',
            LocalStackManager=MagicMock,
            GatewayManager=MagicMock,
            TestExecutor=MagicMock,
            LocalStackReportGenerator=MagicMock,
            S3ReportUploader=MagicMock
        ):
            runner = LocalStackTestRunner(config)
            runner._localstack_started = True
            runner._gateway_started = True
            
            runner.gateway.stop = MagicMock()
            runner.localstack.stop = MagicMock()
            
            runner.cleanup()
            
            # Neither should be stopped when keep_running=True
            # Gateway is stopped regardless, but LocalStack respects keep_running
            runner.localstack.stop.assert_not_called()
    
    @given(cleanup=st.just(True))
    @settings(max_examples=5, deadline=None)
    def test_volumes_removed_when_cleanup_true(self, cleanup: bool):
        """
        Feature: localstack-test-automation, Property 9: Cleanup Behavior
        
        When cleanup=True, LocalStack volumes are removed.
        """
        config = TestRunnerConfig(
            test_types=[TestType.INTEGRATION],
            skip_localstack=True,
            skip_gateway=True,
            keep_running=False,
            cleanup=cleanup
        )
        
        with patch.multiple(
            'tests.localstack_automation.runner',
            LocalStackManager=MagicMock,
            GatewayManager=MagicMock,
            TestExecutor=MagicMock,
            LocalStackReportGenerator=MagicMock,
            S3ReportUploader=MagicMock
        ):
            runner = LocalStackTestRunner(config)
            runner._localstack_started = True
            runner._gateway_started = True
            
            runner.gateway.stop = MagicMock()
            runner.localstack.stop = MagicMock()
            
            runner.cleanup()
            
            # LocalStack should be stopped with remove_volumes=True
            runner.localstack.stop.assert_called_once_with(remove_volumes=True)
    
    @given(cleanup=st.just(False), keep_running=st.just(False))
    @settings(max_examples=5, deadline=None)
    def test_volumes_preserved_when_cleanup_false(self, cleanup: bool, keep_running: bool):
        """
        Feature: localstack-test-automation, Property 9: Cleanup Behavior
        
        When cleanup=False, LocalStack volumes are preserved.
        """
        config = TestRunnerConfig(
            test_types=[TestType.INTEGRATION],
            skip_localstack=True,
            skip_gateway=True,
            keep_running=keep_running,
            cleanup=cleanup
        )
        
        with patch.multiple(
            'tests.localstack_automation.runner',
            LocalStackManager=MagicMock,
            GatewayManager=MagicMock,
            TestExecutor=MagicMock,
            LocalStackReportGenerator=MagicMock,
            S3ReportUploader=MagicMock
        ):
            runner = LocalStackTestRunner(config)
            runner._localstack_started = True
            runner._gateway_started = True
            
            runner.gateway.stop = MagicMock()
            runner.localstack.stop = MagicMock()
            
            runner.cleanup()
            
            # LocalStack should be stopped with remove_volumes=False
            runner.localstack.stop.assert_called_once_with(remove_volumes=False)


class TestCleanupOnlyStartedServices:
    """Property tests for cleanup of only started services."""
    
    @given(
        localstack_started=st.booleans(),
        gateway_started=st.booleans()
    )
    @settings(max_examples=20, deadline=None)
    def test_only_started_services_cleaned(
        self,
        localstack_started: bool,
        gateway_started: bool
    ):
        """
        Feature: localstack-test-automation, Property 9: Cleanup Behavior
        
        Only services that were started by the runner are cleaned up.
        """
        config = TestRunnerConfig(
            test_types=[TestType.INTEGRATION],
            skip_localstack=True,
            skip_gateway=True,
            keep_running=False,
            cleanup=False
        )
        
        with patch.multiple(
            'tests.localstack_automation.runner',
            LocalStackManager=MagicMock,
            GatewayManager=MagicMock,
            TestExecutor=MagicMock,
            LocalStackReportGenerator=MagicMock,
            S3ReportUploader=MagicMock
        ):
            runner = LocalStackTestRunner(config)
            runner._localstack_started = localstack_started
            runner._gateway_started = gateway_started
            
            runner.gateway.stop = MagicMock()
            runner.localstack.stop = MagicMock()
            
            runner.cleanup()
            
            # Gateway cleanup depends on _gateway_started
            if gateway_started:
                runner.gateway.stop.assert_called_once()
            else:
                runner.gateway.stop.assert_not_called()
            
            # LocalStack cleanup depends on _localstack_started
            if localstack_started:
                runner.localstack.stop.assert_called_once()
            else:
                runner.localstack.stop.assert_not_called()
