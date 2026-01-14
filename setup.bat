@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   StreamCaptioner - First Time Setup
echo ============================================
echo.

:: Check for Python
echo [1/6] Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo       Found Python %PYVER%

:: Get the directory where this script is located
cd /d "%~dp0"
echo.
echo [2/6] Working directory: %CD%

:: Create virtual environment
echo.
echo [3/6] Creating virtual environment...
if exist venv (
    echo       Virtual environment already exists, skipping...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo       Virtual environment created successfully
)

:: Activate and install dependencies
echo.
echo [4/6] Installing dependencies...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo       Dependencies installed successfully

:: Check for config.json
echo.
echo [5/6] Checking configuration...
if exist config.json (
    echo       config.json already exists
) else (
    if exist config.example.json (
        copy config.example.json config.json >nul
        echo       Created config.json from example - please edit it for your setup
    ) else (
        echo WARNING: No config.example.json found
    )
)

:: Check for .env file
echo.
echo [6/6] Checking environment variables...
if exist .env (
    echo       .env file already exists
) else (
    echo DEEPGRAM_API_KEY=your_api_key_here> .env
    echo       Created .env file - IMPORTANT: Edit this file and add your Deepgram API key!
)

echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo Next steps:
echo   1. Edit .env and add your Deepgram API key
echo   2. Edit config.json to match your audio setup
echo   3. Run start.bat to launch StreamCaptioner
echo.
pause

