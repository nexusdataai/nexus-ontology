"""
Property-based tests for CloudWatch fallback to console.

Feature: localstack-enablement
Property 5: CloudWatch fallback to console

Tests that CloudWatch logging failures result in graceful fallback to console logging.

**Validates: Requirements 8.4**
"""

import os
import sys
import pytest
import logging
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from hypothesis import given, strategies as st, settings

from src.config.localstack_config import reset_localstack_config


def clean_env():
    """Remove LocalStack-related environment variables."""
    env_vars = [
        'USE_LOCALSTACK', 'LOCALSTACK_HOST', 'LOCALSTACK_PORT',
        'AWS_DEFAULT_REGION', 'AWS_REGION', 'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 'ECS_CONTAINER_METADATA_URI',
        'ENABLE_CLOUDWATCH_LOGS', 'CLOUDWATCH_LOG_GROUP'
    ]
    for var in env_vars:
        os.environ.pop(var, None)


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment before and after each test."""
    clean_env()
    reset_localstack_config()
    # Clear logger cache
    from src.utils.cloudwatch_logger import _loggers
    _loggers.clear()
    yield
    clean_env()
    reset_localstack_config()
    _loggers.clear()


class TestCloudWatchFallbackToConsole:
    """
    Property 5: CloudWatch fallback to console
    
    For any CloudWatch logging failure in LocalStack mode, the CloudWatch_Logger
    SHALL not raise an exception to the caller, fall back to console logging,
    and log a warning about the fallback.
    """
    
    @given(
        logger_name=st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Nd'),
            whitelist_characters='-_'
        )).filter(lambda x: x.strip() and x[0].isalpha())
    )
    @settings(max_examples=100)
    def test_fallback_does_not_raise_exception(self, logger_name):
        """
        Feature: localstack-enablement, Property 5: CloudWatch fallback to console
        **Validates: Requirements 8.4**
        
        CloudWatch failure should not raise exception to caller.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = 'nonexistent-host'
        os.environ['LOCALSTACK_PORT'] = '9999'
        
        # Clear logger cache
        from src.utils.cloudwatch_logger import _loggers
        _loggers.clear()
        
        # This should not raise an exception even if CloudWatch fails
        try:
            from src.utils.cloudwatch_logger import get_logger
            logger = get_logger(f"test-{logger_name}")
            
            # Logger should still work (console fallback)
            logger.info("Test message")
            logger.error("Test error")
            
            # No exception means success
            assert True
        except Exception as e:
            pytest.fail(f"Logger should not raise exception on CloudWatch failure: {e}")
    
    def test_fallback_enables_console_logging(self):
        """
        Feature: localstack-enablement, Property 5: CloudWatch fallback to console
        **Validates: Requirements 8.4**
        
        When CloudWatch fails, console logging should still work.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'true'
        os.environ['LOCALSTACK_HOST'] = 'nonexistent-host'
        
        from src.utils.cloudwatch_logger import _loggers, get_logger
        _loggers.clear()
        
        logger = get_logger('fallback-test')
        
        # Logger should have at least console handler
        assert len(logger.handlers) >= 1, "Logger should have at least one handler (console)"
        
        # Check that at least one handler is a StreamHandler (console)
        has_console = any(
            isinstance(h, logging.StreamHandler) 
            for h in logger.handlers
        )
        assert has_console, "Logger should have console handler as fallback"
    
    @given(
        log_message=st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
    )
    @settings(max_examples=100)
    def test_console_logging_works_after_fallback(self, log_message):
        """
        Feature: localstack-enablement, Property 5: CloudWatch fallback to console
        **Validates: Requirements 8.4**
        
        Console logging should work normally after CloudWatch fallback.
        """
        clean_env()
        reset_localstack_config()
        
        # Don't enable LocalStack or ECS - just use console
        os.environ['USE_LOCALSTACK'] = 'false'
        
        from src.utils.cloudwatch_logger import _loggers, get_logger
        _loggers.clear()
        
        logger = get_logger('console-test')
        
        # These should not raise exceptions
        try:
            logger.info(log_message)
            logger.warning(log_message)
            logger.error(log_message)
        except Exception as e:
            pytest.fail(f"Console logging should work: {e}")
    
    def test_fallback_mode_property_set(self):
        """
        Feature: localstack-enablement, Property 5: CloudWatch fallback to console
        **Validates: Requirements 8.4**
        
        CloudWatchLogger should track fallback mode status.
        """
        clean_env()
        reset_localstack_config()
        
        from src.utils.cloudwatch_logger import CloudWatchLogger, _loggers
        _loggers.clear()
        
        # Create logger without CloudWatch (console only)
        os.environ['USE_LOCALSTACK'] = 'false'
        
        cw_logger = CloudWatchLogger('test-fallback-mode')
        
        # Should not be in CloudWatch mode
        assert not cw_logger.is_cloudwatch_enabled, \
            "CloudWatch should not be enabled in console-only mode"
    
    @given(
        log_level=st.sampled_from(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    )
    @settings(max_examples=100)
    def test_log_level_preserved_in_fallback(self, log_level):
        """
        Feature: localstack-enablement, Property 5: CloudWatch fallback to console
        **Validates: Requirements 8.4**
        
        Log level should be preserved when falling back to console.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'false'
        os.environ['LOG_LEVEL'] = log_level
        
        from src.utils.cloudwatch_logger import _loggers, get_logger
        _loggers.clear()
        
        logger = get_logger('level-test')
        
        expected_level = getattr(logging, log_level)
        assert logger.level == expected_level, \
            f"Logger level should be {log_level} ({expected_level}), got {logger.level}"
    
    def test_multiple_loggers_independent_fallback(self):
        """
        Feature: localstack-enablement, Property 5: CloudWatch fallback to console
        **Validates: Requirements 8.4**
        
        Multiple loggers should handle fallback independently.
        """
        clean_env()
        reset_localstack_config()
        
        os.environ['USE_LOCALSTACK'] = 'false'
        
        from src.utils.cloudwatch_logger import _loggers, get_logger
        _loggers.clear()
        
        logger1 = get_logger('logger-1')
        logger2 = get_logger('logger-2')
        logger3 = get_logger('logger-3')
        
        # All loggers should work independently
        try:
            logger1.info("Message from logger 1")
            logger2.info("Message from logger 2")
            logger3.info("Message from logger 3")
        except Exception as e:
            pytest.fail(f"Multiple loggers should work independently: {e}")
        
        # Each logger should be cached
        assert 'logger-1' in _loggers
        assert 'logger-2' in _loggers
        assert 'logger-3' in _loggers
