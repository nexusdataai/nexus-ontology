# ============================================================================
# Start LocalStack for nexus-backend development (Windows PowerShell)
# ============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "🚀 Starting LocalStack for nexus-backend..." -ForegroundColor Cyan
Write-Host ""

# Check Docker is running
try {
    $null = docker info 2>$null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check docker-compose
$composeCmd = $null
try {
    $null = docker compose version 2>$null
    $composeCmd = "docker compose"
    Write-Host "✓ docker compose available" -ForegroundColor Green
} catch {
    try {
        $null = docker-compose version 2>$null
        $composeCmd = "docker-compose"
        Write-Host "✓ docker-compose available" -ForegroundColor Green
    } catch {
        Write-Host "❌ docker-compose is not installed." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Start services
Write-Host "Starting LocalStack services..." -ForegroundColor Yellow
Set-Location $ProjectRoot

if ($composeCmd -eq "docker compose") {
    docker compose -f docker-compose-localstack.yml up -d
} else {
    docker-compose -f docker-compose-localstack.yml up -d
}

# Wait for LocalStack to be healthy
Write-Host ""
Write-Host "⏳ Waiting for LocalStack to be healthy..." -ForegroundColor Yellow
$timeout = 60
while ($timeout -gt 0) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:4566/_localstack/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($health.services.dynamodb) {
            break
        }
    } catch {
        # Ignore errors, keep trying
    }
    Write-Host "  Waiting... ($timeout seconds remaining)"
    Start-Sleep -Seconds 2
    $timeout -= 2
}

if ($timeout -le 0) {
    Write-Host "❌ LocalStack failed to start within timeout" -ForegroundColor Red
    Write-Host "   Check logs: docker logs nexus-localstack"
    exit 1
}

Write-Host "✓ LocalStack is healthy" -ForegroundColor Green

# Run initialization script
Write-Host ""
Write-Host "Running initialization script..." -ForegroundColor Yellow
& "$ScriptDir\localstack-init.ps1"

Write-Host ""
Write-Host "✅ LocalStack is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Service URLs:" -ForegroundColor Cyan
Write-Host "   LocalStack Gateway:  http://localhost:4566"
Write-Host "   DynamoDB Admin:      http://localhost:8001"
Write-Host ""
Write-Host "🔧 Environment variables to set:" -ForegroundColor Cyan
Write-Host '   $env:USE_LOCALSTACK = "true"'
Write-Host '   $env:LOCALSTACK_HOST = "localhost"'
Write-Host ""
Write-Host "📝 Or copy the example env file:" -ForegroundColor Cyan
Write-Host "   Copy-Item .env.localstack.example .env.local"
Write-Host ""
