# ============================================================================
# Reset LocalStack for nexus-backend (Windows PowerShell)
# ============================================================================
# Completely resets LocalStack by:
# 1. Stopping all services (Gateway + LocalStack)
# 2. Removing Docker volumes and data
# 3. Restarting LocalStack with fresh state
# 4. Re-initializing all resources
#
# Usage:
#   .\reset-localstack.ps1              # Full reset and restart
#   .\reset-localstack.ps1 -NoRestart   # Reset only, don't restart
#   .\reset-localstack.ps1 -DataOnly    # Clear data without stopping container
# ============================================================================

param(
    [switch]$NoRestart,
    [switch]$DataOnly,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

if ($Help) {
    Write-Host "Usage: .\reset-localstack.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -NoRestart  Reset data but don't restart services"
    Write-Host "  -DataOnly   Clear data without stopping container (uses AWS CLI)"
    Write-Host "  -Help       Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\reset-localstack.ps1              # Full reset and restart"
    Write-Host "  .\reset-localstack.ps1 -NoRestart   # Reset only"
    Write-Host "  .\reset-localstack.ps1 -DataOnly    # Clear data in running LocalStack"
    exit 0
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Resetting LocalStack for nexus-backend" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot

$env:AWS_ACCESS_KEY_ID = "test"
$env:AWS_SECRET_ACCESS_KEY = "test"
$env:AWS_DEFAULT_REGION = "us-east-1"
$Endpoint = "http://localhost:4566"

if ($DataOnly) {
    # Clear data without stopping container
    Write-Host "Clearing LocalStack data (container stays running)..." -ForegroundColor Yellow
    Write-Host ""
    
    # Check if LocalStack is running
    $localstackRunning = $false
    try {
        $health = Invoke-RestMethod -Uri "$Endpoint/_localstack/health" -TimeoutSec 5 -ErrorAction Stop
        $localstackRunning = $true
        Write-Host "[OK] LocalStack is running" -ForegroundColor Green
    }
    catch {
        Write-Host "[FAIL] LocalStack is not running. Start it first or use full reset." -ForegroundColor Red
        exit 1
    }
    
    # Delete all items from DynamoDB tables
    Write-Host ""
    Write-Host "Clearing DynamoDB tables..." -ForegroundColor Yellow
    
    $tables = @("TransformationSystem", "nexus-dev-wxcc-task-tracking")
    foreach ($table in $tables) {
        Write-Host "  Clearing table: $table"
        try {
            # Scan table
            $scanJson = aws dynamodb scan --endpoint-url $Endpoint --table-name $table --output json 2>$null
            if ($scanJson) {
                $scanResult = $scanJson | ConvertFrom-Json
                $itemCount = 0
                if ($scanResult.Items -and $scanResult.Items.Count -gt 0) {
                    foreach ($item in $scanResult.Items) {
                        if ($table -eq "TransformationSystem") {
                            $pk = $item.PK.S
                            $sk = $item.SK.S
                            $keyJson = '{"PK":{"S":"' + $pk + '"},"SK":{"S":"' + $sk + '"}}'
                            aws dynamodb delete-item --endpoint-url $Endpoint --table-name $table --key $keyJson 2>$null | Out-Null
                        }
                        else {
                            $taskId = $item.task_id.S
                            $keyJson = '{"task_id":{"S":"' + $taskId + '"}}'
                            aws dynamodb delete-item --endpoint-url $Endpoint --table-name $table --key $keyJson 2>$null | Out-Null
                        }
                        $itemCount++
                    }
                    Write-Host "    [OK] Cleared $itemCount items" -ForegroundColor Green
                }
                else {
                    Write-Host "    [OK] Table already empty" -ForegroundColor Green
                }
            }
        }
        catch {
            Write-Host "    [WARN] Table may not exist or error occurred" -ForegroundColor Yellow
        }
    }
    
    # Clear S3 buckets
    Write-Host ""
    Write-Host "Clearing S3 buckets..." -ForegroundColor Yellow
    
    $buckets = @(
        "transformation-journey-logs",
        "transformation-journey-reports",
        "nexus-dev-wxcc-recordings",
        "nexus-dev-wxcc-transcripts",
        "nexus-dev-wxcc-simulator",
        "test-reports"
    )
    
    foreach ($bucket in $buckets) {
        Write-Host "  Clearing bucket: $bucket"
        try {
            aws s3 rm "s3://$bucket" --endpoint-url $Endpoint --recursive 2>$null | Out-Null
            Write-Host "    [OK] Cleared" -ForegroundColor Green
        }
        catch {
            Write-Host "    [WARN] Bucket may not exist" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "[OK] LocalStack data cleared!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Resources are empty but still exist. Run seed script to add test data:"
    Write-Host "  python localstack/seed-localstack-data.py"
    exit 0
}

# Full reset - stop everything first
Write-Host "Step 1: Stopping all services..." -ForegroundColor Yellow

# Stop Gateway if running
if (Test-Path ".gateway.pid") {
    $gatewayPid = Get-Content ".gateway.pid" -ErrorAction SilentlyContinue
    if ($gatewayPid) {
        $process = Get-Process -Id $gatewayPid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "  Stopping Gateway (PID: $gatewayPid)..."
            Stop-Process -Id $gatewayPid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
    }
    Remove-Item ".gateway.pid" -Force -ErrorAction SilentlyContinue
}

# Clean up gateway logs
Remove-Item "gateway.log" -Force -ErrorAction SilentlyContinue
Remove-Item "gateway-error.log" -Force -ErrorAction SilentlyContinue

# Stop LocalStack and remove volumes
Write-Host "  Stopping LocalStack and removing volumes..."
$ErrorActionPreference = "Continue"
docker-compose -f docker-compose-localstack.yml down -v 2>&1 | Out-Null
$ErrorActionPreference = "Stop"

Write-Host "[OK] Services stopped" -ForegroundColor Green

# Remove local data directory
Write-Host ""
Write-Host "Step 2: Removing local data..." -ForegroundColor Yellow

if (Test-Path "localstack-data") {
    Remove-Item "localstack-data" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Removed localstack-data directory" -ForegroundColor Green
}
else {
    Write-Host "[OK] No local data to remove" -ForegroundColor Green
}

# Remove any orphaned Docker volumes
Write-Host ""
Write-Host "Step 3: Cleaning up Docker resources..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
docker volume prune -f 2>&1 | Out-Null
$ErrorActionPreference = "Stop"
Write-Host "[OK] Docker volumes cleaned" -ForegroundColor Green

if ($NoRestart) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "  [OK] LocalStack reset complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To start LocalStack again, run:"
    Write-Host "  .\localstack\start-localstack.ps1"
    Write-Host ""
    Write-Host "Or to start with Gateway:"
    Write-Host "  .\localstack\start-gateway-localstack.ps1"
    exit 0
}

# Restart LocalStack
Write-Host ""
Write-Host "Step 4: Starting fresh LocalStack..." -ForegroundColor Yellow

$ErrorActionPreference = "Continue"
docker-compose -f docker-compose-localstack.yml up -d 2>&1 | Out-Null
$ErrorActionPreference = "Stop"

# Wait for health
Write-Host "  Waiting for LocalStack to be healthy..."
$timeout = 60
$localstackReady = $false

while ($timeout -gt 0) {
    try {
        $health = Invoke-RestMethod -Uri "$Endpoint/_localstack/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($health.services.dynamodb) {
            $localstackReady = $true
            break
        }
    }
    catch {
        # Continue waiting
    }
    Start-Sleep -Seconds 2
    $timeout -= 2
    Write-Host "." -NoNewline
}
Write-Host ""

if (-not $localstackReady) {
    Write-Host "[FAIL] LocalStack failed to start" -ForegroundColor Red
    Write-Host "   Check logs: docker logs nexus-localstack"
    exit 1
}

Write-Host "[OK] LocalStack is healthy" -ForegroundColor Green

# Re-initialize resources
Write-Host ""
Write-Host "Step 5: Initializing resources..." -ForegroundColor Yellow
& "$ScriptDir\localstack-init.ps1" -Endpoint $Endpoint

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  [OK] LocalStack reset and ready!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service URLs:"
Write-Host "  LocalStack Gateway:  http://localhost:4566"
Write-Host "  DynamoDB Admin:      http://localhost:8001"
Write-Host ""
Write-Host "To seed test data:"
Write-Host "  python localstack/seed-localstack-data.py"
Write-Host ""
Write-Host "To start Gateway:"
Write-Host "  .\localstack\start-gateway-localstack.ps1"
Write-Host ""
