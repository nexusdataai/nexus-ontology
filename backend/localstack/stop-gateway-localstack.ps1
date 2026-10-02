# Stop Gateway and LocalStack services (Windows PowerShell)
# Usage: .\stop-gateway-localstack.ps1 [-Volumes]
#   -Volumes: Also remove LocalStack data volumes

param(
    [switch]$Volumes
)

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "🛑 Stopping Gateway + LocalStack..." -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot

# Stop Gateway
if (Test-Path ".gateway.pid") {
    $gatewayPid = Get-Content ".gateway.pid"
    $process = Get-Process -Id $gatewayPid -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "Stopping Gateway (PID: $gatewayPid)..."
        Stop-Process -Id $gatewayPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Host "✓ Gateway stopped" -ForegroundColor Green
    } else {
        Write-Host "Gateway process not running (stale PID file)"
    }
    Remove-Item ".gateway.pid" -Force -ErrorAction SilentlyContinue
} else {
    # Try to find and kill gateway process
    $gatewayProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*mcp_http_gateway*"
    }
    if ($gatewayProcesses) {
        Write-Host "Stopping Gateway processes..."
        $gatewayProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        Write-Host "✓ Gateway stopped" -ForegroundColor Green
    } else {
        Write-Host "No Gateway process found"
    }
}

# Clean up log files
Remove-Item "gateway.log", "gateway-error.log" -Force -ErrorAction SilentlyContinue

# Stop LocalStack
Write-Host ""
Write-Host "Stopping LocalStack..."

if ($Volumes) {
    Write-Host "Removing LocalStack with volumes..."
    docker-compose -f docker-compose-localstack.yml down -v 2>$null
    Remove-Item "localstack-data" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✓ LocalStack stopped and volumes removed" -ForegroundColor Green
} else {
    docker-compose -f docker-compose-localstack.yml down 2>$null
    Write-Host "✓ LocalStack stopped (data preserved)" -ForegroundColor Green
    Write-Host "   Use -Volumes to also remove data"
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ✅ All services stopped" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
