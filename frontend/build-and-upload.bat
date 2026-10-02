@echo off
setlocal enabledelayedexpansion

REM Simple Build and Upload Script for Nexus Telco UI
REM Usage: build-and-upload.bat <s3-bucket> [s3-path]
REM Example: build-and-upload.bat my-bucket
REM Example: build-and-upload.bat my-bucket nexus-ui/builds

REM Check arguments
if "%~1"=="" (
    echo Usage: %~nx0 ^<s3-bucket^> [s3-path]
    echo Examples:
    echo   %~nx0 my-bucket                    # Upload to bucket root
    echo   %~nx0 my-bucket nexus-ui/builds  # Upload to specific path
    exit /b 1
)

set S3_BUCKET=%~1
set S3_PATH=%~2

REM Get project root (directory where this script lives)
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"
set PROJECT_ROOT=%cd%

echo Starting build process...

REM Step 1: Clean (manually remove dist folder - npm clean uses Unix rm command)
echo Cleaning previous build...
if exist "dist" (
    rmdir /s /q "dist"
    echo   √ Removed dist folder
)

REM Step 2: Build
echo Building application...
call npm run build
if errorlevel 1 (
    echo ERROR: Build failed
    exit /b 1
)

REM Step 3: Ensure public folder contents are included in dist
echo Ensuring public folder contents are in dist...
if exist "public\results" (
    xcopy /E /I /Y "public\results" "dist\results" >nul
    echo   √ Copied results folder
)
if exist "public\transcripts" (
    xcopy /E /I /Y "public\transcripts" "dist\transcripts" >nul
    echo   √ Copied transcripts folder
)
if exist "public\recordings" (
    xcopy /E /I /Y "public\recordings" "dist\recordings" >nul
    echo   √ Copied recordings folder
)

REM Step 4: Get version from package.json
for /f "delims=" %%v in ('node -p "require('./package.json').version"') do set VERSION=%%v
set ZIP_NAME=nexus-ui-%VERSION%.zip

REM Step 5: Create zip using PowerShell (built-in on Windows 10+)
echo Creating %ZIP_NAME%...
if exist "%ZIP_NAME%" del "%ZIP_NAME%"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\*' -DestinationPath '%ZIP_NAME%' -Force"
if errorlevel 1 (
    echo ERROR: Failed to create zip file
    exit /b 1
)

REM Step 6: Upload to S3
echo Uploading to S3...
if "%S3_PATH%"=="" (
    REM Upload to bucket root
    aws s3 cp "%ZIP_NAME%" "s3://%S3_BUCKET%/%ZIP_NAME%"
    set UPLOAD_PATH=s3://%S3_BUCKET%/%ZIP_NAME%
) else (
    REM Upload to specific path
    aws s3 cp "%ZIP_NAME%" "s3://%S3_BUCKET%/%S3_PATH%/%ZIP_NAME%"
    set UPLOAD_PATH=s3://%S3_BUCKET%/%S3_PATH%/%ZIP_NAME%
)
if errorlevel 1 (
    echo ERROR: S3 upload failed
    exit /b 1
)

REM Step 7: Clean up local zip
del "%ZIP_NAME%"

echo.
echo √ Complete!
echo Uploaded: %UPLOAD_PATH%

endlocal
