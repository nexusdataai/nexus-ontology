# ============================================================================
# LocalStack Initialization Script for nexus-backend (Windows PowerShell)
# ============================================================================

param(
    [string]$Endpoint = "http://localhost:4566",
    [string]$Region = "us-east-1"
)

$ErrorActionPreference = "Continue"

$env:AWS_ACCESS_KEY_ID = "test"
$env:AWS_SECRET_ACCESS_KEY = "test"
$env:AWS_DEFAULT_REGION = $Region

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Initializing nexus-backend LocalStack" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Endpoint: $Endpoint"
Write-Host "Region:   $Region"
Write-Host ""

# Wait for LocalStack
Write-Host "Waiting for LocalStack to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1
$localstackReady = $false

while ($attempt -le $maxAttempts) {
    try {
        $health = Invoke-RestMethod -Uri "$Endpoint/_localstack/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($health.services.dynamodb) {
            Write-Host "[OK] LocalStack is ready" -ForegroundColor Green
            $localstackReady = $true
            break
        }
    }
    catch {
        # Ignore errors, keep trying
    }
    Write-Host "  Attempt $attempt/$maxAttempts - waiting..."
    Start-Sleep -Seconds 2
    $attempt++
}

if (-not $localstackReady) {
    Write-Host "[FAIL] LocalStack failed to start within timeout" -ForegroundColor Red
    exit 1
}

# Create DynamoDB table with GSI
Write-Host ""
Write-Host "--- Creating DynamoDB Tables ---" -ForegroundColor Cyan
Write-Host "Creating DynamoDB table: TransformationSystem..." -ForegroundColor Yellow

$tableExists = $false
try {
    $tableJson = aws dynamodb describe-table --endpoint-url $Endpoint --region $Region --table-name "TransformationSystem" 2>$null
    if ($tableJson) {
        $tableExists = $true
        Write-Host "  Table already exists" -ForegroundColor Green
    }
}
catch {
    $tableExists = $false
}

if (-not $tableExists) {
    # Create table with GSI using inline JSON (escaped for Windows)
    $gsiJson = '[{\"IndexName\":\"GSI1\",\"KeySchema\":[{\"AttributeName\":\"GSI1PK\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"GSI1SK\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}]'
    
    $result = aws dynamodb create-table `
        --endpoint-url $Endpoint `
        --region $Region `
        --table-name "TransformationSystem" `
        --attribute-definitions `
            AttributeName=PK,AttributeType=S `
            AttributeName=SK,AttributeType=S `
            AttributeName=GSI1PK,AttributeType=S `
            AttributeName=GSI1SK,AttributeType=S `
        --key-schema `
            AttributeName=PK,KeyType=HASH `
            AttributeName=SK,KeyType=RANGE `
        --global-secondary-indexes $gsiJson `
        --billing-mode PAY_PER_REQUEST 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Table created with GSI1" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Table creation may have failed: $result" -ForegroundColor Yellow
    }
}

# Create S3 buckets
Write-Host ""
Write-Host "--- Creating S3 Buckets ---" -ForegroundColor Cyan

# Core journey/transformation buckets
$coreBuckets = @(
    "transformation-journey-logs",
    "transformation-journey-reports"
)

# Call processing buckets (from call-scripts config)
# These use the naming convention: {capability}-{env}-{purpose}
$callBuckets = @(
    "nexus-dev-wxcc-recordings",
    "nexus-dev-wxcc-transcripts"
)

# WXCC Simulator bucket (for local testing without real WXCC)
$simulatorBuckets = @(
    "nexus-dev-wxcc-simulator"
)

$allBuckets = $coreBuckets + $callBuckets + $simulatorBuckets

foreach ($bucket in $allBuckets) {
    Write-Host "Creating S3 bucket: $bucket..." -ForegroundColor Yellow
    
    # Check if bucket exists using head-bucket (more reliable)
    $headResult = aws s3api head-bucket --bucket $bucket --endpoint-url $Endpoint --region $Region 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Bucket already exists" -ForegroundColor Green
    } else {
        # Create the bucket
        $createResult = aws s3 mb "s3://$bucket" --endpoint-url $Endpoint --region $Region 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Bucket created" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Bucket creation may have failed: $createResult" -ForegroundColor Yellow
        }
    }
}

# Create CloudWatch log groups
Write-Host ""
Write-Host "--- Creating CloudWatch Log Groups ---" -ForegroundColor Cyan

$logGroups = @(
    "/aws/nexus-backend/api",
    "/aws/nexus-backend/jobs"
)

foreach ($logGroup in $logGroups) {
    Write-Host "Creating CloudWatch log group: $logGroup..." -ForegroundColor Yellow
    aws logs create-log-group --endpoint-url $Endpoint --region $Region --log-group-name $logGroup 2>$null | Out-Null
    Write-Host "  [OK] Log group created or exists" -ForegroundColor Green
}

# Create DynamoDB tables for call processing
Write-Host ""
Write-Host "--- Creating Call Processing DynamoDB Tables ---" -ForegroundColor Cyan

# WXCC Task Tracking table (for deduplication)
Write-Host "Creating DynamoDB table: nexus-dev-wxcc-task-tracking..." -ForegroundColor Yellow
$trackingTableExists = $false
try {
    $trackingJson = aws dynamodb describe-table --endpoint-url $Endpoint --region $Region --table-name "nexus-dev-wxcc-task-tracking" 2>$null
    if ($trackingJson) {
        $trackingTableExists = $true
        Write-Host "  Table already exists" -ForegroundColor Green
    }
}
catch {
    $trackingTableExists = $false
}

if (-not $trackingTableExists) {
    aws dynamodb create-table --endpoint-url $Endpoint --region $Region --table-name "nexus-dev-wxcc-task-tracking" --attribute-definitions AttributeName=task_id,AttributeType=S --key-schema AttributeName=task_id,KeyType=HASH --billing-mode PAY_PER_REQUEST 2>$null | Out-Null
    Write-Host "  [OK] Table created" -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  LocalStack initialization complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services available:"
Write-Host "  LocalStack Gateway: $Endpoint"
Write-Host "  DynamoDB Admin:     http://localhost:8001"
Write-Host ""
