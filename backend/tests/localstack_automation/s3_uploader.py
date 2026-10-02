"""
S3 Report Uploader

Uploads test reports to S3 (LocalStack or AWS).
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
import mimetypes

from .logging_config import get_logger, TestAutomationLogger


class S3ReportUploader:
    """Uploads test reports to S3."""
    
    def __init__(
        self,
        bucket_name: str = "test-reports",
        endpoint_url: Optional[str] = None,
        region: str = "us-east-1"
    ):
        """
        Initialize S3 uploader.
        
        Args:
            bucket_name: S3 bucket name for reports
            endpoint_url: LocalStack endpoint URL (None for AWS)
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region = region
        self.logger = get_logger()
        self._client = None
    
    @property
    def client(self):
        """Lazy-load S3 client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self):
        """Create boto3 S3 client."""
        try:
            import boto3
        except ImportError:
            TestAutomationLogger.log_error("boto3 not installed")
            raise
        
        client_kwargs = {
            "service_name": "s3",
            "region_name": self.region
        }
        
        if self.endpoint_url:
            # LocalStack configuration
            client_kwargs.update({
                "endpoint_url": self.endpoint_url,
                "aws_access_key_id": "test",
                "aws_secret_access_key": "test"
            })
        
        return boto3.client(**client_kwargs)

    def ensure_bucket_exists(self) -> bool:
        """
        Create bucket if it doesn't exist.
        
        Returns:
            True if bucket exists or was created, False on error
        """
        from botocore.exceptions import ClientError
        
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            self.logger.info(f"Bucket {self.bucket_name} exists")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ('404', 'NoSuchBucket'):
                # Bucket doesn't exist, create it
                try:
                    if self.region == "us-east-1":
                        self.client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    TestAutomationLogger.log_success(f"Created bucket: {self.bucket_name}")
                    return True
                except ClientError as create_error:
                    TestAutomationLogger.log_error(f"Failed to create bucket: {create_error}")
                    return False
            else:
                TestAutomationLogger.log_error(f"Error checking bucket: {e}")
                return False
    
    def upload_report(self, local_path: Path, s3_key: str) -> str:
        """
        Upload a single report file.
        
        Args:
            local_path: Path to local file
            s3_key: S3 object key
            
        Returns:
            S3 URL of uploaded file
        """
        from botocore.exceptions import ClientError
        
        # Determine content type
        content_type = self._get_content_type(local_path)
        
        try:
            self.logger.info(f"Uploading {local_path.name} to s3://{self.bucket_name}/{s3_key}")
            
            with open(local_path, 'rb') as f:
                self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=f.read(),
                    ContentType=content_type
                )
            
            url = self.get_report_url(s3_key)
            self.logger.info(f"Uploaded: {url}")
            return url
            
        except ClientError as e:
            TestAutomationLogger.log_error(f"Failed to upload {local_path}: {e}")
            raise
        except FileNotFoundError:
            TestAutomationLogger.log_error(f"File not found: {local_path}")
            raise

    def upload_reports(self, report_paths: List[Path], prefix: Optional[str] = None) -> List[str]:
        """
        Upload multiple reports with timestamp-based key structure.
        
        Args:
            report_paths: List of local file paths
            prefix: Optional prefix for S3 keys (defaults to timestamp)
            
        Returns:
            List of S3 URLs for uploaded files
        """
        TestAutomationLogger.log_step(f"Uploading {len(report_paths)} reports to S3...")
        
        # Ensure bucket exists
        if not self.ensure_bucket_exists():
            TestAutomationLogger.log_error("Cannot upload: bucket not available")
            return []
        
        # Generate timestamp prefix if not provided
        if prefix is None:
            prefix = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        uploaded_urls = []
        
        for path in report_paths:
            try:
                # Determine test type from filename
                test_type = self._extract_test_type(path)
                
                # Build S3 key: {test_type}/{timestamp}/{filename}
                s3_key = f"{test_type}/{prefix}/{path.name}"
                
                url = self.upload_report(path, s3_key)
                uploaded_urls.append(url)
                
            except Exception as e:
                TestAutomationLogger.log_warning(f"Failed to upload {path}: {e}")
                continue
        
        if uploaded_urls:
            TestAutomationLogger.log_success(f"Uploaded {len(uploaded_urls)} reports")
        else:
            TestAutomationLogger.log_warning("No reports were uploaded")
        
        return uploaded_urls
    
    def get_report_url(self, s3_key: str) -> str:
        """
        Get the URL for accessing a report.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            URL string
        """
        if self.endpoint_url:
            # LocalStack URL format
            return f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
        else:
            # AWS S3 URL format
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
    
    def _get_content_type(self, path: Path) -> str:
        """Get content type for file."""
        content_type, _ = mimetypes.guess_type(str(path))
        
        if content_type is None:
            # Default based on extension
            ext = path.suffix.lower()
            type_map = {
                '.html': 'text/html; charset=utf-8',
                '.json': 'application/json',
                '.css': 'text/css',
                '.js': 'application/javascript',
                '.txt': 'text/plain'
            }
            content_type = type_map.get(ext, 'application/octet-stream')
        
        # Ensure HTML has charset
        if content_type == 'text/html':
            content_type = 'text/html; charset=utf-8'
        
        return content_type
    
    def _extract_test_type(self, path: Path) -> str:
        """Extract test type from filename."""
        name = path.stem.lower()
        
        if 'integration' in name:
            return 'integration'
        elif 'bdd' in name:
            return 'bdd'
        elif 'endurance' in name:
            return 'endurance'
        elif 'index' in name:
            return 'index'
        else:
            return 'other'
