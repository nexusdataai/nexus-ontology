# Start LocalStack and Gateway together for local development (Windows PowerShell)
# This script provides a single command to start the complete local development environment

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "Starting LocalStack + Gateway for nexus-backend..." -ForegroundColor Cyan
Write-Host ""

# Check Docker
$dockerRunning = $false
try {
    $null = docker info 2>$null
    if ($LASTEXITCODE -eq 0) {
        $dockerRunning = $true
    }
}
catch {
    $dockerRunning = $false
}

if (-not $dockerRunning) {
    Write-Host "Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host "Docker is running" -ForegroundColor Green

# Navigate to project root
Set-Location $ProjectRoot

# Start LocalStack
Write-Host ""
Write-Host "Starting LocalStack..." -ForegroundColor Yellow
docker-compose -f docker-compose-localstack.yml up -d

# Wait for LocalStack health
Write-Host "Waiting for LocalStack to be healthy..." -ForegroundColor Yellow
$timeout = 60
$localstackReady = $false

while ($timeout -gt 0) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:4566/_localstack/health" -ErrorAction SilentlyContinue
        if ($health.services.dynamodb -eq "running" -or $health.services.dynamodb -eq "available") {
            $localstackReady = $true
            break
        }
    }
    catch {
        # Continue waiting
    }
    Start-Sleep -Seconds 2
    $timeout = $timeout - 2
    Write-Host "." -NoNewline
}
Write-Host ""

if (-not $localstackReady) {
    Write-Host "LocalStack failed to start within timeout" -ForegroundColor Red
    Write-Host "   Check logs: docker logs nexus-localstack"
    exit 1
}

Write-Host "LocalStack is ready!" -ForegroundColor Green

# Ensure .env.local exists with LocalStack settings
if (-not (Test-Path ".env.local")) {
    if (Test-Path ".env.localstack.example") {
        Write-Host ""
        Write-Host "Creating .env.local from template..." -ForegroundColor Yellow
        Copy-Item ".env.localstack.example" ".env.local"
        Write-Host "Created .env.local" -ForegroundColor Green
    }
    else {
        Write-Host ""
        Write-Host "No .env.localstack.example found. Creating minimal .env.local..." -ForegroundColor Yellow
        $minimalEnv = "# LocalStack Configuration`nUSE_LOCALSTACK=true`nLOCALSTACK_HOST=localhost`nLOCALSTACK_PORT=4566`nAWS_DEFAULT_REGION=us-east-1`nAWS_ACCESS_KEY_ID=test`nAWS_SECRET_ACCESS_KEY=test`nLOG_LEVEL=DEBUG"
        $minimalEnv | Out-File -FilePath ".env.local" -Encoding UTF8
        Write-Host "Created minimal .env.local" -ForegroundColor Green
    }
}

# Check if gateway is already running
Write-Host ""
Write-Host "Starting Gateway server..." -ForegroundColor Yellow

$gatewayAlreadyRunning = $false
try {
    $null = Invoke-RestMethod -Uri "http://localhost:8000/health" -ErrorAction Stop
    $gatewayAlreadyRunning = $true
}
catch {
    $gatewayAlreadyRunning = $false
}

if ($gatewayAlreadyRunning) {
    Write-Host "Gateway appears to be already running on port 8000" -ForegroundColor Yellow
    Write-Host "   Stop it first or use a different port"
}
else {
    # Gateway not running, start it using uv run for proper virtual environment
    $gateway = Start-Process -FilePath "uv" -ArgumentList "run", "python", "mcp_http_gateway.py", "--host", "0.0.0.0", "--port", "8000" -PassThru -NoNewWindow -RedirectStandardOutput "gateway.log" -RedirectStandardError "gateway-error.log"
    $gateway.Id | Out-File -FilePath ".gateway.pid" -Encoding UTF8
    
    # Wait for gateway to be ready
    Write-Host "Waiting for Gateway to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    $gatewayTimeout = 30
    $gatewayStarted = $false
    
    while ($gatewayTimeout -gt 0) {
        try {
            $null = Invoke-RestMethod -Uri "http://localhost:8000/health" -ErrorAction Stop
            $gatewayStarted = $true
            break
        }
        catch {
            Start-Sleep -Seconds 1
            $gatewayTimeout = $gatewayTimeout - 1
            Write-Host "." -NoNewline
        }
    }
    Write-Host ""
    
    if (-not $gatewayStarted) {
        Write-Host "Gateway failed to start" -ForegroundColor Red
        Write-Host "   Check logs: Get-Content gateway.log"
        Write-Host "   Check errors: Get-Content gateway-error.log"
        Stop-Process -Id $gateway.Id -ErrorAction SilentlyContinue
        exit 1
    }
}

# Verify LocalStack health through gateway
Write-Host ""
Write-Host "Verifying LocalStack connectivity through Gateway..." -ForegroundColor Yellow

$localstackVerified = $false
try {
    $localstackHealth = Invoke-RestMethod -Uri "http://localhost:8000/health/localstack" -ErrorAction Stop
    if ($localstackHealth.status -eq "healthy") {
        Write-Host "LocalStack connectivity verified!" -ForegroundColor Green
        $localstackVerified = $true
    }
    else {
        Write-Host "LocalStack status: $($localstackHealth.status)" -ForegroundColor Yellow
        Write-Host "   Check: Invoke-RestMethod http://localhost:8000/health/localstack"
    }
}
catch {
    Write-Host "Could not verify LocalStack connectivity" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Gateway + LocalStack ready!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
Write-Host "   Gateway:           http://localhost:8000"
Write-Host "   API Docs:          http://localhost:8000/docs"
Write-Host "   LocalStack:        http://localhost:4566"
Write-Host "   DynamoDB Admin:    http://localhost:8001"
Write-Host "   LocalStack Health: http://localhost:8000/health/localstack"
Write-Host ""
Write-Host "Quick Commands:" -ForegroundColor Cyan
Write-Host "   Test Gateway:      Invoke-RestMethod http://localhost:8000/health"
Write-Host "   Test LocalStack:   Invoke-RestMethod http://localhost:8000/health/localstack"
Write-Host "   View Gateway Logs: Get-Content gateway.log -Tail 50"
Write-Host "   Stop All:          .\localstack\stop-gateway-localstack.ps1"
Write-Host ""

if (Test-Path ".gateway.pid") {
    $gatewayPid = Get-Content ".gateway.pid"
    Write-Host "Gateway PID: $gatewayPid"
}
