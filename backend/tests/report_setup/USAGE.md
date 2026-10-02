# CloudFront Test Reports - Quick Usage Guide

All CloudFront report setup tools are in: `tests/report_setup/`

## 🚀 Quick Commands

### From Project Root

```bash
# Upload existing reports
./tests/report_setup/upload_reports_to_cloudfront.sh

# Load environment and run tests
source tests/report_setup/load_cloudfront_env.sh
./tests/run_tests.sh unit

# View configuration
cat tests/report_setup/cloudfront_config.json

# Read documentation
cat tests/report_setup/README.md
```

### From report_setup Directory

```bash
cd tests/report_setup

# Upload reports
./upload_reports_to_cloudfront.sh

# Load environment
source load_cloudfront_env.sh
cd ../..
./tests/run_tests.sh unit

# Setup new CloudFront
./setup_secure_reports.sh

# View docs
cat README.md
cat docs/CLOUDFRONT_QUICK_START.md
```

## 📖 Documentation

All documentation is in `tests/report_setup/docs/`:

- **CLOUDFRONT_QUICK_START.md** - 3-step quick start
- **README_CLOUDFRONT_SETUP.md** - Comprehensive setup guide
- **CLOUDFRONT_PATH_FIX.md** - OriginPath explanation
- **CLOUDFRONT_SUCCESS_GUIDE.md** - Features and usage
- **FINAL_CLOUDFRONT_SETUP_SUMMARY.md** - Complete reference
- **REFACTORING_SUMMARY.md** - Refactoring details

## 🌐 Your URLs

**Index:**
```
https://d37vwg02pj6oqg.cloudfront.net/index.html
```

**Latest Report:**
```
https://d37vwg02pj6oqg.cloudfront.net/unit/20251208_092927/report.html
```

## 🔧 Configuration

Your CloudFront configuration:
```
Distribution ID: E269STPYK4FJVQ
Domain: d37vwg02pj6oqg.cloudfront.net
S3 Bucket: ai-engine-test-reports
Region: ap-southeast-1
```

View full config:
```bash
cat tests/report_setup/cloudfront_config.json
```

## 📋 Common Tasks

### Upload Reports After Tests

```bash
# If tests already run, just upload
./tests/report_setup/upload_reports_to_cloudfront.sh
```

### Run Tests with Automatic Upload

```bash
# Load environment first
source tests/report_setup/load_cloudfront_env.sh

# Verify it's loaded
echo $UPLOAD_TO_S3          # Should show: true
echo $CLOUDFRONT_DOMAIN     # Should show: d37vwg02pj6oqg.cloudfront.net

# Run tests
./tests/run_tests.sh unit
```

### Check What's Uploaded

```bash
aws s3 ls s3://ai-engine-test-reports/test-reports/ --recursive
```

### Clear CloudFront Cache

```bash
aws cloudfront create-invalidation \
  --distribution-id E269STPYK4FJVQ \
  --paths "/*"
```

## 💡 Pro Tips

1. **Always use full paths** from project root for clarity
2. **Load environment** before running tests for auto-upload
3. **Check environment variables** before running tests:
   ```bash
   echo $UPLOAD_TO_S3  # Should be "true"
   ```
4. **Access reports via CloudFront** URLs (no test-reports prefix)
5. **Bookmark your index** for quick access

## 🎯 Remember

**CloudFront OriginPath** = `/test-reports`

This means:
- Upload to S3: `test-reports/unit/TIMESTAMP/report.html`
- Access via: `https://domain/unit/TIMESTAMP/report.html` (CloudFront adds prefix)

**Do NOT** include `/test-reports` in CloudFront URLs!

## ✅ Everything You Need

All in one place: `tests/report_setup/`

- Setup scripts ✅
- Upload tools ✅
- Configuration ✅
- Documentation ✅
- Working examples ✅

Your secure test reports infrastructure is ready to use! 🚀

