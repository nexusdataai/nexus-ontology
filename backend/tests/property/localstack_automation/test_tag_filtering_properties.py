"""
Property Tests for BDD Tag Filtering

Feature: localstack-test-automation
Property 5: BDD Tag Filtering

For any set of BDD tags provided to the test executor, the executed scenarios
SHALL only include those matching at least one of the provided tags. If no tags
are provided, all scenarios SHALL be executed.

Validates: Requirements 4.3
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch
import subprocess

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestBDDTagFiltering:
    """Property tests for BDD tag filtering (Property 5)."""
    
    @given(
        tags=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_tags_included_in_command(self, tags: list):
        """
        Feature: localstack-test-automation, Property 5: BDD Tag Filtering
        
        When tags are provided, they are included in the behave command.
        """
        from tests.localstack_automation.test_executor import TestExecutor
        
        with patch.object(TestExecutor, '_get_test_env', return_value={}):
            with patch('tests.localstack_automation.test_executor.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="",
                    stderr=""
                )
                
                executor = TestExecutor()
                executor.run_bdd_tests(tags=tags)
                
                # Verify subprocess was called
                assert mock_run.called
                
                # Get the command that was executed
                call_args = mock_run.call_args
                cmd = call_args[0][0]  # First positional argument
                
                # Verify each tag is in the command
                for tag in tags:
                    # Tags should be prefixed with @ unless they start with ~
                    expected_tag = f"@{tag}" if not tag.startswith("~") else tag
                    assert "--tags" in cmd
                    # Find the tag in command arguments
                    tag_found = any(expected_tag in arg for arg in cmd)
                    assert tag_found, f"Tag {expected_tag} not found in command: {cmd}"
    
    @given(
        exclude_tags=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_exclude_tags_handled_correctly(self, exclude_tags: list):
        """
        Feature: localstack-test-automation, Property 5: BDD Tag Filtering
        
        Exclude tags (prefixed with ~) are passed correctly to behave.
        """
        from tests.localstack_automation.test_executor import TestExecutor
        
        # Prefix tags with ~ for exclusion
        tags = [f"~{tag}" for tag in exclude_tags]
        
        with patch.object(TestExecutor, '_get_test_env', return_value={}):
            with patch('tests.localstack_automation.test_executor.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="",
                    stderr=""
                )
                
                executor = TestExecutor()
                executor.run_bdd_tests(tags=tags)
                
                # Get the command
                call_args = mock_run.call_args
                cmd = call_args[0][0]
                
                # Verify exclude tags are in command (without additional @)
                for tag in tags:
                    assert "--tags" in cmd
                    tag_found = any(tag in arg for arg in cmd)
                    assert tag_found, f"Exclude tag {tag} not found in command"
    
    @settings(max_examples=10, deadline=None)
    def test_no_tags_runs_all_scenarios(self):
        """
        Feature: localstack-test-automation, Property 5: BDD Tag Filtering
        
        When no tags are provided, all scenarios are executed (no --tags argument).
        """
        from tests.localstack_automation.test_executor import TestExecutor
        
        with patch.object(TestExecutor, '_get_test_env', return_value={}):
            with patch('tests.localstack_automation.test_executor.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="",
                    stderr=""
                )
                
                executor = TestExecutor()
                executor.run_bdd_tests(tags=None)
                
                # Get the command
                call_args = mock_run.call_args
                cmd = call_args[0][0]
                
                # Count --tags occurrences - should be 0 when no tags provided
                tags_count = cmd.count("--tags")
                assert tags_count == 0, f"Expected no --tags, found {tags_count} in: {cmd}"
    
    @given(
        include_tags=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
            min_size=1,
            max_size=2
        ),
        exclude_tags=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
            min_size=1,
            max_size=2
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_mixed_include_exclude_tags(self, include_tags: list, exclude_tags: list):
        """
        Feature: localstack-test-automation, Property 5: BDD Tag Filtering
        
        Mixed include and exclude tags are handled correctly.
        """
        from tests.localstack_automation.test_executor import TestExecutor
        
        # Combine include and exclude tags
        tags = include_tags + [f"~{tag}" for tag in exclude_tags]
        
        with patch.object(TestExecutor, '_get_test_env', return_value={}):
            with patch('tests.localstack_automation.test_executor.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="",
                    stderr=""
                )
                
                executor = TestExecutor()
                executor.run_bdd_tests(tags=tags)
                
                # Get the command
                call_args = mock_run.call_args
                cmd = call_args[0][0]
                
                # Verify all tags are present
                for tag in include_tags:
                    expected = f"@{tag}"
                    assert any(expected in arg for arg in cmd), \
                        f"Include tag {expected} not found"
                
                for tag in exclude_tags:
                    expected = f"~{tag}"
                    assert any(expected in arg for arg in cmd), \
                        f"Exclude tag {expected} not found"


class TestTagCommandConstruction:
    """Property tests for tag command construction."""
    
    @given(
        tag=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N', '_')))
    )
    @settings(max_examples=50, deadline=None)
    def test_single_tag_format(self, tag: str):
        """
        Feature: localstack-test-automation, Property 5: BDD Tag Filtering
        
        Single tags are formatted correctly with @ prefix.
        """
        from tests.localstack_automation.test_executor import TestExecutor
        
        with patch.object(TestExecutor, '_get_test_env', return_value={}):
            with patch('tests.localstack_automation.test_executor.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                
                executor = TestExecutor()
                executor.run_bdd_tests(tags=[tag])
                
                cmd = mock_run.call_args[0][0]
                cmd_str = " ".join(cmd)
                
                # Tag should be prefixed with @
                assert f"@{tag}" in cmd_str
    
    @given(
        num_tags=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=None)
    def test_multiple_tags_all_included(self, num_tags: int):
        """
        Feature: localstack-test-automation, Property 5: BDD Tag Filtering
        
        All provided tags are included in the command.
        """
        from tests.localstack_automation.test_executor import TestExecutor
        
        tags = [f"tag{i}" for i in range(num_tags)]
        
        with patch.object(TestExecutor, '_get_test_env', return_value={}):
            with patch('tests.localstack_automation.test_executor.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                
                executor = TestExecutor()
                executor.run_bdd_tests(tags=tags)
                
                cmd = mock_run.call_args[0][0]
                
                # Count --tags occurrences
                tags_count = sum(1 for arg in cmd if arg == "--tags")
                assert tags_count == num_tags, \
                    f"Expected {num_tags} --tags, found {tags_count}"
