@echo off
chcp 65001 > nul
title JARVIS - Autonomous AI Assistant

REM 1. Auto-detect project directory even if run from Desktop or external folder
set "PROJECT_DIR=%~dp0"
if not exist "%PROJECT_DIR%.venv\Scripts\activate.bat" (
    set "PROJECT_DIR=c:\Users\majun\Coding\javis\"
)

if not exist "%PROJECT_DIR%.venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment .venv was not found.
    echo Searched location: %PROJECT_DIR%
    pause
    exit /b 1
)

REM 2. Switch working directory to project root
cd /d "%PROJECT_DIR%"

REM 3. Activate Python virtual environment
call "%PROJECT_DIR%.venv\Scripts\activate.bat"

REM 4. Set PYTHONPATH
set PYTHONPATH=%PROJECT_DIR%src;%PYTHONPATH%

echo ===================================================================
echo   JARVIS System Starting...
echo ===================================================================
echo.

python -m jarvis.main %*

if errorlevel 1 (
    echo.
    echo [Warning] Jarvis exited with error code %errorlevel%.
)

echo.
pause
