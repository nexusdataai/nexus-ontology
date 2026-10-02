# ============================================================================
# LocalStack Test Automation Runner (Windows PowerShell)
# ============================================================================
# Wrapper script for running LocalStack test automation on Windows.
# Passes all arguments to the Python runner module.
#
# Usage:
#   .\run-localstack-tests.ps1 [test_types] [options]
#
# Examples:
#   .\run-localstack-tests.ps1 all
#   .\run-localstack-tests.ps1 integration bdd
#   .\run-localstack-tests.ps1 all --upload
#   .\run-localstack-tests.ps1 bdd --tags smoke,regression
#   .\run-localstack-tests.ps1 endurance --duration 300
#   .\run-localstack-tests.ps1 all --skip-localstack --skip-gateway
# ============================================================================

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  LocalStack Test Automation Runner" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Change to project root
Set-Location $ProjectRoot

# Check if uv is available
$useUv = $false
try {
    $null = Get-Command uv -ErrorAction Stop
    $useUv = $true
}
catch {
    Write-Host "Note: 'uv' not found, using python directly" -ForegroundColor Yellow
}

# Build command
if ($useUv) {
    $cmd = "uv run python -m tests.localstack_automation.runner"
}
else {
    $cmd = "python -m tests.localstack_automation.runner"
}

# Add arguments
if ($Arguments) {
    $cmd += " " + ($Arguments -join " ")
}

Write-Host "Running: $cmd" -ForegroundColor Gray
Write-Host ""

# Execute
if ($useUv) {
    uv run python -m tests.localstack_automation.runner @Arguments
}
else {
    python -m tests.localstack_automation.runner @Arguments
}

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "Test run completed successfully" -ForegroundColor Green
}
else {
    Write-Host "Test run failed with exit code: $exitCode" -ForegroundColor Red
}

exit $exitCode
