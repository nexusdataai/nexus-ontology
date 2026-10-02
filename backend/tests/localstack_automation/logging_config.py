"""
Logging Configuration for LocalStack Test Automation

Provides centralized logging setup with file and console handlers.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class TestAutomationLogger:
    """Centralized logger for test automation framework."""
    
    _instance: Optional['TestAutomationLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def setup(
        cls,
        log_file: Optional[Path] = None,
        level: int = logging.INFO,
        console_level: int = logging.INFO
    ) -> logging.Logger:
        """
        Set up logging with file and console handlers.
        
        Args:
            log_file: Path to log file (creates parent directories if needed)
            level: File logging level
            console_level: Console logging level
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger("localstack_automation")
        logger.setLevel(logging.DEBUG)  # Capture all, filter at handler level
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (if log_file provided)
        if log_file:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        cls._logger = logger
        return logger
    
    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get the configured logger instance."""
        if cls._logger is None:
            return cls.setup()
        return cls._logger
    
    @classmethod
    def log_section(cls, title: str, char: str = "=") -> None:
        """Log a section header."""
        logger = cls.get_logger()
        line = char * 60
        logger.info(line)
        logger.info(f"  {title}")
        logger.info(line)
    
    @classmethod
    def log_step(cls, step: str) -> None:
        """Log a step in the process."""
        logger = cls.get_logger()
        logger.info(f">>> {step}")
    
    @classmethod
    def log_success(cls, message: str) -> None:
        """Log a success message."""
        logger = cls.get_logger()
        logger.info(f"✅ {message}")
    
    @classmethod
    def log_warning(cls, message: str) -> None:
        """Log a warning message."""
        logger = cls.get_logger()
        logger.warning(f"⚠️  {message}")
    
    @classmethod
    def log_error(cls, message: str) -> None:
        """Log an error message."""
        logger = cls.get_logger()
        logger.error(f"❌ {message}")
    
    @classmethod
    def log_info(cls, message: str) -> None:
        """Log an info message."""
        logger = cls.get_logger()
        logger.info(message)


def get_logger() -> logging.Logger:
    """Convenience function to get the automation logger."""
    return TestAutomationLogger.get_logger()


def setup_logging(log_file: Optional[Path] = None) -> logging.Logger:
    """Convenience function to set up logging."""
    return TestAutomationLogger.setup(log_file=log_file)
