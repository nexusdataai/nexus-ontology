#!/usr/bin/env python3
"""
CloudWatch Logging Utility for Alert Engine
Provides centralized logging that works both locally, in ECS containers, and with LocalStack
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional
import socket

# Import LocalStack configuration
try:
    from ..config.localstack_config import get_localstack_config, is_localstack_enabled
    HAS_LOCALSTACK_CONFIG = True
except ImportError:
    HAS_LOCALSTACK_CONFIG = False
    def is_localstack_enabled():
        return os.getenv('USE_LOCALSTACK', 'false').lower() == 'true'
    def get_localstack_config():
        return None

# Check if we're running in ECS or LocalStack mode
IS_ECS = os.getenv('ECS_CONTAINER_METADATA_URI') is not None or os.getenv('ENABLE_CLOUDWATCH_LOGS', 'false').lower() == 'true'
IS_LOCALSTACK = is_localstack_enabled()

# Try to import watchtower for CloudWatch logging
try:
    import watchtower
    HAS_WATCHTOWER = True
except ImportError:
    HAS_WATCHTOWER = False
    if IS_ECS and not IS_LOCALSTACK:
        print("⚠️  Warning: watchtower not installed. CloudWatch logging disabled. Install with: pip install watchtower")


class CloudWatchLogger:
    """
    Unified logging handler that sends logs to both console and CloudWatch
    
    Supports LocalStack for local development - when USE_LOCALSTACK=true,
    CloudWatch logs are sent to LocalStack's CloudWatch emulation.
    Falls back to console logging if CloudWatch is unavailable.
    
    Usage:
        from scripts.utils.cloudwatch_logger import get_logger
        
        logger = get_logger('my-script')
        logger.info("Processing data...")
        logger.error("Error occurred", exc_info=True)
    """
    
    def __init__(
        self,
        logger_name: str,
        log_level: Optional[str] = None,
        cloudwatch_log_group: Optional[str] = None,
        cloudwatch_stream_prefix: Optional[str] = None
    ):
        """
        Initialize CloudWatch logger
        
        Args:
            logger_name: Name of the logger (used for log stream)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            cloudwatch_log_group: CloudWatch log group name
            cloudwatch_stream_prefix: Prefix for CloudWatch log streams
        """
        self.logger_name = logger_name
        self.log_level = log_level or os.getenv('LOG_LEVEL', 'INFO').upper()
        self.cloudwatch_log_group = cloudwatch_log_group or os.getenv('CLOUDWATCH_LOG_GROUP', '/aws/nexus-backend/default')
        self.cloudwatch_stream_prefix = cloudwatch_stream_prefix or os.getenv('CLOUDWATCH_LOG_STREAM_PREFIX', 'script')
        self._cloudwatch_enabled = False
        self._fallback_to_console = False
        
        # Create logger
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(getattr(logging, self.log_level))
        
        # Remove any existing handlers
        self.logger.handlers = []
        
        # Add console handler (always)
        self._add_console_handler()
        
        # Add CloudWatch handler based on environment
        if IS_LOCALSTACK and HAS_WATCHTOWER:
            # LocalStack mode - use LocalStack CloudWatch endpoint
            self._add_localstack_cloudwatch_handler()
        elif IS_ECS and HAS_WATCHTOWER:
            # ECS mode - use real AWS CloudWatch
            self._add_cloudwatch_handler()
    
    def _add_console_handler(self):
        """Add console (stdout) logging handler"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level))
        
        # Format with timestamp, level, and message
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
    
    def _add_cloudwatch_handler(self):
        """Add CloudWatch logging handler for real AWS"""
        try:
            # Get AWS region
            aws_region = os.getenv('AWS_REGION', 'us-east-1')
            
            # Create unique stream name: prefix/logger-name/hostname/timestamp
            hostname = socket.gethostname()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            stream_name = f"{self.cloudwatch_stream_prefix}/{self.logger_name}/{hostname}/{timestamp}"
            
            # Create CloudWatch handler using watchtower
            cloudwatch_handler = watchtower.CloudWatchLogHandler(
                log_group_name=self.cloudwatch_log_group,
                log_stream_name=stream_name,
                use_queues=True,  # Use background thread for sending logs
                create_log_group=True,  # Create log group if it doesn't exist
                boto3_session=None,  # Use default AWS credentials
                send_interval=5,  # Send logs every 5 seconds
                max_batch_size=100,  # Batch up to 100 log events
                max_batch_count=10000  # Max events to queue
            )
            
            cloudwatch_handler.setLevel(getattr(logging, self.log_level))
            
            # Use JSON format for CloudWatch
            formatter = logging.Formatter(
                '%(levelname)s | %(name)s | %(message)s'
            )
            cloudwatch_handler.setFormatter(formatter)
            
            self.logger.addHandler(cloudwatch_handler)
            self._cloudwatch_enabled = True
            self.logger.info(f"✅ CloudWatch logging enabled: {self.cloudwatch_log_group}/{stream_name}")
            
        except Exception as e:
            self._fallback_to_console = True
            self.logger.warning(f"⚠️  Failed to initialize CloudWatch logging: {e}")
            self.logger.warning("   Continuing with console logging only")
    
    def _add_localstack_cloudwatch_handler(self):
        """Add CloudWatch logging handler for LocalStack"""
        try:
            import boto3
            
            # Get LocalStack configuration
            localstack_config = get_localstack_config() if HAS_LOCALSTACK_CONFIG else None
            
            if localstack_config:
                endpoint_url = localstack_config.endpoint_url
                region = localstack_config.region
                access_key = localstack_config.access_key
                secret_key = localstack_config.secret_key
            else:
                # Fallback to environment variables
                host = os.getenv('LOCALSTACK_HOST', 'localhost')
                port = os.getenv('LOCALSTACK_PORT', '4566')
                endpoint_url = f"http://{host}:{port}"
                region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
                access_key = os.getenv('AWS_ACCESS_KEY_ID', 'test')
                secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
            
            # Create boto3 session for LocalStack
            session = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            
            # Create unique stream name
            hostname = socket.gethostname()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            stream_name = f"{self.cloudwatch_stream_prefix}/{self.logger_name}/{hostname}/{timestamp}"
            
            # Create CloudWatch handler with LocalStack endpoint
            cloudwatch_handler = watchtower.CloudWatchLogHandler(
                log_group_name=self.cloudwatch_log_group,
                log_stream_name=stream_name,
                use_queues=True,
                create_log_group=True,
                boto3_session=session,
                boto3_client=session.client(
                    'logs',
                    endpoint_url=endpoint_url,
                    use_ssl=False,
                    verify=False
                ),
                send_interval=5,
                max_batch_size=100,
                max_batch_count=10000
            )
            
            cloudwatch_handler.setLevel(getattr(logging, self.log_level))
            
            formatter = logging.Formatter(
                '%(levelname)s | %(name)s | %(message)s'
            )
            cloudwatch_handler.setFormatter(formatter)
            
            self.logger.addHandler(cloudwatch_handler)
            self._cloudwatch_enabled = True
            self.logger.info(f"✅ LocalStack CloudWatch logging enabled: {endpoint_url} -> {self.cloudwatch_log_group}/{stream_name}")
            
        except Exception as e:
            self._fallback_to_console = True
            self.logger.warning(f"⚠️  Failed to initialize LocalStack CloudWatch logging: {e}")
            self.logger.warning("   Falling back to console logging only")
            self.logger.warning("   Ensure LocalStack is running: ./scripts/start-localstack.sh")
    
    @property
    def is_cloudwatch_enabled(self) -> bool:
        """Check if CloudWatch logging is enabled"""
        return self._cloudwatch_enabled
    
    @property
    def is_fallback_mode(self) -> bool:
        """Check if logger fell back to console-only mode"""
        return self._fallback_to_console
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger


