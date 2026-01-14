@echo off
title StreamCaptioner - Live Captioning System
echo ============================================
echo   StreamCaptioner - Live Captioning System
echo ============================================
echo.

cd /d "%~dp0"

:: Check if first-time setup is needed
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found - running first-time setup...
    echo.

    :: Check for Python
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed or not in PATH
        echo Please install Python 3.10+ from https://python.org
        echo Make sure to check "Add Python to PATH" during installation
        pause
        exit /b 1
    )

    :: Create venv
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )

    :: Install dependencies
    echo Installing dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )

    :: Create config if needed
    if not exist config.json (
        if exist config.example.json (
            copy config.example.json config.json >nul
            echo Created config.json - please edit for your setup
        )
    )

    :: Create .env if needed
    if not exist .env (
        echo DEEPGRAM_API_KEY=your_api_key_here> .env
        echo.
        echo ============================================
        echo   IMPORTANT: Setup required!
        echo ============================================
        echo.
        echo Created .env file - you MUST edit it and add your Deepgram API key
        echo Get your free API key at: https://deepgram.com
        echo.
        echo Also edit config.json to match your audio setup.
        echo.
        pause
        exit /b 0
    )

    echo Setup complete!
    echo.
)

:: Check for .env file
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Please create .env with your DEEPGRAM_API_KEY
    pause
    exit /b 1
)

:: Activate and run
call venv\Scripts\activate.bat
python -m src.main

if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)

