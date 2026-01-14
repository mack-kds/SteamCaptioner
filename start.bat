@echo off
title StreamCaptioner - Live Captioning System
echo ============================================
echo   StreamCaptioner - Live Captioning System
echo ============================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

if not exist ".env" (
    echo WARNING: .env file not found!
    echo Please create .env with your DEEPGRAM_API_KEY
    pause
)

call venv\Scripts\activate.bat
python -m src.main

if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)

