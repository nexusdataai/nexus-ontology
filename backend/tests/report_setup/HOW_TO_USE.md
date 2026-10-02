# How to Use CloudFront Test Reports

## 🚀 Quick Start

### Running Tests with Automatic Upload

**IMPORTANT**: You must load the environment **in the same terminal session** before running tests!

```bash
# Step 1: Load environment (in same terminal!)
source tests/report_setup/load_cloudfront_env.sh

# Step 2: Verify environment is loaded
echo $UPLOAD_TO_S3          # Should show: true
echo $CLOUDFRONT_DOMAIN     # Should show: d37vwg02pj6oqg.cloudfront.net

# Step 3: Run tests (reports will upload automatically)
./tests/run_tests.sh unit
```

### What You'll See

When environment is loaded correctly:
```
✅ Using CloudFront uploader
S3 Bucket: ai-engine-test-reports
Region: ap-southeast-1
CloudFront: d37vwg02pj6oqg.cloudfront.net

🔄 Uploading enhanced report...
✅ Report uploaded
✅ Index uploaded
🔄 Invalidating cache...
✅ Cache invalidated

View reports at: https://d37vwg02pj6oqg.cloudfront.net/index.html
```

## ❌ Common Mistake

**Wrong (will NOT upload):**
```bash
# Terminal 1:
source tests/report_setup/load_cloudfront_env.sh

# Terminal 2 (DIFFERENT terminal!):
./tests/run_tests.sh unit    # ❌ Environment not loaded in this terminal!
```

**Correct (will upload):**
```bash
# Same terminal:
source tests/report_setup/load_cloudfront_env.sh
./tests/run_tests.sh unit    # ✅ Environment loaded in same terminal!
```

## 📋 Three Ways to Upload

### Method 1: Automatic During Tests (Recommended)

```bash
# In ONE terminal session:
source tests/report_setup/load_cloudfront_env.sh
./tests/run_tests.sh unit
```

**When to use:** Running new tests and want automatic upload

### Method 2: Upload Existing Reports (Quick)

```bash
# No environment needed!
./tests/report_setup/upload_reports_to_cloudfront.sh
```

**When to use:** Tests already run, just want to upload

### Method 3: Manual S3 Upload (Advanced)

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
aws s3 cp test_reports/unit/unit_test_report_enhanced_*.html \
    s3://ai-engine-test-reports/test-reports/unit/$TIMESTAMP/report.html \
    --region ap-southeast-1

# Access via:
https://d37vwg02pj6oqg.cloudfront.net/unit/$TIMESTAMP/report.html
```

**When to use:** Custom scripting or CI/CD

## 🔍 Troubleshooting

### Reports Not Uploading

**Symptom:** Tests run but no S3 upload messages

**Check:**
```bash
echo $UPLOAD_TO_S3
```

**If empty or not "true":**
```bash
source tests/report_setup/load_cloudfront_env.sh
./tests/run_tests.sh unit
```

### Wrong Terminal Session

**Symptom:** Sourced environment in one terminal, ran tests in another

**Solution:** Use same terminal or export globally:
```bash
# Add to ~/.bashrc for all terminals
echo "source /opt/mycode/ptr/ai-job-engine/tests/report_setup/load_cloudfront_env.sh" >> ~/.bashrc
source ~/.bashrc
```

### Upload Script Not Found

**Symptom:** "CloudFront uploader not found"

**Check:**
```bash
ls -la tests/report_setup/upload_reports_to_cloudfront.sh
```

**Should be:** Executable script in tests/report_setup/

## 💡 Pro Tips

### Tip 1: Verify Before Running

Always check environment before running tests:
```bash
# Check all required variables
echo "UPLOAD_TO_S3: $UPLOAD_TO_S3"
echo "S3_BUCKET_NAME: $S3_BUCKET_NAME"
echo "CLOUDFRONT_DOMAIN: $CLOUDFRONT_DOMAIN"
echo "S3_REGION: $S3_REGION"
```

### Tip 2: Create Alias

Add to `~/.bashrc`:
```bash
alias load-cloudfront='source /opt/mycode/ptr/ai-job-engine/tests/report_setup/load_cloudfront_env.sh'
alias upload-reports='/opt/mycode/ptr/ai-job-engine/tests/report_setup/upload_reports_to_cloudfront.sh'
```

Then:
```bash
load-cloudfront
./tests/run_tests.sh unit
```

### Tip 3: CI/CD Integration

```yaml
# GitHub Actions / GitLab CI
script:
  - source tests/report_setup/load_cloudfront_env.sh
  - ./tests/run_tests.sh unit
  - echo "Reports at https://$CLOUDFRONT_DOMAIN/index.html"
```

### Tip 4: Quick Check

See what reports are uploaded:
```bash
aws s3 ls s3://ai-engine-test-reports/test-reports/ --recursive --human-readable
```

### Tip 5: Force Refresh

If reports don't update, clear CloudFront cache:
```bash
aws cloudfront create-invalidation \
  --distribution-id E269STPYK4FJVQ \
  --paths "/*"
```

## 🌐 Your URLs

**Index:**
```
https://d37vwg02pj6oqg.cloudfront.net/index.html
```

**Latest Report:**
```
https://d37vwg02pj6oqg.cloudfront.net/unit/20251208_092927/report.html
```

## 📖 More Help

- **Quick Reference**: `tests/report_setup/USAGE.md`
- **Main README**: `tests/report_setup/README.md`
- **Quick Start**: `tests/report_setup/docs/CLOUDFRONT_QUICK_START.md`
- **Full Guide**: `tests/report_setup/docs/README_CLOUDFRONT_SETUP.md`

## ✅ Summary

**For automatic upload during tests:**
```bash
source tests/report_setup/load_cloudfront_env.sh
./tests/run_tests.sh unit
```

**For manual upload of existing reports:**
```bash
./tests/report_setup/upload_reports_to_cloudfront.sh
```

That's it! 🚀