# Global logger cache
_loggers = {}

# Global CloudWatchLogger instances cache (for log level updates)
_cw_logger_instances = {}


def get_logger(
    name: str,
    log_level: Optional[str] = None,
    cloudwatch_log_group: Optional[str] = None,
    cloudwatch_stream_prefix: Optional[str] = None
) -> logging.Logger:
    """
    Get or create a logger with CloudWatch support
    
    Args:
        name: Logger name (typically script name)
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        cloudwatch_log_group: CloudWatch log group name
        cloudwatch_stream_prefix: Prefix for log streams
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger('pipeline-orchestrator')
        logger.info("Starting pipeline...")
        logger.error("Error occurred", exc_info=True)
    """
    # Return cached logger if exists
    if name in _loggers:
        return _loggers[name]
    
    # Create new logger
    cw_logger = CloudWatchLogger(
        logger_name=name,
        log_level=log_level,
        cloudwatch_log_group=cloudwatch_log_group,
        cloudwatch_stream_prefix=cloudwatch_stream_prefix
    )
    
    logger = cw_logger.get_logger()
    _loggers[name] = logger
    _cw_logger_instances[name] = cw_logger  # Track instance for level updates
    
    return logger


def update_all_logger_levels(new_level: str) -> int:
    """
    Update log level for all CloudWatch loggers at runtime.
    
    This function updates both the logger and all its handlers to the new level,
    allowing runtime log level changes without restarting the application.
    
    Args:
        new_level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Number of loggers updated
    """
    count = 0
    level_value = getattr(logging, new_level.upper(), logging.INFO)
    
    for name, logger in _loggers.items():
        try:
            # Update logger level
            logger.setLevel(level_value)
            
            # Update all handler levels
            for handler in logger.handlers:
                handler.setLevel(level_value)
            
            # Update the CloudWatchLogger instance's tracked level
            if name in _cw_logger_instances:
                _cw_logger_instances[name].log_level = new_level.upper()
            
            count += 1
        except Exception as e:
            print(f"Failed to update logger {name}: {e}")
    
    return count


def get_logger_stats() -> dict:
    """
    Get statistics about active CloudWatch loggers.
    
    Returns:
        Dictionary with logger statistics
    """
    return {
        "total_loggers": len(_loggers),
        "logger_names": list(_loggers.keys()),
        "cloudwatch_enabled_count": sum(
            1 for name in _cw_logger_instances
            if _cw_logger_instances[name].is_cloudwatch_enabled
        )
    }


def configure_script_logging(script_name: str) -> logging.Logger:
    """
    Quick setup for script logging with sensible defaults
    
    Args:
        script_name: Name of the script (without .py extension)
    
    Returns:
        Configured logger
    
    Example:
        logger = configure_script_logging('classify_network_elements')
        logger.info("Script started")
    """
    return get_logger(
        name=script_name,
        cloudwatch_stream_prefix='scripts'
    )


# Example usage
if __name__ == "__main__":
    # Test logging
    logger = get_logger('test-logger')
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # Test with exception
    try:
        1 / 0
    except Exception as e:
        logger.error("An error occurred", exc_info=True)
    
    print("\n✅ CloudWatch logger test complete!")
    print(f"   Running in ECS: {IS_ECS}")
    print(f"   Running in LocalStack: {IS_LOCALSTACK}")
    print(f"   Watchtower available: {HAS_WATCHTOWER}")
    print(f"   Logs sent to: {os.getenv('CLOUDWATCH_LOG_GROUP', 'console-only')}")
