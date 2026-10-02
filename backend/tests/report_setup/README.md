# Test Report Setup - CloudFront + Private S3

Comprehensive setup and management tools for secure test report hosting using AWS CloudFront and private S3 buckets.

## 📁 Directory Structure

```
tests/report_setup/
├── README.md                          # This file
├── setup_cloudfront_reports.py        # Main setup script (482 lines)
├── setup_secure_reports.sh            # Interactive setup helper
├── upload_reports_to_cloudfront.sh    # Quick upload script
├── load_cloudfront_env.sh             # Environment configuration
├── cloudfront_config.json             # CloudFront configuration (generated)
│
└── docs/
    ├── README_CLOUDFRONT_SETUP.md     # Comprehensive setup guide
    ├── CLOUDFRONT_QUICK_START.md      # Quick 3-step guide
    ├── CLOUDFRONT_PATH_FIX.md         # OriginPath explanation
    └── ... (other documentation)
```

## 🚀 Quick Start

### One-Time Setup (15 minutes)

```bash
cd /opt/mycode/ptr/ai-job-engine/tests/report_setup

# Interactive setup
./setup_secure_reports.sh

# OR direct setup
./setup_cloudfront_reports.py --bucket my-test-reports --region ap-southeast-1
```

### Run Tests with Automatic Upload (Recommended!)

```bash
# ONE simple command (checks everything, loads environment, runs tests, uploads)
./tests/report_setup/run_tests_with_upload.sh unit
```

This wrapper script:
- ✅ Checks AWS credentials are valid
- ✅ Loads CloudFront environment automatically
- ✅ Verifies configuration
- ✅ Runs tests
- ✅ Uploads reports to CloudFront

### Alternative Methods

```bash
# Method 1: Manual environment loading
source tests/report_setup/load_cloudfront_env.sh
./tests/run_tests.sh unit

# Method 2: Upload existing reports only
./tests/report_setup/upload_reports_to_cloudfront.sh

# Method 3: From report_setup directory
cd tests/report_setup
./run_tests_with_upload.sh unit
```

## 🔧 Core Scripts

### `setup_cloudfront_reports.py`

Main setup script that creates the complete infrastructure.

**Usage:**
```bash
./setup_cloudfront_reports.py \
  --bucket my-test-reports \
  --region us-east-1 \
  --prefix test-reports \
  --output cloudfront_config.json
```

**What it does:**
- Creates private S3 bucket with public access blocked
- Creates CloudFront Origin Access Control (OAC)
- Creates CloudFront distribution
- Configures bucket policy for CloudFront-only access
- Saves configuration to JSON file

**Options:**
- `--bucket, -b` - S3 bucket name (required)
- `--region, -r` - AWS region (default: us-east-1)
- `--prefix, -p` - S3 key prefix (default: test-reports)
- `--output, -o` - Output config file (default: cloudfront_config.json)

### `setup_secure_reports.sh`

Interactive setup wizard with prompts.

**Usage:**
```bash
./setup_secure_reports.sh
```

Prompts for:
1. S3 bucket name
2. AWS region

Then runs the full setup and creates environment configuration.

### `upload_reports_to_cloudfront.sh`

Quick upload script for existing test reports.

**Usage:**
```bash
./upload_reports_to_cloudfront.sh
```

**What it does:**
- Finds latest enhanced test report
- Uploads to S3 with correct path structure
- Creates index page with proper links
- Invalidates CloudFront cache
- Shows URLs to access reports

### `load_cloudfront_env.sh`

Environment configuration loader.

**Usage:**
```bash
source load_cloudfront_env.sh
```

**Sets:**
```bash
export S3_BUCKET_NAME="ai-engine-test-reports"
export CLOUDFRONT_DOMAIN="d37vwg02pj6oqg.cloudfront.net"
export S3_REGION="ap-southeast-1"
export UPLOAD_TO_S3="true"
```

## 📖 Documentation

### Quick Guides

**[CLOUDFRONT_QUICK_START.md](docs/CLOUDFRONT_QUICK_START.md)**  
3-step quick start guide. Perfect for getting started quickly.

**[CLOUDFRONT_PATH_FIX.md](docs/CLOUDFRONT_PATH_FIX.md)**  
Explains CloudFront OriginPath and correct URL patterns. Important for troubleshooting.

### Comprehensive Guides

**[README_CLOUDFRONT_SETUP.md](docs/README_CLOUDFRONT_SETUP.md)**  
Complete documentation covering:
- Detailed setup instructions
- Architecture and security
- Cost breakdown
- Troubleshooting
- Advanced configuration (custom domains, authentication)
- CI/CD integration examples

**[CLOUDFRONT_SUCCESS_GUIDE.md](docs/CLOUDFRONT_SUCCESS_GUIDE.md)**  
Usage guide showing:
- What you'll see in reports
- All analytics features
- Interactive controls
- Pro tips

**[FINAL_CLOUDFRONT_SETUP_SUMMARY.md](docs/FINAL_CLOUDFRONT_SETUP_SUMMARY.md)**  
Complete working setup reference with URLs and commands.

