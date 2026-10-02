# ============================================================================
# Test LocalStack for nexus-backend (Windows PowerShell)
# ============================================================================
# Verifies LocalStack is running and all resources are properly configured.
# ============================================================================

param(
    [string]$Endpoint = "http://localhost:4566",
    [string]$Region = "us-east-1"
)

$ErrorActionPreference = "Continue"

$env:AWS_ACCESS_KEY_ID = "test"
$env:AWS_SECRET_ACCESS_KEY = "test"
$env:AWS_DEFAULT_REGION = $Region

$Passed = 0
$Failed = 0

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Testing nexus-backend LocalStack" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Endpoint: $Endpoint"
Write-Host "Region:   $Region"
Write-Host ""

function Test-Check {
    param(
        [string]$Name,
        [bool]$Result
    )
    
    if ($Result) {
        Write-Host "  [PASS] $Name" -ForegroundColor Green
        $script:Passed++
    }
    else {
        Write-Host "  [FAIL] $Name" -ForegroundColor Red
        $script:Failed++
    }
}

# Test LocalStack health
Write-Host "Testing LocalStack Health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$Endpoint/_localstack/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
    Test-Check -Name "LocalStack health endpoint" -Result ($null -ne $health.services.dynamodb)
}
catch {
    Test-Check -Name "LocalStack health endpoint" -Result $false
}

# Test DynamoDB
Write-Host ""
Write-Host "Testing DynamoDB..." -ForegroundColor Yellow

# TransformationSystem table
try {
    $tableJson = aws dynamodb describe-table --endpoint-url $Endpoint --region $Region --table-name "TransformationSystem" 2>$null
    $table = $tableJson | ConvertFrom-Json
    Test-Check -Name "TransformationSystem table exists" -Result ($null -ne $table.Table)
    
    # Test GSI1 index
    $hasGSI = $table.Table.GlobalSecondaryIndexes | Where-Object { $_.IndexName -eq "GSI1" }
    Test-Check -Name "GSI1 index exists" -Result ($null -ne $hasGSI)
}
catch {
    Test-Check -Name "TransformationSystem table exists" -Result $false
    Test-Check -Name "GSI1 index exists" -Result $false
}

# WXCC Task Tracking table
try {
    $trackingJson = aws dynamodb describe-table --endpoint-url $Endpoint --region $Region --table-name "nexus-dev-wxcc-task-tracking" 2>$null
    $trackingTable = $trackingJson | ConvertFrom-Json
    Test-Check -Name "WXCC task tracking table exists" -Result ($null -ne $trackingTable.Table)
}
catch {
    Test-Check -Name "WXCC task tracking table exists" -Result $false
}

# Test S3 buckets
Write-Host ""
Write-Host "Testing S3 Buckets..." -ForegroundColor Yellow

# Core journey/transformation buckets
$coreBuckets = @(
    "transformation-journey-logs",
    "transformation-journey-reports"
)

# Call processing buckets
$callBuckets = @(
    "nexus-dev-wxcc-recordings",
    "nexus-dev-wxcc-transcripts"
)

# WXCC Simulator bucket
$simulatorBuckets = @(
    "nexus-dev-wxcc-simulator"
)

$allBuckets = $coreBuckets + $callBuckets + $simulatorBuckets

foreach ($bucket in $allBuckets) {
    try {
        $null = aws s3 ls "s3://$bucket" --endpoint-url $Endpoint --region $Region 2>$null
        Test-Check -Name "S3 bucket: $bucket" -Result $true
    }
    catch {
        Test-Check -Name "S3 bucket: $bucket" -Result $false
    }
}

# Test CloudWatch log groups
Write-Host ""
Write-Host "Testing CloudWatch Log Groups..." -ForegroundColor Yellow
$logGroups = @(
    "/aws/nexus-backend/api",
    "/aws/nexus-backend/jobs"
)

foreach ($logGroup in $logGroups) {
    try {
        $resultJson = aws logs describe-log-groups --endpoint-url $Endpoint --region $Region --log-group-name-prefix $logGroup 2>$null
        $result = $resultJson | ConvertFrom-Json
        $exists = $result.logGroups | Where-Object { $_.logGroupName -eq $logGroup }
        Test-Check -Name "Log group: $logGroup" -Result ($null -ne $exists)
    }
    catch {
        Test-Check -Name "Log group: $logGroup" -Result $false
    }
}

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Passed: $Passed" -ForegroundColor Green
Write-Host "  Failed: $Failed" -ForegroundColor Red
Write-Host ""

if ($Failed -eq 0) {
    Write-Host "All tests passed!" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "Some tests failed. Run .\localstack\localstack-init.ps1 to fix." -ForegroundColor Red
    exit 1
}
