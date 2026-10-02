"""
Property Tests for S3 Upload Key Structure

Feature: localstack-test-automation
Property 7: S3 Upload Key Structure

For any report upload, the S3 key SHALL follow the pattern
`{test_type}/{timestamp}/report.html` where test_type is one of
(integration, bdd, endurance) and timestamp is in the format `YYYYMMDD_HHMMSS`.
The content-type header SHALL be set to `text/html; charset=utf-8`.

Validates: Requirements 7.2, 7.4
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
import re

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.localstack_automation.s3_uploader import S3ReportUploader


class TestS3UploadKeyStructure:
    """Property tests for S3 upload key structure (Property 7)."""
    
    @given(
        test_type=st.sampled_from(['integration', 'bdd', 'endurance']),
        timestamp=st.from_regex(r'[0-9]{8}_[0-9]{6}', fullmatch=True)
    )
    @settings(max_examples=50, deadline=None)
    def test_s3_key_follows_pattern(self, test_type: str, timestamp: str):
        """
        Feature: localstack-test-automation, Property 7: S3 Upload Key Structure
        
        S3 keys follow the pattern {test_type}/{timestamp}/{filename}.
        """
        with patch('tests.localstack_automation.s3_uploader.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.head_bucket.return_value = {}
            mock_client.put_object.return_value = {}
            
            uploader = S3ReportUploader(
                bucket_name="test-reports",
                endpoint_url="http://localhost:4566"
            )
            
            # Create temp file
            with tempfile.NamedTemporaryFile(
                suffix='.html', 
                prefix=f'{test_type}_report_',
                delete=False
            ) as f:
                f.write(b"<html></html>")
                temp_path = Path(f.name)
            
            try:
                uploader.upload_reports([temp_path], prefix=timestamp)
                
                # Verify put_object was called
                assert mock_client.put_object.called
                
                # Get the S3 key used
                call_kwargs = mock_client.put_object.call_args[1]
                s3_key = call_kwargs['Key']
                
                # Verify key structure
                parts = s3_key.split('/')
                assert len(parts) == 3, f"Expected 3 parts in key, got {len(parts)}: {s3_key}"
                assert parts[0] == test_type, f"Test type mismatch: {parts[0]} != {test_type}"
                assert parts[1] == timestamp, f"Timestamp mismatch: {parts[1]} != {timestamp}"
                
            finally:
                temp_path.unlink(missing_ok=True)
    
    @given(
        file_ext=st.sampled_from(['.html', '.json', '.css', '.js'])
    )
    @settings(max_examples=20, deadline=None)
    def test_content_type_set_correctly(self, file_ext: str):
        """
        Feature: localstack-test-automation, Property 7: S3 Upload Key Structure
        
        Content-type header is set correctly based on file type.
        """
        with patch('tests.localstack_automation.s3_uploader.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.head_bucket.return_value = {}
            mock_client.put_object.return_value = {}
            
            uploader = S3ReportUploader(
                bucket_name="test-reports",
                endpoint_url="http://localhost:4566"
            )
            
            # Create temp file with specific extension
            with tempfile.NamedTemporaryFile(
                suffix=file_ext,
                prefix='test_',
                delete=False
            ) as f:
                f.write(b"test content")
                temp_path = Path(f.name)
            
            try:
                uploader.upload_report(temp_path, f"test/report{file_ext}")
                
                # Verify content type
                call_kwargs = mock_client.put_object.call_args[1]
                content_type = call_kwargs['ContentType']
                
                expected_types = {
                    '.html': 'text/html; charset=utf-8',
                    '.json': 'application/json',
                    '.css': 'text/css',
                    '.js': 'application/javascript'
                }
                
                assert content_type == expected_types[file_ext], \
                    f"Content-type mismatch for {file_ext}: {content_type}"
                
            finally:
                temp_path.unlink(missing_ok=True)
    
    @settings(max_examples=10, deadline=None)
    def test_html_content_type_has_charset(self):
        """
        Feature: localstack-test-automation, Property 7: S3 Upload Key Structure
        
        HTML files have content-type with charset=utf-8.
        """
        with patch('tests.localstack_automation.s3_uploader.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.head_bucket.return_value = {}
            mock_client.put_object.return_value = {}
            
            uploader = S3ReportUploader(
                bucket_name="test-reports",
                endpoint_url="http://localhost:4566"
            )
            
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
                f.write(b"<html></html>")
                temp_path = Path(f.name)
            
            try:
                uploader.upload_report(temp_path, "test/report.html")
                
                call_kwargs = mock_client.put_object.call_args[1]
                content_type = call_kwargs['ContentType']
                
                assert 'charset=utf-8' in content_type, \
                    f"HTML content-type missing charset: {content_type}"
                
            finally:
                temp_path.unlink(missing_ok=True)


class TestS3URLGeneration:
    """Property tests for S3 URL generation."""
    
    @given(
        bucket=st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')),
        key=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='/_-.'))
    )
    @settings(max_examples=50, deadline=None)
    def test_localstack_url_format(self, bucket: str, key: str):
        """
        Feature: localstack-test-automation, Property 7: S3 Upload Key Structure
        
        LocalStack URLs follow the correct format.
        """
        assume(bucket[0].isalnum() and bucket[-1].isalnum())
        assume(not key.startswith('/'))
        
        endpoint = "http://localhost:4566"
        uploader = S3ReportUploader(
            bucket_name=bucket,
            endpoint_url=endpoint
        )
        
        url = uploader.get_report_url(key)
        
        expected = f"{endpoint}/{bucket}/{key}"
        assert url == expected, f"URL mismatch: {url} != {expected}"
    
    @given(
        bucket=st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')),
        region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1']),
        key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='/_-.'))
    )
    @settings(max_examples=30, deadline=None)
    def test_aws_url_format(self, bucket: str, region: str, key: str):
        """
        Feature: localstack-test-automation, Property 7: S3 Upload Key Structure
        
        AWS S3 URLs follow the correct format.
        """
        assume(bucket[0].isalnum() and bucket[-1].isalnum())
        assume(not key.startswith('/'))
        
        uploader = S3ReportUploader(
            bucket_name=bucket,
            endpoint_url=None,  # AWS mode
            region=region
        )
        
        url = uploader.get_report_url(key)
        
        expected = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        assert url == expected, f"URL mismatch: {url} != {expected}"


class TestTestTypeExtraction:
    """Property tests for test type extraction from filenames."""
    
    @given(
        test_type=st.sampled_from(['integration', 'bdd', 'endurance']),
        suffix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', '_')))
    )
    @settings(max_examples=50, deadline=None)
    def test_extracts_test_type_from_filename(self, test_type: str, suffix: str):
        """
        Feature: localstack-test-automation, Property 7: S3 Upload Key Structure
        
        Test type is correctly extracted from report filename.
        """
        uploader = S3ReportUploader()
        
        filename = f"{test_type}_report_{suffix}.html"
        path = Path(filename)
        
        extracted = uploader._extract_test_type(path)
        
        assert extracted == test_type, \
            f"Extracted '{extracted}' from '{filename}', expected '{test_type}'"
