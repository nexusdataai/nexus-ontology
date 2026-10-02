"""
Property Tests for CLI Argument Parsing

Feature: localstack-test-automation
Property 8: CLI Argument Parsing

For any valid combination of CLI arguments, the parsed configuration SHALL
correctly reflect the provided values.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.localstack_automation.runner import parse_arguments
from tests.localstack_automation.models import TestType


class TestCLIArgumentParsing:
    """Property tests for CLI argument parsing (Property 8)."""
    
    @given(skip_localstack=st.booleans())
    @settings(max_examples=10, deadline=None)
    def test_skip_localstack_flag(self, skip_localstack: bool):
        """
        Feature: localstack-test-automation, Property 8: CLI Argument Parsing
        
        --skip-localstack flag correctly sets skip_localstack=True.
        """
        args = ['all']
        if skip_localstack:
            args.append('--skip-localstack')
        
        config = parse_arguments(args)
        
        assert config.skip_localstack == skip_localstack
    
    @given(skip_gateway=st.booleans())
    @settings(max_examples=10, deadline=None)
    def test_skip_gateway_flag(self, skip_gateway: bool):
        """
        Feature: localstack-test-automation, Property 8: CLI Argument Parsing
        
        --skip-gateway flag correctly sets skip_gateway=True.
        """
        args = ['all']
        if skip_gateway:
            args.append('--skip-gateway')
        
        config = parse_arguments(args)
        
        assert config.skip_gateway == skip_gateway
    
    @given(upload=st.booleans())
    @settings(max_examples=10, deadline=None)
    def test_upload_flag(self, upload: bool):
        """
        Feature: localstack-test-automation, Property 8: CLI Argument Parsing
        
        --upload flag correctly sets upload_to_s3=True.
        """
        args = ['all']
        if upload:
            args.append('--upload')
        
        config = parse_arguments(args)
        
        assert config.upload_to_s3 == upload
    
    @given(keep_running=st.booleans())
    @settings(max_examples=10, deadline=None)
    def test_keep_running_flag(self, keep_running: bool):
        """
        Feature: localstack-test-automation, Property 8: CLI Argument Parsing
        
        --keep-running flag correctly sets keep_running=True.
        """
        args = ['all']
        if keep_running:
            args.append('--keep-running')
        
        config = parse_arguments(args)
        
        assert config.keep_running == keep_running
    
    @given(duration=st.integers(min_value=1, max_value=3600))
    @settings(max_examples=30, deadline=None)
    def test_duration_argument(self, duration: int):
        """
        Feature: localstack-test-automation, Property 8: CLI Argument Parsing
        
        --duration N correctly sets endurance_duration=N.
        """
        args = ['endurance', '--duration', str(duration)]
        
        config = parse_arguments(args)
        
        assert config.endurance_duration == duration
    
    @given(
        tags=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_tags_argument(self, tags: list):
        """
        Feature: localstack-test-automation, Property 8: CLI Argument Parsing
        
        --tags tag1,tag2 correctly sets bdd_tags=['tag1', 'tag2'].
        """
        tags_str = ','.join(tags)
        args = ['bdd', '--tags', tags_str]
        
        config = parse_arguments(args)
        
        assert config.bdd_tags == tags


class TestCLITestTypeSelection:
    """Property tests for test type selection."""
    
    @given(
        test_type=st.sampled_from(['integration', 'bdd', 'endurance', 'all'])
    )
    @settings(max_examples=10, deadline=None)
    def test_single_test_type(self, test_type: str):
        """
        Feature: localstack-test-automation, Property 8: CLI Argument Parsing
        
        Single test type argument is correctly parsed.
        """
        args = [test_type]
        
        config = parse_arguments(args)
        
        assert TestType(test_type) in config.test_types
    
    @given(
        types=st.lists(
            st.sampled_from(['integration', 'bdd', 'endurance']),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_multiple_test_types(self, types: list):
        """
        Feature: localstack-test-automation, Property 8: CLI Argument Parsing
        
        Multiple test type arguments are correctly parsed.
        """
        config = parse_arguments(types)
        
        for t in types:
            assert TestType(t) in config.test_types


class TestCLICombinedArguments:
    """Property tests for combined CLI arguments."""
    
    @given(
        skip_localstack=st.booleans(),
        skip_gateway=st.booleans(),
        upload=st.booleans(),
        keep_running=st.booleans(),
        cleanup=st.booleans()
    )
    @settings(max_examples=50, deadline=None)
    def test_all_boolean_flags_combined(
        self,
        skip_localstack: bool,
        skip_gateway: bool,
        upload: bool,
        keep_running: bool,
        cleanup: bool
    ):
        """
        Feature: localstack-test-automation, Property 8: CLI Argument Parsing
        
        All boolean flags can be combined correctly.
        """
        args = ['all']
        if skip_localstack:
            args.append('--skip-localstack')
        if skip_gateway:
            args.append('--skip-gateway')
        if upload:
            args.append('--upload')
        if keep_running:
            args.append('--keep-running')
        if cleanup:
            args.append('--cleanup')
        
        config = parse_arguments(args)
        
        assert config.skip_localstack == skip_localstack
        assert config.skip_gateway == skip_gateway
        assert config.upload_to_s3 == upload
        assert config.keep_running == keep_running
        assert config.cleanup == cleanup
    
    @given(
        duration=st.integers(min_value=1, max_value=3600),
        tags=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
            min_size=1,
            max_size=3
        ),
        upload=st.booleans()
    )
    @settings(max_examples=30, deadline=None)
    def test_value_and_flag_arguments_combined(
        self,
        duration: int,
        tags: list,
        upload: bool
    ):
        """
        Feature: localstack-test-automation, Property 8: CLI Argument Parsing
        
        Value arguments and flags can be combined correctly.
        """
        args = ['all', '--duration', str(duration), '--tags', ','.join(tags)]
        if upload:
            args.append('--upload')
        
        config = parse_arguments(args)
        
        assert config.endurance_duration == duration
        assert config.bdd_tags == tags
        assert config.upload_to_s3 == upload