## 🔧 Configuration

### cloudfront_config.json

Generated during setup. Contains:

```json
{
  "bucket_name": "ai-engine-test-reports",
  "region": "ap-southeast-1",
  "prefix": "test-reports",
  "distribution_id": "E269STPYK4FJVQ",
  "distribution_domain": "d37vwg02pj6oqg.cloudfront.net",
  "cloudfront_url": "https://d37vwg02pj6oqg.cloudfront.net",
  "oac_id": "E...",
  "created_at": "2025-12-08T07:32:00"
}
```

## 🌐 URL Patterns (Important!)

### CloudFront OriginPath Configuration

```
OriginPath: /test-reports
```

This means CloudFront **automatically adds** `/test-reports` to all URLs!

### Correct URL Patterns

| S3 Path | CloudFront URL |
|---------|----------------|
| `test-reports/index.html` | `https://domain/index.html` |
| `test-reports/unit/TIME/report.html` | `https://domain/unit/TIME/report.html` |

### ❌ Common Mistake

DO NOT include `/test-reports` in CloudFront URLs - it causes double prefix!

- ❌ Wrong: `https://domain/test-reports/unit/...`
- ✅ Correct: `https://domain/unit/...`

## 🔒 Security Features

- ✅ **Private S3 Bucket** - All public access blocked
- ✅ **Origin Access Control (OAC)** - Only CloudFront can access S3
- ✅ **HTTPS Enforced** - TLS 1.2+ everywhere
- ✅ **No Credentials Needed** - View reports via CloudFront URL
- ✅ **Global CDN** - Fast access worldwide

## 📋 Common Tasks

### Upload New Test Reports

```bash
# Method 1: Automatic during tests (from project root)
source tests/report_setup/load_cloudfront_env.sh
./tests/run_tests.sh unit

# Method 2: Quick upload (from project root)
./tests/report_setup/upload_reports_to_cloudfront.sh

# Method 3: From report_setup directory
cd tests/report_setup
source load_cloudfront_env.sh
./upload_reports_to_cloudfront.sh

# Method 4: Manual
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
aws s3 cp test_reports/unit/report.html \
    s3://ai-engine-test-reports/test-reports/unit/$TIMESTAMP/report.html \
    --region ap-southeast-1
```

### Check Distribution Status

```bash
aws cloudfront get-distribution \
  --id $(jq -r '.distribution_id' tests/report_setup/cloudfront_config.json) \
  --query 'Distribution.Status' \
  --output text
```

### Clear CloudFront Cache

```bash
aws cloudfront create-invalidation \
  --distribution-id $(jq -r '.distribution_id' tests/report_setup/cloudfront_config.json) \
  --paths "/*"
```

### List Uploaded Reports

```bash
aws s3 ls s3://ai-engine-test-reports/test-reports/ --recursive
```

## 🔍 Troubleshooting

### Issue: 403 Forbidden

**Cause:** CloudFront still deploying or bucket policy issue  
**Solution:**
```bash
# Check deployment status
aws cloudfront get-distribution --id YOUR_DIST_ID \
  --query 'Distribution.Status' --output text

# Wait until status is "Deployed" (10-15 minutes)
```

### Issue: Same Page Shows When Clicking Link

**Cause:** Wrong URL path (double test-reports prefix) or browser cache  
**Solution:**
1. Clear browser cache (Ctrl+Shift+R)
2. Use direct URL: `https://domain/unit/TIMESTAMP/report.html`
3. Check URL doesn't have `/test-reports/` in path

### Issue: AWS Token Expired

**Solution:**
```bash
aws sso login
# Then try again
```

## 💰 Cost

For typical usage (100 test runs/month):
- S3 storage: $0.005
- S3 PUT requests: $0.002
- CloudFront: FREE (within 1 TB free tier)

**Total: ~$0.01/month**

## 📞 Support

For issues or questions:
- Check [Quick Start Guide](docs/CLOUDFRONT_QUICK_START.md)
- Read [Full Documentation](docs/README_CLOUDFRONT_SETUP.md)
- Review [Path Fix Guide](docs/CLOUDFRONT_PATH_FIX.md)
- Test AWS: `aws sts get-caller-identity`

## 🎯 Working Example

Your current setup:

**Index:**
```
https://d37vwg02pj6oqg.cloudfront.net/index.html
```

**Latest Report:**
```
https://d37vwg02pj6oqg.cloudfront.net/unit/20251208_092927/report.html
```

## ✅ Success Checklist

- [x] CloudFront distribution created
- [x] Private S3 bucket configured
- [x] Origin Access Control (OAC) enabled
- [x] Bucket policy configured
- [x] Test reports uploaded
- [x] Index page created
- [x] URLs verified working
- [x] Documentation complete

## 🎉 Next Steps

1. Bookmark your CloudFront URLs
2. Share with your team (no AWS credentials needed)
3. Integrate with CI/CD pipeline
4. Run tests and enjoy automatic report uploads!

Your secure, comprehensive test reports infrastructure is ready! 🚀

