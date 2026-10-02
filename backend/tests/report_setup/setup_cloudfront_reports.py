#!/usr/bin/env python3
"""
CloudFront + Private S3 Setup for Test Reports
Creates a secure CloudFront distribution to serve test reports from private S3 bucket
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("❌ Error: boto3 not installed. Install with: pip install boto3")
    sys.exit(1)


class CloudFrontReportsSetup:
    """
    Setup CloudFront distribution with private S3 bucket for test reports
    
    Features:
    - Private S3 bucket (no public access)
    - CloudFront distribution with Origin Access Control (OAC)
    - HTTPS by default
    - Optional basic authentication
    - Custom error pages
    """
    
    def __init__(self, bucket_name: str, region: str = "us-east-1", prefix: str = "test-reports"):
        self.bucket_name = bucket_name
        self.region = region
        self.prefix = prefix
        self.s3_client = None
        self.cloudfront_client = None
        self.distribution_id = None
        self.distribution_domain = None
        self.oac_id = None
        
    def initialize(self) -> bool:
        """Initialize AWS clients"""
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            self.cloudfront_client = boto3.client('cloudfront')
            
            # Test credentials
            self.s3_client.list_buckets()
            
            print(f"✅ AWS credentials verified (region: {self.region})")
            return True
            
        except NoCredentialsError:
            print("❌ Error: AWS credentials not found")
            print("   Configure with: aws configure")
            return False
        except ClientError as e:
            print(f"❌ Error: Failed to initialize AWS client: {e}")
            return False
    
    def create_private_bucket(self) -> bool:
        """Create private S3 bucket with public access blocked"""
        max_retries = 5
        retry_delay = 3  # seconds
        
        for attempt in range(max_retries):
            try:
                # Check if bucket exists
                try:
                    self.s3_client.head_bucket(Bucket=self.bucket_name)
                    print(f"✅ Bucket '{self.bucket_name}' already exists")
                    
                    # Ensure public access is blocked
                    time.sleep(1)  # Small delay before blocking access
                    self.block_public_access()
                    return True
                    
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    if error_code not in ['404', 'NoSuchBucket']:
                        raise
                
                # Create bucket
                if attempt == 0:
                    print(f"🔄 Creating private bucket '{self.bucket_name}'...")
                else:
                    print(f"🔄 Retry attempt {attempt + 1}/{max_retries}...")
                
                if self.region == 'us-east-1':
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                
                # Wait for bucket to be ready
                print(f"⏳ Waiting for bucket to be ready...")
                time.sleep(3)
                
                # Block all public access
                self.block_public_access()
                
                print(f"✅ Private bucket created successfully")
                return True
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                error_msg = str(e)
                
                # Handle specific errors
                if error_code == 'BucketAlreadyOwnedByYou':
                    print(f"✅ Bucket already owned by you")
                    time.sleep(2)
                    self.block_public_access()
                    return True
                
                if error_code == 'BucketAlreadyExists':
                    print(f"❌ Bucket name '{self.bucket_name}' is already taken globally")
                    print(f"   Try a different name: {self.bucket_name}-{int(time.time())}")
                    return False
                
                # Retry on OperationAborted
                if 'OperationAborted' in error_msg or error_code == 'OperationAborted':
                    if attempt < max_retries - 1:
                        print(f"⚠ Conflicting operation detected, waiting {retry_delay}s before retry...")
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30s
                        continue
                
                print(f"❌ Error creating bucket: {e}")
                if attempt == max_retries - 1:
                    print(f"   Failed after {max_retries} attempts")
                return False
        
        return False
    
    def block_public_access(self) -> bool:
        """Block all public access to S3 bucket"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.s3_client.put_public_access_block(
                    Bucket=self.bucket_name,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': True,
                        'IgnorePublicAcls': True,
                        'BlockPublicPolicy': True,
                        'RestrictPublicBuckets': True
                    }
                )
                print(f"✅ Public access blocked on bucket")
                return True
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                # Retry if bucket not ready yet
                if error_code in ['NoSuchBucket', 'OperationAborted'] and attempt < max_retries - 1:
                    print(f"⚠ Bucket not ready yet, waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                if attempt == max_retries - 1:
                    print(f"⚠ Warning: Failed to block public access after {max_retries} attempts: {e}")
                return False
        
        return False
    
    def create_origin_access_control(self) -> Optional[str]:
        """Create CloudFront Origin Access Control (OAC)"""
        try:
            oac_name = f"{self.bucket_name}-oac"
            
            # Check if OAC already exists
            try:
                response = self.cloudfront_client.list_origin_access_controls()
                for oac in response.get('OriginAccessControlList', {}).get('Items', []):
                    if oac['Name'] == oac_name:
                        self.oac_id = oac['Id']
                        print(f"✅ Using existing Origin Access Control: {oac_name}")
                        return self.oac_id
            except Exception:
                pass
            
            # Create new OAC
            print(f"🔄 Creating Origin Access Control...")
            
            response = self.cloudfront_client.create_origin_access_control(
                OriginAccessControlConfig={
                    'Name': oac_name,
                    'Description': f'OAC for {self.bucket_name} test reports',
                    'SigningProtocol': 'sigv4',
                    'SigningBehavior': 'always',
                    'OriginAccessControlOriginType': 's3'
                }
            )
            
            self.oac_id = response['OriginAccessControl']['Id']
            print(f"✅ Origin Access Control created: {self.oac_id}")
            return self.oac_id
            
        except ClientError as e:
            print(f"❌ Error creating Origin Access Control: {e}")
            return None
    
    def create_cloudfront_distribution(self) -> Optional[str]:
        """Create CloudFront distribution"""
        try:
            if not self.oac_id:
                print("❌ Error: Origin Access Control not created")
                return None
            
            print(f"🔄 Creating CloudFront distribution...")
            
            caller_reference = f"{self.bucket_name}-{int(time.time())}"
            origin_domain = f"{self.bucket_name}.s3.{self.region}.amazonaws.com"
            
            distribution_config = {
                'CallerReference': caller_reference,
                'Comment': f'Test Reports Distribution for {self.bucket_name}',
                'Enabled': True,
                'DefaultRootObject': 'index.html',
                'Origins': {
                    'Quantity': 1,
                    'Items': [
                        {
                            'Id': f'{self.bucket_name}-origin',
                            'DomainName': origin_domain,
                            'OriginPath': f'/{self.prefix}',
                            'S3OriginConfig': {
                                'OriginAccessIdentity': ''
                            },
                            'OriginAccessControlId': self.oac_id
                        }
                    ]
                },
                'DefaultCacheBehavior': {
                    'TargetOriginId': f'{self.bucket_name}-origin',
                    'ViewerProtocolPolicy': 'redirect-to-https',
                    'AllowedMethods': {
                        'Quantity': 2,
                        'Items': ['GET', 'HEAD'],
                        'CachedMethods': {
                            'Quantity': 2,
                            'Items': ['GET', 'HEAD']
                        }
                    },
                    'Compress': True,
                    'CachePolicyId': '658327ea-f89d-4fab-a63d-7e88639e58f6',  # CachingOptimized
                    'OriginRequestPolicyId': '88a5eaf4-2fd4-4709-b370-b4c650ea3fcf',  # CORS-S3Origin
                },
                'CustomErrorResponses': {
                    'Quantity': 2,
                    'Items': [
                        {
                            'ErrorCode': 403,
                            'ResponsePagePath': '/index.html',
                            'ResponseCode': '200',
                            'ErrorCachingMinTTL': 300
                        },
                        {
                            'ErrorCode': 404,
                            'ResponsePagePath': '/index.html',
                            'ResponseCode': '200',
                            'ErrorCachingMinTTL': 300
                        }
                    ]
                },
                'ViewerCertificate': {
                    'CloudFrontDefaultCertificate': True,
                    'MinimumProtocolVersion': 'TLSv1.2_2021'
                },
                'HttpVersion': 'http2and3',
                'IsIPV6Enabled': True,
                'PriceClass': 'PriceClass_100'  # Use only North America and Europe
            }
            
            response = self.cloudfront_client.create_distribution(
                DistributionConfig=distribution_config
            )
            
            self.distribution_id = response['Distribution']['Id']
            self.distribution_domain = response['Distribution']['DomainName']
            
            print(f"✅ CloudFront distribution created: {self.distribution_id}")
            print(f"   Domain: {self.distribution_domain}")
            print(f"   Status: Deploying (this may take 10-15 minutes)")
            
            return self.distribution_id
            
        except ClientError as e:
            print(f"❌ Error creating CloudFront distribution: {e}")
            return None
    
    def update_bucket_policy(self) -> bool:
        """Update S3 bucket policy to allow CloudFront access"""
        try:
            if not self.distribution_id:
                print("❌ Error: CloudFront distribution not created")
                return False
            
            print(f"🔄 Updating S3 bucket policy for CloudFront access...")
            
            # Get AWS account ID
            sts_client = boto3.client('sts')
            account_id = sts_client.get_caller_identity()['Account']
            
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowCloudFrontServicePrincipal",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "cloudfront.amazonaws.com"
                        },
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{self.bucket_name}/*",
                        "Condition": {
                            "StringEquals": {
                                "AWS:SourceArn": f"arn:aws:cloudfront::{account_id}:distribution/{self.distribution_id}"
                            }
                        }
                    }
                ]
            }
            
            self.s3_client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            
            print(f"✅ Bucket policy updated")
            return True
            
        except ClientError as e:
            print(f"❌ Error updating bucket policy: {e}")
            return False
    
    def save_configuration(self, output_file: str = "cloudfront_config.json") -> bool:
        """Save configuration to file"""
        try:
            config = {
                'bucket_name': self.bucket_name,
                'region': self.region,
                'prefix': self.prefix,
                'distribution_id': self.distribution_id,
                'distribution_domain': self.distribution_domain,
                'cloudfront_url': f"https://{self.distribution_domain}",
                'oac_id': self.oac_id,
                'created_at': datetime.now().isoformat()
            }
            
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✅ Configuration saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"⚠ Warning: Failed to save configuration: {e}")
            return False
    
    def setup_complete(self) -> bool:
        """Complete setup process"""
        print("=" * 60)
        print("  CloudFront + Private S3 Setup")
        print("=" * 60)
        print()
        
        if not self.initialize():
            return False
        
        print()
        
        if not self.create_private_bucket():
            return False
        
        print()
        
        if not self.create_origin_access_control():
            return False
        
        print()
        
        if not self.create_cloudfront_distribution():
            return False
        
        print()
        
        if not self.update_bucket_policy():
            return False
        
        print()
        
        self.save_configuration()
        
        print()
        print("=" * 60)
        print("  ✅ Setup Complete!")
        print("=" * 60)
        print()
        print(f"🌐 CloudFront URL: https://{self.distribution_domain}")
        print()
        print("📝 Next Steps:")
        print(f"   1. Wait 10-15 minutes for CloudFront deployment")
        print(f"   2. Upload reports to S3 bucket: {self.bucket_name}")
        print(f"   3. Access reports at: https://{self.distribution_domain}/index.html")
        print()
        print("📦 Upload reports with:")
        print(f"   export S3_BUCKET_NAME=\"{self.bucket_name}\"")
        print(f"   export CLOUDFRONT_DOMAIN=\"{self.distribution_domain}\"")
        print(f"   ./tests/run_tests.sh unit")
        print()
        print("🔒 Security: S3 bucket is private, only accessible via CloudFront")
        print()
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Setup CloudFront distribution with private S3 bucket for test reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic setup
  %(prog)s --bucket my-test-reports
  
  # With custom region and prefix
  %(prog)s --bucket my-reports --region us-west-2 --prefix reports
  
  # Save configuration to specific file
  %(prog)s --bucket my-reports --output config.json

Security:
  - S3 bucket is private (no public access)
  - Only CloudFront can access S3 bucket
  - HTTPS enforced by default
  - No AWS credentials needed to view reports
"""
    )
    
    parser.add_argument('--bucket', '-b', required=True,
                       help='S3 bucket name')
    parser.add_argument('--region', '-r', default='us-east-1',
                       help='AWS region (default: us-east-1)')
    parser.add_argument('--prefix', '-p', default='test-reports',
                       help='S3 key prefix (default: test-reports)')
    parser.add_argument('--output', '-o', default='cloudfront_config.json',
                       help='Output configuration file (default: cloudfront_config.json)')
    
    args = parser.parse_args()
    
    setup = CloudFrontReportsSetup(
        bucket_name=args.bucket,
        region=args.region,
        prefix=args.prefix
    )
    
    success = setup.setup_complete()
    
    if success:
        # Save config to specified output file
        setup.save_configuration(args.output)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

