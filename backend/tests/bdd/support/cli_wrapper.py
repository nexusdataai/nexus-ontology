#!/usr/bin/env python3
"""
CLI Wrapper for Journey Manager Interactive Testing
Handles spawning, interaction, and output capture for the CLI process
"""

import pexpect
import sys
import os
import time
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class JourneyManagerCLI:
    """Wrapper for interacting with Journey Manager CLI using pexpect"""
    
    def __init__(self, timeout: int = 30, encoding: str = 'utf-8'):
        """Initialize CLI wrapper
        
        Args:
            timeout: Default timeout for expect operations
            encoding: Character encoding for CLI interaction
        """
        self.cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            "scripts", "actors", "journeys", "journey-manager.py"
        )
        self.process: Optional[pexpect.spawn] = None
        self.timeout = timeout
        self.encoding = encoding
        self.current_menu = "main"
        self.menu_stack = []
        self.output_buffer = []
        
    def start(self, log_output: bool = False) -> None:
        """Start the CLI process
        
        Args:
            log_output: Whether to log CLI output to stdout
        """
        if self.process and self.process.isalive():
            self.stop()
            
        # Spawn the CLI process
        self.process = pexpect.spawn(
            f"python {self.cli_path}",
            encoding=self.encoding,
            timeout=self.timeout,
            env=os.environ.copy()
        )
        
        # Enable logging if requested
        if log_output:
            self.process.logfile_read = sys.stdout
            
        # Wait for initial prompt
        self.wait_for_main_menu()
        
    def stop(self) -> None:
        """Stop the CLI process gracefully"""
        if self.process and self.process.isalive():
            try:
                # Try to exit gracefully
                self.send_input('0')
                self.process.expect(pexpect.EOF, timeout=5)
            except (pexpect.TIMEOUT, pexpect.EOF):
                # Force close if graceful exit fails
                self.process.close(force=True)
                
        self.process = None
        self.current_menu = "main"
        self.menu_stack = []
        
    def send_input(self, text: str) -> None:
        """Send input to the CLI
        
        Args:
            text: Text to send to the CLI
        """
        if not self.process or not self.process.isalive():
            raise RuntimeError("CLI process is not running")
            
        self.process.sendline(text)
        
    def send_control(self, char: str) -> None:
        """Send control character to CLI (e.g., Ctrl+C)
        
        Args:
            char: Control character (e.g., 'c' for Ctrl+C)
        """
        if not self.process:
            raise RuntimeError("CLI process is not running")
            
        self.process.sendcontrol(char)
        
    def wait_for_prompt(self, patterns: List[str], timeout: Optional[int] = None) -> Tuple[int, str]:
        """Wait for one of several prompt patterns
        
        Args:
            patterns: List of regex patterns to wait for
            timeout: Optional timeout override
            
        Returns:
            Tuple of (pattern index, matched text)
        """
        if not self.process:
            raise RuntimeError("CLI process is not running")
            
        timeout = timeout or self.timeout
        index = self.process.expect(patterns, timeout=timeout)
        matched = self.process.after if hasattr(self.process, 'after') else ""
        return index, matched
        
    def wait_for_text(self, text: str, timeout: Optional[int] = None) -> bool:
        """Wait for specific text to appear
        
        Args:
            text: Text to wait for
            timeout: Optional timeout override
            
        Returns:
            True if text was found, False if timeout
        """
        try:
            self.process.expect(text, timeout=timeout or self.timeout)
            return True
        except pexpect.TIMEOUT:
            return False
            
    def capture_output(self, until_pattern: Optional[str] = None, timeout: Optional[int] = None) -> str:
        """Capture output until a specific pattern or timeout
        
        Args:
            until_pattern: Optional pattern to stop capture
            timeout: Optional timeout override
            
        Returns:
            Captured output text
        """
        if not self.process:
            raise RuntimeError("CLI process is not running")
            
        if until_pattern:
            try:
                self.process.expect(until_pattern, timeout=timeout or self.timeout)
            except pexpect.TIMEOUT:
                pass
                
        return self.process.before if hasattr(self.process, 'before') else ""
        
    def get_current_output(self) -> str:
        """Get the current buffer output without waiting"""
        if not self.process:
            return ""
        return self.process.before if hasattr(self.process, 'before') else ""
        
    # Menu Navigation Helpers
    
    def wait_for_main_menu(self) -> None:
        """Wait for main menu to appear"""
        patterns = [
            "Main Menu",
            "Journey Operations",
            "Select option",
            "Exit"
        ]
        self.wait_for_prompt(patterns, timeout=10)
        self.current_menu = "main"
        
    def navigate_to_menu(self, menu_path: List[str]) -> None:
        """Navigate through menu hierarchy
        
        Args:
            menu_path: List of menu selections to reach target
        """
        # Always start from main menu
        if self.current_menu != "main":
            self.return_to_main_menu()
            
        for menu_selection in menu_path:
            self.send_input(menu_selection)
            time.sleep(0.5)  # Small delay for menu rendering
            self.wait_for_prompt(["Select", "Enter", "choice", ":"])
            self.menu_stack.append(menu_selection)
            
    def return_to_main_menu(self) -> None:
        """Return to main menu from any submenu"""
        while self.current_menu != "main" and self.menu_stack:
            self.send_input('0')  # Back option
            self.menu_stack.pop()
            time.sleep(0.5)
            
        self.wait_for_main_menu()
        
    # Input Helpers
    
    def enter_form_data(self, field_values: Dict[str, str]) -> None:
        """Enter data for multiple form fields
        
        Args:
            field_values: Dictionary of field prompts and values
        """
        for prompt, value in field_values.items():
            self.wait_for_text(prompt)
            self.send_input(value)
            time.sleep(0.1)  # Small delay between inputs
            
    def select_from_numbered_list(self, item_text: str, timeout: Optional[int] = None) -> None:
        """Select item from a numbered list by finding its number
        
        Args:
            item_text: Text to search for in the list
            timeout: Optional timeout override
        """
        output = self.capture_output(until_pattern="Select", timeout=timeout)
        lines = output.split('\n')
        
        for line in lines:
            if item_text in line:
                # Extract number from line (assuming format "N. Item Text")
                number = line.strip().split('.')[0].strip()
                if number.isdigit():
                    self.send_input(number)
                    return
                    
        raise ValueError(f"Item '{item_text}' not found in list")
        
    # Validation Helpers
    
    def verify_success_message(self, expected_text: str, timeout: Optional[int] = None) -> bool:
        """Verify a success message appears
        
        Args:
            expected_text: Expected success text
            timeout: Optional timeout override
            
        Returns:
            True if message found, False otherwise
        """
        return self.wait_for_text(expected_text, timeout)
        
    def verify_error_message(self, expected_text: str, timeout: Optional[int] = None) -> bool:
        """Verify an error message appears
        
        Args:
            expected_text: Expected error text
            timeout: Optional timeout override
            
        Returns:
            True if message found, False otherwise
        """
        return self.wait_for_text(expected_text, timeout)
        
    def extract_value_from_output(self, label: str, output: Optional[str] = None) -> Optional[str]:
        """Extract value following a label from output
        
        Args:
            label: Label to search for (e.g., "Journey ID:")
            output: Optional output to search in (uses current buffer if None)
            
        Returns:
            Extracted value or None if not found
        """
        if output is None:
            output = self.get_current_output()
            
        lines = output.split('\n')
        for line in lines:
            if label in line:
                # Try to extract value after label
                parts = line.split(label)
                if len(parts) > 1:
                    return parts[1].strip()
                    
        return None
        
    # Utility Methods
    
    def is_alive(self) -> bool:
        """Check if CLI process is still running"""
        return self.process is not None and self.process.isalive()
        
    def get_exit_status(self) -> Optional[int]:
        """Get exit status of CLI process"""
        if self.process and not self.process.isalive():
            return self.process.exitstatus
        return None
        
    def save_output_to_file(self, filepath: str) -> None:
        """Save current output buffer to file for debugging
        
        Args:
            filepath: Path to save output
        """
        output = self.get_current_output()
        with open(filepath, 'w') as f:
            f.write(f"=== CLI Output Captured at {datetime.now()} ===\n")
            f.write(output)
            f.write("\n=== End of Output ===\n")


class CLITestContext:
    """Context manager for CLI testing"""
    
    def __init__(self, cli: JourneyManagerCLI):
        self.cli = cli
        
    def __enter__(self):
        """Start CLI on context entry"""
        self.cli.start()
        return self.cli
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop CLI on context exit"""
        self.cli.stop()
