@echo off
REM ============================================================================
REM Start LocalStack for nexus-backend development (Windows CMD)
REM ============================================================================
REM This batch file is a wrapper for the PowerShell script

echo Starting LocalStack for nexus-backend...
echo.

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0start-localstack.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Failed to start LocalStack. Check the error messages above.
    pause
    exit /b %ERRORLEVEL%
)
