# ============================================================================
# Stop LocalStack for nexus-backend (Windows PowerShell)
# ============================================================================

param(
    [switch]$Volumes,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

if ($Help) {
    Write-Host "Usage: .\stop-localstack.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Volumes  Remove volumes (delete all data)"
    Write-Host "  -Help     Show this help message"
    exit 0
}

Write-Host "🛑 Stopping LocalStack for nexus-backend..." -ForegroundColor Cyan
Write-Host ""

# Determine docker-compose command
$composeCmd = $null
try {
    $null = docker compose version 2>$null
    $composeCmd = "docker compose"
} catch {
    $composeCmd = "docker-compose"
}

Set-Location $ProjectRoot

if ($Volumes) {
    Write-Host "Stopping services and removing volumes..." -ForegroundColor Yellow
    if ($composeCmd -eq "docker compose") {
        docker compose -f docker-compose-localstack.yml down -v
    } else {
        docker-compose -f docker-compose-localstack.yml down -v
    }
    Write-Host "✓ Services stopped and volumes removed" -ForegroundColor Green
} else {
    Write-Host "Stopping services..." -ForegroundColor Yellow
    if ($composeCmd -eq "docker compose") {
        docker compose -f docker-compose-localstack.yml down
    } else {
        docker-compose -f docker-compose-localstack.yml down
    }
    Write-Host "✓ Services stopped" -ForegroundColor Green
}

Write-Host ""
Write-Host "✅ LocalStack stopped successfully" -ForegroundColor Green
Write-Host ""
Write-Host "To remove all data, run: .\stop-localstack.ps1 -Volumes"
Write-Host ""
